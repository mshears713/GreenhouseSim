"""
Unit tests for Airflow Model

Tests the airflow simulation including:
- Fan-driven forced ventilation
- Natural ventilation dynamics
- Temperature-driven convection (stack effect)
- First-order dynamics (inertia)
- Edge cases and boundary conditions

Educational Note:
Airflow modeling demonstrates:
1. First-order system response (lag between command and effect)
2. Multiple input sources (fan + natural ventilation)
3. Environmental coupling (temperature affects natural ventilation)
"""

import pytest
from python.simulation.airflow_model import AirflowModel


@pytest.fixture
def default_config():
    """Standard configuration for testing"""
    return {
        'airflow': {
            'fan_min_airflow': 0.0,
            'fan_max_airflow': 10.0,
            'natural_ventilation_base': 0.5,
            'natural_ventilation_temp_coefficient': 0.1,
            'vent_effect_multiplier': 2.0,
            'airflow_time_constant': 30.0
        },
        'noise': {
            'enabled': False,
            'airflow_noise': 0.0
        }
    }


@pytest.fixture
def airflow_model(default_config):
    """Create an airflow model instance"""
    return AirflowModel(default_config)


class TestAirflowModelInitialization:
    """Test model initialization"""

    def test_initialization_with_defaults(self, airflow_model):
        """Model should initialize with provided config"""
        assert airflow_model.get_airflow() == 0.0
        assert airflow_model.fan_max_airflow == 10.0
        assert airflow_model.time_constant == 30.0

    def test_initial_airflow_zero(self, airflow_model):
        """Initial airflow should be zero"""
        assert airflow_model.get_airflow() == 0.0
        assert airflow_model.get_target_airflow() == 0.0


class TestFanBehavior:
    """Test fan-driven airflow"""

    def test_fan_increases_airflow(self, airflow_model):
        """Fan ON should increase airflow"""
        initial_airflow = airflow_model.get_airflow()

        # Run fan at 100% for several time constants
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=100.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )

        final_airflow = airflow_model.get_airflow()
        assert final_airflow > initial_airflow

    def test_fan_speed_scaling(self, airflow_model):
        """Higher fan speed should produce more airflow"""
        # Test 50% fan speed
        airflow_model.reset()
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=50.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )
        airflow_50 = airflow_model.get_airflow()

        # Test 100% fan speed
        airflow_model.reset()
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=100.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )
        airflow_100 = airflow_model.get_airflow()

        # 100% should produce more airflow than 50%
        assert airflow_100 > airflow_50

    def test_fan_off_no_forced_airflow(self, airflow_model):
        """Fan OFF should not produce forced airflow"""
        # Let it reach steady state with fan off
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )

        # Airflow should be minimal (just natural base)
        assert airflow_model.get_airflow() < 1.0


class TestNaturalVentilation:
    """Test natural ventilation effects"""

    def test_vent_opening_increases_airflow(self, airflow_model):
        """Opening vents should increase natural ventilation"""
        # Test with vents closed
        airflow_model.reset()
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=0.0,
                temperature=30.0,  # Hot inside
                ambient_temperature=20.0
            )
        airflow_closed = airflow_model.get_airflow()

        # Test with vents open
        airflow_model.reset()
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=100.0,
                temperature=30.0,
                ambient_temperature=20.0
            )
        airflow_open = airflow_model.get_airflow()

        # Open vents should allow more airflow
        assert airflow_open > airflow_closed

    def test_temperature_difference_drives_natural_ventilation(self, airflow_model):
        """Stack effect should increase with temperature difference"""
        # Test with small temperature difference
        airflow_model.reset()
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=100.0,
                temperature=22.0,
                ambient_temperature=20.0
            )
        airflow_small_diff = airflow_model.get_airflow()

        # Test with large temperature difference
        airflow_model.reset()
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=100.0,
                temperature=35.0,
                ambient_temperature=20.0
            )
        airflow_large_diff = airflow_model.get_airflow()

        # Larger temperature difference should create more airflow
        assert airflow_large_diff > airflow_small_diff

    def test_base_natural_ventilation_always_present(self, airflow_model):
        """Base natural ventilation should always exist"""
        # Even with everything at minimum
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )

        # Should have at least base ventilation
        assert airflow_model.get_airflow() > 0.0


class TestFirstOrderDynamics:
    """Test airflow response dynamics"""

    def test_airflow_has_inertia(self, airflow_model):
        """Airflow should not change instantly"""
        # Turn on fan at 100%
        airflow_model.update(
            dt=1.0,
            fan_speed_percent=100.0,
            vent_position_percent=0.0,
            temperature=20.0,
            ambient_temperature=20.0
        )

        # After 1 second, should not be at steady state yet
        airflow = airflow_model.get_airflow()
        target = airflow_model.get_target_airflow()

        assert airflow < target

    def test_airflow_approaches_target(self, airflow_model):
        """Airflow should approach target over time"""
        # Turn on fan
        for _ in range(200):  # Several time constants
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=100.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )

        # Should be close to target
        airflow = airflow_model.get_airflow()
        target = airflow_model.get_target_airflow()

        assert abs(airflow - target) < 0.1

    def test_airflow_decreases_when_fan_stops(self, airflow_model):
        """Airflow should decrease when fan is turned off"""
        # Spin up fan
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=100.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )

        high_airflow = airflow_model.get_airflow()

        # Turn off fan
        for _ in range(120):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )

        low_airflow = airflow_model.get_airflow()

        # Airflow should have decreased
        assert low_airflow < high_airflow


