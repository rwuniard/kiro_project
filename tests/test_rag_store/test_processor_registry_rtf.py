"""
Tests for ProcessorRegistry RTF Integration

This module tests the ProcessorRegistry's smart routing functionality
for RTF files and .doc files that contain RTF content.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestProcessorRegistryRTF(unittest.TestCase):
    """Test cases for ProcessorRegistry RTF integration."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def create_rtf_file(self, filename: str) -> Path:
        """Create a test RTF file."""
        content = r"""{\rtf1\ansi\deff0 
{\fonttbl {\f0 Times New Roman;}}
\f0\fs24 This is a test RTF document.
}"""
        file_path = self.temp_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def create_doc_with_rtf_content(self, filename: str) -> Path:
        """Create a .doc file with RTF content."""
        content = r"""{\rtf1\ansi\deff0 
{\fonttbl {\f0 Arial;}}
\f0\fs20 RTF content with .doc extension.
}"""
        file_path = self.temp_path / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def create_real_doc_file(self, filename: str) -> Path:
        """Create a mock real DOC file with OLE2 signature."""
        ole2_signature = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
        content = ole2_signature + b'\x00' * 100 + b'Microsoft Office Word' + b'\x00' * 1000
        
        file_path = self.temp_path / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.word_processor.UnstructuredLoader')  
    def test_processor_registration(self, mock_word_loader, mock_rtf_loader):
        """Test that RTF processor is properly registered."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.rtf_processor import RTFProcessor
        from src.rag_store.word_processor import WordProcessor
        
        registry = ProcessorRegistry()
        
        # Register processors
        rtf_processor = RTFProcessor()
        word_processor = WordProcessor()
        
        registry.register_processor(rtf_processor)
        registry.register_processor(word_processor)
        
        # Check that both processors are registered
        all_processors = registry.get_all_processors()
        self.assertIn('RTFProcessor', all_processors)
        self.assertIn('WordProcessor', all_processors)
        
        # Check supported extensions
        supported_extensions = registry.get_supported_extensions()
        self.assertIn('.rtf', supported_extensions)
        self.assertIn('.doc', supported_extensions)
        self.assertIn('.docx', supported_extensions)

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.word_processor.UnstructuredLoader')
    def test_rtf_file_routing(self, mock_word_loader, mock_rtf_loader):
        """Test that .rtf files are routed to RTF processor."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.rtf_processor import RTFProcessor
        from src.rag_store.word_processor import WordProcessor
        
        registry = ProcessorRegistry()
        
        rtf_processor = RTFProcessor()
        word_processor = WordProcessor()
        
        registry.register_processor(rtf_processor)
        registry.register_processor(word_processor)
        
        # Create RTF file and test routing
        rtf_file = self.create_rtf_file("test.rtf")
        processor = registry.get_processor_for_file(rtf_file)
        
        self.assertIsInstance(processor, RTFProcessor)

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.word_processor.UnstructuredLoader')
    def test_doc_with_rtf_content_routing(self, mock_word_loader, mock_rtf_loader):
        """Test that .doc files with RTF content are routed to RTF processor."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.rtf_processor import RTFProcessor
        from src.rag_store.word_processor import WordProcessor
        
        registry = ProcessorRegistry()
        
        rtf_processor = RTFProcessor()
        word_processor = WordProcessor()
        
        registry.register_processor(rtf_processor)
        registry.register_processor(word_processor)
        
        # Create .doc file with RTF content
        rtf_as_doc = self.create_doc_with_rtf_content("test.doc")
        processor = registry.get_processor_for_file(rtf_as_doc)
        
        self.assertIsInstance(processor, RTFProcessor)

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.word_processor.UnstructuredLoader')
    def test_real_doc_file_routing(self, mock_word_loader, mock_rtf_loader):
        """Test that real .doc files are routed to Word processor."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.rtf_processor import RTFProcessor
        from src.rag_store.word_processor import WordProcessor
        
        registry = ProcessorRegistry()
        
        rtf_processor = RTFProcessor()
        word_processor = WordProcessor()
        
        registry.register_processor(rtf_processor)
        registry.register_processor(word_processor)
        
        # Create real DOC file
        doc_file = self.create_real_doc_file("test.doc")
        processor = registry.get_processor_for_file(doc_file)
        
        self.assertIsInstance(processor, WordProcessor)

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.word_processor.UnstructuredLoader')
    def test_docx_file_routing(self, mock_word_loader, mock_rtf_loader):
        """Test that .docx files are always routed to Word processor."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.rtf_processor import RTFProcessor
        from src.rag_store.word_processor import WordProcessor
        
        registry = ProcessorRegistry()
        
        rtf_processor = RTFProcessor()
        word_processor = WordProcessor()
        
        registry.register_processor(rtf_processor)
        registry.register_processor(word_processor)
        
        # Test .docx file (doesn't need to exist for routing test)
        docx_file = Path("test.docx")
        processor = registry.get_processor_for_file(docx_file)
        
        self.assertIsInstance(processor, WordProcessor)

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    def test_no_rtf_processor_fallback(self, mock_rtf_loader):
        """Test behavior when RTF processor is not registered."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.word_processor import WordProcessor
        
        registry = ProcessorRegistry()
        
        # Only register Word processor, not RTF processor
        with patch('src.rag_store.word_processor.UnstructuredLoader'):
            word_processor = WordProcessor()
            registry.register_processor(word_processor)
        
        # Create .doc file with RTF content
        rtf_as_doc = self.create_doc_with_rtf_content("test.doc")
        processor = registry.get_processor_for_file(rtf_as_doc)
        
        # Should fall back to Word processor since RTF processor not available
        self.assertIsInstance(processor, WordProcessor)

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.word_processor.UnstructuredLoader')
    @patch('src.rag_store.file_detection.FileContentDetector.should_use_rtf_processor')
    def test_file_detection_error_fallback(self, mock_should_use_rtf, mock_word_loader, mock_rtf_loader):
        """Test fallback when file detection fails."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.rtf_processor import RTFProcessor
        from src.rag_store.word_processor import WordProcessor
        
        # Mock file detection to raise an exception
        mock_should_use_rtf.side_effect = Exception("File detection error")
        
        registry = ProcessorRegistry()
        
        rtf_processor = RTFProcessor()
        word_processor = WordProcessor()
        
        registry.register_processor(rtf_processor)
        registry.register_processor(word_processor)
        
        # Create .doc file
        doc_file = self.create_real_doc_file("test.doc")
        processor = registry.get_processor_for_file(doc_file)
        
        # Should fall back to normal extension-based routing (Word processor)
        self.assertIsInstance(processor, WordProcessor)

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.word_processor.UnstructuredLoader')
    def test_process_document_with_smart_routing(self, mock_word_loader, mock_rtf_loader):
        """Test document processing with smart routing."""
        from src.rag_store.document_processor import ProcessorRegistry
        from src.rag_store.rtf_processor import RTFProcessor
        from src.rag_store.word_processor import WordProcessor
        from langchain.schema import Document
        
        # Setup mock RTF loader
        mock_rtf_loader_instance = MagicMock()
        mock_rtf_loader.return_value = mock_rtf_loader_instance
        mock_rtf_loader_instance.load.return_value = [
            Document(page_content="RTF content", metadata={"source": "test"})
        ]
        
        registry = ProcessorRegistry()
        
        # Register processors
        with patch('src.rag_store.rtf_processor.log_document_processing_start'), \
             patch('src.rag_store.rtf_processor.log_document_processing_complete'):
            rtf_processor = RTFProcessor()
            
        with patch('src.rag_store.word_processor.log_document_processing_start'), \
             patch('src.rag_store.word_processor.log_document_processing_complete'):
            word_processor = WordProcessor()
        
        registry.register_processor(rtf_processor)
        registry.register_processor(word_processor)
        
        # Create .doc file with RTF content
        rtf_as_doc = self.create_doc_with_rtf_content("test.doc")
        
        # Process document - should use RTF processor
        with patch('src.rag_store.rtf_processor.log_document_processing_start') as mock_start, \
             patch('src.rag_store.rtf_processor.log_document_processing_complete') as mock_complete:
            
            mock_start.return_value = {"file_path": str(rtf_as_doc)}
            
            documents = registry.process_document(rtf_as_doc)
            
            # Verify RTF processor was used
            self.assertIsInstance(documents, list)
            mock_rtf_loader.assert_called_once()

    def test_get_supported_extensions_with_rtf(self):
        """Test that supported extensions include RTF."""
        from src.rag_store.document_processor import ProcessorRegistry
        
        with patch('src.rag_store.rtf_processor.UnstructuredRTFLoader'), \
             patch('src.rag_store.word_processor.UnstructuredLoader'):
            
            from src.rag_store.rtf_processor import RTFProcessor
            from src.rag_store.word_processor import WordProcessor
            
            registry = ProcessorRegistry()
            
            rtf_processor = RTFProcessor()
            word_processor = WordProcessor()
            
            registry.register_processor(rtf_processor)
            registry.register_processor(word_processor)
            
            supported_extensions = registry.get_supported_extensions()
            
            # Verify all expected extensions are supported
            expected_extensions = {'.rtf', '.doc', '.docx'}
            self.assertTrue(expected_extensions.issubset(supported_extensions))


if __name__ == '__main__':
    unittest.main()