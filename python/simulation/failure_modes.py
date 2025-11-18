"""
Failure Mode Simulation

This module simulates various failure scenarios for testing control
system robustness and error handling:

- Sensor failures (stuck, noisy, drift, dropout)
- Actuator failures (stuck on/off, degraded performance, intermittent)
- Environmental stress (heatwave, cold snap, humidity spike)
- Equipment failures (reservoir empty, power loss)

Educational Note:
Testing failure modes is essential for robust control systems.
Real systems must handle sensor errors, actuator faults, and
unexpected disturbances gracefully.

Safety-Critical Insight:
In production systems, failure mode analysis (FMEA) identifies
potential failures and their impacts, guiding design of safety
mechanisms and redundancy.
"""

import random
import time
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures that can be simulated"""
    # Sensor failures
    SENSOR_STUCK = auto()           # Sensor reading frozen
    SENSOR_NOISY = auto()           # Excessive noise
    SENSOR_DRIFT = auto()           # Slow bias accumulation
    SENSOR_DROPOUT = auto()         # Intermittent loss of signal
    SENSOR_OFFSET = auto()          # Fixed offset error

    # Actuator failures
    ACTUATOR_STUCK_ON = auto()      # Cannot turn off
    ACTUATOR_STUCK_OFF = auto()     # Cannot turn on
    ACTUATOR_DEGRADED = auto()      # Reduced effectiveness
    ACTUATOR_INTERMITTENT = auto()  # Random on/off
    ACTUATOR_SLOW = auto()          # Slow response

    # Environmental stress
    HEATWAVE = auto()               # Extreme high ambient temperature
    COLD_SNAP = auto()              # Extreme low ambient temperature
    HUMIDITY_SPIKE = auto()         # Very high ambient humidity
    DROUGHT = auto()                # Accelerated evaporation

    # Equipment failures
    RESERVOIR_EMPTY = auto()        # No water for pump
    POWER_LOSS = auto()             # Total power failure
    COMMUNICATION_LOSS = auto()     # Lost connection to controller


@dataclass
class FailureScenario:
    """
    Represents a single failure scenario

    Attributes:
        failure_type: Type of failure
        affected_component: Which sensor/actuator is affected
        severity: Failure severity (0-1)
        duration: How long failure lasts (seconds, None = indefinite)
        start_time: When failure started (None = not yet started)
        active: Whether failure is currently active
        parameters: Additional failure-specific parameters
    """
    failure_type: FailureType
    affected_component: str
    severity: float = 1.0
    duration: Optional[float] = None
    start_time: Optional[float] = None
    active: bool = False
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class FailureModeSimulator:
    """
    Simulates various failure modes for testing system robustness

    Educational Note:
    This simulator allows testing "what if" scenarios:
    - What if the temperature sensor fails?
    - What if the fan gets stuck on?
    - What if there's a heatwave?

    Understanding system behavior under failures guides
    design of fault-tolerant control strategies.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize failure mode simulator

        Args:
            config: Configuration dictionary
        """
        failure_config = config.get('failure_modes', {})

        self.enabled = failure_config.get('enabled', False)
        self.mtbf = failure_config.get('mtbf', 0)  # Mean time between failures (hours)

        # Active failure scenarios
        self.active_failures: Dict[str, FailureScenario] = {}

        # Failure history (for logging/analysis)
        self.failure_history = []

        # Random failure generation
        self.random_failures_enabled = (self.mtbf > 0)
        self.last_failure_time = 0.0

        # Callbacks for failure events
        self.on_failure_start: Optional[Callable[[FailureScenario], None]] = None
        self.on_failure_end: Optional[Callable[[FailureScenario], None]] = None

        logger.info(f"Failure mode simulator initialized (enabled={self.enabled})")

    def inject_failure(
        self,
        failure_type: FailureType,
        affected_component: str,
        severity: float = 1.0,
        duration: Optional[float] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Manually inject a failure scenario

        Args:
            failure_type: Type of failure to inject
            affected_component: Which component is affected
            severity: Failure severity (0-1)
            duration: How long failure lasts (seconds, None = indefinite)
            parameters: Additional failure-specific parameters

        Returns:
            Failure ID for later reference

        Example:
            # Inject stuck temperature sensor
            fms.inject_failure(
                FailureType.SENSOR_STUCK,
                'temperature',
                severity=1.0,
                duration=60.0
            )
        """
        failure_id = f"{failure_type.name}_{affected_component}_{time.time()}"

        scenario = FailureScenario(
            failure_type=failure_type,
            affected_component=affected_component,
            severity=severity,
            duration=duration,
            start_time=time.time(),
            active=True,
            parameters=parameters or {}
        )

        self.active_failures[failure_id] = scenario
        self.failure_history.append(scenario)

        logger.warning(f"Failure injected: {failure_type.name} on {affected_component}")

        if self.on_failure_start:
            self.on_failure_start(scenario)

        return failure_id

    def clear_failure(self, failure_id: str):
        """
        Clear a specific failure

        Args:
            failure_id: ID of failure to clear
        """
        if failure_id in self.active_failures:
            scenario = self.active_failures[failure_id]
            scenario.active = False

            logger.info(f"Failure cleared: {scenario.failure_type.name} on {scenario.affected_component}")

            if self.on_failure_end:
                self.on_failure_end(scenario)

            del self.active_failures[failure_id]

    def clear_all_failures(self):
        """Clear all active failures"""
        for failure_id in list(self.active_failures.keys()):
            self.clear_failure(failure_id)

        logger.info("All failures cleared")

    def update(self, current_time: float):
        """
        Update failure states (check durations, generate random failures)

        Args:
            current_time: Current simulation time (seconds)
        """
        # Check if any failures should expire
        expired_failures = []
        for failure_id, scenario in self.active_failures.items():
            if scenario.duration is not None and scenario.start_time is not None:
                elapsed = current_time - scenario.start_time
                if elapsed >= scenario.duration:
                    expired_failures.append(failure_id)

        # Clear expired failures
        for failure_id in expired_failures:
            self.clear_failure(failure_id)

        # Generate random failures (if enabled)
        if self.random_failures_enabled and self.enabled:
            self._generate_random_failure(current_time)

    def _generate_random_failure(self, current_time: float):
        """
        Randomly generate failures based on MTBF

        Educational Note:
        MTBF (Mean Time Between Failures) models reliability.
        Failures occur randomly with exponential distribution.
        """
        if current_time - self.last_failure_time < self.mtbf * 3600:
            return  # Not time yet

        # Random chance of failure
        # Probability = dt / MTBF
        if random.random() < 0.01:  # 1% chance per check
            # Choose random failure type and component
            failure_types = [
                FailureType.SENSOR_NOISY,
                FailureType.ACTUATOR_DEGRADED,
                FailureType.SENSOR_DRIFT
            ]

            components = ['temperature', 'moisture', 'fan', 'heater']

            failure_type = random.choice(failure_types)
            component = random.choice(components)

            # Random duration: 1-10 minutes
            duration = random.uniform(60, 600)

            self.inject_failure(failure_type, component, severity=0.5, duration=duration)
            self.last_failure_time = current_time

    def apply_sensor_failure(
        self,
        sensor_name: str,
        true_value: float
    ) -> float:
        """
        Apply active sensor failures to a reading

        Args:
            sensor_name: Name of sensor (e.g., 'temperature', 'moisture')
            true_value: True sensor value (before failure)

        Returns:
            Modified value with failure applied

        Educational Note:
        Sensor failures can cause control systems to make wrong
        decisions. Detecting and handling sensor faults is critical.
        """
        modified_value = true_value

        # Check for active sensor failures affecting this sensor
        for scenario in self.active_failures.values():
            if scenario.affected_component != sensor_name:
                continue

            if scenario.failure_type == FailureType.SENSOR_STUCK:
                # Return last "good" value (or initial value)
                if 'stuck_value' not in scenario.parameters:
                    scenario.parameters['stuck_value'] = true_value
                modified_value = scenario.parameters['stuck_value']

            elif scenario.failure_type == FailureType.SENSOR_NOISY:
                # Add excessive noise
                noise_level = scenario.severity * 5.0  # Much higher than normal
                noise = random.gauss(0.0, noise_level)
                modified_value += noise

            elif scenario.failure_type == FailureType.SENSOR_DRIFT:
                # Slow accumulating bias
                if 'drift_accumulator' not in scenario.parameters:
                    scenario.parameters['drift_accumulator'] = 0.0

                drift_rate = scenario.severity * 0.01  # 0.01 per second
                scenario.parameters['drift_accumulator'] += drift_rate
                modified_value += scenario.parameters['drift_accumulator']

            elif scenario.failure_type == FailureType.SENSOR_DROPOUT:
                # Intermittent signal loss
                if random.random() < scenario.severity * 0.3:  # 30% dropout rate
                    modified_value = float('nan')  # Signal lost

            elif scenario.failure_type == FailureType.SENSOR_OFFSET:
                # Fixed offset error
                offset = scenario.parameters.get('offset', scenario.severity * 5.0)
                modified_value += offset

        return modified_value

    def check_actuator_failure(
        self,
        actuator_name: str,
        commanded_state: bool,
        commanded_value: float
    ) -> tuple[bool, float]:
        """
        Check if actuator command should be modified by failure

        Args:
            actuator_name: Name of actuator (e.g., 'fan', 'heater', 'pump')
            commanded_state: Commanded on/off state
            commanded_value: Commanded value (e.g., fan speed %)

        Returns:
            (actual_state, actual_value) with failure applied

        Educational Note:
        Actuator failures prevent the control system from achieving
        desired actions. The controller "thinks" it's controlling
        normally, but the actuator doesn't respond correctly.
        """
        actual_state = commanded_state
        actual_value = commanded_value

        # Check for active actuator failures
        for scenario in self.active_failures.values():
            if scenario.affected_component != actuator_name:
                continue

            if scenario.failure_type == FailureType.ACTUATOR_STUCK_ON:
                # Cannot turn off
                actual_state = True
                actual_value = 100.0 * scenario.severity

            elif scenario.failure_type == FailureType.ACTUATOR_STUCK_OFF:
                # Cannot turn on
                actual_state = False
                actual_value = 0.0

            elif scenario.failure_type == FailureType.ACTUATOR_DEGRADED:
                # Reduced effectiveness
                actual_value = commanded_value * (1.0 - scenario.severity * 0.5)

            elif scenario.failure_type == FailureType.ACTUATOR_INTERMITTENT:
                # Random on/off
                if random.random() < scenario.severity * 0.3:
                    actual_state = not actual_state

            elif scenario.failure_type == FailureType.ACTUATOR_SLOW:
                # Slow response (would need state tracking)
                # Simplified: reduce commanded value
                actual_value = commanded_value * 0.5

        return actual_state, actual_value

    def get_environmental_stress(self, base_ambient_temp: float) -> float:
        """
        Apply environmental stress failures

        Args:
            base_ambient_temp: Normal ambient temperature

        Returns:
            Modified ambient temperature with stress applied

        Educational Note:
        Environmental disturbances test the control system's
        ability to reject external influences and maintain setpoint.
        """
        modified_temp = base_ambient_temp

        for scenario in self.active_failures.values():
            if scenario.failure_type == FailureType.HEATWAVE:
                # Increase ambient temperature
                temp_increase = scenario.severity * 15.0  # Up to +15°C
                modified_temp += temp_increase

            elif scenario.failure_type == FailureType.COLD_SNAP:
                # Decrease ambient temperature
                temp_decrease = scenario.severity * 15.0  # Down to -15°C
                modified_temp -= temp_decrease

        return modified_temp

    def is_reservoir_empty(self) -> bool:
        """Check if reservoir empty failure is active"""
        for scenario in self.active_failures.values():
            if scenario.failure_type == FailureType.RESERVOIR_EMPTY and scenario.active:
                return True
        return False

    def is_power_lost(self) -> bool:
        """Check if power loss failure is active"""
        for scenario in self.active_failures.values():
            if scenario.failure_type == FailureType.POWER_LOSS and scenario.active:
                return True
        return False

    def get_active_failures(self) -> Dict[str, FailureScenario]:
        """Get all currently active failures"""
        return self.active_failures.copy()

    def get_failure_summary(self) -> Dict[str, Any]:
        """Get summary of failure state"""
        return {
            'enabled': self.enabled,
            'active_count': len(self.active_failures),
            'active_failures': [
                {
                    'type': scenario.failure_type.name,
                    'component': scenario.affected_component,
                    'severity': scenario.severity
                }
                for scenario in self.active_failures.values()
            ],
            'total_failures': len(self.failure_history)
        }


