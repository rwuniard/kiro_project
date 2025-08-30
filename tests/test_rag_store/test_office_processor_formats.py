"""
Extended tests for OfficeProcessor format-specific functionality.

This test suite focuses on format-specific behavior for PowerPoint, Excel,
OpenDocument formats, and eBooks that were added in the unified processor.
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


class TestOfficeProcessorFormats(unittest.TestCase):
    """Test format-specific behavior for various office document types."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.processor = OfficeProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test method."""
        shutil.rmtree(self.temp_dir)

    def test_powerpoint_format_configuration(self):
        """Test PowerPoint-specific format configuration."""
        ppt_file = Path(self.temp_dir) / "presentation.pptx"
        
        # Test chunk configuration
        chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=ppt_file)
        self.assertEqual(chunk_size, 800)
        self.assertEqual(chunk_overlap, 120)
        
        # Test separators
        separators = self.processor._get_separators_for_format(ppt_file)
        self.assertEqual(separators[0], "\n\n\n")  # Slide breaks are first priority
        
        # Test description
        description = self.processor._get_document_format_description(ppt_file)
        self.assertEqual(description, "Microsoft PowerPoint")
        
        # Test legacy .ppt format
        legacy_ppt = Path(self.temp_dir) / "old_presentation.ppt"
        description = self.processor._get_document_format_description(legacy_ppt)
        self.assertEqual(description, "Microsoft PowerPoint (Legacy)")

    def test_excel_format_configuration(self):
        """Test Excel-specific format configuration."""
        xlsx_file = Path(self.temp_dir) / "spreadsheet.xlsx"
        
        # Test chunk configuration
        chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=xlsx_file)
        self.assertEqual(chunk_size, 1200)
        self.assertEqual(chunk_overlap, 180)
        
        # Test separators (should include tab for table structure)
        separators = self.processor._get_separators_for_format(xlsx_file)
        self.assertIn("\t", separators)
        
        # Test description
        description = self.processor._get_document_format_description(xlsx_file)
        self.assertEqual(description, "Microsoft Excel")
        
        # Test legacy .xls format
        legacy_xls = Path(self.temp_dir) / "old_spreadsheet.xls"
        description = self.processor._get_document_format_description(legacy_xls)
        self.assertEqual(description, "Microsoft Excel (Legacy)")

    def test_opendocument_formats(self):
        """Test OpenDocument format configurations."""
        # Test ODT (OpenDocument Text) - similar to Word
        odt_file = Path(self.temp_dir) / "document.odt"
        chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=odt_file)
        self.assertEqual(chunk_size, 1000)
        self.assertEqual(chunk_overlap, 150)
        
        description = self.processor._get_document_format_description(odt_file)
        self.assertEqual(description, "OpenDocument Text")
        
        # Test ODP (OpenDocument Presentation) - similar to PowerPoint
        odp_file = Path(self.temp_dir) / "presentation.odp"
        chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=odp_file)
        self.assertEqual(chunk_size, 800)
        self.assertEqual(chunk_overlap, 120)
        
        description = self.processor._get_document_format_description(odp_file)
        self.assertEqual(description, "OpenDocument Presentation")
        
        # Test ODS (OpenDocument Spreadsheet) - similar to Excel
        ods_file = Path(self.temp_dir) / "spreadsheet.ods"
        chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=ods_file)
        self.assertEqual(chunk_size, 1200)
        self.assertEqual(chunk_overlap, 180)
        
        description = self.processor._get_document_format_description(ods_file)
        self.assertEqual(description, "OpenDocument Spreadsheet")

    def test_epub_format_configuration(self):
        """Test eBook (EPUB) format configuration."""
        epub_file = Path(self.temp_dir) / "book.epub"
        
        # Test chunk configuration
        chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=epub_file)
        self.assertEqual(chunk_size, 1000)
        self.assertEqual(chunk_overlap, 150)
        
        # Test separators (should include chapter breaks)
        separators = self.processor._get_separators_for_format(epub_file)
        self.assertEqual(separators[0], "\n\n\n")  # Chapter breaks are first priority
        
        # Test description
        description = self.processor._get_document_format_description(epub_file)
        self.assertEqual(description, "Electronic Publication")

    def test_web_archive_formats(self):
        """Test web archive format configurations."""
        # Test MHT format
        mht_file = Path(self.temp_dir) / "webpage.mht"
        chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=mht_file)
        self.assertEqual(chunk_size, 1200)
        self.assertEqual(chunk_overlap, 180)
        
        description = self.processor._get_document_format_description(mht_file)
        self.assertEqual(description, "Web Archive (MHT)")
        
        # Test MHTML format
        mhtml_file = Path(self.temp_dir) / "webpage.mhtml"
        description = self.processor._get_document_format_description(mhtml_file)
        self.assertEqual(description, "Web Archive (MHTML)")

    def test_all_supported_extensions_covered(self):
        """Test that all supported extensions have proper configuration."""
        expected_extensions = {
            ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
            ".odt", ".odp", ".ods", ".rtf", ".mht", ".mhtml", ".epub"
        }
        
        # Verify all extensions are in supported_extensions
        self.assertEqual(self.processor.supported_extensions, expected_extensions)
        
        # Verify all extensions have chunk configurations (except .rtf which uses default)
        for ext in expected_extensions:
            if ext != ".rtf":  # RTF uses default parameters
                self.assertIn(ext, self.processor.format_chunk_configs)
        
        # Verify all extensions produce valid descriptions
        for ext in expected_extensions:
            test_file = Path(self.temp_dir) / f"test{ext}"
            description = self.processor._get_document_format_description(test_file)
            self.assertIsInstance(description, str)
            self.assertGreater(len(description), 0)

    @patch("rag_store.office_processor.RecursiveCharacterTextSplitter")
    @patch("rag_store.office_processor.UnstructuredLoader")
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_document_processing_complete")
    def test_process_powerpoint_document(
        self, mock_log_complete, mock_log_start, mock_loader_class, mock_splitter_class
    ):
        """Test PowerPoint document processing with format-specific metadata."""
        # Setup mocks
        mock_log_start.return_value = {"context": "test"}
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_splitter_instance = Mock()
        mock_splitter_class.return_value = mock_splitter_instance

        mock_doc = Document(
            page_content="Slide 1: Title\nSlide 2: Content",
            metadata={"source": "test.pptx"},
        )
        
        raw_doc = Document(
            page_content="Full presentation", metadata={"source": "test.pptx"}
        )
        mock_loader_instance.load.return_value = [raw_doc]
        mock_splitter_instance.split_documents.return_value = [mock_doc]

        # Create test file
        pptx_file = Path(self.temp_dir) / "test.pptx"
        pptx_file.write_text("dummy presentation content")

        # Process document
        documents = self.processor.process_document(pptx_file)

        # Verify PowerPoint-specific results
        self.assertEqual(len(documents), 1)
        doc = documents[0]
        
        # Check PowerPoint-specific metadata
        self.assertEqual(doc.metadata["document_format"], "Microsoft PowerPoint")
        self.assertEqual(doc.metadata["chunk_size"], 800)  # PowerPoint default
        self.assertEqual(doc.metadata["chunk_overlap"], 120)  # PowerPoint default
        self.assertEqual(doc.metadata["document_id"], "test_office")
        self.assertEqual(doc.metadata["processor_version"], "unified_office_processor")
        self.assertEqual(doc.metadata["supports_all_office_formats"], True)

        # Verify loader was configured for elements mode
        mock_loader_class.assert_called_once()
        call_kwargs = mock_loader_class.call_args[1]
        self.assertEqual(call_kwargs["mode"], "elements")
        self.assertEqual(call_kwargs["strategy"], "fast")

    @patch("rag_store.office_processor.RecursiveCharacterTextSplitter")
    @patch("rag_store.office_processor.UnstructuredLoader") 
    @patch("rag_store.office_processor.log_document_processing_start")
    @patch("rag_store.office_processor.log_document_processing_complete")
    def test_process_excel_document(
        self, mock_log_complete, mock_log_start, mock_loader_class, mock_splitter_class
    ):
        """Test Excel document processing with format-specific parameters."""
        # Setup mocks
        mock_log_start.return_value = {"context": "test"}
        mock_loader_instance = Mock()
        mock_loader_class.return_value = mock_loader_instance
        mock_splitter_instance = Mock()
        mock_splitter_class.return_value = mock_splitter_instance

        mock_doc = Document(
            page_content="Sheet1: Data\nColumn1\tColumn2\nValue1\tValue2",
            metadata={"source": "test.xlsx"},
        )
        
        raw_doc = Document(
            page_content="Full spreadsheet", metadata={"source": "test.xlsx"}
        )
        mock_loader_instance.load.return_value = [raw_doc]
        mock_splitter_instance.split_documents.return_value = [mock_doc]

        # Create test file
        xlsx_file = Path(self.temp_dir) / "test.xlsx"
        xlsx_file.write_text("dummy spreadsheet content")

        # Process document
        documents = self.processor.process_document(xlsx_file)

        # Verify Excel-specific results
        self.assertEqual(len(documents), 1)
        doc = documents[0]
        
        # Check Excel-specific metadata
        self.assertEqual(doc.metadata["document_format"], "Microsoft Excel")
        self.assertEqual(doc.metadata["chunk_size"], 1200)  # Excel default
        self.assertEqual(doc.metadata["chunk_overlap"], 180)  # Excel default

        # Verify the text splitter was configured with Excel-specific separators
        mock_splitter_class.assert_called_once()
        call_kwargs = mock_splitter_class.call_args[1]
        separators = call_kwargs["separators"]
        self.assertIn("\t", separators)  # Tab separator for Excel tables

    def test_format_specific_error_messages(self):
        """Test that error messages are format-specific."""
        test_files = [
            ("test.pptx", ".pptx"),
            ("test.xlsx", ".xlsx"),
            ("test.odt", ".odt")
        ]
        
        for filename, extension in test_files:
            with self.subTest(filename=filename):
                # Create test file
                test_file = Path(self.temp_dir) / filename
                test_file.write_text("dummy content")
                
                with patch("rag_store.office_processor.UnstructuredLoader") as mock_loader_class:
                    mock_loader_instance = Mock()
                    mock_loader_class.return_value = mock_loader_instance
                    mock_loader_instance.load.side_effect = Exception("format error")
                    
                    with patch("rag_store.office_processor.log_document_processing_start") as mock_log_start:
                        mock_log_start.return_value = {
                            "processor_name": "OfficeProcessor",
                            "file_path": str(test_file),
                            "file_size": 0,
                            "file_type": extension,
                            "operation": "document_processing"
                        }
                        
                        with self.assertRaises(Exception) as context:
                            self.processor.process_document(test_file)
                        
                        error_msg = str(context.exception)
                        self.assertIn(f"Error processing office document {test_file}", error_msg)
                        self.assertIn("format error", error_msg)


