"""
Temperature Dynamics Simulation Model

This module implements a detailed physics-based model of greenhouse
temperature dynamics including:
- Heat transfer with ambient environment
- Heater energy input
- Fan-based cooling
- Solar radiation effects
- Thermal mass and inertia
- Convection and radiation

Educational Note:
Temperature modeling demonstrates first-order thermal dynamics and
heat transfer principles fundamental to control systems engineering.

Physical Model:
The greenhouse temperature is governed by energy balance:

dT/dt = (Q_in - Q_out) / (m * c)

Where:
- Q_in: Heat inputs (heater, solar radiation)
- Q_out: Heat losses (conduction, convection, fan cooling)
- m: Thermal mass
- c: Specific heat capacity
"""

import math
import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TemperatureModel:
    """
    Detailed greenhouse temperature simulation model

    Implements heat transfer dynamics with multiple heat sources
    and sinks, thermal mass effects, and time-varying disturbances.

    Educational Note:
    This model uses a "lumped parameter" approach - treating the
    entire greenhouse as a single temperature node. More advanced
    models would include spatial temperature gradients.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize temperature model

        Args:
            config: Configuration dictionary with physical parameters
        """
        # Load configuration
        temp_config = config.get('temperature', {})

        # Physical parameters
        self.time_constant = temp_config.get('time_constant', 600.0)  # seconds
        self.heater_power = temp_config.get('heater_power', 0.05)  # °C/s at full power
        self.fan_efficiency = temp_config.get('fan_efficiency', 0.03)  # °C/s at full speed
        self.thermal_mass = temp_config.get('thermal_mass', 1.0)  # Multiplier

        # Solar radiation parameters
        self.solar_enabled = temp_config.get('solar_enabled', True)
        self.solar_peak_hour = temp_config.get('solar_peak_hour', 14)
        self.solar_max_power = temp_config.get('solar_max_power', 0.02)  # °C/s
        self.solar_duration = temp_config.get('solar_duration', 6)  # hours

        # Convection parameters
        self.convection_threshold = temp_config.get('convection_threshold', 2.0)  # °C

        # State variables
        self.temperature = temp_config.get('initial_greenhouse_temp', 22.0)  # °C
        self.ambient_temperature = temp_config.get('ambient_temperature', 20.0)  # °C

        # Thermal inertia (smooths rapid changes)
        self.thermal_inertia_buffer = self.temperature

        # Noise parameters
        noise_config = config.get('noise', {})
        self.noise_enabled = noise_config.get('enabled', True)
        self.noise_stddev = noise_config.get('temperature_noise', 0.1)  # °C

        logger.info(f"Temperature model initialized: T={self.temperature}°C, "
                   f"tau={self.time_constant}s")

    def update(
        self,
        dt: float,
        heater_on: bool,
        heater_power_percent: float,
        fan_speed_percent: float,
        current_time_seconds: float
    ) -> float:
        """
        Update temperature for one time step

        Args:
            dt: Time step in seconds
            heater_on: Whether heater is active
            heater_power_percent: Heater power level (0-100%)
            fan_speed_percent: Fan speed (0-100%)
            current_time_seconds: Simulation time for solar calculation

        Returns:
            New temperature in °C

        Educational Note:
        This uses Euler integration: T_new = T_old + (dT/dt) * dt
        More accurate methods exist (Runge-Kutta), but Euler is
        simple and sufficient for our time steps.
        """

        # ========== HEAT SOURCES ==========

        # 1. Heater input
        heater_effect = 0.0
        if heater_on:
            heater_effect = self.heater_power * (heater_power_percent / 100.0)

        # 2. Solar radiation (time-dependent)
        solar_effect = self._calculate_solar_heating(current_time_seconds)

        # ========== HEAT SINKS ==========

        # 1. Natural heat loss to ambient (conduction through walls)
        # Follows Newton's law of cooling: dT/dt ∝ (T_ambient - T)
        temp_difference = self.ambient_temperature - self.temperature
        natural_cooling = temp_difference / self.time_constant

        # 2. Enhanced convection when temperature difference is large
        # (chimney effect - hot air rises and escapes)
        convection_effect = 0.0
        if abs(temp_difference) > self.convection_threshold:
            # Additional cooling proportional to excess temperature difference
            excess_diff = abs(temp_difference) - self.convection_threshold
            convection_effect = -0.001 * excess_diff if temp_difference < 0 else 0.001 * excess_diff

        # 3. Fan cooling (forced convection)
        fan_effect = 0.0
        if fan_speed_percent > 0:
            fan_effect = -self.fan_efficiency * (fan_speed_percent / 100.0)

        # ========== TOTAL HEAT RATE ==========

        total_heat_rate = (
            heater_effect +
            solar_effect +
            natural_cooling +
            convection_effect +
            fan_effect
        )

        # Apply thermal mass (slows temperature changes)
        total_heat_rate /= self.thermal_mass

        # ========== UPDATE TEMPERATURE ==========

        # Euler integration
        self.temperature += total_heat_rate * dt

        # Apply thermal inertia (exponential filter for smoothing)
        # This simulates the fact that thermal mass resists rapid changes
        alpha = 0.3  # Filter coefficient
        self.thermal_inertia_buffer = (
            alpha * self.temperature +
            (1.0 - alpha) * self.thermal_inertia_buffer
        )
        self.temperature = self.thermal_inertia_buffer

        # Add sensor noise
        if self.noise_enabled:
            noise = random.gauss(0.0, self.noise_stddev)
            measured_temp = self.temperature + noise
        else:
            measured_temp = self.temperature

        return measured_temp

    def _calculate_solar_heating(self, current_time_seconds: float) -> float:
        """
        Calculate solar radiation heating effect

        Args:
            current_time_seconds: Current simulation time

        Returns:
            Solar heating rate in °C/s

        Educational Note:
        Solar radiation varies throughout the day following roughly
        a sinusoidal pattern, peaking at solar noon. This is a
        major disturbance in greenhouse temperature control.
        """
        if not self.solar_enabled:
            return 0.0

        # Calculate hour of day from simulation time
        hour_of_day = (current_time_seconds / 3600.0) % 24.0

        # Solar radiation follows a bell curve during daylight hours
        # Peak at solar_peak_hour, significant for solar_duration hours

        # Calculate hours from solar peak
        hours_from_peak = hour_of_day - self.solar_peak_hour

        # Wrap around (handle day boundary)
        if hours_from_peak > 12:
            hours_from_peak -= 24
        elif hours_from_peak < -12:
            hours_from_peak += 24

        # Solar radiation is zero outside duration window
        half_duration = self.solar_duration / 2.0
        if abs(hours_from_peak) > half_duration:
            return 0.0

        # Gaussian-like curve for solar intensity
        # Peak at center, falls off to sides
        normalized_time = hours_from_peak / half_duration  # -1 to +1
        intensity = math.exp(-2.0 * normalized_time ** 2)  # Gaussian

        solar_heating = self.solar_max_power * intensity

        return solar_heating

    def set_ambient_temperature(self, temp: float):
        """Set ambient (outside) temperature"""
        self.ambient_temperature = temp
        logger.debug(f"Ambient temperature set to {temp}°C")

    def add_ambient_variation(self, variation: float):
        """
        Add random variation to ambient temperature

        Simulates weather changes, wind gusts, etc.

        Args:
            variation: Standard deviation of temperature change
        """
        delta = random.gauss(0.0, variation)
        self.ambient_temperature += delta
        self.ambient_temperature = max(-20.0, min(50.0, self.ambient_temperature))

    def get_temperature(self) -> float:
        """Get current greenhouse temperature"""
        return self.temperature

    def get_ambient_temperature(self) -> float:
        """Get current ambient temperature"""
        return self.ambient_temperature

    def reset(self, initial_temp: float = 22.0, ambient_temp: float = 20.0):
        """Reset model to initial conditions"""
        self.temperature = initial_temp
        self.ambient_temperature = ambient_temp
        self.thermal_inertia_buffer = initial_temp
        logger.info(f"Temperature model reset to {initial_temp}°C")

    def get_heat_balance(
        self,
        heater_on: bool,
        heater_power_percent: float,
        fan_speed_percent: float,
        current_time_seconds: float
    ) -> Dict[str, float]:
        """
        Get detailed heat balance (for analysis/visualization)

        Returns dictionary with contributions from each heat source/sink

        Educational Note:
        Analyzing the heat balance helps understand system behavior
        and diagnose control issues.
        """
        heater_effect = 0.0
        if heater_on:
            heater_effect = self.heater_power * (heater_power_percent / 100.0)

        solar_effect = self._calculate_solar_heating(current_time_seconds)

        temp_difference = self.ambient_temperature - self.temperature
        natural_cooling = temp_difference / self.time_constant

        fan_effect = 0.0
        if fan_speed_percent > 0:
            fan_effect = -self.fan_efficiency * (fan_speed_percent / 100.0)

        convection_effect = 0.0
        if abs(temp_difference) > self.convection_threshold:
            excess_diff = abs(temp_difference) - self.convection_threshold
            convection_effect = -0.001 * excess_diff if temp_difference < 0 else 0.001 * excess_diff

        total = heater_effect + solar_effect + natural_cooling + fan_effect + convection_effect

        return {
            'heater': heater_effect,
            'solar': solar_effect,
            'natural_cooling': natural_cooling,
            'fan': fan_effect,
            'convection': convection_effect,
            'total': total / self.thermal_mass
        }


