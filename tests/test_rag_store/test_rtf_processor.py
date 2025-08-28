"""
Tests for RTF Processor

This module tests the RTF processor functionality including document processing
and integration with the RAG system.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain.schema import Document


class TestRTFProcessor(unittest.TestCase):
    """Test cases for RTF processor functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def create_test_rtf_file(self, content: str = None) -> Path:
        """Create a test RTF file with sample content."""
        if content is None:
            content = r"""{\rtf1\ansi\deff0 
{\fonttbl {\f0 Times New Roman;}}
\f0\fs24 This is a test RTF document with some content.
\par
This is a second paragraph with more text.
}"""
        
        rtf_file = self.temp_path / "test_document.rtf"
        with open(rtf_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return rtf_file
    
    def create_test_doc_with_rtf_content(self, content: str = None) -> Path:
        """Create a test .doc file that actually contains RTF content."""
        if content is None:
            content = r"""{\rtf1\ansi\deff0 
{\fonttbl {\f0 Times New Roman;}}
\f0\fs24 This is an RTF document with .doc extension.
}"""
        
        doc_file = self.temp_path / "rtf_as_doc.doc"
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return doc_file

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    def test_rtf_processor_initialization(self, mock_loader_class):
        """Test RTF processor initialization."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        processor = RTFProcessor()
        
        self.assertEqual(processor.supported_extensions, {".rtf"})
        self.assertEqual(processor.default_chunk_size, 800)
        self.assertEqual(processor.default_chunk_overlap, 120)
        self.assertEqual(processor.file_type_description, "Rich Text Format documents (.rtf)")

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader', None)
    def test_rtf_processor_missing_dependency(self):
        """Test RTF processor behavior when UnstructuredRTFLoader is not available."""
        with self.assertRaises(ImportError) as context:
            from src.rag_store.rtf_processor import RTFProcessor
            RTFProcessor()
        
        self.assertIn("langchain_community with RTF support is required", str(context.exception))

    def test_is_supported_file(self):
        """Test file type support detection."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        with patch('src.rag_store.rtf_processor.UnstructuredRTFLoader'):
            processor = RTFProcessor()
            
            # Test supported extensions
            self.assertTrue(processor.is_supported_file(Path("test.rtf")))
            self.assertTrue(processor.is_supported_file(Path("test.RTF")))  # Case insensitive
            
            # Test unsupported extensions
            self.assertFalse(processor.is_supported_file(Path("test.doc")))
            self.assertFalse(processor.is_supported_file(Path("test.pdf")))
            self.assertFalse(processor.is_supported_file(Path("test.txt")))

    def test_validate_file_not_found(self):
        """Test file validation with non-existent file."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        with patch('src.rag_store.rtf_processor.UnstructuredRTFLoader'):
            processor = RTFProcessor()
            
            with self.assertRaises(FileNotFoundError):
                processor.validate_file(Path("nonexistent.rtf"))

    def test_validate_file_unsupported(self):
        """Test file validation with unsupported file type."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        with patch('src.rag_store.rtf_processor.UnstructuredRTFLoader'):
            processor = RTFProcessor()
            
            # Create a temporary file with unsupported extension
            temp_file = self.temp_path / "test.txt"
            temp_file.write_text("test content")
            
            with self.assertRaises(ValueError) as context:
                processor.validate_file(temp_file)
            
            self.assertIn("Unsupported file type", str(context.exception))

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.rtf_processor.log_document_processing_start')
    @patch('src.rag_store.rtf_processor.log_document_processing_complete')
    def test_process_document_success(self, mock_log_complete, mock_log_start, mock_loader_class):
        """Test successful RTF document processing."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        # Setup mock loader
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        
        # Create mock documents
        mock_doc1 = Document(
            page_content="This is test content from RTF.",
            metadata={"source": "test.rtf", "page": 1}
        )
        mock_doc2 = Document(
            page_content="This is more content from RTF.",
            metadata={"source": "test.rtf", "page": 2}
        )
        mock_loader.load.return_value = [mock_doc1, mock_doc2]
        
        # Setup logging mocks
        mock_context = {"file_path": "test.rtf"}
        mock_log_start.return_value = mock_context
        
        # Create test file and processor
        rtf_file = self.create_test_rtf_file()
        processor = RTFProcessor()
        
        # Process document
        documents = processor.process_document(rtf_file)
        
        # Verify results
        self.assertIsInstance(documents, list)
        self.assertGreater(len(documents), 0)
        
        # Verify loader was called with correct parameters
        mock_loader_class.assert_called_once_with(
            str(rtf_file),
            mode="elements",
            strategy="fast"
        )
        
        # Verify logging was called
        mock_log_start.assert_called_once()
        mock_log_complete.assert_called_once()

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.rtf_processor.log_document_processing_start')
    @patch('src.rag_store.rtf_processor.log_processing_error')
    def test_process_document_loader_error(self, mock_log_error, mock_log_start, mock_loader_class):
        """Test RTF document processing when loader fails."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        # Setup mock loader to raise an exception
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load.side_effect = Exception("RTF parsing failed")
        
        # Setup logging mocks
        mock_context = {"file_path": "test.rtf"}
        mock_log_start.return_value = mock_context
        
        # Create test file and processor
        rtf_file = self.create_test_rtf_file()
        processor = RTFProcessor()
        
        # Process document should raise exception
        with self.assertRaises(Exception) as context:
            processor.process_document(rtf_file)
        
        self.assertIn("Error processing RTF document", str(context.exception))
        
        # Verify error logging was called
        mock_log_error.assert_called_once()

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    @patch('src.rag_store.rtf_processor.log_document_processing_start')
    @patch('src.rag_store.rtf_processor.log_document_processing_complete')
    def test_process_empty_document(self, mock_log_complete, mock_log_start, mock_loader_class):
        """Test processing empty RTF document."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        # Setup mock loader to return empty list
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader
        mock_loader.load.return_value = []
        
        # Setup logging mocks
        mock_context = {"file_path": "test.rtf"}
        mock_log_start.return_value = mock_context
        
        # Create test file and processor
        rtf_file = self.create_test_rtf_file()
        processor = RTFProcessor()
        
        # Process document
        documents = processor.process_document(rtf_file)
        
        # Verify results
        self.assertEqual(documents, [])
        
        # Verify completion logging with empty status
        mock_log_complete.assert_called_once()
        args, kwargs = mock_log_complete.call_args
        self.assertEqual(kwargs.get('status'), 'success_empty')

    def test_detect_rtf_content(self):
        """Test RTF content detection."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        with patch('src.rag_store.rtf_processor.UnstructuredRTFLoader'):
            processor = RTFProcessor()
            
            # Test with actual RTF file
            rtf_file = self.create_test_rtf_file()
            self.assertTrue(processor.detect_rtf_content(rtf_file))
            
            # Test with non-RTF file
            text_file = self.temp_path / "test.txt"
            text_file.write_text("This is just plain text, not RTF.")
            self.assertFalse(processor.detect_rtf_content(text_file))
            
            # Test with RTF-like content but not proper RTF
            fake_rtf = self.temp_path / "fake.rtf"
            fake_rtf.write_text("This mentions \\rtf but is not real RTF")
            self.assertFalse(processor.detect_rtf_content(fake_rtf))

    def test_get_processing_params(self):
        """Test processing parameter handling."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        with patch('src.rag_store.rtf_processor.UnstructuredRTFLoader'):
            processor = RTFProcessor()
            
            # Test with default parameters
            chunk_size, chunk_overlap = processor.get_processing_params()
            self.assertEqual(chunk_size, 800)
            self.assertEqual(chunk_overlap, 120)
            
            # Test with custom parameters
            chunk_size, chunk_overlap = processor.get_processing_params(1000, 200)
            self.assertEqual(chunk_size, 1000)
            self.assertEqual(chunk_overlap, 200)
            
            # Test with partial custom parameters
            chunk_size, chunk_overlap = processor.get_processing_params(chunk_size=1500)
            self.assertEqual(chunk_size, 1500)
            self.assertEqual(chunk_overlap, 120)  # Default

    @patch('src.rag_store.rtf_processor.UnstructuredRTFLoader')
    def test_metadata_template(self, mock_loader_class):
        """Test metadata template generation."""
        from src.rag_store.rtf_processor import RTFProcessor
        
        processor = RTFProcessor()
        rtf_file = self.create_test_rtf_file()
        
        metadata = processor.get_metadata_template(rtf_file)
        
        self.assertEqual(metadata["source"], rtf_file.name)
        self.assertEqual(metadata["file_path"], str(rtf_file))
        self.assertEqual(metadata["file_type"], ".rtf")
        self.assertEqual(metadata["processor"], "RTFProcessor")
        self.assertIn("file_size", metadata)


if __name__ == '__main__':
    unittest.main()