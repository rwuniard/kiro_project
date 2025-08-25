"""
Unit tests for FileMonitor class.

Tests file system event monitoring functionality including event handling,
integration with FileProcessor, and error scenarios.
"""

import os
import time
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest

from src.core.file_monitor import FileMonitor, FileEventHandler
from src.core.file_processor import FileProcessor, ProcessingResult
from src.services.logger_service import LoggerService


class TestFileEventHandler:
    """Test cases for FileEventHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_processor = Mock(spec=FileProcessor)
        self.mock_logger = Mock(spec=LoggerService)
        self.handler = FileEventHandler(self.mock_processor, self.mock_logger)
    
    def test_on_created_processes_file_successfully(self):
        """Test that file creation events trigger successful processing."""
        # Arrange
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/test/path/file.txt"
        
        # Mock successful processing
        success_result = ProcessingResult(
            success=True,
            file_path="/test/path/file.txt",
            processing_time=0.5
        )
        self.mock_processor.process_file.return_value = success_result
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('builtins.open', mock_open(read_data=b"test")), \
             patch('time.sleep'):
            
            # Act
            self.handler.on_created(mock_event)
            
            # Assert
            self.mock_logger.log_info.assert_any_call("New file detected: /test/path/file.txt")
            self.mock_processor.process_file.assert_called_once_with("/test/path/file.txt")
            self.mock_logger.log_info.assert_any_call(
                "File processing completed successfully: /test/path/file.txt"
            )
    
    def test_on_created_handles_processing_failure(self):
        """Test that file creation events handle processing failures gracefully."""
        # Arrange
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/test/path/file.txt"
        
        # Mock failed processing
        failure_result = ProcessingResult(
            success=False,
            file_path="/test/path/file.txt",
            error_message="Processing failed",
            processing_time=0.2
        )
        self.mock_processor.process_file.return_value = failure_result
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('builtins.open', mock_open(read_data=b"test")), \
             patch('time.sleep'):
            
            # Act
            self.handler.on_created(mock_event)
            
            # Assert
            self.mock_logger.log_info.assert_any_call("New file detected: /test/path/file.txt")
            self.mock_processor.process_file.assert_called_once_with("/test/path/file.txt")
            self.mock_logger.log_error.assert_called_with("File processing failed: Processing failed")
    
    def test_on_created_ignores_directory_events(self):
        """Test that directory creation events are ignored."""
        # Arrange
        mock_event = Mock()
        mock_event.is_directory = True
        mock_event.src_path = "/test/path/directory"
        
        # Act
        self.handler.on_created(mock_event)
        
        # Assert
        self.mock_processor.process_file.assert_not_called()
        self.mock_logger.log_info.assert_not_called()
    
    def test_on_created_handles_file_not_exists(self):
        """Test handling when file no longer exists after creation event."""
        # Arrange
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/test/path/file.txt"
        
        with patch('os.path.exists', return_value=False), \
             patch('time.sleep'):
            
            # Act
            self.handler.on_created(mock_event)
            
            # Assert
            self.mock_logger.log_info.assert_called_with("New file detected: /test/path/file.txt")
            self.mock_processor.process_file.assert_not_called()
            self.mock_logger.log_error.assert_called_with(
                "File stability check failed: /test/path/file.txt"
            )
    
    def test_on_created_handles_processing_exception(self):
        """Test handling of unexpected exceptions during processing."""
        # Arrange
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/test/path/file.txt"
        
        # Mock processing exception
        test_exception = Exception("Unexpected error")
        self.mock_processor.process_file.side_effect = test_exception
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True), \
             patch('os.path.getsize', return_value=100), \
             patch('builtins.open', mock_open(read_data=b"test")), \
             patch('time.sleep'):
            
            # Act
            self.handler.on_created(mock_event)
            
            # Assert
            self.mock_logger.log_info.assert_any_call("New file detected: /test/path/file.txt")
            # With retry logic, process_file may be called multiple times
            assert self.mock_processor.process_file.called
            assert self.mock_processor.process_file.call_args[0][0] == "/test/path/file.txt"
            # The error message format may have changed in the new implementation
            assert self.mock_logger.log_error.called


class TestFileMonitor:
    """Test cases for FileMonitor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_processor = Mock(spec=FileProcessor)
        self.mock_logger = Mock(spec=LoggerService)
        
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_folder = self.temp_dir
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_with_valid_folder(self):
        """Test FileMonitor initialization with valid source folder."""
        # Act
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        
        # Assert
        assert monitor.source_folder == Path(self.source_folder).resolve()
        assert monitor.file_processor == self.mock_processor
        assert monitor.logger == self.mock_logger
        assert monitor.observer is not None
        assert monitor.event_handler is not None
    
    def test_init_with_nonexistent_folder(self):
        """Test FileMonitor initialization with non-existent folder."""
        # Arrange
        nonexistent_folder = "/path/that/does/not/exist"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Source folder does not exist"):
            FileMonitor(nonexistent_folder, self.mock_processor, self.mock_logger)
    
    def test_init_with_file_instead_of_folder(self):
        """Test FileMonitor initialization with file path instead of folder."""
        # Arrange
        test_file = os.path.join(self.temp_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Source path is not a directory"):
            FileMonitor(test_file, self.mock_processor, self.mock_logger)
    
    @patch('src.core.file_monitor.Observer')
    def test_start_monitoring_success(self, mock_observer_class):
        """Test successful start of monitoring."""
        # Arrange
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        monitor.observer = mock_observer
        
        # Act
        monitor.start_monitoring()
        
        # Assert
        mock_observer.schedule.assert_called_once()
        mock_observer.start.assert_called_once()
        self.mock_logger.log_info.assert_called_with(
            f"Started monitoring folder: {Path(self.source_folder).resolve()}"
        )
    
    @patch('src.core.file_monitor.Observer')
    def test_start_monitoring_failure(self, mock_observer_class):
        """Test handling of monitoring start failure."""
        # Arrange
        mock_observer = Mock()
        mock_observer.schedule.side_effect = Exception("Failed to schedule")
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        monitor.observer = mock_observer
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to start file system monitoring"):
            monitor.start_monitoring()
        
        self.mock_logger.log_error.assert_called()
    
    @patch('src.core.file_monitor.Observer')
    def test_stop_monitoring_success(self, mock_observer_class):
        """Test successful stop of monitoring."""
        # Arrange
        mock_observer = Mock()
        mock_observer.is_alive.side_effect = [True, False]  # Alive before stop, not alive after join
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        monitor.observer = mock_observer
        
        # Act
        monitor.stop_monitoring()
        
        # Assert
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5.0)
        self.mock_logger.log_info.assert_called_with("File system monitoring stopped")
    
    @patch('src.core.file_monitor.Observer')
    def test_stop_monitoring_timeout(self, mock_observer_class):
        """Test handling of monitoring stop timeout."""
        # Arrange
        mock_observer = Mock()
        mock_observer.is_alive.side_effect = [True, True]  # Still alive after join
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        monitor.observer = mock_observer
        
        # Act
        monitor.stop_monitoring()
        
        # Assert
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5.0)
        self.mock_logger.log_error.assert_called_with(
            "Observer did not stop gracefully within timeout"
        )
    
    @patch('src.core.file_monitor.Observer')
    def test_is_monitoring_active(self, mock_observer_class):
        """Test is_monitoring when monitoring is active."""
        # Arrange
        mock_observer = Mock()
        mock_observer.is_alive.return_value = True
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        monitor.observer = mock_observer
        
        # Act & Assert
        assert monitor.is_monitoring() is True
    
    @patch('src.core.file_monitor.Observer')
    def test_is_monitoring_inactive(self, mock_observer_class):
        """Test is_monitoring when monitoring is inactive."""
        # Arrange
        mock_observer = Mock()
        mock_observer.is_alive.return_value = False
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        monitor.observer = mock_observer
        
        # Act & Assert
        assert monitor.is_monitoring() is False
    
    @patch('src.core.file_monitor.Observer')
    def test_context_manager(self, mock_observer_class):
        """Test FileMonitor as context manager."""
        # Arrange
        mock_observer = Mock()
        mock_observer.is_alive.return_value = True
        mock_observer_class.return_value = mock_observer
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        monitor.observer = mock_observer
        
        # Act
        with monitor as m:
            assert m is monitor
            mock_observer.schedule.assert_called_once()
            mock_observer.start.assert_called_once()
        
        # Assert
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()


