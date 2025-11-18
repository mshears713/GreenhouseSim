/*
 * Sensor Reading Functions
 *
 * This file contains all sensor reading and processing functions
 * for the greenhouse control system.
 *
 * Sensors:
 * - Temperature (TMP36 on A0)
 * - Soil Moisture (Capacitive/Resistive on A1)
 * - Airflow (Optional on A2)
 *
 * Educational Notes:
 * - Raw sensor values are converted to meaningful units (°C, %, etc.)
 * - Simple filtering is applied to reduce noise
 * - Calibration constants allow for sensor-specific adjustments
 */

// ============================================================================
// SENSOR CONFIGURATION
// ============================================================================

// Number of samples for averaging (noise reduction)
const int TEMP_SAMPLES = 5;
const int MOISTURE_SAMPLES = 10;  // Moisture sensors tend to be noisier
const int AIRFLOW_SAMPLES = 5;

// Moisture sensor calibration (to be determined during setup)
// These values map the raw analog reading to percentage
int moistureCalibrationDry = 850;   // Analog reading in completely dry soil
int moistureCalibrationWet = 400;   // Analog reading in saturated soil

// Temperature sensor calibration
const float TEMP_VOLTAGE_OFFSET = 0.5;  // TMP36 has 500mV offset
const float TEMP_SCALE = 100.0;         // 10mV/°C = 100°C per volt

// Airflow sensor calibration (sensor-dependent)
const float AIRFLOW_SCALE = 1.0;  // Placeholder, depends on sensor type

// ============================================================================
// SENSOR READING FUNCTIONS
// ============================================================================

/**
 * Read all sensors and update global variables
 *
 * This is the main function called from the main loop to update
 * all sensor readings. It applies filtering and calibration.
 *
 * Educational Note:
 * This function demonstrates how to organize sensor reading in a
 * structured way, making the main loop clean and readable.
 */
void readSensors() {
  currentTemperature = readTemperature();
  currentMoisture = readMoisture();
  currentAirflow = readAirflow();

  // Optional: Add sensor validation here
  validateSensorReadings();
}

/**
 * Read temperature from TMP36 sensor
 *
 * Returns: Temperature in degrees Celsius
 *
 * TMP36 Conversion:
 * - Output voltage = 10mV per degree C
 * - 500mV offset (0°C = 500mV, 25°C = 750mV)
 * - Formula: Temp(°C) = (Voltage - 0.5V) × 100
 *
 * Educational Note:
 * Analog sensors require conversion from ADC counts (0-1023)
 * to voltage (0-5V), then to the physical quantity (temperature).
 */
float readTemperature() {
  // Take multiple samples for averaging (reduces noise)
  long sum = 0;
  for (int i = 0; i < TEMP_SAMPLES; i++) {
    sum += analogRead(TEMP_SENSOR_PIN);
    delay(10);  // Small delay between readings
  }

  // Calculate average ADC reading
  float avgReading = (float)sum / TEMP_SAMPLES;

  // Convert ADC reading (0-1023) to voltage (0-5V)
  // ADC is 10-bit: 1024 steps over 5V range
  float voltage = avgReading * (5.0 / 1023.0);

  // Convert voltage to temperature using TMP36 formula
  float tempC = (voltage - TEMP_VOLTAGE_OFFSET) * TEMP_SCALE;

  // Apply calibration offset if needed
  tempC += TEMP_OFFSET;

  return tempC;
}

/**
 * Read soil moisture sensor
 *
 * Returns: Moisture percentage (0-100%)
 *
 * Moisture Sensor Types:
 * - Capacitive: Higher reading = wetter (recommended)
 * - Resistive: Lower reading = wetter (less reliable)
 *
 * Educational Note:
 * Moisture sensors need calibration! The raw readings vary by
 * sensor type, soil composition, and placement. Always calibrate
 * with known dry and wet samples.
 */
float readMoisture() {
  // Take multiple samples for averaging (moisture sensors are noisy)
  long sum = 0;
  for (int i = 0; i < MOISTURE_SAMPLES; i++) {
    sum += analogRead(MOISTURE_SENSOR_PIN);
    delay(10);
  }

  // Calculate average ADC reading
  float avgReading = (float)sum / MOISTURE_SAMPLES;

  // Convert to percentage using calibration values
  // map() function: map(value, fromLow, fromHigh, toLow, toHigh)
  // For capacitive sensors: higher reading = drier (inverse relationship)
  float moisturePercent = map(avgReading,
                               moistureCalibrationDry,  // Dry (high reading)
                               moistureCalibrationWet,  // Wet (low reading)
                               0,                        // 0% moisture
                               100);                     // 100% moisture

  // Constrain to valid range (prevent values outside 0-100%)
  moisturePercent = constrain(moisturePercent, 0.0, 100.0);

  return moisturePercent;
}

/**
 * Read airflow sensor (optional)
 *
 * Returns: Airflow in arbitrary units (sensor-dependent)
 *
 * Educational Note:
 * Airflow sensors vary widely in type and output. This is a
 * generic implementation that may need adjustment based on
 * the specific sensor used. Common types include:
 * - Hot-wire anemometers (analog voltage output)
 * - Rotating anemometers (digital pulse counting)
 * - Differential pressure sensors
 */
