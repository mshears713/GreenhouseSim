"""
Data Models for Smart Mini Greenhouse Control System

This module defines the core data structures used throughout the system:
- Sensor readings
- Actuator states
- Environmental state
- Control parameters
- System status

Educational Note:
Using dataclasses provides clean, type-safe data structures with
automatic initialization, repr, and comparison methods. This makes
code more maintainable and self-documenting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Dict, Any


class ControlMode(Enum):
    """
    Control strategy modes

    Each mode represents a progressively more sophisticated
    control strategy, building from simple manual control to
    advanced PID regulation.
    """
    MANUAL = auto()        # Manual actuator control via UI
    OPEN_LOOP = auto()     # Simple threshold-based control
    CLOSED_LOOP = auto()   # Feedback control with error correction
    FEEDFORWARD = auto()   # Anticipatory control based on predictions
    PID = auto()           # Full PID control with tuning


class SensorType(Enum):
    """Types of sensors in the system"""
    TEMPERATURE = auto()
    MOISTURE = auto()
    AIRFLOW = auto()
    HUMIDITY = auto()      # Calculated or measured
    LIGHT = auto()         # Optional


class ActuatorType(Enum):
    """Types of actuators in the system"""
    FAN = auto()
    HEATER = auto()
    PUMP = auto()
    VENT = auto()


@dataclass
class SensorReading:
    """
    Represents a single sensor reading with metadata

    Attributes:
        sensor_type: Type of sensor
        value: Measured value (units depend on sensor type)
        unit: Measurement unit (e.g., '°C', '%', 'units')
        timestamp: When the reading was taken
        raw_value: Raw ADC value before conversion (optional)
        valid: Whether the reading passed validation
        error_message: Description of any error (if invalid)

    Example:
        temp = SensorReading(
            sensor_type=SensorType.TEMPERATURE,
            value=24.5,
            unit='°C',
            timestamp=datetime.now()
        )
    """
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    raw_value: Optional[int] = None
    valid: bool = True
    error_message: Optional[str] = None

    def __str__(self) -> str:
        """Human-readable representation"""
        status = "✓" if self.valid else "✗"
        return f"[{status}] {self.sensor_type.name}: {self.value:.2f} {self.unit}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'sensor_type': self.sensor_type.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'raw_value': self.raw_value,
            'valid': self.valid,
            'error_message': self.error_message
        }


@dataclass
class ActuatorState:
    """
    Represents the current state of an actuator

    Attributes:
        actuator_type: Type of actuator
        enabled: Whether actuator is currently active
        value: Actuator setting (meaning depends on type)
               - Fan: PWM value 0-255 or speed %
               - Heater: ON=1, OFF=0, or power %
               - Pump: ON=1, OFF=0
               - Vent: Position 0-180 degrees or %
        unit: Value unit (e.g., '%', 'degrees', 'PWM')
        timestamp: When state was last updated
        runtime_seconds: How long actuator has been continuously running
        power_consumption: Current power draw in Watts (optional)

    Example:
        fan = ActuatorState(
            actuator_type=ActuatorType.FAN,
            enabled=True,
            value=75.0,
            unit='%'
        )
    """
    actuator_type: ActuatorType
    enabled: bool
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    runtime_seconds: float = 0.0
    power_consumption: Optional[float] = None

    def __str__(self) -> str:
        """Human-readable representation"""
        state = "ON" if self.enabled else "OFF"
        return f"{self.actuator_type.name}: {state} ({self.value:.1f} {self.unit})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'actuator_type': self.actuator_type.name,
            'enabled': self.enabled,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'runtime_seconds': self.runtime_seconds,
            'power_consumption': self.power_consumption
        }


@dataclass
class EnvironmentState:
    """
    Complete environmental state of the greenhouse

    This class encapsulates all environmental variables at a single
    point in time, both measured (from sensors) and simulated.

    Attributes:
        temperature: Current temperature in °C
        moisture: Soil moisture in %
        humidity: Relative humidity in %
        airflow: Airflow measurement (arbitrary units)
        light_level: Light intensity 0-100%
        ambient_temperature: Outside temperature in °C
        timestamp: When state was recorded
        is_simulated: True if from simulation, False if from real sensors

    Educational Note:
    Keeping all environmental variables in one structure makes it
    easy to snapshot the system state for logging, debugging, and
    visualization.
    """
    temperature: float = 20.0
    moisture: float = 50.0
    humidity: float = 50.0
    airflow: float = 0.0
    light_level: float = 0.0
    ambient_temperature: float = 20.0
    timestamp: datetime = field(default_factory=datetime.now)
    is_simulated: bool = False

    def __str__(self) -> str:
        """Human-readable representation"""
        source = "SIM" if self.is_simulated else "REAL"
        return (
            f"[{source}] Temp: {self.temperature:.1f}°C, "
            f"Moisture: {self.moisture:.1f}%, "
            f"Humidity: {self.humidity:.1f}%, "
            f"Airflow: {self.airflow:.2f}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'temperature': self.temperature,
            'moisture': self.moisture,
            'humidity': self.humidity,
            'airflow': self.airflow,
            'light_level': self.light_level,
            'ambient_temperature': self.ambient_temperature,
            'timestamp': self.timestamp.isoformat(),
            'is_simulated': self.is_simulated
        }

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate environmental readings are within plausible ranges

        Returns:
            (valid, error_message) tuple
        """
        if not (-50 <= self.temperature <= 80):
            return False, f"Temperature {self.temperature}°C out of range"

        if not (0 <= self.moisture <= 100):
            return False, f"Moisture {self.moisture}% out of range"

        if not (0 <= self.humidity <= 100):
            return False, f"Humidity {self.humidity}% out of range"

        if self.airflow < 0:
            return False, f"Airflow {self.airflow} cannot be negative"

        if not (0 <= self.light_level <= 100):
            return False, f"Light level {self.light_level}% out of range"

        return True, None


