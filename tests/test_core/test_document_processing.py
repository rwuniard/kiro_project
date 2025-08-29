"""
Unit tests for document processing interface and base classes.

Tests the abstract DocumentProcessingInterface, ProcessingResult dataclass,
and DocumentProcessingError dataclass for proper validation and behavior.
"""

import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Set
from unittest.mock import patch, mock_open

from src.core.document_processing import (
    DocumentProcessingInterface,
    ProcessingResult,
    DocumentProcessingError
)


class TestProcessingResult:
    """Test cases for ProcessingResult dataclass."""
    
    def test_processing_result_initialization_with_defaults(self):
        """Test ProcessingResult initialization with default values."""
        result = ProcessingResult(success=True, file_path="/test/file.txt")
        
        assert result.success is True
        assert result.file_path == "/test/file.txt"
        assert result.processor_used is None
        assert result.chunks_created == 0
        assert result.processing_time == 0.0
        assert result.error_message is None
        assert result.error_type is None
        assert result.metadata == {}
    
    def test_processing_result_initialization_with_all_fields(self):
        """Test ProcessingResult initialization with all fields specified."""
        metadata = {"key": "value", "count": 42}
        result = ProcessingResult(
            success=False,
            file_path="/test/error.pdf",
            processor_used="TestProcessor",
            chunks_created=5,
            processing_time=2.5,
            error_message="Processing failed",
            error_type="validation_error",
            metadata=metadata
        )
        
        assert result.success is False
        assert result.file_path == "/test/error.pdf"
        assert result.processor_used == "TestProcessor"
        assert result.chunks_created == 5
        assert result.processing_time == 2.5
        assert result.error_message == "Processing failed"
        assert result.error_type == "validation_error"
        assert result.metadata == metadata
    
    def test_processing_result_metadata_none_initialization(self):
        """Test ProcessingResult handles None metadata properly."""
        result = ProcessingResult(success=True, file_path="/test/file.txt", metadata=None)
        
        assert result.metadata == {}
    
    def test_processing_result_metadata_modification(self):
        """Test ProcessingResult metadata can be modified after creation."""
        result = ProcessingResult(success=True, file_path="/test/file.txt")
        result.metadata["new_key"] = "new_value"
        
        assert result.metadata["new_key"] == "new_value"


class TestDocumentProcessingError:
    """Test cases for DocumentProcessingError dataclass."""
    
    def test_document_processing_error_initialization_with_required_fields(self):
        """Test DocumentProcessingError initialization with required fields only."""
        error = DocumentProcessingError(
            file_path="/test/error.txt",
            processor_type="TestProcessor",
            error_message="Test error message",
            error_type="test_error"
        )
        
        assert error.file_path == "/test/error.txt"
        assert error.processor_type == "TestProcessor"
        assert error.error_message == "Test error message"
        assert error.error_type == "test_error"
        assert isinstance(error.timestamp, datetime)
        assert error.stack_trace is None
        assert error.file_metadata == {}
        assert error.processing_context == {}
    
    def test_document_processing_error_initialization_with_all_fields(self):
        """Test DocumentProcessingError initialization with all fields specified."""
        timestamp = datetime.now()
        file_metadata = {"size": 1024, "type": "pdf"}
        processing_context = {"chunks_attempted": 3, "model": "test-model"}
        
        error = DocumentProcessingError(
            file_path="/test/error.pdf",
            processor_type="RAGProcessor",
            error_message="Embedding generation failed",
            error_type="embedding_error",
            timestamp=timestamp,
            stack_trace="Traceback...",
            file_metadata=file_metadata,
            processing_context=processing_context
        )
        
        assert error.file_path == "/test/error.pdf"
        assert error.processor_type == "RAGProcessor"
        assert error.error_message == "Embedding generation failed"
        assert error.error_type == "embedding_error"
        assert error.timestamp == timestamp
        assert error.stack_trace == "Traceback..."
        assert error.file_metadata == file_metadata
        assert error.processing_context == processing_context
    
    def test_document_processing_error_none_dictionaries_initialization(self):
        """Test DocumentProcessingError handles None dictionaries properly."""
        error = DocumentProcessingError(
            file_path="/test/error.txt",
            processor_type="TestProcessor",
            error_message="Test error",
            error_type="test_error",
            file_metadata=None,
            processing_context=None
        )
        
        assert error.file_metadata == {}
        assert error.processing_context == {}
    
    def test_document_processing_error_timestamp_auto_generation(self):
        """Test DocumentProcessingError automatically generates timestamp."""
        before = datetime.now()
        error = DocumentProcessingError(
            file_path="/test/error.txt",
            processor_type="TestProcessor",
            error_message="Test error",
            error_type="test_error"
        )
        after = datetime.now()
        
        assert before <= error.timestamp <= after


