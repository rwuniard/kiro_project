"""
Unit tests for ErrorHandler service.

Tests error log file creation, formatting, and error handling scenarios.
"""

import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open

from src.services.error_handler import ErrorHandler


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    @pytest.fixture
    def temp_error_folder(self):
        """Create a temporary directory for error logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def error_handler(self, temp_error_folder):
        """Create ErrorHandler instance with temporary folder."""
        return ErrorHandler(temp_error_folder)
    
    @pytest.fixture
    def sample_file(self, temp_error_folder):
        """Create a sample file for testing."""
        sample_file_path = Path(temp_error_folder) / "sample.txt"
        sample_file_path.write_text("Sample content")
        return str(sample_file_path)
    
    def test_error_handler_initialization(self, temp_error_folder):
        """Test ErrorHandler initialization with error folder."""
        handler = ErrorHandler(temp_error_folder)
        assert handler.error_folder == Path(temp_error_folder)
    
    def test_create_error_log_basic(self, error_handler, sample_file):
        """Test basic error log creation."""
        error_message = "Test error message"
        
        error_handler.create_error_log(sample_file, error_message)
        
        # Check that error log file was created
        expected_log_path = error_handler.error_folder / "sample.log"
        assert expected_log_path.exists()
        
        # Verify log content
        log_content = expected_log_path.read_text()
        assert "FILE PROCESSING ERROR LOG" in log_content
        assert error_message in log_content
        assert sample_file in log_content
        assert "Timestamp:" in log_content
    
    def test_create_error_log_with_exception(self, error_handler, sample_file):
        """Test error log creation with exception details."""
        error_message = "File processing failed"
        test_exception = ValueError("Invalid file format")
        
        error_handler.create_error_log(sample_file, error_message, test_exception)
        
        expected_log_path = error_handler.error_folder / "sample.log"
        log_content = expected_log_path.read_text()
        
        assert error_message in log_content
        assert "ValueError" in log_content
        assert "Stack Trace:" in log_content
        assert "Invalid file format" in log_content
    
    def test_get_error_log_path_simple_file(self, error_handler):
        """Test error log path generation for simple filename."""
        file_path = "/source/document.txt"
        
        log_path = error_handler._get_error_log_path(file_path)
        
        assert log_path.name == "document.log"
        assert log_path.parent == error_handler.error_folder
    
    def test_get_error_log_path_nested_structure(self, error_handler):
        """Test error log path generation for nested files."""
        file_path = "/source/subfolder/nested/file.pdf"
        
        log_path = error_handler._get_error_log_path(file_path)
        
        assert log_path.name == "file.log"
        # Log files are placed directly in error folder
        assert log_path.parent == error_handler.error_folder
    
    def test_get_error_log_path_creates_directory(self, error_handler):
        """Test that error log path creation creates necessary directories."""
        file_path = "/source/newdir/file.txt"
        
        log_path = error_handler._get_error_log_path(file_path)
        
        # Error folder should be created and log placed there
        assert log_path.parent.exists()
        assert log_path.parent == error_handler.error_folder
        assert log_path.name == "file.log"
    
    def test_build_error_info_basic(self, error_handler, sample_file):
        """Test building basic error information."""
        error_message = "Processing failed"
        
        error_info = error_handler._build_error_info(sample_file, error_message)
        
        assert error_info['file_path'] == sample_file
        assert error_info['error_message'] == error_message
        assert 'timestamp' in error_info
        assert 'file_size' in error_info
        assert 'last_modified' in error_info
        
        # Verify timestamp format
        datetime.fromisoformat(error_info['timestamp'])
    
    def test_build_error_info_with_exception(self, error_handler, sample_file):
        """Test building error info with exception details."""
        error_message = "Processing failed"
        test_exception = RuntimeError("Runtime error occurred")
        
        error_info = error_handler._build_error_info(
            sample_file, error_message, test_exception
        )
        
        assert error_info['exception_type'] == 'RuntimeError'
        assert 'stack_trace' in error_info
        assert isinstance(error_info['stack_trace'], list)
    
    def test_build_error_info_nonexistent_file(self, error_handler):
        """Test building error info for non-existent file."""
        nonexistent_file = "/path/to/nonexistent/file.txt"
        error_message = "File not found"
        
        error_info = error_handler._build_error_info(nonexistent_file, error_message)
        
        assert error_info['file_path'] == nonexistent_file
        assert error_info['file_size'] == 'Unknown'
        assert error_info['last_modified'] == 'Unknown'
    
    def test_write_error_log_format(self, error_handler, temp_error_folder):
        """Test error log file format and content structure."""
        log_path = Path(temp_error_folder) / "test.log"
        error_info = {
            'timestamp': '2025-01-23T10:30:45.123456',
            'file_path': '/source/test.txt',
            'error_message': 'Test error',
            'file_size': 1024,
            'last_modified': '2025-01-23T10:29:12.000000',
            'exception_type': 'ValueError',
            'stack_trace': ['Traceback (most recent call last):\n', '  ValueError: Test\n']
        }
        
        error_handler._write_error_log(log_path, error_info)
        
        content = log_path.read_text()
        
        # Check required sections
        assert "FILE PROCESSING ERROR LOG" in content
        assert "Timestamp: 2025-01-23T10:30:45.123456" in content
        assert "File: /source/test.txt" in content
        assert "Error: Test error" in content
        assert "Size: 1024 bytes" in content
        assert "Last Modified: 2025-01-23T10:29:12.000000" in content
        assert "Exception Type: ValueError" in content
        assert "Stack Trace:" in content
        assert "ValueError: Test" in content
    
    def test_write_error_log_minimal_info(self, error_handler, temp_error_folder):
        """Test error log with minimal information (no exception)."""
        log_path = Path(temp_error_folder) / "minimal.log"
        error_info = {
            'timestamp': '2025-01-23T10:30:45.123456',
            'file_path': '/source/minimal.txt',
            'error_message': 'Simple error',
            'file_size': 512,
            'last_modified': '2025-01-23T10:29:12.000000'
        }
        
        error_handler._write_error_log(log_path, error_info)
        
        content = log_path.read_text()
        
        # Should have basic info but no exception details
        assert "Simple error" in content
        assert "Exception Type:" not in content
        assert "Stack Trace:" not in content
    
    def test_create_error_log_handles_write_failure(self, error_handler, sample_file):
        """Test error log creation handles write failures gracefully."""
        # Mock open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('builtins.print') as mock_print:
                error_handler.create_error_log(sample_file, "Test error")
                
                # Should print error message instead of crashing
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                assert "Failed to create error log" in call_args
                assert sample_file in call_args
    
    def test_error_log_file_extension(self, error_handler):
        """Test that error log files always have .log extension."""
        test_cases = [
            "/source/document.txt",
            "/source/image.jpg", 
            "/source/data.csv",
            "/source/file_without_extension"
        ]
        
        for file_path in test_cases:
            log_path = error_handler._get_error_log_path(file_path)
            assert log_path.suffix == ".log"
    
    def test_error_log_timestamp_format(self, error_handler, sample_file):
        """Test that error log timestamps are properly formatted."""
        with patch('src.services.error_handler.datetime') as mock_datetime:
            mock_now = datetime(2025, 1, 23, 10, 30, 45, 123456)
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp.return_value = mock_now
            
            error_info = error_handler._build_error_info(sample_file, "Test error")
            
            assert error_info['timestamp'] == '2025-01-23T10:30:45.123456'
    
    def test_multiple_error_logs_same_directory(self, error_handler, temp_error_folder):
        """Test creating multiple error logs in the same directory."""
        # Create multiple sample files
        file1 = Path(temp_error_folder) / "file1.txt"
        file2 = Path(temp_error_folder) / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Create error logs for both
        error_handler.create_error_log(str(file1), "Error 1")
        error_handler.create_error_log(str(file2), "Error 2")
        
        # Both log files should exist
        log1 = error_handler.error_folder / "file1.log"
        log2 = error_handler.error_folder / "file2.log"
        
        assert log1.exists()
        assert log2.exists()
        
        # Verify content is different
        content1 = log1.read_text()
        content2 = log2.read_text()
        
        assert "Error 1" in content1
        assert "Error 2" in content2
        assert content1 != content2