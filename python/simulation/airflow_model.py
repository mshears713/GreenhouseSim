"""
Airflow Simulation Model

This module implements airflow dynamics in the greenhouse including:
- Fan-driven forced ventilation
- Natural ventilation through vents
- Temperature-driven convection (stack effect)
- Airflow's effects on temperature and humidity

Educational Note:
Airflow modeling demonstrates fluid dynamics principles and
shows how ventilation affects other environmental variables.

Physical Model:
Airflow is modeled as a first-order system responding to
fan speed and natural ventilation:

dA/dt = (A_target - A_current) / tau

Where:
- A_target: Target airflow based on fan speed and vents
- tau: Airflow time constant (inertia)
"""

import math
import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class AirflowModel:
    """
    Greenhouse airflow simulation model

    Implements forced and natural ventilation dynamics.

    Educational Note:
    Airflow is important because it:
    1. Removes heat (convective cooling)
    2. Reduces humidity (moisture removal)
    3. Improves air quality (CO2/O2 exchange)
    4. Affects evaporation rate
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize airflow model

        Args:
            config: Configuration dictionary with physical parameters
        """
        # Load configuration
        airflow_config = config.get('airflow', {})

        # Fan parameters
        self.fan_min_airflow = airflow_config.get('fan_min_airflow', 0.0)
        self.fan_max_airflow = airflow_config.get('fan_max_airflow', 10.0)

        # Natural ventilation parameters
        self.natural_vent_base = airflow_config.get('natural_ventilation_base', 0.5)
        self.natural_vent_temp_coeff = airflow_config.get('natural_ventilation_temp_coefficient', 0.1)
        self.vent_effect_multiplier = airflow_config.get('vent_effect_multiplier', 2.0)

        # Dynamics
        self.time_constant = airflow_config.get('airflow_time_constant', 30.0)  # seconds

        # State variables
        self.airflow = 0.0  # Current airflow (arbitrary units)
        self.target_airflow = 0.0  # Target based on fan and vents

        # Noise parameters
        noise_config = config.get('noise', {})
        self.noise_enabled = noise_config.get('enabled', True)
        self.noise_stddev = noise_config.get('airflow_noise', 0.2)

        logger.info(f"Airflow model initialized")

    def update(
        self,
        dt: float,
        fan_speed_percent: float,
        vent_position_percent: float,
        temperature: float,
        ambient_temperature: float
    ) -> float:
        """
        Update airflow for one time step

        Args:
            dt: Time step in seconds
            fan_speed_percent: Fan speed (0-100%)
            vent_position_percent: Vent opening (0-100%)
            temperature: Current greenhouse temperature (°C)
            ambient_temperature: Outside temperature (°C)

        Returns:
            New airflow level (arbitrary units)

        Educational Note:
        Airflow has inertia - it doesn't change instantly when fan
        speed changes. This models the time for air to accelerate
        and reach steady-state flow.
        """

        # ========== CALCULATE TARGET AIRFLOW ==========

        # 1. Fan-driven airflow (forced ventilation)
        fan_airflow = self._calculate_fan_airflow(fan_speed_percent)

        # 2. Natural ventilation (passive airflow through vents)
        natural_airflow = self._calculate_natural_ventilation(
            vent_position_percent,
            temperature,
            ambient_temperature
        )

        # Total target airflow (fan and natural ventilation add)
        self.target_airflow = fan_airflow + natural_airflow

        # ========== FIRST-ORDER DYNAMICS ==========

        # Airflow changes gradually towards target
        # dA/dt = (A_target - A_current) / tau
        dA_dt = (self.target_airflow - self.airflow) / self.time_constant

        # Update airflow
        self.airflow += dA_dt * dt

        # Ensure non-negative
        self.airflow = max(0.0, self.airflow)

        # Add sensor noise
        if self.noise_enabled:
            noise = random.gauss(0.0, self.noise_stddev)
            measured_airflow = self.airflow + noise
            measured_airflow = max(0.0, measured_airflow)
        else:
            measured_airflow = self.airflow

        return measured_airflow

    def _calculate_fan_airflow(self, fan_speed_percent: float) -> float:
        """
        Calculate airflow from fan

        Args:
            fan_speed_percent: Fan speed (0-100%)

        Returns:
            Fan-driven airflow

        Educational Note:
        Fan airflow is roughly proportional to fan speed for
        centrifugal fans. More accurate models would include
        fan curves (airflow vs. pressure).
        """
        # Linear relationship between fan speed and airflow
        fan_fraction = fan_speed_percent / 100.0

        airflow = self.fan_min_airflow + (
            fan_fraction * (self.fan_max_airflow - self.fan_min_airflow)
        )

        return airflow

    def _calculate_natural_ventilation(
        self,
        vent_position_percent: float,
        temperature: float,
        ambient_temperature: float
    ) -> float:
        """
        Calculate natural ventilation airflow

        Natural ventilation is driven by:
        1. Vent opening area
        2. Temperature difference (stack effect/buoyancy)

        Args:
            vent_position_percent: Vent opening (0-100%)
            temperature: Greenhouse temperature (°C)
            ambient_temperature: Outside temperature (°C)

        Returns:
            Natural ventilation airflow

        Educational Note:
        The "stack effect" (or chimney effect) occurs when warm air
        rises and escapes through vents, drawing in cooler air from
        below. This is free cooling but hard to control precisely.

        Airflow ∝ √(ΔT * h)

        Where ΔT is temperature difference and h is vent height.
        We simplify this to linear relationship for our model.
        """
        # Base natural ventilation (air leaks, etc.)
        base_airflow = self.natural_vent_base

        # Temperature-driven component (stack effect)
        # Warmer inside = more upward airflow
        temp_difference = temperature - ambient_temperature

        # Stack effect strength (proportional to temperature difference)
        stack_effect = self.natural_vent_temp_coeff * abs(temp_difference)

        # Only significant if greenhouse is warmer (hot air rises)
        if temp_difference > 0:
            temp_driven_airflow = stack_effect
        else:
            # Cooler inside = reduced natural ventilation
            temp_driven_airflow = stack_effect * 0.2

        # Vent position effect (controls how much air can flow)
        vent_fraction = vent_position_percent / 100.0

        # Total natural ventilation
        # Vent position acts as a multiplier on temp-driven flow
        natural_airflow = base_airflow + (temp_driven_airflow * vent_fraction * self.vent_effect_multiplier)

        return natural_airflow

    def get_airflow(self) -> float:
        """Get current airflow"""
        return self.airflow

    def get_target_airflow(self) -> float:
        """Get target airflow (steady-state)"""
        return self.target_airflow

    def reset(self, initial_airflow: float = 0.0):
        """Reset model to initial conditions"""
        self.airflow = initial_airflow
        self.target_airflow = initial_airflow
        logger.info(f"Airflow model reset")

    def get_airflow_components(
        self,
        fan_speed_percent: float,
        vent_position_percent: float,
        temperature: float,
        ambient_temperature: float
    ) -> Dict[str, float]:
        """
        Get detailed airflow breakdown (for analysis/visualization)

        Returns dictionary with contributions from each source

        Educational Note:
        Understanding airflow components helps optimize ventilation
        strategy (when to use fan vs. natural ventilation).
        """
        fan_airflow = self._calculate_fan_airflow(fan_speed_percent)

        natural_airflow = self._calculate_natural_ventilation(
            vent_position_percent,
            temperature,
            ambient_temperature
        )

        temp_diff = temperature - ambient_temperature

        return {
            'fan': fan_airflow,
            'natural': natural_airflow,
            'total_target': fan_airflow + natural_airflow,
            'current': self.airflow,
            'temperature_difference': temp_diff
        }

    def calculate_cooling_effect(self, airflow: float) -> float:
        """
        Calculate temperature reduction rate from airflow

        Args:
            airflow: Current airflow level

        Returns:
            Cooling rate in °C/s

        Educational Note:
        Ventilation cooling effectiveness depends on airflow rate
        and temperature difference. This is used by the temperature
        model to calculate fan cooling effect.
        """
        # Simplified model: cooling proportional to airflow
        # More accurate would consider temperature difference
        # and specific heat of air

        # Typical coefficient: ~0.003 °C/s per unit airflow
        cooling_rate = 0.003 * airflow

        return cooling_rate

    def calculate_dehumidification_effect(self, airflow: float) -> float:
        """
        Calculate humidity reduction rate from airflow

        Args:
            airflow: Current airflow level

        Returns:
            Dehumidification rate in %/s

        Educational Note:
        Ventilation removes humid air and replaces it with
        (typically drier) outside air. This is the primary
        means of humidity control in greenhouses.
        """
        # Simplified model: dehumidification proportional to airflow
        # Typical coefficient: ~0.002 %/s per unit airflow

        dehumidification_rate = 0.002 * airflow

        return dehumidification_rate


