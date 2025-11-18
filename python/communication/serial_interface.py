"""
Serial Interface for Arduino Communication

This module provides a high-level interface for communicating with
the Arduino greenhouse controller over USB serial.

Features:
- Asynchronous message handling
- Automatic reconnection on connection loss
- Message queuing and acknowledgment
- Thread-safe operations
- Timeout handling

Educational Note:
Serial communication requires careful handling of:
- Encoding/decoding (bytes ↔ strings)
- Timeouts (don't block forever)
- Reconnection (USB can disconnect)
- Thread safety (if using multiple threads)
"""

import serial
import serial.tools.list_ports
import threading
import queue
import time
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime


# Configure logging
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in the serial protocol"""
    SENSOR = auto()
    ACTUATOR = auto()
    STATUS = auto()
    CMD = auto()
    ACK = auto()
    ERROR = auto()
    INFO = auto()


@dataclass
class SerialMessage:
    """
    Represents a parsed serial message

    Attributes:
        msg_type: Type of message
        content: Message content (parsed data)
        timestamp: When message was received
        raw: Raw message string
    """
    msg_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime
    raw: str

    def __str__(self) -> str:
        return f"[{self.msg_type.name}] {self.content}"


class ArduinoInterface:
    """
    High-level interface for Arduino serial communication

    Handles connection management, message parsing, and
    asynchronous sending/receiving of messages.

    Example usage:
        arduino = ArduinoInterface(port='/dev/ttyACM0')
        arduino.connect()

        # Set callback for sensor readings
        arduino.on_sensor_reading = lambda msg: print(f"Sensor: {msg}")

        # Send command
        arduino.send_command('SET_MODE', ['1'])

        # Close when done
        arduino.disconnect()
    """

    def __init__(
        self,
        port: str = '/dev/ttyACM0',
        baud_rate: int = 9600,
        timeout: float = 2.0,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0
    ):
        """
        Initialize Arduino interface

        Args:
            port: Serial port path
            baud_rate: Communication speed (must match Arduino)
            timeout: Read timeout in seconds
            reconnect_attempts: Number of reconnection attempts
            reconnect_delay: Delay between reconnection attempts
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay

        # Serial connection
        self.serial: Optional[serial.Serial] = None
        self.connected = False

        # Threading for asynchronous reading
        self.read_thread: Optional[threading.Thread] = None
        self.running = False

        # Message queues
        self.incoming_queue: queue.Queue = queue.Queue()
        self.outgoing_queue: queue.Queue = queue.Queue()

        # Callbacks for different message types
        self.on_sensor_reading: Optional[Callable[[SerialMessage], None]] = None
        self.on_actuator_state: Optional[Callable[[SerialMessage], None]] = None
        self.on_status: Optional[Callable[[SerialMessage], None]] = None
        self.on_acknowledgment: Optional[Callable[[SerialMessage], None]] = None
        self.on_error: Optional[Callable[[SerialMessage], None]] = None
        self.on_info: Optional[Callable[[SerialMessage], None]] = None

        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.errors_count = 0
        self.last_message_time: Optional[datetime] = None

        logger.info(f"ArduinoInterface initialized on {port} @ {baud_rate} baud")

    def connect(self) -> bool:
        """
        Establish serial connection to Arduino

        Returns:
            True if connection successful, False otherwise
        """
        if self.connected:
            logger.warning("Already connected")
            return True

        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )

            # Wait for Arduino to reset (DTR toggles reset on many Arduinos)
            time.sleep(2.0)

            # Flush any startup messages
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            self.connected = True
            logger.info(f"Connected to Arduino on {self.port}")

            # Start read thread
            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()

            return True

        except serial.SerialException as e:
            logger.error(f"Failed to connect: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Close serial connection"""
        if not self.connected:
            return

        logger.info("Disconnecting from Arduino")

        # Stop read thread
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=1.0)

        # Close serial port
        if self.serial:
            self.serial.close()
            self.serial = None

        self.connected = False
        logger.info("Disconnected")

    def _read_loop(self):
        """
        Background thread for reading serial messages

        Educational Note:
        Running serial reading in a separate thread prevents
        blocking the main application while waiting for data.
        """
        logger.info("Read thread started")

        while self.running:
            try:
                if not self.serial or not self.serial.is_open:
                    logger.warning("Serial port not open, attempting reconnect...")
                    if not self._attempt_reconnect():
                        time.sleep(self.reconnect_delay)
                        continue

                # Read line from serial (blocks until \n or timeout)
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()

                if line:
                    self.messages_received += 1
                    self.last_message_time = datetime.now()

                    # Parse and route message
                    message = self._parse_message(line)
                    if message:
                        self._route_message(message)

            except serial.SerialException as e:
                logger.error(f"Serial error: {e}")
                self.connected = False
                time.sleep(self.reconnect_delay)

            except Exception as e:
                logger.error(f"Unexpected error in read loop: {e}")
                time.sleep(0.1)

        logger.info("Read thread stopped")

    def _parse_message(self, line: str) -> Optional[SerialMessage]:
        """
        Parse a raw serial message into structured format

        Message format: PREFIX:data1,data2,data3,...

        Args:
            line: Raw message string

        Returns:
            Parsed SerialMessage or None if parsing failed
        """
        try:
            # Split on first colon to get prefix and content
            parts = line.split(':', 1)
            if len(parts) < 2:
                logger.warning(f"Invalid message format: {line}")
                return None

            prefix, content = parts

            # Determine message type
            msg_type_map = {
                'SENSOR': MessageType.SENSOR,
                'ACTUATOR': MessageType.ACTUATOR,
                'STATUS': MessageType.STATUS,
                'CMD': MessageType.CMD,
                'ACK': MessageType.ACK,
                'ERROR': MessageType.ERROR,
                'INFO': MessageType.INFO
            }

            msg_type = msg_type_map.get(prefix)
            if not msg_type:
                logger.warning(f"Unknown message type: {prefix}")
                return None

            # Parse content based on message type
            parsed_content = self._parse_content(msg_type, content)

            return SerialMessage(
                msg_type=msg_type,
                content=parsed_content,
                timestamp=datetime.now(),
                raw=line
            )

        except Exception as e:
            logger.error(f"Error parsing message '{line}': {e}")
            return None

    def _parse_content(self, msg_type: MessageType, content: str) -> Dict[str, Any]:
        """
        Parse message content based on type

        Returns:
            Dictionary with parsed content
        """
        parts = content.split(',')

        if msg_type == MessageType.SENSOR:
            # Format: SENSOR:type,value,timestamp
            return {
                'sensor_type': parts[0] if len(parts) > 0 else None,
                'value': float(parts[1]) if len(parts) > 1 else 0.0,
                'timestamp': int(parts[2]) if len(parts) > 2 else 0
            }

        elif msg_type == MessageType.ACTUATOR:
            # Format: ACTUATOR:type,state,value,timestamp
            return {
                'actuator_type': parts[0] if len(parts) > 0 else None,
                'enabled': parts[1] == '1' if len(parts) > 1 else False,
                'value': float(parts[2]) if len(parts) > 2 else 0.0,
                'timestamp': int(parts[3]) if len(parts) > 3 else 0
            }

        elif msg_type == MessageType.STATUS:
            # Format: STATUS:enabled,mode,error,timestamp
            return {
                'enabled': parts[0] == '1' if len(parts) > 0 else False,
                'mode': int(parts[1]) if len(parts) > 1 else 0,
                'error': parts[2] == '1' if len(parts) > 2 else False,
                'timestamp': int(parts[3]) if len(parts) > 3 else 0
            }

        elif msg_type == MessageType.ERROR:
            # Format: ERROR:code,description
            return {
                'error_code': int(parts[0]) if len(parts) > 0 else 0,
                'description': parts[1] if len(parts) > 1 else ''
            }

        elif msg_type == MessageType.ACK:
            # Format: ACK:message
            return {
                'message': content
            }

        elif msg_type == MessageType.INFO:
            # Format: INFO:message
            return {
                'message': content
            }

        else:
            # Generic parsing for unknown types
            return {'raw': content}

    def _route_message(self, message: SerialMessage):
        """
        Route message to appropriate callback

        Args:
            message: Parsed SerialMessage
        """
        # Call appropriate callback if registered
        if message.msg_type == MessageType.SENSOR and self.on_sensor_reading:
            self.on_sensor_reading(message)

        elif message.msg_type == MessageType.ACTUATOR and self.on_actuator_state:
            self.on_actuator_state(message)

        elif message.msg_type == MessageType.STATUS and self.on_status:
            self.on_status(message)

        elif message.msg_type == MessageType.ACK and self.on_acknowledgment:
            self.on_acknowledgment(message)

        elif message.msg_type == MessageType.ERROR:
            self.errors_count += 1
            if self.on_error:
                self.on_error(message)
            logger.warning(f"Arduino error: {message.content}")

        elif message.msg_type == MessageType.INFO and self.on_info:
            self.on_info(message)

        # Also add to incoming queue for polling
        self.incoming_queue.put(message)

    def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to Arduino

        Returns:
            True if reconnection successful
        """
        for attempt in range(self.reconnect_attempts):
            logger.info(f"Reconnection attempt {attempt + 1}/{self.reconnect_attempts}")

            try:
                if self.serial:
                    try:
                        self.serial.close()
                    except:
                        pass

                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baud_rate,
                    timeout=self.timeout
                )

                time.sleep(2.0)  # Wait for Arduino reset
                self.connected = True
                logger.info("Reconnection successful")
                return True

            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                time.sleep(self.reconnect_delay)

        logger.error("All reconnection attempts failed")
        self.connected = False
        return False

    def send_command(self, command: str, params: List[str] = None):
        """
        Send a command to Arduino

        Format: CMD:<command>,<param1>,<param2>,...

        Args:
            command: Command name (e.g., 'SET_MODE')
            params: List of parameter strings

        Example:
            arduino.send_command('SET_SETPOINT', ['TEMP', '25.0'])
        """
        if not self.connected or not self.serial:
            logger.error("Cannot send command: not connected")
            return

        # Build command message
        message = f"CMD:{command}"
        if params:
            message += ',' + ','.join(str(p) for p in params)
        message += '\n'

        try:
            self.serial.write(message.encode('utf-8'))
            self.messages_sent += 1
            logger.debug(f"Sent: {message.strip()}")

        except serial.SerialException as e:
            logger.error(f"Error sending command: {e}")
            self.connected = False

    def send_raw(self, message: str):
        """
        Send raw message to Arduino

        Args:
            message: Raw message string (will add newline if missing)
        """
        if not self.connected or not self.serial:
            logger.error("Cannot send message: not connected")
            return

        if not message.endswith('\n'):
            message += '\n'

        try:
            self.serial.write(message.encode('utf-8'))
            self.messages_sent += 1
            logger.debug(f"Sent raw: {message.strip()}")

        except serial.SerialException as e:
            logger.error(f"Error sending message: {e}")
            self.connected = False

    def get_message(self, timeout: float = 0.1) -> Optional[SerialMessage]:
        """
        Get next message from incoming queue (polling interface)

        Args:
            timeout: How long to wait for message

        Returns:
            SerialMessage or None if no message available
        """
        try:
            return self.incoming_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get communication statistics

        Returns:
            Dictionary with statistics
        """
        return {
            'connected': self.connected,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'errors_count': self.errors_count,
            'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
            'queue_size': self.incoming_queue.qsize()
        }

    @staticmethod
    def list_available_ports() -> List[str]:
        """
        List all available serial ports

        Returns:
            List of port names

        Educational Note:
        Use this to find the Arduino port if unsure.
        Arduino typically shows as /dev/ttyACM0 on Linux,
        COM3/COM4 on Windows, /dev/cu.usbmodem* on macOS.
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup"""
        self.disconnect()


