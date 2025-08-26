"""
Unit tests for document processing workflow and ChromaDB integration.

This module tests the complete document processing workflow from file input
to ChromaDB storage, including error handling and edge cases.
"""

import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.core.rag_store_processor import RAGStoreProcessor
from src.core.document_processing import ProcessingResult


class TestDocumentProcessingWorkflow:
    """Test document processing workflow."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.processor = RAGStoreProcessor()
        self.test_config = {
            "model_vendor": "google",
            "google_api_key": "test_api_key"
        }
    
    def _initialize_processor_with_mocks(self):
        """Helper to initialize processor with mocked components."""
        with patch('src.core.rag_store_processor.ProcessorRegistry') as mock_registry_class, \
             patch('src.core.rag_store_processor.load_embedding_model') as mock_load_model, \
             patch('src.core.rag_store_processor.ensure_data_directory') as mock_ensure_dir, \
             patch('src.core.rag_store_processor.PDFProcessor'), \
             patch('src.core.rag_store_processor.TextProcessor'), \
             patch('src.core.rag_store_processor.WordProcessor'):
            
            # Setup mocks
            mock_registry = Mock()
            mock_registry.get_all_processors.return_value = {"PDFProcessor": Mock()}
            mock_registry.get_supported_extensions.return_value = {'.pdf', '.txt', '.docx'}
            mock_registry_class.return_value = mock_registry
            
            mock_load_model.return_value = Mock()
            mock_ensure_dir.return_value = Path(tempfile.mkdtemp()) / "chroma"
            
            # Initialize processor
            self.processor.initialize(self.test_config)
            return mock_registry
    
    def test_successful_document_processing_workflow(self):
        """Test complete successful document processing workflow."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test PDF content")
            test_file = Path(tmp_file.name)
        
        try:
            # Setup mocks for successful processing
            mock_processor = Mock()
            mock_processor.processor_name = "PDFProcessor"
            mock_registry.get_processor_for_file.return_value = mock_processor
            
            # Mock document objects
            mock_doc1 = Mock()
            mock_doc1.page_content = "First chunk content"
            mock_doc1.metadata = {"page": 1, "source": "test.pdf"}
            
            mock_doc2 = Mock()
            mock_doc2.page_content = "Second chunk content"
            mock_doc2.metadata = {"page": 2, "source": "test.pdf"}
            
            mock_registry.process_document.return_value = [mock_doc1, mock_doc2]
            
            # Mock ChromaDB storage
            with patch('src.core.rag_store_processor.store_to_chroma') as mock_store:
                mock_vectorstore = Mock()
                mock_store.return_value = mock_vectorstore
                
                # Process document
                result = self.processor.process_document(test_file)
                
                # Verify result
                assert result.success is True
                assert result.file_path == str(test_file)
                assert result.processor_used == "RAGStoreProcessor"
                assert result.chunks_created == 2
                assert result.processing_time > 0
                
                # Verify metadata
                assert "model_vendor" in result.metadata
                assert "chroma_db_path" in result.metadata
                assert "document_processor" in result.metadata
                assert "file_size" in result.metadata
                assert "file_extension" in result.metadata
                
                assert result.metadata["model_vendor"] == "google"
                assert result.metadata["document_processor"] == "PDFProcessor"
                assert result.metadata["file_extension"] == ".pdf"
                
                # Verify mocks were called correctly
                # get_processor_for_file is called twice: once in is_supported_file, once in process_document
                assert mock_registry.get_processor_for_file.call_count == 2
                mock_registry.process_document.assert_called_once_with(test_file)
                mock_store.assert_called_once_with([mock_doc1, mock_doc2], self.processor.model_vendor)
        
        finally:
            test_file.unlink()
    
    def test_unsupported_file_type_workflow(self):
        """Test workflow with unsupported file type."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Create test file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as tmp_file:
            tmp_file.write(b"unsupported content")
            test_file = Path(tmp_file.name)
        
        try:
            # Setup mocks for unsupported file
            mock_registry.get_processor_for_file.return_value = None
            mock_registry.get_supported_extensions.return_value = {'.pdf', '.txt', '.docx'}
            
            # Process document
            result = self.processor.process_document(test_file)
            
            # Verify result
            assert result.success is False
            assert result.error_type == "unsupported_file_type"
            assert ".xyz" in result.error_message
            assert result.chunks_created == 0
            assert result.processing_time > 0
            
            # Verify metadata contains supported extensions
            assert "supported_extensions" in result.metadata
            # Convert to set for comparison since order doesn't matter
            assert set(result.metadata["supported_extensions"]) == {'.pdf', '.txt', '.docx'}
        
        finally:
            test_file.unlink()
    
    def test_empty_document_workflow(self):
        """Test workflow with document that produces no content."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"empty PDF")
            test_file = Path(tmp_file.name)
        
        try:
            # Setup mocks for empty document processing
            mock_processor = Mock()
            mock_processor.processor_name = "PDFProcessor"
            mock_registry.get_processor_for_file.return_value = mock_processor
            mock_registry.process_document.return_value = []  # Empty list
            
            # Process document
            result = self.processor.process_document(test_file)
            
            # Verify result
            assert result.success is False
            assert result.error_type == "empty_document"
            assert "No content extracted" in result.error_message
            assert result.chunks_created == 0
            assert result.processing_time > 0
            
            # Verify metadata
            assert "file_size" in result.metadata
            assert result.metadata["file_size"] > 0
        
        finally:
            test_file.unlink()
    
    def test_document_processing_failure_workflow(self):
        """Test workflow when document processing fails."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"corrupted PDF")
            test_file = Path(tmp_file.name)
        
        try:
            # Setup mocks for processing failure
            mock_processor = Mock()
            mock_processor.processor_name = "PDFProcessor"
            mock_registry.get_processor_for_file.return_value = mock_processor
            mock_registry.process_document.side_effect = Exception("PDF parsing failed")
            
            # Process document
            result = self.processor.process_document(test_file)
            
            # Verify result
            assert result.success is False
            assert result.error_type == "Exception"
            assert "PDF parsing failed" in result.error_message
            assert result.chunks_created == 0
            assert result.processing_time > 0
            
            # Verify processing error metadata
            assert "processing_error" in result.metadata
            processing_error = result.metadata["processing_error"]
            assert processing_error.file_path == str(test_file)
            assert processing_error.processor_type == "RAGStoreProcessor"
            assert processing_error.error_message == "PDF parsing failed"
            assert processing_error.error_type == "Exception"
        
        finally:
            test_file.unlink()
    
    def test_chroma_db_storage_failure_workflow(self):
        """Test workflow when ChromaDB storage fails."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test PDF content")
            test_file = Path(tmp_file.name)
        
        try:
            # Setup mocks for successful document processing but ChromaDB failure
            mock_processor = Mock()
            mock_processor.processor_name = "PDFProcessor"
            mock_registry.get_processor_for_file.return_value = mock_processor
            
            mock_doc = Mock()
            mock_doc.page_content = "Test content"
            mock_doc.metadata = {"page": 1}
            mock_registry.process_document.return_value = [mock_doc]
            
            # Mock ChromaDB storage failure
            with patch('src.core.rag_store_processor.store_to_chroma') as mock_store:
                mock_store.side_effect = Exception("ChromaDB connection failed")
                
                # Process document
                result = self.processor.process_document(test_file)
                
                # Verify result
                assert result.success is False
                assert result.error_type == "Exception"
                assert "ChromaDB connection failed" in result.error_message
                assert result.processing_time > 0
                
                # Verify that document processing was attempted
                mock_registry.process_document.assert_called_once_with(test_file)
                mock_store.assert_called_once()
        
        finally:
            test_file.unlink()
    
    def test_file_validation_workflow(self):
        """Test workflow with invalid file paths."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Test with non-existent file
        non_existent_file = Path("non_existent_file.pdf")
        result = self.processor.process_document(non_existent_file)
        
        assert result.success is False
        assert result.error_type == "FileNotFoundError"
        assert "not found" in result.error_message.lower()
        
        # Test with directory instead of file
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)
            result = self.processor.process_document(dir_path)
            
            assert result.success is False
            assert result.error_type == "ValueError"
            assert "not a file" in result.error_message.lower()
    
    def test_different_file_types_workflow(self):
        """Test workflow with different supported file types."""
        mock_registry = self._initialize_processor_with_mocks()
        
        file_types = [
            ('.pdf', 'PDFProcessor', b'PDF content'),
            ('.txt', 'TextProcessor', b'Text content'),
            ('.docx', 'WordProcessor', b'Word content')
        ]
        
        for extension, processor_name, content in file_types:
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp_file:
                tmp_file.write(content)
                test_file = Path(tmp_file.name)
            
            try:
                # Setup mocks for this file type
                mock_processor = Mock()
                mock_processor.processor_name = processor_name
                mock_registry.get_processor_for_file.return_value = mock_processor
                
                mock_doc = Mock()
                mock_doc.page_content = f"Content from {extension} file"
                mock_doc.metadata = {"source": test_file.name}
                mock_registry.process_document.return_value = [mock_doc]
                
                with patch('src.core.rag_store_processor.store_to_chroma') as mock_store:
                    mock_store.return_value = Mock()
                    
                    # Process document
                    result = self.processor.process_document(test_file)
                    
                    # Verify result
                    assert result.success is True
                    assert result.chunks_created == 1
                    assert result.metadata["document_processor"] == processor_name
                    assert result.metadata["file_extension"] == extension
            
            finally:
                test_file.unlink()
    
    def test_large_document_workflow(self):
        """Test workflow with document that produces many chunks."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"large PDF content" * 1000)  # Simulate large file
            test_file = Path(tmp_file.name)
        
        try:
            # Setup mocks for large document processing
            mock_processor = Mock()
            mock_processor.processor_name = "PDFProcessor"
            mock_registry.get_processor_for_file.return_value = mock_processor
            
            # Create many mock documents (chunks)
            mock_docs = []
            for i in range(50):  # 50 chunks
                mock_doc = Mock()
                mock_doc.page_content = f"Chunk {i} content"
                mock_doc.metadata = {"page": i // 5 + 1, "chunk": i}
                mock_docs.append(mock_doc)
            
            mock_registry.process_document.return_value = mock_docs
            
            with patch('src.core.rag_store_processor.store_to_chroma') as mock_store:
                mock_store.return_value = Mock()
                
                # Process document
                result = self.processor.process_document(test_file)
                
                # Verify result
                assert result.success is True
                assert result.chunks_created == 50
                assert result.processing_time > 0
                
                # Verify ChromaDB was called with all chunks
                mock_store.assert_called_once_with(mock_docs, self.processor.model_vendor)
        
        finally:
            test_file.unlink()
    
    def test_metadata_enrichment_workflow(self):
        """Test that processing result metadata is properly enriched."""
        mock_registry = self._initialize_processor_with_mocks()
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(b"test content for metadata")
            test_file = Path(tmp_file.name)
        
        try:
            # Setup mocks
            mock_processor = Mock()
            mock_processor.processor_name = "PDFProcessor"
            mock_registry.get_processor_for_file.return_value = mock_processor
            
            mock_doc = Mock()
            mock_registry.process_document.return_value = [mock_doc]
            
            with patch('src.core.rag_store_processor.store_to_chroma') as mock_store:
                mock_store.return_value = Mock()
                
                # Process document
                result = self.processor.process_document(test_file)
                
                # Verify all expected metadata fields
                expected_fields = [
                    "model_vendor", "chroma_db_path", "document_processor",
                    "file_size", "file_extension"
                ]
                
                for field in expected_fields:
                    assert field in result.metadata, f"Missing metadata field: {field}"
                
                # Verify metadata values
                assert result.metadata["model_vendor"] == "google"
                assert result.metadata["document_processor"] == "PDFProcessor"
                assert result.metadata["file_extension"] == ".pdf"
                assert result.metadata["file_size"] > 0
                assert isinstance(result.metadata["chroma_db_path"], str)
        
        finally:
            test_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__])