# Hardware Setup Guide

## Overview

This guide provides detailed instructions for connecting sensors and actuators to the Arduino for the Smart Mini Greenhouse Control System.

## Required Components

### Arduino Board
- **Recommended:** Arduino Uno or Arduino Mega
- USB cable for programming and communication
- Power supply (9V, 1A recommended for actuators)

### Sensors

#### 1. Temperature Sensor - TMP36
- **Connection:**
  - Pin 1 (Left, flat side facing you): +5V
  - Pin 2 (Center): Signal → Arduino A0
  - Pin 3 (Right): GND
- **Characteristics:**
  - Range: -40°C to +125°C
  - Output: 10mV/°C with 500mV offset
  - Formula: Temperature (°C) = (Voltage - 0.5) × 100

#### 2. Soil Moisture Sensor
- **Type:** Capacitive (recommended) or Resistive
- **Connection:**
  - VCC → Arduino 5V
  - GND → Arduino GND
  - AOUT (Analog) → Arduino A1
- **Characteristics:**
  - Output: 0-1023 (analog reading)
  - Higher values = Wetter soil (capacitive)
  - Calibration required for accurate readings

#### 3. Airflow Sensor (Optional)
- **Type:** Small anemometer or air velocity sensor
- **Connection:**
  - VCC → Arduino 5V
  - GND → Arduino GND
  - Signal → Arduino A2
- **Note:** This is optional for basic system operation

### Actuators

#### 1. Fan (Temperature Control)
- **Type:** 12V DC fan or 5V PWM fan
- **Connection via MOSFET/Transistor:**
  - Arduino Pin 9 → MOSFET Gate (via 220Ω resistor)
  - MOSFET Drain → Fan Negative
  - MOSFET Source → GND
  - Fan Positive → External Power Supply Positive
  - Flyback diode across fan terminals (cathode to +)
- **Educational Note:** PWM on Pin 9 allows variable speed control

#### 2. Heater Element
- **Type:** Small heating resistor or heating pad (5-12V, <1A)
- **Connection via Relay or MOSFET:**
  - Arduino Pin 10 → Relay/MOSFET control
  - Heater → Switched power supply
- **Safety:** Ensure heater is appropriately rated and insulated
- **Note:** Can use simple on/off or PWM for proportional control

#### 3. Water Pump
- **Type:** Small submersible pump (5-12V)
- **Connection via Relay:**
  - Arduino Pin 11 → Relay control (via transistor if needed)
  - Pump → Switched power supply
  - Flyback diode across pump terminals
- **Note:** Keep pump in water reservoir, check water level

#### 4. Vent Servo (Optional)
- **Type:** Standard hobby servo (SG90 or similar)
- **Connection:**
  - Brown/Black → GND
  - Red → 5V
  - Orange/Yellow → Arduino Pin 6
- **Note:** Controls vent opening for passive airflow
- **Library:** Use Servo.h library

### Additional Components

- **Status LED:** Built-in LED on Pin 13 (no external connection needed)
- **Power Supply:** 9-12V, 1-2A for Arduino + actuators
- **Breadboard:** For prototyping connections
- **Resistors:** 220Ω, 10kΩ for various circuits
- **MOSFETs:** N-channel (e.g., IRF520) for switching loads
- **Diodes:** 1N4001 or similar for flyback protection
- **Relay Module:** 5V relay board for high-current switching

## Wiring Diagram

```
                    Arduino Uno
                    ┌─────────┐
    TMP36 ──────────│ A0      │
    Moisture ───────│ A1      │
    Airflow ────────│ A2      │
                    │         │
    Fan PWM ────────│ D9   5V │──── Sensors VCC
    Heater ─────────│ D10 GND │──── Common GND
    Pump ───────────│ D11     │
    Servo ──────────│ D6      │
    Status LED ─────│ D13     │
                    └─────────┘
                    USB │
                        ▼
                    Computer
```

**Important:** All high-power loads (fan, heater, pump) should be switched through transistors, MOSFETs, or relays—never connect directly to Arduino pins!

## Setup Procedure

### Step 1: Prepare Workspace
1. Clear, dry workspace with adequate lighting
2. Anti-static mat (recommended)
3. Tools: wire strippers, screwdriver, multimeter

### Step 2: Connect Sensors First
1. **Without power connected**, wire temperature sensor to A0
2. Connect soil moisture sensor to A1
3. Optional: Connect airflow sensor to A2
4. Double-check all connections against pin diagram
5. Ensure no short circuits between 5V and GND