class MockDocumentProcessor(DocumentProcessingInterface):
    """Mock implementation of DocumentProcessingInterface for testing."""
    
    def __init__(self):
        self.initialized = False
        self.supported_extensions = {'.txt', '.pdf', '.docx'}
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        self.initialized = True
        return True
    
    def is_supported_file(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions
    
    def process_document(self, file_path: Path) -> ProcessingResult:
        if not self.initialized:
            raise RuntimeError("Processor not initialized")
        
        return ProcessingResult(
            success=True,
            file_path=str(file_path),
            processor_used="MockDocumentProcessor",
            chunks_created=1,
            processing_time=0.1
        )
    
    def get_supported_extensions(self) -> Set[str]:
        return self.supported_extensions.copy()
    
    def cleanup(self) -> None:
        self.initialized = False


class TestDocumentProcessingInterface:
    """Test cases for DocumentProcessingInterface abstract class."""
    
    def test_cannot_instantiate_abstract_interface(self):
        """Test that DocumentProcessingInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DocumentProcessingInterface()
    
    def test_mock_processor_implementation(self):
        """Test that mock processor correctly implements the interface."""
        processor = MockDocumentProcessor()
        
        # Test initialization
        assert not processor.initialized
        result = processor.initialize({"test": "config"})
        assert result is True
        assert processor.initialized
        
        # Test supported extensions
        extensions = processor.get_supported_extensions()
        assert extensions == {'.txt', '.pdf', '.docx'}
        
        # Test file support checking
        assert processor.is_supported_file(Path("test.txt"))
        assert processor.is_supported_file(Path("test.PDF"))  # Case insensitive
        assert not processor.is_supported_file(Path("test.jpg"))
        
        # Test processor name
        assert processor.get_processor_name() == "MockDocumentProcessor"
        
        # Test cleanup
        processor.cleanup()
        assert not processor.initialized
    
    def test_mock_processor_document_processing(self):
        """Test document processing functionality of mock processor."""
        processor = MockDocumentProcessor()
        processor.initialize({})
        
        file_path = Path("test.txt")
        result = processor.process_document(file_path)
        
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.file_path == str(file_path)
        assert result.processor_used == "MockDocumentProcessor"
        assert result.chunks_created == 1
        assert result.processing_time == 0.1
    
    def test_mock_processor_uninitialized_processing(self):
        """Test that uninitialized processor raises error on processing."""
        processor = MockDocumentProcessor()
        
        with pytest.raises(RuntimeError, match="Processor not initialized"):
            processor.process_document(Path("test.txt"))
    
    @patch("builtins.open", mock_open(read_data="test content"))
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    def test_validate_file_path_success(self, mock_is_file, mock_exists):
        """Test successful file path validation."""
        processor = MockDocumentProcessor()
        file_path = Path("test.txt")
        
        # Should not raise any exception
        processor.validate_file_path(file_path)
    
    @patch("pathlib.Path.exists", return_value=False)
    def test_validate_file_path_not_found(self, mock_exists):
        """Test file path validation with non-existent file."""
        processor = MockDocumentProcessor()
        file_path = Path("nonexistent.txt")
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            processor.validate_file_path(file_path)
    
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=False)
    def test_validate_file_path_not_file(self, mock_is_file, mock_exists):
        """Test file path validation with directory instead of file."""
        processor = MockDocumentProcessor()
        file_path = Path("directory")
        
        with pytest.raises(ValueError, match="Path is not a file"):
            processor.validate_file_path(file_path)
    
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("builtins.open", side_effect=PermissionError("Access denied"))
    def test_validate_file_path_permission_error(self, mock_open, mock_is_file, mock_exists):
        """Test file path validation with permission error."""
        processor = MockDocumentProcessor()
        file_path = Path("restricted.txt")
        
        with pytest.raises(PermissionError, match="Cannot access file"):
            processor.validate_file_path(file_path)


class TestInterfaceCompliance:
    """Test cases for ensuring interface compliance."""
    
    def test_mock_processor_has_all_required_methods(self):
        """Test that mock processor implements all required abstract methods."""
        processor = MockDocumentProcessor()
        
        # Check that all abstract methods are implemented
        assert hasattr(processor, 'initialize')
        assert hasattr(processor, 'is_supported_file')
        assert hasattr(processor, 'process_document')
        assert hasattr(processor, 'get_supported_extensions')
        assert hasattr(processor, 'cleanup')
        
        # Check that methods are callable
        assert callable(processor.initialize)
        assert callable(processor.is_supported_file)
        assert callable(processor.process_document)
        assert callable(processor.get_supported_extensions)
        assert callable(processor.cleanup)
    
    def test_processing_result_type_validation(self):
        """Test ProcessingResult with various data types."""
        # Test with string file path
        result1 = ProcessingResult(success=True, file_path="string_path.txt")
        assert result1.file_path == "string_path.txt"
        
        # Test with Path object converted to string
        result2 = ProcessingResult(success=True, file_path=str(Path("path_object.txt")))
        assert result2.file_path == str(Path("path_object.txt"))
        
        # Test with integer values
        result3 = ProcessingResult(
            success=True, 
            file_path="test.txt", 
            chunks_created=100,
            processing_time=5.5
        )
        assert result3.chunks_created == 100
        assert result3.processing_time == 5.5
    
    def test_document_processing_error_immutability_of_required_fields(self):
        """Test that required fields of DocumentProcessingError maintain their values."""
        error = DocumentProcessingError(
            file_path="/original/path.txt",
            processor_type="OriginalProcessor",
            error_message="Original message",
            error_type="original_error"
        )
        
        # Verify original values
        assert error.file_path == "/original/path.txt"
        assert error.processor_type == "OriginalProcessor"
        assert error.error_message == "Original message"
        assert error.error_type == "original_error"
        
        # Modify values (dataclasses are mutable by default)
        error.file_path = "/modified/path.txt"
        error.processor_type = "ModifiedProcessor"
        
        # Verify modifications took effect
        assert error.file_path == "/modified/path.txt"
        assert error.processor_type == "ModifiedProcessor"