if __name__ == "__main__":
    # Test the temperature model
    print("=== Temperature Model Test ===\n")

    config = {
        'temperature': {
            'time_constant': 600.0,
            'heater_power': 0.05,
            'fan_efficiency': 0.03,
            'thermal_mass': 1.0,
            'solar_enabled': True,
            'solar_peak_hour': 14,
            'solar_max_power': 0.02,
            'initial_greenhouse_temp': 22.0,
            'ambient_temperature': 20.0
        },
        'noise': {
            'enabled': True,
            'temperature_noise': 0.1
        }
    }

    model = TemperatureModel(config)

    print(f"Initial temperature: {model.get_temperature():.2f}°C")
    print(f"Ambient temperature: {model.get_ambient_temperature():.2f}°C\n")

    # Simulate heating
    print("Simulating heater ON for 60 seconds...")
    for i in range(60):
        temp = model.update(
            dt=1.0,
            heater_on=True,
            heater_power_percent=100.0,
            fan_speed_percent=0.0,
            current_time_seconds=i
        )
        if i % 10 == 0:
            print(f"  t={i}s: T={temp:.2f}°C")

    print(f"\nFinal temperature: {model.get_temperature():.2f}°C")

    # Test heat balance
    balance = model.get_heat_balance(True, 100.0, 0.0, 60.0)
    print("\nHeat balance:")
    for source, rate in balance.items():
        print(f"  {source}: {rate:+.4f} °C/s")

    print("\nTest complete!")