### Step 3: Connect Actuators
1. Build MOSFET/relay circuits on breadboard first
2. Test each circuit individually with LED before connecting actuators
3. Connect fan circuit to Pin 9
4. Connect heater circuit to Pin 10
5. Connect pump circuit to Pin 11
6. Optional: Connect servo to Pin 6
7. Add flyback diodes across all inductive loads

### Step 4: Power Considerations
1. Arduino can be powered via USB during development
2. For actuators, use external power supply
3. **Common ground:** Connect Arduino GND to external power GND
4. **Do not** power high-current actuators from Arduino 5V pin
5. Total current from Arduino 5V rail: <400mA

### Step 5: Initial Testing
1. Connect Arduino to computer via USB (no other power yet)
2. Upload test sketch (see `arduino/tests/test_sensors.ino`)
3. Open Serial Monitor at 9600 baud
4. Verify sensor readings are reasonable:
   - Temperature: Should be near room temperature (~20-25°C)
   - Moisture: 0-1023 range, changes when sensor touched with wet finger
5. Test actuators one at a time with test sketches

## Safety Checklist

- [ ] All connections checked for correct polarity
- [ ] No exposed wires that could short circuit
- [ ] Flyback diodes installed on all inductive loads
- [ ] External power supply rated appropriately
- [ ] Heater element properly insulated and rated
- [ ] Water pump kept away from electronics
- [ ] Fire extinguisher nearby when testing heater
- [ ] Adequate ventilation for testing

## Troubleshooting

### Sensors Not Reading Correctly

**Temperature always 0 or -40°C:**
- Check TMP36 wiring (easy to reverse pins)
- Verify 5V power supply is stable
- Measure voltage at sensor output pin (should be ~0.75V at 25°C)

**Moisture reading stuck at 0 or 1023:**
- Check sensor power connections
- Verify sensor is capacitive type (more reliable)
- Calibrate sensor: dry = one value, in water = different value

**Noisy sensor readings:**
- Add 0.1µF capacitor between sensor output and GND
- Use averaging in code (moving average filter)
- Check for nearby noise sources (motors, relays switching)

### Actuators Not Responding

**Fan not spinning:**
- Check MOSFET connections and orientation
- Verify PWM signal with multimeter or oscilloscope
- Test fan directly with power supply
- Check gate resistor (220Ω) is installed

**Heater not heating:**
- Verify relay clicking (if using relay)
- Check power supply voltage and current capacity
- Measure voltage across heater when activated
- Test heater element with multimeter (resistance should be reasonable)

**Pump not pumping:**
- Ensure pump is submerged in water
- Check relay operation (LED should light)
- Verify pump power supply
- Test pump directly with power supply

### Communication Issues

**Serial not connecting:**
- Check correct COM port selected
- Verify baud rate is 9600
- Try unplugging/replugging USB
- Check USB cable (some are charge-only)

**Erratic serial data:**
- Add delay between sensor readings
- Check for baud rate mismatch
- Ensure common ground between Arduino and sensors
- Reduce cable lengths if possible

## Calibration Procedure

### Temperature Sensor
1. Measure room temperature with reference thermometer
2. Compare to Arduino reading
3. Adjust `TEMP_OFFSET` constant in code if needed
4. For better accuracy, create lookup table or polynomial correction

### Moisture Sensor
1. Measure sensor value in completely dry soil: `MOISTURE_MIN`
2. Measure sensor value in saturated soil: `MOISTURE_MAX`
3. Update constants in code
4. Moisture % = map(reading, MOISTURE_MIN, MOISTURE_MAX, 0, 100)

### Actuators
1. Fan: Test at various PWM values (0, 64, 128, 192, 255)
2. Heater: Measure temperature rise rate
3. Pump: Measure flow rate (mL/second)
4. Record values for simulation model calibration

## Maintenance

- Clean moisture sensor weekly (corrosion prevention)
- Check all connections monthly
- Replace pump water regularly
- Test heater for proper shutoff (safety)
- Verify flyback diodes are intact

## Next Steps

After successful hardware setup:
1. Run sensor test sketches (`arduino/tests/test_sensors.ino`)
2. Run actuator test sketches (`arduino/tests/test_actuators.ino`)
3. Upload main control sketch (`arduino/greenhouse_control/greenhouse_control.ino`)
4. Proceed to Python simulation setup

## References

- [Arduino Uno Pinout](https://www.arduino.cc/en/Reference/Board)
- [TMP36 Datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/TMP35_36_37.pdf)
- [MOSFET Switching Tutorial](https://www.electronics-tutorials.ws/transistor/tran_7.html)
- [Flyback Diode Explanation](https://en.wikipedia.org/wiki/Flyback_diode)

---

**Safety Warning:** Working with electrical components carries risk. Always disconnect power before making changes. If unsure, consult an experienced electronics hobbyist or instructor.
