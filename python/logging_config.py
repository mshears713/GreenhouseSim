"""
Logging Configuration for Greenhouse System

This module provides comprehensive logging setup for:
- Console output (INFO level)
- File output (DEBUG level)
- Communication events (dedicated log file)
- Error tracking (dedicated log file)
- Rotating log files to prevent disk space issues

Educational Note:
Python's logging module provides a flexible framework for capturing
diagnostic information. Using different handlers allows routing different
severity levels to different destinations (console, files, network, etc.).
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class LoggingConfig:
    """
    Centralized logging configuration for the greenhouse system

    Features:
    - Multiple log files for different purposes
    - Automatic log rotation
    - Colored console output (if colorlog available)
    - Structured logging with context
    """

    def __init__(
        self,
        log_dir: str = "./data/logs",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5
    ):
        """
        Initialize logging configuration

        Args:
            log_dir: Directory for log files
            console_level: Logging level for console output
            file_level: Logging level for file output
            max_bytes: Maximum size of each log file before rotation
            backup_count: Number of backup log files to keep
        """
        self.log_dir = Path(log_dir)
        self.console_level = console_level
        self.file_level = file_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count

        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging
        self._setup_logging()

    def _setup_logging(self):
        """Configure all logging handlers and formatters"""

        # Define log format
        detailed_format = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        simple_format = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter

        # Remove any existing handlers
        root_logger.handlers.clear()

        # 1. Console Handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.console_level)
        console_handler.setFormatter(simple_format)
        root_logger.addHandler(console_handler)

        # 2. Main Application Log (DEBUG and above) - Rotating
        main_log_file = self.log_dir / "greenhouse_main.log"
        main_file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        main_file_handler.setLevel(self.file_level)
        main_file_handler.setFormatter(detailed_format)
        root_logger.addHandler(main_file_handler)

        # 3. Communication Log (dedicated for serial communication) - Rotating
        comm_log_file = self.log_dir / "communication.log"
        comm_file_handler = logging.handlers.RotatingFileHandler(
            comm_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        comm_file_handler.setLevel(logging.DEBUG)
        comm_file_handler.setFormatter(detailed_format)

        # Only add communication logs to this handler
        comm_logger = logging.getLogger('communication')
        comm_logger.addHandler(comm_file_handler)
        comm_logger.setLevel(logging.DEBUG)

        # 4. Error Log (WARNING and above only) - Rotating
        error_log_file = self.log_dir / "errors.log"
        error_file_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.WARNING)
        error_file_handler.setFormatter(detailed_format)
        root_logger.addHandler(error_file_handler)

        # Log startup message
        root_logger.info("="*80)
        root_logger.info(f"Logging system initialized - {datetime.now().isoformat()}")
        root_logger.info(f"Log directory: {self.log_dir.absolute()}")
        root_logger.info(f"Console level: {logging.getLevelName(self.console_level)}")
        root_logger.info(f"File level: {logging.getLevelName(self.file_level)}")
        root_logger.info("="*80)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name

        Args:
            name: Logger name (usually __name__ of the calling module)

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)

    @staticmethod
    def log_statistics(logger: logging.Logger, stats_dict: dict, prefix: str = "Statistics"):
        """
        Log a dictionary of statistics in a formatted way

        Args:
            logger: Logger instance to use
            stats_dict: Dictionary of statistics to log
            prefix: Prefix for log messages
        """
        logger.info(f"{prefix}:")
        for key, value in stats_dict.items():
            logger.info(f"  {key}: {value}")

    @staticmethod
    def log_communication_event(
        event_type: str,
        direction: str,
        message: str,
        success: bool = True,
        error_msg: Optional[str] = None
    ):
        """
        Log a communication event to the dedicated communication logger

        Args:
            event_type: Type of event (SEND, RECEIVE, CONNECT, DISCONNECT, etc.)
            direction: Direction (TX, RX, N/A)
            message: Message content
            success: Whether operation succeeded
            error_msg: Error message if not successful

        Example:
            log_communication_event('SEND', 'TX', 'CMD:SET_MODE,2', success=True)
        """
        comm_logger = logging.getLogger('communication')

        status = "OK" if success else "FAIL"
        log_message = f"[{event_type:10s}] [{direction:2s}] [{status:4s}] {message}"

        if success:
            comm_logger.info(log_message)
        else:
            log_message += f" | Error: {error_msg}" if error_msg else ""
            comm_logger.error(log_message)


def setup_greenhouse_logging(
    log_dir: str = "./data/logs",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> LoggingConfig:
    """
    Convenience function to set up greenhouse logging

    Args:
        log_dir: Directory for log files
        console_level: Logging level for console
        file_level: Logging level for files

    Returns:
        LoggingConfig instance

    Example:
        # At the start of main application
        setup_greenhouse_logging()
    """
    return LoggingConfig(
        log_dir=log_dir,
        console_level=console_level,
        file_level=file_level
    )


if __name__ == "__main__":
    # Demo logging setup
    print("Setting up logging demo...")

    config = setup_greenhouse_logging()
    logger = config.get_logger(__name__)

    # Test different log levels
    logger.debug("This is a DEBUG message (file only)")
    logger.info("This is an INFO message (console and file)")
    logger.warning("This is a WARNING message (console, file, and errors.log)")
    logger.error("This is an ERROR message (console, file, and errors.log)")

    # Test statistics logging
    test_stats = {
        'messages_sent': 42,
        'messages_received': 38,
        'errors': 2,
        'uptime_seconds': 3600
    }
    config.log_statistics(logger, test_stats, "Test Statistics")

    # Test communication event logging
    LoggingConfig.log_communication_event('SEND', 'TX', 'CMD:SET_MODE,2', success=True)
    LoggingConfig.log_communication_event('RECEIVE', 'RX', 'ACK:Mode changed', success=True)
    LoggingConfig.log_communication_event('SEND', 'TX', 'CMD:INVALID', success=False, error_msg='Timeout')

    print("\nDemo complete! Check the logs directory for output files.")
    print(f"Logs are in: {config.log_dir.absolute()}")
