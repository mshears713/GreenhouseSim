# Greenhouse Control System - End-to-End Testing Guide

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [System Testing](#system-testing)
6. [Hardware Testing](#hardware-testing)
7. [Performance Testing](#performance-testing)
8. [Failure Mode Testing](#failure-mode-testing)
9. [Test Checklist](#test-checklist)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides comprehensive testing procedures for the Greenhouse Control System, covering simulation-only testing, hardware integration testing, and end-to-end validation.

### Testing Levels

- **Unit Tests**: Individual component testing (models, controllers)
- **Integration Tests**: Component interaction testing (simulation engine, serial communication)
- **System Tests**: Full system behavior testing (UI, control loops, data logging)
- **Hardware Tests**: Arduino integration and sensor/actuator validation
- **Performance Tests**: Real-time performance and reliability validation
- **Failure Mode Tests**: Robustness and error handling validation

---

## Test Environment Setup

### Prerequisites

1. **Python Environment**:
   ```bash
   python --version  # Should be 3.8+
   pip install -r requirements.txt
   ```

2. **Testing Tools**:
   ```bash
   pip install pytest pytest-cov
   ```

3. **Arduino Environment** (for hardware testing):
   - Arduino IDE 1.8.19+ or Arduino CLI
   - USB cable for Arduino connection
   - Arduino Mega 2560 (or compatible)

4. **Directory Structure**:
   ```
   GreenhouseSim/
   ├── python/
   │   ├── tests/           # Unit tests
   │   └── ...
   ├── arduino/
   │   ├── tests/           # Arduino test sketches
   │   └── ...
   ├── data/
   │   └── logs/            # Log files
   └── docs/
       └── TESTING_GUIDE.md # This file
   ```

---

## Unit Testing

### Running Python Unit Tests

Execute all unit tests with pytest:

```bash
cd /path/to/GreenhouseSim
pytest python/tests/ -v
```

### Expected Results

```
python/tests/test_temperature_model.py::TestTemperatureModelInitialization::test_initial_temperature PASSED
python/tests/test_temperature_model.py::TestHeaterBehavior::test_heater_increases_temperature PASSED
python/tests/test_moisture_model.py::TestMoistureModelInitialization::test_initial_moisture PASSED
...
======================== 60 passed in 2.34s ========================
```

### Coverage Report

Generate coverage report:

```bash
pytest python/tests/ --cov=python/simulation --cov-report=html
```

View report: Open `htmlcov/index.html` in a browser.

**Target Coverage**: ≥ 85% for core simulation modules

---

## Integration Testing

### Simulation Engine Integration

**Test Objective**: Verify all simulation models work together correctly.

**Procedure**:

1. Start simulation engine:
   ```python
   from python.simulation.engine import SimulationEngine

   engine = SimulationEngine("simulation_config.yaml")
   engine.start()
   ```

2. Run for 60 seconds of simulated time

3. Verify:
   - Temperature model responds to heater/fan
   - Moisture model responds to pump
   - Humidity updates based on evaporation
   - Airflow responds to fan speed
   - No crashes or errors

**Expected Results**:
- ✅ All models update smoothly
- ✅ Values remain within physical bounds
- ✅ Update rate maintains target (10 Hz)
- ✅ Performance ratio ≥ 95%

### Serial Communication Integration

**Test Objective**: Verify Python ↔ Arduino communication without hardware.

**Procedure**:

1. Use virtual serial port (socat or com0com):
   ```bash
   # Linux/macOS
   socat -d -d pty,raw,echo=0 pty,raw,echo=0
   ```

2. Connect serial interface to virtual port

3. Send test commands and verify parsing

**Expected Results**:
- ✅ Messages sent successfully
- ✅ Checksums validated correctly
- ✅ No message loss
- ✅ Error detection working

---

## System Testing

### End-to-End Simulation Testing

**Test Objective**: Verify complete system functionality in simulation mode.

**Procedure**:

1. **Launch Dashboard**:
   ```bash
   cd python/ui
   streamlit run app.py
   ```

2. **Configure System**:
   - Select "Simulation Only" mode
   - Set temperature setpoint: 24°C
   - Set moisture setpoint: 60%

3. **Test Each Control Mode**:

   **a. Manual Mode**
   - Set control mode to "Manual"
   - Adjust fan speed slider: 0% → 50% → 100%
   - Observe temperature decreasing with higher fan speed
   - Toggle heater ON/OFF
   - Observe temperature increasing when ON
   - Trigger pump (1s pulse)
   - Observe moisture increasing

   **b. PID Mode**
   - Set control mode to "PID"
   - Set Kp=1.0, Ki=0.1, Kd=0.05
   - Set temperature setpoint: 22°C
   - Observe system converging to setpoint
   - Verify no excessive oscillation
   - Check settling time < 300 seconds

4. **Monitor Data Logging**:
   - Navigate to "Data & Logs" tab
   - Verify data appearing in table
   - Export CSV and verify format
   - Check log files in `data/logs/`

5. **Performance Monitoring**:
   - Navigate to "Simulation" tab
   - Verify update rate ≈ 10 Hz
   - Check performance ratio ≥ 95%
   - Expand "Advanced Performance Metrics"
   - Verify avg update time < 10 ms

**Expected Results**:
- ✅ All tabs render without errors
- ✅ Controls respond immediately
- ✅ Charts update in real-time
- ✅ Data logged correctly
- ✅ Performance metrics healthy

---

## Hardware Testing

### Arduino Test Sketches

**Test Objective**: Validate Arduino sensors and actuators independently.

#### 1. Sensor Testing

**Procedure**:

1. Upload `arduino/tests/test_sensors/test_sensors.ino` to Arduino

2. Open Serial Monitor (9600 baud)

3. Tests run automatically:
   - Temperature sensor (DHT11/DHT22)
   - Moisture sensor (analog)
   - ADC calibration
   - Noise measurement
   - Response time

**Expected Results**:
```
===== GREENHOUSE SENSOR TEST SUITE =====
[TEST 1] Temperature Sensor
  Measured temperature: 22.3 °C
  ✓ PASS

[TEST 2] Moisture Sensor
  Measured moisture: 45.2 %
  ✓ PASS
...
===== ALL TESTS COMPLETE =====
Passed: 6 / Failed: 0
```

#### 2. Actuator Testing

**Procedure**:

1. Upload `arduino/tests/test_actuators/test_actuators.ino` to Arduino

2. Open Serial Monitor (9600 baud)

3. Type `START` to begin interactive tests

4. Follow prompts for each actuator:
   - Fan: Verify spinning at different speeds
   - Heater: Verify heating (touch test - careful!)
   - Pump: Verify water flow
   - Servo: Verify vent movement

5. Type `STOP` if emergency shutdown needed

**Expected Results**:
- ✅ Fan spins at all speed levels
- ✅ Heater warms up when ON
- ✅ Pump delivers water
- ✅ Servo moves smoothly to positions

### Arduino ↔ Python Integration

**Test Objective**: Verify full hardware communication loop.

**Procedure**:

1. Upload `arduino/greenhouse_control/greenhouse_control.ino` to Arduino

2. Launch Streamlit dashboard:
   ```bash
   streamlit run python/ui/app.py
   ```

3. Select "Hardware Connected" mode

4. Enter serial port (e.g., `/dev/ttyACM0` or `COM3`)

5. Click "Connect to Arduino"

6. **Verify Communication**:
   - Check sidebar shows "Arduino: Connected"
   - Monitor tab shows real sensor readings
   - Actuator status updates in real-time

7. **Test Commands**:
   - Change setpoint → verify Arduino ACK
   - Switch control modes → verify mode change
   - Manual controls → verify actuators respond
   - PID tuning → verify parameters applied

**Expected Results**:
- ✅ Connection established within 5 seconds
- ✅ Real sensor data appears in monitoring tab
- ✅ Commands acknowledged by Arduino
- ✅ Actuators respond to manual controls
- ✅ No checksum errors in logs
- ✅ Reconnection works if USB unplugged/replugged

---

## Performance Testing

### Real-Time Performance

**Test Objective**: Verify system meets real-time requirements.

**Test Procedure**:

1. Run simulation for 1 hour of real time

2. Monitor performance metrics in "Simulation" tab

3. Record statistics every 5 minutes

**Acceptance Criteria**:
- ✅ Update rate: 9.5-10.5 Hz (±5%)
- ✅ Performance ratio: ≥ 95%
- ✅ Average update time: < 10 ms
- ✅ Max update time: < 50 ms
- ✅ No crashes or freezes
- ✅ Memory usage stable (no leaks)

### Stress Testing

**Test Objective**: Verify system stability under load.

**Procedure**:

1. Enable all failure modes simultaneously

2. Inject failures every 60 seconds

3. Rapidly change setpoints (every 5 seconds)

4. Run for 30 minutes

**Expected Results**:
- ✅ System remains responsive
- ✅ No crashes or hangs
- ✅ Errors logged appropriately
- ✅ Recovery from failures automatic

---

## Failure Mode Testing

### Sensor Failure Testing

**Test Objective**: Verify system handles sensor failures gracefully.

**Test Cases**:

| Failure Type | Component | Duration | Expected Behavior |
|--------------|-----------|----------|-------------------|
| Sensor Stuck | Temperature | 60s | Controller uses last valid reading, alert generated |
| Sensor Noisy | Moisture | 120s | Controller filters noise, may reduce accuracy |
| Sensor Dropout | Temperature | 30s | Fallback to default/safe value |

**Procedure**:

1. Navigate to "Simulation" tab

2. Select failure type: "Sensor Stuck"

3. Component: "temperature"

4. Duration: 60 seconds

5. Click "Inject Failure"

6. **Observe**:
   - Alert appears in sidebar
   - Temperature reading freezes
   - Controller continues operating
   - System recovers after 60s

**Expected Results**:
- ✅ Failure indicated visually
- ✅ System remains safe (no plant damage)
- ✅ Automatic recovery after duration
- ✅ Event logged in `data/logs/errors.log`

### Communication Failure Testing

**Test Objective**: Verify reconnection logic works.

**Procedure**:

1. Connect to Arduino in hardware mode

2. Verify connection healthy

3. Unplug USB cable

4. Wait 5 seconds

5. Reconnect USB cable

6. Observe reconnection attempts

**Expected Results**:
- ✅ Connection loss detected within 10 seconds
- ✅ Reconnection attempts begin automatically
- ✅ Exponential backoff used (2s, 4s, 8s, ...)
- ✅ Connection re-established successfully
- ✅ Operation resumes normally
- ✅ Events logged in `communication.log`

### Power Loss Simulation

**Test Objective**: Verify system handles power interruptions.

**Procedure**:

1. In simulation tab, inject "Power Failure" for 30s

2. Observe all actuators turn OFF

3. System should:
   - Stop all control actions
   - Log power failure event
   - Resume control after recovery

**Expected Results**:
- ✅ Immediate actuator shutdown
- ✅ Alert generated
- ✅ Automatic recovery after 30s
- ✅ Control resumes smoothly

---

## Test Checklist

### Pre-Release Validation Checklist

Use this checklist before each release to ensure quality:

#### Python Unit Tests
- [ ] All unit tests pass (pytest)
- [ ] Code coverage ≥ 85%
- [ ] No warnings or deprecations

#### Simulation Tests
- [ ] Temperature model: heater, fan, solar working
- [ ] Moisture model: pump, evaporation, drainage working
- [ ] Airflow model: fan, natural ventilation working
- [ ] Simulation performance ≥ 95%

#### UI/Dashboard Tests
- [ ] All tabs render without errors
- [ ] Monitoring tab: metrics display correctly
- [ ] Control tab: setpoints apply correctly
- [ ] Simulation tab: performance metrics visible
- [ ] Data tab: export CSV working
- [ ] Input validation: warnings for out-of-range values
- [ ] Responsive layout: works on different screen sizes

#### Arduino Tests
- [ ] Sensor test sketch: all sensors pass
- [ ] Actuator test sketch: all actuators respond
- [ ] Serial checksum: no errors in 1000 messages
- [ ] Command acknowledgment: all commands ACKed

#### Integration Tests
- [ ] Python ↔ Arduino: successful connection
- [ ] Real-time sensor data: appearing in UI
- [ ] Command execution: actuators respond
- [ ] Reconnection: works after disconnect
- [ ] Data logging: CSV and SQLite working

#### Performance Tests
- [ ] Update rate: 9.5-10.5 Hz sustained
- [ ] Performance ratio: ≥ 95% for 1 hour
- [ ] Memory usage: stable (no leaks)
- [ ] CPU usage: < 50% average

#### Failure Mode Tests
- [ ] Sensor stuck: detected and handled
- [ ] Sensor noisy: filtered appropriately
- [ ] Actuator stuck: detected and alarmed
- [ ] Communication loss: reconnection working
- [ ] Checksum errors: detected and logged
- [ ] Power failure: graceful shutdown/recovery

#### Logging Tests
- [ ] Main log: entries appear in `greenhouse_main.log`
- [ ] Communication log: TX/RX logged in `communication.log`
- [ ] Error log: errors appear in `errors.log`
- [ ] Log rotation: files rotate at 10MB
- [ ] Performance: logging doesn't impact update rate

#### Documentation Tests
- [ ] README accurate and complete
- [ ] Code comments clear and helpful
- [ ] Docstrings present for all public functions
- [ ] Testing guide (this file) up to date
- [ ] Configuration file documented

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Unit tests fail on temperature model

**Symptoms**:
```
AssertionError: Temperature should decrease with fan ON
```

**Diagnosis**:
- Check `simulation_config.yaml` fan efficiency parameter
- Verify time step allows sufficient cooling

**Solution**:
```yaml
temperature:
  fan_efficiency: 0.03  # Should be > 0
```

#### Issue: Arduino not connecting

**Symptoms**:
```
ERROR: Failed to connect to /dev/ttyACM0
```

**Diagnosis**:
1. List available ports:
   ```python
   from python.communication.serial_interface import ArduinoInterface
   print(ArduinoInterface.list_available_ports())
   ```
2. Check permissions (Linux):
   ```bash
   sudo usermod -a -G dialout $USER
   ```

**Solution**:
- Use correct port name
- Check USB cable connection
- Verify Arduino power LED is on
- Try different USB port

#### Issue: Checksum errors in communication

**Symptoms**:
```
ERROR: Checksum validation failed
```

**Diagnosis**:
- Check baud rate matches (9600)
- Verify USB cable quality
- Check for electrical interference

**Solution**:
- Replace USB cable
- Enable/disable checksums in both sides
- Reduce baud rate if errors persist

#### Issue: Simulation performance < 95%

**Symptoms**:
```
WARNING: Performance ratio: 78%
```

**Diagnosis**:
- Check CPU usage (other processes?)
- Verify update rate target is reasonable
- Check if advanced physics enabled

**Solution**:
```yaml
simulation:
  target_update_rate: 5.0  # Reduce from 10.0
  adaptive_timing: true     # Enable adaptive mode
advanced:
  enabled: false            # Disable CPU-intensive features
```

#### Issue: Streamlit dashboard unresponsive

**Symptoms**:
- Controls don't respond
- Charts not updating

**Diagnosis**:
- Check simulation engine running
- Verify no exceptions in console
- Check browser console for errors

**Solution**:
1. Restart Streamlit:
   ```bash
   streamlit run python/ui/app.py --server.port 8501
   ```
2. Clear browser cache
3. Try different browser

#### Issue: Data not logging

**Symptoms**:
- No entries in SQLite database
- CSV files empty

**Diagnosis**:
- Check `data/logs/` directory exists
- Verify write permissions
- Check DataLogger initialization

**Solution**:
```bash
mkdir -p data/logs
chmod 755 data/logs
```

#### Issue: PID controller oscillating

**Symptoms**:
- Temperature overshoots setpoint
- Continuous oscillation

**Diagnosis**:
- Kp too high
- Ki too high
- Kd too low

**Solution**:
1. Reduce Kp by 50%
2. Reduce Ki by 75%
3. Increase Kd slightly
4. Use Ziegler-Nichols tuning method

---

## Acceptance Criteria

### System Acceptance

The system is considered ready for deployment when:

1. **All unit tests pass** with ≥ 85% coverage
2. **Integration tests pass** without errors
3. **Hardware tests pass** all sensor/actuator checks
4. **Performance criteria met**:
   - Update rate: 9.5-10.5 Hz
   - Performance ratio: ≥ 95%
   - Response time: < 100ms
5. **Failure handling verified**:
   - All failure modes tested
   - Recovery automatic
   - Alerts generated appropriately
6. **Logging functional**:
   - All events logged
   - Log files rotate correctly
   - No performance impact
7. **Documentation complete**:
   - README current
   - Code commented
   - Testing guide (this file) accurate

---

## Continuous Integration

### Automated Testing

**Recommended CI/CD Pipeline**:

```yaml
# .github/workflows/test.yml (example)
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest python/tests/ -v --cov
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-19 | Initial testing guide created |

---

**For questions or issues, please open a GitHub issue or contact the development team.**
