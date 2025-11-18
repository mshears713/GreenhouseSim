/*
 * PID Controller Implementation
 *
 * Dedicated PID controller module for temperature and moisture regulation.
 * This file contains a reusable PID controller class that can be applied
 * to any control variable.
 *
 * Educational Notes:
 * PID (Proportional-Integral-Derivative) control is the most widely used
 * control algorithm in industrial applications. Understanding PID is
 * essential for embedded control systems.
 *
 * PID Formula:
 * output = Kp * error + Ki * integral(error) + Kd * derivative(error)
 *
 * Where:
 * - Kp (Proportional gain): Immediate response to current error
 * - Ki (Integral gain): Eliminates steady-state offset
 * - Kd (Derivative gain): Dampens oscillations, predicts future error
 */

// ============================================================================
// PID CONTROLLER STRUCTURE
// ============================================================================

/**
 * PID Controller structure
 *
 * Encapsulates all state and parameters for a single PID controller
 *
 * Educational Note:
 * Using a struct allows multiple independent PID controllers
 * (e.g., one for temperature, one for moisture) with separate tuning.
 */
struct PIDController {
  // Tuning parameters (gains)
  float Kp;  // Proportional gain
  float Ki;  // Integral gain
  float Kd;  // Derivative gain

  // Controller state
  float integral;        // Accumulated error (for I term)
  float previousError;   // Last error value (for D term)
  float previousOutput;  // Last output value

  // Output limits
  float outputMin;
  float outputMax;

  // Integral anti-windup limits
  float integralMin;
  float integralMax;

  // Deadband (optional - prevents oscillation near setpoint)
  float deadband;

  // Derivative filter coefficient (0-1, higher = more filtering)
  float derivativeFilter;
  float filteredDerivative;

  // Timing
  unsigned long lastUpdateTime;

  // Enable/disable integral and derivative terms
  bool enableIntegral;
  bool enableDerivative;
};

// Global PID controllers
PIDController tempPID;
PIDController moisturePID;

// ============================================================================
// PID INITIALIZATION
// ============================================================================

/**
 * Initialize a PID controller with default parameters
 *
 * Educational Note:
 * Always initialize PID controllers before use. Starting with
 * conservative gains (small Kp, Ki, Kd) prevents unstable behavior.
 */
void initPID(PIDController* pid, float kp, float ki, float kd) {
  pid->Kp = kp;
  pid->Ki = ki;
  pid->Kd = kd;

  pid->integral = 0.0;
  pid->previousError = 0.0;
  pid->previousOutput = 0.0;

  pid->outputMin = -100.0;
  pid->outputMax = 100.0;

  pid->integralMin = -50.0;
  pid->integralMax = 50.0;

  pid->deadband = 0.0;

  pid->derivativeFilter = 0.0;  // No filtering by default
  pid->filteredDerivative = 0.0;

  pid->lastUpdateTime = millis();

  pid->enableIntegral = true;
  pid->enableDerivative = true;
}

/**
 * Initialize temperature PID controller
 *
 * Starting parameters based on typical greenhouse thermal response:
 * - Kp: 1.0 (moderate proportional response)
 * - Ki: 0.1 (slow integral action to eliminate offset)
 * - Kd: 0.05 (light derivative to dampen overshoot)
 */
void initTemperaturePID() {
  initPID(&tempPID, 1.0, 0.1, 0.05);

  tempPID.outputMin = -100.0;  // -100 = full cooling
  tempPID.outputMax = 100.0;   // +100 = full heating

  tempPID.deadband = 0.2;  // ±0.2°C deadband to prevent oscillation

  tempPID.derivativeFilter = 0.3;  // Light filtering on derivative

  sendInfo("Temperature PID initialized: Kp=1.0, Ki=0.1, Kd=0.05");
}

/**
 * Initialize moisture PID controller
 *
 * Moisture control is slower than temperature, so we use:
 * - Lower gains (system has more inertia)
 * - Larger deadband (moisture sensors are noisier)
 */
void initMoisturePID() {
  initPID(&moisturePID, 0.8, 0.05, 0.02);

  moisturePID.outputMin = 0.0;    // Can't "remove" water
  moisturePID.outputMax = 100.0;  // Full watering

  moisturePID.deadband = 2.0;  // ±2% deadband

  moisturePID.derivativeFilter = 0.5;  // More filtering (noisy sensor)

  sendInfo("Moisture PID initialized: Kp=0.8, Ki=0.05, Kd=0.02");
}

// ============================================================================
// PID COMPUTATION
// ============================================================================

