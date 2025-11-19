"""
Unit tests for Moisture Model

Tests the soil moisture simulation including:
- Evaporation dynamics
- Irrigation (pump) effects
- Drainage modeling
- Water absorption
- Environmental coupling (temperature, humidity, airflow)
- Edge cases and boundary conditions

Educational Note:
Moisture modeling is more complex than temperature because:
- It's strictly bounded (0-100%)
- It couples with multiple environmental variables
- Rates are highly nonlinear
"""

import pytest
from python.simulation.moisture_model import MoistureModel


@pytest.fixture
def default_config():
    """Standard configuration for testing"""
    return {
        'moisture': {
            'evaporation_base_rate': 0.001,
            'evaporation_temp_coefficient': 0.05,
            'evaporation_airflow_coefficient': 0.02,
            'pump_rate': 0.5,
            'drainage_rate': 0.0005,
            'drainage_threshold': 80.0,
            'max_capacity': 100.0,
            'min_level': 10.0,
            'absorption_time_constant': 60.0,
            'initial': 50.0
        },
        'noise': {
            'enabled': False,
            'moisture_noise': 0.0
        }
    }


@pytest.fixture
def moisture_model(default_config):
    """Create a moisture model instance"""
    return MoistureModel(default_config)


class TestMoistureModelInitialization:
    """Test model initialization"""

    def test_initialization_with_defaults(self, moisture_model):
        """Model should initialize with provided config"""
        assert moisture_model.get_moisture() == 50.0
        assert moisture_model.pump_rate == 0.5
        assert moisture_model.evaporation_base_rate == 0.001

    def test_initialization_with_custom_moisture(self, default_config):
        """Model should accept custom initial moisture"""
        default_config['moisture']['initial'] = 75.0
        model = MoistureModel(default_config)
        assert model.get_moisture() == 75.0


class TestPumpBehavior:
    """Test irrigation pump effects"""

    def test_pump_increases_moisture(self, moisture_model):
        """Pump ON should increase moisture"""
        initial_moisture = moisture_model.get_moisture()

        # Run pump for several seconds
        for _ in range(100):
            moisture_model.update(
                dt=1.0,
                pump_on=True,
                temperature=20.0,
                humidity=50.0,
                airflow=0.0
            )

        final_moisture = moisture_model.get_moisture()
        assert final_moisture > initial_moisture

    def test_pump_off_no_watering(self, moisture_model):
        """Pump OFF should not add water"""
        initial_moisture = moisture_model.get_moisture()

        # Update without pump (but no evaporation either - neutral conditions)
        moisture_model.update(
            dt=1.0,
            pump_on=False,
            temperature=20.0,
            humidity=100.0,  # High humidity = minimal evaporation
            airflow=0.0
        )

        # Should not increase (may decrease slightly due to evaporation)
        assert moisture_model.get_moisture() <= initial_moisture

    def test_water_buffer_accumulation(self, moisture_model):
        """Water should accumulate in buffer before absorbing"""
        # Pump adds to buffer immediately
        moisture_model.update(
            dt=1.0,
            pump_on=True,
            temperature=20.0,
            humidity=50.0,
            airflow=0.0
        )

        # Buffer should have some water
        assert moisture_model.get_water_buffer() > 0.0

    def test_water_absorption_from_buffer(self, moisture_model):
        """Water should gradually absorb from buffer into soil"""
        # Fill buffer
        moisture_model.water_buffer = 10.0
        initial_buffer = moisture_model.get_water_buffer()
        initial_moisture = moisture_model.get_moisture()

        # Let it absorb (no pump)
        for _ in range(60):
            moisture_model.update(
                dt=1.0,
                pump_on=False,
                temperature=20.0,
                humidity=100.0,  # Prevent evaporation
                airflow=0.0
            )

        # Buffer should decrease
        assert moisture_model.get_water_buffer() < initial_buffer
        # Moisture should increase
        assert moisture_model.get_moisture() > initial_moisture


