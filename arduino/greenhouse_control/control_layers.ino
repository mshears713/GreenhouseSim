/*
 * Layered Control Strategies
 *
 * This file implements progressive control strategies from simple
 * to sophisticated:
 * 1. Manual - Direct user control
 * 2. Open-loop - Simple threshold-based control
 * 3. Closed-loop - Feedback with error correction
 * 4. Feed-forward - Anticipatory control
 * 5. PID - Full proportional-integral-derivative control
 *
 * Educational Notes:
 * Each layer builds on the previous, demonstrating how control
 * systems evolve from basic to advanced. This progression helps
 * learners understand the purpose and benefits of each approach.
 */

// ============================================================================
// CONTROL SYSTEM UPDATE
// ============================================================================

/**
 * Main control system update function
 *
 * Routes to appropriate control strategy based on current mode.
 * Called periodically from main loop at CONTROL_UPDATE_INTERVAL.
 *
 * Educational Note:
 * Using a dispatch function keeps the main loop clean and makes
 * it easy to switch between control modes at runtime.
 */
void updateControlSystem() {
  // Safety check: pump runtime limit
  checkPumpSafety();

  // Route to appropriate control strategy
  switch (currentControlMode) {
    case MODE_MANUAL:
      // Manual mode - do nothing, user controls actuators directly
      break;

    case MODE_OPEN_LOOP:
      controlOpenLoop();
      break;

    case MODE_CLOSED_LOOP:
      controlClosedLoop();
      break;

    case MODE_FEEDFORWARD:
      controlFeedForward();
      break;

    case MODE_PID:
      controlPID();
      break;

    default:
      // Unknown mode, fall back to manual
      currentControlMode = MODE_MANUAL;
      break;
  }
}

// ============================================================================
// OPEN-LOOP CONTROL (Layer 1)
// ============================================================================

/**
 * Open-loop control strategy
 *
 * Simple threshold-based control without feedback.
 * Actuators turn on/off based on sensor readings exceeding thresholds.
 *
 * Educational Note:
 * Open-loop control is the simplest approach:
 * - If too hot → turn on fan
 * - If too cold → turn on heater
 * - If too dry → turn on pump
 *
 * Limitations:
 * - No correction for overshoot
 * - Doesn't account for disturbances
 * - Can oscillate around setpoint
 *
 * Good for: Simple on/off devices, basic environmental control
 */
void controlOpenLoop() {
  // Temperature control thresholds
  const float TEMP_HIGH_THRESHOLD = temperatureSetpoint + 1.0;   // 1°C above setpoint
  const float TEMP_LOW_THRESHOLD = temperatureSetpoint - 1.0;    // 1°C below setpoint

  // Moisture control thresholds
  const float MOISTURE_LOW_THRESHOLD = moistureSetpoint - 5.0;   // 5% below setpoint
  const float MOISTURE_HIGH_THRESHOLD = moistureSetpoint + 5.0;  // 5% above setpoint

  // Temperature control
  if (currentTemperature > TEMP_HIGH_THRESHOLD) {
    // Too hot: turn on fan, turn off heater
    setFanSpeed(255);  // Full speed
    setHeater(false);
  }
  else if (currentTemperature < TEMP_LOW_THRESHOLD) {
    // Too cold: turn on heater, turn off fan
    setHeater(true);
    setFanSpeed(0);
  }
  // else: in acceptable range, maintain current state

  // Moisture control
  if (currentMoisture < MOISTURE_LOW_THRESHOLD) {
    // Too dry: water for 1 second
    static unsigned long lastWatering = 0;
    if (millis() - lastWatering > 60000) {  // At least 60 seconds between waterings
      pulsePump(1000);  // 1-second pulse
      lastWatering = millis();
    }
  }
}

// ============================================================================
// CLOSED-LOOP CONTROL (Layer 2)
// ============================================================================

/**
 * Closed-loop control strategy
 *
 * Feedback-based control that responds proportionally to error.
 * Error = Setpoint - Current Value
 *
 * Educational Note:
 * Closed-loop adds feedback:
 * - Calculate error (how far from setpoint)
 * - Apply correction proportional to error
 * - Larger error → stronger correction
 *
 * Improvements over open-loop:
 * - Proportional response reduces oscillation
 * - Adapts to disturbances
 * - Smoother control
 *
 * Limitations:
 * - Steady-state error (never quite reaches setpoint)
 * - Can still overshoot with large disturbances
 *
 * Good for: Most basic automatic control applications
 */
