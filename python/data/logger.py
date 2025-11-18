"""
Data Logging Utilities for Smart Mini Greenhouse Control System

This module provides logging functionality for sensor readings,
actuator states, and system events. Supports both CSV and SQLite formats.

Educational Note:
Logging is essential for:
- System monitoring and debugging
- Performance analysis and optimization
- Control algorithm tuning
- Historical data review and reporting
"""

import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .models import (
    GreenhouseSnapshot,
    SensorReading,
    ActuatorState,
    EnvironmentState,
    SystemStatus
)


# Configure Python logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataLogger:
    """
    Main data logging class supporting CSV and SQLite output

    Handles automatic file rotation, data buffering, and
    multiple output formats.

    Educational Note:
    Using both CSV and SQLite provides flexibility:
    - CSV: Human-readable, easy to import to Excel/spreadsheets
    - SQLite: Queryable, better for large datasets
    """

    def __init__(
        self,
        log_dir: str = "./data/logs",
        db_path: str = "./data/greenhouse.db",
        enable_csv: bool = True,
        enable_sqlite: bool = True,
        buffer_size: int = 10
    ):
        """
        Initialize data logger

        Args:
            log_dir: Directory for CSV log files
            db_path: Path to SQLite database
            enable_csv: Enable CSV logging
            enable_sqlite: Enable SQLite logging
            buffer_size: Number of records to buffer before writing
        """
        self.log_dir = Path(log_dir)
        self.db_path = Path(db_path)
        self.enable_csv = enable_csv
        self.enable_sqlite = enable_sqlite
        self.buffer_size = buffer_size

        # Create directories if they don't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Buffer for batch writing
        self.buffer: List[GreenhouseSnapshot] = []

        # Current CSV file info
        self.current_csv_file: Optional[Path] = None
        self.csv_writer: Optional[csv.DictWriter] = None
        self.csv_file_handle = None

        # Initialize SQLite database
        if self.enable_sqlite:
            self._init_database()

        # Start new CSV file
        if self.enable_csv:
            self._start_new_csv_file()

        logger.info(f"DataLogger initialized: CSV={enable_csv}, SQLite={enable_sqlite}")

    def _init_database(self):
        """
        Initialize SQLite database schema

        Creates tables for:
        - Snapshots (time-series data)
        - Events (system events, errors, mode changes)
        - Calibration (sensor calibration history)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Snapshots table (main time-series data)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temperature REAL,
                moisture REAL,
                humidity REAL,
                airflow REAL,
                light_level REAL,
                ambient_temp REAL,
                fan_enabled INTEGER,
                fan_value REAL,
                heater_enabled INTEGER,
                heater_value REAL,
                pump_enabled INTEGER,
                pump_value REAL,
                vent_value REAL,
                temp_setpoint REAL,
                moisture_setpoint REAL,
                control_mode TEXT,
                system_enabled INTEGER,
                error_state INTEGER,
                is_simulated INTEGER
            )
        ''')

        # Events table (errors, mode changes, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT,
                message TEXT,
                details TEXT
            )
        ''')

        # Calibration table (sensor calibration history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calibration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                calibration_type TEXT,
                value REAL,
                notes TEXT
            )
        ''')

        # Create indices for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp
            ON snapshots(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON events(timestamp)
        ''')

        conn.commit()
        conn.close()
        logger.info("SQLite database initialized")

    def _start_new_csv_file(self):
        """
        Start a new CSV file with timestamp in filename

        CSV files are named: greenhouse_YYYYMMDD_HHMMSS.csv
        """
        # Close previous file if open
        if self.csv_file_handle:
            self.csv_file_handle.close()

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_csv_file = self.log_dir / f"greenhouse_{timestamp}.csv"

        # Define CSV columns
        fieldnames = [
            'timestamp',
            'temperature', 'moisture', 'humidity', 'airflow', 'light_level',
            'ambient_temp',
            'fan_enabled', 'fan_value',
            'heater_enabled', 'heater_value',
            'pump_enabled', 'pump_value',
            'vent_value',
            'temp_setpoint', 'moisture_setpoint',
            'control_mode', 'system_enabled', 'error_state', 'is_simulated'
        ]

        # Open file and create CSV writer
        self.csv_file_handle = open(self.current_csv_file, 'w', newline='')
        self.csv_writer = csv.DictWriter(self.csv_file_handle, fieldnames=fieldnames)
        self.csv_writer.writeheader()

        logger.info(f"Started new CSV file: {self.current_csv_file}")

    def log_snapshot(self, snapshot: GreenhouseSnapshot):
        """
        Log a complete system snapshot

        Args:
            snapshot: GreenhouseSnapshot object to log
        """
        # Add to buffer
        self.buffer.append(snapshot)

        # Write if buffer is full
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self):
        """
        Write buffered data to disk

        Educational Note:
        Buffering reduces I/O operations, improving performance.
        Flush periodically or when buffer is full.
        """
        if not self.buffer:
            return

        try:
            # Write to CSV
            if self.enable_csv and self.csv_writer:
                for snapshot in self.buffer:
                    row = snapshot.to_csv_row()
                    self.csv_writer.writerow(row)
                self.csv_file_handle.flush()

            # Write to SQLite
            if self.enable_sqlite:
                self._write_to_sqlite(self.buffer)

            logger.debug(f"Flushed {len(self.buffer)} records to disk")
            self.buffer.clear()

        except Exception as e:
            logger.error(f"Error flushing data: {e}")

    def _write_to_sqlite(self, snapshots: List[GreenhouseSnapshot]):
        """Write multiple snapshots to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for snapshot in snapshots:
            # Extract data from snapshot
            env = snapshot.environment
            status = snapshot.system_status
            params = snapshot.control_params

            # Get actuator values
            fan = snapshot.actuators.get('FAN')
            heater = snapshot.actuators.get('HEATER')
            pump = snapshot.actuators.get('PUMP')
            vent = snapshot.actuators.get('VENT')

            cursor.execute('''
                INSERT INTO snapshots (
                    timestamp, temperature, moisture, humidity, airflow,
                    light_level, ambient_temp,
                    fan_enabled, fan_value,
                    heater_enabled, heater_value,
                    pump_enabled, pump_value,
                    vent_value,
                    temp_setpoint, moisture_setpoint,
                    control_mode, system_enabled, error_state, is_simulated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.timestamp.isoformat(),
                env.temperature,
                env.moisture,
                env.humidity,
                env.airflow,
                env.light_level,
                env.ambient_temperature,
                fan.enabled if fan else 0,
                fan.value if fan else 0,
                heater.enabled if heater else 0,
                heater.value if heater else 0,
                pump.enabled if pump else 0,
                pump.value if pump else 0,
                vent.value if vent else 0,
                params.temperature_setpoint,
                params.moisture_setpoint,
                status.control_mode.name,
                status.enabled,
                status.error_state,
                env.is_simulated
            ))

        conn.commit()
        conn.close()

    def log_event(
        self,
        event_type: str,
        message: str,
        severity: str = "INFO",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a system event (error, mode change, calibration, etc.)

        Args:
            event_type: Type of event (ERROR, MODE_CHANGE, CALIBRATION, etc.)
            message: Human-readable message
            severity: INFO, WARNING, ERROR, CRITICAL
            details: Additional details as dictionary
        """
        if not self.enable_sqlite:
            logger.warning(f"Event logging requires SQLite: {event_type} - {message}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        details_str = str(details) if details else None

        cursor.execute('''
            INSERT INTO events (timestamp, event_type, severity, message, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            event_type,
            severity,
            message,
            details_str
        ))

        conn.commit()
        conn.close()

        # Also log to Python logger
        log_func = getattr(logger, severity.lower(), logger.info)
        log_func(f"{event_type}: {message}")

    def log_calibration(
        self,
        sensor_type: str,
        calibration_type: str,
        value: float,
        notes: Optional[str] = None
    ):
        """
        Log sensor calibration event

        Args:
            sensor_type: Type of sensor (TEMPERATURE, MOISTURE, etc.)
            calibration_type: DRY, WET, OFFSET, SCALE, etc.
            value: Calibration value
            notes: Additional notes
        """
        if not self.enable_sqlite:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO calibration (timestamp, sensor_type, calibration_type, value, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            sensor_type,
            calibration_type,
            value,
            notes
        ))

        conn.commit()
        conn.close()

        logger.info(f"Calibration logged: {sensor_type} {calibration_type} = {value}")

    def get_recent_data(
        self,
        hours: float = 1.0,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent data from database

        Args:
            hours: Number of hours of data to retrieve
            limit: Maximum number of records (None = all)

        Returns:
            List of snapshot dictionaries
        """
        if not self.enable_sqlite:
            logger.warning("get_recent_data requires SQLite")
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()

        # Calculate timestamp threshold
        from datetime import timedelta
        threshold = datetime.now() - timedelta(hours=hours)

        query = '''
            SELECT * FROM snapshots
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        '''

        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query, (threshold.isoformat(),))
        rows = cursor.fetchall()

        conn.close()

        return [dict(row) for row in rows]

    def get_events(
        self,
        hours: float = 24.0,
        severity: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve system events

        Args:
            hours: Number of hours of events to retrieve
            severity: Filter by severity (INFO, WARNING, ERROR, CRITICAL)
            event_type: Filter by event type

        Returns:
            List of event dictionaries
        """
        if not self.enable_sqlite:
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        from datetime import timedelta
        threshold = datetime.now() - timedelta(hours=hours)

        query = 'SELECT * FROM events WHERE timestamp >= ?'
        params = [threshold.isoformat()]

        if severity:
            query += ' AND severity = ?'
            params.append(severity)

        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)

        query += ' ORDER BY timestamp DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        return [dict(row) for row in rows]

    def close(self):
        """Close all file handles and flush remaining data"""
        self.flush()

        if self.csv_file_handle:
            self.csv_file_handle.close()
            self.csv_file_handle = None

        logger.info("DataLogger closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup"""
        self.close()


class EventLogger:
    """
    Simplified event-only logger

    Useful for logging errors, warnings, and status changes
    without the overhead of full snapshot logging.
    """

    def __init__(self, db_path: str = "./data/greenhouse.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event_type: str,
        message: str,
        severity: str = "INFO",
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Ensure events table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT,
                message TEXT,
                details TEXT
            )
        ''')

        details_str = str(details) if details else None

        cursor.execute('''
            INSERT INTO events (timestamp, event_type, severity, message, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            event_type,
            severity,
            message,
            details_str
        ))

        conn.commit()
        conn.close()

        # Also log to Python logger
        log_func = getattr(logger, severity.lower(), logger.info)
        log_func(f"{event_type}: {message}")


