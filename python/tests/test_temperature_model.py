"""
Unit tests for Temperature Model

Tests the physics-based temperature simulation including:
- Heat transfer dynamics
- Heater and fan effects
- Solar radiation modeling
- Natural cooling
- Edge cases and boundary conditions

Educational Note:
Good tests verify both normal operation and edge cases.
For physical models, we check:
1. Direction of change is correct
2. Magnitude is reasonable
3. Steady-state behavior is correct
4. Boundary conditions are handled
"""

import pytest
import math
from python.simulation.temperature_model import TemperatureModel


@pytest.fixture
def default_config():
    """Standard configuration for testing"""
    return {
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
            'enabled': False,  # Disable noise for deterministic tests
            'temperature_noise': 0.0
        }
    }


@pytest.fixture
def temp_model(default_config):
    """Create a temperature model instance"""
    return TemperatureModel(default_config)


class TestTemperatureModelInitialization:
    """Test model initialization and configuration"""

    def test_initialization_with_default_config(self, temp_model):
        """Model should initialize with provided config"""
        assert temp_model.temperature == 22.0
        assert temp_model.ambient_temperature == 20.0
        assert temp_model.time_constant == 600.0

    def test_initialization_with_custom_temp(self, default_config):
        """Model should accept custom initial temperature"""
        default_config['temperature']['initial_greenhouse_temp'] = 25.0
        model = TemperatureModel(default_config)
        assert model.temperature == 25.0

    def test_ambient_temperature_setter(self, temp_model):
        """Should be able to set ambient temperature"""
        temp_model.set_ambient_temperature(15.0)
        assert temp_model.get_ambient_temperature() == 15.0


class TestHeaterBehavior:
    """Test heater heating effects"""

    def test_heater_increases_temperature(self, temp_model):
        """Heater ON should increase temperature"""
        initial_temp = temp_model.get_temperature()

        # Run heater for several seconds
        for _ in range(10):
            new_temp = temp_model.update(
                dt=1.0,
                heater_on=True,
                heater_power_percent=100.0,
                fan_speed_percent=0.0,
                current_time_seconds=0.0
            )

        assert new_temp > initial_temp

    def test_heater_off_no_heating(self, temp_model):
        """Heater OFF should not add heat (but temp may change due to ambient)"""
        # Set greenhouse and ambient to same temperature
        temp_model.temperature = 22.0
        temp_model.set_ambient_temperature(22.0)

        # Update with heater off
        new_temp = temp_model.update(
            dt=1.0,
            heater_on=False,
            heater_power_percent=0.0,
            fan_speed_percent=0.0,
            current_time_seconds=0.0
        )

        # Temperature should stay approximately the same (within numerical error)
        assert abs(new_temp - 22.0) < 0.1

    def test_heater_power_scaling(self, temp_model):
        """Higher heater power should heat faster"""
        temp_model.reset(initial_temp=20.0, ambient_temp=20.0)
        temp_model.update(dt=1.0, heater_on=True, heater_power_percent=50.0,
                         fan_speed_percent=0.0, current_time_seconds=0.0)
        temp_50 = temp_model.get_temperature()

        temp_model.reset(initial_temp=20.0, ambient_temp=20.0)
        temp_model.update(dt=1.0, heater_on=True, heater_power_percent=100.0,
                         fan_speed_percent=0.0, current_time_seconds=0.0)
        temp_100 = temp_model.get_temperature()

        # 100% power should heat more than 50% power
        assert temp_100 > temp_50


class TestFanCooling:
    """Test fan cooling effects"""

    def test_fan_decreases_temperature(self, temp_model):
        """Fan should cool greenhouse"""
        # Start with hot greenhouse
        temp_model.reset(initial_temp=30.0, ambient_temp=20.0)
        initial_temp = temp_model.get_temperature()

        # Run fan for several seconds
        for _ in range(10):
            new_temp = temp_model.update(
                dt=1.0,
                heater_on=False,
                heater_power_percent=0.0,
                fan_speed_percent=100.0,
                current_time_seconds=0.0
            )

        # Should have cooled down
        assert new_temp < initial_temp

    def test_fan_speed_scaling(self, temp_model):
        """Higher fan speed should cool faster"""
        # Test at 50% fan speed
        temp_model.reset(initial_temp=30.0, ambient_temp=20.0)
        temp_model.update(dt=1.0, heater_on=False, heater_power_percent=0.0,
                         fan_speed_percent=50.0, current_time_seconds=0.0)
        temp_50 = temp_model.get_temperature()

        # Test at 100% fan speed
        temp_model.reset(initial_temp=30.0, ambient_temp=20.0)
        temp_model.update(dt=1.0, heater_on=False, heater_power_percent=0.0,
                         fan_speed_percent=100.0, current_time_seconds=0.0)
        temp_100 = temp_model.get_temperature()

        # 100% fan should cool more than 50% fan
        assert temp_100 < temp_50