@dataclass
class ControlParameters:
    """
    Control system parameters and setpoints

    This class holds all tunable parameters for the control system,
    including setpoints and PID gains.

    Attributes:
        temperature_setpoint: Target temperature in °C
        moisture_setpoint: Target moisture in %

        # Temperature PID gains
        temp_kp: Proportional gain
        temp_ki: Integral gain
        temp_kd: Derivative gain

        # Moisture PID gains
        moisture_kp: Proportional gain
        moisture_ki: Integral gain
        moisture_kd: Derivative gain

        # Control limits
        fan_min: Minimum fan speed %
        fan_max: Maximum fan speed %
        heater_max_power: Maximum heater power %
        pump_pulse_duration: Pump activation duration in seconds

    Educational Note:
    Separating control parameters into their own class makes it
    easy to save/load configurations and tune the system.
    """
    # Setpoints
    temperature_setpoint: float = 24.0
    moisture_setpoint: float = 50.0

    # Temperature PID parameters
    temp_kp: float = 1.0
    temp_ki: float = 0.1
    temp_kd: float = 0.05

    # Moisture PID parameters
    moisture_kp: float = 0.8
    moisture_ki: float = 0.05
    moisture_kd: float = 0.02

    # Control limits
    fan_min: float = 0.0
    fan_max: float = 100.0
    heater_max_power: float = 100.0
    pump_pulse_duration: float = 1.0  # seconds

    # Deadband (prevent oscillation around setpoint)
    temp_deadband: float = 0.5  # ±0.5°C
    moisture_deadband: float = 2.0  # ±2%

    def __str__(self) -> str:
        """Human-readable representation"""
        return (
            f"Setpoints: Temp={self.temperature_setpoint}°C, "
            f"Moisture={self.moisture_setpoint}% | "
            f"Temp PID: Kp={self.temp_kp}, Ki={self.temp_ki}, Kd={self.temp_kd}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'temperature_setpoint': self.temperature_setpoint,
            'moisture_setpoint': self.moisture_setpoint,
            'temp_kp': self.temp_kp,
            'temp_ki': self.temp_ki,
            'temp_kd': self.temp_kd,
            'moisture_kp': self.moisture_kp,
            'moisture_ki': self.moisture_ki,
            'moisture_kd': self.moisture_kd,
            'fan_min': self.fan_min,
            'fan_max': self.fan_max,
            'heater_max_power': self.heater_max_power,
            'pump_pulse_duration': self.pump_pulse_duration,
            'temp_deadband': self.temp_deadband,
            'moisture_deadband': self.moisture_deadband
        }


@dataclass
class PIDState:
    """
    Internal state of a PID controller

    Tracks error history for integral and derivative calculations.

    Educational Note:
    PID controllers need to remember past errors (for integral term)
    and previous error (for derivative term). This class encapsulates
    that state.
    """
    integral: float = 0.0
    previous_error: float = 0.0
    last_update: Optional[datetime] = None

    def reset(self):
        """Reset PID state (useful when changing setpoints)"""
        self.integral = 0.0
        self.previous_error = 0.0
        self.last_update = None