if __name__ == "__main__":
    # Example usage and testing
    print("=== Arduino Serial Interface Demo ===\n")

    # List available ports
    print("Available serial ports:")
    for port in ArduinoInterface.list_available_ports():
        print(f"  - {port}")
    print()

    # Create interface (modify port as needed)
    arduino = ArduinoInterface(port='/dev/ttyACM0')

    # Set up callbacks
    def on_sensor(msg: SerialMessage):
        print(f"Sensor: {msg.content['sensor_type']} = {msg.content['value']}")

    def on_error(msg: SerialMessage):
        print(f"ERROR {msg.content['error_code']}: {msg.content['description']}")

    def on_info(msg: SerialMessage):
        print(f"Info: {msg.content['message']}")

    arduino.on_sensor_reading = on_sensor
    arduino.on_error = on_error
    arduino.on_info = on_info

    # Connect
    if arduino.connect():
        print("Connected! Listening for messages...")
        print("(Press Ctrl+C to exit)\n")

        try:
            # Send some test commands
            time.sleep(1)
            arduino.send_command('STATUS')

            time.sleep(2)
            arduino.send_command('SET_MODE', ['2'])

            # Run for a while
            time.sleep(10)

        except KeyboardInterrupt:
            print("\nInterrupted by user")

        finally:
            # Print statistics
            stats = arduino.get_statistics()
            print(f"\nStatistics:")
            print(f"  Sent: {stats['messages_sent']}")
            print(f"  Received: {stats['messages_received']}")
            print(f"  Errors: {stats['errors_count']}")

            arduino.disconnect()

    else:
        print("Failed to connect!")

    print("\nDemo complete!")
