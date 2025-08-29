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

    @patch('src.core.rag_store_processor.RTFProcessor')
    @patch('src.core.rag_store_processor.MHTProcessor')
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.store_to_chroma')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_metadata_path_update_with_file_manager(self, mock_registry, mock_load_model, mock_ensure_dir, mock_store_chroma, mock_pdf, mock_text, mock_word, mock_mht, mock_rtf):
        """Test that metadata is updated with destination path when file manager is provided."""
        # Setup mocks for successful initialization
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Create mock file manager
        mock_file_manager = Mock()
        source_path = "/test/source/Federal Law/IRS/test.pdf"
        dest_path = "/test/saved/Federal Law/IRS/test.pdf"
        mock_file_manager.get_saved_path.return_value = dest_path
        
        # Create processor with file manager
        processor_with_fm = RAGStoreProcessor(file_manager=mock_file_manager)
        processor_with_fm.initialize(self.test_config)
        
        # Create mock documents with metadata
        mock_doc1 = Mock()
        mock_doc1.metadata = {
            'file_path': source_path,
            'source': 'test.pdf',
            'processor': 'PDFProcessor'
        }
        mock_doc2 = Mock()
        mock_doc2.metadata = {
            'file_path': source_path,
            'source': 'test.pdf', 
            'processor': 'PDFProcessor'
        }
        
        mock_documents = [mock_doc1, mock_doc2]
        mock_registry_instance.process_document.return_value = mock_documents
        mock_registry_instance.get_processor_for_file.return_value = Mock(processor_name="PDFProcessor")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            test_file = Path(temp_file.name)
            
            # Process the document
            result = processor_with_fm.process_document(test_file)
            
            # Verify successful processing
            assert result.success is True
            
            # Verify file manager was called with correct path
            mock_file_manager.get_saved_path.assert_called_once_with(str(test_file))
            
            # Verify metadata was updated for all documents
            for doc in mock_documents:
                assert doc.metadata['file_path'] == dest_path, f"Expected destination path, got {doc.metadata['file_path']}"
                assert doc.metadata['source_path'] == str(test_file), f"Expected source path preserved"
            
            # Cleanup
            test_file.unlink()

    @patch('src.core.rag_store_processor.RTFProcessor')
    @patch('src.core.rag_store_processor.MHTProcessor')
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.store_to_chroma')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_metadata_path_update_without_file_manager(self, mock_registry, mock_load_model, mock_ensure_dir, mock_store_chroma, mock_pdf, mock_text, mock_word, mock_mht, mock_rtf):
        """Test that metadata retains original path when no file manager is provided."""
        # Setup mocks for successful initialization  
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Create processor WITHOUT file manager (default constructor)
        processor_no_fm = RAGStoreProcessor()
        processor_no_fm.initialize(self.test_config)
        
        # Create mock documents with metadata
        mock_doc = Mock()
        original_path = "/test/source/Federal Law/IRS/test.pdf"
        mock_doc.metadata = {
            'file_path': original_path,
            'source': 'test.pdf',
            'processor': 'PDFProcessor'
        }
        
        mock_documents = [mock_doc]
        mock_registry_instance.process_document.return_value = mock_documents
        mock_registry_instance.get_processor_for_file.return_value = Mock(processor_name="PDFProcessor")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            test_file = Path(temp_file.name)
            
            # Process the document
            result = processor_no_fm.process_document(test_file)
            
            # Verify successful processing
            assert result.success is True
            
            # Verify metadata was NOT modified (no file manager)
            assert mock_doc.metadata['file_path'] == original_path, "Path should not be modified without file manager"
            assert 'source_path' not in mock_doc.metadata, "source_path should not be added without file manager"
            
            # Cleanup
            test_file.unlink()

    @patch('src.core.rag_store_processor.RTFProcessor')
    @patch('src.core.rag_store_processor.MHTProcessor')
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.store_to_chroma')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_metadata_path_update_file_manager_error(self, mock_registry, mock_load_model, mock_ensure_dir, mock_store_chroma, mock_pdf, mock_text, mock_word, mock_mht, mock_rtf):
        """Test that processing continues when file manager throws an error during path calculation."""
        # Setup mocks for successful initialization
        mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
        
        # Create mock file manager that throws an error
        mock_file_manager = Mock()
        mock_file_manager.get_saved_path.side_effect = Exception("File manager error")
        
        # Create processor with faulty file manager
        processor_with_fm = RAGStoreProcessor(file_manager=mock_file_manager)
        processor_with_fm.initialize(self.test_config)
        
        # Create mock documents
        mock_doc = Mock()
        original_path = "/test/source/Federal Law/IRS/test.pdf"
        mock_doc.metadata = {
            'file_path': original_path,
            'source': 'test.pdf',
            'processor': 'PDFProcessor'
        }
        
        mock_documents = [mock_doc]
        mock_registry_instance.process_document.return_value = mock_documents
        mock_registry_instance.get_processor_for_file.return_value = Mock(processor_name="PDFProcessor")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            test_file = Path(temp_file.name)
            
            # Process the document - should succeed despite file manager error
            result = processor_with_fm.process_document(test_file)
            
            # Verify processing still succeeds
            assert result.success is True
            
            # Verify file manager was called but failed gracefully
            mock_file_manager.get_saved_path.assert_called_once_with(str(test_file))
            
            # Verify metadata was NOT modified due to error (graceful degradation)
            assert mock_doc.metadata['file_path'] == original_path, "Path should remain unchanged after error"
            
            # Cleanup
            test_file.unlink()

    def test_processor_initialization_with_file_manager(self):
        """Test that RAGStoreProcessor can be initialized with a file manager."""
        mock_file_manager = Mock()
        processor = RAGStoreProcessor(file_manager=mock_file_manager)
        
        assert processor.file_manager is mock_file_manager
        assert processor.initialized is False  # Should still require initialize() call

    def test_processor_initialization_without_file_manager(self):
        """Test that RAGStoreProcessor can be initialized without a file manager (backward compatibility)."""
        processor = RAGStoreProcessor()
        
        assert processor.file_manager is None
        assert processor.initialized is False

    def test_rag_store_processor_stores_collection_name_from_config(self):
        """Test RAGStoreProcessor stores ChromaDB collection name during initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "model_vendor": "google",
                "google_api_key": "test_key",
                "chroma_client_mode": "embedded",
                "chroma_db_path": os.path.join(temp_dir, "chroma"),
                "chroma_server_host": "localhost",
                "chroma_server_port": 8000,
                "chroma_collection_name": "my_test_collection"
            }
            
            processor = RAGStoreProcessor()
            
            # Call _setup_chroma_configuration directly
            processor._setup_chroma_configuration(config)
            
            # Verify the collection name is stored in the processor
            assert processor.chroma_collection_name == "my_test_collection"
            assert processor.chroma_client_mode == "embedded"

    def test_rag_store_processor_handles_missing_collection_name(self):
        """Test RAGStoreProcessor handles missing ChromaDB collection name gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "model_vendor": "google",
                "google_api_key": "test_key",
                "chroma_client_mode": "embedded",
                "chroma_db_path": os.path.join(temp_dir, "chroma"),
                "chroma_server_host": "localhost",
                "chroma_server_port": 8000
                # chroma_collection_name not provided
            }
            
            processor = RAGStoreProcessor()
            
            # Call _setup_chroma_configuration directly
            processor._setup_chroma_configuration(config)
            
            # Verify the collection name remains None when not provided
            assert processor.chroma_collection_name is None

    def test_rag_store_processor_client_server_collection_name(self):
        """Test RAGStoreProcessor stores collection name for client-server mode."""
        config = {
            "model_vendor": "google", 
            "google_api_key": "test_key",
            "chroma_client_mode": "client_server",
            "chroma_server_host": "remote-server.com",
            "chroma_server_port": 9000,
            "chroma_collection_name": "client_server_collection"
        }
        
        processor = RAGStoreProcessor()
        
        # Call _setup_chroma_configuration directly
        processor._setup_chroma_configuration(config)
        
        # Verify client-server settings and collection name
        assert processor.chroma_collection_name == "client_server_collection"
        assert processor.chroma_client_mode == "client_server"
        assert processor.chroma_server_host == "remote-server.com"
        assert processor.chroma_server_port == 9000

    @patch('src.core.rag_store_processor.store_to_chroma')
    @patch('src.core.rag_store_processor.RTFProcessor')
    @patch('src.core.rag_store_processor.MHTProcessor')
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_rag_store_processor_process_passes_collection_name(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word, mock_mht, mock_rtf, mock_store_chroma):
        """Test that RAGStoreProcessor passes collection name to store_to_chroma."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "model_vendor": "google",
                "google_api_key": "test_key",
                "chroma_client_mode": "embedded",
                "chroma_db_path": os.path.join(temp_dir, "chroma"),
                "chroma_server_host": "localhost",
                "chroma_server_port": 8000,
                "chroma_collection_name": "my_test_collection"
            }
            
            # Setup mocks for successful initialization
            mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
            
            # Create processor with file_manager
            mock_file_manager = Mock()
            mock_file_manager.get_saved_path.return_value = "/saved/test.txt"
            processor = RAGStoreProcessor(file_manager=mock_file_manager)
            processor.initialize(config)
            
            # Setup processor mock  
            mock_processor = Mock()
            mock_processor.processor_name = "TestProcessor"
            mock_registry_instance.get_processor_for_file.return_value = mock_processor
            mock_registry_instance.process_document.return_value = [Mock(), Mock()]  # 2 documents
            mock_store_chroma.return_value = Mock()
            
            # Create temporary test file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(b"test content")
                test_file = Path(tmp_file.name)
            
            try:
                # Process the document
                result = processor.process_document(test_file)
                
                # Verify store_to_chroma was called with collection name
                mock_store_chroma.assert_called_once()
                call_args, call_kwargs = mock_store_chroma.call_args
                
                # Check that collection_name is in the kwargs
                assert "collection_name" in call_kwargs
                assert call_kwargs["collection_name"] == "my_test_collection"
                
                # Verify successful result
                assert result.success is True
            finally:
                test_file.unlink()

    @patch('src.core.rag_store_processor.store_to_chroma')
    @patch('src.core.rag_store_processor.RTFProcessor')
    @patch('src.core.rag_store_processor.MHTProcessor')
    @patch('src.core.rag_store_processor.WordProcessor')
    @patch('src.core.rag_store_processor.TextProcessor')
    @patch('src.core.rag_store_processor.PDFProcessor')
    @patch('src.core.rag_store_processor.ensure_data_directory')
    @patch('src.core.rag_store_processor.load_embedding_model')
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_rag_store_processor_process_without_collection_name(self, mock_registry, mock_load_model, mock_ensure_dir, mock_pdf, mock_text, mock_word, mock_mht, mock_rtf, mock_store_chroma):
        """Test that RAGStoreProcessor handles missing collection name gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "model_vendor": "google",
                "google_api_key": "test_key",
                "chroma_client_mode": "embedded",
                "chroma_db_path": os.path.join(temp_dir, "chroma"),
                "chroma_server_host": "localhost",
                "chroma_server_port": 8000
                # chroma_collection_name not provided
            }
            
            # Setup mocks for successful initialization
            mock_registry_instance = self._setup_successful_mocks(mock_registry, mock_load_model, mock_ensure_dir)
            
            # Create processor with file_manager
            mock_file_manager = Mock()
            mock_file_manager.get_saved_path.return_value = "/saved/test.txt"
            processor = RAGStoreProcessor(file_manager=mock_file_manager)
            processor.initialize(config)
            
            # Setup processor mock
            mock_processor = Mock()
            mock_processor.processor_name = "TestProcessor"
            mock_registry_instance.get_processor_for_file.return_value = mock_processor
            mock_registry_instance.process_document.return_value = [Mock(), Mock(), Mock()]  # 3 documents
            mock_store_chroma.return_value = Mock()
            
            # Create temporary test file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(b"test content")
                test_file = Path(tmp_file.name)
            
            try:
                # Process the document
                result = processor.process_document(test_file)
                
                # Verify store_to_chroma was called without collection name
                mock_store_chroma.assert_called_once()
                call_args, call_kwargs = mock_store_chroma.call_args
                
                # Check that collection_name is either not present or None
                if "collection_name" in call_kwargs:
                    assert call_kwargs["collection_name"] is None
                
                # Verify successful result
                assert result.success is True
            finally:
                test_file.unlink()


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
