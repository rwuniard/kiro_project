"""
Integration tests for RAG store component integration.

This module tests the integration between RAGStoreProcessor and existing
RAG store components to ensure proper functionality.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.rag_store_processor import RAGStoreProcessor


class TestRAGStoreIntegration:
    """Test RAG store component integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.processor = RAGStoreProcessor()
    
    def test_processor_registry_integration(self):
        """Test ProcessorRegistry integration."""
        # Test that we can import and use ProcessorRegistry
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.pdf_processor import PDFProcessor
        from src.rag_store.text_processor import TextProcessor
        from src.rag_store.word_processor import WordProcessor
        
        # Create registry and register processors
        registry = ProcessorRegistry()
        registry.register_processor(PDFProcessor())
        registry.register_processor(TextProcessor())
        registry.register_processor(WordProcessor())
        
        # Verify registry functionality
        extensions = registry.get_supported_extensions()
        assert len(extensions) > 0
        assert '.pdf' in extensions
        assert '.txt' in extensions
        assert '.docx' in extensions
        
        processors = registry.get_all_processors()
        assert len(processors) >= 3
        assert 'PDFProcessor' in processors
        assert 'TextProcessor' in processors
        assert 'WordProcessor' in processors
    
    def test_embedding_model_integration(self):
        """Test embedding model integration."""
        from src.rag_store.store_embeddings import ModelVendor, load_embedding_model
        
        # Test that ModelVendor enum works
        assert ModelVendor.GOOGLE.value == "google"
        assert ModelVendor.OPENAI.value == "openai"
        
        # Test that load_embedding_model function exists and can be called
        # (We won't actually call it without API keys)
        assert callable(load_embedding_model)
    
    def test_chroma_db_integration(self):
        """Test ChromaDB integration."""
        from src.rag_store.store_embeddings import ensure_data_directory, ModelVendor
        
        # Test ensure_data_directory function
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the DATA_DIR to use temp directory
            with patch('src.rag_store.store_embeddings.DATA_DIR', Path(temp_dir)):
                google_path = ensure_data_directory(ModelVendor.GOOGLE)
                openai_path = ensure_data_directory(ModelVendor.OPENAI)
                
                assert google_path.exists()
                assert openai_path.exists()
                assert google_path.name == "chroma_db_google"
                assert openai_path.name == "chroma_db_openai"
    
    @patch('src.rag_store.store_embeddings.load_embedding_model')
    @patch('src.rag_store.store_embeddings.ensure_data_directory')
    def test_environment_variable_handling(self, mock_ensure_dir, mock_load_model):
        """Test environment variable loading and validation."""
        mock_ensure_dir.return_value = Path(tempfile.mkdtemp())
        mock_load_model.return_value = Mock()
        
        # Test Google API key handling
        config_google = {
            "model_vendor": "google",
            "google_api_key": "test_google_key"
        }
        
        # Clear existing environment variables
        old_google_key = os.environ.get("GOOGLE_API_KEY")
        old_openai_key = os.environ.get("OPENAI_API_KEY")
        
        try:
            # Remove keys if they exist
            if "GOOGLE_API_KEY" in os.environ:
                del os.environ["GOOGLE_API_KEY"]
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
            
            # Test that initialization sets environment variable
            with patch.object(self.processor, '_initialize_processor_registry'), \
                 patch.object(self.processor, '_initialize_embedding_model'):
                
                result = self.processor.initialize(config_google)
                assert result is True
                assert os.environ.get("GOOGLE_API_KEY") == "test_google_key"
            
            # Test OpenAI API key handling
            config_openai = {
                "model_vendor": "openai",
                "openai_api_key": "test_openai_key"
            }
            
            self.processor = RAGStoreProcessor()  # Reset processor
            with patch.object(self.processor, '_initialize_processor_registry'), \
                 patch.object(self.processor, '_initialize_embedding_model'):
                
                result = self.processor.initialize(config_openai)
                assert result is True
                assert os.environ.get("OPENAI_API_KEY") == "test_openai_key"
        
        finally:
            # Restore original environment variables
            if old_google_key:
                os.environ["GOOGLE_API_KEY"] = old_google_key
            elif "GOOGLE_API_KEY" in os.environ:
                del os.environ["GOOGLE_API_KEY"]
                
            if old_openai_key:
                os.environ["OPENAI_API_KEY"] = old_openai_key
            elif "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_error_handling_integration(self):
        """Test error handling for RAG store initialization failures."""
        # Test missing API key error
        config_no_key = {"model_vendor": "google"}
        
        # Clear environment variable
        old_key = os.environ.get("GOOGLE_API_KEY")
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        
        try:
            with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
                self.processor.initialize(config_no_key)
        finally:
            if old_key:
                os.environ["GOOGLE_API_KEY"] = old_key
        
        # Test invalid model vendor error
        config_invalid = {
            "model_vendor": "invalid",
            "google_api_key": "test_key"
        }
        
        with pytest.raises(ValueError, match="Unsupported model vendor"):
            self.processor.initialize(config_invalid)
    
    @patch('src.core.rag_store_processor.ProcessorRegistry')
    def test_processor_registry_initialization_error(self, mock_registry):
        """Test error handling when ProcessorRegistry initialization fails."""
        mock_registry.side_effect = Exception("Registry initialization failed")
        
        config = {
            "model_vendor": "google",
            "google_api_key": "test_key"
        }
        
        with pytest.raises(Exception, match="Registry initialization failed"):
            self.processor.initialize(config)
        
        assert not self.processor.initialized
    
    @patch('src.core.rag_store_processor.load_embedding_model')
    def test_embedding_model_initialization_error(self, mock_load_model):
        """Test error handling when embedding model initialization fails."""
        mock_load_model.side_effect = Exception("Model loading failed")
        
        config = {
            "model_vendor": "google",
            "google_api_key": "test_key"
        }
        
        with pytest.raises(Exception, match="Model loading failed"):
            self.processor.initialize(config)
        
        assert not self.processor.initialized
    
    def test_chroma_db_path_configuration(self):
        """Test ChromaDB path configuration options."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test custom ChromaDB path
            custom_path = Path(temp_dir) / "custom_chroma"
            config = {
                "model_vendor": "google",
                "google_api_key": "test_key",
                "chroma_db_path": str(custom_path)
            }
            
            with patch.object(self.processor, '_initialize_processor_registry'), \
                 patch.object(self.processor, '_initialize_embedding_model'):
                
                result = self.processor.initialize(config)
                assert result is True
                assert self.processor.chroma_db_path == custom_path
                assert custom_path.exists()
    
    def test_component_cleanup(self):
        """Test proper cleanup of RAG store components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "model_vendor": "google",
                "google_api_key": "test_key",
                "chroma_db_path": str(Path(temp_dir) / "chroma")
            }
            
            # Mock the initialization methods but set the attributes manually
            with patch.object(self.processor, '_initialize_processor_registry') as mock_init_registry, \
                 patch.object(self.processor, '_initialize_embedding_model') as mock_init_model:
                
                # Set up the processor state manually since we're mocking the init methods
                def setup_registry():
                    mock_registry = Mock()
                    mock_registry.get_supported_extensions.return_value = {'.pdf', '.txt'}
                    self.processor.registry = mock_registry
                
                def setup_model():
                    self.processor.embedding_model = Mock()
                
                mock_init_registry.side_effect = setup_registry
                mock_init_model.side_effect = setup_model
                
                # Initialize
                self.processor.initialize(config)
                assert self.processor.initialized is True
                assert self.processor.registry is not None
                assert self.processor.embedding_model is not None
                assert self.processor.chroma_db_path is not None
                
                # Cleanup
                self.processor.cleanup()
                assert self.processor.initialized is False
                assert self.processor.registry is None
                assert self.processor.embedding_model is None
                assert self.processor.chroma_db_path is None


if __name__ == "__main__":
    pytest.main([__file__])