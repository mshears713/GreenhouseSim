# Arduino Test Sketches

This directory contains test sketches for validating Arduino hardware functionality.

## Available Tests

### 1. test_sensors
**Purpose:** Validate sensor reading functions

**Tests:**
- Temperature sensor accuracy and range
- Moisture sensor calibration
- Airflow sensor (if present)
- Raw ADC readings
- Sensor noise analysis
- Response time measurement

**Usage:**
```bash
# Upload test_sensors.ino to Arduino
# Open Serial Monitor at 115200 baud
# Tests run automatically on startup
# Continuous monitoring displays updated readings every 2 seconds
```

**Expected Results:**
- Temperature: 15-35°C (room temperature)
- Moisture: 0-100% (calibrated)
- ADC values: Not stuck at 0 or 1023
- Noise: Standard deviation < 2°C
- Response time: < 500ms per sensor

### 2. test_actuators
**Purpose:** Validate actuator control functions

**Tests:**
- Fan PWM control
- Heater on/off switching
- Pump on/off control and safety timers
- Servo positioning (if present)
- PWM range verification

**SAFETY WARNINGS:**
- Ensure pump has water supply
- Position heater safely
- Be ready to disconnect power if needed
- Clear area of obstructions

**Usage:**
```bash
# Upload test_actuators.ino to Arduino
# Open Serial Monitor at 115200 baud
# Type 'START' to begin tests
# Type 'STOP' for emergency shutdown
# Observe actuator behavior during tests
```

**Expected Results:**
- Fan spins at various speeds
- Heater indicator turns on/off
- Pump activates and water flows
- Servo moves smoothly through range
- Safety timers prevent rapid pump cycling

## Test Development Guidelines

### Creating New Tests

1. **Structure:** Follow the pattern in existing tests
   - Setup: Initialize hardware
   - Test functions: One function per test
   - Utility functions: Helpers for output formatting

2. **Serial Output:** Use clear, descriptive messages
   ```cpp
   Serial.println(F("Testing XYZ..."));
   Serial.print(F("  Result: "));
   Serial.println(value);
   ```

3. **Safety First:**
   - Always initialize to safe state
   - Implement emergency stop
   - Warn user before activating actuators
   - Include appropriate delays

4. **Manual Verification:**
   - Embedded tests often require human observation
   - Provide clear "OBSERVE:" prompts
   - Ask user to verify expected behavior

### Best Practices

- **Use F() macro** for string literals to save RAM
- **Constrain values** before sending to actuators
- **Add delays** between operations to allow observation
- **Test edge cases** (0%, 100%, min, max values)
- **Document expected behavior** in comments

## Troubleshooting

### Sensor Tests Failing

**Problem:** Temperature reading unreasonable
- **Check:** Sensor wiring (VCC, GND, Signal)
- **Check:** Sensor type (ensure it's TMP36 or compatible)
- **Check:** Pin assignment matches sketch

**Problem:** Moisture reading always 0 or 100%
- **Check:** Calibration values need adjustment
- **Check:** Sensor connected properly
- **Action:** Run calibration procedure in main sketch

**Problem:** High sensor noise
- **Check:** Power supply quality
- **Check:** Wire length and routing (avoid power wires)
- **Action:** Increase averaging samples

### Actuator Tests Failing

**Problem:** Fan not spinning
- **Check:** Power supply adequate (fans draw current)
- **Check:** PWM pin correct (must be PWM-capable pin)
- **Check:** Fan minimum startup speed threshold
- **Try:** Increase FAN_STARTUP_SPEED constant

**Problem:** Pump safety timer not working
- **Check:** Code logic in setPump() function
- **Check:** millis() rollover handling (occurs every 50 days)

**Problem:** Servo not moving
- **Check:** Servo power supply (needs good 5V source)
- **Check:** Servo.h library included
- **Check:** Servo attached to correct pin

## Integration with Main Sketch

After testing:
1. Verify all tests pass
2. Note any calibration adjustments needed
3. Update main sketch configuration with calibration values
4. Document any hardware quirks or limitations

## Educational Notes

These test sketches demonstrate:
- **Structured testing** on embedded systems
- **Hardware validation** techniques
- **Safety-first** programming approach
- **User interaction** via Serial Monitor
- **Diagnostic output** for debugging

Unlike Python with pytest, Arduino testing is more manual but equally important for ensuring hardware reliability.
