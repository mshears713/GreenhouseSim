"""
Protocol utilities for building and parsing Arduino messages

Helper functions for constructing properly formatted commands
and parsing responses.
"""

from typing import List, Optional
from ..data.models import ControlMode


class CommandBuilder:
    """
    Helper class for building Arduino commands

    Provides methods for constructing properly formatted
    command strings for common operations.
    """

    @staticmethod
    def set_mode(mode: ControlMode) -> str:
        """Build SET_MODE command"""
        return f"CMD:SET_MODE,{mode.value - 1}\n"

    @staticmethod
    def set_temperature_setpoint(temp: float) -> str:
        """Build SET_SETPOINT command for temperature"""
        return f"CMD:SET_SETPOINT,TEMP,{temp:.1f}\n"

    @staticmethod
    def set_moisture_setpoint(moisture: float) -> str:
        """Build SET_SETPOINT command for moisture"""
        return f"CMD:SET_SETPOINT,MOISTURE,{moisture:.1f}\n"

    @staticmethod
    def set_fan(speed_percent: float) -> str:
        """Build SET_ACTUATOR command for fan"""
        return f"CMD:SET_ACTUATOR,FAN,{speed_percent:.1f}\n"

    @staticmethod
    def set_heater(enabled: bool) -> str:
        """Build SET_ACTUATOR command for heater"""
        value = "100" if enabled else "0"
        return f"CMD:SET_ACTUATOR,HEATER,{value}\n"

    @staticmethod
    def set_pump(enabled: bool) -> str:
        """Build SET_ACTUATOR command for pump"""
        value = "100" if enabled else "0"
        return f"CMD:SET_ACTUATOR,PUMP,{value}\n"

    @staticmethod
    def set_pid_params(
        controller_type: str,
        kp: float,
        ki: float,
        kd: float
    ) -> str:
        """Build SET_PID command"""
        return f"CMD:SET_PID,{controller_type},{kp:.4f},{ki:.4f},{kd:.4f}\n"

    @staticmethod
    def enable_system() -> str:
        """Build ENABLE command"""
        return "CMD:ENABLE\n"

    @staticmethod
    def disable_system() -> str:
        """Build DISABLE command"""
        return "CMD:DISABLE\n"

    @staticmethod
    def request_status() -> str:
        """Build STATUS request command"""
        return "CMD:STATUS\n"

    @staticmethod
    def calibrate_moisture(calibration_type: str) -> str:
        """Build CALIBRATE command for moisture sensor"""
        return f"CMD:CALIBRATE,MOISTURE,{calibration_type}\n"

    @staticmethod
    def test_actuators() -> str:
        """Build TEST command"""
        return "CMD:TEST\n"

    @staticmethod
    def reset_system() -> str:
        """Build RESET command"""
        return "CMD:RESET\n"


class ProtocolParser:
    """
    Helper class for parsing Arduino messages

    Provides utility methods for extracting specific
    data from parsed messages.
    """

    @staticmethod
    def extract_sensor_value(message_content: dict) -> Optional[float]:
        """Extract sensor value from parsed message"""
        return message_content.get('value')

    @staticmethod
    def extract_sensor_type(message_content: dict) -> Optional[str]:
        """Extract sensor type from parsed message"""
        return message_content.get('sensor_type')

    @staticmethod
    def extract_actuator_state(message_content: dict) -> Optional[bool]:
        """Extract actuator enabled state from parsed message"""
        return message_content.get('enabled')

    @staticmethod
    def extract_error_info(message_content: dict) -> tuple[int, str]:
        """Extract error code and description"""
        code = message_content.get('error_code', 0)
        desc = message_content.get('description', '')
        return code, desc
