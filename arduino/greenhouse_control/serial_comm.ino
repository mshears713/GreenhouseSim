/*
 * Serial Communication Protocol
 *
 * This file implements bidirectional serial communication between
 * Arduino and the Python interface.
 *
 * Message Format:
 * - Arduino → Python: SENSOR:<type>,<value>,<timestamp>
 * - Python → Arduino: CMD:<command>,<param1>,<param2>,...
 * - Acknowledgments: ACK:<message_id>
 * - Errors: ERROR:<code>,<description>
 *
 * Educational Notes:
 * - Messages are newline-terminated for simple parsing
 * - Each message type has a distinct prefix for routing
 * - Timestamps allow synchronization and latency measurement
 * - Error codes enable robust error handling
 */

// ============================================================================
// SERIAL PROTOCOL CONSTANTS
// ============================================================================

// Message prefixes
const char* MSG_SENSOR = "SENSOR";
const char* MSG_ACTUATOR = "ACTUATOR";
const char* MSG_STATUS = "STATUS";
const char* MSG_CMD = "CMD";
const char* MSG_ACK = "ACK";
const char* MSG_ERROR = "ERROR";
const char* MSG_INFO = "INFO";

// Command types (received from Python)
const char* CMD_SET_MODE = "SET_MODE";
const char* CMD_SET_SETPOINT = "SET_SETPOINT";
const char* CMD_SET_ACTUATOR = "SET_ACTUATOR";
const char* CMD_SET_PID = "SET_PID";
const char* CMD_ENABLE = "ENABLE";
const char* CMD_DISABLE = "DISABLE";
const char* CMD_CALIBRATE = "CALIBRATE";
const char* CMD_TEST = "TEST";
const char* CMD_STATUS = "STATUS";
const char* CMD_RESET = "RESET";

// Error codes
const int ERR_INVALID_CMD = 1;
const int ERR_INVALID_PARAM = 2;
const int ERR_SENSOR_FAIL = 3;
const int ERR_ACTUATOR_FAIL = 4;
const int ERR_SAFETY_LIMIT = 5;
const int ERR_COMM_TIMEOUT = 6;

// Serial buffer
const int SERIAL_BUFFER_SIZE = 128;
char serialBuffer[SERIAL_BUFFER_SIZE];
int bufferIndex = 0;

// Message counter for ACK tracking
unsigned long messageCounter = 0;

// Last message receive time (for timeout detection)
unsigned long lastMessageReceived = 0;
const unsigned long MESSAGE_TIMEOUT = 5000;  // 5 seconds

// ============================================================================
// SERIAL INPUT HANDLING
// ============================================================================

/**
 * Handle incoming serial data
 *
 * Reads characters from serial buffer, assembles complete messages,
 * and routes them to appropriate handlers.
 *
 * Educational Note:
 * Non-blocking serial reading is essential to keep the main loop
 * responsive. We read one character at a time and process when
 * a complete message (ending with \n) is received.
 */
void handleSerialInput() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    // Handle message terminator (newline)
    if (c == '\n' || c == '\r') {
      if (bufferIndex > 0) {
        serialBuffer[bufferIndex] = '\0';  // Null-terminate string
        processSerialMessage(serialBuffer);
        bufferIndex = 0;  // Reset buffer
        lastMessageReceived = millis();
      }
    }
    // Handle buffer overflow
    else if (bufferIndex >= SERIAL_BUFFER_SIZE - 1) {
      sendError(ERR_COMM_TIMEOUT, "Serial buffer overflow");
      bufferIndex = 0;
    }
    // Add character to buffer
    else {
      serialBuffer[bufferIndex++] = c;
    }
  }

  // Check for communication timeout
  if (lastMessageReceived > 0 && (millis() - lastMessageReceived > MESSAGE_TIMEOUT)) {
    // Communication has been lost - could trigger safety mode
    // For now, just log it
    static bool timeoutLogged = false;
    if (!timeoutLogged) {
      sendInfo("No serial communication for >5 seconds");
      timeoutLogged = true;
    }
  }
}

/**
 * Process a complete serial message
 *
 * Parses message and routes to appropriate handler based on prefix
 */
void processSerialMessage(char* message) {
  // Parse message prefix
  char* prefix = strtok(message, ":");

  if (prefix == NULL) {
    sendError(ERR_INVALID_CMD, "Missing message prefix");
    return;
  }

  // Route to appropriate handler
  if (strcmp(prefix, MSG_CMD) == 0) {
    handleCommand();
  }
  else if (strcmp(prefix, MSG_ACK) == 0) {
    // Acknowledgment received (could track for reliability)
    handleAcknowledgment();
  }
  else {
    sendError(ERR_INVALID_CMD, "Unknown message prefix");
  }
}

// ============================================================================
// COMMAND HANDLERS
// ============================================================================