@dataclass
class SystemStatus:
    """
    Overall system status and health

    Tracks system state, errors, and operational statistics.

    Attributes:
        enabled: Whether system is active
        control_mode: Current control strategy
        error_state: Whether system is in error condition
        error_messages: List of current error messages
        uptime_seconds: How long system has been running
        arduino_connected: Whether Arduino connection is active
        simulation_running: Whether simulation is active
        total_power_consumption: Current total power draw in Watts
    """
    enabled: bool = True
    control_mode: ControlMode = ControlMode.MANUAL
    error_state: bool = False
    error_messages: list[str] = field(default_factory=list)
    uptime_seconds: float = 0.0
    arduino_connected: bool = False
    simulation_running: bool = False
    total_power_consumption: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)

    def add_error(self, message: str):
        """Add an error message"""
        if message not in self.error_messages:
            self.error_messages.append(message)
            self.error_state = True

    def clear_errors(self):
        """Clear all errors"""
        self.error_messages.clear()
        self.error_state = False

    def __str__(self) -> str:
        """Human-readable representation"""
        status = "ENABLED" if self.enabled else "DISABLED"
        errors = f" | ERRORS: {len(self.error_messages)}" if self.error_state else ""
        return f"[{status}] Mode: {self.control_mode.name}{errors}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'enabled': self.enabled,
            'control_mode': self.control_mode.name,
            'error_state': self.error_state,
            'error_messages': self.error_messages.copy(),
            'uptime_seconds': self.uptime_seconds,
            'arduino_connected': self.arduino_connected,
            'simulation_running': self.simulation_running,
            'total_power_consumption': self.total_power_consumption,
            'last_update': self.last_update.isoformat()
        }


@dataclass
class GreenhouseSnapshot:
    """
    Complete snapshot of greenhouse state at a point in time

    Combines all system data into a single comprehensive snapshot
    useful for logging, visualization, and analysis.

    This is the primary data structure for time-series logging.
    """
    timestamp: datetime
    environment: EnvironmentState
    actuators: Dict[ActuatorType, ActuatorState]
    control_params: ControlParameters
    system_status: SystemStatus

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'environment': self.environment.to_dict(),
            'actuators': {
                name.name: state.to_dict()
                for name, state in self.actuators.items()
            },
            'control_params': self.control_params.to_dict(),
            'system_status': self.system_status.to_dict()
        }

    def to_csv_row(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary suitable for CSV export

        Returns a single-level dictionary with all values,
        useful for pandas DataFrame creation.
        """
        row = {
            'timestamp': self.timestamp.isoformat(),
            # Environment
            'temp': self.environment.temperature,
            'moisture': self.environment.moisture,
            'humidity': self.environment.humidity,
            'airflow': self.environment.airflow,
            'light': self.environment.light_level,
            'ambient_temp': self.environment.ambient_temperature,
            # System status
            'enabled': self.system_status.enabled,
            'mode': self.system_status.control_mode.name,
            'error': self.system_status.error_state,
            # Control parameters
            'temp_setpoint': self.control_params.temperature_setpoint,
            'moisture_setpoint': self.control_params.moisture_setpoint,
        }

        # Add actuator states
        for actuator_type, state in self.actuators.items():
            prefix = actuator_type.name.lower()
            row[f'{prefix}_enabled'] = state.enabled
            row[f'{prefix}_value'] = state.value
            row[f'{prefix}_runtime'] = state.runtime_seconds

        return row


if __name__ == "__main__":
    # Example usage and testing
    print("=== Data Models Demo ===\n")

    # Create sensor reading
    temp_reading = SensorReading(
        sensor_type=SensorType.TEMPERATURE,
        value=24.5,
        unit='°C',
        raw_value=512
    )
    print(f"Sensor Reading: {temp_reading}\n")

    # Create actuator state
    fan_state = ActuatorState(
        actuator_type=ActuatorType.FAN,
        enabled=True,
        value=75.0,
        unit='%',
        power_consumption=9.0
    )
    print(f"Actuator State: {fan_state}\n")

    # Create environment state
    env = EnvironmentState(
        temperature=24.5,
        moisture=52.0,
        humidity=60.0,
        airflow=5.2
    )
    print(f"Environment: {env}")
    valid, error = env.validate()
    print(f"Valid: {valid}\n")

    # Create control parameters
    params = ControlParameters(
        temperature_setpoint=24.0,
        moisture_setpoint=50.0,
        temp_kp=1.5,
        temp_ki=0.2,
        temp_kd=0.1
    )
    print(f"Control Params: {params}\n")

    # Create system status
    status = SystemStatus(
        enabled=True,
        control_mode=ControlMode.PID,
        arduino_connected=True,
        simulation_running=True
    )
    print(f"System Status: {status}\n")

    # Create complete snapshot
    snapshot = GreenhouseSnapshot(
        timestamp=datetime.now(),
        environment=env,
        actuators={ActuatorType.FAN: fan_state},
        control_params=params,
        system_status=status
    )
    print("Complete Snapshot:")
    print(f"CSV Row: {snapshot.to_csv_row()}")