/**
 * Compute PID output
 *
 * This is the core PID algorithm implementation
 *
 * Args:
 *   pid: Pointer to PID controller structure
 *   setpoint: Desired value
 *   measurement: Current measured value
 *
 * Returns:
 *   Control output (within outputMin to outputMax range)
 *
 * Educational Note:
 * This function should be called at regular intervals (e.g., every 100ms).
 * Irregular timing will cause incorrect integral and derivative calculations.
 */
float computePID(PIDController* pid, float setpoint, float measurement) {
  unsigned long now = millis();
  float dt = (now - pid->lastUpdateTime) / 1000.0;  // Convert to seconds
  pid->lastUpdateTime = now;

  // Ensure reasonable time step
  if (dt <= 0.0 || dt > 10.0) {
    dt = 0.1;  // Default to 100ms if timing is weird
  }

  // Calculate error
  float error = setpoint - measurement;

  // Apply deadband to prevent oscillation near setpoint
  if (abs(error) < pid->deadband) {
    error = 0.0;
  }

  // ========== PROPORTIONAL TERM ==========
  // Responds immediately to current error
  float pTerm = pid->Kp * error;

  // ========== INTEGRAL TERM ==========
  // Accumulates error over time to eliminate steady-state offset
  float iTerm = 0.0;
  if (pid->enableIntegral) {
    pid->integral += error * dt;

    // Anti-windup: constrain integral to prevent runaway
    pid->integral = constrain(pid->integral, pid->integralMin, pid->integralMax);

    iTerm = pid->Ki * pid->integral;
  }

  // ========== DERIVATIVE TERM ==========
  // Responds to rate of change to dampen oscillations
  float dTerm = 0.0;
  if (pid->enableDerivative) {
    // Calculate derivative (rate of change of error)
    float derivative = (error - pid->previousError) / dt;

    // Apply exponential filter to reduce noise sensitivity
    // filtered = alpha * new + (1-alpha) * old
    float alpha = pid->derivativeFilter;
    pid->filteredDerivative = alpha * derivative + (1.0 - alpha) * pid->filteredDerivative;

    dTerm = pid->Kd * pid->filteredDerivative;
  }

  // ========== COMPUTE OUTPUT ==========
  float output = pTerm + iTerm + dTerm;

  // Constrain output to valid range
  output = constrain(output, pid->outputMin, pid->outputMax);

  // Save for next iteration
  pid->previousError = error;
  pid->previousOutput = output;

  return output;
}

// ============================================================================
// PID TUNING AND UTILITY FUNCTIONS
// ============================================================================

/**
 * Update PID gains
 *
 * Allows runtime tuning of PID parameters
 *
 * Educational Note:
 * PID tuning is an iterative process:
 * 1. Start with Kp only (Ki=0, Kd=0)
 * 2. Increase Kp until oscillation, then reduce by 50%
 * 3. Add Ki to eliminate steady-state error
 * 4. Add Kd to reduce overshoot
 */
void setPIDGains(PIDController* pid, float kp, float ki, float kd) {
  pid->Kp = kp;
  pid->Ki = ki;
  pid->Kd = kd;

  // Reset integral when gains change to prevent windup
  pid->integral = 0.0;
  pid->previousError = 0.0;
  pid->filteredDerivative = 0.0;
}

/**
 * Reset PID controller state
 *
 * Call this when:
 * - Changing setpoints significantly
 * - Recovering from errors
 * - Starting a new control session
 */
void resetPID(PIDController* pid) {
  pid->integral = 0.0;
  pid->previousError = 0.0;
  pid->previousOutput = 0.0;
  pid->filteredDerivative = 0.0;
  pid->lastUpdateTime = millis();
}

/**
 * Set PID output limits
 *
 * Constrains controller output to actuator capabilities
 */
void setPIDLimits(PIDController* pid, float minOutput, float maxOutput) {
  pid->outputMin = minOutput;
  pid->outputMax = maxOutput;
}

/**
 * Set integral limits (anti-windup)
 *
 * Prevents integral term from growing too large
 *
 * Educational Note:
 * Integral windup occurs when the integral accumulates during
 * saturation (e.g., heater already at max, but still cold).
 * Limiting the integral prevents excessive overshoot when
 * the error finally decreases.
 */
void setPIDIntegralLimits(PIDController* pid, float minIntegral, float maxIntegral) {
  pid->integralMin = minIntegral;
  pid->integralMax = maxIntegral;
}

/**
 * Enable/disable integral term
 *
 * Useful for testing or when integral action is not desired
 */
void setPIDIntegralEnable(PIDController* pid, bool enable) {
  pid->enableIntegral = enable;
  if (!enable) {
    pid->integral = 0.0;
  }
}