void controlClosedLoop() {
  // Calculate temperature error
  float tempError = temperatureSetpoint - currentTemperature;

  // Temperature control with proportional response
  if (tempError > 0) {
    // Need heating
    setHeater(true);
    setFanSpeed(0);
  }
  else if (tempError < 0) {
    // Need cooling - fan speed proportional to error
    float absTempError = abs(tempError);
    float fanSpeed = constrain(absTempError * 50.0, 0.0, 100.0);  // Scale error to fan speed %
    setFanSpeedPercent(fanSpeed);
    setHeater(false);
  }

  // Moisture control with hysteresis (prevent rapid on/off)
  float moistureError = moistureSetpoint - currentMoisture;
  const float MOISTURE_HYSTERESIS = 3.0;  // 3% deadband

  static bool pumpRecentlyRan = false;
  static unsigned long pumpStopTime = 0;

  if (moistureError > MOISTURE_HYSTERESIS && !pumpRecentlyRan) {
    // Need watering
    pulsePump(1000);
    pumpRecentlyRan = true;
    pumpStopTime = millis();
  }

  // Reset pump flag after cooldown period
  if (pumpRecentlyRan && (millis() - pumpStopTime > 30000)) {
    pumpRecentlyRan = false;
  }
}

// ============================================================================
// FEED-FORWARD CONTROL (Layer 3)
// ============================================================================

/**
 * Feed-forward control strategy
 *
 * Anticipatory control based on known disturbances.
 * Combines feedback with predictive adjustments.
 *
 * Educational Note:
 * Feed-forward anticipates disturbances:
 * - Time of day (solar heating)
 * - Scheduled events
 * - Known patterns
 *
 * Works by:
 * 1. Predict disturbance effect
 * 2. Apply correction BEFORE error occurs
 * 3. Combine with feedback for robustness
 *
 * Benefits:
 * - Faster response to known disturbances
 * - Reduced error magnitude
 * - More proactive than reactive
 *
 * Limitations:
 * - Requires knowledge of disturbances
 * - Model inaccuracies can cause problems
 *
 * Good for: Systems with predictable disturbances
 *
 * PLACEHOLDER: Will be fully implemented in Phase 2
 */
void controlFeedForward() {
  // Start with closed-loop control as base
  controlClosedLoop();

  // Add feed-forward compensation for time-of-day effects
  // (Simplified placeholder - will be expanded)

  // Get current hour (would need RTC in real implementation)
  // For now, use millis() to simulate time of day
  unsigned long seconds = millis() / 1000;
  int simulatedHour = (seconds / 3600) % 24;  // Simulated hour of day

  // During peak sun hours (12-3 PM), preemptively increase fan speed
  if (simulatedHour >= 12 && simulatedHour <= 15) {
    // Anticipate solar heating, increase cooling preemptively
    int currentFanSpeed = fanSpeed;
    int boostedSpeed = constrain(currentFanSpeed + 50, 0, 255);
    setFanSpeed(boostedSpeed);
  }

  // During early morning (6-8 AM), anticipate rapid heating
  else if (simulatedHour >= 6 && simulatedHour <= 8) {
    // Prepare for temperature rise
    // Reduce heating slightly
    if (heaterState && currentTemperature > temperatureSetpoint - 0.5) {
      setHeater(false);
    }
  }
}

// ============================================================================
// PID CONTROL (Layer 4)
// ============================================================================

// PID state variables (will be moved to pid_controller.ino in Phase 2)
float tempIntegral = 0.0;
float tempPrevError = 0.0;
float moistureIntegral = 0.0;
float moisturePrevError = 0.0;

// PID gains (tunable, will be set via serial in Phase 2)
float tempKp = 1.0;
float tempKi = 0.1;
float tempKd = 0.05;

float moistureKp = 0.8;
float moistureKi = 0.05;
float moistureKd = 0.02;

