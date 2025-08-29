"""
Unit tests for the FileProcessor class.

Tests cover file processing success and failure scenarios, integration with
FileManager and ErrorHandler, and proper error handling.
"""

import os
import tempfile
import shutil
import time
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
        file_manager.cleanup_empty_folders.return_value = []
        
        return {
            'file_manager': file_manager,
            'error_handler': error_handler,
            'logger_service': logger_service
        }
    
    @pytest.fixture
    def mock_document_processor(self):
        """Create mock document processor for existing tests."""
        from src.core.document_processing import DocumentProcessingInterface, ProcessingResult
        
        mock_processor = Mock(spec=DocumentProcessingInterface)
        mock_processor.get_processor_name.return_value = "MockProcessor"
        mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx'}
        mock_processor.initialize.return_value = True
        mock_processor.is_supported_file.return_value = True
        mock_processor.cleanup.return_value = None
        
        # Default successful processing result
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            file_path="/test/file.txt",
            processor_used="MockProcessor",
            chunks_created=5,
            processing_time=1.5,
            metadata={
                'document_processor': 'TextProcessor',
                'file_size': 1024,
                'model_vendor': 'google',
                'file_extension': '.txt'
            }
        )
        
        return mock_processor

    @pytest.fixture
    def file_processor(self, mock_services, mock_document_processor):
        """Create FileProcessor instance with mock services."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_document_processor
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
    
    def test_process_empty_file(self, file_processor, mock_services, mock_document_processor, temp_dirs):
        """Test processing an empty file."""
        from src.core.document_processing import ProcessingResult
        
        # Create empty test file
        test_file = Path(temp_dirs['source']) / "empty_file.txt"
        test_file.write_text("")
        
        # Configure mock document processor to return empty document error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 0}
        )
        
        result = file_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert result.file_path == str(test_file)
        assert "Empty document" in result.error_message
        
        # Verify error handling
        mock_services['error_handler'].create_error_log.assert_called_once()
        mock_services['file_manager'].move_to_error.assert_called_once()
    
    def test_process_whitespace_only_file(self, file_processor, mock_services, mock_document_processor, temp_dirs):
        """Test processing a file with only whitespace."""
        from src.core.document_processing import ProcessingResult
        
        # Create whitespace-only test file
        test_file = Path(temp_dirs['source']) / "whitespace_file.txt"
        test_file.write_text("   \n\t  \n   ")
        
        # Configure mock document processor to return empty document error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 10}
        )
        
        result = file_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert "Empty document" in result.error_message
    
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
    
    def test_process_file_unicode_decode_error(self, file_processor, mock_services, mock_document_processor, temp_dirs):
        """Test processing file with unicode decode error handled by document processor."""
        test_file = Path(temp_dirs['source']) / "binary_file.txt"
        test_file.write_text("content")  # Create file first
        
        # Document processor should handle encoding issues internally
        # and return success if it can process the file
        result = file_processor.process_file(str(test_file))
        
        # Should succeed as document processor handles encoding
        assert result.success is True
        mock_document_processor.process_document.assert_called_once()
    
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
    
    def test_process_file_move_to_error_fails(self, file_processor, mock_services, mock_document_processor, temp_dirs):
        """Test when moving to error folder fails."""
        from src.core.document_processing import ProcessingResult
        
        # Create a test file that will cause processing to fail
        test_file = Path(temp_dirs['source']) / "empty_file.txt"
        test_file.write_text("")
        
        # Configure mock document processor to return failure
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 0}
        )
        
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
    
    def test_perform_processing_success(self, file_processor, mock_services, mock_document_processor, temp_dirs):
        """Test successful document processing logic."""
        # Create test file
        test_file = Path(temp_dirs['source']) / "test_file.txt"
        test_file.write_text("This is valid content\nWith multiple lines")
        
        # Should not raise any exception
        file_processor._perform_processing(str(test_file))
        
        # Should log processing information
        mock_services['logger_service'].log_info.assert_called()
        
        # Should call document processor
        mock_document_processor.process_document.assert_called_once()
    
    def test_perform_processing_empty_content(self, file_processor, mock_services, mock_document_processor, temp_dirs):
        """Test processing with empty content."""
        from src.core.document_processing import ProcessingResult
        
        # Create empty test file
        test_file = Path(temp_dirs['source']) / "empty_file.txt"
        test_file.write_text("")
        
        # Configure mock document processor to return empty document error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 0}
        )
        
        with pytest.raises(ValueError, match="Empty document"):
            file_processor._perform_processing(str(test_file))
    
    def test_perform_processing_whitespace_content(self, file_processor, mock_services, mock_document_processor, temp_dirs):
        """Test processing with whitespace-only content."""
        from src.core.document_processing import ProcessingResult
        
        # Create whitespace-only test file
        test_file = Path(temp_dirs['source']) / "whitespace_file.txt"
        test_file.write_text("   \n\t  \n   ")
        
        # Configure mock document processor to return empty document error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 10}
        )
        
        with pytest.raises(ValueError, match="Empty document"):
            file_processor._perform_processing(str(test_file))
    
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
    def mock_document_processor(self):
        """Create mock document processor for integration tests."""
        from src.core.document_processing import DocumentProcessingInterface, ProcessingResult
        
        mock_processor = Mock(spec=DocumentProcessingInterface)
        mock_processor.get_processor_name.return_value = "MockProcessor"
        mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx'}
        mock_processor.initialize.return_value = True
        mock_processor.is_supported_file.return_value = True
        mock_processor.cleanup.return_value = None
        
        # Default successful processing result
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            file_path="/test/file.txt",
            processor_used="MockProcessor",
            chunks_created=5,
            processing_time=1.5,
            metadata={
                'document_processor': 'TextProcessor',
                'file_size': 1024,
                'model_vendor': 'google',
                'file_extension': '.txt'
            }
        )
        
        return mock_processor

    @pytest.fixture
    def file_processor_real(self, real_services, mock_document_processor):
        """Create FileProcessor with real services."""
        return FileProcessor(
            file_manager=real_services['file_manager'],
            error_handler=real_services['error_handler'],
            logger_service=real_services['logger_service'],
            document_processor=mock_document_processor
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
    
    def test_integration_failed_processing_with_error_log(self, file_processor_real, temp_dirs, mock_document_processor):
        """Test complete failed file processing workflow with error log creation."""
        from src.core.document_processing import ProcessingResult
        
        # Create empty test file (will cause processing failure)
        test_file = Path(temp_dirs['source']) / "empty_test.txt"
        test_file.write_text("")
        
        # Configure mock document processor to return failure for empty file
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 0}
        )
        
        # Process file
        result = file_processor_real.process_file(str(test_file))
        
        # Verify failure
        assert result.success is False
        
        # Verify file was moved to error folder
        error_file = Path(temp_dirs['error']) / "empty_test.txt"
        assert error_file.exists()
        
        # Verify error log was created (new format: filename.extension.log)
        error_log = Path(temp_dirs['error']) / "empty_test.txt.log"
        assert error_log.exists()
        
        # Verify error log content
        log_content = error_log.read_text()
        assert "FILE PROCESSING ERROR LOG" in log_content
        assert "Empty document: No content extracted from document" in log_content
        
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
        file_manager.cleanup_empty_folders.return_value = []  # Return empty list for cleaned folders
        
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
    def mock_document_processor(self):
        """Create mock document processor for resilience tests."""
        from src.core.document_processing import DocumentProcessingInterface, ProcessingResult
        
        mock_processor = Mock(spec=DocumentProcessingInterface)
        mock_processor.get_processor_name.return_value = "MockProcessor"
        mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx'}
        mock_processor.initialize.return_value = True
        mock_processor.is_supported_file.return_value = True
        mock_processor.cleanup.return_value = None
        
        # Default successful processing result
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            file_path="/test/file.txt",
            processor_used="MockProcessor",
            chunks_created=5,
            processing_time=1.5,
            metadata={
                'document_processor': 'TextProcessor',
                'file_size': 1024,
                'model_vendor': 'google',
                'file_extension': '.txt'
            }
        )
        
        return mock_processor

    @pytest.fixture
    def file_processor_with_retry(self, mock_services, retry_config, mock_document_processor):
        """Create FileProcessor with retry configuration."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_document_processor,
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
    def mock_document_processor(self):
        """Create mock document processor for additional coverage tests."""
        from src.core.document_processing import DocumentProcessingInterface, ProcessingResult
        
        mock_processor = Mock(spec=DocumentProcessingInterface)
        mock_processor.get_processor_name.return_value = "MockProcessor"
        mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx'}
        mock_processor.initialize.return_value = True
        mock_processor.is_supported_file.return_value = True
        mock_processor.cleanup.return_value = None
        
        # Default successful processing result
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            file_path="/test/file.txt",
            processor_used="MockProcessor",
            chunks_created=5,
            processing_time=1.5,
            metadata={
                'document_processor': 'TextProcessor',
                'file_size': 1024,
                'model_vendor': 'google',
                'file_extension': '.txt'
            }
        )
        
        return mock_processor

    @pytest.fixture
    def file_processor(self, mock_services, mock_document_processor):
        """Create FileProcessor instance with mock services."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_document_processor
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
        
        # Create mock document processor
        from src.core.document_processing import DocumentProcessingInterface, ProcessingResult
        
        self.mock_document_processor = Mock(spec=DocumentProcessingInterface)
        self.mock_document_processor.get_processor_name.return_value = "MockProcessor"
        self.mock_document_processor.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx'}
        self.mock_document_processor.initialize.return_value = True
        self.mock_document_processor.is_supported_file.return_value = True
        self.mock_document_processor.cleanup.return_value = None
        
        # Default successful processing result
        self.mock_document_processor.process_document.return_value = ProcessingResult(
            success=True,
            file_path="/test/file.txt",
            processor_used="MockProcessor",
            chunks_created=5,
            processing_time=1.5,
            metadata={
                'document_processor': 'TextProcessor',
                'file_size': 1024,
                'model_vendor': 'google',
                'file_extension': '.txt'
            }
        )

        # Create FileProcessor with real services
        self.file_processor = FileProcessor(
            self.file_manager,
            self.error_handler,
            self.logger_service,
            self.mock_document_processor
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
        from src.core.document_processing import ProcessingResult
        
        # Configure mock document processor to return failure for empty files
        self.mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path="/test/empty.txt",
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 0}
        )
        
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

class TestFileProcessorEmptyFolderHandling:
    """Test cases for FileProcessor empty folder handling functionality (Task 15.2)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.source_folder = Path(self.temp_dir) / "source"
        self.saved_folder = Path(self.temp_dir) / "saved"
        self.error_folder = Path(self.temp_dir) / "error"
        
        self.source_folder.mkdir(parents=True)
        self.saved_folder.mkdir(parents=True)
        self.error_folder.mkdir(parents=True)
        
        # Create mock services
        self.mock_file_manager = Mock()
        self.mock_error_handler = Mock()
        self.mock_logger = Mock()
        
        # Create mock document processor
        from src.core.document_processing import DocumentProcessingInterface, ProcessingResult
        
        self.mock_document_processor = Mock(spec=DocumentProcessingInterface)
        self.mock_document_processor.get_processor_name.return_value = "MockProcessor"
        self.mock_document_processor.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx'}
        self.mock_document_processor.initialize.return_value = True
        self.mock_document_processor.is_supported_file.return_value = True
        self.mock_document_processor.cleanup.return_value = None
        
        # Default successful processing result
        self.mock_document_processor.process_document.return_value = ProcessingResult(
            success=True,
            file_path="/test/file.txt",
            processor_used="MockProcessor",
            chunks_created=5,
            processing_time=1.5,
            metadata={
                'document_processor': 'TextProcessor',
                'file_size': 1024,
                'model_vendor': 'google',
                'file_extension': '.txt'
            }
        )

        # Initialize FileProcessor
        self.file_processor = FileProcessor(
            self.mock_file_manager,
            self.mock_error_handler,
            self.mock_logger,
            self.mock_document_processor
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_process_empty_folder_success(self):
        """Test successful processing of completely empty folder."""
        # Create completely empty folder
        empty_folder = self.source_folder / "empty_test"
        empty_folder.mkdir()
        
        # Mock FileManager methods
        self.mock_file_manager.should_process_as_empty_folder.return_value = True
        self.mock_file_manager.move_empty_folder_to_error.return_value = True
        self.mock_file_manager.get_relative_path.return_value = "empty_test"
        
        # Process empty folder
        result = self.file_processor.process_empty_folder(str(empty_folder))
        
        # Verify result
        assert result.success is True
        assert result.file_path == str(empty_folder)
        assert result.error_message is None
        assert result.processing_time > 0
        
        # Verify method calls
        self.mock_file_manager.should_process_as_empty_folder.assert_called_once_with(str(empty_folder))
        self.mock_file_manager.move_empty_folder_to_error.assert_called_once_with(str(empty_folder))
        self.mock_error_handler.create_empty_folder_log.assert_called_once_with(str(empty_folder))
        
        # Verify logging
        self.mock_logger.log_info.assert_called_with("Successfully processed completely empty folder: empty_test")
    
    def test_process_empty_folder_not_completely_empty(self):
        """Test processing folder that is not completely empty."""
        # Create folder with subfolder
        folder_with_sub = self.source_folder / "not_empty"
        folder_with_sub.mkdir()
        (folder_with_sub / "subfolder").mkdir()
        
        # Mock FileManager to return False for empty check
        self.mock_file_manager.should_process_as_empty_folder.return_value = False
        
        # Process folder
        result = self.file_processor.process_empty_folder(str(folder_with_sub))
        
        # Verify result
        assert result.success is False
        assert result.file_path == str(folder_with_sub)
        assert "should not be processed as empty (may have had processed files)" in result.error_message
        assert result.processing_time > 0
        
        # Verify only empty check was called
        self.mock_file_manager.should_process_as_empty_folder.assert_called_once_with(str(folder_with_sub))
        self.mock_file_manager.move_empty_folder_to_error.assert_not_called()
        self.mock_error_handler.create_empty_folder_log.assert_not_called()
        
        # Verify error logging
        self.mock_logger.log_error.assert_called_with(f"Folder should not be processed as empty (may have had processed files): {folder_with_sub}")
    
    def test_process_empty_folder_move_fails(self):
        """Test processing when moving empty folder to error folder fails."""
        # Create completely empty folder
        empty_folder = self.source_folder / "move_fail_test"
        empty_folder.mkdir()
        
        # Mock FileManager methods
        self.mock_file_manager.should_process_as_empty_folder.return_value = True
        self.mock_file_manager.move_empty_folder_to_error.return_value = False  # Move fails
        
        # Process empty folder
        result = self.file_processor.process_empty_folder(str(empty_folder))
        
        # Verify result
        assert result.success is False
        assert result.file_path == str(empty_folder)
        assert "Failed to move empty folder to error folder" in result.error_message
        assert result.processing_time > 0
        
        # Verify method calls
        self.mock_file_manager.should_process_as_empty_folder.assert_called_once_with(str(empty_folder))
        self.mock_file_manager.move_empty_folder_to_error.assert_called_once_with(str(empty_folder))
        self.mock_error_handler.create_empty_folder_log.assert_not_called()  # Should not create log if move fails
        
        # Verify error logging
        self.mock_logger.log_error.assert_called_with(f"Failed to move empty folder to error folder: {empty_folder}")
    
    def test_process_empty_folder_log_creation_fails(self):
        """Test processing when empty folder log creation fails."""
        # Create completely empty folder
        empty_folder = self.source_folder / "log_fail_test"
        empty_folder.mkdir()
        
        # Mock FileManager methods
        self.mock_file_manager.should_process_as_empty_folder.return_value = True
        self.mock_file_manager.move_empty_folder_to_error.return_value = True
        self.mock_file_manager.get_relative_path.return_value = "log_fail_test"
        
        # Mock error handler to raise exception
        self.mock_error_handler.create_empty_folder_log.side_effect = Exception("Log creation failed")
        
        # Process empty folder
        result = self.file_processor.process_empty_folder(str(empty_folder))
        
        # Verify result (should still be successful since log creation failure doesn't fail the whole operation)
        assert result.success is True
        assert result.file_path == str(empty_folder)
        assert result.error_message is None
        
        # Verify method calls
        self.mock_file_manager.move_empty_folder_to_error.assert_called_once_with(str(empty_folder))
        self.mock_error_handler.create_empty_folder_log.assert_called_once_with(str(empty_folder))
        
        # Verify error logging for log creation failure
        self.mock_logger.log_error.assert_any_call("Failed to create empty folder log: Log creation failed")
        # Verify success logging still occurs
        self.mock_logger.log_info.assert_called_with("Successfully processed completely empty folder: log_fail_test")
    
    def test_process_empty_folder_general_exception(self):
        """Test processing when general exception occurs."""
        # Create completely empty folder
        empty_folder = self.source_folder / "exception_test"
        empty_folder.mkdir()
        
        # Mock FileManager to raise exception
        self.mock_file_manager.should_process_as_empty_folder.side_effect = Exception("General error")
        
        # Process empty folder
        result = self.file_processor.process_empty_folder(str(empty_folder))
        
        # Verify result
        assert result.success is False
        assert result.file_path == str(empty_folder)
        assert "Failed to process empty folder" in result.error_message
        assert "General error" in result.error_message
        assert result.processing_time > 0
        
        # Verify error logging
        self.mock_logger.log_error.assert_called()
        call_args = self.mock_logger.log_error.call_args[0]
        assert "Failed to process empty folder" in call_args[0]
        assert "General error" in call_args[0]
    
    def test_process_empty_folder_with_relative_path(self):
        """Test processing empty folder with relative path calculation."""
        # Create nested empty folder
        nested_empty = self.source_folder / "level1" / "level2" / "empty_nested"
        nested_empty.mkdir(parents=True)
        
        # Mock FileManager methods
        self.mock_file_manager.should_process_as_empty_folder.return_value = True
        self.mock_file_manager.move_empty_folder_to_error.return_value = True
        self.mock_file_manager.get_relative_path.return_value = "level1/level2/empty_nested"
        
        # Process empty folder
        result = self.file_processor.process_empty_folder(str(nested_empty))
        
        # Verify result
        assert result.success is True
        
        # Verify relative path was used in logging
        self.mock_file_manager.get_relative_path.assert_called_with(str(nested_empty))
        self.mock_logger.log_info.assert_called_with("Successfully processed completely empty folder: level1/level2/empty_nested")
    
    def test_process_empty_folder_fallback_to_basename(self):
        """Test processing empty folder when relative path calculation fails."""
        # Create empty folder
        empty_folder = self.source_folder / "basename_test"
        empty_folder.mkdir()
        
        # Mock FileManager methods
        self.mock_file_manager.should_process_as_empty_folder.return_value = True
        self.mock_file_manager.move_empty_folder_to_error.return_value = True
        self.mock_file_manager.get_relative_path.return_value = None  # Relative path fails
        
        # Process empty folder
        result = self.file_processor.process_empty_folder(str(empty_folder))
        
        # Verify result
        assert result.success is True
        
        # Verify basename was used in logging when relative path fails
        self.mock_logger.log_info.assert_called_with("Successfully processed completely empty folder: basename_test")
    
    def test_process_empty_folder_nonexistent_folder(self):
        """Test processing non-existent folder."""
        # Use path to non-existent folder
        nonexistent_folder = str(self.source_folder / "nonexistent")
        
        # Mock FileManager to return False for empty check
        self.mock_file_manager.should_process_as_empty_folder.return_value = False
        
        # Process folder
        result = self.file_processor.process_empty_folder(nonexistent_folder)
        
        # Verify result
        assert result.success is False
        assert result.file_path == nonexistent_folder
        assert "should not be processed as empty (may have had processed files)" in result.error_message
        
        # Verify only empty check was called
        self.mock_file_manager.should_process_as_empty_folder.assert_called_once_with(nonexistent_folder)
        self.mock_file_manager.move_empty_folder_to_error.assert_not_called()
    
    def test_process_empty_folder_timing_measurement(self):
        """Test that processing time is accurately measured."""
        # Create empty folder
        empty_folder = self.source_folder / "timing_test"
        empty_folder.mkdir()
        
        # Mock FileManager methods with delay
        def slow_empty_check(path):
            time.sleep(0.1)  # Simulate some processing time
            return True
        
        def slow_move(path):
            time.sleep(0.1)  # Simulate some processing time
            return True
        
        self.mock_file_manager.should_process_as_empty_folder.side_effect = slow_empty_check
        self.mock_file_manager.move_empty_folder_to_error.side_effect = slow_move
        self.mock_file_manager.get_relative_path.return_value = "timing_test"
        
        # Process empty folder
        result = self.file_processor.process_empty_folder(str(empty_folder))
        
        # Verify timing
        assert result.success is True
        assert result.processing_time >= 0.2  # Should be at least 0.2 seconds due to delays
        assert result.processing_time < 1.0   # Should be reasonable
    
    def test_process_empty_folder_multiple_folders(self):
        """Test processing multiple empty folders."""
        # Create multiple empty folders
        empty_folders = []
        for i in range(3):
            folder = self.source_folder / f"empty_{i}"
            folder.mkdir()
            empty_folders.append(str(folder))
        
        # Mock FileManager methods
        self.mock_file_manager.should_process_as_empty_folder.return_value = True
        self.mock_file_manager.move_empty_folder_to_error.return_value = True
        self.mock_file_manager.get_relative_path.side_effect = lambda path: Path(path).name
        
        # Process all empty folders
        results = []
        for folder_path in empty_folders:
            result = self.file_processor.process_empty_folder(folder_path)
            results.append(result)
        
        # Verify all results
        for i, result in enumerate(results):
            assert result.success is True
            assert result.file_path == empty_folders[i]
            assert result.error_message is None
        
        # Verify all folders were processed
        assert self.mock_file_manager.should_process_as_empty_folder.call_count == 3
        assert self.mock_file_manager.move_empty_folder_to_error.call_count == 3
        assert self.mock_error_handler.create_empty_folder_log.call_count == 3
    
    def test_empty_folder_processing_integration_with_regular_file_processing(self):
        """Test that empty folder processing doesn't interfere with regular file processing."""
        # Create test file
        test_file = self.source_folder / "test.txt"
        test_file.write_text("test content")
        
        # Create empty folder
        empty_folder = self.source_folder / "empty"
        empty_folder.mkdir()
        
        # Mock FileManager for regular file processing
        self.mock_file_manager.move_to_saved.return_value = True
        self.mock_file_manager.cleanup_empty_folders.return_value = []
        self.mock_file_manager.get_relative_path.return_value = "test.txt"
        
        # Mock FileManager for empty folder processing
        self.mock_file_manager.should_process_as_empty_folder.return_value = True
        self.mock_file_manager.move_empty_folder_to_error.return_value = True
        
        # Process regular file
        file_result = self.file_processor.process_file(str(test_file))
        
        # Process empty folder
        folder_result = self.file_processor.process_empty_folder(str(empty_folder))
        
        # Verify both processed successfully
        assert file_result.success is True
        assert folder_result.success is True
        
        # Verify different methods were called for each type
        self.mock_file_manager.move_to_saved.assert_called_once()
        self.mock_file_manager.move_empty_folder_to_error.assert_called_once()
        self.mock_error_handler.create_empty_folder_log.assert_called_once()
        
        # Verify different logging occurred
        self.mock_logger.log_info.assert_any_call("Successfully processed file: test.txt")
        # Note: The empty folder logging uses the relative path which returns "test.txt" in this mock setup
        # This is expected behavior as the mock returns "test.txt" for any path
        assert any("Successfully processed completely empty folder:" in str(call) for call in self.mock_logger.log_info.call_args_list)


class TestDocumentProcessingIntegration:
    """Test cases for document processing integration in FileProcessor."""
    
    @pytest.fixture
    def mock_document_processor(self):
        """Create mock document processor for testing."""
        from src.core.document_processing import DocumentProcessingInterface, ProcessingResult
        
        mock_processor = Mock(spec=DocumentProcessingInterface)
        mock_processor.get_processor_name.return_value = "MockProcessor"
        mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx'}
        mock_processor.initialize.return_value = True
        mock_processor.is_supported_file.return_value = True
        mock_processor.cleanup.return_value = None
        
        # Default successful processing result
        mock_processor.process_document.return_value = ProcessingResult(
            success=True,
            file_path="/test/file.txt",
            processor_used="MockProcessor",
            chunks_created=5,
            processing_time=1.5,
            metadata={
                'document_processor': 'TextProcessor',
                'file_size': 1024,
                'model_vendor': 'google',
                'file_extension': '.txt'
            }
        )
        
        return mock_processor
    
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
        file_manager.cleanup_empty_folders.return_value = []
        
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
    def file_processor_with_doc_processor(self, mock_services, mock_document_processor):
        """Create FileProcessor with document processor."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_document_processor
        )
    
    def test_file_processor_initialization_with_document_processor(self, mock_services, mock_document_processor):
        """Test FileProcessor initialization with document processor."""
        processor = FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_document_processor
        )
        
        assert processor.document_processor == mock_document_processor
        mock_services['logger_service'].log_info.assert_called()
    
    def test_file_processor_initialization_none_document_processor(self, mock_services):
        """Test FileProcessor initialization with None document processor works correctly."""
        processor = FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=None
        )
        
        # Should successfully create FileProcessor with None document processor
        assert processor.document_processor is None
        
        # Verify no validation logging occurs when document processor is None
        mock_services['logger_service'].log_info.assert_not_called()
        mock_services['logger_service'].log_error.assert_not_called()
    
    def test_file_processor_initialization_invalid_document_processor(self, mock_services):
        """Test FileProcessor initialization with invalid document processor."""
        # Create a class that doesn't implement all required methods
        class InvalidProcessor:
            def get_supported_extensions(self):
                return {'.txt'}
            # Missing other required methods like initialize, process_document, etc.
        
        invalid_processor = InvalidProcessor()
        
        with pytest.raises(ValueError, match="Document processor missing required method"):
            FileProcessor(
                file_manager=mock_services['file_manager'],
                error_handler=mock_services['error_handler'],
                logger_service=mock_services['logger_service'],
                document_processor=invalid_processor
            )
    
    def test_document_processing_success(self, file_processor_with_doc_processor, mock_services, mock_document_processor, temp_dirs):
        """Test successful document processing workflow."""
        # Create test file
        test_file = Path(temp_dirs['source']) / "test_document.txt"
        test_file.write_text("Test content")
        
        # Configure mock to return correct filename
        mock_services['file_manager'].get_relative_path.return_value = "test_document.txt"
        
        # Process file
        with patch('builtins.print') as mock_print:
            result = file_processor_with_doc_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is True
        assert result.file_path == str(test_file)
        assert result.processing_time > 0
        
        # Verify document processor was called
        mock_document_processor.process_document.assert_called_once()
        call_args = mock_document_processor.process_document.call_args[0][0]
        assert str(call_args) == str(test_file)
        
        # Verify file was moved to saved folder
        mock_services['file_manager'].move_to_saved.assert_called_once_with(str(test_file))
        
        # Verify detailed logging
        mock_services['logger_service'].log_info.assert_called()
        log_calls = mock_services['logger_service'].log_info.call_args_list
        processing_log = [call for call in log_calls if 'Document processing completed' in str(call)]
        assert len(processing_log) > 0
        
        # Verify print output
        mock_print.assert_called_once_with("Processed file: test_document.txt")
    
    def test_document_processing_unsupported_file_type(self, file_processor_with_doc_processor, mock_services, mock_document_processor, temp_dirs):
        """Test document processing with unsupported file type."""
        from src.core.document_processing import ProcessingResult
        
        # Create test file
        test_file = Path(temp_dirs['source']) / "unsupported.xyz"
        test_file.write_text("Test content")
        
        # Mock document processor to return unsupported file type error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="Unsupported file type: .xyz",
            error_type="unsupported_file_type",
            metadata={
                'file_extension': '.xyz',
                'supported_extensions': ['.txt', '.pdf', '.docx']
            }
        )
        
        # Process file
        result = file_processor_with_doc_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert "Unsupported file type" in result.error_message
        
        # Verify file was moved to error folder
        mock_services['file_manager'].move_to_error.assert_called_once_with(str(test_file))
        mock_services['error_handler'].create_error_log.assert_called_once()
    
    def test_document_processing_empty_document(self, file_processor_with_doc_processor, mock_services, mock_document_processor, temp_dirs):
        """Test document processing with empty document."""
        from src.core.document_processing import ProcessingResult
        
        # Create test file
        test_file = Path(temp_dirs['source']) / "empty.txt"
        test_file.write_text("")
        
        # Mock document processor to return empty document error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="No content extracted from document",
            error_type="empty_document",
            metadata={'file_size': 0}
        )
        
        # Process file
        result = file_processor_with_doc_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert "Empty document" in result.error_message
        
        # Verify error handling
        mock_services['file_manager'].move_to_error.assert_called_once()
        mock_services['error_handler'].create_error_log.assert_called_once()
    
    def test_document_processing_initialization_error(self, file_processor_with_doc_processor, mock_services, mock_document_processor, temp_dirs):
        """Test document processing with initialization error."""
        from src.core.document_processing import ProcessingResult
        
        # Create test file
        test_file = Path(temp_dirs['source']) / "test.txt"
        test_file.write_text("Test content")
        
        # Mock document processor to return initialization error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.0,
            error_message="Processor not initialized",
            error_type="initialization_error"
        )
        
        # Process file
        result = file_processor_with_doc_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert "Processor not initialized" in result.error_message
        
        # Verify error handling
        mock_services['file_manager'].move_to_error.assert_called_once()
    
    def test_document_processing_with_enhanced_error_info(self, file_processor_with_doc_processor, mock_services, mock_document_processor, temp_dirs):
        """Test document processing with DocumentProcessingError in metadata."""
        from src.core.document_processing import ProcessingResult, DocumentProcessingError
        
        # Create test file
        test_file = Path(temp_dirs['source']) / "error_test.txt"
        test_file.write_text("Test content")
        
        # Create DocumentProcessingError
        processing_error = DocumentProcessingError(
            file_path=str(test_file),
            processor_type="MockProcessor",
            error_message="API rate limit exceeded",
            error_type="rate_limit_error",
            stack_trace="Mock stack trace",
            file_metadata={'file_size': 100},
            processing_context={'model_vendor': 'google'}
        )
        
        # Mock document processor to return error with enhanced info
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.5,
            error_message="API rate limit exceeded",
            error_type="rate_limit_error",
            metadata={'processing_error': processing_error}
        )
        
        # Process file
        result = file_processor_with_doc_processor.process_file(str(test_file))
        
        # Verify result
        assert result.success is False
        assert "Document processing failed" in result.error_message
        
        # Verify error handling
        mock_services['file_manager'].move_to_error.assert_called_once()
        # Should call enhanced error logging since DocumentProcessingError is present
        mock_services['error_handler'].create_document_processing_error_log.assert_called_once()
    
    def test_error_classification_document_processing_errors(self, file_processor_with_doc_processor):
        """Test error classification for document processing specific errors."""
        processor = file_processor_with_doc_processor
        
        # Test permanent document processing errors
        assert processor._classify_error(ValueError("Unsupported file type")) == ErrorType.PERMANENT
        assert processor._classify_error(ValueError("Empty document")) == ErrorType.PERMANENT
        assert processor._classify_error(RuntimeError("Processor not initialized")) == ErrorType.PERMANENT
        assert processor._classify_error(ValueError("Invalid file format")) == ErrorType.PERMANENT
        
        # Test transient document processing errors
        assert processor._classify_error(RuntimeError("API rate limit exceeded")) == ErrorType.TRANSIENT
        assert processor._classify_error(RuntimeError("Connection timeout")) == ErrorType.TRANSIENT
        assert processor._classify_error(RuntimeError("Network error")) == ErrorType.TRANSIENT
        assert processor._classify_error(RuntimeError("ChromaDB connection failed")) == ErrorType.TRANSIENT
        assert processor._classify_error(RuntimeError("Embedding generation failed")) == ErrorType.TRANSIENT
    
    def test_document_processing_retry_on_transient_errors(self, mock_services, mock_document_processor, temp_dirs):
        """Test that document processing retries on transient errors."""
        from src.core.document_processing import ProcessingResult
        
        # Create processor with retry config
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)
        processor = FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_document_processor,
            retry_config=retry_config
        )
        
        # Create test file
        test_file = Path(temp_dirs['source']) / "retry_test.txt"
        test_file.write_text("Test content")
        
        # Mock document processor to fail with transient error then succeed
        mock_document_processor.process_document.side_effect = [
            RuntimeError("API rate limit exceeded"),  # Transient error
            ProcessingResult(
                success=True,
                file_path=str(test_file),
                processor_used="MockProcessor",
                chunks_created=3,
                processing_time=1.0
            )
        ]
        
        # Process file
        with patch('builtins.print'):
            result = processor.process_file(str(test_file))
        
        # Should succeed after retry
        assert result.success is True
        assert mock_document_processor.process_document.call_count == 2
        assert processor.stats['retries_attempted'] == 1
    
    def test_document_processing_no_retry_on_permanent_errors(self, mock_services, mock_document_processor, temp_dirs):
        """Test that document processing doesn't retry on permanent errors."""
        from src.core.document_processing import ProcessingResult
        
        # Create processor with retry config
        retry_config = RetryConfig(max_attempts=3, base_delay=0.01)
        processor = FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_document_processor,
            retry_config=retry_config
        )
        
        # Create test file
        test_file = Path(temp_dirs['source']) / "permanent_error_test.xyz"
        test_file.write_text("Test content")
        
        # Mock document processor to fail with permanent error
        mock_document_processor.process_document.return_value = ProcessingResult(
            success=False,
            file_path=str(test_file),
            processor_used="MockProcessor",
            processing_time=0.1,
            error_message="Unsupported file type: .xyz",
            error_type="unsupported_file_type"
        )
        
        # Process file
        result = processor.process_file(str(test_file))
        
        # Should fail without retry
        assert result.success is False
        assert mock_document_processor.process_document.call_count == 1
        assert processor.stats['retries_attempted'] == 0
        assert processor.stats['failed_permanent'] == 1