if __name__ == "__main__":
    # Example usage and testing
    from .models import (
        EnvironmentState,
        ActuatorState,
        ActuatorType,
        ControlParameters,
        SystemStatus,
        ControlMode,
        GreenhouseSnapshot
    )

    print("=== Data Logger Demo ===\n")

    # Create test data logger
    with DataLogger(
        log_dir="./test_logs",
        db_path="./test_greenhouse.db",
        enable_csv=True,
        enable_sqlite=True,
        buffer_size=5
    ) as data_logger:

        # Create and log some test snapshots
        for i in range(10):
            env = EnvironmentState(
                temperature=20.0 + i * 0.5,
                moisture=50.0 + i,
                humidity=60.0 - i * 0.5,
                airflow=float(i)
            )

            fan_state = ActuatorState(
                actuator_type=ActuatorType.FAN,
                enabled=(i % 2 == 0),
                value=float(i * 10),
                unit='%'
            )

            snapshot = GreenhouseSnapshot(
                timestamp=datetime.now(),
                environment=env,
                actuators={ActuatorType.FAN: fan_state},
                control_params=ControlParameters(),
                system_status=SystemStatus(control_mode=ControlMode.PID)
            )

            data_logger.log_snapshot(snapshot)
            print(f"Logged snapshot {i+1}")

        # Log some events
        data_logger.log_event("SYSTEM_START", "System initialized", "INFO")
        data_logger.log_event("MODE_CHANGE", "Switched to PID mode", "INFO")
        data_logger.log_event("SENSOR_ERROR", "Temperature sensor unstable", "WARNING")

        # Log calibration
        data_logger.log_calibration("MOISTURE", "DRY", 850, "Dry calibration in sand")

    print("\nFlushed and closed logger")

    # Retrieve data
    with DataLogger(db_path="./test_greenhouse.db", enable_csv=False) as retriever:
        recent = retriever.get_recent_data(hours=1.0)
        print(f"\nRetrieved {len(recent)} recent records")

        events = retriever.get_events(hours=24.0)
        print(f"Retrieved {len(events)} events")
        for event in events:
            print(f"  - {event['event_type']}: {event['message']}")

    print("\nDemo complete!")
