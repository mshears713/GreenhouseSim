/*
 * Actuator Control Functions
 *
 * This file contains all actuator control functions for the
 * greenhouse control system.
 *
 * Actuators:
 * - Fan (PWM speed control on Pin 9)
 * - Heater (On/Off or PWM on Pin 10)
 * - Water Pump (On/Off on Pin 11)
 * - Vent Servo (Position control on Pin 6) - Optional
 *
 * Educational Notes:
 * - PWM (Pulse Width Modulation) allows proportional control
 * - Safety limits prevent actuator damage
 * - State tracking allows monitoring and logging
 * - Gradual changes prevent mechanical stress
 */

#include <Servo.h>  // Library for servo control

// ============================================================================
// ACTUATOR CONFIGURATION
// ============================================================================

// Fan control parameters
const int FAN_MIN_SPEED = 0;      // Minimum PWM value (off)
const int FAN_MAX_SPEED = 255;    // Maximum PWM value (full speed)
const int FAN_STARTUP_SPEED = 100; // Minimum speed for fan to spin

// Heater control parameters
const int HEATER_PWM_MAX = 255;   // Maximum heater power (if using PWM)
const bool HEATER_USE_PWM = false; // Set true for proportional heating

// Pump control parameters
const unsigned long PUMP_MAX_RUNTIME = 30000;  // Max continuous run: 30 seconds
const unsigned long PUMP_MIN_OFFTIME = 10000;  // Min off time: 10 seconds
unsigned long pumpStartTime = 0;
unsigned long pumpStopTime = 0;

// Servo control (optional)
Servo ventServo;
const int SERVO_MIN_POS = 0;      // Fully closed
const int SERVO_MAX_POS = 180;    // Fully open
const int SERVO_DEFAULT_POS = 90; // Half open
bool servoAttached = false;

// Ramping parameters (for smooth changes)
const int FAN_RAMP_RATE = 5;      // PWM units per update (smooth acceleration)

// ============================================================================
// ACTUATOR CONTROL FUNCTIONS
// ============================================================================

/**
 * Initialize all actuators to safe state
 *
 * Should be called during setup() to ensure all actuators
 * start in a known, safe state (typically OFF).
 *
 * Educational Note:
 * Always initialize hardware to a safe state on startup.
 * This prevents unexpected behavior if Arduino resets during operation.
 */
void initializeActuators() {
  // Set all actuators to OFF/safe state
  setFanSpeed(0);
  setHeater(false);
  setPump(false);

  // Initialize servo if used
  if (!servoAttached) {
    ventServo.attach(VENT_SERVO_PIN);
    servoAttached = true;
    setVentPosition(SERVO_DEFAULT_POS);
  }

  Serial.println(F("Actuators initialized to safe state"));
}

// ============================================================================
// FAN CONTROL
// ============================================================================

/**
 * Set fan speed with PWM
 *
 * Parameters:
 *   speed: 0-255 (0 = off, 255 = maximum speed)
 *
 * Educational Note:
 * PWM (Pulse Width Modulation) varies the average power by rapidly
 * switching the output on and off. Higher duty cycle = more power.
 * Arduino's analogWrite() function provides 8-bit PWM (0-255).
 */
void setFanSpeed(int speed) {
  // Constrain to valid range
  speed = constrain(speed, FAN_MIN_SPEED, FAN_MAX_SPEED);

  // Apply minimum speed threshold (some fans don't spin below certain PWM)
  if (speed > 0 && speed < FAN_STARTUP_SPEED) {
    speed = FAN_STARTUP_SPEED;
  }

  // Update global state
  fanSpeed = speed;

  // Apply PWM to fan pin
  analogWrite(FAN_PIN, fanSpeed);
}

/**
 * Set fan speed with percentage (0-100%)
 *
 * More intuitive interface than raw PWM values
 */
void setFanSpeedPercent(float percent) {
  percent = constrain(percent, 0.0, 100.0);
  int pwmValue = map(percent, 0, 100, 0, 255);
  setFanSpeed(pwmValue);
}

/**
 * Gradually ramp fan speed to target
 *
 * Smooth speed changes reduce mechanical stress and noise
 *
 * Educational Note:
 * Sudden speed changes can cause wear on motor bearings and
 * create noise. Ramping provides smoother operation.
 */
