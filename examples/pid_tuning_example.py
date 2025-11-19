#!/usr/bin/env python3
"""
PID Tuning Example Script

This script demonstrates automated PID tuning using the Ziegler-Nichols method.
It runs test scenarios to help you find optimal PID parameters for your greenhouse.

Educational Note:
The Ziegler-Nichols method involves:
1. Setting Ki and Kd to 0
2. Increasing Kp until system oscillates
3. Measuring oscillation period
4. Calculating optimal PID parameters

Usage:
    python examples/pid_tuning_example.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from python.simulation.engine import SimulationEngine
from python.data.models import ActuatorType
import time
import matplotlib.pyplot as plt
import numpy as np


class PIDTuner:
    """Automated PID tuning using Ziegler-Nichols method"""

    def __init__(self, simulation_engine):
        self.engine = simulation_engine
        self.temperature_history = []
        self.time_history = []
        self.setpoint = 24.0  # Target temperature

    def test_p_only(self, kp_values):
        """
        Test proportional-only control with different Kp values

        Args:
            kp_values: List of Kp values to test

        Returns:
            dict: Results for each Kp value
        """
        results = {}

        for kp in kp_values:
            print(f"\n{'='*50}")
            print(f"Testing Kp = {kp:.2f} (Ki=0, Kd=0)")
            print(f"{'='*50}")

            # Reset simulation
            self.engine.reset()
            self.temperature_history = []
            self.time_history = []

            # Run for 600 seconds (10 minutes)
            duration = 600
            start_time = time.time()
            sim_time = 0

            while sim_time < duration:
                # Get current temperature
                state = self.engine.get_state()
                current_temp = state.temperature

                # P-only control
                error = self.setpoint - current_temp
                control_output = kp * error

                # Apply control (heater or fan)
                if control_output > 0:
                    # Need heating
                    self.engine.set_actuator(ActuatorType.HEATER, True, min(100, control_output * 10))
                    self.engine.set_actuator(ActuatorType.FAN, False, 0)
                else:
                    # Need cooling
                    self.engine.set_actuator(ActuatorType.HEATER, False, 0)
                    self.engine.set_actuator(ActuatorType.FAN, True, min(100, abs(control_output) * 10))

                # Record data
                self.temperature_history.append(current_temp)
                self.time_history.append(sim_time)

                # Wait for next update
                time.sleep(0.1)
                sim_time = (time.time() - start_time) * 10  # Accelerated time

                # Early exit if stable
                if sim_time > 300 and self._is_stable():
                    print(f"  System stabilized at {sim_time:.0f}s")
                    break

            # Analyze results
            analysis = self._analyze_response()
            results[kp] = {
                'temperature_history': self.temperature_history.copy(),
                'time_history': self.time_history.copy(),
                'analysis': analysis
            }

            print(f"  Overshoot: {analysis['overshoot']:.1f}%")
            print(f"  Settling time: {analysis['settling_time']:.0f}s")
            print(f"  Steady-state error: {analysis['steady_state_error']:.2f}°C")

        return results

    def find_ultimate_gain(self, kp_start=0.5, kp_increment=0.5, max_iterations=20):
        """
        Find the ultimate gain (Ku) where system oscillates continuously

        Args:
            kp_start: Starting Kp value
            kp_increment: How much to increase Kp each iteration
            max_iterations: Maximum number of tests

        Returns:
            dict: Ultimate gain and period
        """
        print("\n" + "="*60)
        print(" Finding Ultimate Gain (Ku) - Ziegler-Nichols Method")
        print("="*60)
        print("\nThis will test increasing Kp values until oscillation occurs...")

        kp = kp_start
        oscillation_detected = False
        ku = None
        tu = None

        for i in range(max_iterations):
            print(f"\nIteration {i+1}: Testing Kp = {kp:.2f}")

            # Reset simulation
            self.engine.reset()
            self.temperature_history = []
            self.time_history = []

            # Run test
            duration = 400
            start_time = time.time()
            sim_time = 0

            while sim_time < duration:
                state = self.engine.get_state()
                current_temp = state.temperature

                # P-only control
                error = self.setpoint - current_temp
                control_output = kp * error

                if control_output > 0:
                    self.engine.set_actuator(ActuatorType.HEATER, True, min(100, abs(control_output) * 10))
                    self.engine.set_actuator(ActuatorType.FAN, False, 0)
                else:
                    self.engine.set_actuator(ActuatorType.HEATER, False, 0)
                    self.engine.set_actuator(ActuatorType.FAN, True, min(100, abs(control_output) * 10))

                self.temperature_history.append(current_temp)
                self.time_history.append(sim_time)

                time.sleep(0.05)
                sim_time = (time.time() - start_time) * 10

            # Check for sustained oscillation
            if self._has_sustained_oscillation():
                oscillation_detected = True
                ku = kp
                tu = self._estimate_oscillation_period()
                print(f"  ✓ Sustained oscillation detected!")
                print(f"  Ultimate Gain (Ku) = {ku:.2f}")
                print(f"  Ultimate Period (Tu) = {tu:.1f}s")
                break
            else:
                print(f"  No sustained oscillation")

            kp += kp_increment

        if not oscillation_detected:
            print("\n⚠ Warning: Could not find ultimate gain in max iterations")
            print("  Try increasing kp_increment or max_iterations")
            return None

        return {'ku': ku, 'tu': tu}

    def calculate_ziegler_nichols_params(self, ku, tu):
        """
        Calculate PID parameters using Ziegler-Nichols tuning rules

        Args:
            ku: Ultimate gain
            tu: Ultimate period

        Returns:
            dict: Recommended Kp, Ki, Kd values
        """
        print("\n" + "="*60)
        print(" Ziegler-Nichols PID Parameter Calculation")
        print("="*60)

        # Classic Ziegler-Nichols rules
        kp = 0.6 * ku
        ki = 1.2 * ku / tu
        kd = 0.075 * ku * tu

        print(f"\nRecommended PID Parameters:")
        print(f"  Kp (Proportional) = {kp:.3f}")
        print(f"  Ki (Integral)     = {ki:.3f}")
        print(f"  Kd (Derivative)   = {kd:.3f}")

        print(f"\nAlternative tuning rules:")
        print(f"  P-only:  Kp = {0.5 * ku:.3f}")
        print(f"  PI:      Kp = {0.45 * ku:.3f}, Ki = {0.54 * ku / tu:.3f}")
        print(f"  PID:     Kp = {kp:.3f}, Ki = {ki:.3f}, Kd = {kd:.3f}")

        return {'kp': kp, 'ki': ki, 'kd': kd}

    def _is_stable(self, tolerance=0.5, window=50):
        """Check if temperature is stable within tolerance"""
        if len(self.temperature_history) < window:
            return False

        recent_temps = self.temperature_history[-window:]
        temp_range = max(recent_temps) - min(recent_temps)
        return temp_range < tolerance

    def _has_sustained_oscillation(self, min_cycles=3):
        """Check if system shows sustained oscillation"""
        if len(self.temperature_history) < 100:
            return False

        # Find zero crossings (crossing setpoint)
        temps = np.array(self.temperature_history)
        crossings = np.where(np.diff(np.sign(temps - self.setpoint)))[0]

        if len(crossings) < min_cycles * 2:
            return False

        # Check if oscillation is consistent
        periods = np.diff(crossings)
        if len(periods) > 2:
            period_variation = np.std(periods) / np.mean(periods)
            return period_variation < 0.3  # Less than 30% variation

        return False

    def _estimate_oscillation_period(self):
        """Estimate the period of oscillation"""
        temps = np.array(self.temperature_history)
        times = np.array(self.time_history)

        # Find peaks
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(temps)

        if len(peaks) < 2:
            return 0

        # Calculate average period between peaks
        peak_times = times[peaks]
        periods = np.diff(peak_times)
        return np.mean(periods)

    def _analyze_response(self):
        """Analyze system response metrics"""
        temps = np.array(self.temperature_history)

        # Overshoot
        max_temp = np.max(temps)
        overshoot = ((max_temp - self.setpoint) / self.setpoint) * 100

        # Settling time (within 2% of setpoint)
        tolerance = 0.02 * self.setpoint
        settled_indices = np.where(np.abs(temps - self.setpoint) < tolerance)[0]
        settling_time = self.time_history[settled_indices[0]] if len(settled_indices) > 0 else self.time_history[-1]

        # Steady-state error
        steady_state_error = abs(np.mean(temps[-20:]) - self.setpoint)

        return {
            'overshoot': overshoot,
            'settling_time': settling_time,
            'steady_state_error': steady_state_error
        }

    def plot_results(self, results, title="PID Tuning Results"):
        """Plot temperature responses for comparison"""
        plt.figure(figsize=(12, 8))

        for kp, data in results.items():
            plt.plot(data['time_history'], data['temperature_history'],
                    label=f'Kp={kp:.2f}', linewidth=2)

        plt.axhline(y=self.setpoint, color='r', linestyle='--',
                   label='Setpoint', linewidth=2)
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('Temperature (°C)', fontsize=12)
        plt.title(title, fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('pid_tuning_results.png', dpi=150)
        print(f"\n📊 Plot saved to: pid_tuning_results.png")
        plt.show()


def main():
    """Main tuning demonstration"""
    print("\n" + "="*60)
    print(" Greenhouse PID Tuning Assistant")
    print(" Automated Parameter Optimization")
    print("="*60)

    # Initialize simulation
    print("\nInitializing simulation engine...")
    engine = SimulationEngine("simulation_config.yaml")
    engine.start()

    tuner = PIDTuner(engine)

    print("\nChoose tuning method:")
    print("  1. Quick test with preset Kp values")
    print("  2. Ziegler-Nichols automatic tuning (recommended)")
    print("  3. Manual Kp sweep")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == '1':
        # Quick test
        print("\n Running quick test with preset Kp values...")
        kp_values = [0.5, 1.0, 1.5, 2.0]
        results = tuner.test_p_only(kp_values)
        tuner.plot_results(results, "P-Only Control Comparison")

    elif choice == '2':
        # Ziegler-Nichols
        print("\nStarting Ziegler-Nichols auto-tuning...")
        print("This will take a few minutes...\n")

        ultimate = tuner.find_ultimate_gain()
        if ultimate:
            params = tuner.calculate_ziegler_nichols_params(ultimate['ku'], ultimate['tu'])

            print("\n" + "="*60)
            print(" TUNING COMPLETE!")
            print("="*60)
            print("\nCopy these values to your greenhouse control system:")
            print(f"  Temperature PID:")
            print(f"    Kp = {params['kp']:.3f}")
            print(f"    Ki = {params['ki']:.3f}")
            print(f"    Kd = {params['kd']:.3f}")

    elif choice == '3':
        # Manual sweep
        kp_start = float(input("Enter starting Kp value: "))
        kp_end = float(input("Enter ending Kp value: "))
        kp_step = float(input("Enter step size: "))

        kp_values = np.arange(kp_start, kp_end + kp_step, kp_step)
        print(f"\nTesting {len(kp_values)} Kp values...")
        results = tuner.test_p_only(kp_values.tolist())
        tuner.plot_results(results, f"Kp Sweep: {kp_start} to {kp_end}")

    else:
        print("Invalid choice!")
        return

    print("\n✅ Tuning session complete!")
    print("="*60)

    # Cleanup
    engine.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Tuning interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