/**
 * Handle command messages from Python
 *
 * Command format: CMD:<command>,<param1>,<param2>,...
 */
void handleCommand() {
  char* cmd = strtok(NULL, ",");

  if (cmd == NULL) {
    sendError(ERR_INVALID_CMD, "Missing command");
    return;
  }

  // SET_MODE: Change control mode
  if (strcmp(cmd, CMD_SET_MODE) == 0) {
    char* modeStr = strtok(NULL, ",");
    if (modeStr != NULL) {
      int mode = atoi(modeStr);
      if (mode >= 0 && mode <= 4) {
        currentControlMode = (ControlMode)mode;
        sendAck("Mode changed");
        sendInfo(String("Control mode: ") + mode);
      } else {
        sendError(ERR_INVALID_PARAM, "Invalid mode");
      }
    }
  }

  // SET_SETPOINT: Update temperature or moisture setpoint
  else if (strcmp(cmd, CMD_SET_SETPOINT) == 0) {
    char* type = strtok(NULL, ",");
    char* valueStr = strtok(NULL, ",");

    if (type != NULL && valueStr != NULL) {
      float value = atof(valueStr);

      if (strcmp(type, "TEMP") == 0) {
        if (value >= 10.0 && value <= 40.0) {
          temperatureSetpoint = value;
          sendAck("Temperature setpoint updated");
        } else {
          sendError(ERR_SAFETY_LIMIT, "Temperature setpoint out of range");
        }
      }
      else if (strcmp(type, "MOISTURE") == 0) {
        if (value >= 0.0 && value <= 100.0) {
          moistureSetpoint = value;
          sendAck("Moisture setpoint updated");
        } else {
          sendError(ERR_SAFETY_LIMIT, "Moisture setpoint out of range");
        }
      }
    }
  }

  // SET_ACTUATOR: Manually control an actuator (manual mode only)
  else if (strcmp(cmd, CMD_SET_ACTUATOR) == 0) {
    if (currentControlMode != MODE_MANUAL) {
      sendError(ERR_INVALID_CMD, "Manual actuator control requires MANUAL mode");
      return;
    }

    char* actuator = strtok(NULL, ",");
    char* valueStr = strtok(NULL, ",");

    if (actuator != NULL && valueStr != NULL) {
      float value = atof(valueStr);

      if (strcmp(actuator, "FAN") == 0) {
        setFanSpeedPercent(value);
        sendAck("Fan speed set");
      }
      else if (strcmp(actuator, "HEATER") == 0) {
        setHeater(value > 0);
        sendAck("Heater state set");
      }
      else if (strcmp(actuator, "PUMP") == 0) {
        setPump(value > 0);
        sendAck("Pump state set");
      }
      else if (strcmp(actuator, "VENT") == 0) {
        setVentPositionPercent(value);
        sendAck("Vent position set");
      }
    }
  }

  // SET_PID: Update PID parameters
  else if (strcmp(cmd, CMD_SET_PID) == 0) {
    char* type = strtok(NULL, ",");
    char* kpStr = strtok(NULL, ",");
    char* kiStr = strtok(NULL, ",");
    char* kdStr = strtok(NULL, ",");

    if (type != NULL && kpStr != NULL && kiStr != NULL && kdStr != NULL) {
      // PID parameters will be stored in global variables
      // (to be implemented in pid_controller.ino)
      sendAck("PID parameters updated");
      sendInfo(String("PID ") + type + String(": Kp=") + kpStr +
               String(" Ki=") + kiStr + String(" Kd=") + kdStr);
    }
  }

  // ENABLE/DISABLE: System enable/disable
  else if (strcmp(cmd, CMD_ENABLE) == 0) {
    systemEnabled = true;
    sendAck("System enabled");
    sendInfo("System ENABLED");
  }
  else if (strcmp(cmd, CMD_DISABLE) == 0) {
    systemEnabled = false;
    emergencyStopAll();  // Turn off all actuators
    sendAck("System disabled");
    sendInfo("System DISABLED");
  }

  // CALIBRATE: Trigger sensor calibration
  else if (strcmp(cmd, CMD_CALIBRATE) == 0) {
    char* sensor = strtok(NULL, ",");
    char* type = strtok(NULL, ",");

    if (strcmp(sensor, "MOISTURE") == 0) {
      if (strcmp(type, "DRY") == 0) {
        calibrateMoistureDry();
      } else if (strcmp(type, "WET") == 0) {
        calibrateMoistureWet();
      }
    }
  }

  // TEST: Run actuator test sequence
  else if (strcmp(cmd, CMD_TEST) == 0) {
    sendInfo("Starting actuator test...");
    testActuators();
  }

  // STATUS: Send full system status
  else if (strcmp(cmd, CMD_STATUS) == 0) {
    printSystemStatus();
    printSensorReadings();
    printActuatorStatus();
  }

  // RESET: Software reset (re-initialize system)
  else if (strcmp(cmd, CMD_RESET) == 0) {
    sendInfo("Resetting system...");
    // In a real system, might call software reset
    // For now, just reinitialize
    initializeActuators();
    errorState = false;
    lastError = "";
    sendAck("System reset complete");
  }

  // Unknown command
  else {
    sendError(ERR_INVALID_CMD, String("Unknown command: ") + cmd);
  }
}