void rampFanSpeed(int targetSpeed) {
  targetSpeed = constrain(targetSpeed, FAN_MIN_SPEED, FAN_MAX_SPEED);

  if (fanSpeed < targetSpeed) {
    // Ramp up
    fanSpeed = min(fanSpeed + FAN_RAMP_RATE, targetSpeed);
  } else if (fanSpeed > targetSpeed) {
    // Ramp down
    fanSpeed = max(fanSpeed - FAN_RAMP_RATE, targetSpeed);
  }

  analogWrite(FAN_PIN, fanSpeed);
}

// ============================================================================
// HEATER CONTROL
// ============================================================================

/**
 * Set heater state (ON/OFF)
 *
 * Parameters:
 *   state: true = ON, false = OFF
 *
 * Educational Note:
 * Heating elements should be controlled carefully:
 * - Use relay or MOSFET rated for the heater current
 * - Include thermal protection (fuse, temperature cutoff)
 * - Never leave heater on if temperature sensor fails
 */
void setHeater(bool state) {
  // Safety check: don't turn on heater if sensor error
  if (state && errorState) {
    Serial.println(F("WARNING: Cannot enable heater - sensor error"));
    state = false;
  }

  // Safety check: don't overheat
  if (state && currentTemperature > 50.0) {
    Serial.println(F("WARNING: Temperature too high, disabling heater"));
    state = false;
  }

  heaterState = state;

  if (HEATER_USE_PWM) {
    // PWM control for proportional heating
    analogWrite(HEATER_PIN, state ? HEATER_PWM_MAX : 0);
  } else {
    // Simple on/off control
    digitalWrite(HEATER_PIN, state ? HIGH : LOW);
  }
}

/**
 * Set heater power level (if using PWM)
 *
 * Parameters:
 *   power: 0-100% power level
 */
void setHeaterPower(float percent) {
  if (!HEATER_USE_PWM) {
    // If not using PWM, treat >50% as ON, <=50% as OFF
    setHeater(percent > 50.0);
    return;
  }

  // Safety checks
  if (errorState || currentTemperature > 50.0) {
    setHeater(false);
    return;
  }

  percent = constrain(percent, 0.0, 100.0);
  int pwmValue = map(percent, 0, 100, 0, HEATER_PWM_MAX);

  heaterState = (pwmValue > 0);
  analogWrite(HEATER_PIN, pwmValue);
}

// ============================================================================
// PUMP CONTROL
// ============================================================================

/**
 * Set water pump state (ON/OFF)
 *
 * Parameters:
 *   state: true = ON, false = OFF
 *
 * Safety Features:
 * - Maximum continuous runtime limit
 * - Minimum off time between runs (prevent overheating)
 * - Automatic shutoff if runtime exceeded
 *
 * Educational Note:
 * Pumps can overheat if run continuously without water or for too long.
 * Implementing runtime limits protects the pump and prevents flooding.
 */
void setPump(bool state) {
  unsigned long currentTime = millis();

  if (state) {
    // Turning pump ON

    // Check if minimum off time has elapsed since last stop
    if (pumpStopTime > 0 && (currentTime - pumpStopTime) < PUMP_MIN_OFFTIME) {
      Serial.println(F("WARNING: Pump minimum off time not elapsed"));
      return;
    }

    // Start pump
    if (!pumpState) {  // Only if not already running
      pumpState = true;
      pumpStartTime = currentTime;
      digitalWrite(PUMP_PIN, HIGH);
      Serial.println(F("Pump started"));
    }

  } else {
    // Turning pump OFF

    if (pumpState) {  // Only if currently running
      pumpState = false;
      pumpStopTime = currentTime;
      digitalWrite(PUMP_PIN, LOW);

      // Log runtime for monitoring
      unsigned long runtime = currentTime - pumpStartTime;
      Serial.print(F("Pump stopped. Runtime: "));
      Serial.print(runtime / 1000);
      Serial.println(F(" seconds"));
    }
  }
}

/**
 * Check and enforce pump safety limits
 *
 * Should be called regularly from main loop to ensure pump
 * doesn't exceed maximum runtime.
 */
void checkPumpSafety() {
  if (pumpState) {
    unsigned long runtime = millis() - pumpStartTime;

    if (runtime > PUMP_MAX_RUNTIME) {
      Serial.println(F("WARNING: Pump max runtime exceeded, shutting off"));
      setPump(false);

      // Set error flag
      errorState = true;
      lastError = "PUMP_OVERTIME";
    }
  }
}

/**
 * Pulse pump for specified duration
 *
 * Useful for precise watering control
 *
 * Parameters:
 *   durationMs: How long to run pump in milliseconds
 */
