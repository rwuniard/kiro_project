"""
Unit tests for RAGStoreProcessor class and interface compliance.

This module tests the RAGStoreProcessor implementation of DocumentProcessingInterface
to ensure proper functionality and interface compliance.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.core.document_processing import (
    DocumentProcessingInterface,
    ProcessingResult,
    DocumentProcessingError
)
from src.core.rag_store_processor import RAGStoreProcessor


class TestRAGStoreProcessor:
    """Test cases for RAGStoreProcessor class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.processor = RAGStoreProcessor()
        self.test_config = {
            "model_vendor": "google",
            "google_api_key": "test_api_key"
        }
    
    def test_implements_document_processing_interface(self):
        """Test that RAGStoreProcessor implements DocumentProcessingInterface."""
        assert isinstance(self.processor, DocumentProcessingInterface)
        
        # Check that all required methods are implemented
        required_methods = [
            'initialize', 'is_supported_file', 'process_document',
            'get_supported_extensions', 'cleanup'
        ]
        
        for method_name in required_methods:
            assert hasattr(self.processor, method_name)
            assert callable(getattr(self.processor, method_name))
    
    def test_initial_state(self):
        """Test initial state of RAGStoreProcessor."""
        assert self.processor.registry is None
        assert self.processor.embedding_model is None
        assert self.processor.chroma_db_path is None
        assert self.processor.initialized is False
        assert self.processor.get_processor_name() == "RAGStoreProcessor"
    
    def _setup_successful_mocks(self, mock_registry, mock_load_model, mock_ensure_dir):
        """Helper to setup successful initialization mocks."""
        mock_registry_instance = Mock()
        mock_registry_instance.get_all_processors.return_value = {"PDFProcessor": Mock(), "TextProcessor": Mock()}
        mock_registry_instance.get_supported_extensions.return_value = {'.pdf', '.txt'}
        mock_registry.return_value = mock_registry_instance
        mock_load_model.return_value = Mock()
        
        # Use a temporary directory that can be created
        import tempfile
        temp_dir = tempfile.mkdtemp()
        mock_ensure_dir.return_value = Path(temp_dir) / "chroma"
        return mock_registry_instance
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_initialize_success_google(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test successful initialization with Google model vendor."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Test initialization
        result = self.processor.initialize(self.test_config)
        
        assert result is True
        assert self.processor.initialized is True
        assert self.processor.model_vendor.value == "google"
        assert self.processor.registry == mock_registry_instance
        
        # Verify mocks were called
        mock_registry.assert_called_once()
        mock_load_model.assert_called_once()
        mock_ensure_dir.assert_called_once()
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_initialize_success_openai(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test successful initialization with OpenAI model vendor."""
        config = {
            "model_vendor": "openai",
            "openai_api_key": "test_openai_key"
        }
        
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Test initialization
        result = self.processor.initialize(config)
        
        assert result is True
        assert self.processor.initialized is True
        assert self.processor.model_vendor.value == "openai"
    
    def test_initialize_missing_api_key_google(self):
        """Test initialization failure with missing Google API key."""
        config = {"model_vendor": "google"}
        
        # Clear any existing environment variable
        old_key = os.environ.get("GOOGLE_API_KEY")
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        
        try:
            with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
                self.processor.initialize(config)
            
            assert self.processor.initialized is False
        finally:
            # Restore environment variable if it existed
            if old_key:
                os.environ["GOOGLE_API_KEY"] = old_key
    
    def test_initialize_missing_api_key_openai(self):
        """Test initialization failure with missing OpenAI API key."""
        config = {"model_vendor": "openai"}
        
        # Clear any existing environment variable
        old_key = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        try:
            with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
                self.processor.initialize(config)
            
            assert self.processor.initialized is False
        finally:
            # Restore environment variable if it existed
            if old_key:
                os.environ["OPENAI_API_KEY"] = old_key
    
    def test_initialize_invalid_model_vendor(self):
        """Test initialization failure with invalid model vendor."""
        config = {
            "model_vendor": "invalid_vendor",
            "google_api_key": "test_key"
        }
        
        with pytest.raises(ValueError, match="Unsupported model vendor"):
            self.processor.initialize(config)
        
        assert self.processor.initialized is False
    
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_initialize_registry_failure(self, mock_registry):
        """Test initialization failure when registry setup fails."""
        mock_registry.side_effect = Exception("Registry setup failed")
        
        with pytest.raises(Exception, match="Registry setup failed"):
            self.processor.initialize(self.test_config)
        
        assert self.processor.initialized is False
    
    def test_is_supported_file_not_initialized(self):
        """Test is_supported_file returns False when not initialized."""
        test_file = Path("test.pdf")
        result = self.processor.is_supported_file(test_file)
        assert result is False
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_is_supported_file_initialized(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test is_supported_file when initialized."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Initialize processor
        self.processor.initialize(self.test_config)
        
        # Test supported file
        test_file = Path("test.pdf")
        mock_registry_instance.get_processor_for_file.return_value = Mock()
        result = self.processor.is_supported_file(test_file)
        assert result is True
        
        # Test unsupported file
        mock_registry_instance.get_processor_for_file.return_value = None
        result = self.processor.is_supported_file(test_file)
        assert result is False
    
    def test_process_document_not_initialized(self):
        """Test process_document returns error result when not initialized."""
        test_file = Path("test.pdf")
        
        result = self.processor.process_document(test_file)
        
        assert result.success is False
        assert result.processor_used == "RAGStoreProcessor"
        assert "not initialized" in result.error_message
        assert result.error_type == "initialization_error"
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_process_document_unsupported_file(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test process_document with unsupported file type."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        mock_registry_instance.get_processor_for_file.return_value = None
        mock_registry_instance.get_supported_extensions.return_value = {'.pdf', '.txt'}
        
        # Initialize processor
        self.processor.initialize(self.test_config)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            test_file = Path(tmp_file.name)
        
        try:
            result = self.processor.process_document(test_file)
            
            assert result.success is False
            assert result.error_type == "unsupported_file_type"
            assert ".xyz" in result.error_message
            assert result.processor_used == "RAGStoreProcessor"
        finally:
            test_file.unlink()
    
    @patch('src.core.rag_store_processor.store_to_chroma')
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_process_document_success(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word, mock_store_chroma):
        """Test successful document processing."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Setup processor mock
        mock_processor = Mock()
        mock_processor.processor_name = "TestProcessor"
        mock_registry_instance.get_processor_for_file.return_value = mock_processor
        mock_registry_instance.process_document.return_value = [Mock(), Mock()]  # 2 documents
        mock_store_chroma.return_value = Mock()
        
        # Initialize processor
        self.processor.initialize(self.test_config)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            test_file = Path(tmp_file.name)
        
        try:
            result = self.processor.process_document(test_file)
            
            assert result.success is True
            assert result.chunks_created == 2
            assert result.processor_used == "RAGStoreProcessor"
            assert result.processing_time > 0
            assert "model_vendor" in result.metadata
            assert "chroma_db_path" in result.metadata
            assert "document_processor" in result.metadata
            
            # Verify mocks were called
            mock_registry_instance.process_document.assert_called_once_with(test_file)
            mock_store_chroma.assert_called_once()
        finally:
            test_file.unlink()
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_process_document_empty_document(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test process_document with empty document (no content extracted)."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Setup processor mock
        mock_processor = Mock()
        mock_registry_instance.get_processor_for_file.return_value = mock_processor
        mock_registry_instance.process_document.return_value = []  # Empty list
        
        # Initialize processor
        self.processor.initialize(self.test_config)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            test_file = Path(tmp_file.name)
        
        try:
            result = self.processor.process_document(test_file)
            
            assert result.success is False
            assert result.error_type == "empty_document"
            assert "No content extracted" in result.error_message
            assert result.chunks_created == 0
        finally:
            test_file.unlink()
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_process_document_processing_failure(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test process_document with processing failure."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Setup processor mock
        mock_processor = Mock()
        mock_registry_instance.get_processor_for_file.return_value = mock_processor
        mock_registry_instance.process_document.side_effect = Exception("Processing failed")
        
        # Initialize processor
        self.processor.initialize(self.test_config)
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            test_file = Path(tmp_file.name)
        
        try:
            result = self.processor.process_document(test_file)
            
            assert result.success is False
            assert result.error_type == "Exception"
            assert "Processing failed" in result.error_message
            assert result.processing_time > 0
            assert "processing_error" in result.metadata
        finally:
            test_file.unlink()
    
    def test_get_supported_extensions_not_initialized(self):
        """Test get_supported_extensions returns empty set when not initialized."""
        result = self.processor.get_supported_extensions()
        assert result == set()
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_get_supported_extensions_initialized(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test get_supported_extensions when initialized."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        mock_registry_instance.get_supported_extensions.return_value = {'.pdf', '.txt', '.docx'}
        
        # Initialize processor
        self.processor.initialize(self.test_config)
        
        result = self.processor.get_supported_extensions()
        assert result == {'.pdf', '.txt', '.docx'}
    
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_cleanup(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word):
        """Test cleanup method."""
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        self.processor.initialize(self.test_config)
        assert self.processor.initialized is True
        
        # Test cleanup
        self.processor.cleanup()
        
        assert self.processor.registry is None
        assert self.processor.embedding_model is None
        assert self.processor.chroma_db_path is None
        assert self.processor.initialized is False
    
    def test_processor_name(self):
        """Test get_processor_name method."""
        assert self.processor.get_processor_name() == "RAGStoreProcessor"


class TestRAGStoreProcessorIntegration:
    """Integration tests for RAGStoreProcessor with real components."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.processor = RAGStoreProcessor()
    
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="GOOGLE_API_KEY not available for integration test"
    )
    def test_real_initialization_google(self):
        """Test real initialization with Google API (requires API key)."""
        config = {
            "model_vendor": "google",
            "google_api_key": os.getenv("GOOGLE_API_KEY")
        }
        
        try:
            result = self.processor.initialize(config)
            assert result is True
            assert self.processor.initialized is True
            
            # Test supported extensions
            extensions = self.processor.get_supported_extensions()
            assert len(extensions) > 0
            assert '.pdf' in extensions or '.txt' in extensions
            
        finally:
            self.processor.cleanup()
    
    def test_file_validation(self):
        """Test file validation functionality."""
        # Test with non-existent file
        non_existent = Path("non_existent_file.pdf")
        
        with pytest.raises(FileNotFoundError):
            self.processor.validate_file_path(non_existent)
        
        # Test with directory instead of file
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            
            with pytest.raises(ValueError, match="Path is not a file"):
                self.processor.validate_file_path(dir_path)


if __name__ == "__main__":
    pytest.main([__file__])