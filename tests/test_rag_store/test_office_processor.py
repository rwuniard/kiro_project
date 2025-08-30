"""
Unit tests for Office document processor.

This test suite covers the OfficeProcessor class functionality
including document processing for various office formats, metadata generation, and error handling.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from langchain.schema import Document

from rag_store.office_processor import OfficeProcessor


class TestOfficeProcessor(unittest.TestCase):
    """Test cases for OfficeProcessor class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.processor = OfficeProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test method."""
        shutil.rmtree(self.temp_dir)

    def test_processor_initialization(self):
        """Test OfficeProcessor initialization."""
        processor = OfficeProcessor()
        self.assertIsInstance(processor, OfficeProcessor)
        
        # Test supported extensions
        expected_extensions = {
            ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
            ".odt", ".odp", ".ods", ".rtf", ".mht", ".mhtml", ".epub"
        }
        self.assertEqual(processor.supported_extensions, expected_extensions)
        
        self.assertEqual(processor.default_chunk_size, 1000)
        self.assertEqual(processor.default_chunk_overlap, 150)
        self.assertEqual(processor.processor_name, "OfficeProcessor")

    def test_file_type_description(self):
        """Test file type description."""
        description = self.processor.file_type_description
        self.assertIn("Office documents", description)
        self.assertIn("Word", description)
        self.assertIn("PowerPoint", description)
        self.assertIn("Excel", description)

    def test_is_supported_file_valid_formats(self):
        """Test is_supported_file with valid office formats."""
        test_files = [
            "test.docx", "test.doc", "test.pptx", "test.ppt",
            "test.xlsx", "test.xls", "test.odt", "test.odp",
            "test.ods", "test.rtf", "test.mht", "test.mhtml", "test.epub"
        ]
        
        for filename in test_files:
            with self.subTest(filename=filename):
                test_file = Path(self.temp_dir) / filename
                test_file.touch()
                self.assertTrue(self.processor.is_supported_file(test_file), 
                              f"Failed for {filename}")

    def test_is_supported_file_invalid_extension(self):
        """Test is_supported_file with invalid extension."""
        txt_file = Path(self.temp_dir) / "test.txt"
        txt_file.touch()
        self.assertFalse(self.processor.is_supported_file(txt_file))

    def test_is_supported_file_case_insensitive(self):
        """Test is_supported_file is case insensitive."""
        docx_file = Path(self.temp_dir) / "test.DOCX"
        docx_file.touch()
        self.assertTrue(self.processor.is_supported_file(docx_file))

    def test_get_processing_params_format_specific(self):
        """Test format-specific processing parameters."""
        # Test Word document parameters
        word_file = Path(self.temp_dir) / "test.docx"
        chunk_size, chunk_overlap = self.processor.get_processing_params(
            file_path=word_file
        )
        self.assertEqual(chunk_size, 1000)
        self.assertEqual(chunk_overlap, 150)
        
        # Test PowerPoint parameters
        ppt_file = Path(self.temp_dir) / "test.pptx"
        chunk_size, chunk_overlap = self.processor.get_processing_params(
            file_path=ppt_file
        )
        self.assertEqual(chunk_size, 800)
        self.assertEqual(chunk_overlap, 120)
        
        # Test Excel parameters
        xlsx_file = Path(self.temp_dir) / "test.xlsx"
        chunk_size, chunk_overlap = self.processor.get_processing_params(
            file_path=xlsx_file
        )
        self.assertEqual(chunk_size, 1200)
        self.assertEqual(chunk_overlap, 180)

    def test_get_processing_params_custom_override(self):
        """Test custom parameters override format-specific ones."""
        word_file = Path(self.temp_dir) / "test.docx"
        chunk_size, chunk_overlap = self.processor.get_processing_params(
            chunk_size=2000, chunk_overlap=300, file_path=word_file
        )
        self.assertEqual(chunk_size, 2000)
        self.assertEqual(chunk_overlap, 300)

    def test_get_processing_params_default_fallback(self):
        """Test default parameters when no file path provided."""
        chunk_size, chunk_overlap = self.processor.get_processing_params()
        self.assertEqual(chunk_size, 1000)
        self.assertEqual(chunk_overlap, 150)

    def test_get_separators_for_format(self):
        """Test format-specific text separators."""
        # Test PowerPoint separators
        ppt_file = Path(self.temp_dir) / "test.pptx"
        separators = self.processor._get_separators_for_format(ppt_file)
        self.assertIn("\n\n\n", separators)  # Slide breaks
        
        # Test Excel separators
        xlsx_file = Path(self.temp_dir) / "test.xlsx"
        separators = self.processor._get_separators_for_format(xlsx_file)
        self.assertIn("\t", separators)  # Tab separation for tables
        
        # Test default Word separators
        docx_file = Path(self.temp_dir) / "test.docx"
        separators = self.processor._get_separators_for_format(docx_file)
        self.assertEqual(separators, ["\n\n", "\n", ". ", " ", ""])

    def test_get_document_format_description(self):
        """Test document format descriptions."""
        test_cases = [
            ("test.docx", "Microsoft Word"),
            ("test.pptx", "Microsoft PowerPoint"),
            ("test.xlsx", "Microsoft Excel"),
            ("test.odt", "OpenDocument Text"),
            ("test.rtf", "Rich Text Format"),
            ("test.epub", "Electronic Publication")
        ]
        
        for filename, expected_desc in test_cases:
            with self.subTest(filename=filename):
                file_path = Path(self.temp_dir) / filename
                description = self.processor._get_document_format_description(file_path)
                self.assertEqual(description, expected_desc)

    def test_detect_rtf_content(self):
        """Test RTF content detection."""
        # Create a file with RTF content
        rtf_file = Path(self.temp_dir) / "test_rtf.doc"
        rtf_content = r"""{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}
        \f0\fs24 Hello, RTF world!
        }"""
        rtf_file.write_text(rtf_content, encoding='utf-8')
        
        self.assertTrue(self.processor.detect_rtf_content(rtf_file))
        
        # Create a file without RTF content
        non_rtf_file = Path(self.temp_dir) / "test_non_rtf.doc"
        non_rtf_file.write_text("This is not RTF content")
        
        self.assertFalse(self.processor.detect_rtf_content(non_rtf_file))

    def test_get_metadata_template(self):
        """Test metadata template generation."""
        docx_file = Path(self.temp_dir) / "test_document.docx"
        docx_file.touch()

        metadata = self.processor.get_metadata_template(docx_file)

        self.assertEqual(metadata["source"], "test_document.docx")
        self.assertEqual(metadata["file_type"], ".docx")
        self.assertEqual(metadata["processor"], "OfficeProcessor")
        self.assertIn("file_path", metadata)
        self.assertIn("file_size", metadata)

    def test_validate_file_not_found(self):
        """Test validate_file with non-existent file."""
        non_existent_file = Path(self.temp_dir) / "nonexistent.docx"

        with self.assertRaises(FileNotFoundError):
            self.processor.validate_file(non_existent_file)

    def test_validate_file_unsupported(self):
        """Test validate_file with unsupported file type."""
        txt_file = Path(self.temp_dir) / "test.txt"
        txt_file.touch()

        with self.assertRaises(ValueError) as context:
            self.processor.validate_file(txt_file)

        self.assertIn("Unsupported file type", str(context.exception))

    def test_legacy_method_compatibility(self):
        """Test legacy method compatibility."""
        docx_file = Path(self.temp_dir) / "legacy.docx"
        docx_file.write_text("dummy content")

        with patch.object(self.processor, "process_document") as mock_process:
            mock_process.return_value = [Document(page_content="test", metadata={})]

            # Test legacy Word processor method
            result = self.processor.load_docx_documents(docx_file)
            mock_process.assert_called_once_with(docx_file)
            self.assertEqual(len(result), 1)

            # Test legacy MHT processor method
            mht_file = Path(self.temp_dir) / "legacy.mht"
            mht_file.write_text("dummy content")
            mock_process.reset_mock()
            
            result = self.processor.process_mht_file(mht_file)
            mock_process.assert_called_once_with(mht_file)
            self.assertEqual(len(result), 1)


class TestOfficeProcessorIntegration(unittest.TestCase):
    """Integration tests for OfficeProcessor with mocked dependencies."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = OfficeProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    @patch("rag_store.office_processor.RecursiveCharacterTextSplitter")
    @patch("rag_store.office_processor.UnstructuredLoader")
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_document_processing_complete")
    def test_process_document_success_word(
        self, mock_log_complete, mock_log_start, mock_loader_class, mock_splitter_class
    ):
        """Test successful Word document processing."""
        # Setup mocks
        mock_log_start.return_value = {
            "processor_name": "OfficeProcessor",
            "file_path": "test.docx",
            "file_size": 0,
            "file_type": ".docx",
            "operation": "document_processing"
        }
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_splitter_instance = Mock()
        mock_splitter_class.return_value = mock_splitter_instance

        # Create mock documents
        mock_doc1 = Document(
            page_content="First chunk of text content.",
            metadata={"source": "test.docx"},
        )
        mock_doc2 = Document(
            page_content="Second chunk of text content.",
            metadata={"source": "test.docx"},
        )
        
        # Mock the document loading and splitting process
        raw_doc = Document(
            page_content="Full document content", metadata={"source": "test.docx"}
        )
        mock_loader_instance.load.return_value = [raw_doc]
        mock_splitter_instance.split_documents.return_value = [mock_doc1, mock_doc2]

        # Create test file
        docx_file = Path(self.temp_dir) / "test.docx"
        docx_file.write_text("dummy content")

        # Process document
        documents = self.processor.process_document(
            docx_file, chunk_size=800, chunk_overlap=120
        )

        # Verify results
        self.assertEqual(len(documents), 2)

        # Check first document metadata
        self.assertEqual(documents[0].page_content, "First chunk of text content.")
        self.assertEqual(documents[0].metadata["source"], "test.docx")
        self.assertEqual(documents[0].metadata["chunk_id"], "chunk_0")
        self.assertEqual(documents[0].metadata["document_id"], "test_office")
        self.assertEqual(documents[0].metadata["chunk_size"], 800)
        self.assertEqual(documents[0].metadata["chunk_overlap"], 120)
        self.assertEqual(documents[0].metadata["splitting_method"], "RecursiveCharacterTextSplitter")
        self.assertEqual(documents[0].metadata["total_chunks"], 2)
        self.assertEqual(documents[0].metadata["loader_type"], "UnstructuredLoader")
        self.assertEqual(documents[0].metadata["processor_version"], "unified_office_processor")
        self.assertEqual(documents[0].metadata["supports_all_office_formats"], True)
        self.assertEqual(documents[0].metadata["document_format"], "Microsoft Word")

        # Verify loader and splitter were called correctly
        mock_loader_class.assert_called_once()
        mock_loader_instance.load.assert_called_once()
        mock_splitter_class.assert_called_once()
        mock_splitter_instance.split_documents.assert_called_once_with([raw_doc])

        # Verify logging was called
        mock_log_start.assert_called_once()
        mock_log_complete.assert_called_once()

    @patch("rag_store.office_processor.RecursiveCharacterTextSplitter")
    @patch("rag_store.office_processor.UnstructuredLoader")
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_document_processing_complete")
    def test_process_document_success_powerpoint(
        self, mock_log_complete, mock_log_start, mock_loader_class, mock_splitter_class
    ):
        """Test successful PowerPoint document processing."""
        # Setup mocks
        mock_log_start.return_value = {
            "processor_name": "OfficeProcessor",
            "file_path": "test.pptx",
            "file_size": 0,
            "file_type": ".pptx",
            "operation": "document_processing"
        }
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_splitter_instance = Mock()
        mock_splitter_class.return_value = mock_splitter_instance

        # Create mock document
        mock_doc = Document(
            page_content="Slide content.",
            metadata={"source": "test.pptx"},
        )
        
        raw_doc = Document(
            page_content="Full presentation content", metadata={"source": "test.pptx"}
        )
        mock_loader_instance.load.return_value = [raw_doc]
        mock_splitter_instance.split_documents.return_value = [mock_doc]

        # Create test file
        pptx_file = Path(self.temp_dir) / "test.pptx"
        pptx_file.write_text("dummy content")

        # Process document (should use PowerPoint-specific parameters)
        documents = self.processor.process_document(pptx_file)

        # Verify results
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].metadata["document_format"], "Microsoft PowerPoint")
        self.assertEqual(documents[0].metadata["chunk_size"], 800)  # PowerPoint default
        self.assertEqual(documents[0].metadata["chunk_overlap"], 120)  # PowerPoint default

    @patch("rag_store.office_processor.RecursiveCharacterTextSplitter")
    @patch("rag_store.office_processor.UnstructuredLoader")
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_document_processing_complete")
    def test_process_document_empty_result(
        self, mock_log_complete, mock_log_start, mock_loader_class, mock_splitter_class
    ):
        """Test processing document with empty result."""
        # Setup mocks
        mock_log_start.return_value = {
            "processor_name": "OfficeProcessor",
            "file_path": "empty.docx",
            "file_size": 0,
            "file_type": ".docx",
            "operation": "document_processing"
        }
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_loader_instance.load.return_value = []

        # Create test file
        docx_file = Path(self.temp_dir) / "empty.docx"
        docx_file.write_text("dummy content")

        # Process document
        documents = self.processor.process_document(docx_file)

        # Verify results
        self.assertEqual(len(documents), 0)

        # Verify logging was called with empty status
        mock_log_complete.assert_called_once()
        call_args = mock_log_complete.call_args[1]
        self.assertEqual(call_args["chunks_created"], 0)
        self.assertEqual(call_args["status"], "success_empty")

    @patch("rag_store.office_processor.UnstructuredLoader")
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_processing_error")
    def test_process_document_loader_error(
        self, mock_log_error, mock_log_start, mock_loader_class
    ):
        """Test processing document with loader error."""
        # Setup mocks
        mock_log_start.return_value = {
            "processor_name": "OfficeProcessor",
            "file_path": "error.docx",
            "file_size": 0,
            "file_type": ".docx",
            "operation": "document_processing"
        }
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_loader_instance.load.side_effect = Exception("Loading failed")

        # Create test file
        docx_file = Path(self.temp_dir) / "error.docx"
        docx_file.write_text("dummy content")

        # Test error handling
        with self.assertRaises(Exception) as context:
            self.processor.process_document(docx_file)

        self.assertIn("Error processing office document", str(context.exception))
        self.assertIn("Loading failed", str(context.exception))

        # Verify error logging was called
        mock_log_error.assert_called_once()

    def test_rtf_content_handling_flag(self):
        """Test RTF content handling flag management."""
        # Create test file
        doc_file = Path(self.temp_dir) / "test.doc"
        doc_file.write_text("dummy content")

        # Set the flag manually (simulating ProcessorRegistry behavior)
        self.processor._handling_doc_with_rtf_content = True
        self.assertTrue(self.processor.is_supported_file(doc_file))

        # Process document (flag should be cleared after processing)
        with patch("rag_store.office_processor.UnstructuredLoader") as mock_loader_class:
            mock_loader_instance = Mock()
            mock_loader_class.return_value = mock_loader_instance
            mock_loader_instance.load.return_value = []

            with patch("rag_store.office_processor.log_document_processing_start") as mock_log_start:
                mock_log_start.return_value = {
                    "processor_name": "OfficeProcessor",
                    "file_path": str(doc_file),
                    "file_size": 0,
                    "file_type": ".doc",
                    "operation": "document_processing"
                }
                
                # This should clear the flag
                self.processor.process_document(doc_file)

        # Verify flag was cleared
        self.assertFalse(hasattr(self.processor, '_handling_doc_with_rtf_content'))