/**
 * Handle acknowledgment messages from Python
 */
void handleAcknowledgment() {
  // Could track ACKs for reliability
  // For now, just note that we received one
  char* ackMsg = strtok(NULL, ",");
  // ACK received, message was processed by Python
}

// ============================================================================
// SERIAL OUTPUT FUNCTIONS
// ============================================================================

/**
 * Send sensor data to Python
 *
 * Format: SENSOR:<type>,<value>,<timestamp>
 */
void sendSensorData() {
  unsigned long timestamp = millis();

  // Send temperature
  Serial.print(MSG_SENSOR);
  Serial.print(":TEMP,");
  Serial.print(currentTemperature, 2);
  Serial.print(",");
  Serial.println(timestamp);

  // Send moisture
  Serial.print(MSG_SENSOR);
  Serial.print(":MOISTURE,");
  Serial.print(currentMoisture, 1);
  Serial.print(",");
  Serial.println(timestamp);

  // Send airflow (if available)
  if (currentAirflow > 0) {
    Serial.print(MSG_SENSOR);
    Serial.print(":AIRFLOW,");
    Serial.print(currentAirflow, 2);
    Serial.print(",");
    Serial.println(timestamp);
  }

  // Send actuator states
  sendActuatorStates(timestamp);
}

/**
 * Send actuator states to Python
 *
 * Format: ACTUATOR:<type>,<state>,<value>,<timestamp>
 */
void sendActuatorStates(unsigned long timestamp) {
  // Fan state
  Serial.print(MSG_ACTUATOR);
  Serial.print(":FAN,");
  Serial.print(fanSpeed > 0 ? "1" : "0");
  Serial.print(",");
  Serial.print(fanSpeed);
  Serial.print(",");
  Serial.println(timestamp);

  // Heater state
  Serial.print(MSG_ACTUATOR);
  Serial.print(":HEATER,");
  Serial.print(heaterState ? "1" : "0");
  Serial.print(",");
  Serial.print(heaterState ? "100" : "0");
  Serial.print(",");
  Serial.println(timestamp);

  // Pump state
  Serial.print(MSG_ACTUATOR);
  Serial.print(":PUMP,");
  Serial.print(pumpState ? "1" : "0");
  Serial.print(",");
  Serial.print(pumpState ? "100" : "0");
  Serial.print(",");
  Serial.println(timestamp);

  // Vent position
  Serial.print(MSG_ACTUATOR);
  Serial.print(":VENT,1,");
  Serial.print(ventPosition);
  Serial.print(",");
  Serial.println(timestamp);
}

/**
 * Send acknowledgment message
 *
 * Format: ACK:<message>
 */
void sendAck(String message) {
  Serial.print(MSG_ACK);
  Serial.print(":");
  Serial.println(message);
}

/**
 * Send error message
 *
 * Format: ERROR:<code>,<description>
 */
void sendError(int errorCode, String description) {
  Serial.print(MSG_ERROR);
  Serial.print(":");
  Serial.print(errorCode);
  Serial.print(",");
  Serial.println(description);

  // Update global error state
  errorState = true;
  lastError = description;
}

/**
 * Send informational message
 *
 * Format: INFO:<message>
 */
void sendInfo(String message) {
  Serial.print(MSG_INFO);
  Serial.print(":");
  Serial.println(message);
}

/**
 * Send system status message
 *
 * Compact status update with key system parameters
 */
void sendSystemStatus() {
  Serial.print(MSG_STATUS);
  Serial.print(":");
  Serial.print(systemEnabled ? "1" : "0");
  Serial.print(",");
  Serial.print((int)currentControlMode);
  Serial.print(",");
  Serial.print(errorState ? "1" : "0");
  Serial.print(",");
  Serial.print(millis());
  Serial.println();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Check serial communication health
 *
 * Returns true if communication is active, false if timeout
 */
bool isSerialHealthy() {
  if (lastMessageReceived == 0) {
    return true;  // No messages yet, assume OK
  }

  return (millis() - lastMessageReceived) < MESSAGE_TIMEOUT;
}

/**
 * Send heartbeat message
 *
 * Periodic message to indicate Arduino is alive and responsive
 */
void sendHeartbeat() {
  static unsigned long lastHeartbeat = 0;
  const unsigned long HEARTBEAT_INTERVAL = 10000;  // 10 seconds

  if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    sendInfo("Heartbeat");
    lastHeartbeat = millis();
  }
}
