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
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Monitoring",
            "⚙️ Control",
            "🔬 Simulation",
            "📈 Data & Logs"
        ])

        with tab1:
            self._render_monitoring_tab()

        with tab2:
            self._render_control_tab()

        with tab3:
            self._render_simulation_tab()

        with tab4:
            self._render_data_tab()

        # Update data (simulation or Arduino)
        self._update_data()

    def _render_sidebar(self):
        """Render sidebar with system controls and status"""

        st.sidebar.header("🎛️ System Control")

        # Mode selection
        mode_option = st.sidebar.radio(
            "Operation Mode",
            ["Simulation Only", "Hardware Connected"],
            index=0 if st.session_state.simulation_mode else 1,
            help="Simulation: Test without hardware. Hardware: Connect to Arduino."
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

        # System status
        st.sidebar.divider()
        st.sidebar.subheader("📊 System Status")

        sim_status = "🟢 Running" if self.simulation.running else "🔴 Stopped"
        st.sidebar.write(f"Simulation: {sim_status}")

        if st.session_state.arduino_connected:
            st.sidebar.write("Arduino: 🟢 Connected")
        else:
            st.sidebar.write("Arduino: ⚪ Disconnected")

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

    def _render_monitoring_tab(self):
        """Render real-time monitoring dashboard"""

        st.header("Real-Time Environmental Monitoring")

        # Get current state
        env_state = self.simulation.get_state()
        actuators = self.simulation.get_actuators()

        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            temp_delta = env_state.temperature - st.session_state.temp_setpoint
            st.metric(
                "🌡️ Temperature",
                f"{env_state.temperature:.1f} °C",
                f"{temp_delta:+.1f} °C",
                delta_color="inverse"
            )

        with col2:
            moisture_delta = env_state.moisture - st.session_state.moisture_setpoint
            st.metric(
                "💧 Soil Moisture",
                f"{env_state.moisture:.1f} %",
                f"{moisture_delta:+.1f} %",
                delta_color="inverse"
            )

        with col3:
            st.metric(
                "💨 Humidity",
                f"{env_state.humidity:.1f} %",
                help="Relative humidity inside greenhouse"
            )

        with col4:
            st.metric(
                "🌪️ Airflow",
                f"{env_state.airflow:.2f}",
                help="Airflow measurement (arbitrary units)"
            )

        st.divider()

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            self._render_temperature_chart()

        with col2:
            self._render_moisture_chart()

        st.divider()

        # Actuator status
        st.subheader("🔧 Actuator Status")

        col1, col2, col3, col4 = st.columns(4)

        fan = actuators.get(ActuatorType.FAN)
        heater = actuators.get(ActuatorType.HEATER)
        pump = actuators.get(ActuatorType.PUMP)
        vent = actuators.get(ActuatorType.VENT)

        with col1:
            fan_status = "🟢 ON" if fan and fan.enabled else "⚪ OFF"
            fan_value = fan.value if fan else 0
            st.write(f"**Fan:** {fan_status}")
            st.progress(fan_value / 100.0)
            st.caption(f"Speed: {fan_value:.0f}%")

        with col2:
            heater_status = "🟢 ON" if heater and heater.enabled else "⚪ OFF"
            st.write(f"**Heater:** {heater_status}")
            st.write(f"Power: {heater.value:.0f}%" if heater and heater.enabled else "Power: 0%")

        with col3:
            pump_status = "🟢 ON" if pump and pump.enabled else "⚪ OFF"
            st.write(f"**Pump:** {pump_status}")
            if pump and pump.enabled:
                st.write(f"Runtime: {pump.runtime_seconds:.0f}s")

        with col4:
            st.write(f"**Vent Position:**")
            vent_value = vent.value if vent else 90
            st.progress(vent_value / 180.0)
            st.caption(f"{vent_value:.0f}°")

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

        # Setpoints
        st.subheader("🎚️ Setpoints")

        col1, col2 = st.columns(2)

        with col1:
            temp_setpoint = st.slider(
                "Temperature Setpoint (°C)",
                min_value=10.0,
                max_value=40.0,
                value=st.session_state.temp_setpoint,
                step=0.5,
                help="Target temperature for greenhouse"
            )

            if temp_setpoint != st.session_state.temp_setpoint:
                st.session_state.temp_setpoint = temp_setpoint
                # Send to Arduino if connected
                if st.session_state.arduino_connected and st.session_state.arduino:
                    st.session_state.arduino.send_command('SET_SETPOINT', ['TEMP', str(temp_setpoint)])

        with col2:
            moisture_setpoint = st.slider(
                "Moisture Setpoint (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.moisture_setpoint,
                step=1.0,
                help="Target soil moisture percentage"
            )

            if moisture_setpoint != st.session_state.moisture_setpoint:
                st.session_state.moisture_setpoint = moisture_setpoint
                # Send to Arduino if connected
                if st.session_state.arduino_connected and st.session_state.arduino:
                    st.session_state.arduino.send_command('SET_SETPOINT', ['MOISTURE', str(moisture_setpoint)])

        st.divider()

        # PID tuning (only visible in PID mode)
        if selected_mode == ControlMode.PID:
            self._render_pid_tuning()

        # Manual controls (only visible in manual mode)
        if selected_mode == ControlMode.MANUAL:
            self._render_manual_controls()

    def _render_pid_tuning(self):
        """Render PID parameter tuning interface"""

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

            temp_kp = st.number_input("Kp", value=st.session_state.temp_kp, min_value=0.0, max_value=10.0, step=0.1, key="temp_kp_input")
            temp_ki = st.number_input("Ki", value=st.session_state.temp_ki, min_value=0.0, max_value=5.0, step=0.01, key="temp_ki_input")
            temp_kd = st.number_input("Kd", value=st.session_state.temp_kd, min_value=0.0, max_value=2.0, step=0.01, key="temp_kd_input")

            if st.button("Apply Temperature PID", key="apply_temp_pid"):
                st.session_state.temp_kp = temp_kp
                st.session_state.temp_ki = temp_ki
                st.session_state.temp_kd = temp_kd

                # Send to Arduino
                if st.session_state.arduino_connected and st.session_state.arduino:
                    st.session_state.arduino.send_command('SET_PID', ['TEMP', str(temp_kp), str(temp_ki), str(temp_kd)])

                st.success("Temperature PID parameters updated!")

        with col2:
            st.write("**Moisture PID**")

            moisture_kp = st.number_input("Kp", value=st.session_state.moisture_kp, min_value=0.0, max_value=10.0, step=0.1, key="moisture_kp_input")
            moisture_ki = st.number_input("Ki", value=st.session_state.moisture_ki, min_value=0.0, max_value=5.0, step=0.01, key="moisture_ki_input")
            moisture_kd = st.number_input("Kd", value=st.session_state.moisture_kd, min_value=0.0, max_value=2.0, step=0.01, key="moisture_kd_input")

            if st.button("Apply Moisture PID", key="apply_moisture_pid"):
                st.session_state.moisture_kp = moisture_kp
                st.session_state.moisture_ki = moisture_ki
                st.session_state.moisture_kd = moisture_kd

                # Send to Arduino
                if st.session_state.arduino_connected and st.session_state.arduino:
                    st.session_state.arduino.send_command('SET_PID', ['MOISTURE', str(moisture_kp), str(moisture_ki), str(moisture_kd)])

                st.success("Moisture PID parameters updated!")

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

        # Simulation status
        stats = self.simulation.get_statistics()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Simulation Time", f"{stats['sim_time']:.0f} s")

        with col2:
            st.metric("Update Rate", f"{stats['updates_per_second']:.1f} Hz")

        with col3:
            status = "🟢 Running" if stats['running'] else "🔴 Stopped"
            st.metric("Status", status)

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

        # Failure injection
        st.subheader("⚠️ Failure Mode Injection")

        st.info("Inject failures to test system robustness and error handling")

        failure_sim = self.simulation.get_failure_simulator()

        col1, col2 = st.columns(2)

        with col1:
            failure_type = st.selectbox(
                "Failure Type",
                ["Sensor Stuck", "Sensor Noisy", "Actuator Stuck On", "Actuator Degraded", "Heatwave", "Reservoir Empty"],
                help="Select type of failure to inject"
            )

            component = st.selectbox(
                "Affected Component",
                ["temperature", "moisture", "fan", "heater", "pump", "environment"],
                help="Which component should fail"
            )

            duration = st.number_input(
                "Duration (seconds)",
                min_value=10,
                max_value=300,
                value=60,
                step=10,
                help="How long the failure lasts"
            )

        with col2:
            if st.button("💥 Inject Failure"):
                self._inject_failure(failure_type, component, duration)
                st.success(f"Injected {failure_type} on {component} for {duration}s")

            if st.button("✅ Clear All Failures"):
                failure_sim.clear_all_failures()
                st.session_state.active_failures = []
                st.success("All failures cleared")

        # Show active failures
        active_failures = failure_sim.get_active_failures()
        if active_failures:
            st.warning(f"**Active Failures:** {len(active_failures)}")
            for failure_id, scenario in active_failures.items():
                st.write(f"- {scenario.failure_type.name} on {scenario.affected_component}")

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
