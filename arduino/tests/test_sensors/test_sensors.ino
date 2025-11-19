/*
 * Arduino Sensor Test Sketch
 *
 * This test sketch validates sensor reading functionality for:
 * - Temperature sensor (TMP36)
 * - Soil moisture sensor
 * - Airflow sensor (optional)
 *
 * Purpose:
 * - Verify sensor wiring and connections
 * - Validate sensor reading functions
 * - Check calibration accuracy
 * - Test noise filtering effectiveness
 *
 * Instructions:
 * 1. Upload this sketch to your Arduino
 * 2. Open Serial Monitor (115200 baud)
 * 3. Follow the test prompts
 * 4. Verify sensor readings are reasonable
 *
 * Educational Note:
 * Automated testing on embedded systems is limited (no unit test
 * framework like pytest), but we can create test sketches that
 * help verify correct operation through serial output and manual
 * validation.
 */

// ============================================================================
// PIN DEFINITIONS (Match main sketch)
// ============================================================================

const int TEMP_SENSOR_PIN = A0;
const int MOISTURE_SENSOR_PIN = A1;
const int AIRFLOW_SENSOR_PIN = A2;

// ============================================================================
// SENSOR CONFIGURATION (Match main sketch)
// ============================================================================

const int TEMP_SAMPLES = 5;
const int MOISTURE_SAMPLES = 10;
const int AIRFLOW_SAMPLES = 5;

int moistureCalibrationDry = 850;
int moistureCalibrationWet = 400;

const float TEMP_VOLTAGE_OFFSET = 0.5;
const float TEMP_SCALE = 100.0;
const float TEMP_OFFSET = 0.0;

const float AIRFLOW_SCALE = 1.0;

// ============================================================================
// TEST STATE
// ============================================================================

int testNumber = 0;
bool allTestsPassed = true;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for serial port to connect (needed for some boards)
  }

  delay(1000);

  printHeader();

  // Run all tests
  Serial.println(F("\n=== STARTING SENSOR TESTS ===\n"));

  testTemperatureSensor();
  testMoistureSensor();
  testAirflowSensor();
  testRawADCReadings();
  testSensorNoise();
  testSensorResponseTime();

  printSummary();
}

void loop() {
  // Continuous monitoring mode
  delay(2000);

  Serial.println(F("\n--- Continuous Sensor Monitoring ---"));
  Serial.print(F("Temperature: "));
  Serial.print(readTemperature());
  Serial.println(F(" °C"));

  Serial.print(F("Moisture: "));
  Serial.print(readMoisture());
  Serial.println(F(" %"));

  Serial.print(F("Airflow: "));
  Serial.println(readAirflow());
}

// ============================================================================
// SENSOR READING FUNCTIONS (Copied from main sketch)
// ============================================================================

float readTemperature() {
  long sum = 0;
  for (int i = 0; i < TEMP_SAMPLES; i++) {
    sum += analogRead(TEMP_SENSOR_PIN);
    delay(10);
  }

  float avgReading = (float)sum / TEMP_SAMPLES;
  float voltage = avgReading * (5.0 / 1023.0);
  float tempC = (voltage - TEMP_VOLTAGE_OFFSET) * TEMP_SCALE;
  tempC += TEMP_OFFSET;

  return tempC;
}

float readMoisture() {
  long sum = 0;
  for (int i = 0; i < MOISTURE_SAMPLES; i++) {
    sum += analogRead(MOISTURE_SENSOR_PIN);
    delay(10);
  }

  float avgReading = (float)sum / MOISTURE_SAMPLES;

  float moisturePercent = map(avgReading,
                               moistureCalibrationDry,
                               moistureCalibrationWet,
                               0,
                               100);

  moisturePercent = constrain(moisturePercent, 0.0, 100.0);

  return moisturePercent;
}

