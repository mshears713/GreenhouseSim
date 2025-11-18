"""
Simulation Engine for Greenhouse Environmental Modeling

This module implements the core simulation loop and coordinates
environmental models for temperature, moisture, airflow, etc.

Educational Note:
Simulation allows testing control strategies without hardware:
- Model physical processes (heat transfer, evaporation)
- Validate control algorithms
- Tune parameters safely
- Demonstrate failure modes
"""

import time
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import yaml
from pathlib import Path

from ..data.models import (
    EnvironmentState,
    ActuatorState,
    ActuatorType,
    ControlParameters
)

from .temperature_model import TemperatureModel
from .moisture_model import MoistureModel
from .airflow_model import AirflowModel
from .failure_modes import FailureModeSimulator


logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Main simulation engine coordinating environmental models

    Runs a real-time simulation loop updating environmental variables
    based on physical models and actuator states.

    Educational Note:
    The simulation uses numerical integration to update state variables:
    1. Calculate rates of change (dX/dt) based on current state
    2. Update state: X_new = X_old + (dX/dt) * dt
    3. Repeat at fixed time steps

    This is called "Euler integration" - simple but effective for
    our purposes.
    """

    def __init__(self, config_path: str = "simulation_config.yaml"):
        """
        Initialize simulation engine

        Args:
            config_path: Path to simulation configuration YAML file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Simulation parameters
        self.time_step = self.config.get('temperature', {}).get('time_constant', 0.1)
        self.running = False
        self.paused = False

        # Current environmental state
        self.environment = EnvironmentState(
            temperature=self.config.get('temperature', {}).get('initial', 22.0),
            moisture=self.config.get('moisture', {}).get('initial', 50.0),
            humidity=self.config.get('humidity', {}).get('initial', 60.0),
            airflow=0.0,
            light_level=0.0,
            ambient_temperature=self.config.get('temperature', {}).get('ambient', 20.0),
            is_simulated=True
        )

        # Current actuator states
        self.actuators: Dict[ActuatorType, ActuatorState] = {
            ActuatorType.FAN: ActuatorState(
                actuator_type=ActuatorType.FAN,
                enabled=False,
                value=0.0,
                unit='%'
            ),
            ActuatorType.HEATER: ActuatorState(
                actuator_type=ActuatorType.HEATER,
                enabled=False,
                value=0.0,
                unit='%'
            ),
            ActuatorType.PUMP: ActuatorState(
                actuator_type=ActuatorType.PUMP,
                enabled=False,
                value=0.0,
                unit='%'
            ),
            ActuatorType.VENT: ActuatorState(
                actuator_type=ActuatorType.VENT,
                enabled=True,
                value=90.0,  # Half open
                unit='degrees'
            )
        }

        # Simulation thread
        self.sim_thread: Optional[threading.Thread] = None

        # Timing
        self.sim_time = 0.0  # Simulated time in seconds
        self.iteration_count = 0

        # Statistics
        self.updates_per_second = 0.0
        self.last_update_time = time.time()

        # Initialize detailed physics models
        self.temperature_model = TemperatureModel(self.config)
        self.moisture_model = MoistureModel(self.config)
        self.airflow_model = AirflowModel(self.config)
        self.failure_simulator = FailureModeSimulator(self.config)

        logger.info("SimulationEngine initialized with detailed physics models")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load simulation configuration from YAML file"""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Config file {config_path} not found, using defaults")
                return {}

            with open(path, 'r') as f:
                config = yaml.safe_load(f)

            logger.info(f"Loaded configuration from {config_path}")
            return config

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def start(self):
        """Start simulation loop in background thread"""
        if self.running:
            logger.warning("Simulation already running")
            return

        self.running = True
        self.sim_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.sim_thread.start()

        logger.info("Simulation started")

    def stop(self):
        """Stop simulation loop"""
        if not self.running:
            return

        self.running = False
        if self.sim_thread:
            self.sim_thread.join(timeout=1.0)

        logger.info("Simulation stopped")

    def pause(self):
        """Pause simulation (keeps thread running, but stops updates)"""
        self.paused = True
        logger.info("Simulation paused")

    def resume(self):
        """Resume paused simulation"""
        self.paused = False
        logger.info("Simulation resumed")

    def _simulation_loop(self):
        """
        Main simulation loop (runs in background thread)

        Educational Note:
        Real-time simulation maintains wall-clock synchronization:
        - Update at fixed intervals (e.g., 10 Hz)
        - Keep simulation time aligned with real time
        - Allows "slow-motion" or "fast-forward" by adjusting time scale
        """
        logger.info("Simulation loop started")

        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            loop_start = time.time()

            # Update simulation state
            self._update_state(self.time_step)

            # Update statistics
            self.iteration_count += 1
            self.sim_time += self.time_step

            # Calculate update rate
            elapsed = time.time() - self.last_update_time
            if elapsed > 1.0:
                self.updates_per_second = self.iteration_count / elapsed
                self.iteration_count = 0
                self.last_update_time = time.time()

            # Sleep to maintain real-time synchronization
            loop_duration = time.time() - loop_start
            sleep_time = max(0, self.time_step - loop_duration)
            time.sleep(sleep_time)

        logger.info("Simulation loop stopped")

    def _update_state(self, dt: float):
        """
        Update all environmental variables for one time step

        Args:
            dt: Time step in seconds

        Educational Note:
        This is where the physics happens! Each update:
        1. Reads current actuator states
        2. Applies failure modes (if enabled)
        3. Calculates environmental changes using detailed models
        4. Updates state variables
        """
        # Update failure simulator
        self.failure_simulator.update(self.sim_time)

        # Get actuator states (with potential failures applied)
        fan = self.actuators[ActuatorType.FAN]
        heater = self.actuators[ActuatorType.HEATER]
        pump = self.actuators[ActuatorType.PUMP]
        vent = self.actuators[ActuatorType.VENT]

        # Apply actuator failures
        fan_state, fan_value = self.failure_simulator.check_actuator_failure(
            'fan', fan.enabled, fan.value
        )
        heater_state, heater_value = self.failure_simulator.check_actuator_failure(
            'heater', heater.enabled, heater.value
        )
        pump_state, pump_value = self.failure_simulator.check_actuator_failure(
            'pump', pump.enabled, pump.value
        )

        # Check for reservoir empty (pump can't work)
        if self.failure_simulator.is_reservoir_empty():
            pump_state = False

        # Check for power loss (all actuators fail)
        if self.failure_simulator.is_power_lost():
            fan_state = heater_state = pump_state = False
            fan_value = heater_value = pump_value = 0.0

        # Update airflow model first (needed by other models)
        airflow = self.airflow_model.update(
            dt=dt,
            fan_speed_percent=fan_value if fan_state else 0.0,
            vent_position_percent=vent.value,
            temperature=self.environment.temperature,
            ambient_temperature=self.environment.ambient_temperature
        )
        self.environment.airflow = self.failure_simulator.apply_sensor_failure('airflow', airflow)

        # Update temperature model
        temp = self.temperature_model.update(
            dt=dt,
            heater_on=heater_state,
            heater_power_percent=heater_value,
            fan_speed_percent=fan_value if fan_state else 0.0,
            current_time_seconds=self.sim_time
        )
        self.environment.temperature = self.failure_simulator.apply_sensor_failure('temperature', temp)

        # Update moisture model
        moisture = self.moisture_model.update(
            dt=dt,
            pump_on=pump_state,
            temperature=self.temperature_model.get_temperature(),  # Use actual temp for evaporation
            humidity=self.environment.humidity,
            airflow=self.airflow_model.get_airflow()
        )
        self.environment.moisture = self.failure_simulator.apply_sensor_failure('moisture', moisture)

        # Update humidity (simplified - affected by evaporation and ventilation)
        self._update_humidity(dt)

        # Update light level (time-of-day dependent)
        self._update_light(dt)

        # Apply environmental stress to ambient temperature
        base_ambient = self.config.get('temperature', {}).get('ambient_temperature', 20.0)
        stressed_ambient = self.failure_simulator.get_environmental_stress(base_ambient)
        self.environment.ambient_temperature = stressed_ambient
        self.temperature_model.set_ambient_temperature(stressed_ambient)

        # Update timestamp
        self.environment.timestamp = datetime.now()

    def _update_temperature(self, dt: float):
        """
        Update greenhouse temperature

        Simplified model:
        dT/dt = (T_ambient - T) / tau + Q_heater - Q_fan

        Where:
        - tau: thermal time constant
        - Q_heater: heat input from heater
        - Q_fan: cooling from fan

        Educational Note:
        This is a first-order thermal model. Real greenhouses are
        more complex, but this captures the essential dynamics.
        """
        temp_config = self.config.get('temperature', {})

        # Thermal time constant (how fast temperature equilibrates)
        tau = temp_config.get('time_constant', 600.0)

        # Natural temperature change (towards ambient)
        ambient_temp = self.environment.ambient_temperature
        natural_change = (ambient_temp - self.environment.temperature) / tau

        # Heater contribution
        heater = self.actuators[ActuatorType.HEATER]
        heater_power = temp_config.get('heater_power', 0.05)
        heater_effect = heater_power * (heater.value / 100.0) if heater.enabled else 0.0

        # Fan cooling
        fan = self.actuators[ActuatorType.FAN]
        fan_efficiency = temp_config.get('fan_efficiency', 0.03)
        fan_effect = -fan_efficiency * (fan.value / 100.0) if fan.enabled else 0.0

        # Total temperature change rate
        dT_dt = natural_change + heater_effect + fan_effect

        # Update temperature
        self.environment.temperature += dT_dt * dt

    def _update_moisture(self, dt: float):
        """
        Update soil moisture

        Simplified model:
        dM/dt = -k_evap * M + Q_pump

        Where:
        - k_evap: evaporation rate constant
        - Q_pump: water input from pump
        """
        moisture_config = self.config.get('moisture', {})

        # Evaporation (depends on current moisture)
        evap_rate = moisture_config.get('evaporation_base_rate', 0.001)
        evaporation = -evap_rate * self.environment.moisture

        # Pump watering
        pump = self.actuators[ActuatorType.PUMP]
        pump_rate = moisture_config.get('pump_rate', 0.5)
        pump_effect = pump_rate if pump.enabled else 0.0

        # Total moisture change rate
        dM_dt = evaporation + pump_effect

        # Update moisture (constrain to 0-100%)
        self.environment.moisture += dM_dt * dt
        self.environment.moisture = max(0.0, min(100.0, self.environment.moisture))

    def _update_humidity(self, dt: float):
        """
        Update relative humidity

        Simplified model:
        - Evaporation increases humidity
        - Ventilation decreases humidity
        """
        humidity_config = self.config.get('humidity', {})

        # Ventilation effect (fan removes humid air)
        fan = self.actuators[ActuatorType.FAN]
        vent_rate = humidity_config.get('ventilation_rate', 0.02)
        vent_effect = -vent_rate * (fan.value / 100.0) if fan.enabled else 0.0

        # Ambient humidity exchange
        ambient_humidity = humidity_config.get('ambient_humidity', 50.0)
        exchange_rate = humidity_config.get('ambient_exchange_rate', 0.001)
        ambient_effect = (ambient_humidity - self.environment.humidity) * exchange_rate

        # Total humidity change
        dH_dt = vent_effect + ambient_effect

        # Update humidity (constrain to 0-100%)
        self.environment.humidity += dH_dt * dt
        self.environment.humidity = max(0.0, min(100.0, self.environment.humidity))

    def _update_airflow(self, dt: float):
        """
        Update airflow measurement

        Airflow directly correlates with fan speed
        """
        airflow_config = self.config.get('airflow', {})

        fan = self.actuators[ActuatorType.FAN]
        max_airflow = airflow_config.get('fan_max_airflow', 10.0)

        # Target airflow based on fan speed
        target_airflow = max_airflow * (fan.value / 100.0) if fan.enabled else 0.0

        # Smooth transition to target (first-order lag)
        time_constant = airflow_config.get('airflow_time_constant', 30.0)
        self.environment.airflow += (target_airflow - self.environment.airflow) / time_constant * dt

    def _update_light(self, dt: float):
        """
        Update light level based on time of day

        Simulates day/night cycle
        """
        light_config = self.config.get('light', {})

        if not light_config.get('enabled', True):
            self.environment.light_level = 50.0  # Constant
            return

        # Calculate simulated time of day from sim_time
        # Assume 1 hour = 3600 seconds
        hour_of_day = (self.sim_time / 3600.0) % 24

        sunrise = light_config.get('sunrise', 6)
        sunset = light_config.get('sunset', 20)

        if sunrise <= hour_of_day <= sunset:
            # Daytime - simple sine curve
            day_fraction = (hour_of_day - sunrise) / (sunset - sunrise)
            self.environment.light_level = 100.0 * (1.0 - abs(2.0 * day_fraction - 1.0))
        else:
            # Nighttime
            self.environment.light_level = 0.0

    def set_actuator(self, actuator_type: ActuatorType, enabled: bool, value: float):
        """
        Update actuator state (called by control system)

        Args:
            actuator_type: Type of actuator
            enabled: Whether actuator is on
            value: Actuator setting (meaning depends on type)
        """
        if actuator_type in self.actuators:
            self.actuators[actuator_type].enabled = enabled
            self.actuators[actuator_type].value = value
            self.actuators[actuator_type].timestamp = datetime.now()

            logger.debug(f"Actuator updated: {actuator_type.name} = {value}")

    def set_ambient_temperature(self, temp: float):
        """Set ambient (outside) temperature"""
        self.environment.ambient_temperature = temp
        logger.info(f"Ambient temperature set to {temp}°C")

    def get_state(self) -> EnvironmentState:
        """Get current environmental state"""
        return self.environment

    def get_actuators(self) -> Dict[ActuatorType, ActuatorState]:
        """Get current actuator states"""
        return self.actuators

    def get_failure_simulator(self) -> FailureModeSimulator:
        """Get failure mode simulator for injecting failures"""
        return self.failure_simulator

    def get_temperature_model(self) -> TemperatureModel:
        """Get temperature model for detailed analysis"""
        return self.temperature_model

    def get_moisture_model(self) -> MoistureModel:
        """Get moisture model for detailed analysis"""
        return self.moisture_model

    def get_airflow_model(self) -> AirflowModel:
        """Get airflow model for detailed analysis"""
        return self.airflow_model

    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics"""
        return {
            'running': self.running,
            'paused': self.paused,
            'sim_time': self.sim_time,
            'updates_per_second': self.updates_per_second,
            'temperature': self.environment.temperature,
            'moisture': self.environment.moisture,
            'humidity': self.environment.humidity
        }

    def reset(self):
        """Reset simulation to initial state"""
        self.sim_time = 0.0
        self.iteration_count = 0

        # Reset environment to initial conditions
        self.environment = EnvironmentState(
            temperature=22.0,
            moisture=50.0,
            humidity=60.0,
            airflow=0.0,
            light_level=0.0,
            ambient_temperature=20.0,
            is_simulated=True
        )

        # Reset all actuators
        for actuator in self.actuators.values():
            actuator.enabled = False
            actuator.value = 0.0

        logger.info("Simulation reset")

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