/**
 * PID control strategy
 *
 * Full proportional-integral-derivative control.
 * Most sophisticated control strategy for precise regulation.
 *
 * Educational Note:
 * PID combines three terms:
 *
 * P (Proportional): Responds to current error
 *   - Larger error → stronger correction
 *   - Like closed-loop, but tunable
 *
 * I (Integral): Eliminates steady-state error
 *   - Accumulates error over time
 *   - Pushes output until error is zero
 *   - Eliminates offset
 *
 * D (Derivative): Dampens oscillation
 *   - Responds to rate of change
 *   - Predicts future error
 *   - Reduces overshoot
 *
 * Together: Fast response (P), no offset (I), no overshoot (D)
 *
 * Tuning:
 * - Increase Kp: Faster response, but more overshoot
 * - Increase Ki: Eliminate offset, but can cause overshoot
 * - Increase Kd: Reduce overshoot, but can amplify noise
 *
 * PLACEHOLDER: Basic implementation, will be refined in Phase 2
 */
void controlPID() {
  // Get time step
  static unsigned long lastPIDUpdate = 0;
  unsigned long now = millis();
  float dt = (now - lastPIDUpdate) / 1000.0;  // Convert to seconds
  lastPIDUpdate = now;

  if (dt == 0) {
    dt = 0.5;  // Default time step for first iteration
  }

  // ========== Temperature PID ==========

  // Calculate error
  float tempError = temperatureSetpoint - currentTemperature;

  // Integral term (with anti-windup)
  tempIntegral += tempError * dt;
  tempIntegral = constrain(tempIntegral, -100.0, 100.0);  // Prevent windup

  // Derivative term
  float tempDerivative = (tempError - tempPrevError) / dt;

  // PID output
  float tempOutput = tempKp * tempError +
                     tempKi * tempIntegral +
                     tempKd * tempDerivative;

  tempPrevError = tempError;

  // Apply temperature control based on PID output
  if (tempOutput > 0) {
    // Need heating
    setHeater(true);
    setFanSpeed(0);
  }
  else {
    // Need cooling
    float fanPercent = constrain(abs(tempOutput) * 10.0, 0.0, 100.0);
    setFanSpeedPercent(fanPercent);
    setHeater(false);
  }

  // ========== Moisture PID ==========
  // (Simplified - pump is on/off, but PID determines timing)

  float moistureError = moistureSetpoint - currentMoisture;

  moistureIntegral += moistureError * dt;
  moistureIntegral = constrain(moistureIntegral, -100.0, 100.0);

  float moistureDerivative = (moistureError - moisturePrevError) / dt;

  float moistureOutput = moistureKp * moistureError +
                         moistureKi * moistureIntegral +
                         moistureKd * moistureDerivative;

  moisturePrevError = moistureError;

  // Apply moisture control
  static unsigned long lastPumpTime = 0;
  const unsigned long PUMP_MIN_INTERVAL = 30000;  // 30 seconds minimum

  if (moistureOutput > 5.0 && (now - lastPumpTime > PUMP_MIN_INTERVAL)) {
    // PID says we need significant watering
    pulsePump(1000);
    lastPumpTime = now;
  }
}

// ============================================================================
// CONTROL UTILITIES
// ============================================================================

/**
 * Reset PID integrators
 *
 * Should be called when:
 * - Changing setpoints
 * - Switching to/from PID mode
 * - Recovering from errors
 *
 * Educational Note:
 * Resetting integral terms prevents "integral windup" - where
 * accumulated error from one operating condition affects the next.
 */
void resetPIDIntegrals() {
  tempIntegral = 0.0;
  tempPrevError = 0.0;
  moistureIntegral = 0.0;
  moisturePrevError = 0.0;

  sendInfo("PID integrals reset");
}

/**
 * Update PID parameters from serial command
 *
 * Will be called from serial_comm.ino when SET_PID command received
 */
void updatePIDParameters(String type, float kp, float ki, float kd) {
  if (type == "TEMP") {
    tempKp = kp;
    tempKi = ki;
    tempKd = kd;
  }
  else if (type == "MOISTURE") {
    moistureKp = kp;
    moistureKi = ki;
    moistureKd = kd;
  }

  // Reset integrators when changing parameters
  resetPIDIntegrals();
}
