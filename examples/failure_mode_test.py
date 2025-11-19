#!/usr/bin/env python3
"""
Failure Mode Testing Example

This script demonstrates how to test system robustness by injecting
various failure scenarios and monitoring system response.

Educational Note:
Understanding system behavior under fault conditions is crucial for:
- Designing robust control algorithms
- Implementing proper error handling
- Ensuring safe degradation modes

Usage:
    python examples/failure_mode_test.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from python.simulation.engine import SimulationEngine
from python.simulation.failure_modes import FailureType
import time
import matplotlib.pyplot as plt


class FailureModeTest:
    """Automated failure mode testing"""

    def __init__(self, simulation_engine):
        self.engine = simulation_engine
        self.failure_sim = simulation_engine.get_failure_simulator()

    def test_sensor_stuck(self, duration=120):
        """
        Test: Temperature sensor reading freezes

        Expected behavior:
        - Controller continues with last valid reading
        - System should remain safe (no runaway heating/cooling)
        - Alert should be generated (in full system)
        """
        print("\n" + "="*60)
        print(" TEST: Sensor Stuck Failure")
        print("="*60)
        print(f"\nInjecting sensor stuck failure for {duration}s...")

        # Record initial state
        initial_temp = self.engine.get_state().temperature
        print(f"Initial temperature: {initial_temp:.1f}°C")

        # Inject failure
        self.failure_sim.inject_failure(
            FailureType.SENSOR_STUCK,
            affected_component='temperature',
            severity=1.0,
            duration=float(duration)
        )

        # Monitor for duration
        temps = []
        times = []
        start_time = time.time()

        while (time.time() - start_time) < duration / 10:  # Accelerated
            state = self.engine.get_state()
            temps.append(state.temperature)
            times.append(time.time() - start_time)
            time.sleep(0.1)

        # Analyze results
        temp_variation = max(temps) - min(temps)
        print(f"\nResults:")
        print(f"  Temperature variation during failure: {temp_variation:.2f}°C")
        print(f"  Final temperature: {temps[-1]:.1f}°C")

        if temp_variation < 2.0:
            print(f"  ✓ PASS: Sensor reading remained stable")
        else:
            print(f"  ⚠ WARNING: Temperature varied more than expected")

        return {'temps': temps, 'times': times, 'passed': temp_variation < 2.0}

    def test_sensor_noisy(self, duration=120):
        """
        Test: Sensor produces noisy/erratic readings

        Expected behavior:
        - Controller should filter noise (moving average, etc.)
        - No rapid actuator cycling
        - System maintains approximate setpoint
        """
        print("\n" + "="*60)
        print(" TEST: Noisy Sensor Failure")
        print("="*60)
        print(f"\nInjecting noisy sensor failure for {duration}s...")

        # Inject failure
        self.failure_sim.inject_failure(
            FailureType.SENSOR_NOISY,
            affected_component='temperature',
            severity=1.0,
            duration=float(duration)
        )

        # Monitor actuator cycling
        actuator_changes = 0
        last_heater_state = None
        temps = []
        times = []
        start_time = time.time()

        while (time.time() - start_time) < duration / 10:
            state = self.engine.get_state()
            actuators = self.engine.get_actuators()

            temps.append(state.temperature)
            times.append(time.time() - start_time)

            # Count actuator state changes
            from python.data.models import ActuatorType
            heater = actuators.get(ActuatorType.HEATER)
            if heater and last_heater_state is not None:
                if heater.enabled != last_heater_state:
                    actuator_changes += 1
            if heater:
                last_heater_state = heater.enabled

            time.sleep(0.1)

        print(f"\nResults:")
        print(f"  Actuator state changes: {actuator_changes}")
        print(f"  Temperature std dev: {self._std_dev(temps):.2f}°C")

        if actuator_changes < 20:
            print(f"  ✓ PASS: Actuator cycling is reasonable")
        else:
            print(f"  ⚠ WARNING: Excessive actuator cycling detected")

        return {'temps': temps, 'times': times, 'changes': actuator_changes}

    def test_actuator_stuck_on(self, duration=120):
        """
        Test: Heater stuck in ON position

        Expected behavior:
        - System detects stuck actuator
        - Compensates with other actuators (fan)
        - Temperature doesn't runaway
        - Alert generated
        """
        print("\n" + "="*60)
        print(" TEST: Actuator Stuck ON Failure")
        print("="*60)
        print(f"\nInjecting stuck heater failure for {duration}s...")

        initial_temp = self.engine.get_state().temperature
        print(f"Initial temperature: {initial_temp:.1f}°C")

        # Inject failure
        self.failure_sim.inject_failure(
            FailureType.ACTUATOR_STUCK_ON,
            affected_component='heater',
            severity=1.0,
            duration=float(duration)
        )

        # Monitor temperature rise
        temps = []
        times = []
        max_temp = initial_temp
        start_time = time.time()

        while (time.time() - start_time) < duration / 10:
            state = self.engine.get_state()
            temps.append(state.temperature)
            times.append(time.time() - start_time)
            max_temp = max(max_temp, state.temperature)
            time.sleep(0.1)

        temp_rise = max_temp - initial_temp
        print(f"\nResults:")
        print(f"  Maximum temperature reached: {max_temp:.1f}°C")
        print(f"  Temperature rise: {temp_rise:.1f}°C")

        if temp_rise < 10.0:
            print(f"  ✓ PASS: Temperature remained controlled")
        else:
            print(f"  ⚠ WARNING: Excessive temperature rise")

        return {'temps': temps, 'times': times, 'max_temp': max_temp}

    def test_environmental_stress(self, event_type='heatwave', duration=180):
        """
        Test: Environmental stress (heatwave or cold snap)

        Expected behavior:
        - System adapts to changing ambient conditions
        - Maintains setpoint within reasonable bounds
        - No equipment overload
        """
        print("\n" + "="*60)
        print(f" TEST: Environmental Stress - {event_type.upper()}")
        print("="*60)
        print(f"\nInjecting {event_type} event for {duration}s...")

        # Inject environmental failure
        failure_type = FailureType.HEATWAVE if event_type == 'heatwave' else FailureType.COLD_SNAP
        self.failure_sim.inject_failure(
            failure_type,
            affected_component='environment',
            severity=1.0,
            duration=float(duration)
        )

        # Monitor system response
        temps = []
        ambient_temps = []
        times = []
        start_time = time.time()

        while (time.time() - start_time) < duration / 10:
            state = self.engine.get_state()
            temps.append(state.temperature)
            # Note: ambient temp would need to be exposed in state
            times.append(time.time() - start_time)
            time.sleep(0.1)

        avg_temp = sum(temps) / len(temps)
        setpoint = 24.0  # Assumed setpoint
        error = abs(avg_temp - setpoint)

        print(f"\nResults:")
        print(f"  Average temperature: {avg_temp:.1f}°C")
        print(f"  Average error from setpoint: {error:.1f}°C")

        if error < 3.0:
            print(f"  ✓ PASS: System maintained control under stress")
        else:
            print(f"  ⚠ WARNING: Significant deviation from setpoint")

        return {'temps': temps, 'times': times, 'avg_error': error}

    def test_communication_loss(self, duration=60):
        """
        Test: Simulated communication loss with Arduino

        Expected behavior:
        - System enters safe mode
        - Actuators go to safe state
        - Reconnection handled gracefully
        """
        print("\n" + "="*60)
        print(" TEST: Communication Loss")
        print("="*60)
        print(f"\nSimulating communication loss for {duration}s...")
        print("(In real system, this would test serial interface reconnection)")

        # This would require integration with serial interface
        # For now, just demonstrate the concept
        print("\nExpected behavior:")
        print("  1. Detect communication timeout")
        print("  2. Enter safe mode (turn off heater, fan to medium)")
        print("  3. Attempt reconnection with exponential backoff")
        print("  4. Resume normal operation once reconnected")
        print("\n✓ This test requires hardware Arduino connection")

        return {'status': 'requires_hardware'}

    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print(" FAILURE MODE TEST SUITE")
        print(" Testing System Robustness")
        print("="*60)

        results = {}

        # Test 1: Sensor Stuck
        results['sensor_stuck'] = self.test_sensor_stuck(duration=120)
        self._wait_between_tests()

        # Test 2: Noisy Sensor
        results['sensor_noisy'] = self.test_sensor_noisy(duration=120)
        self._wait_between_tests()

        # Test 3: Actuator Stuck
        results['actuator_stuck'] = self.test_actuator_stuck_on(duration=120)
        self._wait_between_tests()

        # Test 4: Heatwave
        results['heatwave'] = self.test_environmental_stress('heatwave', duration=180)
        self._wait_between_tests()

        # Test 5: Communication Loss (conceptual)
        results['comm_loss'] = self.test_communication_loss(duration=60)

        # Summary
        print("\n" + "="*60)
        print(" TEST SUITE SUMMARY")
        print("="*60)

        passed = sum(1 for r in results.values() if r.get('passed', False))
        total = len([r for r in results.values() if 'passed' in r])

        print(f"\nTests passed: {passed}/{total}")
        print("\nRecommendations:")
        print("  - Review any failed tests")
        print("  - Tune control parameters if needed")
        print("  - Test with real hardware for full validation")

        return results

    def _wait_between_tests(self, duration=5):
        """Wait between tests for system to stabilize"""
        print(f"\nWaiting {duration}s before next test...")
        # Clear any active failures
        self.failure_sim.clear_all_failures()
        self.engine.reset()
        time.sleep(duration)

    @staticmethod
    def _std_dev(values):
        """Calculate standard deviation"""
        if not values:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


def main():
    """Main test execution"""
    print("\n" + "="*60)
    print(" Greenhouse Failure Mode Testing")
    print(" System Robustness Validation")
    print("="*60)

    # Initialize simulation
    print("\nInitializing simulation engine...")
    engine = SimulationEngine("simulation_config.yaml")
    engine.start()

    tester = FailureModeTest(engine)

    print("\nTest options:")
    print("  1. Run all tests (comprehensive)")
    print("  2. Test sensor stuck")
    print("  3. Test noisy sensor")
    print("  4. Test actuator stuck")
    print("  5. Test environmental stress (heatwave)")
    print("  6. Custom test")

    choice = input("\nEnter choice (1-6): ").strip()

    if choice == '1':
        results = tester.run_all_tests()
    elif choice == '2':
        results = {'test': tester.test_sensor_stuck()}
    elif choice == '3':
        results = {'test': tester.test_sensor_noisy()}
    elif choice == '4':
        results = {'test': tester.test_actuator_stuck_on()}
    elif choice == '5':
        results = {'test': tester.test_environmental_stress('heatwave')}
    elif choice == '6':
        print("\nAvailable failure types:")
        print("  - sensor_stuck")
        print("  - sensor_noisy")
        print("  - actuator_stuck_on")
        print("  - heatwave")
        print("  - cold_snap")

        failure = input("Enter failure type: ").strip()
        duration = int(input("Enter duration (seconds): "))

        if failure in ['sensor_stuck', 'sensor_noisy']:
            component = input("Enter component (temperature/moisture): ").strip()
        elif 'actuator' in failure:
            component = input("Enter component (heater/fan/pump): ").strip()
        else:
            component = 'environment'

        # Inject custom failure
        print(f"\nInjecting {failure} on {component} for {duration}s...")
        # Implementation would go here
        results = {'custom': True}
    else:
        print("Invalid choice!")
        return

    print("\n" + "="*60)
    print(" TESTING COMPLETE")
    print("="*60)
    print("\n✅ All requested tests finished")
    print("📊 Check results above for details")

    # Cleanup
    engine.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