if __name__ == "__main__":
    # Test the airflow model
    print("=== Airflow Model Test ===\n")

    config = {
        'airflow': {
            'fan_min_airflow': 0.0,
            'fan_max_airflow': 10.0,
            'natural_ventilation_base': 0.5,
            'natural_ventilation_temp_coefficient': 0.1,
            'vent_effect_multiplier': 2.0,
            'airflow_time_constant': 30.0
        },
        'noise': {
            'enabled': True,
            'airflow_noise': 0.2
        }
    }

    model = AirflowModel(config)

    print(f"Initial airflow: {model.get_airflow():.2f}\n")

    # Test fan response
    print("Testing fan at 50% speed...")
    for i in range(60):
        airflow = model.update(
            dt=1.0,
            fan_speed_percent=50.0,
            vent_position_percent=50.0,
            temperature=25.0,
            ambient_temperature=20.0
        )
        if i % 15 == 0:
            print(f"  t={i}s: Airflow={airflow:.2f}, Target={model.get_target_airflow():.2f}")

    print(f"\nSteady-state airflow: {model.get_airflow():.2f}\n")

    # Test natural ventilation with temperature difference
    print("Testing natural ventilation (hot greenhouse, vents open)...")
    model.reset()

    for i in range(60):
        airflow = model.update(
            dt=1.0,
            fan_speed_percent=0.0,  # Fan off
            vent_position_percent=100.0,  # Vents fully open
            temperature=35.0,  # Very hot inside
            ambient_temperature=20.0
        )
        if i % 15 == 0:
            print(f"  t={i}s: Airflow={airflow:.2f}")

    # Get component breakdown
    components = model.get_airflow_components(
        fan_speed_percent=50.0,
        vent_position_percent=100.0,
        temperature=35.0,
        ambient_temperature=20.0
    )

    print("\nAirflow components:")
    for component, value in components.items():
        print(f"  {component}: {value:.2f}")

    # Test cooling effect
    cooling = model.calculate_cooling_effect(model.get_airflow())
    print(f"\nCooling effect: {cooling:.4f} °C/s")

    dehumid = model.calculate_dehumidification_effect(model.get_airflow())
    print(f"Dehumidification effect: {dehumid:.4f} %/s")

    print("\nTest complete!")
