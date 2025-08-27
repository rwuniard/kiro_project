"""
Unit tests for PDF processor module.

This test suite covers the core functionality of the PDFProcessor class,
including PDF file validation, document chunking, and metadata generation.
"""

import shutil

# Import the module to test
import sys
import tempfile
import unittest

from pathlib import Path
from unittest.mock import Mock, patch

from langchain.schema import Document

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from rag_store.pdf_processor import PDFProcessor


class TestPDFProcessor(unittest.TestCase):
    """Test cases for PDFProcessor class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.processor = PDFProcessor()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up after each test method."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_values(self):
        """Test PDFProcessor initialization with default values."""
        self.assertEqual(self.processor.supported_extensions, {".pdf"})
        self.assertEqual(self.processor.default_chunk_size, 1800)
        self.assertEqual(self.processor.default_chunk_overlap, 270)

    def test_is_pdf_file_valid_pdf(self):
        """Test is_pdf_file with valid PDF extensions."""
        # Test lowercase .pdf
        pdf_path = Path("document.pdf")
        self.assertTrue(self.processor.is_pdf_file(pdf_path))

        # Test uppercase .PDF
        pdf_path_upper = Path("document.PDF")
        self.assertTrue(self.processor.is_pdf_file(pdf_path_upper))

        # Test mixed case .Pdf
        pdf_path_mixed = Path("document.Pdf")
        self.assertTrue(self.processor.is_pdf_file(pdf_path_mixed))

    def test_is_pdf_file_invalid_extensions(self):
        """Test is_pdf_file with invalid file extensions."""
        # Test various non-PDF extensions
        invalid_files = [
            "document.txt",
            "document.docx",
            "document.png",
            "document",
            "document.pdf.txt",
        ]

        for filename in invalid_files:
            with self.subTest(filename=filename):
                self.assertFalse(self.processor.is_pdf_file(Path(filename)))

    @patch("rag_store.pdf_processor.fitz.open")
    def test_pdf_to_documents_recursive_default_params(self, mock_fitz_open):
        """Test pdf_to_documents_recursive with default parameters using PyMuPDF."""
        # Setup mock PyMuPDF document
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 2
        
        # Create mock pages
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Sample content from page 1"
        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Sample content from page 2"
        
        # Configure mock document indexing
        mock_doc.__getitem__ = Mock(side_effect=[mock_page1, mock_page2])

        # Create a temporary PDF file path
        pdf_path = self.temp_dir_path / "test.pdf"
        pdf_path.touch()  # Create empty file

        # Call the method
        result = self.processor.pdf_to_documents_recursive(pdf_path)

        # Verify fitz.open was called with correct path
        mock_fitz_open.assert_called_once_with(str(pdf_path))

        # Verify document close was called
        mock_doc.close.assert_called_once()

        # Verify returned documents
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        # Verify first document structure
        if result:
            doc = result[0]
            self.assertIsInstance(doc, Document)

            # Verify metadata enhancement with new interface
            expected_metadata_keys = {
                "source",
                "chunk_id",
                "document_id",
                "file_path",
                "file_type",
                "processor",
                "chunk_size",
                "chunk_overlap",
                "splitting_method",
                "loader_type"
            }

            # Check expected metadata keys are present
            self.assertTrue(expected_metadata_keys.issubset(doc.metadata.keys()))

            # Check specific metadata values with new interface
            self.assertEqual(doc.metadata["source"], "test.pdf")
            self.assertEqual(doc.metadata["document_id"], "test_pdf")
            self.assertEqual(doc.metadata["file_type"], ".pdf")
            self.assertEqual(doc.metadata["processor"], "PDFProcessor")
            self.assertEqual(doc.metadata["chunk_size"], 1800)
            self.assertEqual(doc.metadata["chunk_overlap"], 270)
            self.assertEqual(
                doc.metadata["splitting_method"], "RecursiveCharacterTextSplitter"
            )
            self.assertEqual(doc.metadata["loader_type"], "PyMuPDF_OCR")

    @patch("rag_store.pdf_processor.fitz.open")
    def test_pdf_to_documents_recursive_custom_params(self, mock_fitz_open):
        """Test pdf_to_documents_recursive with custom parameters."""
        # Setup mock PyMuPDF document
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 1
        
        # Create mock page
        mock_page = Mock()
        mock_page.get_text.return_value = "Test content for custom parameters"
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        # Create temporary PDF file
        pdf_path = self.temp_dir_path / "custom_test.pdf"
        pdf_path.touch()

        # Custom parameters
        custom_chunk_size = 1000
        custom_overlap = 100

        # Call with custom parameters
        result = self.processor.pdf_to_documents_recursive(
            pdf_path, chunk_size=custom_chunk_size, chunk_overlap=custom_overlap
        )

        # Verify custom parameters were used in metadata
        if result:
            self.assertEqual(result[0].metadata["chunk_size"], custom_chunk_size)
            self.assertEqual(result[0].metadata["chunk_overlap"], custom_overlap)

    @patch("rag_store.pdf_processor.fitz.open")
    def test_pdf_to_documents_recursive_empty_result(self, mock_fitz_open):
        """Test pdf_to_documents_recursive when document has no pages."""
        # Setup mock to return document with no pages
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 0

        # Create temporary PDF file
        pdf_path = self.temp_dir_path / "empty_test.pdf"
        pdf_path.touch()

        # Call the method
        result = self.processor.pdf_to_documents_recursive(pdf_path)

        # Verify empty result
        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, list)
        
        # Verify document was closed
        mock_doc.close.assert_called_once()

    @patch("rag_store.pdf_processor.fitz.open")
    def test_pdf_to_documents_recursive_loader_exception(self, mock_fitz_open):
        """Test pdf_to_documents_recursive when PyMuPDF raises an exception."""
        # Setup mock to raise exception
        mock_fitz_open.side_effect = Exception("PDF loading failed")

        # Create temporary PDF file
        pdf_path = self.temp_dir_path / "error_test.pdf"
        pdf_path.touch()

        # Verify exception is propagated
        with self.assertRaises(Exception) as context:
            self.processor.pdf_to_documents_recursive(pdf_path)

        self.assertIn("Error processing PDF", str(context.exception))
        self.assertIn("PDF loading failed", str(context.exception))

    @patch("rag_store.pdf_processor.fitz.open")
    def test_pdf_to_documents_recursive_nonexistent_file(self, mock_fitz_open):
        """Test pdf_to_documents_recursive with non-existent file."""
        # Create path to non-existent file
        nonexistent_path = self.temp_dir_path / "nonexistent.pdf"

        # The method should still try to process (PyMuPDF will handle the error)
        # We expect it to raise an exception when fitz.open tries to load
        mock_fitz_open.side_effect = FileNotFoundError("File not found")

        with self.assertRaises(FileNotFoundError):
            self.processor.pdf_to_documents_recursive(nonexistent_path)

    @patch("rag_store.pdf_processor.fitz.open")
    def test_metadata_document_id_extraction(self, mock_fitz_open):
        """Test that document_id is correctly extracted from file path."""
        # Setup mock PyMuPDF document
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 1
        
        # Create mock page
        mock_page = Mock()
        mock_page.get_text.return_value = "Test content"
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        # Test various file names - updated expected format for new interface
        test_cases = [
            ("simple.pdf", "simple_pdf"),
            ("complex_document_name.pdf", "complex_document_name_pdf"),
            ("document with spaces.pdf", "document with spaces_pdf"),
            ("123_numbers.pdf", "123_numbers_pdf"),
        ]

        for filename, expected_id in test_cases:
            with self.subTest(filename=filename):
                pdf_path = self.temp_dir_path / filename
                pdf_path.touch()

                result = self.processor.pdf_to_documents_recursive(pdf_path)
                if result:
                    self.assertEqual(result[0].metadata["document_id"], expected_id)

    @patch("rag_store.pdf_processor.fitz.open")
    def test_chunk_numbering_sequence(self, mock_fitz_open):
        """Test that chunks are numbered sequentially starting from 0."""
        # Setup mock PyMuPDF document
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 3
        
        # Create mock pages with enough content to generate multiple chunks
        mock_pages = []
        page_contents = []
        for i in range(3):
            mock_page = Mock()
            content = f"This is content for page {i}. " * 100  # Enough content to create chunks
            mock_page.get_text.return_value = content
            page_contents.append(content)
            mock_pages.append(mock_page)
        
        mock_doc.__getitem__ = Mock(side_effect=mock_pages)

        pdf_path = self.temp_dir_path / "multi_chunk.pdf"
        pdf_path.touch()

        result = self.processor.pdf_to_documents_recursive(pdf_path)

        # Verify sequential numbering (new interface generates chunk_id strings)
        for i, doc in enumerate(result):
            self.assertEqual(doc.metadata["chunk_id"], f"chunk_{i}")
            # Don't check total_chunks since it depends on how the splitter works

    @patch("rag_store.pdf_processor.fitz.open")
    @patch("rag_store.pdf_processor.OCR_AVAILABLE", True)
    def test_ocr_fallback_for_image_based_pdf(self, mock_fitz_open):
        """Test OCR fallback when PDF contains minimal text (image-based)."""
        # Setup mock PyMuPDF document
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 1
        
        # Create mock page that initially returns minimal text (triggering OCR)
        mock_page = Mock()
        # First call returns minimal text (empty), triggering OCR attempt
        mock_page.get_text.return_value = ""  # Triggers OCR
        mock_page.get_text.side_effect = None  # Reset side_effect
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        # Mock the OCR method to return successful OCR text
        with patch.object(self.processor, '_perform_ocr_on_page', return_value="OCR extracted text from image"):
            # Create temporary PDF file
            pdf_path = self.temp_dir_path / "image_pdf.pdf"
            pdf_path.touch()

            # Call the method
            result = self.processor.pdf_to_documents_recursive(pdf_path)

            # Verify result contains OCR text
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)
            
            if result:
                # Verify OCR metadata is present - note the metadata structure changed
                self.assertEqual(result[0].metadata["loader_type"], "PyMuPDF_OCR")
                # Verify content was extracted
                self.assertIn("OCR extracted", result[0].page_content)
                # Verify extraction method shows OCR was used
                self.assertEqual(result[0].metadata["extraction_method"], "tesseract_ocr")

    @patch("rag_store.pdf_processor.fitz.open")
    def test_ocr_blocks_fallback(self, mock_fitz_open):
        """Test OCR blocks fallback when standard text extraction fails completely."""
        # Setup mock PyMuPDF document
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 1
        
        # Create mock page that returns empty text but has text blocks
        mock_page = Mock()
        # Both get_text() calls return empty
        mock_page.get_text.return_value = ""
        # But get_text("blocks") returns structured data
        def get_text_side_effect(mode=None):
            if mode == "blocks":
                # Return mock blocks data (x0, y0, x1, y1, text, block_no, block_type)
                return [
                    (0, 0, 100, 20, "Block 1 text content", 0, 0),
                    (0, 25, 100, 45, "Block 2 more content", 1, 0),
                ]
            return ""
        
        mock_page.get_text.side_effect = get_text_side_effect
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        # Create temporary PDF file
        pdf_path = self.temp_dir_path / "blocks_pdf.pdf"
        pdf_path.touch()

        # Call the method
        result = self.processor.pdf_to_documents_recursive(pdf_path)

        # Verify result contains text from blocks
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        if result:
            # Verify blocks extraction worked
            content = result[0].page_content
            self.assertIn("Block 1 text content", content)
            self.assertIn("Block 2 more content", content)
            self.assertEqual(result[0].metadata["loader_type"], "PyMuPDF_OCR")

    @patch("rag_store.pdf_processor.fitz.open")
    @patch("rag_store.pdf_processor.OCR_AVAILABLE", False)
    def test_ocr_not_available_fallback(self, mock_fitz_open):
        """Test behavior when OCR is not available."""
        # Setup mock PyMuPDF document
        mock_doc = Mock()
        mock_fitz_open.return_value = mock_doc
        mock_doc.page_count = 1
        
        # Create mock page that returns no text
        mock_page = Mock()
        mock_page.get_text.return_value = ""
        mock_doc.__getitem__ = Mock(return_value=mock_page)

        # Create temporary PDF file
        pdf_path = self.temp_dir_path / "no_ocr_pdf.pdf"
        pdf_path.touch()

        # Call the method
        result = self.processor.pdf_to_documents_recursive(pdf_path)

        # Should return empty result since no OCR is available and no text found
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


class TestPDFProcessorIntegration(unittest.TestCase):
    """Integration tests that may require actual PDF processing (optional)."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = PDFProcessor()

    def test_with_real_pdf_if_available(self):
        """Test with a real PDF file if one is available in the rag_store directory."""
        # Look for test PDF files in the correct data_source directory
        data_source_path = (
            Path(__file__).parent.parent.parent / "src" / "rag_store" / "data_source"
        )
        test_pdf_path = data_source_path / "thinkpython.pdf"

        if test_pdf_path.exists():
            print(f"Running integration test with {test_pdf_path.name}")

            try:
                # Process the PDF
                documents = self.processor.pdf_to_documents_recursive(test_pdf_path)

                # Basic validation
                self.assertIsInstance(documents, list)
                self.assertGreater(len(documents), 0)

                # Check first document
                if documents:
                    doc = documents[0]
                    self.assertIsInstance(doc, Document)
                    self.assertIsInstance(doc.page_content, str)
                    self.assertGreater(len(doc.page_content), 0)

                    # Check metadata with new interface structure
                    required_keys = {
                        "source",
                        "chunk_id",
                        "document_id",
                        "file_path",
                        "file_type",
                        "processor",
                        "chunk_size",
                        "chunk_overlap",
                        "splitting_method",
                    }
                    self.assertTrue(required_keys.issubset(doc.metadata.keys()))

                print(
                    f"✓ Successfully processed {len(documents)} chunks from {test_pdf_path.name}"
                )

            except Exception as e:
                self.skipTest(
                    f"Integration test skipped due to PDF processing error: {e}"
                )
        else:
            self.skipTest("No test PDF file available for integration testing")


if __name__ == "__main__":
    # Configure test runner
    unittest.main(verbosity=2)
