/*
 * Arduino Actuator Test Sketch
 *
 * This test sketch validates actuator control functionality for:
 * - Fan (PWM speed control)
 * - Heater (On/Off control)
 * - Water pump (On/Off control)
 * - Vent servo (Position control - optional)
 *
 * Purpose:
 * - Verify actuator wiring and connections
 * - Validate actuator control functions
 * - Test safety limits and constraints
 * - Verify PWM functionality
 *
 * SAFETY WARNING:
 * - This test will activate all actuators
 * - Ensure pump has water supply
 * - Ensure heater is in safe location
 * - Monitor test execution - be ready to disconnect power
 *
 * Instructions:
 * 1. Connect all actuators
 * 2. Ensure safe operating environment
 * 3. Upload this sketch to your Arduino
 * 4. Open Serial Monitor (115200 baud)
 * 5. Type 'START' to begin tests
 * 6. Monitor actuator behavior
 *
 * Educational Note:
 * Testing actuators requires careful observation. We use serial
 * commands to manually trigger tests, allowing operator control.
 */

#include <Servo.h>

// ============================================================================
// PIN DEFINITIONS (Match main sketch)
// ============================================================================

const int FAN_PIN = 9;
const int HEATER_PIN = 10;
const int PUMP_PIN = 11;
const int VENT_SERVO_PIN = 6;

// ============================================================================
// ACTUATOR CONFIGURATION
// ============================================================================

const int FAN_MIN_SPEED = 0;
const int FAN_MAX_SPEED = 255;
const int FAN_STARTUP_SPEED = 100;

const unsigned long PUMP_MAX_RUNTIME = 30000;
const unsigned long PUMP_MIN_OFFTIME = 10000;
unsigned long pumpStartTime = 0;
unsigned long pumpStopTime = 0;

Servo ventServo;
const int SERVO_MIN_POS = 0;
const int SERVO_MAX_POS = 180;
const int SERVO_DEFAULT_POS = 90;
bool servoAttached = false;

// ============================================================================
// TEST STATE
// ============================================================================

int testNumber = 0;
bool allTestsPassed = true;
bool testingEnabled = false;

int fanSpeed = 0;
bool heaterState = false;
bool pumpState = false;
int ventPosition = SERVO_DEFAULT_POS;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  delay(1000);

  // Configure pins
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HEATER_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);

  // Initialize to safe state
  initializeActuators();

  printHeader();
  printSafetyWarning();

  Serial.println(F("\nType 'START' to begin actuator tests"));
  Serial.println(F("Type 'STOP' to halt all actuators"));
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();

    if (command == "START") {
      testingEnabled = true;
      Serial.println(F("\n=== STARTING ACTUATOR TESTS ===\n"));
      runAllTests();
    } else if (command == "STOP") {
      testingEnabled = false;
      emergencyStop();
      Serial.println(F("\nAll actuators stopped"));
    }
  }
}

// ============================================================================
// ACTUATOR CONTROL FUNCTIONS (From main sketch)
// ============================================================================

void initializeActuators() {
  setFanSpeed(0);
  setHeater(false);
  setPump(false);

  if (!servoAttached) {
    ventServo.attach(VENT_SERVO_PIN);
    servoAttached = true;
    setVentPosition(SERVO_DEFAULT_POS);
  }

  Serial.println(F("Actuators initialized to safe state"));
}

void setFanSpeed(int speed) {
  speed = constrain(speed, FAN_MIN_SPEED, FAN_MAX_SPEED);

  if (speed > 0 && speed < FAN_STARTUP_SPEED) {
    speed = FAN_STARTUP_SPEED;
  }

  fanSpeed = speed;
  analogWrite(FAN_PIN, fanSpeed);
}

void setFanSpeedPercent(float percent) {
  percent = constrain(percent, 0.0, 100.0);
  int pwmValue = map(percent, 0, 100, 0, 255);
  setFanSpeed(pwmValue);
}

