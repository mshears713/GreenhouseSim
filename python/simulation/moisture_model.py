"""
Soil Moisture Dynamics Simulation Model

This module implements a detailed physics-based model of soil moisture
dynamics including:
- Evaporation (temperature and humidity dependent)
- Water input from irrigation pump
- Drainage and percolation
- Plant water uptake (simplified)
- Soil water retention characteristics

Educational Note:
Soil moisture modeling demonstrates mass balance principles and
coupled dynamics (moisture affects humidity, which affects evaporation).

Physical Model:
Soil moisture is governed by water balance:

dM/dt = I - E - D - U

Where:
- I: Irrigation input (pump)
- E: Evaporation
- D: Drainage
- U: Plant uptake (simplified)
"""

import math
import random
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MoistureModel:
    """
    Detailed soil moisture simulation model

    Implements water balance dynamics with evaporation, irrigation,
    drainage, and environmental coupling.

    Educational Note:
    Soil moisture is more complex than temperature because:
    1. It's bounded (0-100%)
    2. Rates are nonlinear (evaporation depends on moisture level)
    3. It couples with other variables (temperature, humidity)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize moisture model

        Args:
            config: Configuration dictionary with physical parameters
        """
        # Load configuration
        moisture_config = config.get('moisture', {})

        # Physical parameters
        self.evaporation_base_rate = moisture_config.get('evaporation_base_rate', 0.001)  # %/s
        self.evaporation_temp_coeff = moisture_config.get('evaporation_temp_coefficient', 0.05)
        self.evaporation_airflow_coeff = moisture_config.get('evaporation_airflow_coefficient', 0.02)

        self.pump_rate = moisture_config.get('pump_rate', 0.5)  # %/s when ON
        self.drainage_rate = moisture_config.get('drainage_rate', 0.0005)  # %/s
        self.drainage_threshold = moisture_config.get('drainage_threshold', 80.0)  # %

        self.max_capacity = moisture_config.get('max_capacity', 100.0)  # %
        self.min_level = moisture_config.get('min_level', 10.0)  # %

        self.absorption_time_constant = moisture_config.get('absorption_time_constant', 60.0)  # s

        # State variables
        self.moisture = moisture_config.get('initial', 50.0)  # % (0-100)

        # Water absorption buffer (water takes time to penetrate soil)
        self.water_buffer = 0.0  # % pending absorption

        # Plant uptake (simplified constant rate)
        self.plant_uptake_rate = 0.0001  # %/s (very slow)

        # Noise parameters
        noise_config = config.get('noise', {})
        self.noise_enabled = noise_config.get('enabled', True)
        self.noise_stddev = noise_config.get('moisture_noise', 1.0)  # %

        logger.info(f"Moisture model initialized: M={self.moisture}%")

    def update(
        self,
        dt: float,
        pump_on: bool,
        temperature: float,
        humidity: float,
        airflow: float
    ) -> float:
        """
        Update soil moisture for one time step

        Args:
            dt: Time step in seconds
            pump_on: Whether irrigation pump is active
            temperature: Current temperature (°C) - affects evaporation
            humidity: Current humidity (%) - affects evaporation
            airflow: Current airflow (arbitrary units) - affects evaporation

        Returns:
            New moisture level in %

        Educational Note:
        Moisture dynamics are slower than temperature but more
        nonlinear. Small changes in conditions can have large
        effects on evaporation rate.
        """

        # ========== WATER INPUTS ==========

        # 1. Irrigation pump
        pump_input = 0.0
        if pump_on:
            # Water goes into buffer first (doesn't instantly absorb)
            self.water_buffer += self.pump_rate * dt

        # 2. Water absorption from buffer into soil
        # First-order absorption with time constant
        absorption_rate = self.water_buffer / self.absorption_time_constant
        absorbed_water = absorption_rate * dt
        self.water_buffer -= absorbed_water
        self.water_buffer = max(0.0, self.water_buffer)  # Can't go negative

        # ========== WATER OUTPUTS ==========

        # 1. Evaporation (depends on temperature, humidity, and current moisture)
        evaporation = self._calculate_evaporation(
            temperature, humidity, airflow, self.moisture
        )

        # 2. Drainage (only significant when soil is saturated)
        drainage = self._calculate_drainage(self.moisture)

        # 3. Plant water uptake (simplified constant rate)
        plant_uptake = self.plant_uptake_rate * self.moisture / 50.0  # Scales with moisture

        # ========== TOTAL WATER BALANCE ==========

        dM_dt = absorbed_water - evaporation - drainage - plant_uptake

        # Update moisture level
        self.moisture += dM_dt * dt

        # Constrain to physical limits
        self.moisture = max(0.0, min(self.max_capacity, self.moisture))

        # Add sensor noise
        if self.noise_enabled:
            noise = random.gauss(0.0, self.noise_stddev)
            measured_moisture = self.moisture + noise
            measured_moisture = max(0.0, min(100.0, measured_moisture))
        else:
            measured_moisture = self.moisture

        return measured_moisture

    def _calculate_evaporation(
        self,
        temperature: float,
        humidity: float,
        airflow: float,
        moisture_level: float
    ) -> float:
        """
        Calculate evaporation rate

        Args:
            temperature: Current temperature (°C)
            humidity: Current humidity (%)
            airflow: Current airflow
            moisture_level: Current soil moisture (%)

        Returns:
            Evaporation rate in %/s

        Educational Note:
        Evaporation is driven by:
        1. Temperature (higher = faster evaporation)
        2. Humidity deficit (dry air = faster evaporation)
        3. Airflow (wind = faster evaporation)
        4. Available moisture (wet soil = faster evaporation)

        This is a simplified Penman-Monteith-like model.
        """
        # Base evaporation rate
        base_evap = self.evaporation_base_rate

        # Temperature effect (increases exponentially with temperature)
        # Reference temperature: 20°C
        temp_factor = 1.0 + self.evaporation_temp_coeff * (temperature - 20.0)
        temp_factor = max(0.1, temp_factor)  # Can't be negative

        # Humidity effect (evaporation decreases as humidity approaches 100%)
        # Driving force is vapor pressure deficit
        humidity_factor = max(0.0, (100.0 - humidity) / 100.0)

        # Airflow effect (ventilation removes humid air, accelerating evaporation)
        airflow_factor = 1.0 + self.evaporation_airflow_coeff * airflow

        # Moisture availability (can't evaporate from dry soil)
        # Nonlinear relationship - evaporation drops off sharply below ~20% moisture
        if moisture_level > 20.0:
            moisture_factor = 1.0
        else:
            moisture_factor = moisture_level / 20.0

        # Total evaporation rate
        evaporation = (
            base_evap *
            temp_factor *
            humidity_factor *
            airflow_factor *
            moisture_factor
        )

        return evaporation

    def _calculate_drainage(self, moisture_level: float) -> float:
        """
        Calculate drainage rate

        Drainage only occurs when soil exceeds field capacity
        (drainage_threshold)

        Args:
            moisture_level: Current moisture (%)

        Returns:
            Drainage rate in %/s

        Educational Note:
        Soil has a "field capacity" - the amount of water it can
        retain against gravity. Excess water drains away.
        """
        if moisture_level > self.drainage_threshold:
            # Drainage proportional to excess moisture
            excess = moisture_level - self.drainage_threshold
            drainage = self.drainage_rate * excess
        else:
            drainage = 0.0

        return drainage

    def add_water(self, amount: float):
        """
        Manually add water (for testing or events)

        Args:
            amount: Water to add in %
        """
        self.water_buffer += amount
        logger.debug(f"Added {amount}% water to buffer")

    def get_moisture(self) -> float:
        """Get current soil moisture"""
        return self.moisture

    def get_water_buffer(self) -> float:
        """Get current water buffer (pending absorption)"""
        return self.water_buffer

    def is_dry(self) -> bool:
        """Check if soil is too dry (below minimum level)"""
        return self.moisture < self.min_level

    def is_saturated(self) -> bool:
        """Check if soil is saturated (at max capacity)"""
        return self.moisture >= self.max_capacity

    def reset(self, initial_moisture: float = 50.0):
        """Reset model to initial conditions"""
        self.moisture = initial_moisture
        self.water_buffer = 0.0
        logger.info(f"Moisture model reset to {initial_moisture}%")

    def get_water_balance(
        self,
        pump_on: bool,
        temperature: float,
        humidity: float,
        airflow: float
    ) -> Dict[str, float]:
        """
        Get detailed water balance (for analysis/visualization)

        Returns dictionary with contributions from each source/sink

        Educational Note:
        Water balance analysis helps understand where water is
        going and optimize irrigation strategies.
        """
        pump_rate = self.pump_rate if pump_on else 0.0

        absorption = self.water_buffer / self.absorption_time_constant

        evaporation = self._calculate_evaporation(
            temperature, humidity, airflow, self.moisture
        )

        drainage = self._calculate_drainage(self.moisture)

        plant_uptake = self.plant_uptake_rate * self.moisture / 50.0

        total = absorption - evaporation - drainage - plant_uptake

        return {
            'pump_input': pump_rate,
            'buffer': self.water_buffer,
            'absorption': absorption,
            'evaporation': evaporation,
            'drainage': drainage,
            'plant_uptake': plant_uptake,
            'total': total
        }