class TestEvaporation:
    """Test evaporation effects"""

    def test_evaporation_decreases_moisture(self, moisture_model):
        """Evaporation should reduce moisture"""
        initial_moisture = moisture_model.get_moisture()

        # High temperature, low humidity, high airflow = strong evaporation
        for _ in range(100):
            moisture_model.update(
                dt=1.0,
                pump_on=False,
                temperature=35.0,
                humidity=20.0,
                airflow=10.0
            )

        assert moisture_model.get_moisture() < initial_moisture

    def test_high_temperature_increases_evaporation(self, moisture_model):
        """Higher temperature should evaporate faster"""
        # Test at low temperature
        moisture_model.reset(initial_moisture=50.0)
        for _ in range(50):
            moisture_model.update(dt=1.0, pump_on=False, temperature=20.0,
                                 humidity=50.0, airflow=0.0)
        moisture_low_temp = moisture_model.get_moisture()

        # Test at high temperature
        moisture_model.reset(initial_moisture=50.0)
        for _ in range(50):
            moisture_model.update(dt=1.0, pump_on=False, temperature=30.0,
                                 humidity=50.0, airflow=0.0)
        moisture_high_temp = moisture_model.get_moisture()

        # High temperature should evaporate more
        assert moisture_high_temp < moisture_low_temp

    def test_high_humidity_reduces_evaporation(self, moisture_model):
        """Higher humidity should slow evaporation"""
        # Test at low humidity
        moisture_model.reset(initial_moisture=50.0)
        for _ in range(50):
            moisture_model.update(dt=1.0, pump_on=False, temperature=25.0,
                                 humidity=30.0, airflow=0.0)
        moisture_low_humidity = moisture_model.get_moisture()

        # Test at high humidity
        moisture_model.reset(initial_moisture=50.0)
        for _ in range(50):
            moisture_model.update(dt=1.0, pump_on=False, temperature=25.0,
                                 humidity=80.0, airflow=0.0)
        moisture_high_humidity = moisture_model.get_moisture()

        # High humidity should evaporate less
        assert moisture_high_humidity > moisture_low_humidity

    def test_airflow_increases_evaporation(self, moisture_model):
        """Higher airflow should increase evaporation"""
        # Test with no airflow
        moisture_model.reset(initial_moisture=50.0)
        for _ in range(50):
            moisture_model.update(dt=1.0, pump_on=False, temperature=25.0,
                                 humidity=50.0, airflow=0.0)
        moisture_no_airflow = moisture_model.get_moisture()

        # Test with high airflow
        moisture_model.reset(initial_moisture=50.0)
        for _ in range(50):
            moisture_model.update(dt=1.0, pump_on=False, temperature=25.0,
                                 humidity=50.0, airflow=10.0)
        moisture_high_airflow = moisture_model.get_moisture()

        # High airflow should evaporate more
        assert moisture_high_airflow < moisture_no_airflow


class TestDrainage:
    """Test drainage behavior"""

    def test_drainage_above_threshold(self, moisture_model):
        """Drainage should occur when moisture exceeds threshold"""
        # Saturate soil well above drainage threshold (80%)
        moisture_model.moisture = 95.0
        initial_moisture = moisture_model.get_moisture()

        # Update (no pump, prevent evaporation)
        for _ in range(100):
            moisture_model.update(
                dt=1.0,
                pump_on=False,
                temperature=20.0,
                humidity=100.0,
                airflow=0.0
            )

        # Should have drained
        assert moisture_model.get_moisture() < initial_moisture

    def test_no_drainage_below_threshold(self, moisture_model):
        """No drainage should occur below threshold"""
        # Set moisture below threshold
        moisture_model.moisture = 50.0

        # Check water balance
        balance = moisture_model.get_water_balance(
            pump_on=False,
            temperature=20.0,
            humidity=100.0,  # Prevent evaporation
            airflow=0.0
        )

        # Drainage should be zero or very small
        assert balance['drainage'] < 0.001


class TestBoundaryConditions:
    """Test moisture boundaries"""

    def test_moisture_cannot_exceed_max(self, moisture_model):
        """Moisture should be clamped at maximum capacity"""
        # Try to overfill
        for _ in range(500):
            moisture_model.update(
                dt=1.0,
                pump_on=True,
                temperature=10.0,  # Low temp = low evaporation
                humidity=100.0,
                airflow=0.0
            )

        # Should not exceed 100%
        assert moisture_model.get_moisture() <= 100.0

    def test_moisture_cannot_go_negative(self, moisture_model):
        """Moisture should not go below zero"""
        # Try to evaporate everything
        moisture_model.moisture = 5.0

        for _ in range(500):
            moisture_model.update(
                dt=1.0,
                pump_on=False,
                temperature=40.0,
                humidity=0.0,
                airflow=20.0
            )

        # Should not go negative
        assert moisture_model.get_moisture() >= 0.0

    def test_is_dry_detection(self, moisture_model):
        """Should correctly detect when soil is too dry"""
        moisture_model.moisture = 5.0  # Below min_level (10%)
        assert moisture_model.is_dry() is True

        moisture_model.moisture = 30.0  # Above min_level
        assert moisture_model.is_dry() is False

    def test_is_saturated_detection(self, moisture_model):
        """Should correctly detect when soil is saturated"""
        moisture_model.moisture = 100.0
        assert moisture_model.is_saturated() is True

        moisture_model.moisture = 80.0
        assert moisture_model.is_saturated() is False