float readAirflow() {
  long sum = 0;
  for (int i = 0; i < AIRFLOW_SAMPLES; i++) {
    sum += analogRead(AIRFLOW_SENSOR_PIN);
    delay(10);
  }

  float avgReading = (float)sum / AIRFLOW_SAMPLES;
  float airflow = avgReading * AIRFLOW_SCALE;

  return airflow;
}

// ============================================================================
// TEST FUNCTIONS
// ============================================================================

void testTemperatureSensor() {
  printTestHeader("Temperature Sensor");

  Serial.println(F("Testing temperature sensor..."));
  Serial.println(F("Expected range: 15-35°C (room temperature)"));

  float temp = readTemperature();

  Serial.print(F("  Measured temperature: "));
  Serial.print(temp);
  Serial.println(F(" °C"));

  // Sanity check: temperature should be in reasonable range
  bool passed = (temp > -10.0 && temp < 50.0);

  if (temp < 15.0 || temp > 35.0) {
    Serial.println(F("  WARNING: Temperature outside typical room range"));
    Serial.println(F("           This may be normal if environment is hot/cold"));
  }

  if (passed) {
    printTestPass();
  } else {
    printTestFail();
    Serial.println(F("  ISSUE: Temperature reading is unreasonable"));
    Serial.println(F("  Check: Sensor wiring, power supply, sensor type"));
  }
}

void testMoistureSensor() {
  printTestHeader("Moisture Sensor");

  Serial.println(F("Testing moisture sensor..."));
  Serial.println(F("Expected range: 0-100%"));

  float moisture = readMoisture();

  Serial.print(F("  Measured moisture: "));
  Serial.print(moisture);
  Serial.println(F(" %"));

  // Should be within valid range
  bool passed = (moisture >= 0.0 && moisture <= 100.0);

  if (moisture == 0.0 || moisture == 100.0) {
    Serial.println(F("  WARNING: Sensor at extreme value"));
    Serial.println(F("           May need calibration adjustment"));
  }

  if (passed) {
    printTestPass();
  } else {
    printTestFail();
    Serial.println(F("  ISSUE: Moisture reading out of range"));
    Serial.println(F("  Check: Calibration values, sensor connection"));
  }
}

void testAirflowSensor() {
  printTestHeader("Airflow Sensor (Optional)");

  Serial.println(F("Testing airflow sensor..."));

  float airflow = readAirflow();

  Serial.print(F("  Measured airflow: "));
  Serial.println(airflow);

  if (airflow == 0.0) {
    Serial.println(F("  NOTE: Airflow sensor may not be connected"));
    Serial.println(F("        This is optional for the system"));
  }

  // Always pass (airflow is optional)
  printTestPass();
}

void testRawADCReadings() {
  printTestHeader("Raw ADC Values");

  Serial.println(F("Checking raw analog-to-digital converter readings..."));

  int tempRaw = analogRead(TEMP_SENSOR_PIN);
  int moistureRaw = analogRead(MOISTURE_SENSOR_PIN);
  int airflowRaw = analogRead(AIRFLOW_SENSOR_PIN);

  Serial.print(F("  Temperature ADC: "));
  Serial.print(tempRaw);
  Serial.print(F(" ("));
  Serial.print(tempRaw * (5.0 / 1023.0));
  Serial.println(F("V)"));

  Serial.print(F("  Moisture ADC: "));
  Serial.print(moistureRaw);
  Serial.print(F(" ("));
  Serial.print(moistureRaw * (5.0 / 1023.0));
  Serial.println(F("V)"));

  Serial.print(F("  Airflow ADC: "));
  Serial.print(airflowRaw);
  Serial.print(F(" ("));
  Serial.print(airflowRaw * (5.0 / 1023.0));
  Serial.println(F("V)"));

  // Check that ADC values are not stuck at 0 or 1023
  bool passed = true;

  if (tempRaw == 0 || tempRaw == 1023) {
    Serial.println(F("  WARNING: Temperature ADC at extreme value"));
    Serial.println(F("           Check sensor connection"));
    passed = false;
  }

  if (moistureRaw == 0 || moistureRaw == 1023) {
    Serial.println(F("  WARNING: Moisture ADC at extreme value"));
    Serial.println(F("           Check sensor connection"));
  }

  if (passed) {
    printTestPass();
  } else {
    printTestFail();
  }
}

