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

from src.core.file_processor import FileProcessor, ProcessingResult
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
        mock_services['logger_service'].log_error.assert_called_once()
    
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
        assert "Permission denied when reading file" in result.error_message
        
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
        assert "Failed to decode file" in result.error_message
    
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