class TestNaturalCooling:
    """Test natural heat transfer to ambient"""

    def test_natural_cooling_to_ambient(self, temp_model):
        """Hot greenhouse should naturally cool toward ambient"""
        temp_model.reset(initial_temp=30.0, ambient_temp=20.0)

        # Let it cool naturally (no heater or fan)
        for _ in range(100):
            temp_model.update(
                dt=1.0,
                heater_on=False,
                heater_power_percent=0.0,
                fan_speed_percent=0.0,
                current_time_seconds=0.0
            )

        # Should have cooled toward ambient
        assert temp_model.get_temperature() < 30.0

    def test_natural_heating_from_cold(self, temp_model):
        """Cold greenhouse should warm toward higher ambient"""
        temp_model.reset(initial_temp=15.0, ambient_temp=25.0)

        # Let it warm naturally
        for _ in range(100):
            temp_model.update(
                dt=1.0,
                heater_on=False,
                heater_power_percent=0.0,
                fan_speed_percent=0.0,
                current_time_seconds=0.0
            )

        # Should have warmed toward ambient
        assert temp_model.get_temperature() > 15.0


class TestSolarRadiation:
    """Test solar radiation effects"""

    def test_solar_heating_at_peak(self, temp_model):
        """Solar radiation should heat greenhouse at peak hour"""
        temp_model.reset(initial_temp=22.0, ambient_temp=22.0)

        # Simulate at solar peak (14:00 = 14*3600 seconds)
        peak_time = 14 * 3600

        initial_temp = temp_model.get_temperature()

        for i in range(60):
            temp_model.update(
                dt=1.0,
                heater_on=False,
                heater_power_percent=0.0,
                fan_speed_percent=0.0,
                current_time_seconds=peak_time + i
            )

        # Should have warmed due to solar
        assert temp_model.get_temperature() > initial_temp

    def test_no_solar_at_night(self, temp_model):
        """No solar heating at night"""
        temp_model.reset(initial_temp=22.0, ambient_temp=22.0)

        # Simulate at midnight (0:00)
        night_time = 0

        initial_temp = temp_model.get_temperature()

        for i in range(60):
            temp_model.update(
                dt=1.0,
                heater_on=False,
                heater_power_percent=0.0,
                fan_speed_percent=0.0,
                current_time_seconds=night_time + i
            )

        # Should not have significant solar heating
        # (may drift slightly due to numerical effects)
        assert abs(temp_model.get_temperature() - initial_temp) < 0.5

    def test_solar_disabled(self, default_config):
        """Solar can be disabled via config"""
        default_config['temperature']['solar_enabled'] = False
        model = TemperatureModel(default_config)

        model.reset(initial_temp=22.0, ambient_temp=22.0)

        # At peak solar time
        for i in range(60):
            model.update(
                dt=1.0,
                heater_on=False,
                heater_power_percent=0.0,
                fan_speed_percent=0.0,
                current_time_seconds=14 * 3600 + i
            )

        # Should not warm significantly without solar
        assert abs(model.get_temperature() - 22.0) < 0.5


class TestHeatBalance:
    """Test heat balance calculations"""

    def test_heat_balance_returns_dict(self, temp_model):
        """Heat balance should return dictionary of components"""
        balance = temp_model.get_heat_balance(
            heater_on=True,
            heater_power_percent=100.0,
            fan_speed_percent=50.0,
            current_time_seconds=14 * 3600
        )

        assert isinstance(balance, dict)
        assert 'heater' in balance
        assert 'solar' in balance
        assert 'fan' in balance
        assert 'natural_cooling' in balance
        assert 'total' in balance

    def test_heater_contribution_positive(self, temp_model):
        """Heater should contribute positive heat"""
        balance = temp_model.get_heat_balance(
            heater_on=True,
            heater_power_percent=100.0,
            fan_speed_percent=0.0,
            current_time_seconds=0.0
        )

        assert balance['heater'] > 0

    def test_fan_contribution_negative(self, temp_model):
        """Fan should contribute negative heat (cooling)"""
        balance = temp_model.get_heat_balance(
            heater_on=False,
            heater_power_percent=0.0,
            fan_speed_percent=100.0,
            current_time_seconds=0.0
        )

        assert balance['fan'] < 0