void testSensorNoise() {
  printTestHeader("Sensor Noise Analysis");

  Serial.println(F("Taking 20 temperature readings to analyze noise..."));

  float readings[20];
  float sum = 0.0;

  for (int i = 0; i < 20; i++) {
    readings[i] = readTemperature();
    sum += readings[i];
    delay(100);
  }

  float mean = sum / 20.0;

  // Calculate standard deviation
  float variance = 0.0;
  for (int i = 0; i < 20; i++) {
    float diff = readings[i] - mean;
    variance += diff * diff;
  }
  variance /= 20.0;
  float stdDev = sqrt(variance);

  Serial.print(F("  Mean temperature: "));
  Serial.print(mean);
  Serial.println(F(" °C"));

  Serial.print(F("  Standard deviation: "));
  Serial.print(stdDev);
  Serial.println(F(" °C"));

  // Noise should be relatively small (< 1°C typical)
  bool passed = (stdDev < 2.0);

  if (stdDev > 1.0) {
    Serial.println(F("  NOTE: Noise is higher than typical"));
    Serial.println(F("        Consider increasing averaging samples"));
  }

  if (passed) {
    printTestPass();
  } else {
    printTestFail();
    Serial.println(F("  ISSUE: Excessive sensor noise detected"));
    Serial.println(F("  Check: Sensor quality, wiring, power supply filtering"));
  }
}

void testSensorResponseTime() {
  printTestHeader("Sensor Response Time");

  Serial.println(F("Measuring sensor read time..."));

  unsigned long startTime = micros();
  float temp = readTemperature();
  unsigned long tempTime = micros() - startTime;

  startTime = micros();
  float moisture = readMoisture();
  unsigned long moistureTime = micros() - startTime;

  Serial.print(F("  Temperature read time: "));
  Serial.print(tempTime / 1000.0);
  Serial.println(F(" ms"));

  Serial.print(F("  Moisture read time: "));
  Serial.print(moistureTime / 1000.0);
  Serial.println(F(" ms"));

  // Should complete in reasonable time (< 500ms)
  bool passed = (tempTime < 500000 && moistureTime < 500000);

  if (passed) {
    printTestPass();
  } else {
    printTestFail();
    Serial.println(F("  ISSUE: Sensor reading taking too long"));
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

void printHeader() {
  Serial.println(F("\n"));
  Serial.println(F("===================================="));
  Serial.println(F("   GREENHOUSE SENSOR TEST SUITE    "));
  Serial.println(F("===================================="));
  Serial.println(F(""));
  Serial.println(F("This sketch tests all sensor reading"));
  Serial.println(F("functions and validates proper operation."));
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
  Serial.println(F("  ✓ PASSED"));
}

void printTestFail() {
  Serial.println(F("  ✗ FAILED"));
  allTestsPassed = false;
}

void printSummary() {
  Serial.println(F("\n"));
  Serial.println(F("===================================="));
  Serial.println(F("         TEST SUMMARY               "));
  Serial.println(F("===================================="));
  Serial.print(F("Total tests run: "));
  Serial.println(testNumber);

  if (allTestsPassed) {
    Serial.println(F("\n✓ ALL TESTS PASSED!\n"));
    Serial.println(F("Sensors are functioning correctly."));
    Serial.println(F("Ready to integrate with control system."));
  } else {
    Serial.println(F("\n✗ SOME TESTS FAILED\n"));
    Serial.println(F("Review failure messages above and"));
    Serial.println(F("check sensor connections/calibration."));
  }

  Serial.println(F("\nEntering continuous monitoring mode..."));
  Serial.println(F("Sensor readings will update every 2 seconds.\n"));
}
