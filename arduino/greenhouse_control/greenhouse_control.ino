/*
 * Smart Mini Greenhouse Control System - Main Sketch
 *
 * This is the main Arduino firmware for the greenhouse control system.
 * It manages sensors, actuators, and implements layered control strategies.
 *
 * Hardware Connections:
 * - Temperature Sensor (TMP36): A0
 * - Soil Moisture Sensor: A1
 * - Airflow Sensor (Optional): A2
 * - Fan Control (PWM): Pin 9
 * - Heater Control: Pin 10
 * - Pump Control: Pin 11
 * - Vent Servo (Optional): Pin 6
 * - Status LED: Pin 13 (built-in)
 *
 * Communication:
 * - Serial USB at 9600 baud for Python communication
 *
 * Educational Note:
 * This firmware demonstrates layered control strategies from simple
 * open-loop to sophisticated PID control. Each layer builds upon
 * previous concepts to enhance system stability and responsiveness.
 */

// ============================================================================
// PIN DEFINITIONS
// ============================================================================

// Analog Input Pins (Sensors)
const int TEMP_SENSOR_PIN = A0;      // TMP36 temperature sensor
const int MOISTURE_SENSOR_PIN = A1;  // Capacitive or resistive soil moisture sensor
const int AIRFLOW_SENSOR_PIN = A2;   // Optional airflow/anemometer sensor

// Digital Output Pins (Actuators)
const int FAN_PIN = 9;              // PWM-capable pin for fan speed control
const int HEATER_PIN = 10;          // Digital or PWM for heater control
const int PUMP_PIN = 11;            // Water pump control
const int VENT_SERVO_PIN = 6;       // Servo for vent control (optional)
const int STATUS_LED_PIN = 13;      // Built-in LED for status indication

// ============================================================================
// GLOBAL CONSTANTS
// ============================================================================

// Serial Communication
const long BAUD_RATE = 9600;        // Serial communication speed
const int SERIAL_TIMEOUT = 2000;    // Serial timeout in milliseconds

// Timing Constants
const unsigned long SENSOR_READ_INTERVAL = 1000;  // Read sensors every 1 second
const unsigned long CONTROL_UPDATE_INTERVAL = 500; // Update control every 0.5 seconds
const unsigned long SERIAL_SEND_INTERVAL = 1000;   // Send data every 1 second

// Sensor Calibration (will be refined during testing)
const float TEMP_OFFSET = 0.0;      // Temperature calibration offset in °C
const float MOISTURE_MIN = 0.0;     // Moisture sensor minimum (dry)
const float MOISTURE_MAX = 100.0;   // Moisture sensor maximum (wet)

// Control Thresholds (default values - will be tunable via serial)
const float DEFAULT_TEMP_SETPOINT = 24.0;     // Target temperature in °C
const float DEFAULT_MOISTURE_SETPOINT = 50.0; // Target moisture in %

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

// Sensor Readings (current values)
float currentTemperature = 0.0;     // Current temperature in °C
float currentMoisture = 0.0;        // Current soil moisture in %
float currentAirflow = 0.0;         // Current airflow (arbitrary units)

// Actuator States
int fanSpeed = 0;                   // Fan speed: 0-255 (PWM)
bool heaterState = false;           // Heater on/off
bool pumpState = false;             // Pump on/off
int ventPosition = 0;               // Vent servo position: 0-180 degrees

// Control Setpoints (can be updated via serial)
float temperatureSetpoint = DEFAULT_TEMP_SETPOINT;
float moistureSetpoint = DEFAULT_MOISTURE_SETPOINT;

// Control Mode Selection
enum ControlMode {
  MODE_MANUAL = 0,        // Manual control via serial commands
  MODE_OPEN_LOOP = 1,     // Simple threshold-based control
  MODE_CLOSED_LOOP = 2,   // Feedback control with error correction
  MODE_FEEDFORWARD = 3,   // Anticipatory control (advanced)
  MODE_PID = 4            // Full PID control (most advanced)
};
ControlMode currentControlMode = MODE_MANUAL;

// Timing Variables
unsigned long lastSensorRead = 0;
unsigned long lastControlUpdate = 0;
unsigned long lastSerialSend = 0;
unsigned long currentTime = 0;

// System Status
bool systemEnabled = true;          // Master enable/disable
bool errorState = false;            // Error flag
String lastError = "";              // Last error message

