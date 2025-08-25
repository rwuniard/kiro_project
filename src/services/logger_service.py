"""
Logger Service for the Folder File Processor application.

This module provides centralized logging functionality with both console and file output,
proper formatting with timestamps, and support for INFO and ERROR level logging.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class LoggerService:
    """
    Centralized logging service that provides INFO and ERROR level logging
    with proper formatting, timestamps, and both console and file outputs.
    """
    
    def __init__(self, log_file_path: Optional[str] = None, logger_name: str = "folder_file_processor"):
        """
        Initialize the LoggerService with console and optional file logging.
        
        Args:
            log_file_path: Optional path to log file. If None, only console logging is used.
            logger_name: Name for the logger instance.
        """
        self.logger_name = logger_name
        self.log_file_path = log_file_path
        self._logger = None
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Set up the logger with proper formatting and handlers."""
        # Create logger
        self._logger = logging.getLogger(self.logger_name)
        self._logger.setLevel(logging.INFO)
        
        # Clear any existing handlers to avoid duplicates
        self._logger.handlers.clear()
        
        # Create formatter with timestamp
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        # File handler (if log file path is provided)
        if self.log_file_path:
            # Ensure log directory exists
            log_dir = Path(self.log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.log_file_path)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
    
    def log_info(self, message: str) -> None:
        """
        Log an informational message.
        
        Args:
            message: The message to log at INFO level.
        """
        if self._logger:
            self._logger.info(message)
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Log an error message with optional exception details.
        
        Args:
            message: The error message to log.
            exception: Optional exception to include in the log.
        """
        if self._logger:
            if exception:
                # Create a more detailed error message with exception info
                error_msg = f"{message}: {type(exception).__name__}: {str(exception)}"
                self._logger.error(error_msg)
            else:
                self._logger.error(message)
    
    def get_logger(self) -> logging.Logger:
        """
        Get the underlying logger instance for advanced usage.
        
        Returns:
            The configured logger instance.
        """
        return self._logger
    
    @classmethod
    def setup_logger(cls, log_file_path: Optional[str] = None, logger_name: str = "folder_file_processor") -> 'LoggerService':
        """
        Class method to create and configure a LoggerService instance.
        
        Args:
            log_file_path: Optional path to log file.
            logger_name: Name for the logger instance.
            
        Returns:
            Configured LoggerService instance.
        """
        return cls(log_file_path=log_file_path, logger_name=logger_name)