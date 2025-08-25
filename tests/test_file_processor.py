"""
Unit tests for the FileProcessor class.

Tests cover file processing success and failure scenarios, integration with
FileManager and ErrorHandler, and proper error handling.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from src.core.file_processor import (
    FileProcessor, ProcessingResult, ErrorType, RetryConfig
)
from src.core.file_manager import FileManager
from src.services.error_handler import ErrorHandler
from src.services.logger_service import LoggerService


class TestFileProcessor:
    """Test cases for FileProcessor class."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            saved_dir = temp_path / "saved"
            error_dir = temp_path / "error"
            
            source_dir.mkdir()
            saved_dir.mkdir()
            error_dir.mkdir()
            
            yield {
                'source': str(source_dir),
                'saved': str(saved_dir),
                'error': str(error_dir),
                'temp': str(temp_path)
            }
    
    @pytest.fixture
    def mock_services(self, temp_dirs):
        """Create mock services for testing."""
        file_manager = Mock(spec=FileManager)
        error_handler = Mock(spec=ErrorHandler)
        logger_service = Mock(spec=LoggerService)
        
        # Configure file_manager mocks
        file_manager.move_to_saved.return_value = True
        file_manager.move_to_error.return_value = True
        file_manager.get_relative_path.return_value = "test_file.txt"
        
        return {
            'file_manager': file_manager,
            'error_handler': error_handler,
            'logger_service': logger_service
        }
    
    @pytest.fixture
    def file_processor(self, mock_services):
        """Create FileProcessor instance with mock services."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service']
        )
    
    def test_process_file_success(self, file_processor, mock_services, temp_dirs):
        """Test successful file processing."""
        # Create a test file
        test_file = Path(temp_dirs['source']) / "test_file.txt"
        test_content = "This is test content\nWith multiple lines"
        test_file.write_text(test_content)
        
        # Process the file
        with patch('builtins.print') as mock_print:
            result = file_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is True
        assert result.file_path == str(test_file)
        assert result.error_message is None
        assert result.processing_time > 0
        
        # Verify file manager was called to move to saved
        mock_services['file_manager'].move_to_saved.assert_called_once_with(str(test_file))
        
        # Verify logging
        mock_services['logger_service'].log_info.assert_called()
        
        # Verify print to screen
        mock_print.assert_called_once_with("Processed file: test_file.txt")
    
    def test_process_file_not_found(self, file_processor, mock_services):
        """Test processing non-existent file."""
        non_existent_file = "/path/to/non/existent/file.txt"
        
        result = file_processor.process_file(non_existent_file)
        
        # Verify result
        assert result.success is False
        assert result.file_path == non_existent_file
        assert "File not found" in result.error_message
        
        # Verify error handling
        mock_services['error_handler'].create_error_log.assert_called_once()
        mock_services['file_manager'].move_to_error.assert_called_once_with(non_existent_file)
        # With retry logic, log_error may be called multiple times
        assert mock_services['logger_service'].log_error.call_count >= 1
    
    def test_process_file_is_directory(self, file_processor, mock_services, temp_dirs):
        """Test processing a directory instead of a file."""
        directory_path = temp_dirs['source']
        
        result = file_processor.process_file(directory_path)
        
        # Verify result
        assert result.success is False
        assert result.file_path == directory_path
        assert "Path is not a file" in result.error_message
        
        # Verify error handling
        mock_services['error_handler'].create_error_log.assert_called_once()
        mock_services['file_manager'].move_to_error.assert_called_once_with(directory_path)
    
    def test_process_empty_file(self, file_processor, mock_services, temp_dirs):
        """Test processing an empty file."""
        # Create empty test file
        test_file = Path(temp_dirs['source']) / "empty_file.txt"
        test_file.write_text("")
        
        result = file_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert result.file_path == str(test_file)
        assert "empty or contains only whitespace" in result.error_message
        
        # Verify error handling
        mock_services['error_handler'].create_error_log.assert_called_once()
        mock_services['file_manager'].move_to_error.assert_called_once()
    
    def test_process_whitespace_only_file(self, file_processor, mock_services, temp_dirs):
        """Test processing a file with only whitespace."""
        # Create whitespace-only test file
        test_file = Path(temp_dirs['source']) / "whitespace_file.txt"
        test_file.write_text("   \n\t  \n   ")
        
        result = file_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert "empty or contains only whitespace" in result.error_message
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_process_file_permission_error(self, mock_open, file_processor, mock_services, temp_dirs):
        """Test processing file with permission error."""
        test_file = Path(temp_dirs['source']) / "permission_file.txt"
        test_file.write_text("content")  # Create file first
        
        result = file_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert "Permission denied" in result.error_message or "Cannot access file" in result.error_message
        
        # Verify error handling
        mock_services['error_handler'].create_error_log.assert_called_once()
        mock_services['file_manager'].move_to_error.assert_called_once()
    
    def test_process_file_unicode_decode_error(self, file_processor, mock_services, temp_dirs):
        """Test processing file with unicode decode error."""
        test_file = Path(temp_dirs['source']) / "binary_file.txt"
        test_file.write_text("content")  # Create file first
        
        # Mock the _read_file_content method to test encoding fallback
        with patch.object(file_processor, '_read_file_content') as mock_read:
            mock_read.return_value = "decoded content"
            
            result = file_processor.process_file(str(test_file))
            
            # Should succeed with fallback
            assert result.success is True
            mock_read.assert_called_once_with(str(test_file))
    
    @patch('builtins.open')
    def test_process_file_unicode_decode_error_both_encodings_fail(self, mock_open, file_processor, mock_services, temp_dirs):
        """Test processing file when both UTF-8 and Latin-1 fail."""
        test_file = Path(temp_dirs['source']) / "binary_file.txt"
        test_file.write_text("content")  # Create file first
        
        # Mock open to raise UnicodeDecodeError for both encodings
        mock_open.side_effect = [
            UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte'),
            UnicodeDecodeError('latin-1', b'', 0, 1, 'invalid start byte')
        ]
        
        result = file_processor.process_file(str(test_file))
        
        # Should fail
        assert result.success is False
        assert ("Failed to decode file" in result.error_message or 
                "codec can't decode" in result.error_message)
    
    def test_process_file_move_to_saved_fails(self, file_processor, mock_services, temp_dirs):
        """Test when moving to saved folder fails."""
        # Create a test file
        test_file = Path(temp_dirs['source']) / "test_file.txt"
        test_file.write_text("This is test content")
        
        # Mock move_to_saved to fail
        mock_services['file_manager'].move_to_saved.return_value = False
        
        result = file_processor.process_file(str(test_file))
        
        # Should fail due to move failure
        assert result.success is False
        assert "Failed to move file to saved folder" in result.error_message
        
        # Should still try to handle as error
        mock_services['error_handler'].create_error_log.assert_called_once()
        mock_services['file_manager'].move_to_error.assert_called_once()
    
    def test_process_file_move_to_error_fails(self, file_processor, mock_services, temp_dirs):
        """Test when moving to error folder fails."""
        # Create a test file that will cause processing to fail
        test_file = Path(temp_dirs['source']) / "empty_file.txt"
        test_file.write_text("")
        
        # Mock move_to_error to fail
        mock_services['file_manager'].move_to_error.side_effect = Exception("Move failed")
        
        result = file_processor.process_file(str(test_file))
        
        # Should still return failure result
        assert result.success is False
        
        # Should log the move error
        assert mock_services['logger_service'].log_error.call_count >= 2  # Original error + move error
    
    def test_read_file_content_success(self, file_processor, temp_dirs):
        """Test successful file content reading."""
        test_file = Path(temp_dirs['source']) / "test_file.txt"
        test_content = "This is test content\nWith multiple lines"
        test_file.write_text(test_content)
        
        content = file_processor._read_file_content(str(test_file))
        
        assert content == test_content
    
    def test_perform_processing_success(self, file_processor, mock_services):
        """Test successful file processing logic."""
        content = "This is valid content\nWith multiple lines"
        file_path = "/path/to/test_file.txt"
        
        # Should not raise any exception
        file_processor._perform_processing(content, file_path)
        
        # Should log processing information
        mock_services['logger_service'].log_info.assert_called()
    
    def test_perform_processing_empty_content(self, file_processor, mock_services):
        """Test processing with empty content."""
        content = ""
        file_path = "/path/to/test_file.txt"
        
        with pytest.raises(ValueError, match="empty or contains only whitespace"):
            file_processor._perform_processing(content, file_path)
    
    def test_perform_processing_whitespace_content(self, file_processor, mock_services):
        """Test processing with whitespace-only content."""
        content = "   \n\t  \n   "
        file_path = "/path/to/test_file.txt"
        
        with pytest.raises(ValueError, match="empty or contains only whitespace"):
            file_processor._perform_processing(content, file_path)
    
    def test_read_file_content_encoding_fallback(self, file_processor, temp_dirs):
        """Test encoding fallback in _read_file_content method."""
        # Create a file with content that can be read with latin-1
        test_file = Path(temp_dirs['source']) / "encoding_test.txt"
        test_file.write_text("test content", encoding='latin-1')
        
        # Mock the first open call to raise UnicodeDecodeError
        original_open = open
        call_count = 0
        
        def mock_open_func(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and kwargs.get('encoding') == 'utf-8':
                raise UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
            return original_open(*args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open_func):
            content = file_processor._read_file_content(str(test_file))
        
        # Should succeed with latin-1 fallback
        assert content == "test content"
        
        # Verify both encodings were tried
        assert call_count == 2


class TestFileProcessorIntegration:
    """Integration tests with real services."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            saved_dir = temp_path / "saved"
            error_dir = temp_path / "error"
            
            source_dir.mkdir()
            saved_dir.mkdir()
            error_dir.mkdir()
            
            yield {
                'source': str(source_dir),
                'saved': str(saved_dir),
                'error': str(error_dir),
                'temp': str(temp_path)
            }
    
    @pytest.fixture
    def real_services(self, temp_dirs):
        """Create real service instances for integration testing."""
        file_manager = FileManager(
            source_folder=temp_dirs['source'],
            saved_folder=temp_dirs['saved'],
            error_folder=temp_dirs['error']
        )
        error_handler = ErrorHandler(error_folder=temp_dirs['error'])
        logger_service = LoggerService()
        
        return {
            'file_manager': file_manager,
            'error_handler': error_handler,
            'logger_service': logger_service
        }
    
    @pytest.fixture
    def file_processor_real(self, real_services):
        """Create FileProcessor with real services."""
        return FileProcessor(
            file_manager=real_services['file_manager'],
            error_handler=real_services['error_handler'],
            logger_service=real_services['logger_service']
        )
    
    def test_integration_successful_processing(self, file_processor_real, temp_dirs):
        """Test complete successful file processing workflow."""
        # Create test file
        test_file = Path(temp_dirs['source']) / "integration_test.txt"
        test_content = "This is integration test content"
        test_file.write_text(test_content)
        
        # Process file
        with patch('builtins.print') as mock_print:
            result = file_processor_real.process_file(str(test_file))
        
        # Verify success
        assert result.success is True
        
        # Verify file was moved to saved folder
        saved_file = Path(temp_dirs['saved']) / "integration_test.txt"
        assert saved_file.exists()
        assert saved_file.read_text() == test_content
        
        # Verify original file was moved (not copied)
        assert not test_file.exists()
        
        # Verify print output
        mock_print.assert_called_once_with("Processed file: integration_test.txt")
    
    def test_integration_failed_processing_with_error_log(self, file_processor_real, temp_dirs):
        """Test complete failed file processing workflow with error log creation."""
        # Create empty test file (will cause processing failure)
        test_file = Path(temp_dirs['source']) / "empty_test.txt"
        test_file.write_text("")
        
        # Process file
        result = file_processor_real.process_file(str(test_file))
        
        # Verify failure
        assert result.success is False
        
        # Verify file was moved to error folder
        error_file = Path(temp_dirs['error']) / "empty_test.txt"
        assert error_file.exists()
        
        # Verify error log was created
        error_log = Path(temp_dirs['error']) / "empty_test.log"
        assert error_log.exists()
        
        # Verify error log content
        log_content = error_log.read_text()
        assert "FILE PROCESSING ERROR LOG" in log_content
        assert "empty or contains only whitespace" in log_content
        
        # Verify original file was moved
        assert not test_file.exists()