class TestOfficeProcessorPerformance(unittest.TestCase):
    """Test performance-related aspects of format-specific processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = OfficeProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_format_chunk_config_lookup_performance(self):
        """Test that format configuration lookup is efficient."""
        # Test with all supported formats
        test_files = [
            ("test.docx", 1000, 150),
            ("test.pptx", 800, 120),
            ("test.xlsx", 1200, 180),
            ("test.odt", 1000, 150),
            ("test.odp", 800, 120),
            ("test.ods", 1200, 180),
            ("test.rtf", 800, 120),
            ("test.mht", 1200, 180),
            ("test.epub", 1000, 150)
        ]
        
        for filename, expected_chunk, expected_overlap in test_files:
            with self.subTest(filename=filename):
                test_file = Path(self.temp_dir) / filename
                
                # This should be a fast lookup
                chunk_size, chunk_overlap = self.processor.get_processing_params(file_path=test_file)
                
                self.assertEqual(chunk_size, expected_chunk)
                self.assertEqual(chunk_overlap, expected_overlap)

    def test_separator_configuration_consistency(self):
        """Test that separator configurations are consistent and logical."""
        # PowerPoint and eBook should have chapter/slide breaks
        for ext in [".pptx", ".ppt", ".odp", ".epub"]:
            test_file = Path(self.temp_dir) / f"test{ext}"
            separators = self.processor._get_separators_for_format(test_file)
            self.assertEqual(separators[0], "\n\n\n", f"Failed for {ext}")
        
        # Excel and ODS should have tab separators
        for ext in [".xlsx", ".xls", ".ods"]:
            test_file = Path(self.temp_dir) / f"test{ext}"
            separators = self.processor._get_separators_for_format(test_file)
            self.assertIn("\t", separators, f"Failed for {ext}")
        
        # Web archives should have HTML-friendly separators
        for ext in [".mht", ".mhtml"]:
            test_file = Path(self.temp_dir) / f"test{ext}"
            separators = self.processor._get_separators_for_format(test_file)
            self.assertEqual(separators, ["\n\n", "\n", ". ", " ", ""], f"Failed for {ext}")


if __name__ == "__main__":
    unittest.main()