class TestModelReset:
    """Test model reset functionality"""

    def test_reset_to_default(self, temp_model):
        """Reset should restore initial conditions"""
        # Modify temperature
        temp_model.temperature = 35.0
        temp_model.ambient_temperature = 10.0

        # Reset
        temp_model.reset(initial_temp=22.0, ambient_temp=20.0)

        assert temp_model.get_temperature() == 22.0
        assert temp_model.get_ambient_temperature() == 20.0


class TestAmbientVariation:
    """Test ambient temperature variation"""

    def test_add_ambient_variation(self, temp_model):
        """Should be able to add random variation to ambient"""
        initial_ambient = temp_model.get_ambient_temperature()

        # Add some variation (may or may not change in specific test due to randomness)
        # Just verify it doesn't crash
        temp_model.add_ambient_variation(1.0)

        # Ambient should still be within reasonable range
        assert -20.0 <= temp_model.get_ambient_temperature() <= 50.0

    def test_ambient_variation_bounded(self, temp_model):
        """Ambient variation should respect physical bounds"""
        # Try to push ambient very low
        temp_model.set_ambient_temperature(-15.0)
        for _ in range(100):
            temp_model.add_ambient_variation(10.0)

        # Should be bounded above -20°C
        assert temp_model.get_ambient_temperature() >= -20.0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_time_step(self, temp_model):
        """Zero time step should not change temperature"""
        initial_temp = temp_model.get_temperature()

        new_temp = temp_model.update(
            dt=0.0,
            heater_on=True,
            heater_power_percent=100.0,
            fan_speed_percent=0.0,
            current_time_seconds=0.0
        )

        assert new_temp == initial_temp

    def test_very_small_time_step(self, temp_model):
        """Very small time steps should work correctly"""
        # This tests numerical stability
        temp_model.reset(initial_temp=20.0, ambient_temp=20.0)

        for _ in range(1000):
            temp_model.update(
                dt=0.001,
                heater_on=True,
                heater_power_percent=100.0,
                fan_speed_percent=0.0,
                current_time_seconds=0.0
            )

        # Should have heated up (1000 * 0.001s = 1s total)
        assert temp_model.get_temperature() > 20.0

    def test_negative_percentages_handled(self, temp_model):
        """Negative percentages should be handled gracefully"""
        # Model should handle this without crashing
        # (behavior may vary - either clamp to 0 or treat as 0)
        initial_temp = temp_model.get_temperature()

        try:
            temp_model.update(
                dt=1.0,
                heater_on=True,
                heater_power_percent=-10.0,  # Invalid
                fan_speed_percent=-5.0,  # Invalid
                current_time_seconds=0.0
            )
            # If it doesn't crash, that's acceptable
        except Exception:
            # If it raises an exception, that's also acceptable
            pass


class TestNoise:
    """Test sensor noise functionality"""

    def test_noise_disabled_deterministic(self, default_config):
        """With noise disabled, readings should be deterministic"""
        default_config['noise']['enabled'] = False
        model = TemperatureModel(default_config)

        temp1 = model.update(dt=1.0, heater_on=False, heater_power_percent=0.0,
                            fan_speed_percent=0.0, current_time_seconds=0.0)

        model.reset()

        temp2 = model.update(dt=1.0, heater_on=False, heater_power_percent=0.0,
                            fan_speed_percent=0.0, current_time_seconds=0.0)

        assert temp1 == temp2

    def test_noise_enabled_adds_variation(self, default_config):
        """With noise enabled, readings should vary"""
        default_config['noise']['enabled'] = True
        default_config['noise']['temperature_noise'] = 0.5
        model = TemperatureModel(default_config)

        # Take multiple readings at same state
        readings = []
        for _ in range(20):
            model.reset()
            temp = model.update(dt=0.0, heater_on=False, heater_power_percent=0.0,
                               fan_speed_percent=0.0, current_time_seconds=0.0)
            readings.append(temp)

        # Readings should not all be identical (very unlikely with noise)
        assert len(set(readings)) > 1  # At least some variation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
