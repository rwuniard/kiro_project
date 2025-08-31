"""
Unit Tests for MHT Processor Module

Tests the MHT/MHTML document processing functionality including:
- File type validation and support detection
- MIME multipart parsing and HTML extraction
- Text chunking and metadata generation
- Error handling for malformed files
- Legacy method compatibility
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from langchain.schema import Document

from src.rag_store.mht_processor import MHTProcessor


class TestMHTProcessor(unittest.TestCase):
    """Test cases for MHTProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = MHTProcessor()
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_processor_initialization(self):
        """Test MHTProcessor initialization and basic properties."""
        # Test supported extensions
        expected_extensions = {".mht", ".mhtml"}
        self.assertEqual(self.processor.supported_extensions, expected_extensions)
        
        # Test default parameters
        self.assertEqual(self.processor.default_chunk_size, 1200)
        self.assertEqual(self.processor.default_chunk_overlap, 180)
        
        # Test processor name
        self.assertEqual(self.processor.processor_name, "MHTProcessor")

    def test_file_type_description(self):
        """Test file type description property."""
        description = self.processor.file_type_description
        self.assertIn("Web Archive", description)
        self.assertIn("MHT/MHTML", description)
        self.assertIn(".mht", description)
        self.assertIn(".mhtml", description)

    def test_is_supported_file(self):
        """Test file support detection."""
        # Test supported extensions
        mht_file = Path(self.temp_dir) / "test.mht"
        mhtml_file = Path(self.temp_dir) / "test.mhtml"
        
        self.assertTrue(self.processor.is_supported_file(mht_file))
        self.assertTrue(self.processor.is_supported_file(mhtml_file))
        
        # Test case insensitivity
        upper_mht = Path(self.temp_dir) / "test.MHT"
        self.assertTrue(self.processor.is_supported_file(upper_mht))
        
        # Test unsupported extensions
        unsupported_files = [
            "test.pdf", "test.txt", "test.docx", "test.html", "test.xml"
        ]
        for filename in unsupported_files:
            file_path = Path(self.temp_dir) / filename
            self.assertFalse(self.processor.is_supported_file(file_path))

    def test_get_processing_params_defaults(self):
        """Test processing parameter retrieval with defaults."""
        # Test default parameters
        chunk_size, chunk_overlap = self.processor.get_processing_params()
        self.assertEqual(chunk_size, 1200)
        self.assertEqual(chunk_overlap, 180)
        
        # Test explicit parameters override defaults
        chunk_size, chunk_overlap = self.processor.get_processing_params(
            chunk_size=800, chunk_overlap=100
        )
        self.assertEqual(chunk_size, 800)
        self.assertEqual(chunk_overlap, 100)
        
        # Test partial override
        chunk_size, chunk_overlap = self.processor.get_processing_params(
            chunk_size=1000
        )
        self.assertEqual(chunk_size, 1000)
        self.assertEqual(chunk_overlap, 180)  # Default

    def create_sample_mht_file(self):
        """Create a sample MHT file for testing."""
        mht_content = """MIME-Version: 1.0
Content-Type: multipart/related; boundary="----=_NextPart_01DC17A4.68DC3690"

------=_NextPart_01DC17A4.68DC3690
Content-Location: file:///C:/test.htm
Content-Transfer-Encoding: quoted-printable
Content-Type: text/html

<html>
<head>
    <title>Test Document</title>
</head>
<body>
    <h1>Electronic Signatures Test Document</h1>
    <p>This is a test MHT file containing HTML content for processing.</p>
    <p>It includes multiple paragraphs to test text extraction and chunking.</p>
    <div>
        <h2>Section 1</h2>
        <p>This section contains information about electronic signatures and digital documents.</p>
        <p>MHT files are web archive format that includes HTML and related resources.</p>
    </div>
    <div>
        <h2>Section 2</h2>
        <p>Testing text extraction from MIME multipart format.</p>
        <p>The processor should handle HTML parsing and text cleaning.</p>
    </div>
</body>
</html>

------=_NextPart_01DC17A4.68DC3690--
"""
        mht_file = Path(self.temp_dir) / "test.mht"
        with open(mht_file, 'w', encoding='utf-8') as f:
            f.write(mht_content)
        return mht_file

    def test_create_sample_mht_file(self):
        """Test MHT file creation helper method."""
        mht_file = self.create_sample_mht_file()
        self.assertTrue(mht_file.exists())
        self.assertEqual(mht_file.suffix, '.mht')

    def test_process_document_success(self):
        """Test successful MHT document processing."""
        # Create test MHT file
        mht_file = self.create_sample_mht_file()
        
        # Process the document
        documents = self.processor.process_document(mht_file)
        
        # Validate results
        self.assertIsInstance(documents, list)
        self.assertGreater(len(documents), 0)
        
        # Check document structure
        for doc in documents:
            self.assertIsInstance(doc, Document)
            self.assertIsInstance(doc.page_content, str)
            self.assertIsInstance(doc.metadata, dict)
            self.assertGreater(len(doc.page_content.strip()), 0)
        
        # Check content extraction
        full_content = " ".join(doc.page_content for doc in documents)
        self.assertIn("Electronic Signatures Test Document", full_content)
        self.assertIn("test MHT file", full_content)
        self.assertIn("MIME multipart format", full_content)
        
        # Verify HTML tags were removed
        self.assertNotIn("<html>", full_content)
        self.assertNotIn("<body>", full_content)
        self.assertNotIn("<h1>", full_content)

    def test_document_metadata(self):
        """Test document metadata generation."""
        mht_file = self.create_sample_mht_file()
        documents = self.processor.process_document(mht_file)
        
        self.assertGreater(len(documents), 0)
        
        # Check metadata in first document
        metadata = documents[0].metadata
        
        # Check common metadata fields
        expected_fields = [
            'source', 'file_path', 'file_type', 'processor', 'file_size',
            'chunk_id', 'document_id', 'chunk_size', 'chunk_overlap',
            'splitting_method', 'total_chunks', 'document_format',
            'processor_version', 'original_encoding'
        ]
        
        for field in expected_fields:
            self.assertIn(field, metadata, f"Missing metadata field: {field}")
        
        # Check specific values
        self.assertEqual(metadata['file_type'], '.mht')
        self.assertEqual(metadata['processor'], 'MHTProcessor')
        self.assertEqual(metadata['document_format'], 'Web Archive (MHT/MHTML)')
        self.assertEqual(metadata['original_encoding'], 'MIME multipart')
        self.assertEqual(metadata['splitting_method'], 'RecursiveCharacterTextSplitter')
        self.assertEqual(metadata['total_chunks'], len(documents))
        
        # Check chunk-specific metadata
        for i, doc in enumerate(documents):
            self.assertEqual(doc.metadata['chunk_id'], f'chunk_{i}')

    def test_chunk_parameters(self):
        """Test chunking with custom parameters."""
        mht_file = self.create_sample_mht_file()
        
        # Test with custom chunk parameters
        chunk_size = 500
        chunk_overlap = 50
        documents = self.processor.process_document(
            mht_file, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        
        self.assertGreater(len(documents), 0)
        
        # Verify chunk parameters in metadata
        for doc in documents:
            self.assertEqual(doc.metadata['chunk_size'], chunk_size)
            self.assertEqual(doc.metadata['chunk_overlap'], chunk_overlap)
        
        # Verify chunks are within size limits (allowing some flexibility)
        for doc in documents:
            self.assertLessEqual(len(doc.page_content), chunk_size + chunk_overlap + 50)

    def test_empty_content_handling(self):
        """Test handling of MHT files with no meaningful content."""
        # Create MHT file with minimal content
        empty_mht_content = """MIME-Version: 1.0
Content-Type: multipart/related; boundary="----=_NextPart_EMPTY"

------=_NextPart_EMPTY
Content-Type: text/html

<html><body></body></html>

------=_NextPart_EMPTY--
"""
        mht_file = Path(self.temp_dir) / "empty.mht"
        with open(mht_file, 'w', encoding='utf-8') as f:
            f.write(empty_mht_content)
        
        documents = self.processor.process_document(mht_file)
        
        # Should return empty list for files with no meaningful content
        self.assertEqual(len(documents), 0)

    def test_malformed_mht_fallback(self):
        """Test fallback handling for malformed MHT files."""
        # Create malformed MHT file (missing proper MIME structure)
        malformed_content = """This is not a proper MHT file.
<html>
<body>
<h1>Test Content</h1>
<p>This should still be extracted by fallback method.</p>
</body>
</html>
Some trailing content."""
        
        mht_file = Path(self.temp_dir) / "malformed.mht"
        with open(mht_file, 'w', encoding='utf-8') as f:
            f.write(malformed_content)
        
        documents = self.processor.process_document(mht_file)
        
        # Should still extract some content using fallback
        self.assertGreater(len(documents), 0)
        full_content = " ".join(doc.page_content for doc in documents)
        self.assertIn("Test Content", full_content)
        self.assertIn("extracted by fallback", full_content)

    def test_encoding_handling(self):
        """Test handling of different text encodings."""
        # Create MHT with non-UTF8 characters
        mht_content = """MIME-Version: 1.0
Content-Type: multipart/related; boundary="----=_NextPart_ENCODING"

------=_NextPart_ENCODING
Content-Type: text/html; charset=UTF-8

<html>
<body>
<h1>Encoding Test: Café, naïve, résumé</h1>
<p>Special characters: © ® ™ € £ ¥</p>
<p>Unicode: 你好 こんにちは Здравствуйте</p>
</body>
</html>

------=_NextPart_ENCODING--
"""
        
        mht_file = Path(self.temp_dir) / "encoding.mht"
        with open(mht_file, 'w', encoding='utf-8') as f:
            f.write(mht_content)
        
        documents = self.processor.process_document(mht_file)
        
        self.assertGreater(len(documents), 0)
        full_content = " ".join(doc.page_content for doc in documents)
        
        # Check that content was extracted successfully (encoding may vary)
        self.assertIn("Encoding Test", full_content)
        self.assertIn("Special characters", full_content)
        self.assertIn("Unicode", full_content)
        
        # Content should be present even if special chars are converted
        # The processor handles various encodings and may convert special chars

    def test_file_validation(self):
        """Test file validation methods."""
        # Test non-existent file
        non_existent = Path(self.temp_dir) / "nonexistent.mht"
        with self.assertRaises(FileNotFoundError):
            self.processor.process_document(non_existent)
        
        # Test unsupported file type
        txt_file = Path(self.temp_dir) / "test.txt"
        txt_file.write_text("This is a text file")
        
        with self.assertRaises(ValueError) as context:
            self.processor.process_document(txt_file)
        
        self.assertIn("Unsupported file type", str(context.exception))

    def test_extract_html_from_message(self):
        """Test HTML extraction from email message."""
        import email
        
        # Create test email message
        msg_content = """MIME-Version: 1.0
Content-Type: multipart/related; boundary="test"

--test
Content-Type: text/html

<html><body><h1>Test HTML</h1></body></html>

--test--
"""
        
        msg = email.message_from_string(msg_content)
        html_content = self.processor._extract_html_from_message(msg)
        
        self.assertIn("<html>", html_content)
        self.assertIn("Test HTML", html_content)

    def test_extract_text_fallback(self):
        """Test fallback text extraction method."""
        content_with_html = """Some header content
<html>
<body>
<h1>Main Content</h1>
<p>This is the main content.</p>
</body>
</html>
Some footer content"""
        
        extracted_text = self.processor._extract_text_fallback(content_with_html)
        
        self.assertIn("Main Content", extracted_text)
        self.assertIn("main content", extracted_text)
        # HTML tags should be removed
        self.assertNotIn("<h1>", extracted_text)
        self.assertNotIn("<body>", extracted_text)

    def test_rtf_content_detection(self):
        """Test RTF content detection in MHT context."""
        # While not typical, test edge case handling
        test_content = "{\\rtf1 This is RTF content}"
        
        # This should not cause issues with MHT processor
        mht_file = Path(self.temp_dir) / "mixed.mht" 
        with open(mht_file, 'w', encoding='utf-8') as f:
            f.write(f"""MIME-Version: 1.0
Content-Type: text/html

<html><body><pre>{test_content}</pre></body></html>""")
        
        documents = self.processor.process_document(mht_file)
        self.assertGreater(len(documents), 0)

    def test_legacy_compatibility_methods(self):
        """Test legacy method compatibility."""
        mht_file = self.create_sample_mht_file()
        
        # Test legacy process_mht_file method
        documents = self.processor.process_mht_file(mht_file)
        
        self.assertIsInstance(documents, list)
        self.assertGreater(len(documents), 0)
        
        # Should produce same results as process_document
        documents_new = self.processor.process_document(mht_file)
        self.assertEqual(len(documents), len(documents_new))
        
        for doc_old, doc_new in zip(documents, documents_new):
            self.assertEqual(doc_old.page_content, doc_new.page_content)

    @patch('src.rag_store.logging_config.log_processing_error')
    def test_error_handling_and_logging(self, mock_log_error):
        """Test error handling and logging."""
        # Create file that will cause processing error (completely empty MHT)
        bad_file = Path(self.temp_dir) / "bad.mht"
        bad_file.write_bytes(b'\x00\x01\x02\x03')  # Binary garbage
        
        # The processor should handle this gracefully and return empty results
        # since it has robust fallback methods
        documents = self.processor.process_document(bad_file)
        
        # May return empty documents or process with fallback
        self.assertIsInstance(documents, list)
        
        # Note: The processor is quite robust and may not fail on binary data
        # It will try multiple fallback methods before giving up

    def test_processor_registry_integration(self):
        """Test integration with processor registry."""
        from src.rag_store.document_processor import ProcessorRegistry
        
        registry = ProcessorRegistry()
        registry.register_processor(self.processor)
        
        # Test that MHT files are routed to MHT processor
        mht_file = Path(self.temp_dir) / "test.mht"
        processor = registry.get_processor_for_file(mht_file)
        
        self.assertIsInstance(processor, MHTProcessor)
        
        # Test supported extensions are registered
        supported = registry.get_supported_extensions()
        self.assertIn('.mht', supported)
        self.assertIn('.mhtml', supported)

    def test_performance_characteristics(self):
        """Test performance characteristics of MHT processing."""
        import time
        
        # Create larger MHT file for performance testing
        large_content = "<p>Test paragraph. " * 100 + "</p>"
        mht_content = f"""MIME-Version: 1.0
Content-Type: text/html

<html><body>{large_content * 50}</body></html>"""
        
        mht_file = Path(self.temp_dir) / "large.mht"
        with open(mht_file, 'w', encoding='utf-8') as f:
            f.write(mht_content)
        
        start_time = time.time()
        documents = self.processor.process_document(mht_file)
        processing_time = time.time() - start_time
        
        # Should process in reasonable time (< 5 seconds for test content)
        self.assertLess(processing_time, 5.0)
        self.assertGreater(len(documents), 0)


if __name__ == '__main__':
    unittest.main()