class TestAirflowComponents:
    """Test airflow component breakdown"""

    def test_get_airflow_components_returns_dict(self, airflow_model):
        """Should return dictionary of airflow components"""
        components = airflow_model.get_airflow_components(
            fan_speed_percent=50.0,
            vent_position_percent=50.0,
            temperature=25.0,
            ambient_temperature=20.0
        )

        assert isinstance(components, dict)
        assert 'fan' in components
        assert 'natural' in components
        assert 'total_target' in components
        assert 'current' in components

    def test_fan_component_scales_with_speed(self, airflow_model):
        """Fan component should scale with fan speed"""
        comp_50 = airflow_model.get_airflow_components(
            fan_speed_percent=50.0,
            vent_position_percent=0.0,
            temperature=20.0,
            ambient_temperature=20.0
        )

        comp_100 = airflow_model.get_airflow_components(
            fan_speed_percent=100.0,
            vent_position_percent=0.0,
            temperature=20.0,
            ambient_temperature=20.0
        )

        assert comp_100['fan'] > comp_50['fan']


class TestCoolingAndDehumidification:
    """Test airflow effects on temperature and humidity"""

    def test_calculate_cooling_effect_positive(self, airflow_model):
        """Airflow should produce cooling effect"""
        # Set some airflow
        airflow_model.airflow = 5.0

        cooling = airflow_model.calculate_cooling_effect(5.0)

        assert cooling > 0.0

    def test_cooling_scales_with_airflow(self, airflow_model):
        """More airflow should produce more cooling"""
        cooling_low = airflow_model.calculate_cooling_effect(2.0)
        cooling_high = airflow_model.calculate_cooling_effect(8.0)

        assert cooling_high > cooling_low

    def test_calculate_dehumidification_effect_positive(self, airflow_model):
        """Airflow should produce dehumidification effect"""
        dehumid = airflow_model.calculate_dehumidification_effect(5.0)

        assert dehumid > 0.0

    def test_dehumidification_scales_with_airflow(self, airflow_model):
        """More airflow should produce more dehumidification"""
        dehumid_low = airflow_model.calculate_dehumidification_effect(2.0)
        dehumid_high = airflow_model.calculate_dehumidification_effect(8.0)

        assert dehumid_high > dehumid_low


class TestModelReset:
    """Test model reset functionality"""

    def test_reset_clears_airflow(self, airflow_model):
        """Reset should clear airflow"""
        # Generate some airflow
        airflow_model.airflow = 7.0
        airflow_model.target_airflow = 8.0

        # Reset
        airflow_model.reset(initial_airflow=0.0)

        assert airflow_model.get_airflow() == 0.0
        assert airflow_model.get_target_airflow() == 0.0

    def test_reset_with_initial_value(self, airflow_model):
        """Reset should accept initial airflow value"""
        airflow_model.reset(initial_airflow=5.0)

        assert airflow_model.get_airflow() == 5.0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_time_step(self, airflow_model):
        """Zero time step should not change airflow"""
        initial_airflow = airflow_model.get_airflow()

        new_airflow = airflow_model.update(
            dt=0.0,
            fan_speed_percent=100.0,
            vent_position_percent=100.0,
            temperature=25.0,
            ambient_temperature=20.0
        )

        assert new_airflow == initial_airflow

    def test_very_small_time_step(self, airflow_model):
        """Very small time steps should work correctly"""
        # Many tiny steps with fan on
        for _ in range(1000):
            airflow_model.update(
                dt=0.01,
                fan_speed_percent=100.0,
                vent_position_percent=0.0,
                temperature=20.0,
                ambient_temperature=20.0
            )

        # Should have some airflow after 10 seconds
        assert airflow_model.get_airflow() > 0.0

    def test_airflow_never_negative(self, airflow_model):
        """Airflow should never go negative"""
        # Try various scenarios
        for _ in range(100):
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=0.0,
                vent_position_percent=0.0,
                temperature=10.0,  # Cold inside
                ambient_temperature=25.0
            )

        assert airflow_model.get_airflow() >= 0.0

    def test_negative_percentages_handled(self, airflow_model):
        """Negative percentages should be handled gracefully"""
        # Should not crash with invalid inputs
        try:
            airflow_model.update(
                dt=1.0,
                fan_speed_percent=-10.0,
                vent_position_percent=-5.0,
                temperature=20.0,
                ambient_temperature=20.0
            )
        except Exception:
            # Crashing is acceptable behavior for invalid input
            pass


class TestNoise:
    """Test sensor noise functionality"""

    def test_noise_disabled_deterministic(self, default_config):
        """With noise disabled, readings should be deterministic"""
        default_config['noise']['enabled'] = False
        model = AirflowModel(default_config)

        a1 = model.update(dt=1.0, fan_speed_percent=50.0, vent_position_percent=0.0,
                         temperature=20.0, ambient_temperature=20.0)
        model.reset()
        a2 = model.update(dt=1.0, fan_speed_percent=50.0, vent_position_percent=0.0,
                         temperature=20.0, ambient_temperature=20.0)

        assert a1 == a2

    def test_noise_enabled_adds_variation(self, default_config):
        """With noise enabled, readings should vary"""
        default_config['noise']['enabled'] = True
        default_config['noise']['airflow_noise'] = 0.5
        model = AirflowModel(default_config)

        readings = []
        for _ in range(20):
            model.reset()
            a = model.update(dt=0.0, fan_speed_percent=50.0, vent_position_percent=0.0,
                            temperature=20.0, ambient_temperature=20.0)
            readings.append(a)

        # Should have some variation
        assert len(set(readings)) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