if __name__ == "__main__":
    # Test failure mode simulator
    print("=== Failure Mode Simulator Test ===\n")

    config = {
        'failure_modes': {
            'enabled': True,
            'mtbf': 0  # Disable random failures for testing
        }
    }

    fms = FailureModeSimulator(config)

    # Test sensor failure
    print("Testing sensor failures...\n")

    # Inject stuck sensor
    print("1. Stuck sensor:")
    fms.inject_failure(FailureType.SENSOR_STUCK, 'temperature', duration=5.0)

    for i in range(10):
        true_value = 20.0 + i * 0.5
        measured = fms.apply_sensor_failure('temperature', true_value)
        print(f"   True: {true_value:.1f}°C, Measured: {measured:.1f}°C")
        time.sleep(0.5)
        fms.update(i * 0.5)

    fms.clear_all_failures()

    # Test noisy sensor
    print("\n2. Noisy sensor:")
    fms.inject_failure(FailureType.SENSOR_NOISY, 'temperature', severity=1.0, duration=5.0)

    for i in range(5):
        true_value = 25.0
        measured = fms.apply_sensor_failure('temperature', true_value)
        print(f"   True: {true_value:.1f}°C, Measured: {measured:.1f}°C")

    fms.clear_all_failures()

    # Test actuator failure
    print("\n3. Actuator stuck on:")
    fms.inject_failure(FailureType.ACTUATOR_STUCK_ON, 'fan', severity=0.8)

    for commanded_value in [0, 25, 50, 75, 100]:
        actual_state, actual_value = fms.check_actuator_failure('fan', True, commanded_value)
        print(f"   Commanded: {commanded_value}%, Actual: {actual_value:.0f}%")

    fms.clear_all_failures()

    # Test environmental stress
    print("\n4. Heatwave:")
    fms.inject_failure(FailureType.HEATWAVE, 'environment', severity=1.0)

    base_temp = 20.0
    stressed_temp = fms.get_environmental_stress(base_temp)
    print(f"   Base ambient: {base_temp}°C, Stressed: {stressed_temp}°C")

    # Summary
    summary = fms.get_failure_summary()
    print(f"\nFailure summary:")
    print(f"   Active failures: {summary['active_count']}")
    print(f"   Total failures injected: {summary['total_failures']}")

    print("\nTest complete!")