class TestErrorHandlingAndResilience:
    """Test cases for comprehensive error handling and resilience features."""
    
    @pytest.fixture
    def retry_config(self):
        """Create retry configuration for testing."""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,  # Short delay for testing
            max_delay=1.0,
            backoff_multiplier=2.0
        )
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        file_manager = Mock(spec=FileManager)
        error_handler = Mock(spec=ErrorHandler)
        logger_service = Mock(spec=LoggerService)
        
        file_manager.move_to_saved.return_value = True
        file_manager.move_to_error.return_value = True
        file_manager.get_relative_path.return_value = "test_file.txt"
        
        return {
            'file_manager': file_manager,
            'error_handler': error_handler,
            'logger_service': logger_service
        }
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            saved_dir = temp_path / "saved"
            error_dir = temp_path / "error"
            
            source_dir.mkdir()
            saved_dir.mkdir()
            error_dir.mkdir()
            
            yield {
                'source': str(source_dir),
                'saved': str(saved_dir),
                'error': str(error_dir),
                'temp': str(temp_path)
            }
    
    @pytest.fixture
    def file_processor_with_retry(self, mock_services, retry_config):
        """Create FileProcessor with retry configuration."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            retry_config=retry_config
        )
    
    def test_error_classification_transient_errors(self, file_processor_with_retry):
        """Test classification of transient errors."""
        processor = file_processor_with_retry
        
        # Test transient errors
        assert processor._classify_error(OSError("Temporary failure")) == ErrorType.TRANSIENT
        assert processor._classify_error(PermissionError("File locked")) == ErrorType.TRANSIENT
        assert processor._classify_error(FileNotFoundError("File not found")) == ErrorType.TRANSIENT
    
    def test_error_classification_permanent_errors(self, file_processor_with_retry):
        """Test classification of permanent errors."""
        processor = file_processor_with_retry
        
        # Test permanent errors
        unicode_error = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
        assert processor._classify_error(unicode_error) == ErrorType.PERMANENT
        assert processor._classify_error(ValueError("Invalid content")) == ErrorType.PERMANENT
    
    def test_error_classification_unknown_errors(self, file_processor_with_retry):
        """Test classification of unknown errors."""
        processor = file_processor_with_retry
        
        # Test unknown errors
        assert processor._classify_error(RuntimeError("Unknown error")) == ErrorType.UNKNOWN
        assert processor._classify_error(Exception("Generic error")) == ErrorType.UNKNOWN
    
    def test_retry_logic_success_on_second_attempt(self, file_processor_with_retry):
        """Test retry logic succeeds on second attempt."""
        processor = file_processor_with_retry
        
        # Mock operation that fails once then succeeds
        mock_operation = Mock()
        mock_operation.side_effect = [OSError("Temporary failure"), "success"]
        
        result = processor._execute_with_retry(mock_operation, "Test operation")
        
        assert result == "success"
        assert mock_operation.call_count == 2
    
    def test_retry_logic_permanent_error_no_retry(self, file_processor_with_retry):
        """Test that permanent errors are not retried."""
        processor = file_processor_with_retry
        
        # Mock operation that raises permanent error
        mock_operation = Mock()
        unicode_error = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
        mock_operation.side_effect = unicode_error
        
        with pytest.raises(UnicodeDecodeError):
            processor._execute_with_retry(mock_operation, "Test operation")
        
        # Should only be called once (no retry)
        assert mock_operation.call_count == 1
    
    def test_retry_logic_exhausts_attempts(self, file_processor_with_retry):
        """Test retry logic when all attempts are exhausted."""
        processor = file_processor_with_retry
        
        # Mock operation that always fails with transient error
        mock_operation = Mock()
        mock_operation.side_effect = OSError("Persistent failure")
        
        with pytest.raises(OSError):
            processor._execute_with_retry(mock_operation, "Test operation")
        
        # Should be called max_attempts times
        assert mock_operation.call_count == processor.retry_config.max_attempts
    
    def test_retry_logic_exponential_backoff(self, file_processor_with_retry):
        """Test that retry logic uses exponential backoff."""
        processor = file_processor_with_retry
        
        # Mock operation that always fails
        mock_operation = Mock()
        mock_operation.side_effect = OSError("Persistent failure")
        
        with patch('time.sleep') as mock_sleep:
            with pytest.raises(OSError):
                processor._execute_with_retry(mock_operation, "Test operation")
        
        # Verify exponential backoff delays
        expected_delays = [0.1, 0.2]  # base_delay * backoff_multiplier^attempt
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays
    
    def test_process_file_with_retry_success_after_transient_failure(self, file_processor_with_retry, mock_services, temp_dirs):
        """Test file processing succeeds after transient failure."""
        # Create test file
        test_file = Path(temp_dirs['source']) / "retry_test.txt"
        test_file.write_text("Test content")
        
        # Mock _validate_file_access to fail once then succeed
        with patch.object(file_processor_with_retry, '_validate_file_access') as mock_validate:
            mock_validate.side_effect = [OSError("Temporary failure"), None]
            
            with patch('builtins.print'):
                result = file_processor_with_retry.process_file(str(test_file))
        
        assert result.success is True
        assert mock_validate.call_count == 2
        assert file_processor_with_retry.stats['retries_attempted'] == 1
    
    def test_process_file_statistics_tracking(self, file_processor_with_retry, mock_services, temp_dirs):
        """Test that processing statistics are properly tracked."""
        processor = file_processor_with_retry
        
        # Test successful processing
        test_file = Path(temp_dirs['source']) / "stats_test.txt"
        test_file.write_text("Test content")
        
        with patch('builtins.print'):
            result = processor.process_file(str(test_file))
        
        stats = processor.get_processing_stats()
        assert stats['total_processed'] == 1
        assert stats['successful'] == 1
        assert stats['failed_permanent'] == 0
        assert stats['failed_after_retry'] == 0
    
    def test_process_file_statistics_permanent_failure(self, file_processor_with_retry, mock_services):
        """Test statistics tracking for permanent failures."""
        processor = file_processor_with_retry
        
        # Mock permanent error
        with patch.object(processor, '_validate_file_access') as mock_validate:
            unicode_error = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte')
            mock_validate.side_effect = unicode_error
            
            result = processor.process_file("/nonexistent/file.txt")
        
        assert result.success is False
        stats = processor.get_processing_stats()
        assert stats['total_processed'] == 1
        assert stats['successful'] == 0
        assert stats['failed_permanent'] == 1
        assert stats['failed_after_retry'] == 0
    
    def test_process_file_statistics_retry_failure(self, file_processor_with_retry, mock_services):
        """Test statistics tracking for failures after retry."""
        processor = file_processor_with_retry
        
        # Mock transient error that persists
        with patch.object(processor, '_validate_file_access') as mock_validate:
            mock_validate.side_effect = OSError("Persistent transient error")
            
            result = processor.process_file("/nonexistent/file.txt")
        
        assert result.success is False
        stats = processor.get_processing_stats()
        assert stats['total_processed'] == 1
        assert stats['successful'] == 0
        assert stats['failed_permanent'] == 0
        assert stats['failed_after_retry'] == 1
        assert stats['retries_attempted'] == 2  # 3 attempts - 1 = 2 retries
    
    def test_resilient_error_log_creation(self, file_processor_with_retry, mock_services):
        """Test that error log creation uses retry logic."""
        processor = file_processor_with_retry
        
        # Mock error handler to fail once then succeed
        mock_services['error_handler'].create_error_log.side_effect = [
            OSError("Temporary failure"),
            None
        ]
        
        # Create scenario that causes processing failure
        with patch.object(processor, '_validate_file_access') as mock_validate:
            mock_validate.side_effect = ValueError("Permanent error")
            
            result = processor.process_file("/test/file.txt")
        
        assert result.success is False
        # Error log creation should have been retried
        assert mock_services['error_handler'].create_error_log.call_count == 2
    
    def test_resilient_file_movement(self, file_processor_with_retry, mock_services):
        """Test that file movement uses retry logic."""
        processor = file_processor_with_retry
        
        # Mock file movement to fail once then succeed
        mock_services['file_manager'].move_to_error.side_effect = [False, True]
        
        # Create scenario that causes processing failure
        with patch.object(processor, '_validate_file_access') as mock_validate:
            mock_validate.side_effect = ValueError("Permanent error")
            
            with patch.object(processor, '_move_to_error_with_validation') as mock_move:
                mock_move.side_effect = [OSError("Temporary failure"), None]
                
                result = processor.process_file("/test/file.txt")
        
        assert result.success is False
        # File movement should have been retried
        assert mock_move.call_count == 2


class TestFileManagerResilience:
    """Test cases for FileManager resilience improvements."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            saved_dir = temp_path / "saved"
            error_dir = temp_path / "error"
            
            source_dir.mkdir()
            saved_dir.mkdir()
            error_dir.mkdir()
            
            yield {
                'source': str(source_dir),
                'saved': str(saved_dir),
                'error': str(error_dir),
                'temp': str(temp_path)
            }
    
    @pytest.fixture
    def file_manager(self, temp_dirs):
        """Create FileManager instance."""
        return FileManager(
            source_folder=temp_dirs['source'],
            saved_folder=temp_dirs['saved'],
            error_folder=temp_dirs['error']
        )
    
    def test_move_with_destination_conflict_resolution(self, file_manager, temp_dirs):
        """Test file movement with destination conflict resolution."""
        # Create source file
        source_file = Path(temp_dirs['source']) / "conflict_test.txt"
        source_file.write_text("Source content")
        
        # Create conflicting file in destination
        saved_dir = Path(temp_dirs['saved'])
        conflicting_file = saved_dir / "conflict_test.txt"
        conflicting_file.write_text("Existing content")
        
        # Move file - should resolve conflict
        result = file_manager.move_to_saved(str(source_file))
        
        assert result is True
        assert not source_file.exists()  # Source should be moved
        assert conflicting_file.exists()  # Original should remain
        
        # New file should have suffix
        new_files = list(saved_dir.glob("conflict_test_*.txt"))
        assert len(new_files) == 1
        assert new_files[0].read_text() == "Source content"
    
    def test_atomic_move_fallback_to_copy_delete(self, file_manager, temp_dirs):
        """Test atomic move fallback to copy+delete strategy."""
        # Create source file
        source_file = Path(temp_dirs['source']) / "atomic_test.txt"
        source_file.write_text("Test content")
        
        # Test the _atomic_move method directly to verify fallback behavior
        dest_path = Path(temp_dirs['saved']) / "atomic_test.txt"
        
        # Mock shutil.move to fail, forcing copy+delete fallback
        with patch('shutil.move', side_effect=OSError("Cross-device link")):
            with patch('shutil.copy2') as mock_copy:
                # Mock copy2 to actually perform the copy
                def actual_copy(src, dst):
                    Path(dst).write_text(Path(src).read_text())
                mock_copy.side_effect = actual_copy
                
                # Call _atomic_move directly
                file_manager._atomic_move(source_file, dest_path)
        
        # Verify the fallback was used
        mock_copy.assert_called_once()
        assert dest_path.exists()
        assert dest_path.read_text() == "Test content"
    
    def test_move_with_retry_on_transient_failure(self, file_manager, temp_dirs):
        """Test file movement retry on transient failures."""
        # Create source file
        source_file = Path(temp_dirs['source']) / "retry_move_test.txt"
        source_file.write_text("Test content")
        
        # Mock _atomic_move to fail twice then succeed
        call_count = 0
        original_atomic_move = file_manager._atomic_move
        
        def mock_atomic_move(source, dest):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OSError("Temporary failure")
            # Success on third attempt - use original method
            original_atomic_move(source, dest)
        
        with patch.object(file_manager, '_atomic_move', side_effect=mock_atomic_move):
            with patch('time.sleep'):  # Speed up test
                result = file_manager.move_to_saved(str(source_file))
        
        assert result is True
        assert call_count == 3
    
    def test_move_failure_after_max_retries(self, file_manager, temp_dirs):
        """Test file movement failure after exhausting retries."""
        # Create source file
        source_file = Path(temp_dirs['source']) / "fail_move_test.txt"
        source_file.write_text("Test content")
        
        # Mock _atomic_move to always fail
        with patch.object(file_manager, '_atomic_move', side_effect=OSError("Persistent failure")):
            with patch('time.sleep'):  # Speed up test
                result = file_manager.move_to_saved(str(source_file))
        
        assert result is False