class TestWaterBalance:
    """Test water balance calculations"""

    def test_water_balance_returns_dict(self, moisture_model):
        """Water balance should return dictionary of components"""
        balance = moisture_model.get_water_balance(
            pump_on=True,
            temperature=25.0,
            humidity=50.0,
            airflow=5.0
        )

        assert isinstance(balance, dict)
        assert 'pump_input' in balance
        assert 'absorption' in balance
        assert 'evaporation' in balance
        assert 'drainage' in balance
        assert 'total' in balance

    def test_pump_input_in_balance(self, moisture_model):
        """Pump input should appear in balance when ON"""
        balance = moisture_model.get_water_balance(
            pump_on=True,
            temperature=20.0,
            humidity=50.0,
            airflow=0.0
        )

        assert balance['pump_input'] > 0

    def test_evaporation_in_balance(self, moisture_model):
        """Evaporation should appear in balance"""
        balance = moisture_model.get_water_balance(
            pump_on=False,
            temperature=30.0,
            humidity=30.0,
            airflow=10.0
        )

        # Should have some evaporation
        assert balance['evaporation'] > 0


class TestModelReset:
    """Test model reset functionality"""

    def test_reset_to_default(self, moisture_model):
        """Reset should restore initial conditions"""
        # Modify state
        moisture_model.moisture = 90.0
        moisture_model.water_buffer = 10.0

        # Reset
        moisture_model.reset(initial_moisture=50.0)

        assert moisture_model.get_moisture() == 50.0
        assert moisture_model.get_water_buffer() == 0.0


class TestManualWaterAddition:
    """Test manual water addition"""

    def test_add_water_increases_buffer(self, moisture_model):
        """Adding water should increase buffer"""
        initial_buffer = moisture_model.get_water_buffer()

        moisture_model.add_water(5.0)

        assert moisture_model.get_water_buffer() == initial_buffer + 5.0


class TestEdgeCases:
    """Test edge cases"""

    def test_zero_time_step(self, moisture_model):
        """Zero time step should not change moisture"""
        initial_moisture = moisture_model.get_moisture()

        new_moisture = moisture_model.update(
            dt=0.0,
            pump_on=True,
            temperature=25.0,
            humidity=50.0,
            airflow=5.0
        )

        # Should be essentially unchanged
        assert abs(new_moisture - initial_moisture) < 0.001

    def test_very_small_time_step(self, moisture_model):
        """Very small time steps should work correctly"""
        moisture_model.reset(initial_moisture=50.0)

        # Many tiny steps
        for _ in range(1000):
            moisture_model.update(
                dt=0.001,
                pump_on=True,
                temperature=20.0,
                humidity=50.0,
                airflow=0.0
            )

        # Should have increased (1000 * 0.001s = 1s total with pump)
        assert moisture_model.get_moisture() >= 50.0


class TestNoise:
    """Test sensor noise functionality"""

    def test_noise_disabled_deterministic(self, default_config):
        """With noise disabled, readings should be deterministic"""
        default_config['noise']['enabled'] = False
        model = MoistureModel(default_config)

        m1 = model.update(dt=1.0, pump_on=False, temperature=20.0,
                         humidity=50.0, airflow=0.0)
        model.reset()
        m2 = model.update(dt=1.0, pump_on=False, temperature=20.0,
                         humidity=50.0, airflow=0.0)

        assert m1 == m2

    def test_noise_enabled_adds_variation(self, default_config):
        """With noise enabled, readings should vary"""
        default_config['noise']['enabled'] = True
        default_config['noise']['moisture_noise'] = 2.0
        model = MoistureModel(default_config)

        readings = []
        for _ in range(20):
            model.reset()
            m = model.update(dt=0.0, pump_on=False, temperature=20.0,
                            humidity=50.0, airflow=0.0)
            readings.append(m)

        # Should have some variation
        assert len(set(readings)) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