void pulsePump(unsigned long durationMs) {
  durationMs = min(durationMs, PUMP_MAX_RUNTIME);

  Serial.print(F("Pulsing pump for "));
  Serial.print(durationMs);
  Serial.println(F(" ms"));

  setPump(true);
  delay(durationMs);
  setPump(false);
}

// ============================================================================
// VENT SERVO CONTROL (Optional)
// ============================================================================

/**
 * Set vent position using servo
 *
 * Parameters:
 *   position: 0-180 degrees (0 = closed, 180 = fully open)
 *
 * Educational Note:
 * Servos provide precise position control, useful for vents,
 * louvers, or other mechanical adjustments. Standard hobby servos
 * use 50Hz PWM with 1-2ms pulse width for 0-180° range.
 */
void setVentPosition(int position) {
  if (!servoAttached) {
    ventServo.attach(VENT_SERVO_PIN);
    servoAttached = true;
  }

  position = constrain(position, SERVO_MIN_POS, SERVO_MAX_POS);
  ventPosition = position;
  ventServo.write(position);

  // Small delay for servo to reach position
  delay(15);
}

/**
 * Set vent position as percentage (0-100%)
 */
void setVentPositionPercent(float percent) {
  percent = constrain(percent, 0.0, 100.0);
  int position = map(percent, 0, 100, SERVO_MIN_POS, SERVO_MAX_POS);
  setVentPosition(position);
}

/**
 * Open vent fully
 */
void openVent() {
  setVentPosition(SERVO_MAX_POS);
  Serial.println(F("Vent fully opened"));
}

/**
 * Close vent fully
 */
void closeVent() {
  setVentPosition(SERVO_MIN_POS);
  Serial.println(F("Vent fully closed"));
}

// ============================================================================
// ACTUATOR STATUS AND SAFETY
// ============================================================================

/**
 * Emergency stop - turn off all actuators
 *
 * Should be called in error conditions or when system is disabled
 */
void emergencyStopAll() {
  Serial.println(F("!!! EMERGENCY STOP - All actuators disabled !!!"));

  setFanSpeed(0);
  setHeater(false);
  setPump(false);
  setVentPosition(SERVO_DEFAULT_POS);

  systemEnabled = false;
  errorState = true;
  lastError = "EMERGENCY_STOP";
}

/**
 * Print current actuator states
 *
 * Useful for debugging and status monitoring
 */
void printActuatorStatus() {
  Serial.println(F("=== Actuator Status ==="));

  Serial.print(F("Fan Speed: "));
  Serial.print(fanSpeed);
  Serial.print(F(" ("));
  Serial.print(map(fanSpeed, 0, 255, 0, 100));
  Serial.println(F("%)"));

  Serial.print(F("Heater: "));
  Serial.println(heaterState ? F("ON") : F("OFF"));

  Serial.print(F("Pump: "));
  Serial.println(pumpState ? F("ON") : F("OFF"));
  if (pumpState) {
    unsigned long runtime = millis() - pumpStartTime;
    Serial.print(F("  Runtime: "));
    Serial.print(runtime / 1000);
    Serial.println(F(" s"));
  }

  Serial.print(F("Vent Position: "));
  Serial.print(ventPosition);
  Serial.print(F("° ("));
  Serial.print(map(ventPosition, 0, 180, 0, 100));
  Serial.println(F("%)"));

  Serial.println(F("====================="));
  Serial.println();
}

/**
 * Test all actuators sequentially
 *
 * Useful for initial hardware validation
 */
void testActuators() {
  Serial.println(F("Starting actuator test sequence..."));
  Serial.println(F("WARNING: Ensure safe conditions before proceeding!"));
  delay(2000);

  // Test Fan
  Serial.println(F("Testing Fan..."));
  setFanSpeed(128);  // 50% speed
  delay(3000);
  setFanSpeed(255);  // 100% speed
  delay(3000);
  setFanSpeed(0);    // Off
  delay(1000);

  // Test Heater (short duration for safety)
  Serial.println(F("Testing Heater (2 seconds)..."));
  setHeater(true);
  delay(2000);
  setHeater(false);
  delay(1000);

  // Test Pump (short pulse)
  Serial.println(F("Testing Pump (1 second)..."));
  pulsePump(1000);
  delay(1000);

  // Test Vent Servo
  Serial.println(F("Testing Vent Servo..."));
  closeVent();
  delay(1000);
  setVentPosition(90);
  delay(1000);
  openVent();
  delay(1000);
  setVentPosition(90);

  Serial.println(F("Actuator test complete!"));
  printActuatorStatus();
}