if __name__ == "__main__":
    # Example usage and testing
    print("=== Simulation Engine Demo ===\n")

    # Create and start simulation
    sim = SimulationEngine()
    sim.start()

    print("Simulation running...")
    print("Testing heater and fan effects\n")

    # Run for 5 seconds with heater on
    print("Turning heater ON for 5 seconds...")
    sim.set_actuator(ActuatorType.HEATER, True, 100.0)
    time.sleep(5)

    # Check temperature
    state = sim.get_state()
    print(f"Temperature after heating: {state.temperature:.2f}°C\n")

    # Turn heater off, fan on
    print("Turning heater OFF, fan ON for 5 seconds...")
    sim.set_actuator(ActuatorType.HEATER, False, 0.0)
    sim.set_actuator(ActuatorType.FAN, True, 100.0)
    time.sleep(5)

    # Check temperature
    state = sim.get_state()
    print(f"Temperature after cooling: {state.temperature:.2f}°C\n")

    # Test pump
    print("Turning pump ON for 3 seconds...")
    sim.set_actuator(ActuatorType.PUMP, True, 100.0)
    time.sleep(3)
    sim.set_actuator(ActuatorType.PUMP, False, 0.0)

    # Check moisture
    state = sim.get_state()
    print(f"Moisture after watering: {state.moisture:.1f}%\n")

    # Print statistics
    stats = sim.get_statistics()
    print("Simulation Statistics:")
    print(f"  Sim time: {stats['sim_time']:.1f}s")
    print(f"  Update rate: {stats['updates_per_second']:.1f} Hz")
    print(f"  Temperature: {stats['temperature']:.2f}°C")
    print(f"  Moisture: {stats['moisture']:.1f}%")

    # Stop simulation
    sim.stop()
    print("\nDemo complete!")