if __name__ == "__main__":
    # Test the moisture model
    print("=== Moisture Model Test ===\n")

    config = {
        'moisture': {
            'evaporation_base_rate': 0.001,
            'evaporation_temp_coefficient': 0.05,
            'evaporation_airflow_coefficient': 0.02,
            'pump_rate': 0.5,
            'drainage_rate': 0.0005,
            'drainage_threshold': 80.0,
            'initial': 50.0
        },
        'noise': {
            'enabled': True,
            'moisture_noise': 1.0
        }
    }

    model = MoistureModel(config)

    print(f"Initial moisture: {model.get_moisture():.1f}%\n")

    # Simulate watering
    print("Simulating pump ON for 5 seconds...")
    for i in range(5):
        moisture = model.update(
            dt=1.0,
            pump_on=True,
            temperature=25.0,
            humidity=60.0,
            airflow=0.0
        )
        print(f"  t={i+1}s: M={moisture:.1f}%, Buffer={model.get_water_buffer():.2f}%")

    print(f"\nWaiting 30 seconds for absorption...")
    for i in range(30):
        moisture = model.update(
            dt=1.0,
            pump_on=False,
            temperature=25.0,
            humidity=60.0,
            airflow=0.0
        )
        if i % 10 == 9:
            print(f"  t={i+1}s: M={moisture:.1f}%, Buffer={model.get_water_buffer():.2f}%")

    # Test evaporation
    print(f"\nSimulating evaporation (high temp, low humidity, high airflow)...")
    for i in range(60):
        moisture = model.update(
            dt=1.0,
            pump_on=False,
            temperature=30.0,
            humidity=30.0,
            airflow=10.0
        )
        if i % 20 == 19:
            print(f"  t={i+1}s: M={moisture:.1f}%")

    # Test water balance
    balance = model.get_water_balance(False, 30.0, 30.0, 10.0)
    print("\nWater balance:")
    for component, rate in balance.items():
        if component != 'buffer':
            print(f"  {component}: {rate:+.6f} %/s")
        else:
            print(f"  {component}: {rate:.2f} %")

    print("\nTest complete!")
