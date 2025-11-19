# Greenhouse Control System - Example Scripts

This directory contains example scripts demonstrating various features and use cases of the Greenhouse Control System.

## Available Examples

### 1. PID Tuning Example (`pid_tuning_example.py`)

**Purpose:** Automated PID parameter tuning using the Ziegler-Nichols method.

**Features:**
- Quick test with preset Kp values
- Automatic Ziegler-Nichols tuning
- Manual Kp sweep
- Visualization of temperature responses
- Performance metrics (overshoot, settling time, steady-state error)

**Usage:**
```bash
# Run with Python
python examples/pid_tuning_example.py

# Or make executable and run directly (Linux/macOS)
chmod +x examples/pid_tuning_example.py
./examples/pid_tuning_example.py
```

**What You'll Learn:**
- How to systematically tune PID controllers
- Understanding P, I, and D effects on system response
- Ziegler-Nichols tuning methodology
- Interpreting step response characteristics

**Example Output:**
```
 Greenhouse PID Tuning Assistant
 Automated Parameter Optimization
========================================

Choose tuning method:
  1. Quick test with preset Kp values
  2. Ziegler-Nichols automatic tuning (recommended)
  3. Manual Kp sweep

Enter choice (1-3): 2

Finding Ultimate Gain (Ku) - Ziegler-Nichols Method
Iteration 1: Testing Kp = 0.50
  No sustained oscillation
Iteration 2: Testing Kp = 1.00
  No sustained oscillation
Iteration 3: Testing Kp = 1.50
  ✓ Sustained oscillation detected!
  Ultimate Gain (Ku) = 1.50
  Ultimate Period (Tu) = 45.2s

Recommended PID Parameters:
  Kp (Proportional) = 0.900
  Ki (Integral)     = 0.040
  Kd (Derivative)   = 5.085
```

---

### 2. Failure Mode Testing (`failure_mode_test.py`)

**Purpose:** Test system robustness under various failure scenarios.

**Features:**
- Sensor stuck testing
- Noisy sensor testing
- Actuator stuck-on testing
- Environmental stress testing (heatwave/cold snap)
- Communication loss simulation
- Automated test suite

**Usage:**
```bash
# Run with Python
python examples/failure_mode_test.py

# Or run directly
./examples/failure_mode_test.py
```

**What You'll Learn:**
- How systems handle sensor failures
- Importance of error detection and recovery
- Safe degradation modes
- Robustness testing methodologies

**Example Output:**
```
 Greenhouse Failure Mode Testing
 System Robustness Validation
========================================

Test options:
  1. Run all tests (comprehensive)
  2. Test sensor stuck
  3. Test noisy sensor
  4. Test actuator stuck
  5. Test environmental stress (heatwave)
  6. Custom test

Enter choice (1-6): 1

TEST: Sensor Stuck Failure
========================================
Injecting sensor stuck failure for 120s...
Initial temperature: 23.5°C

Results:
  Temperature variation during failure: 0.8°C
  Final temperature: 23.8°C
  ✓ PASS: Sensor reading remained stable
```

---

## Running Examples in Docker

If you're running the system in Docker, you can execute examples inside the container:

```bash
# Start container
docker-compose up -d

# Run PID tuning example
docker exec -it greenhouse-control python /app/examples/pid_tuning_example.py

# Run failure mode tests
docker exec -it greenhouse-control python /app/examples/failure_mode_test.py
```

---

## Creating Your Own Examples

### Template Structure

```python
#!/usr/bin/env python3
"""
Example Script Title

Description of what this example demonstrates.

Usage:
    python examples/your_example.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from python.simulation.engine import SimulationEngine

def main():
    """Main execution"""
    # Initialize simulation
    engine = SimulationEngine("simulation_config.yaml")
    engine.start()

    # Your example code here
    print("Hello from greenhouse control system!")

    # Cleanup
    engine.stop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
```

### Best Practices

1. **Always include docstrings** explaining the purpose and usage
2. **Handle exceptions gracefully** with try/except blocks
3. **Clean up resources** (stop simulation engine when done)
4. **Add user interaction** where appropriate (input prompts, confirmations)
5. **Provide clear output** with formatting and status indicators
6. **Make scripts executable** with proper shebang (`#!/usr/bin/env python3`)
7. **Include educational comments** explaining control theory concepts

---

## Example Ideas

Here are some ideas for additional examples you could create:

### Control Strategy Comparison
Compare different control strategies (open-loop, closed-loop, PID) on the same scenario:
- Temperature regulation under varying ambient conditions
- Moisture control with different evaporation rates
- Response to disturbances

### Data Logging and Analysis
Demonstrate data collection and analysis:
- Export CSV data
- Generate statistical reports
- Create custom visualizations
- Analyze long-term trends

### Custom Control Algorithms
Implement and test custom control strategies:
- Fuzzy logic controller
- Model predictive control (MPC)
- Adaptive control
- Bang-bang control with hysteresis

### Multi-Variable Control
Coordinate control of multiple variables:
- Temperature and humidity coupling
- Energy optimization
- Multi-objective control (comfort + efficiency)

### Hardware Integration
Examples for working with real Arduino:
- Sensor calibration procedures
- Actuator testing sequences
- Communication diagnostics
- Data synchronization

---

## Troubleshooting Examples

### Import Errors

**Issue:** `ModuleNotFoundError: No module named 'python'`

**Solution:**
```bash
# Make sure you're in the project root directory
cd /path/to/GreenhouseSim

# Run examples from project root
python examples/pid_tuning_example.py
```

### Simulation Not Starting

**Issue:** Example hangs at "Initializing simulation engine..."

**Solution:**
```bash
# Check simulation_config.yaml exists
ls -l simulation_config.yaml

# Verify config is valid YAML
python -c "import yaml; yaml.safe_load(open('simulation_config.yaml'))"

# Run with debug output
python -u examples/pid_tuning_example.py
```

### Missing Dependencies

**Issue:** `ImportError: No module named 'scipy'` or similar

**Solution:**
```bash
# Install all requirements
pip install -r requirements.txt

# Or install specific package
pip install scipy matplotlib
```

### Permission Denied

**Issue:** `bash: ./examples/pid_tuning_example.py: Permission denied`

**Solution:**
```bash
# Make script executable
chmod +x examples/pid_tuning_example.py

# Or run with python explicitly
python examples/pid_tuning_example.py
```

---

## Contributing Examples

If you create a useful example script, consider contributing it:

1. Follow the template structure above
2. Include comprehensive docstrings
3. Add error handling
4. Test on multiple platforms (Windows, Linux, macOS)
5. Update this README with your example
6. Submit a pull request

---

## Resources

- [PID Controller Theory](https://en.wikipedia.org/wiki/PID_controller)
- [Ziegler-Nichols Tuning](https://en.wikipedia.org/wiki/Ziegler%E2%80%93Nichols_method)
- [Control Systems Primer](../docs/CONTROL_STRATEGIES.md)
- [Testing Guide](../docs/TESTING_GUIDE.md)

---

**Last Updated:** 2025-01-19
**Version:** 1.0.0
