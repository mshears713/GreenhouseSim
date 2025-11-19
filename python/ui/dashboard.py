"""
Main Greenhouse Dashboard

This module implements the primary Streamlit dashboard with:
- Real-time sensor monitoring
- Actuator status display
- Interactive control parameter tuning
- Simulation controls
- Data logging and export
- Error/alarm panels

Educational Note:
Streamlit's reactive model automatically updates the UI when data changes,
making it ideal for real-time monitoring dashboards.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from ..simulation.engine import SimulationEngine
from ..communication.serial_interface import ArduinoInterface
from ..data.models import ControlMode, ActuatorType
from ..data.logger import DataLogger

logger = logging.getLogger(__name__)


class GreenhouseDashboard:
    """
    Main dashboard for greenhouse monitoring and control

    Manages the Streamlit UI, simulation engine, Arduino communication,
    and data logging.

    Educational Note:
    This class uses Streamlit's session state to maintain persistence
    across page reruns (Streamlit reruns the entire script on interaction).
    """

    def __init__(self):
        """Initialize dashboard components"""

        # Initialize session state variables if not present
        if 'initialized' not in st.session_state:
            self._initialize_session_state()

        # Get references to session state (for cleaner code)
        self.simulation = st.session_state.simulation
        self.arduino = st.session_state.arduino
        self.data_logger = st.session_state.data_logger

    def _initialize_session_state(self):
        """Initialize Streamlit session state variables"""

        # Simulation mode flag
        st.session_state.simulation_mode = True  # Start in simulation mode
        st.session_state.arduino_connected = False

        # Initialize simulation engine
        st.session_state.simulation = SimulationEngine("simulation_config.yaml")
        st.session_state.simulation.start()

        # Arduino interface (not connected yet)
        st.session_state.arduino = None

        # Data logger
        st.session_state.data_logger = DataLogger(
            log_dir="./data/logs",
            db_path="./data/greenhouse.db",
            enable_csv=True,
            enable_sqlite=True
        )

        # Control parameters
        st.session_state.current_mode = ControlMode.MANUAL
        st.session_state.temp_setpoint = 24.0
        st.session_state.moisture_setpoint = 50.0

        # PID parameters (temperature)
        st.session_state.temp_kp = 1.0
        st.session_state.temp_ki = 0.1
        st.session_state.temp_kd = 0.05

        # PID parameters (moisture)
        st.session_state.moisture_kp = 0.8
        st.session_state.moisture_ki = 0.05
        st.session_state.moisture_kd = 0.02

        # Manual actuator controls
        st.session_state.manual_fan_speed = 0.0
        st.session_state.manual_heater = False
        st.session_state.manual_pump = False

        # Data history for charts (last 5 minutes)
        st.session_state.history_size = 300  # 5 minutes at 1Hz
        st.session_state.temp_history = []
        st.session_state.moisture_history = []
        st.session_state.time_history = []

        # Alerts and errors
        st.session_state.alerts = []

        # Failure injection
        st.session_state.active_failures = []

        # Mark as initialized
        st.session_state.initialized = True

        logger.info("Dashboard session state initialized")

    def render(self):
        """
        Render the complete dashboard

        Educational Note:
        This method is called on every Streamlit rerun. We organize
        the dashboard into sections for clarity.
        """

        # Sidebar navigation and controls
        self._render_sidebar()

        # Main dashboard content
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🚀 Mission Brief",
            "📊 Monitoring",
            "⚙️ Control",
            "🔬 Simulation",
            "📈 Data & Logs"
        ])

        with tab1:
            self._render_tutorial_tab()

        with tab2:
            self._render_monitoring_tab()

        with tab3:
            self._render_control_tab()

        with tab4:
            self._render_simulation_tab()

        with tab5:
            self._render_data_tab()

        # Update data (simulation or Arduino)
        self._update_data()

    def _render_sidebar(self):
        """Render sidebar with system controls and status"""

        st.sidebar.header("🎛️ System Control")
        st.sidebar.caption("Control system operation mode and view status")

        # Mode selection with enhanced help text
        mode_option = st.sidebar.radio(
            "Operation Mode",
            ["Simulation Only", "Hardware Connected"],
            index=0 if st.session_state.simulation_mode else 1,
            help="""
            **Simulation Only**: Run physics-based simulation without Arduino hardware.
            Perfect for testing control strategies and learning system behavior.

            **Hardware Connected**: Connect to real Arduino hardware via serial port.
            Use this mode to control actual greenhouse equipment.
            """
        )

        st.session_state.simulation_mode = (mode_option == "Simulation Only")

        # Arduino connection (if in hardware mode)
        if not st.session_state.simulation_mode:
            st.sidebar.subheader("Arduino Connection")

            if not st.session_state.arduino_connected:
                # Show connection interface
                port = st.sidebar.text_input(
                    "Serial Port",
                    value="/dev/ttyACM0",
                    help="Arduino serial port (e.g., /dev/ttyACM0, COM3)"
                )

                if st.sidebar.button("Connect to Arduino"):
                    self._connect_arduino(port)
            else:
                st.sidebar.success("✅ Arduino Connected")
                if st.sidebar.button("Disconnect"):
                    self._disconnect_arduino()

        # System status with enhanced visual feedback
        st.sidebar.divider()
        st.sidebar.subheader("📊 System Status")

        sim_status = "🟢 Running" if self.simulation.running else "🔴 Stopped"
        st.sidebar.write(f"**Simulation:** {sim_status}")

        if st.session_state.arduino_connected:
            st.sidebar.success("**Arduino:** Connected")
        else:
            st.sidebar.info("**Arduino:** Disconnected")

        # Performance metrics in sidebar
        stats = self.simulation.get_statistics()
        if 'performance_ratio' in stats:
            perf_ratio = stats['performance_ratio']
            if perf_ratio >= 95:
                st.sidebar.write(f"⚡ Performance: {perf_ratio:.0f}%")
            elif perf_ratio >= 80:
                st.sidebar.warning(f"⚠️ Performance: {perf_ratio:.0f}%")
            else:
                st.sidebar.error(f"🐌 Performance: {perf_ratio:.0f}% (Lagging)")

        # Quick actions
        st.sidebar.divider()
        st.sidebar.subheader("⚡ Quick Actions")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🔄 Reset"):
                self._reset_system()

        with col2:
            if st.button("⏸️ Pause" if self.simulation.running else "▶️ Resume"):
                self._toggle_pause()

        # Alerts summary
        if st.session_state.alerts:
            st.sidebar.divider()
            st.sidebar.subheader("⚠️ Active Alerts")
            for alert in st.session_state.alerts[-5:]:  # Show last 5
                st.sidebar.warning(alert)

    def _render_tutorial_tab(self):
        """Render interactive tutorial with space colony narrative"""

        st.header("🚀 Project EDEN: Space Colony Greenhouse Initiative")

        # Mission briefing header with dramatic styling
        st.markdown("""
        <div style='background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h2 style='color: white; margin: 0;'>📡 INCOMING TRANSMISSION</h2>
            <p style='color: #b3d9ff; margin-top: 0.5rem; font-size: 0.9rem;'>
                <b>FROM:</b> Dr. Sarah Chen, Director of Life Support Systems<br>
                <b>TO:</b> Greenhouse Operations Specialist (You)<br>
                <b>RE:</b> URGENT - Prototype Greenhouse Activation Required<br>
                <b>CLASSIFICATION:</b> Priority Alpha
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Story introduction
        with st.expander("📜 READ YOUR MISSION BRIEFING", expanded=True):
            st.markdown("""
            Welcome aboard, Specialist.

            You've been selected for a critical mission. In six months, humanity will establish its first
            permanent colony on Mars. Before we send our pioneers into the void, we need to know they
            can **survive** - and that means growing food in environments hostile to life.

            The prototype you're looking at isn't just a greenhouse. It's hope in glass and steel. A proof
            of concept that we can create Eden anywhere in the solar system. **If it works.**

            That's where you come in.

            This facility has been sitting dormant since the last test cycle. Your mission is simple but
            vital: **bring it online, stabilize it, and prove it can sustain life under automated control.**

            The colonists are counting on you. Their survival depends on systems like this one running
            flawlessly, 225 million kilometers from the nearest technician.

            **No pressure.**

            Let's get you up to speed.

            *— Dr. Chen*
            """)

        st.divider()

        # Tutorial sections with story integration
        tutorial_section = st.radio(
            "📚 Select Training Module",
            [
                "1️⃣ Understanding Your Greenhouse",
                "2️⃣ The Monitoring Systems",
                "3️⃣ Control Strategies for Space",
                "4️⃣ Running Your First Test",
                "5️⃣ Handling Emergencies",
                "6️⃣ Final Certification"
            ],
            horizontal=False
        )

        st.divider()

        if "1️⃣" in tutorial_section:
            self._render_tutorial_section_1()
        elif "2️⃣" in tutorial_section:
            self._render_tutorial_section_2()
        elif "3️⃣" in tutorial_section:
            self._render_tutorial_section_3()
        elif "4️⃣" in tutorial_section:
            self._render_tutorial_section_4()
        elif "5️⃣" in tutorial_section:
            self._render_tutorial_section_5()
        elif "6️⃣" in tutorial_section:
            self._render_tutorial_section_6()

    def _render_tutorial_section_1(self):
        """Tutorial Section 1: Understanding the greenhouse"""
        st.subheader("1️⃣ Understanding Your Greenhouse")

        st.markdown("""
        ### The EDEN-1 Prototype

        You're looking at a scaled-down version of the life support greenhouse that will be deployed
        to Mars Base Alpha. While this prototype operates on Earth, it's designed to simulate the
        challenges of extraterrestrial agriculture.
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.info("""
            **🌡️ ENVIRONMENTAL CONTROL**

            In space, there's no weather to rely on. No rain. No seasons. Just the hostile void.
            Everything must be controlled:

            - **Temperature**: Plants need warmth, but too much kills them
            - **Moisture**: Water is precious in space - every drop must be perfect
            - **Humidity**: Affects plant health and disease resistance
            - **Airflow**: Ensures CO₂ reaches leaves for photosynthesis
            """)

        with col2:
            st.success("""
            **🔧 YOUR EQUIPMENT**

            You have four primary systems:

            - **💨 Ventilation Fan**: Controls cooling and air circulation
            - **🔥 Heater**: Maintains temperature in cold conditions
            - **💧 Water Pump**: Delivers precise irrigation
            - **🪟 Vent**: Adjusts airflow and temperature regulation

            *On Mars, if one fails, crops die. Here, we learn to prevent that.*
            """)

        st.markdown("""
        ### Why This Matters

        Traditional greenhouses rely on Earth's atmosphere, predictable sunlight, and human intervention.
        **Space greenhouses can't.**

        This system must run autonomously for weeks at a time. It must sense problems before they become
        catastrophic. It must adapt to equipment failures and environmental changes without human help.

        Your job is to master it before it ships to Mars.
        """)

        st.warning("""
        **🎯 TRAINING OBJECTIVE**

        By the end of this tutorial, you should be able to:
        - Monitor all environmental parameters
        - Understand what each actuator does
        - Choose appropriate control strategies
        - Respond to system failures
        - Optimize growth conditions for maximum yield
        """)

    def _render_tutorial_section_2(self):
        """Tutorial Section 2: Monitoring systems"""
        st.subheader("2️⃣ The Monitoring Systems")

        st.markdown("""
        ### Real-Time Sensor Array

        Head over to the **📊 Monitoring** tab (you can keep this Mission Brief open in another window)
        and familiarize yourself with the sensor readings.
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            #### 🌡️ Temperature Sensor

            **What it does:**
            - Measures air temperature inside the greenhouse
            - Updates in real-time (10 times per second)
            - Typical range: 15-35°C

            **Why it matters:**
            - Too cold: Plant growth slows or stops
            - Too hot: Proteins denature, plants die
            - Optimal: 18-28°C for most crops

            **On the dashboard:**
            - Look for the 🌡️ Temperature metric
            - Green = good, Red = deviation from target
            - The delta shows how far from your setpoint
            """)

        with col2:
            st.markdown("""
            #### 💧 Moisture Sensor

            **What it does:**
            - Measures soil water content
            - Range: 0% (bone dry) to 100% (saturated)
            - Critical for plant survival

            **Why it matters:**
            - Too dry: Wilting, death within hours
            - Too wet: Root rot, fungal disease
            - Optimal: 40-70% for most plants

            **On the dashboard:**
            - Look for the 💧 Soil Moisture metric
            - Watch the trend over time
            - Pump activations should correlate with moisture drops
            """)

        st.markdown("""
        #### 💨 Humidity & 🌪️ Airflow

        These secondary metrics help you understand the complete environmental picture:

        - **Humidity**: High humidity (>80%) can cause condensation and disease
        - **Airflow**: Higher values mean better CO₂ distribution to plant leaves
        """)

        st.info("""
        **📊 INTERACTIVE EXERCISE**

        1. Go to the **📊 Monitoring** tab
        2. Watch the live sensor readings for 30 seconds
        3. Observe how the charts update in real-time
        4. Note the current temperature and moisture values
        5. Check if any actuators are currently active (look for 🟢 ON indicators)

        **Questions to consider:**
        - Are the current values within optimal range?
        - Is the system currently heating or cooling?
        - When did the pump last activate?
        """)

        st.success("""
        **💡 PRO TIP**

        In space, sensor failures are catastrophic. That's why the **🔬 Simulation** tab lets you
        inject sensor failures to test how the control system responds. We'll cover that later.
        """)

    def _render_tutorial_section_3(self):
        """Tutorial Section 3: Control strategies"""
        st.subheader("3️⃣ Control Strategies for Space")

        st.markdown("""
        ### From Manual to Autonomous

        This greenhouse can operate in five different control modes. Each represents a different level
        of automation and sophistication. Think of them as evolutionary steps in autonomous systems.
        """)

        # Control mode explanations
        with st.expander("🎮 MANUAL CONTROL - Direct Human Operation", expanded=False):
            st.markdown("""
            **How it works:**
            You directly control every actuator. Fan speed, heater on/off, pump activation - all manual.

            **Advantages:**
            - Complete control
            - Good for testing and diagnostics
            - Simple to understand

            **Disadvantages:**
            - Requires constant human attention
            - **Impossible for long-duration space missions**
            - Human error leads to crop failure

            **When to use:**
            - Initial system testing
            - Troubleshooting equipment
            - Emergency overrides

            **Try it:**
            Go to **⚙️ Control** tab → Select "Manual Control" → Adjust actuators directly
            """)

        with st.expander("📡 OPEN-LOOP (Threshold) - Simple Automation", expanded=False):
            st.markdown("""
            **How it works:**
            Simple rules: "If temperature > 26°C, turn on fan." No feedback, just thresholds.

            **Advantages:**
            - Simple and predictable
            - Low computational requirements
            - Easy to debug

            **Disadvantages:**
            - Can't adapt to changing conditions
            - May oscillate around setpoint
            - Ignores system dynamics

            **Space application:**
            Backup mode if advanced controllers fail. Better than nothing.

            **Analogy:**
            Like a thermostat that just turns on/off at fixed temperatures.
            """)

        with st.expander("🔄 CLOSED-LOOP (Feedback) - Reactive Control", expanded=False):
            st.markdown("""
            **How it works:**
            Continuously measures the error (difference from setpoint) and adjusts actuators accordingly.

            **Advantages:**
            - Adapts to disturbances
            - Self-correcting
            - More stable than open-loop

            **Disadvantages:**
            - Always reactive (waits for error to occur)
            - Can be slow to respond
            - May overshoot

            **Space application:**
            Good baseline for automated control. Reliable and well-understood.
            """)

        with st.expander("⚡ FEED-FORWARD (Predictive) - Proactive Control", expanded=False):
            st.markdown("""
            **How it works:**
            Anticipates disturbances before they affect the system. "Ambient temp dropping?
            Start heating NOW, before greenhouse temperature falls."

            **Advantages:**
            - Proactive, not reactive
            - Faster response
            - Better disturbance rejection

            **Disadvantages:**
            - Requires accurate system model
            - Can't correct for modeling errors
            - More complex

            **Space application:**
            Excellent for known disturbances (day/night cycles, shadowing events).
            """)

        with st.expander("🎯 PID CONTROL - Advanced Precision", expanded=True):
            st.markdown("""
            **How it works:**
            Combines three control actions:

            - **P (Proportional)**: React to current error → "We're 3°C too cold, heat harder!"
            - **I (Integral)**: Eliminate persistent error → "We've been slightly cold for 10 minutes, compensate!"
            - **D (Derivative)**: Predict future error → "Temperature is dropping fast, act NOW!"

            **Advantages:**
            - Industry standard for precision control
            - Can achieve zero steady-state error
            - Tunable for different performance characteristics
            - Handles complex dynamics

            **Disadvantages:**
            - Requires tuning (finding optimal P, I, D values)
            - Can become unstable if poorly tuned
            - More computational overhead

            **Space application:**
            **THIS IS WHAT MARS NEEDS.** Precise, autonomous, reliable. Once tuned correctly,
            PID controllers can run for months without intervention.

            ---

            **🎛️ Tuning PID Controllers**

            The art of PID tuning is finding the balance:

            - **Kp too low**: Slow, sluggish response
            - **Kp too high**: Oscillation, instability
            - **Ki too low**: Never reaches exact setpoint
            - **Ki too high**: Overshoot, slow settling
            - **Kd too low**: Overshoot on disturbances
            - **Kd too high**: Noise amplification, jittery control

            **Default values:**
            - Temperature: Kp=1.0, Ki=0.1, Kd=0.05
            - Moisture: Kp=0.8, Ki=0.05, Kd=0.02

            These are starting points. Real-world systems require experimentation.
            """)

        st.info("""
        **🎯 RECOMMENDED FOR MISSION SUCCESS**

        Start with **Manual** mode to understand the hardware.

        Then activate **PID Control** and let the system run autonomously. This simulates the
        Mars deployment scenario.

        Monitor for at least 5 minutes to see how well it maintains setpoints.
        """)

    def _render_tutorial_section_4(self):
        """Tutorial Section 4: Running first test"""
        st.subheader("4️⃣ Running Your First Test")

        st.markdown("""
        ### Activation Checklist

        Time to bring EDEN-1 online. Follow this sequence exactly - it's the same procedure
        you'll use for the Mars deployment.
        """)

        st.warning("""
        **⚠️ PRE-ACTIVATION WARNING**

        The system is currently running in simulation mode. This is intentional. We don't risk
        real hardware until we've proven the control software works flawlessly in simulation.

        In the sidebar, you should see: **Simulation: 🟢 Running**
        """)

        # Step-by-step activation checklist
        st.markdown("### 📋 Activation Sequence")

        with st.expander("STEP 1: Verify System Status", expanded=True):
            st.markdown("""
            **Look at the sidebar (left side):**

            ✅ Simulation: 🟢 Running
            ✅ Performance: >95%

            If performance is below 80%, the simulation is lagging. This won't affect functionality
            but may cause delays in visualization.

            **Action required:** None, just verify everything is nominal.
            """)

        with st.expander("STEP 2: Set Environmental Targets", expanded=True):
            st.markdown("""
            **Navigate to: ⚙️ Control Tab**

            Set your target values:

            1. **Temperature Setpoint**: 24°C (optimal for lettuce and herbs)
            2. **Moisture Setpoint**: 50% (moderate watering)

            These values tell the control system what you want to maintain.

            **Why these values?**
            - 24°C: Comfortable growth temperature, energy efficient
            - 50%: Moist enough for growth, not so wet it causes rot

            **Action required:** Adjust sliders in Control tab if not already set.
            """)

        with st.expander("STEP 3: Activate PID Control", expanded=True):
            st.markdown("""
            **Still in: ⚙️ Control Tab**

            1. Find "Control Mode" dropdown
            2. Select **"PID Control (Advanced)"**
            3. System will immediately begin autonomous operation

            **What you'll see:**
            - Control mode confirmation message
            - System begins adjusting actuators automatically
            - Temperature and moisture start tracking toward setpoints

            **Expected behavior:**
            - If current temp < 24°C: Heater activates
            - If current temp > 24°C: Fan increases speed
            - If moisture < 50%: Pump activates periodically

            **Action required:** Select PID mode.
            """)

        with st.expander("STEP 4: Monitor System Response", expanded=True):
            st.markdown("""
            **Navigate to: 📊 Monitoring Tab**

            Watch the system for 2-3 minutes:

            **What to observe:**

            1. **Temperature chart**: Should show movement toward 24°C setpoint (dashed line)
            2. **Moisture chart**: Should show gentle oscillation around 50% setpoint
            3. **Actuator status**: Watch for:
               - 💨 Fan adjusting speed based on temperature
               - 🔥 Heater turning on/off as needed
               - 💧 Pump pulsing when moisture drops

            **Good signs:**
            - Smooth convergence to setpoints
            - No wild oscillations
            - Actuators responding logically

            **Bad signs:**
            - Temperature oscillating wildly (±5°C swings)
            - Actuators rapidly switching on/off
            - System not reaching setpoint after 5 minutes

            *(If you see bad signs, the PID needs tuning - we'll cover that in Section 6)*

            **Action required:** Observe and verify stable operation.
            """)

        with st.expander("STEP 5: Check Data Logging", expanded=True):
            st.markdown("""
            **Navigate to: 📈 Data & Logs Tab**

            Verify the system is recording telemetry:

            - You should see a table of recent sensor readings
            - Each row is a timestamped data point
            - This data would be transmitted back to Earth from Mars

            **Why this matters:**
            On Mars, this data is how ground control monitors system health. If something goes wrong
            225 million km away, this log is how engineers diagnose it.

            **Action required:** Verify data is being logged.
            """)

        st.success("""
        **✅ CONGRATULATIONS!**

        If you've completed all 5 steps, EDEN-1 is now running in autonomous mode.

        You've successfully:
        - Configured environmental targets
        - Activated advanced PID control
        - Verified system response
        - Confirmed data logging

        The greenhouse is now operating exactly as it would on Mars: **autonomously,
        reliably, without human intervention.**

        Let it run for a few minutes while you continue with the training.
        """)

    def _render_tutorial_section_5(self):
        """Tutorial Section 5: Emergency scenarios"""
        st.subheader("5️⃣ Handling Emergencies")

        st.markdown("""
        ### When Things Go Wrong

        In space, equipment fails. Sensors break. Actuators jam. Cosmic radiation corrupts electronics.

        The colonists can't run outside and swap parts. **The system must handle failures gracefully.**

        That's what we test now.
        """)

        st.error("""
        **🚨 FAILURE MODE TESTING**

        This is the most important part of your training. Anyone can run a greenhouse when everything
        works. You need to prove you can keep crops alive when the hardware betrays you.
        """)

        # Failure scenarios
        with st.expander("⚠️ SCENARIO 1: Stuck Temperature Sensor", expanded=True):
            st.markdown("""
            **The Situation:**
            The temperature sensor freezes at its current reading due to a failed chip. The actual
            temperature continues to change, but the controller sees a constant value.

            **Why it's dangerous:**
            - Controller thinks temp is stable (it's not)
            - May overheat or freeze the greenhouse
            - Plants can die within hours

            **How to test it:**

            1. Go to **🔬 Simulation** tab
            2. Scroll to "⚠️ Failure Mode Injection"
            3. Set:
               - Failure Type: **Sensor Stuck**
               - Affected Component: **temperature**
               - Duration: **60 seconds**
            4. Click **💥 Inject Failure**

            **What to observe:**

            Watch the **📊 Monitoring** tab:
            - Temperature reading freezes
            - But actual temperature (in real system) continues changing
            - PID controller gets confused
            - May see actuator hunting (rapid on/off cycles)

            **What should happen:**
            - In a production system, redundant sensors would detect the failure
            - Alarms would trigger
            - System would enter safe mode

            *This demo shows WHY redundancy is critical for space systems.*
            """)

        with st.expander("⚠️ SCENARIO 2: Fan Degradation", expanded=True):
            st.markdown("""
            **The Situation:**
            The ventilation fan's motor is failing. It still spins, but at reduced efficiency.
            The controller commands 100% power, but only gets 50% airflow.

            **Why it's dangerous:**
            - Inadequate cooling → overheating
            - Poor CO₂ distribution → reduced photosynthesis
            - System may not realize fan is failing

            **How to test it:**

            1. **🔬 Simulation** tab → Failure Mode Injection
            2. Set:
               - Failure Type: **Actuator Degraded**
               - Affected Component: **fan**
               - Duration: **120 seconds**
            3. Click **💥 Inject Failure**

            **What to observe:**
            - Fan shows as active but effectiveness is reduced
            - Temperature may rise above setpoint
            - PID controller tries to compensate by increasing fan command
            - May see temperature oscillation

            **Real-world response:**
            On Mars, this would trigger a maintenance alert. Ground control would schedule a
            robot repair mission or instruct colonists to replace the fan motor.
            """)

        with st.expander("⚠️ SCENARIO 3: Environmental Disaster - Heatwave", expanded=True):
            st.markdown("""
            **The Situation:**
            External temperature spikes dramatically. On Mars, this could be:
            - Greenhouse exposed to direct sunlight during dust storm clearing
            - Thermal regulation failure in the habitat
            - Equipment malfunction generating excess heat

            **Why it's dangerous:**
            - Overwhelming heat load
            - Cooling systems may be insufficient
            - Crop damage or death possible

            **How to test it:**

            1. **🔬 Simulation** tab → Failure Mode Injection
            2. Set:
               - Failure Type: **Heatwave**
               - Affected Component: **environment**
               - Duration: **90 seconds**
            3. Click **💥 Inject Failure**

            **What to observe:**
            - Ambient temperature spikes
            - Greenhouse internal temperature rises
            - Fan goes to maximum
            - System fights to maintain setpoint
            - May not be able to fully compensate

            **What you'll learn:**
            - System limitations under extreme conditions
            - Importance of thermal margin in design
            - When to activate emergency protocols (vent plants, emergency cooling, etc.)
            """)

        with st.expander("⚠️ SCENARIO 4: Water System Failure", expanded=True):
            st.markdown("""
            **The Situation:**
            The water reservoir runs dry, but the pump doesn't know it. It keeps trying to pump,
            burning out the motor while plants die of thirst.

            **Critical for space:**
            Water is the most precious resource off-Earth. Every drop is recycled. Running the
            reservoir dry is a **mission-critical failure.**

            **How to test it:**

            1. **🔬 Simulation** tab → Failure Mode Injection
            2. Set:
               - Failure Type: **Reservoir Empty**
               - Affected Component: **pump**
               - Duration: **90 seconds**
            3. Click **💥 Inject Failure**

            **What to observe:**
            - Pump activates normally
            - Moisture level DOESN'T increase (no water delivered)
            - PID controller gets increasingly desperate
            - May attempt more frequent watering (damaging pump)

            **Proper response:**
            - Reservoir level sensor should trigger alarm
            - Pump should lock out until refill confirmed
            - Alert sent to crew for manual intervention

            *This scenario emphasizes the need for safety interlocks.*
            """)

        st.info("""
        **🎯 TRAINING EXERCISE**

        Try each scenario above. For each one:

        1. Predict what will happen BEFORE injecting the failure
        2. Watch the system response
        3. Note how long it takes to recover after failure clears
        4. Consider: What would you do if this happened on Mars?

        **Reflection questions:**
        - Which failures are most dangerous?
        - Which ones did the PID controller handle well?
        - Which ones would require human intervention?
        - How would you redesign the system to handle these better?
        """)

        st.success("""
        **💡 LESSON LEARNED**

        Space-rated systems need:
        - **Redundancy**: Backup sensors and actuators
        - **Fault detection**: Know when something is wrong
        - **Graceful degradation**: Fail safely, not catastrophically
        - **Telemetry**: Log everything for post-failure analysis

        The difference between Earth and space: On Earth, failures are expensive.
        In space, they're **lethal**.
        """)

    def _render_tutorial_section_6(self):
        """Tutorial Section 6: Final certification"""
        st.subheader("6️⃣ Final Certification")

        st.markdown("""
        ### Mission Readiness Assessment

        You've learned the theory. You've seen the system operate. You've tested failure scenarios.

        Now it's time to prove you're ready to support the Mars mission.
        """)

        st.warning("""
        **🎓 CERTIFICATION CHALLENGE**

        To be certified as an EDEN-1 Greenhouse Operator, you must successfully complete
        the following practical examination.

        **Scenario:**
        The greenhouse has been offline for maintenance. You need to bring it online and
        demonstrate 5 minutes of stable operation under optimal conditions.
        """)

        # Certification checklist
        st.markdown("### 📝 Certification Requirements")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            **TASK 1: System Configuration** ✓

            - [ ] Reset system to initial state (sidebar: 🔄 Reset)
            - [ ] Verify simulation running at >90% performance
            - [ ] Set temperature setpoint to 25°C
            - [ ] Set moisture setpoint to 55%
            - [ ] Enable PID control mode
            """)

            st.markdown("""
            **TASK 2: Monitoring & Verification** ✓

            - [ ] Observe temperature converge to 25°C (±1°C)
            - [ ] Observe moisture stabilize at 55% (±5%)
            - [ ] Verify actuators responding appropriately
            - [ ] Confirm no wild oscillations or instability
            - [ ] Maintain stable operation for 5 minutes
            """)

        with col2:
            st.markdown("""
            **TASK 3: Emergency Response** ✓

            - [ ] Inject a "Sensor Noisy" failure on temperature
            - [ ] Observe system handling noisy data
            - [ ] Clear failure and verify recovery
            - [ ] System returns to stable operation
            """)

            st.markdown("""
            **TASK 4: Optimization** ✓

            - [ ] Experiment with PID tuning (optional)
            - [ ] Try different setpoints
            - [ ] Observe system response to changes
            - [ ] Document findings in Data & Logs tab
            """)

        st.info("""
        **⏱️ TIME REQUIREMENT**

        Complete all tasks above. The entire certification should take approximately 15-20 minutes.

        Take your time. The colonists' lives depend on your expertise.
        """)

        # Advanced topics
        with st.expander("🚀 ADVANCED TOPICS (Optional Deep Dive)", expanded=False):
            st.markdown("""
            ### For the Truly Curious

            If you want to go beyond basic operation:

            **PID Tuning Optimization:**
            - Try the Ziegler-Nichols method for systematic tuning
            - Increase Kp until system oscillates, then back off
            - Add Ki gradually to eliminate steady-state error
            - Add Kd to dampen overshoot

            **Multi-Variable Control:**
            - Note that temperature and moisture are coupled
            - Watering affects humidity which affects temperature
            - Advanced systems use MIMO (Multi-Input Multi-Output) controllers

            **Predictive Control:**
            - Try Feed-Forward mode
            - Manually adjust ambient temperature (Simulation tab)
            - Observe how Feed-Forward anticipates the disturbance

            **Data Analysis:**
            - Export CSV data from Data & Logs tab
            - Plot in external tools (Excel, Python, etc.)
            - Analyze PID response characteristics
            - Calculate overshoot, settling time, steady-state error

            **Hardware Integration:**
            - If you have Arduino hardware, connect it
            - Switch to "Hardware Connected" mode
            - Control a real greenhouse using this interface

            *These topics are beyond certification requirements but valuable for system mastery.*
            """)

        st.divider()

        # Final message
        st.markdown("""
        ### 🎖️ Certification Complete

        If you've successfully completed all required tasks, congratulations. You now understand:

        ✅ How greenhouse environmental control works
        ✅ The difference between manual and autonomous operation
        ✅ How PID controllers maintain precise setpoints
        ✅ How to detect and respond to system failures
        ✅ Why redundancy and fault tolerance matter in space

        **More importantly**, you understand that this isn't just about plants in a box.

        It's about **survival**. It's about humans living where life shouldn't exist. It's about
        taking a barren rock and making it bloom.

        Every sensor reading, every actuator command, every line of control code - they all
        serve one purpose: **Keep the colonists alive.**

        The systems you've mastered today are the same ones that will grow the first meal on Mars.
        The first salad harvested under an alien sky. The first proof that we can make ourselves
        at home among the stars.
        """)

        st.success("""
        **📡 TRANSMISSION FROM DR. CHEN:**

        *"Well done, Specialist. Your certification results have been logged and transmitted
        to Mission Control.*

        *The EDEN-1 prototype is now cleared for extended autonomous operation. Based on your
        successful activation and testing, we're proceeding with the Mars deployment timeline.*

        *In six months, when the colonists step into their greenhouse and see green leaves
        growing in Martian soil, they'll have you to thank.*

        *You didn't just run a simulation. You proved it could work.*

        *That's what pioneers do.*

        *Fair winds and clear skies, Specialist.*

        *— Dr. Sarah Chen*
        *Director of Life Support Systems*
        *Project EDEN"*
        """)

        st.balloons()

    def _render_monitoring_tab(self):
        """Render real-time monitoring dashboard"""

        st.header("Real-Time Environmental Monitoring")
        st.caption("Live sensor readings and environmental conditions")

        # Get current state
        env_state = self.simulation.get_state()
        actuators = self.simulation.get_actuators()

        # Top metrics row with enhanced help text
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            temp_delta = env_state.temperature - st.session_state.temp_setpoint
            st.metric(
                "🌡️ Temperature",
                f"{env_state.temperature:.1f} °C",
                f"{temp_delta:+.1f} °C",
                delta_color="inverse",
                help=f"Current: {env_state.temperature:.1f}°C | Target: {st.session_state.temp_setpoint:.1f}°C | Deviation: {temp_delta:+.1f}°C"
            )

        with col2:
            moisture_delta = env_state.moisture - st.session_state.moisture_setpoint
            st.metric(
                "💧 Soil Moisture",
                f"{env_state.moisture:.1f} %",
                f"{moisture_delta:+.1f} %",
                delta_color="inverse",
                help=f"Current: {env_state.moisture:.1f}% | Target: {st.session_state.moisture_setpoint:.1f}% | Deviation: {moisture_delta:+.1f}%"
            )

        with col3:
            st.metric(
                "💨 Humidity",
                f"{env_state.humidity:.1f} %",
                help="Relative humidity inside greenhouse. High humidity (>80%) may cause condensation and plant diseases."
            )

        with col4:
            st.metric(
                "🌪️ Airflow",
                f"{env_state.airflow:.2f}",
                help="Air circulation rate (arbitrary units). Higher values indicate better ventilation and CO₂ exchange."
            )

        st.divider()

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            self._render_temperature_chart()

        with col2:
            self._render_moisture_chart()

        st.divider()

        # Actuator status with enhanced visual design
        st.subheader("🔧 Actuator Status")
        st.caption("Current state of all greenhouse equipment")

        col1, col2, col3, col4 = st.columns(4)

        fan = actuators.get(ActuatorType.FAN)
        heater = actuators.get(ActuatorType.HEATER)
        pump = actuators.get(ActuatorType.PUMP)
        vent = actuators.get(ActuatorType.VENT)

        with col1:
            fan_status = "🟢 ON" if fan and fan.enabled else "⚪ OFF"
            fan_value = fan.value if fan else 0
            st.write(f"**💨 Fan:** {fan_status}")
            st.progress(fan_value / 100.0)
            st.caption(f"Speed: {fan_value:.0f}% | Cooling & ventilation")

        with col2:
            heater_status = "🟢 ON" if heater and heater.enabled else "⚪ OFF"
            heater_value = heater.value if heater else 0
            st.write(f"**🔥 Heater:** {heater_status}")
            st.progress(heater_value / 100.0)
            st.caption(f"Power: {heater_value:.0f}% | Temperature control")

        with col3:
            pump_status = "🟢 ON" if pump and pump.enabled else "⚪ OFF"
            st.write(f"**💧 Pump:** {pump_status}")
            if pump and pump.enabled:
                st.write(f"⏱️ {pump.runtime_seconds:.0f}s")
                st.caption("Watering in progress")
            else:
                st.write("⏸️ Idle")
                st.caption("Ready to water")

        with col4:
            vent_value = vent.value if vent else 90
            vent_percent = (vent_value / 180.0) * 100
            st.write(f"**🪟 Vent Position:**")
            st.progress(vent_value / 180.0)
            st.caption(f"{vent_value:.0f}° ({vent_percent:.0f}% open)")

    def _render_control_tab(self):
        """Render control parameters and settings"""

        st.header("Control Parameters & Settings")

        # Control mode selection
        st.subheader("🎯 Control Mode")

        mode_names = {
            ControlMode.MANUAL: "Manual Control",
            ControlMode.OPEN_LOOP: "Open-Loop (Threshold)",
            ControlMode.CLOSED_LOOP: "Closed-Loop (Feedback)",
            ControlMode.FEEDFORWARD: "Feed-Forward (Predictive)",
            ControlMode.PID: "PID Control (Advanced)"
        }

        selected_mode = st.selectbox(
            "Select Control Strategy",
            options=list(mode_names.keys()),
            format_func=lambda x: mode_names[x],
            index=list(mode_names.keys()).index(st.session_state.current_mode),
            help="Different control strategies from simple to advanced"
        )

        if selected_mode != st.session_state.current_mode:
            st.session_state.current_mode = selected_mode
            self._update_control_mode(selected_mode)

        st.divider()

        # Setpoints with validation and warnings
        st.subheader("🎚️ Setpoints")
        st.caption("Set target values for temperature and moisture control")

        col1, col2 = st.columns(2)

        with col1:
            temp_setpoint = st.slider(
                "Temperature Setpoint (°C)",
                min_value=10.0,
                max_value=40.0,
                value=st.session_state.temp_setpoint,
                step=0.5,
                help="Target temperature (10-40°C). Typical greenhouse range: 18-28°C"
            )

            # Validation warnings for temperature
            if temp_setpoint < 15.0:
                st.warning("⚠️ Low temperature setpoint may slow plant growth")
            elif temp_setpoint > 35.0:
                st.warning("⚠️ High temperature setpoint may stress plants")
            elif 18.0 <= temp_setpoint <= 28.0:
                st.success("✅ Optimal temperature range for most plants")

            if temp_setpoint != st.session_state.temp_setpoint:
                # Validate range
                if 10.0 <= temp_setpoint <= 40.0:
                    st.session_state.temp_setpoint = temp_setpoint
                    # Send to Arduino if connected
                    if st.session_state.arduino_connected and st.session_state.arduino:
                        st.session_state.arduino.send_command('SET_SETPOINT', ['TEMP', str(temp_setpoint)])
                    st.info(f"✅ Temperature setpoint updated to {temp_setpoint:.1f}°C")
                else:
                    st.error(f"❌ Invalid temperature: {temp_setpoint}°C. Must be between 10-40°C")

        with col2:
            moisture_setpoint = st.slider(
                "Moisture Setpoint (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.moisture_setpoint,
                step=1.0,
                help="Target soil moisture (0-100%). Typical range: 40-70%"
            )

            # Validation warnings for moisture
            if moisture_setpoint < 20.0:
                st.warning("⚠️ Low moisture may cause plant water stress")
            elif moisture_setpoint > 80.0:
                st.warning("⚠️ High moisture may cause root rot and fungal issues")
            elif 40.0 <= moisture_setpoint <= 70.0:
                st.success("✅ Optimal moisture range for most plants")

            if moisture_setpoint != st.session_state.moisture_setpoint:
                # Validate range
                if 0.0 <= moisture_setpoint <= 100.0:
                    st.session_state.moisture_setpoint = moisture_setpoint
                    # Send to Arduino if connected
                    if st.session_state.arduino_connected and st.session_state.arduino:
                        st.session_state.arduino.send_command('SET_SETPOINT', ['MOISTURE', str(moisture_setpoint)])
                    st.info(f"✅ Moisture setpoint updated to {moisture_setpoint:.1f}%")
                else:
                    st.error(f"❌ Invalid moisture: {moisture_setpoint}%. Must be between 0-100%")

        st.divider()

        # PID tuning (only visible in PID mode)
        if selected_mode == ControlMode.PID:
            self._render_pid_tuning()

        # Manual controls (only visible in manual mode)
        if selected_mode == ControlMode.MANUAL:
            self._render_manual_controls()

    def _render_pid_tuning(self):
        """Render PID parameter tuning interface with validation"""

        st.subheader("🎛️ PID Tuning")

        st.info("""
        **PID Controller Tuning:**
        - **Kp (Proportional)**: Immediate response to error. Higher = faster but more overshoot.
        - **Ki (Integral)**: Eliminates steady-state error. Higher = faster settling but can overshoot.
        - **Kd (Derivative)**: Dampens oscillations. Higher = less overshoot but sensitive to noise.

        **Tuning Tips:**
        1. Start with Kp only (Ki=0, Kd=0)
        2. Increase until oscillation, then reduce by 50%
        3. Add Ki to eliminate offset
        4. Add Kd to reduce overshoot
        """)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Temperature PID**")

            temp_kp = st.number_input(
                "Kp (Proportional Gain)",
                value=st.session_state.temp_kp,
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                key="temp_kp_input",
                help="Proportional gain (0-10). Typical range: 0.5-2.0"
            )
            temp_ki = st.number_input(
                "Ki (Integral Gain)",
                value=st.session_state.temp_ki,
                min_value=0.0,
                max_value=5.0,
                step=0.01,
                key="temp_ki_input",
                help="Integral gain (0-5). Typical range: 0.01-0.5"
            )
            temp_kd = st.number_input(
                "Kd (Derivative Gain)",
                value=st.session_state.temp_kd,
                min_value=0.0,
                max_value=2.0,
                step=0.01,
                key="temp_kd_input",
                help="Derivative gain (0-2). Typical range: 0.01-0.2"
            )

            # Validation warnings
            if temp_kp > 5.0:
                st.warning("⚠️ High Kp may cause oscillations")
            if temp_ki > 1.0:
                st.warning("⚠️ High Ki may cause overshoot and instability")
            if temp_kd > 1.0:
                st.warning("⚠️ High Kd may amplify noise")

            if st.button("Apply Temperature PID", key="apply_temp_pid", type="primary"):
                # Validate all parameters are non-negative
                if temp_kp >= 0 and temp_ki >= 0 and temp_kd >= 0:
                    st.session_state.temp_kp = temp_kp
                    st.session_state.temp_ki = temp_ki
                    st.session_state.temp_kd = temp_kd

                    # Send to Arduino
                    if st.session_state.arduino_connected and st.session_state.arduino:
                        st.session_state.arduino.send_command('SET_PID', ['TEMP', str(temp_kp), str(temp_ki), str(temp_kd)])

                    st.success(f"✅ Temperature PID updated: Kp={temp_kp:.2f}, Ki={temp_ki:.3f}, Kd={temp_kd:.3f}")
                else:
                    st.error("❌ All PID parameters must be non-negative")

        with col2:
            st.write("**Moisture PID**")

            moisture_kp = st.number_input(
                "Kp (Proportional Gain)",
                value=st.session_state.moisture_kp,
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                key="moisture_kp_input",
                help="Proportional gain (0-10). Typical range: 0.5-1.5"
            )
            moisture_ki = st.number_input(
                "Ki (Integral Gain)",
                value=st.session_state.moisture_ki,
                min_value=0.0,
                max_value=5.0,
                step=0.01,
                key="moisture_ki_input",
                help="Integral gain (0-5). Typical range: 0.01-0.2"
            )
            moisture_kd = st.number_input(
                "Kd (Derivative Gain)",
                value=st.session_state.moisture_kd,
                min_value=0.0,
                max_value=2.0,
                step=0.01,
                key="moisture_kd_input",
                help="Derivative gain (0-2). Typical range: 0.01-0.1"
            )

            # Validation warnings
            if moisture_kp > 5.0:
                st.warning("⚠️ High Kp may cause oscillations")
            if moisture_ki > 1.0:
                st.warning("⚠️ High Ki may cause overshoot and instability")
            if moisture_kd > 1.0:
                st.warning("⚠️ High Kd may amplify noise")

            if st.button("Apply Moisture PID", key="apply_moisture_pid", type="primary"):
                # Validate all parameters are non-negative
                if moisture_kp >= 0 and moisture_ki >= 0 and moisture_kd >= 0:
                    st.session_state.moisture_kp = moisture_kp
                    st.session_state.moisture_ki = moisture_ki
                    st.session_state.moisture_kd = moisture_kd

                    # Send to Arduino
                    if st.session_state.arduino_connected and st.session_state.arduino:
                        st.session_state.arduino.send_command('SET_PID', ['MOISTURE', str(moisture_kp), str(moisture_ki), str(moisture_kd)])

                    st.success(f"✅ Moisture PID updated: Kp={moisture_kp:.2f}, Ki={moisture_ki:.3f}, Kd={moisture_kd:.3f}")
                else:
                    st.error("❌ All PID parameters must be non-negative")

    def _render_manual_controls(self):
        """Render manual actuator controls"""

        st.subheader("🕹️ Manual Actuator Control")

        st.warning("Manual mode: Control actuators directly. Automatic control is disabled.")

        col1, col2, col3 = st.columns(3)

        with col1:
            fan_speed = st.slider(
                "Fan Speed (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.manual_fan_speed,
                step=5.0,
                key="manual_fan_slider"
            )

            if fan_speed != st.session_state.manual_fan_speed:
                st.session_state.manual_fan_speed = fan_speed
                self.simulation.set_actuator(ActuatorType.FAN, fan_speed > 0, fan_speed)

                # Send to Arduino
                if st.session_state.arduino_connected and st.session_state.arduino:
                    st.session_state.arduino.send_command('SET_ACTUATOR', ['FAN', str(fan_speed)])

        with col2:
            heater_on = st.checkbox(
                "Heater ON/OFF",
                value=st.session_state.manual_heater,
                key="manual_heater_checkbox"
            )

            if heater_on != st.session_state.manual_heater:
                st.session_state.manual_heater = heater_on
                self.simulation.set_actuator(ActuatorType.HEATER, heater_on, 100.0 if heater_on else 0.0)

                # Send to Arduino
                if st.session_state.arduino_connected and st.session_state.arduino:
                    st.session_state.arduino.send_command('SET_ACTUATOR', ['HEATER', '100' if heater_on else '0'])

        with col3:
            if st.button("💧 Pulse Pump (1s)", key="manual_pump_button"):
                st.session_state.manual_pump = True
                self.simulation.set_actuator(ActuatorType.PUMP, True, 100.0)

                # Send to Arduino
                if st.session_state.arduino_connected and st.session_state.arduino:
                    st.session_state.arduino.send_command('SET_ACTUATOR', ['PUMP', '100'])

                # Auto-off after 1 second (handled by Arduino/simulation)
                st.info("Pump activated for 1 second")

    def _render_simulation_tab(self):
        """Render simulation controls and parameters"""

        st.header("Simulation Controls & Parameters")
        st.caption("Configure simulation environment and inject test scenarios")

        # Simulation status with enhanced performance metrics
        stats = self.simulation.get_statistics()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "⏱️ Simulation Time",
                f"{stats['sim_time']:.0f} s",
                help="Total elapsed simulation time (may differ from real time)"
            )

        with col2:
            update_rate = stats['updates_per_second']
            target_rate = 10.0  # From config
            rate_delta = update_rate - target_rate
            st.metric(
                "🔄 Update Rate",
                f"{update_rate:.1f} Hz",
                f"{rate_delta:+.1f} Hz",
                delta_color="normal",
                help=f"Current: {update_rate:.1f} Hz | Target: {target_rate:.1f} Hz"
            )

        with col3:
            if 'avg_update_time_ms' in stats:
                avg_time = stats['avg_update_time_ms']
                st.metric(
                    "⚡ Avg Update Time",
                    f"{avg_time:.2f} ms",
                    help="Average time to compute each simulation step. Lower is better."
                )
            else:
                status = "🟢 Running" if stats['running'] else "🔴 Stopped"
                st.metric("Status", status)

        with col4:
            if 'performance_ratio' in stats:
                perf_ratio = stats['performance_ratio']
                perf_delta = perf_ratio - 100.0
                st.metric(
                    "📊 Performance",
                    f"{perf_ratio:.0f}%",
                    f"{perf_delta:+.0f}%",
                    delta_color="normal",
                    help="Percentage of target update rate achieved. 100% = perfect real-time. <80% = lagging behind."
                )
            else:
                st.metric("Updates", f"{stats.get('total_updates', 0)}")

        st.divider()

        # Performance details in expander for advanced users
        with st.expander("🔍 Advanced Performance Metrics", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Timing Statistics:**")
                if 'avg_update_time_ms' in stats:
                    st.write(f"• Average update: {stats['avg_update_time_ms']:.3f} ms")
                if 'max_update_time_ms' in stats:
                    st.write(f"• Maximum update: {stats['max_update_time_ms']:.3f} ms")
                st.write(f"• Update rate: {stats['updates_per_second']:.2f} Hz")
            with col2:
                st.write("**Simulation State:**")
                st.write(f"• Total updates: {stats.get('total_updates', 0)}")
                st.write(f"• Running: {'Yes' if stats['running'] else 'No'}")
                if 'performance_ratio' in stats:
                    st.write(f"• Performance: {stats['performance_ratio']:.1f}%")

        st.divider()

        # Environmental parameters
        st.subheader("🌍 Environmental Parameters")

        ambient_temp = st.slider(
            "Ambient Temperature (°C)",
            min_value=-10.0,
            max_value=50.0,
            value=20.0,
            step=1.0,
            help="Outside temperature affecting greenhouse"
        )

        self.simulation.set_ambient_temperature(ambient_temp)

        st.divider()

        # Failure injection with enhanced UI
        st.subheader("⚠️ Failure Mode Injection")
        st.caption("Test system robustness by simulating equipment failures and environmental stress")

        failure_sim = self.simulation.get_failure_simulator()

        # Help section in expander
        with st.expander("ℹ️ About Failure Mode Testing", expanded=False):
            st.markdown("""
            **Why Test Failures?**
            Understanding how your greenhouse system responds to equipment failures and environmental stress
            is crucial for building reliable control algorithms.

            **Available Failure Types:**
            - **Sensor Stuck**: Sensor reading freezes at current value
            - **Sensor Noisy**: Sensor produces random fluctuations
            - **Actuator Stuck On**: Equipment stays on regardless of control signals
            - **Actuator Degraded**: Equipment operates at reduced efficiency
            - **Heatwave**: Extreme high ambient temperature event
            - **Reservoir Empty**: Water pump runs dry

            **Best Practices:**
            1. Test one failure at a time to understand individual impacts
            2. Observe how PID controllers respond to sensor failures
            3. Check if alerts are generated appropriately
            4. Verify graceful degradation (system stays safe)
            """)

        col1, col2 = st.columns(2)

        with col1:
            failure_type = st.selectbox(
                "Failure Type",
                ["Sensor Stuck", "Sensor Noisy", "Actuator Stuck On", "Actuator Degraded", "Heatwave", "Reservoir Empty"],
                help="Type of equipment or environmental failure to simulate"
            )

            component = st.selectbox(
                "Affected Component",
                ["temperature", "moisture", "fan", "heater", "pump", "environment"],
                help="Which sensor, actuator, or system component should experience the failure"
            )

            duration = st.slider(
                "Duration (seconds)",
                min_value=10,
                max_value=300,
                value=60,
                step=10,
                help="How long the failure condition will persist before auto-recovery"
            )

        with col2:
            st.write("")  # Spacing
            st.write("")

            if st.button("💥 Inject Failure", type="primary", use_container_width=True):
                self._inject_failure(failure_type, component, duration)
                st.success(f"✅ Injected **{failure_type}** on **{component}** for **{duration}s**")
                st.info(f"💡 Watch the monitoring tab to observe system response")

            if st.button("🔄 Clear All Failures", use_container_width=True):
                failure_sim.clear_all_failures()
                st.session_state.active_failures = []
                st.success("✅ All failures cleared - system returned to normal")

        # Show active failures with enhanced visualization
        active_failures = failure_sim.get_active_failures()
        if active_failures:
            st.divider()
            st.error(f"**⚠️ Active Failures: {len(active_failures)}**")

            for failure_id, scenario in active_failures.items():
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"🔴 **{scenario.failure_type.name}**")
                    with col2:
                        st.write(f"Component: `{scenario.affected_component}`")
                    with col3:
                        st.write(f"⏱️ Active")
        else:
            st.success("✅ No active failures - system operating normally")

    def _render_data_tab(self):
        """Render data logging and export interface"""

        st.header("Data Logging & Export")

        # Recent data summary
        recent_data = self.data_logger.get_recent_data(hours=1.0, limit=100)

        st.subheader("📊 Recent Data Summary")
        st.write(f"Records in last hour: {len(recent_data)}")

        if recent_data:
            df = pd.DataFrame(recent_data)
            st.dataframe(df.tail(20), use_container_width=True)

            # Export options
            st.subheader("💾 Export Data")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Export as CSV"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "Download CSV",
                        csv,
                        "greenhouse_data.csv",
                        "text/csv"
                    )

            with col2:
                hours = st.number_input("Hours of data", min_value=1, max_value=24, value=1)
                if st.button(f"Fetch {hours}h data"):
                    data = self.data_logger.get_recent_data(hours=float(hours))
                    st.write(f"Retrieved {len(data)} records")

        # Events log
        st.divider()
        st.subheader("📋 System Events")

        events = self.data_logger.get_events(hours=24.0)

        if events:
            event_df = pd.DataFrame(events)
            st.dataframe(event_df, use_container_width=True)
        else:
            st.info("No events logged yet")

    def _render_temperature_chart(self):
        """Render temperature history chart"""

        st.subheader("🌡️ Temperature History")

        if len(st.session_state.temp_history) > 0:
            fig, ax = plt.subplots(figsize=(10, 4))

            ax.plot(st.session_state.time_history, st.session_state.temp_history,
                   label='Temperature', color='#ff6b6b', linewidth=2)

            # Plot setpoint
            ax.axhline(y=st.session_state.temp_setpoint, color='#4ecdc4',
                      linestyle='--', label='Setpoint', linewidth=1.5)

            ax.set_xlabel('Time')
            ax.set_ylabel('Temperature (°C)')
            ax.legend()
            ax.grid(True, alpha=0.3)

            st.pyplot(fig)
            plt.close()
        else:
            st.info("Collecting data...")

    def _render_moisture_chart(self):
        """Render moisture history chart"""

        st.subheader("💧 Moisture History")

        if len(st.session_state.moisture_history) > 0:
            fig, ax = plt.subplots(figsize=(10, 4))

            ax.plot(st.session_state.time_history, st.session_state.moisture_history,
                   label='Moisture', color='#4ecdc4', linewidth=2)

            # Plot setpoint
            ax.axhline(y=st.session_state.moisture_setpoint, color='#ff6b6b',
                      linestyle='--', label='Setpoint', linewidth=1.5)

            ax.set_xlabel('Time')
            ax.set_ylabel('Moisture (%)')
            ax.set_ylim(0, 100)
            ax.legend()
            ax.grid(True, alpha=0.3)

            st.pyplot(fig)
            plt.close()
        else:
            st.info("Collecting data...")

    def _update_data(self):
        """Update data from simulation or Arduino"""

        env_state = self.simulation.get_state()

        # Update history
        current_time = datetime.now()

        st.session_state.temp_history.append(env_state.temperature)
        st.session_state.moisture_history.append(env_state.moisture)
        st.session_state.time_history.append(current_time)

        # Limit history size
        if len(st.session_state.temp_history) > st.session_state.history_size:
            st.session_state.temp_history.pop(0)
            st.session_state.moisture_history.pop(0)
            st.session_state.time_history.pop(0)

        # TODO: If Arduino connected, fetch real sensor data

    def _connect_arduino(self, port: str):
        """Connect to Arduino"""
        try:
            arduino = ArduinoInterface(port=port)
            if arduino.connect():
                st.session_state.arduino = arduino
                st.session_state.arduino_connected = True
                st.success(f"Connected to Arduino on {port}")
            else:
                st.error(f"Failed to connect to {port}")
        except Exception as e:
            st.error(f"Connection error: {e}")

    def _disconnect_arduino(self):
        """Disconnect from Arduino"""
        if st.session_state.arduino:
            st.session_state.arduino.disconnect()
            st.session_state.arduino = None
            st.session_state.arduino_connected = False
            st.info("Disconnected from Arduino")

    def _update_control_mode(self, mode: ControlMode):
        """Update control mode"""
        # Send to Arduino if connected
        if st.session_state.arduino_connected and st.session_state.arduino:
            mode_value = mode.value - 1  # Arduino uses 0-indexed modes
            st.session_state.arduino.send_command('SET_MODE', [str(mode_value)])

        st.info(f"Control mode changed to: {mode.name}")

    def _reset_system(self):
        """Reset system to initial state"""
        self.simulation.reset()
        st.session_state.temp_history = []
        st.session_state.moisture_history = []
        st.session_state.time_history = []
        st.session_state.alerts = []
        st.success("System reset complete")

    def _toggle_pause(self):
        """Toggle simulation pause/resume"""
        if self.simulation.running:
            self.simulation.pause()
        else:
            self.simulation.resume()

    def _inject_failure(self, failure_type: str, component: str, duration: int):
        """Inject a failure into simulation"""
        from ..simulation.failure_modes import FailureType

        failure_map = {
            "Sensor Stuck": FailureType.SENSOR_STUCK,
            "Sensor Noisy": FailureType.SENSOR_NOISY,
            "Actuator Stuck On": FailureType.ACTUATOR_STUCK_ON,
            "Actuator Degraded": FailureType.ACTUATOR_DEGRADED,
            "Heatwave": FailureType.HEATWAVE,
            "Reservoir Empty": FailureType.RESERVOIR_EMPTY
        }

        failure_sim = self.simulation.get_failure_simulator()
        failure_sim.inject_failure(
            failure_map[failure_type],
            component,
            severity=1.0,
            duration=float(duration)
        )

        st.session_state.active_failures.append({
            'type': failure_type,
            'component': component,
            'time': datetime.now()
        })
