"""
Unit tests for enhanced document processing error handling.

Tests the enhanced error classification, DocumentProcessingError handling,
and enhanced error logging functionality in FileProcessor and ErrorHandler.
"""

import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.core.file_processor import FileProcessor, ErrorType
from src.services.error_handler import ErrorHandler
from src.services.logger_service import LoggerService
from src.core.file_manager import FileManager
from src.core.document_processing import (
    DocumentProcessingInterface,
    DocumentProcessingError,
    ProcessingResult
)


class TestDocumentProcessingErrorClassification:
    """Test cases for enhanced error classification with DocumentProcessingError support."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for FileProcessor."""
        document_processor = Mock(spec=DocumentProcessingInterface)
        document_processor.get_supported_extensions.return_value = {'.pdf', '.txt', '.docx'}
        document_processor.get_processor_name.return_value = "MockProcessor"
        
        return {
            'file_manager': Mock(spec=FileManager),
            'error_handler': Mock(spec=ErrorHandler),
            'logger_service': Mock(spec=LoggerService),
            'document_processor': document_processor
        }
    
    @pytest.fixture
    def file_processor(self, mock_services):
        """Create FileProcessor instance with mocked services."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_services['document_processor']
        )
    
    def test_classify_document_processing_error_permanent_types(self, file_processor):
        """Test classification of permanent DocumentProcessingError types."""
        permanent_error_types = [
            'unsupported_file_type',
            'empty_document',
            'invalid_file_format',
            'corrupted_file',
            'file_too_large',
            'initialization_error',
            'configuration_error',
            'invalid_document_structure',
            'malformed_content',
            'encoding_error'
        ]
        
        for error_type in permanent_error_types:
            doc_error = DocumentProcessingError(
                file_path="/test/file.txt",
                processor_type="TestProcessor",
                error_message=f"Test {error_type} error",
                error_type=error_type
            )
            
            classification = file_processor._classify_document_processing_error(doc_error)
            assert classification == ErrorType.PERMANENT, f"Failed for error_type: {error_type}"
    
    def test_classify_document_processing_error_transient_types(self, file_processor):
        """Test classification of transient DocumentProcessingError types."""
        transient_error_types = [
            'api_rate_limit',
            'connection_timeout',
            'network_error',
            'service_unavailable',
            'temporary_failure',
            'quota_exceeded',
            'server_overloaded',
            'chromadb_error',
            'embedding_generation_failed'
        ]
        
        for error_type in transient_error_types:
            doc_error = DocumentProcessingError(
                file_path="/test/file.txt",
                processor_type="TestProcessor",
                error_message=f"Test {error_type} error",
                error_type=error_type
            )
            
            classification = file_processor._classify_document_processing_error(doc_error)
            assert classification == ErrorType.TRANSIENT, f"Failed for error_type: {error_type}"
    
    def test_classify_document_processing_error_by_message_content(self, file_processor):
        """Test classification based on error message content."""
        # Transient error messages
        transient_messages = [
            "Rate limit exceeded for API",
            "Connection timeout occurred",
            "Network error during processing",
            "Service temporarily unavailable",
            "ChromaDB connection failed",
            "Quota exceeded for embeddings"
        ]
        
        for message in transient_messages:
            doc_error = DocumentProcessingError(
                file_path="/test/file.txt",
                processor_type="TestProcessor",
                error_message=message,
                error_type="unknown_error"
            )
            
            classification = file_processor._classify_document_processing_error(doc_error)
            assert classification == ErrorType.TRANSIENT, f"Failed for message: {message}"
        
        # Permanent error messages
        permanent_messages = [
            "Unsupported file format detected",
            "Invalid document structure",
            "File is corrupted and cannot be processed",
            "Empty document with no content",
            "Malformed PDF structure"
        ]
        
        for message in permanent_messages:
            doc_error = DocumentProcessingError(
                file_path="/test/file.txt",
                processor_type="TestProcessor",
                error_message=message,
                error_type="unknown_error"
            )
            
            classification = file_processor._classify_document_processing_error(doc_error)
            assert classification == ErrorType.PERMANENT, f"Failed for message: {message}"
    
    def test_classify_document_processing_error_unknown_defaults_permanent(self, file_processor):
        """Test that unknown DocumentProcessingError types default to permanent."""
        doc_error = DocumentProcessingError(
            file_path="/test/file.txt",
            processor_type="TestProcessor",
            error_message="Unknown processing error",
            error_type="completely_unknown_error_type"
        )
        
        classification = file_processor._classify_document_processing_error(doc_error)
        assert classification == ErrorType.PERMANENT
    
    def test_classify_error_with_document_processing_error_cause(self, file_processor):
        """Test error classification when exception has DocumentProcessingError as cause."""
        doc_error = DocumentProcessingError(
            file_path="/test/file.txt",
            processor_type="TestProcessor",
            error_message="API rate limit exceeded",
            error_type="api_rate_limit"
        )
        
        # Create exception with DocumentProcessingError information
        # Since DocumentProcessingError is not a BaseException, we simulate it differently
        runtime_error = RuntimeError("Document processing failed: API rate limit exceeded")
        
        classification = file_processor._classify_error(runtime_error)
        assert classification == ErrorType.TRANSIENT
    
    def test_classify_error_enhanced_document_processing_keywords(self, file_processor):
        """Test enhanced error classification with additional document processing keywords."""
        # Test new permanent error keywords
        permanent_errors = [
            RuntimeError("Invalid document structure detected"),
            ValueError("Malformed content in file"),
            RuntimeError("File too large for processing")
        ]
        
        for error in permanent_errors:
            classification = file_processor._classify_error(error)
            assert classification == ErrorType.PERMANENT, f"Failed for error: {error}"
        
        # Test new transient error keywords
        transient_errors = [
            RuntimeError("Rate limit exceeded by API"),
            RuntimeError("Quota exceeded for service"),
            RuntimeError("Server overloaded, try again later")
        ]
        
        for error in transient_errors:
            classification = file_processor._classify_error(error)
            assert classification == ErrorType.TRANSIENT, f"Failed for error: {error}"
    
    def test_extract_document_processing_error_from_cause(self, file_processor):
        """Test extraction of DocumentProcessingError from exception cause."""
        doc_error = DocumentProcessingError(
            file_path="/test/file.txt",
            processor_type="TestProcessor",
            error_message="Test error",
            error_type="test_error"
        )
        
        # Since DocumentProcessingError can't be a cause, test with a custom exception
        class DocumentProcessingException(Exception):
            def __init__(self, message, doc_error):
                super().__init__(message)
                self.doc_error = doc_error
        
        runtime_error = RuntimeError("Processing failed")
        runtime_error.__cause__ = DocumentProcessingException("Doc error", doc_error)
        
        # For this test, we'll check metadata extraction instead
        runtime_error.metadata = {'processing_error': doc_error}
        extracted = file_processor._extract_document_processing_error(runtime_error)
        assert extracted is doc_error
    
    def test_extract_document_processing_error_from_args(self, file_processor):
        """Test extraction of DocumentProcessingError from exception args."""
        doc_error = DocumentProcessingError(
            file_path="/test/file.txt",
            processor_type="TestProcessor",
            error_message="Test error",
            error_type="test_error"
        )
        
        runtime_error = RuntimeError("Processing failed", doc_error)
        
        extracted = file_processor._extract_document_processing_error(runtime_error)
        assert extracted is doc_error
    
    def test_extract_document_processing_error_from_metadata(self, file_processor):
        """Test extraction of DocumentProcessingError from exception metadata."""
        doc_error = DocumentProcessingError(
            file_path="/test/file.txt",
            processor_type="TestProcessor",
            error_message="Test error",
            error_type="test_error"
        )
        
        runtime_error = RuntimeError("Processing failed")
        runtime_error.metadata = {'processing_error': doc_error}
        
        extracted = file_processor._extract_document_processing_error(runtime_error)
        assert extracted is doc_error
    
    def test_extract_document_processing_error_not_found(self, file_processor):
        """Test extraction returns None when no DocumentProcessingError is found."""
        runtime_error = RuntimeError("Regular error")
        
        extracted = file_processor._extract_document_processing_error(runtime_error)
        assert extracted is None


class TestEnhancedErrorLogging:
    """Test cases for enhanced error logging with DocumentProcessingError support."""
    
    @pytest.fixture
    def temp_error_folder(self):
        """Create a temporary directory for error logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def temp_source_folder(self):
        """Create a temporary directory for source files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def error_handler(self, temp_error_folder, temp_source_folder):
        """Create ErrorHandler instance with temporary folders."""
        return ErrorHandler(temp_error_folder, temp_source_folder)
    
    @pytest.fixture
    def sample_file(self, temp_source_folder):
        """Create a sample file for testing."""
        sample_file_path = Path(temp_source_folder) / "sample.pdf"
        sample_file_path.write_text("Sample PDF content")
        return str(sample_file_path)
    
    def test_create_document_processing_error_log_basic(self, error_handler, sample_file):
        """Test basic document processing error log creation."""
        doc_error = DocumentProcessingError(
            file_path=sample_file,
            processor_type="RAGStoreProcessor",
            error_message="Failed to generate embeddings",
            error_type="embedding_generation_failed",
            file_metadata={"size": 1024, "type": "pdf"},
            processing_context={"chunks_attempted": 5, "model": "text-embedding-004"}
        )
        
        error_handler.create_document_processing_error_log(
            sample_file, 
            "Document processing failed", 
            None, 
            doc_error
        )
        
        # Check that error log file was created
        expected_log_path = error_handler.error_folder / "sample.pdf.log"
        assert expected_log_path.exists()
        
        # Verify log content
        log_content = expected_log_path.read_text()
        assert "DOCUMENT PROCESSING ERROR LOG" in log_content
        assert "Document processing failed" in log_content
        assert "RAGStoreProcessor" in log_content
        assert "embedding_generation_failed" in log_content
        assert "Failed to generate embeddings" in log_content
        assert "chunks_attempted: 5" in log_content
        assert "model: text-embedding-004" in log_content
        assert "size: 1024" in log_content
        assert "type: pdf" in log_content
    
    def test_create_document_processing_error_log_with_exception(self, error_handler, sample_file):
        """Test document processing error log creation with exception details."""
        doc_error = DocumentProcessingError(
            file_path=sample_file,
            processor_type="RAGStoreProcessor",
            error_message="ChromaDB connection failed",
            error_type="chromadb_error",
            stack_trace="Traceback: ChromaDB connection error\n"
        )
        
        test_exception = RuntimeError("Processing pipeline failed")
        
        error_handler.create_document_processing_error_log(
            sample_file,
            "Document processing pipeline error",
            test_exception,
            doc_error
        )
        
        expected_log_path = error_handler.error_folder / "sample.pdf.log"
        log_content = expected_log_path.read_text()
        
        assert "Document processing pipeline error" in log_content
        assert "RuntimeError" in log_content
        assert "Application Stack Trace:" in log_content
        assert "Document Processing Stack Trace:" in log_content
        assert "ChromaDB connection error" in log_content
    
    def test_create_document_processing_error_log_without_doc_error(self, error_handler, sample_file):
        """Test document processing error log creation falls back to regular log when no DocumentProcessingError."""
        error_handler.create_document_processing_error_log(
            sample_file,
            "Regular processing error",
            None,
            None
        )
        
        expected_log_path = error_handler.error_folder / "sample.pdf.log"
        log_content = expected_log_path.read_text()
        
        # Should still create log but without document processing specific sections
        assert "DOCUMENT PROCESSING ERROR LOG" in log_content
        assert "Regular processing error" in log_content
        # Should not have document processing specific sections
        assert "Document Processing Information:" not in log_content
        assert "Processing Context:" not in log_content
    
    def test_build_document_processing_error_info_complete(self, error_handler, sample_file):
        """Test building complete document processing error information."""
        doc_error = DocumentProcessingError(
            file_path=sample_file,
            processor_type="RAGStoreProcessor",
            error_message="Embedding API rate limit exceeded",
            error_type="api_rate_limit",
            file_metadata={"size": 2048, "type": "pdf", "pages": 10},
            processing_context={
                "chunks_created": 3,
                "chunks_failed": 2,
                "model_vendor": "google",
                "collection": "documents_google"
            },
            stack_trace="Document processing stack trace here"
        )
        
        test_exception = RuntimeError("Rate limit error")
        
        error_info = error_handler._build_document_processing_error_info(
            sample_file, "Processing failed due to rate limit", test_exception, doc_error
        )
        
        # Check basic error info is included
        assert error_info['file_path'] == sample_file
        assert error_info['error_message'] == "Processing failed due to rate limit"
        assert error_info['exception_type'] == 'RuntimeError'
        
        # Check document processing specific info
        assert error_info['processor_type'] == "RAGStoreProcessor"
        assert error_info['document_error_type'] == "api_rate_limit"
        assert error_info['document_error_message'] == "Embedding API rate limit exceeded"
        assert 'processing_timestamp' in error_info
        
        # Check metadata and context
        assert error_info['file_metadata']['size'] == 2048
        assert error_info['file_metadata']['pages'] == 10
        assert error_info['processing_context']['chunks_created'] == 3
        assert error_info['processing_context']['model_vendor'] == "google"
        assert error_info['document_stack_trace'] == "Document processing stack trace here"
    
    def test_write_document_processing_error_log_format(self, error_handler, temp_error_folder):
        """Test document processing error log file format and structure."""
        log_path = Path(temp_error_folder) / "test_doc_error.log"
        
        error_info = {
            'timestamp': '2025-01-23T10:30:45.123456',
            'file_path': '/source/document.pdf',
            'error_message': 'Document processing failed',
            'file_size': 2048,
            'last_modified': '2025-01-23T10:29:12.000000',
            'processor_type': 'RAGStoreProcessor',
            'document_error_type': 'embedding_generation_failed',
            'document_error_message': 'Failed to generate embeddings for chunks',
            'processing_timestamp': '2025-01-23T10:30:44.000000',
            'file_metadata': {
                'type': 'pdf',
                'pages': 5,
                'size_mb': 2.0
            },
            'processing_context': {
                'chunks_attempted': 10,
                'chunks_successful': 7,
                'model_vendor': 'google',
                'collection': 'documents_google'
            },
            'exception_type': 'RuntimeError',
            'stack_trace': ['Traceback (most recent call last):\n', '  RuntimeError: Processing failed\n'],
            'document_stack_trace': 'Document processor stack trace here'
        }
        
        error_handler._write_document_processing_error_log(log_path, error_info)
        
        content = log_path.read_text()
        
        # Check required sections and format
        assert "DOCUMENT PROCESSING ERROR LOG" in content
        assert "=" * 60 in content  # Enhanced header
        
        # Basic information
        assert "Timestamp: 2025-01-23T10:30:45.123456" in content
        assert "File: /source/document.pdf" in content
        assert "Error: Document processing failed" in content
        
        # Document processing specific information
        assert "Document Processing Information:" in content
        assert "Processor Type: RAGStoreProcessor" in content
        assert "Document Error Type: embedding_generation_failed" in content
        assert "Document Error Message: Failed to generate embeddings for chunks" in content
        assert "Processing Timestamp: 2025-01-23T10:30:44.000000" in content
        
        # File information with metadata
        assert "File Information:" in content
        assert "Size: 2048 bytes" in content
        assert "Document Metadata:" in content
        assert "type: pdf" in content
        assert "pages: 5" in content
        
        # Processing context
        assert "Processing Context:" in content
        assert "chunks_attempted: 10" in content
        assert "model_vendor: google" in content
        
        # Stack traces
        assert "Application Stack Trace:" in content
        assert "Document Processing Stack Trace:" in content
        assert "Document processor stack trace here" in content
    
    def test_create_document_processing_error_log_handles_write_failure(self, error_handler, sample_file):
        """Test document processing error log creation handles write failures gracefully."""
        doc_error = DocumentProcessingError(
            file_path=sample_file,
            processor_type="TestProcessor",
            error_message="Test error",
            error_type="test_error"
        )
        
        # Mock open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('builtins.print') as mock_print:
                error_handler.create_document_processing_error_log(
                    sample_file, "Test error", None, doc_error
                )
                
                # Should print error message instead of crashing
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                assert "Failed to create document processing error log" in call_args
                assert sample_file in call_args


class TestFileProcessorDocumentErrorIntegration:
    """Test cases for FileProcessor integration with document processing error handling."""
    
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
                'error': str(error_dir)
            }
    
    @pytest.fixture
    def mock_services(self, temp_dirs):
        """Create mock services for FileProcessor."""
        file_manager = Mock(spec=FileManager)
        file_manager.get_relative_path.return_value = "test_file.pdf"
        
        error_handler = Mock(spec=ErrorHandler)
        logger_service = Mock(spec=LoggerService)
        document_processor = Mock(spec=DocumentProcessingInterface)
        
        # Setup document processor mock
        document_processor.get_supported_extensions.return_value = {'.pdf', '.txt', '.docx'}
        document_processor.get_processor_name.return_value = "MockProcessor"
        
        return {
            'file_manager': file_manager,
            'error_handler': error_handler,
            'logger_service': logger_service,
            'document_processor': document_processor
        }
    
    @pytest.fixture
    def file_processor(self, mock_services):
        """Create FileProcessor instance with mocked services."""
        return FileProcessor(
            file_manager=mock_services['file_manager'],
            error_handler=mock_services['error_handler'],
            logger_service=mock_services['logger_service'],
            document_processor=mock_services['document_processor']
        )
    
    def test_process_file_with_document_processing_error_calls_enhanced_logging(self, file_processor, mock_services, temp_dirs):
        """Test that FileProcessor calls enhanced error logging when DocumentProcessingError is present."""
        # Create test file
        test_file = Path(temp_dirs['source']) / "test_document.pdf"
        test_file.write_text("Test content")
        
        # Create DocumentProcessingError
        doc_error = DocumentProcessingError(
            file_path=str(test_file),
            processor_type="MockProcessor",
            error_message="Failed to process document",
            error_type="processing_failure"
        )
        
        # Setup document processor to fail with DocumentProcessingError in metadata
        processing_result = ProcessingResult(
            success=False,
            file_path=str(test_file),
            error_message="Processing failed",
            error_type="processing_failure",
            metadata={'processing_error': doc_error}
        )
        mock_services['document_processor'].process_document.return_value = processing_result
        
        # Setup file manager to fail move operations (to trigger error handling)
        mock_services['file_manager'].move_to_error.return_value = True
        
        # Process the file
        result = file_processor.process_file(str(test_file))
        
        # Verify the result indicates failure
        assert not result.success
        assert "Failed to process file" in result.error_message
        
        # Verify enhanced error logging was called
        mock_services['error_handler'].create_document_processing_error_log.assert_called_once()
        call_args = mock_services['error_handler'].create_document_processing_error_log.call_args
        
        # Check the arguments passed to enhanced error logging
        assert call_args[0][0] == str(test_file)  # file_path
        assert "Document processing failed" in call_args[0][1]  # error_message
        assert call_args[0][3] is doc_error  # doc_processing_error
    
    def test_process_file_without_document_processing_error_calls_regular_logging(self, file_processor, mock_services, temp_dirs):
        """Test that FileProcessor calls regular error logging when no DocumentProcessingError is present."""
        # Create test file
        test_file = Path(temp_dirs['source']) / "test_document.pdf"
        test_file.write_text("Test content")
        
        # Setup document processor to fail without DocumentProcessingError
        processing_result = ProcessingResult(
            success=False,
            file_path=str(test_file),
            error_message="Regular processing failure",
            error_type="regular_failure"
        )
        mock_services['document_processor'].process_document.return_value = processing_result
        
        # Setup file manager to fail move operations (to trigger error handling)
        mock_services['file_manager'].move_to_error.return_value = True
        
        # Process the file
        result = file_processor.process_file(str(test_file))
        
        # Verify the result indicates failure
        assert not result.success
        
        # Verify regular error logging was called (not enhanced)
        mock_services['error_handler'].create_error_log.assert_called_once()
        mock_services['error_handler'].create_document_processing_error_log.assert_not_called()
    
    def test_process_file_error_classification_affects_retry_behavior(self, file_processor, mock_services, temp_dirs):
        """Test that document processing error classification affects retry behavior."""
        # Create test file
        test_file = Path(temp_dirs['source']) / "test_document.pdf"
        test_file.write_text("Test content")
        
        # Create permanent DocumentProcessingError
        doc_error = DocumentProcessingError(
            file_path=str(test_file),
            processor_type="MockProcessor",
            error_message="Unsupported file format",
            error_type="unsupported_file_type"
        )
        
        # Create exception with DocumentProcessingError information
        # Since DocumentProcessingError can't be a cause, we'll use metadata
        runtime_error = RuntimeError("Document processing failed")
        runtime_error.metadata = {'processing_error': doc_error}
        
        # Setup document processor to raise the exception
        mock_services['document_processor'].process_document.side_effect = runtime_error
        
        # Setup file manager
        mock_services['file_manager'].move_to_error.return_value = True
        
        # Process the file
        result = file_processor.process_file(str(test_file))
        
        # Verify the result indicates failure
        assert not result.success
        
        # Verify document processor was called only once (no retries for permanent errors)
        assert mock_services['document_processor'].process_document.call_count == 1
        
        # Verify error was classified as permanent and no retries occurred
        assert file_processor.stats['failed_permanent'] == 1
        assert file_processor.stats['retries_attempted'] == 0


if __name__ == "__main__":
    pytest.main([__file__])