class TestOfficeProcessorErrorHandling(unittest.TestCase):
    """Test error handling scenarios in OfficeProcessor."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = OfficeProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    @patch("rag_store.office_processor.UnstructuredLoader")
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_processing_error")
    def test_process_document_unstructured_error(
        self, mock_log_error, mock_log_start, mock_loader_class
    ):
        """Test processing document with unstructured-related error."""
        # Setup mocks
        mock_log_start.return_value = {
            "processor_name": "OfficeProcessor",
            "file_path": "unstructured_error.docx",
            "file_size": 0,
            "file_type": ".docx",
            "operation": "document_processing"
        }
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_loader_instance.load.side_effect = Exception("unstructured dependency issue")

        # Create test file
        docx_file = Path(self.temp_dir) / "unstructured_error.docx"
        docx_file.write_text("dummy content")

        # Test error handling
        with self.assertRaises(Exception) as context:
            self.processor.process_document(docx_file)

        error_msg = str(context.exception)
        self.assertIn("Error processing office document", error_msg)
        self.assertIn("unstructured dependency issue", error_msg)
        self.assertIn("UnstructuredLoader with all-docs support may require", error_msg)

        # Verify error logging was called
        mock_log_error.assert_called_once()

    @patch("rag_store.office_processor.UnstructuredLoader")
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_processing_error")
    def test_process_document_permission_error(
        self, mock_log_error, mock_log_start, mock_loader_class
    ):
        """Test processing document with permission error."""
        # Setup mocks
        mock_log_start.return_value = {
            "processor_name": "OfficeProcessor",
            "file_path": "permission_error.pptx", 
            "file_size": 0,
            "file_type": ".pptx",
            "operation": "document_processing"
        }
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_loader_instance.load.side_effect = Exception("permission denied")

        # Create test file
        pptx_file = Path(self.temp_dir) / "permission_error.pptx"
        pptx_file.write_text("dummy content")

        # Test error handling
        with self.assertRaises(Exception) as context:
            self.processor.process_document(pptx_file)

        error_msg = str(context.exception)
        self.assertIn("Error processing office document", error_msg)
        self.assertIn("permission denied", error_msg)
        self.assertIn("Permission denied accessing the .pptx file", error_msg)


class TestOfficeProcessorImportFallback(unittest.TestCase):
    """Test import fallback scenarios."""

    def test_import_fallback_covered(self):
        """Test that import fallback is properly structured."""
        # Verify that the processor can be instantiated
        processor = OfficeProcessor()
        self.assertIsNotNone(processor)
        self.assertEqual(processor.processor_name, "OfficeProcessor")
        
        # Test that logging function is available
        try:
            from rag_store.logging_config import log_processing_error
            self.assertTrue(callable(log_processing_error))
        except ImportError:
            # If relative import fails, absolute should work
            from logging_config import log_processing_error
            self.assertTrue(callable(log_processing_error))


if __name__ == "__main__":
    unittest.main()