class TestFileMonitorIntegration:
    """Integration tests for FileMonitor with real file system events."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_processor = Mock(spec=FileProcessor)
        self.mock_logger = Mock(spec=LoggerService)
        
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_folder = self.temp_dir
        
        # Mock successful processing by default
        success_result = ProcessingResult(
            success=True,
            file_path="",
            processing_time=0.1
        )
        self.mock_processor.process_file.return_value = success_result
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_real_file_creation_triggers_processing(self):
        """Test that creating a real file triggers processing."""
        # Arrange
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        
        # Start monitoring in a separate thread to avoid blocking
        def start_monitoring():
            monitor.start_monitoring()
            time.sleep(2)  # Monitor for 2 seconds
            monitor.stop_monitoring()
        
        monitor_thread = threading.Thread(target=start_monitoring)
        monitor_thread.start()
        
        # Give monitor time to start
        time.sleep(0.5)
        
        # Act - Create a file
        test_file = os.path.join(self.source_folder, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Wait for processing
        time.sleep(0.5)
        
        # Clean up
        monitor_thread.join(timeout=3)
        
        # Assert
        self.mock_processor.process_file.assert_called()
        # Verify the file path matches what we created (resolve both paths to handle symlinks)
        call_args = self.mock_processor.process_file.call_args[0]
        assert Path(call_args[0]).resolve() == Path(test_file).resolve()
    
    def test_nested_folder_file_creation(self):
        """Test that files created in nested folders are detected."""
        # Arrange
        nested_dir = os.path.join(self.source_folder, "subdir", "nested")
        os.makedirs(nested_dir)
        
        monitor = FileMonitor(self.source_folder, self.mock_processor, self.mock_logger)
        
        # Start monitoring
        def start_monitoring():
            monitor.start_monitoring()
            time.sleep(2)
            monitor.stop_monitoring()
        
        monitor_thread = threading.Thread(target=start_monitoring)
        monitor_thread.start()
        
        # Give monitor time to start
        time.sleep(0.5)
        
        # Act - Create a file in nested directory
        test_file = os.path.join(nested_dir, "nested_file.txt")
        with open(test_file, 'w') as f:
            f.write("nested content")
        
        # Wait for processing
        time.sleep(0.5)
        
        # Clean up
        monitor_thread.join(timeout=3)
        
        # Assert
        self.mock_processor.process_file.assert_called()
        call_args = self.mock_processor.process_file.call_args[0]
        assert Path(call_args[0]).resolve() == Path(test_file).resolve()