// ============================================================================
// SETUP FUNCTION
// ============================================================================

void setup() {
  // Initialize Serial Communication
  Serial.begin(BAUD_RATE);
  Serial.setTimeout(SERIAL_TIMEOUT);

  // Wait for serial port to connect (useful for debugging)
  while (!Serial && millis() < 3000) {
    ; // Wait up to 3 seconds for serial connection
  }

  // Print startup message
  Serial.println(F("==========================================="));
  Serial.println(F("Smart Mini Greenhouse Control System v1.0"));
  Serial.println(F("==========================================="));
  Serial.println(F("Initializing hardware..."));

  // Configure Sensor Pins
  pinMode(TEMP_SENSOR_PIN, INPUT);
  pinMode(MOISTURE_SENSOR_PIN, INPUT);
  pinMode(AIRFLOW_SENSOR_PIN, INPUT);

  // Configure Actuator Pins
  pinMode(FAN_PIN, OUTPUT);
  pinMode(HEATER_PIN, OUTPUT);
  pinMode(PUMP_PIN, OUTPUT);
  pinMode(VENT_SERVO_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);

  // Initialize Actuators to Safe State (all off)
  analogWrite(FAN_PIN, 0);        // Fan off
  digitalWrite(HEATER_PIN, LOW);  // Heater off
  digitalWrite(PUMP_PIN, LOW);    // Pump off
  digitalWrite(STATUS_LED_PIN, HIGH); // LED on = system ready

  // Initial sensor reading
  readSensors();

  Serial.println(F("Hardware initialized successfully!"));
  Serial.println(F("System ready. Awaiting commands..."));
  Serial.println();

  // Print initial status
  printSystemStatus();
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Update current time
  currentTime = millis();

  // Handle incoming serial commands (non-blocking)
  if (Serial.available() > 0) {
    handleSerialInput();
  }

  // Read sensors at specified interval
  if (currentTime - lastSensorRead >= SENSOR_READ_INTERVAL) {
    readSensors();
    lastSensorRead = currentTime;
  }

  // Update control system at specified interval
  if (currentTime - lastControlUpdate >= CONTROL_UPDATE_INTERVAL) {
    if (systemEnabled) {
      updateControlSystem();
    }
    lastControlUpdate = currentTime;
  }

  // Send data via serial at specified interval
  if (currentTime - lastSerialSend >= SERIAL_SEND_INTERVAL) {
    sendSensorData();
    lastSerialSend = currentTime;
  }

  // Blink status LED to indicate system is running
  blinkStatusLED();
}

// ============================================================================
// HELPER FUNCTIONS (Placeholders - will be implemented in separate files)
// ============================================================================

// Placeholder for sensor reading function
void readSensors() {
  // Will be implemented in sensors.ino
  // For now, just indicate function was called
}

// Placeholder for control system update
void updateControlSystem() {
  // Will be implemented in control_layers.ino
  // This is where different control strategies will be applied
}

// Placeholder for serial input handling
void handleSerialInput() {
  // Will be implemented in serial_comm.ino
  // Handles commands from Python interface
}

// Placeholder for sending sensor data
void sendSensorData() {
  // Will be implemented in serial_comm.ino
  // Sends current state to Python interface
}

// Status LED blink function
void blinkStatusLED() {
  // Simple heartbeat blink every 2 seconds
  static unsigned long lastBlink = 0;
  static bool ledState = false;

  if (currentTime - lastBlink >= 2000) {
    ledState = !ledState;
    digitalWrite(STATUS_LED_PIN, ledState ? HIGH : LOW);
    lastBlink = currentTime;
  }
}

// Print system status to serial (for debugging)
void printSystemStatus() {
  Serial.println(F("--- System Status ---"));
  Serial.print(F("Control Mode: "));
  Serial.println(currentControlMode);
  Serial.print(F("System Enabled: "));
  Serial.println(systemEnabled ? F("Yes") : F("No"));
  Serial.print(F("Temperature Setpoint: "));
  Serial.print(temperatureSetpoint);
  Serial.println(F(" °C"));
  Serial.print(F("Moisture Setpoint: "));
  Serial.print(moistureSetpoint);
  Serial.println(F(" %"));
  Serial.println(F("--------------------"));
  Serial.println();
}
