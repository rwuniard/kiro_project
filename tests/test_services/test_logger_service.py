"""Unit tests for LoggerService class."""

import logging
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.services.logger_service import LoggerService


class TestLoggerService:
    """Test cases for LoggerService class."""
    
    def test_init_console_only(self):
        """Test LoggerService initialization with console logging only."""
        logger_service = LoggerService()
        
        assert logger_service.logger_name == "folder_file_processor"
        assert logger_service.log_file_path is None
        assert logger_service._logger is not None
        assert logger_service._logger.level == logging.INFO
        
        # Should have one handler (console)
        assert len(logger_service._logger.handlers) == 1
        assert isinstance(logger_service._logger.handlers[0], logging.StreamHandler)
    
    def test_init_with_file_logging(self):
        """Test LoggerService initialization with both console and file logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger_service = LoggerService(log_file_path=log_file)
            
            assert logger_service.log_file_path == log_file
            assert logger_service._logger is not None
            
            # Should have two handlers (console and file)
            assert len(logger_service._logger.handlers) == 2
            handler_types = [type(handler) for handler in logger_service._logger.handlers]
            assert logging.StreamHandler in handler_types
            assert logging.FileHandler in handler_types
    
    def test_init_custom_logger_name(self):
        """Test LoggerService initialization with custom logger name."""
        logger_service = LoggerService(logger_name="custom_logger")
        
        assert logger_service.logger_name == "custom_logger"
        assert logger_service._logger.name == "custom_logger"
    
    def test_log_file_directory_creation(self):
        """Test that log file directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "subdir", "nested", "test.log")
            logger_service = LoggerService(log_file_path=log_file)
            
            # Directory should be created
            assert os.path.exists(os.path.dirname(log_file))
            assert logger_service.log_file_path == log_file
    
    def test_log_info(self):
        """Test logging info messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger_service = LoggerService(log_file_path=log_file)
            
            test_message = "This is a test info message"
            logger_service.log_info(test_message)
            
            # Check that message was written to file
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert test_message in log_content
                assert "INFO" in log_content
                assert "folder_file_processor" in log_content
    
    def test_log_error_without_exception(self):
        """Test logging error messages without exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger_service = LoggerService(log_file_path=log_file)
            
            test_message = "This is a test error message"
            logger_service.log_error(test_message)
            
            # Check that message was written to file
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert test_message in log_content
                assert "ERROR" in log_content
                assert "folder_file_processor" in log_content
    
    def test_log_error_with_exception(self):
        """Test logging error messages with exception."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger_service = LoggerService(log_file_path=log_file)
            
            test_message = "This is a test error with exception"
            test_exception = ValueError("Test exception message")
            logger_service.log_error(test_message, test_exception)
            
            # Check that message and exception were written to file
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert test_message in log_content
                assert "Test exception message" in log_content
                assert "ERROR" in log_content
                # Check for exception type and message
                assert "ValueError" in log_content
    
    def test_get_logger(self):
        """Test getting the underlying logger instance."""
        logger_service = LoggerService()
        logger = logger_service.get_logger()
        
        assert isinstance(logger, logging.Logger)
        assert logger is logger_service._logger
        assert logger.name == "folder_file_processor"
    
    def test_setup_logger_class_method(self):
        """Test the setup_logger class method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger_service = LoggerService.setup_logger(
                log_file_path=log_file,
                logger_name="test_logger"
            )
            
            assert isinstance(logger_service, LoggerService)
            assert logger_service.log_file_path == log_file
            assert logger_service.logger_name == "test_logger"
    
    def test_setup_logger_class_method_defaults(self):
        """Test the setup_logger class method with default parameters."""
        logger_service = LoggerService.setup_logger()
        
        assert isinstance(logger_service, LoggerService)
        assert logger_service.log_file_path is None
        assert logger_service.logger_name == "folder_file_processor"
    
    def test_formatter_configuration(self):
        """Test that the log formatter is configured correctly."""
        logger_service = LoggerService()
        
        # Get the console handler
        console_handler = logger_service._logger.handlers[0]
        formatter = console_handler.formatter
        
        # Test the format string
        assert formatter._fmt == '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        assert formatter.datefmt == '%Y-%m-%d %H:%M:%S'
    
    def test_multiple_instances_no_handler_duplication(self):
        """Test that creating multiple instances doesn't duplicate handlers."""
        # Create first instance
        logger_service1 = LoggerService(logger_name="test_logger")
        initial_handler_count = len(logger_service1._logger.handlers)
        
        # Create second instance with same logger name
        logger_service2 = LoggerService(logger_name="test_logger")
        
        # Handler count should be the same (handlers cleared before setup)
        assert len(logger_service2._logger.handlers) == initial_handler_count
    
    @patch('logging.StreamHandler')
    @patch('logging.FileHandler')
    def test_handler_level_configuration(self, mock_file_handler, mock_stream_handler):
        """Test that handlers are configured with correct log levels."""
        mock_stream_instance = MagicMock()
        mock_file_instance = MagicMock()
        mock_stream_handler.return_value = mock_stream_instance
        mock_file_handler.return_value = mock_file_instance
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            LoggerService(log_file_path=log_file)
            
            # Verify that both handlers are set to INFO level
            mock_stream_instance.setLevel.assert_called_with(logging.INFO)
            mock_file_instance.setLevel.assert_called_with(logging.INFO)
    
    def test_log_info_console_only(self):
        """Test info logging with console-only configuration."""
        with patch('logging.StreamHandler') as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.level = logging.INFO  # Set the level attribute properly
            mock_handler_class.return_value = mock_handler
            
            logger_service = LoggerService()
            logger_service.log_info("Test message")
            
            # Verify the logger was called (indirectly through handler setup)
            assert mock_handler_class.called
    
    def test_log_error_console_only(self):
        """Test error logging with console-only configuration."""
        with patch('logging.StreamHandler') as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.level = logging.INFO  # Set the level attribute properly
            mock_handler_class.return_value = mock_handler
            
            logger_service = LoggerService()
            logger_service.log_error("Test error")
            
            # Verify the logger was called (indirectly through handler setup)
            assert mock_handler_class.called
    
    def test_log_with_none_logger(self):
        """Test logging behavior when logger is None (edge case)."""
        logger_service = LoggerService()
        logger_service._logger = None
        
        # Should not raise exceptions
        logger_service.log_info("Test message")
        logger_service.log_error("Test error")
        logger_service.log_error("Test error", Exception("test"))
    
    def test_timestamp_format_in_logs(self):
        """Test that timestamps are formatted correctly in log messages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            logger_service = LoggerService(log_file_path=log_file)
            
            logger_service.log_info("Timestamp test message")
            
            with open(log_file, 'r') as f:
                log_content = f.read()
                
                # Check for timestamp format (YYYY-MM-DD HH:MM:SS)
                import re
                timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
                assert re.search(timestamp_pattern, log_content) is not None