void setHeater(bool state) {
  heaterState = state;
  digitalWrite(HEATER_PIN, heaterState ? HIGH : LOW);
}

void setPump(bool state) {
  if (state) {
    // Check if pump has been off long enough
    if (pumpState == false) {
      unsigned long timeSinceOff = millis() - pumpStopTime;
      if (timeSinceOff < PUMP_MIN_OFFTIME && pumpStopTime > 0) {
        Serial.println(F("  WARNING: Pump minimum off time not met"));
        return;
      }
      pumpStartTime = millis();
    }
  } else {
    if (pumpState == true) {
      pumpStopTime = millis();
    }
  }

  pumpState = state;
  digitalWrite(PUMP_PIN, pumpState ? HIGH : LOW);
}

void setVentPosition(int position) {
  position = constrain(position, SERVO_MIN_POS, SERVO_MAX_POS);
  ventPosition = position;
  ventServo.write(ventPosition);
}

void emergencyStop() {
  setFanSpeed(0);
  setHeater(false);
  setPump(false);
  Serial.println(F("EMERGENCY STOP: All actuators deactivated"));
}

// ============================================================================
// TEST FUNCTIONS
// ============================================================================

void runAllTests() {
  testFanControl();
  testHeaterControl();
  testPumpControl();
  testPumpSafetyTimer();
  testServoControl();
  testFanPWMRange();

  printSummary();
}

void testFanControl() {
  printTestHeader("Fan Basic Control");

  Serial.println(F("Testing fan ON/OFF..."));

  // Turn fan on at 50%
  Serial.println(F("  Setting fan to 50%..."));
  setFanSpeedPercent(50.0);
  delay(2000);

  Serial.println(F("  OBSERVE: Is fan spinning?"));
  Serial.print(F("  Current fan PWM: "));
  Serial.println(fanSpeed);

  // Turn fan off
  Serial.println(F("  Turning fan OFF..."));
  setFanSpeed(0);
  delay(2000);

  Serial.println(F("  OBSERVE: Did fan stop?"));

  printTestPass();  // Manual verification
}

void testHeaterControl() {
  printTestHeader("Heater Control");

  Serial.println(F("Testing heater ON/OFF..."));
  Serial.println(F("  WARNING: Ensure heater is in safe location!"));

  // Turn heater on briefly
  Serial.println(F("  Turning heater ON for 3 seconds..."));
  setHeater(true);
  delay(3000);

  Serial.println(F("  OBSERVE: Is heater indicator on?"));

  // Turn heater off
  Serial.println(F("  Turning heater OFF..."));
  setHeater(false);

  Serial.print(F("  Heater state: "));
  Serial.println(heaterState ? "ON" : "OFF");

  printTestPass();
}

void testPumpControl() {
  printTestHeader("Pump Basic Control");

  Serial.println(F("Testing pump ON/OFF..."));
  Serial.println(F("  WARNING: Ensure pump has water supply!"));

  // Turn pump on briefly
  Serial.println(F("  Turning pump ON for 3 seconds..."));
  setPump(true);
  delay(3000);

  Serial.println(F("  OBSERVE: Is pump running? Is water flowing?"));

  // Turn pump off
  Serial.println(F("  Turning pump OFF..."));
  setPump(false);

  Serial.print(F("  Pump state: "));
  Serial.println(pumpState ? "ON" : "OFF");

  printTestPass();
}

void testPumpSafetyTimer() {
  printTestHeader("Pump Safety Timer");

  Serial.println(F("Testing pump minimum off time..."));

  // Try to turn on pump immediately after turning it off
  Serial.println(F("  Turning pump ON..."));
  setPump(true);
  delay(1000);

  Serial.println(F("  Turning pump OFF..."));
  setPump(false);

  Serial.println(F("  Immediately trying to turn pump back ON..."));
  Serial.println(F("  (Should be prevented by safety timer)"));

  setPump(true);  // Should fail or warn

  if (pumpState == false) {
    Serial.println(F("  ✓ Safety timer working - pump activation prevented"));
    printTestPass();
  } else {
    Serial.println(F("  ✗ Safety timer may not be working"));
    printTestFail();
  }

  // Turn off and wait
  setPump(false);
  delay(1000);
}