float readAirflow() {
  // Check if airflow sensor is connected (optional sensor)
  // If reading is 0 or very low, sensor may not be present
  int testReading = analogRead(AIRFLOW_SENSOR_PIN);
  if (testReading < 5) {
    return 0.0;  // No sensor connected
  }

  // Take multiple samples for averaging
  long sum = 0;
  for (int i = 0; i < AIRFLOW_SAMPLES; i++) {
    sum += analogRead(AIRFLOW_SENSOR_PIN);
    delay(10);
  }

  // Calculate average ADC reading
  float avgReading = (float)sum / AIRFLOW_SAMPLES;

  // Convert to voltage
  float voltage = avgReading * (5.0 / 1023.0);

  // Convert to airflow units (sensor-specific)
  // This is a placeholder - adjust based on actual sensor
  float airflow = voltage * AIRFLOW_SCALE;

  return airflow;
}

// ============================================================================
// SENSOR VALIDATION AND ERROR DETECTION
// ============================================================================

/**
 * Validate sensor readings for plausibility
 *
 * This function checks if sensor readings are within expected ranges
 * and sets error flags if readings seem impossible or sensor failure
 * is detected.
 *
 * Educational Note:
 * Always validate sensor data! Sensors can fail, connections can
 * become loose, and readings can be affected by interference.
 * Detecting bad data early prevents poor control decisions.
 */
void validateSensorReadings() {
  bool hasError = false;
  String errorMsg = "";

  // Temperature validation
  // Reasonable range: -10°C to 60°C (greenhouse shouldn't exceed this)
  if (currentTemperature < -10.0 || currentTemperature > 60.0) {
    hasError = true;
    errorMsg += "TEMP_RANGE;";
  }

  // Check for stuck temperature reading (may indicate sensor failure)
  static float lastTemp = 0;
  static int tempUnchangedCount = 0;
  if (abs(currentTemperature - lastTemp) < 0.01) {
    tempUnchangedCount++;
    if (tempUnchangedCount > 30) {  // Unchanged for 30 readings
      hasError = true;
      errorMsg += "TEMP_STUCK;";
    }
  } else {
    tempUnchangedCount = 0;
  }
  lastTemp = currentTemperature;

  // Moisture validation
  // Range already constrained in readMoisture(), but check for sensor issues
  int rawMoisture = analogRead(MOISTURE_SENSOR_PIN);
  if (rawMoisture < 10 || rawMoisture > 1010) {
    hasError = true;
    errorMsg += "MOISTURE_FAULT;";
  }

  // Update global error state
  if (hasError) {
    errorState = true;
    lastError = errorMsg;

    // Print error to serial for debugging
    Serial.print(F("ERROR: Sensor validation failed: "));
    Serial.println(errorMsg);
  } else {
    // Clear error if readings are now valid
    if (errorState && lastError.startsWith("TEMP") || lastError.startsWith("MOISTURE")) {
      errorState = false;
      lastError = "";
      Serial.println(F("INFO: Sensor errors cleared"));
    }
  }
}

// ============================================================================
// SENSOR CALIBRATION FUNCTIONS
// ============================================================================

/**
 * Calibrate moisture sensor
 *
 * This function should be called during setup to calibrate the moisture
 * sensor with dry and wet samples. Can be triggered via serial command.
 *
 * Calibration Procedure:
 * 1. Place sensor in completely dry soil, call calibrateMoistureDry()
 * 2. Place sensor in saturated soil, call calibrateMoistureWet()
 * 3. Values are stored and used for future conversions
 *
 * Educational Note:
 * Calibration is essential for accurate sensor readings. Each sensor
 * is slightly different, and environmental factors (soil type, temperature)
 * can affect readings.
 */
void calibrateMoistureDry() {
  Serial.println(F("Calibrating moisture sensor - DRY sample"));
  Serial.println(F("Ensure sensor is in completely dry soil..."));
  delay(2000);

  // Take several readings for accuracy
  long sum = 0;
  const int samples = 20;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(MOISTURE_SENSOR_PIN);
    delay(100);
    Serial.print(F("."));
  }
  Serial.println();

  moistureCalibrationDry = sum / samples;

  Serial.print(F("Dry calibration value: "));
  Serial.println(moistureCalibrationDry);
  Serial.println(F("Calibration complete!"));
}

void calibrateMoistureWet() {
  Serial.println(F("Calibrating moisture sensor - WET sample"));
  Serial.println(F("Ensure sensor is in saturated soil..."));
  delay(2000);

  // Take several readings for accuracy
  long sum = 0;
  const int samples = 20;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(MOISTURE_SENSOR_PIN);
    delay(100);
    Serial.print(F("."));
  }
  Serial.println();

  moistureCalibrationWet = sum / samples;

  Serial.print(F("Wet calibration value: "));
  Serial.println(moistureCalibrationWet);
  Serial.println(F("Calibration complete!"));
}

/**
 * Print current sensor readings to serial
 *
 * Useful for debugging and manual verification of sensor operation
 */
void printSensorReadings() {
  Serial.println(F("=== Current Sensor Readings ==="));

  Serial.print(F("Temperature: "));
  Serial.print(currentTemperature, 2);
  Serial.println(F(" °C"));

  Serial.print(F("Soil Moisture: "));
  Serial.print(currentMoisture, 1);
  Serial.println(F(" %"));

  Serial.print(F("Airflow: "));
  Serial.print(currentAirflow, 2);
  Serial.println(F(" (units)"));

  // Also print raw values for debugging
  Serial.print(F("Raw ADC - Temp: "));
  Serial.print(analogRead(TEMP_SENSOR_PIN));
  Serial.print(F(", Moisture: "));
  Serial.print(analogRead(MOISTURE_SENSOR_PIN));
  Serial.print(F(", Airflow: "));
  Serial.println(analogRead(AIRFLOW_SENSOR_PIN));

  Serial.println(F("=============================="));
  Serial.println();
}