/**
 * Enable/disable derivative term
 *
 * Useful for noisy sensors where derivative amplifies noise
 */
void setPIDDerivativeEnable(PIDController* pid, bool enable) {
  pid->enableDerivative = enable;
  if (!enable) {
    pid->filteredDerivative = 0.0;
  }
}

/**
 * Set deadband
 *
 * Prevents control action for small errors near setpoint
 *
 * Educational Note:
 * Deadband creates a "good enough" zone around the setpoint.
 * This prevents actuator wear from constant small adjustments
 * and reduces oscillation.
 */
void setPIDDeadband(PIDController* pid, float deadband) {
  pid->deadband = abs(deadband);
}

// ============================================================================
// PID DIAGNOSTICS
// ============================================================================

/**
 * Print PID controller state for debugging
 *
 * Shows current gains, state, and output
 */
void printPIDStatus(PIDController* pid, const char* name) {
  Serial.println(String("=== ") + name + String(" PID Status ==="));

  Serial.print(F("Gains: Kp="));
  Serial.print(pid->Kp, 4);
  Serial.print(F(", Ki="));
  Serial.print(pid->Ki, 4);
  Serial.print(F(", Kd="));
  Serial.println(pid->Kd, 4);

  Serial.print(F("State: Integral="));
  Serial.print(pid->integral, 2);
  Serial.print(F(", PrevError="));
  Serial.print(pid->previousError, 2);
  Serial.print(F(", PrevOutput="));
  Serial.println(pid->previousOutput, 2);

  Serial.print(F("Limits: Out=["));
  Serial.print(pid->outputMin);
  Serial.print(F(", "));
  Serial.print(pid->outputMax);
  Serial.print(F("], Int=["));
  Serial.print(pid->integralMin);
  Serial.print(F(", "));
  Serial.print(pid->integralMax);
  Serial.println(F("]"));

  Serial.print(F("Deadband: "));
  Serial.println(pid->deadband, 2);

  Serial.println(F("============================="));
  Serial.println();
}

/**
 * Auto-tune PID using Ziegler-Nichols method (simplified)
 *
 * EDUCATIONAL PLACEHOLDER - Advanced feature for Phase 3+
 *
 * Ziegler-Nichols tuning method:
 * 1. Set Ki=0, Kd=0
 * 2. Increase Kp until system oscillates continuously
 * 3. Measure oscillation period Tu and ultimate gain Ku
 * 4. Calculate: Kp = 0.6*Ku, Ki = 2*Kp/Tu, Kd = Kp*Tu/8
 */
void autoTunePID(PIDController* pid) {
  sendInfo("Auto-tune not yet implemented (Phase 3 feature)");
  // TODO: Implement relay-based auto-tuning
}

// ============================================================================
// TEMPERATURE CONTROL WITH PID
// ============================================================================

/**
 * Temperature control using PID
 *
 * Called from main control loop when in PID mode
 *
 * Educational Note:
 * PID output is "effort" - positive for heating, negative for cooling.
 * We map this to actuator commands (heater on/off, fan speed).
 */
void temperaturePIDControl() {
  // Compute PID output
  float output = computePID(&tempPID, temperatureSetpoint, currentTemperature);

  // Apply control based on PID output
  // Positive output = need heating
  // Negative output = need cooling

  if (output > 1.0) {
    // Need heating
    setHeater(true);
    setFanSpeed(0);
  }
  else if (output < -1.0) {
    // Need cooling - map output to fan speed
    float fanPercent = constrain(abs(output), 0.0, 100.0);
    setFanSpeedPercent(fanPercent);
    setHeater(false);
  }
  else {
    // Within deadband - minimal control
    setHeater(false);
    setFanSpeed(0);
  }
}

/**
 * Moisture control using PID
 *
 * Note: Pump is on/off, so PID determines watering frequency/duration
 */
void moisturePIDControl() {
  // Compute PID output (0-100 range for moisture)
  float output = computePID(&moisturePID, moistureSetpoint, currentMoisture);

  // Apply watering based on PID output
  static unsigned long lastPumpTime = 0;
  const unsigned long PUMP_MIN_INTERVAL = 30000;  // 30 seconds minimum

  unsigned long now = millis();

  // If PID says we need significant watering, pulse the pump
  if (output > 10.0 && (now - lastPumpTime > PUMP_MIN_INTERVAL)) {
    // Duration proportional to PID output (100ms to 2000ms)
    unsigned long pulseDuration = map(output, 10, 100, 100, 2000);
    pulsePump(pulseDuration);
    lastPumpTime = now;
  }
}