void testServoControl() {
  printTestHeader("Servo Control (Optional)");

  Serial.println(F("Testing vent servo positioning..."));

  if (!servoAttached) {
    Serial.println(F("  NOTE: Servo not attached"));
    printTestPass();
    return;
  }

  // Test different positions
  Serial.println(F("  Moving to 0° (closed)..."));
  setVentPosition(0);
  delay(1000);

  Serial.println(F("  Moving to 90° (half open)..."));
  setVentPosition(90);
  delay(1000);

  Serial.println(F("  Moving to 180° (fully open)..."));
  setVentPosition(180);
  delay(1000);

  Serial.println(F("  Returning to default position (90°)..."));
  setVentPosition(SERVO_DEFAULT_POS);

  Serial.println(F("  OBSERVE: Did servo move smoothly through positions?"));

  printTestPass();
}

void testFanPWMRange() {
  printTestHeader("Fan PWM Range Test");

  Serial.println(F("Testing fan across full PWM range..."));

  for (int speed = 0; speed <= 100; speed += 25) {
    Serial.print(F("  Setting fan to "));
    Serial.print(speed);
    Serial.println(F("%"));

    setFanSpeedPercent(speed);

    Serial.print(F("    PWM value: "));
    Serial.println(fanSpeed);

    delay(2000);
  }

  Serial.println(F("  OBSERVE: Did fan speed vary smoothly?"));

  // Turn off
  setFanSpeed(0);

  printTestPass();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

void printHeader() {
  Serial.println(F("\n"));
  Serial.println(F("===================================="));
  Serial.println(F("  GREENHOUSE ACTUATOR TEST SUITE   "));
  Serial.println(F("===================================="));
  Serial.println(F(""));
  Serial.println(F("This sketch tests all actuator control"));
  Serial.println(F("functions. Tests require manual observation."));
  Serial.println(F(""));
}

void printSafetyWarning() {
  Serial.println(F(""));
  Serial.println(F("!!!  SAFETY WARNING  !!!"));
  Serial.println(F(""));
  Serial.println(F("This test will activate:"));
  Serial.println(F("- Fan (high speed)"));
  Serial.println(F("- Heater (brief activation)"));
  Serial.println(F("- Water pump (brief activation)"));
  Serial.println(F("- Vent servo (full range)"));
  Serial.println(F(""));
  Serial.println(F("Ensure:"));
  Serial.println(F("1. Pump has water supply"));
  Serial.println(F("2. Heater is safely positioned"));
  Serial.println(F("3. You can stop test quickly if needed"));
  Serial.println(F("4. Area is clear of obstructions"));
  Serial.println(F(""));
}

void printTestHeader(const char* testName) {
  testNumber++;
  Serial.println(F(""));
  Serial.print(F("TEST "));
  Serial.print(testNumber);
  Serial.print(F(": "));
  Serial.println(testName);
  Serial.println(F("------------------------------------"));
}

void printTestPass() {
  Serial.println(F("  ✓ Test completed"));
}

void printTestFail() {
  Serial.println(F("  ✗ Test failed"));
  allTestsPassed = false;
}

void printSummary() {
  Serial.println(F("\n"));
  Serial.println(F("===================================="));
  Serial.println(F("         TEST SUMMARY               "));
  Serial.println(F("===================================="));
  Serial.print(F("Total tests run: "));
  Serial.println(testNumber);

  Serial.println(F("\nTests require manual verification."));
  Serial.println(F("Review observations above to confirm"));
  Serial.println(F("all actuators are working correctly."));

  Serial.println(F("\nAll actuators returned to OFF state."));
  Serial.println(F("\nType 'START' to run tests again"));
  Serial.println(F("Type 'STOP' for emergency stop"));
}
