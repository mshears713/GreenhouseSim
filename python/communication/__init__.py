"""
Communication package for Smart Mini Greenhouse Control System

This package handles serial communication with the Arduino controller.
"""

from .serial_interface import ArduinoInterface, SerialMessage, MessageType
from .protocol import ProtocolParser, CommandBuilder

__all__ = [
    'ArduinoInterface',
    'SerialMessage',
    'MessageType',
    'ProtocolParser',
    'CommandBuilder'
]