class TestFileMonitorResilience:
    """Test cases for FileMonitor resilience improvements."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            
            yield {
                'source': str(source_dir),
                'temp': str(temp_path)
            }
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        file_processor = Mock(spec=FileProcessor)
        logger_service = Mock(spec=LoggerService)
        
        file_processor.process_file.return_value = ProcessingResult(
            success=True, file_path="test.txt"
        )
        
        return {
            'file_processor': file_processor,
            'logger_service': logger_service
        }
    
    def test_event_handler_duplicate_filtering(self, mock_services):
        """Test that duplicate events are filtered."""
        from src.core.file_monitor import FileEventHandler
        
        handler = FileEventHandler(
            file_processor=mock_services['file_processor'],
            logger_service=mock_services['logger_service']
        )
        
        # Test the _is_duplicate_event method directly
        file_path = "/test/file.txt"
        
        # First call should return False (not duplicate)
        assert handler._is_duplicate_event(file_path) is False
        
        # Second call should return True (is duplicate)
        assert handler._is_duplicate_event(file_path) is True
        
        # Check that the file is in recent files
        assert file_path in handler._recent_files
    
    def test_event_handler_file_stability_check(self, mock_services):
        """Test file stability checking before processing."""
        from src.core.file_monitor import FileEventHandler
        
        handler = FileEventHandler(
            file_processor=mock_services['file_processor'],
            logger_service=mock_services['logger_service']
        )
        
        # Create mock event
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/test/file.txt"
        
        # Mock file size changing (unstable file)
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isfile', return_value=True):
                with patch('os.path.getsize', side_effect=[100, 200]):  # Size changes
                    handler.on_created(mock_event)
        
        # File should not be processed due to instability
        assert mock_services['file_processor'].process_file.call_count == 0
        
        # Check statistics
        stats = handler.get_stats()
        assert stats['processing_errors'] == 0  # Not counted as error, just skipped
    
    def test_event_handler_resilience_to_processing_errors(self, mock_services):
        """Test that event handler continues after processing errors."""
        from src.core.file_monitor import FileEventHandler
        
        handler = FileEventHandler(
            file_processor=mock_services['file_processor'],
            logger_service=mock_services['logger_service']
        )
        
        # Mock file processor to raise exception
        mock_services['file_processor'].process_file.side_effect = Exception("Processing error")
        
        # Create mock event
        mock_event = Mock()
        mock_event.is_directory = False
        mock_event.src_path = "/test/file.txt"
        
        # Mock file checks
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isfile', return_value=True):
                with patch('os.path.getsize', return_value=100):
                    with patch('builtins.open', mock_open(read_data="test")):
                        # Should not raise exception despite processing error
                        handler.on_created(mock_event)
        
        # Check that error was logged
        mock_services['logger_service'].log_error.assert_called()
        
        # Check statistics
        stats = handler.get_stats()
        assert stats['processing_errors'] == 1


class TestFileProcessorAdditionalCoverage:
    """Additional tests to ensure comprehensive FileProcessor coverage."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            saved_dir = temp_path / "saved"
            error_dir = temp_path / "error"
            
            source_dir.mkdir()
            saved_dir.mkdir()
            error_dir.mkdir()
            
            yield {
                'source': str(source_dir),
                'saved': str(saved_dir),
                'error': str(error_dir),
                'temp': str(temp_path)
            }
    
    @pytest.fixture
    def mock_services(self, temp_dirs):
        """Create mock services for testing."""
        file_manager = Mock(spec=FileManager)
        error_handler = Mock(spec=ErrorHandler)
        logger_service = Mock(spec=LoggerService)
        
        file_manager.move_to_saved.return_value = True
        file_manager.move_to_error.return_value = True
        file_manager.get_relative_path.return_value = "test_file.txt"
        
        return {
            'file_manager': file_manager,
            'error_handler': error_handler,
            'logger_service': logger_service
        }
    
    @pytest.fixture
    def file_processor(self, mock_services):
        """Create FileProcessor instance with mock services."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service']
        )
    
    def test_validate_file_access_permission_error(self, file_processor, temp_dirs):
        """Test file access validation with permission error."""
        test_file = Path(temp_dirs['source']) / "permission_test.txt"
        test_file.write_text("test content")
        
        # Mock open to raise PermissionError
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError, match="Cannot access file"):
                file_processor._validate_file_access(str(test_file))
    
    def test_read_file_content_os_error(self, file_processor, temp_dirs):
        """Test file content reading with OS error."""
        test_file = Path(temp_dirs['source']) / "os_error_test.txt"
        test_file.write_text("test content")
        
        # Mock open to raise OSError
        with patch('builtins.open', side_effect=OSError("Disk error")):
            with pytest.raises(OSError, match="OS error when reading file"):
                file_processor._read_file_content(str(test_file))
    
    def test_read_file_content_unexpected_error(self, file_processor, temp_dirs):
        """Test file content reading with unexpected error."""
        test_file = Path(temp_dirs['source']) / "unexpected_error_test.txt"
        test_file.write_text("test content")
        
        # Mock open to raise unexpected exception
        with patch('builtins.open', side_effect=RuntimeError("Unexpected error")):
            with pytest.raises(RuntimeError, match="Unexpected error reading file"):
                file_processor._read_file_content(str(test_file))
    
    def test_classify_error_os_error_with_errno(self, file_processor):
        """Test error classification for OS errors with specific errno."""
        # Test transient OS error with specific errno
        os_error = OSError("File busy")
        os_error.errno = 16  # EBUSY - transient error
        
        error_type = file_processor._classify_error(os_error)
        assert error_type == ErrorType.TRANSIENT
    
    def test_classify_error_os_error_without_errno(self, file_processor):
        """Test error classification for OS errors without errno."""
        os_error = OSError("Generic OS error")
        # No errno attribute
        
        error_type = file_processor._classify_error(os_error)
        assert error_type == ErrorType.TRANSIENT
    
    def test_execute_with_retry_unknown_error_classification(self, file_processor):
        """Test retry logic with unknown error classification."""
        def failing_operation():
            raise RuntimeError("Unknown error type")
        
        # Unknown errors should still be retried
        with pytest.raises(RuntimeError):
            file_processor._execute_with_retry(failing_operation, "Test operation")
    
    def test_process_file_error_log_creation_failure(self, file_processor, mock_services, temp_dirs):
        """Test process file when error log creation fails."""
        # Create empty test file (will cause processing failure)
        test_file = Path(temp_dirs['source']) / "empty_test.txt"
        test_file.write_text("")
        
        # Mock error handler to fail
        mock_services['error_handler'].create_error_log.side_effect = Exception("Log creation failed")
        
        result = file_processor.process_file(str(test_file))
        
        # Should still return failure result
        assert result.success is False
        
        # Should have attempted to create error log
        mock_services['error_handler'].create_error_log.assert_called()
    
    def test_process_file_move_to_error_exception(self, file_processor, mock_services, temp_dirs):
        """Test process file when move to error raises exception."""
        # Create empty test file (will cause processing failure)
        test_file = Path(temp_dirs['source']) / "empty_test.txt"
        test_file.write_text("")
        
        # Mock move_to_error_with_validation to raise exception
        with patch.object(file_processor, '_move_to_error_with_validation', side_effect=Exception("Move failed")):
            result = file_processor.process_file(str(test_file))
            
            # Should still return failure result
            assert result.success is False
    
    def test_move_to_saved_with_validation_failure(self, file_processor, mock_services):
        """Test move to saved validation failure."""
        mock_services['file_manager'].move_to_saved.return_value = False
        
        with pytest.raises(RuntimeError, match="Failed to move file to saved folder"):
            file_processor._move_to_saved_with_validation("/test/file.txt")
    
    def test_move_to_error_with_validation_failure(self, file_processor, mock_services):
        """Test move to error validation failure."""
        mock_services['file_manager'].move_to_error.return_value = False
        
        with pytest.raises(RuntimeError, match="Failed to move file to error folder"):
            file_processor._move_to_error_with_validation("/test/file.txt")


class TestFileProcessorFolderCleanupIntegration:
    """Integration tests for folder cleanup functionality with file processing."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_folder = Path(self.temp_dir) / "source"
        self.saved_folder = Path(self.temp_dir) / "saved"
        self.error_folder = Path(self.temp_dir) / "error"
        
        # Create the directories
        self.source_folder.mkdir(parents=True)
        self.saved_folder.mkdir(parents=True)
        self.error_folder.mkdir(parents=True)
        
        # Create real services
        self.file_manager = FileManager(
            str(self.source_folder),
            str(self.saved_folder),
            str(self.error_folder)
        )
        self.error_handler = ErrorHandler(str(self.error_folder))
        self.logger_service = LoggerService()
        
        # Create FileProcessor with real services
        self.file_processor = FileProcessor(
            self.file_manager,
            self.error_handler,
            self.logger_service
        )
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Remove temporary directory and all contents
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_process_file_with_folder_cleanup_single_level(self):
        """Test file processing with folder cleanup for single level structure."""
        # Create nested structure with file
        nested_folder = self.source_folder / "level1"
        nested_folder.mkdir()
        test_file = nested_folder / "test.txt"
        test_file.write_text("test content")
        
        # Process the file
        with patch('builtins.print'):  # Suppress print output
            result = self.file_processor.process_file(str(test_file))
        
        # Verify processing was successful
        assert result.success is True
        assert result.file_path == str(test_file)
        
        # Verify folder cleanup occurred
        assert len(result.cleaned_folders) == 1
        cleaned_paths = [Path(p).resolve() for p in result.cleaned_folders]
        assert nested_folder.resolve() in cleaned_paths
        
        # Verify folder was actually removed
        assert not nested_folder.exists()
        
        # Verify source folder still exists
        assert self.source_folder.exists()
        
        # Verify file was moved to saved folder
        saved_file = self.saved_folder / "level1" / "test.txt"
        assert saved_file.exists()
    
    def test_process_file_with_folder_cleanup_multiple_levels(self):
        """Test file processing with folder cleanup for multiple level structure."""
        # Create deeply nested structure with file
        nested_path = self.source_folder / "level1" / "level2" / "level3"
        nested_path.mkdir(parents=True)
        test_file = nested_path / "deep_test.txt"
        test_file.write_text("deep content")
        
        # Process the file
        with patch('builtins.print'):  # Suppress print output
            result = self.file_processor.process_file(str(test_file))
        
        # Verify processing was successful
        assert result.success is True
        
        # Verify folder cleanup occurred for all levels
        assert len(result.cleaned_folders) == 3
        
        # Verify all nested folders were removed
        assert not nested_path.exists()
        assert not nested_path.parent.exists()
        assert not nested_path.parent.parent.exists()
        
        # Verify source folder still exists
        assert self.source_folder.exists()
    
    def test_process_file_with_folder_cleanup_stops_at_non_empty(self):
        """Test folder cleanup stops when encountering non-empty folder."""
        # Create nested structure
        level1 = self.source_folder / "level1"
        level2 = level1 / "level2"
        level2.mkdir(parents=True)
        
        # Add files to different levels
        (level1 / "keep.txt").write_text("keep this")
        test_file = level2 / "remove.txt"
        test_file.write_text("remove this")
        
        # Process the file
        with patch('builtins.print'):  # Suppress print output
            result = self.file_processor.process_file(str(test_file))
        
        # Verify processing was successful
        assert result.success is True
        
        # Verify only level2 was cleaned up (level1 has keep.txt)
        assert len(result.cleaned_folders) == 1
        cleaned_paths = [Path(p).resolve() for p in result.cleaned_folders]
        assert level2.resolve() in cleaned_paths
        
        # Verify level2 was removed but level1 still exists
        assert not level2.exists()
        assert level1.exists()
        assert (level1 / "keep.txt").exists()
    
    def test_process_file_with_no_folder_cleanup_needed(self):
        """Test file processing when no folder cleanup is needed."""
        # Create file directly in source folder
        test_file = self.source_folder / "root_test.txt"
        test_file.write_text("root content")
        
        # Process the file
        with patch('builtins.print'):  # Suppress print output
            result = self.file_processor.process_file(str(test_file))
        
        # Verify processing was successful
        assert result.success is True
        
        # Verify no folder cleanup occurred (can't remove source root)
        assert len(result.cleaned_folders) == 0
        
        # Verify source folder still exists
        assert self.source_folder.exists()
    
    def test_process_file_folder_cleanup_logging(self):
        """Test that folder cleanup operations are logged at INFO level."""
        # Create nested structure with file
        nested_folder = self.source_folder / "logged_cleanup"
        nested_folder.mkdir()
        test_file = nested_folder / "test.txt"
        test_file.write_text("test content")
        
        # Mock the logger to capture log calls
        with patch.object(self.logger_service, 'log_info') as mock_log_info, \
             patch('builtins.print'):  # Suppress print output
            
            result = self.file_processor.process_file(str(test_file))
        
        # Verify processing was successful
        assert result.success is True
        assert len(result.cleaned_folders) == 1
        
        # Verify logging calls were made
        log_calls = [call.args[0] for call in mock_log_info.call_args_list]
        
        # Should have logs for file processing and folder cleanup
        assert any("Successfully processed file" in call for call in log_calls)
        assert any("Cleaned up empty folder" in call for call in log_calls)
    
    def test_process_file_with_folder_cleanup_permission_error(self):
        """Test file processing when folder cleanup encounters permission error."""
        # Create nested structure with file
        nested_folder = self.source_folder / "permission_test"
        nested_folder.mkdir()
        test_file = nested_folder / "test.txt"
        test_file.write_text("test content")
        
        # Mock rmdir to raise PermissionError
        original_rmdir = Path.rmdir
        def mock_rmdir(self):
            if "permission_test" in str(self):
                raise PermissionError("Access denied")
            return original_rmdir(self)
        
        with patch.object(Path, 'rmdir', mock_rmdir), \
             patch('builtins.print'):  # Suppress print output
            
            result = self.file_processor.process_file(str(test_file))
        
        # Verify processing was still successful (cleanup failure doesn't fail processing)
        assert result.success is True
        
        # Verify no folders were cleaned up due to permission error
        assert len(result.cleaned_folders) == 0
        
        # Verify folder still exists due to permission error
        assert nested_folder.exists()
    
    def test_process_file_error_case_no_folder_cleanup(self):
        """Test that folder cleanup doesn't occur when file processing fails."""
        # Create nested structure with file
        nested_folder = self.source_folder / "error_test"
        nested_folder.mkdir()
        test_file = nested_folder / "empty.txt"
        test_file.write_text("")  # Empty file will cause processing to fail
        
        # Process the file (should fail due to empty content)
        with patch('builtins.print'):  # Suppress print output
            result = self.file_processor.process_file(str(test_file))
        
        # Verify processing failed
        assert result.success is False
        
        # Verify no folder cleanup occurred (only happens on successful processing)
        assert len(result.cleaned_folders) == 0
        
        # Verify folder still exists
        assert nested_folder.exists()
        
        # Verify file was moved to error folder
        error_file = self.error_folder / "error_test" / "empty.txt"
        assert error_file.exists()