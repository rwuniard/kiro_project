"""
Unit tests for store_embeddings module.

This test suite covers the document storage and embedding functionality.
"""

import os
import shutil

# Import the module to test
import sys
import tempfile
import unittest

from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from rag_store.store_embeddings import (
    ModelVendor,
    ChromaClientMode,
    create_chroma_client,
    get_chroma_collection_name,
    get_text_splitter,
    load_embedding_model,
    load_txt_documents,
    process_documents_from_directory,
    process_pdf_files,
    process_text_files,
    ensure_data_directory,
    store_to_chroma,
    load_documents_from_directory,
)


class TestStoreEmbeddings(unittest.TestCase):
    """Test cases for store_embeddings module."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up after each test method."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_model_vendor_enum(self):
        """Test ModelVendor enum values."""
        self.assertEqual(ModelVendor.OPENAI.value, "openai")
        self.assertEqual(ModelVendor.GOOGLE.value, "google")

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key"})
    @patch("rag_store.store_embeddings.GoogleGenerativeAIEmbeddings")
    def test_load_embedding_model_google(self, mock_google):
        """Test loading Google embedding model."""
        mock_model = Mock()
        mock_google.return_value = mock_model

        result = load_embedding_model(ModelVendor.GOOGLE)

        mock_google.assert_called_once_with(
            model="models/text-embedding-004", google_api_key="test_key"
        )
        self.assertEqual(result, mock_model)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
    @patch("rag_store.store_embeddings.OpenAIEmbeddings")
    def test_load_embedding_model_openai(self, mock_openai):
        """Test loading OpenAI embedding model."""
        mock_model = Mock()
        mock_openai.return_value = mock_model

        result = load_embedding_model(ModelVendor.OPENAI)

        mock_openai.assert_called_once()
        self.assertEqual(result, mock_model)

    def test_process_pdf_files_empty_directory(self):
        """Test processing PDF files from empty directory."""
        # Create empty directory
        empty_dir = self.temp_dir_path / "empty"
        empty_dir.mkdir()

        result = process_pdf_files(empty_dir)

        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, list)

    @patch("rag_store.store_embeddings.get_document_processor_registry")
    def test_process_pdf_files_with_pdfs(self, mock_registry_func):
        """Test processing PDF files from directory with PDFs."""
        # Create mock PDF files
        pdf1 = self.temp_dir_path / "test1.pdf"
        pdf2 = self.temp_dir_path / "test2.pdf"
        pdf1.touch()
        pdf2.touch()

        # Mock registry and processor
        mock_registry = Mock()
        mock_registry_func.return_value = mock_registry
        mock_registry.process_document.return_value = [
            Mock(page_content="Test content", metadata={"source": "test1.pdf"})
        ]

        result = process_pdf_files(self.temp_dir_path)

        # Should process both PDF files
        self.assertEqual(mock_registry.process_document.call_count, 2)
        self.assertEqual(len(result), 2)  # 2 PDFs × 1 document each

    def test_process_text_files_empty_directory(self):
        """Test processing text files from empty directory."""
        # Create empty directory
        empty_dir = self.temp_dir_path / "empty"
        empty_dir.mkdir()

        result = process_text_files(empty_dir)

        self.assertEqual(len(result), 0)
        self.assertIsInstance(result, list)

    @patch("rag_store.store_embeddings.get_document_processor_registry")
    def test_process_text_files_with_texts(self, mock_registry_func):
        """Test processing text files from directory with text files."""
        # Create mock text files
        txt1 = self.temp_dir_path / "test1.txt"
        txt2 = self.temp_dir_path / "test2.txt"
        txt1.touch()
        txt2.touch()

        # Mock registry and processor
        mock_registry = Mock()
        mock_registry_func.return_value = mock_registry
        mock_registry.process_document.return_value = [
            Mock(page_content="Test content", metadata={"source": "test.txt"})
        ]

        result = process_text_files(self.temp_dir_path)

        # Should process both text files
        self.assertEqual(mock_registry.process_document.call_count, 2)
        self.assertEqual(len(result), 2)  # 2 text files × 1 document each

    @patch("rag_store.store_embeddings.get_document_processor_registry")
    def test_process_documents_from_directory_unified(self, mock_registry_func):
        """Test the new unified document processing function."""
        # Create mixed file types
        pdf_file = self.temp_dir_path / "test.pdf"
        txt_file = self.temp_dir_path / "test.txt"
        md_file = self.temp_dir_path / "test.md"
        unsupported_file = self.temp_dir_path / "test.xyz"

        pdf_file.touch()
        txt_file.touch()
        md_file.touch()
        unsupported_file.touch()

        # Mock registry
        mock_registry = Mock()
        mock_registry_func.return_value = mock_registry
        mock_registry.get_supported_extensions.return_value = {".pdf", ".txt", ".md"}

        # Mock processor selection
        def mock_get_processor(file_path):
            if file_path.suffix in {".pdf", ".txt", ".md"}:
                return Mock()  # Return a mock processor
            return None

        mock_registry.get_processor_for_file.side_effect = mock_get_processor
        mock_registry.process_document.return_value = [
            Mock(page_content="Test content", metadata={"source": "test.pdf"})
        ]

        result = process_documents_from_directory(self.temp_dir_path)

        # Should process 3 supported files (pdf, txt, md) but not xyz
        self.assertEqual(mock_registry.process_document.call_count, 3)
        self.assertEqual(len(result), 3)  # 3 supported files × 1 document each


class TestStoreEmbeddingsErrorHandling(unittest.TestCase):
    """Test error handling in store_embeddings module."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_process_documents_from_directory_no_processor_found(self):
        """Test process_documents_from_directory when no processor found for file."""
        # Create a file with unsupported extension
        unsupported_file = Path(self.temp_dir) / "test.xyz"
        unsupported_file.write_text("test content")

        # Process should handle the unsupported file gracefully
        documents = process_documents_from_directory(Path(self.temp_dir))
        
        # Should return empty list since no processors support .xyz files
        self.assertEqual(documents, [])

    def test_process_documents_from_directory_processing_error(self):
        """Test process_documents_from_directory when document processing fails."""
        # Create a text file
        text_file = Path(self.temp_dir) / "test.txt"
        text_file.write_text("test content")

        # Mock processor registry to raise an exception
        with patch('rag_store.store_embeddings.get_document_processor_registry') as mock_registry:
            mock_registry_instance = Mock()
            mock_registry.return_value = mock_registry_instance
            
            # Mock processor that raises exception
            mock_processor = Mock()
            mock_processor.file_type_description = "Text files"
            mock_processor.processor_name = "TextProcessor"
            mock_registry_instance.get_processor_for_file.return_value = mock_processor
            mock_registry_instance.process_document.side_effect = Exception("Processing failed")
            mock_registry_instance.get_supported_extensions.return_value = {'.txt'}

            # Process should handle the exception gracefully
            documents = process_documents_from_directory(Path(self.temp_dir))
            
            # Should return empty list due to processing error
            self.assertEqual(documents, [])

    def test_process_documents_from_directory_empty_directory(self):
        """Test process_documents_from_directory with empty directory."""
        # Test with empty directory
        documents = process_documents_from_directory(Path(self.temp_dir))
        
        # Should return empty list and log warning
        self.assertEqual(documents, [])

    def test_load_txt_documents_function(self):
        """Test the legacy load_txt_documents function."""
        # Create a text file
        text_file = Path(self.temp_dir) / "test.txt"
        text_file.write_text("test content")

        # Mock the registry
        with patch('rag_store.store_embeddings.get_document_processor_registry') as mock_registry:
            mock_registry_instance = Mock()
            mock_registry.return_value = mock_registry_instance
            
            # Mock successful processing
            mock_doc = Mock()
            mock_doc.page_content = "test content"
            mock_registry_instance.process_document.return_value = [mock_doc]

            # Test the function
            documents = load_txt_documents(text_file)
            
            # Verify it uses the registry correctly
            mock_registry_instance.process_document.assert_called_once_with(text_file)
            self.assertEqual(len(documents), 1)

    @patch.dict(os.environ, {}, clear=True)
    def test_load_embedding_model_missing_google_key(self):
        """Test load_embedding_model with missing GOOGLE_API_KEY."""
        with self.assertRaises(ValueError) as context:
            load_embedding_model(ModelVendor.GOOGLE)
        
        self.assertIn("GOOGLE_API_KEY environment variable is required", str(context.exception))

    @patch.dict(os.environ, {}, clear=True)
    def test_load_embedding_model_missing_openai_key(self):
        """Test load_embedding_model with missing OPENAI_API_KEY."""
        with self.assertRaises(ValueError) as context:
            load_embedding_model(ModelVendor.OPENAI)
        
        self.assertIn("OPENAI_API_KEY environment variable is required", str(context.exception))

    def test_get_text_splitter_function(self):
        """Test the get_text_splitter function."""
        splitter = get_text_splitter()
        
        # Verify splitter configuration
        self.assertEqual(splitter._chunk_size, 300)
        self.assertEqual(splitter._chunk_overlap, 50)
        self.assertEqual(splitter._separator, "\n")


class TestMainFunction(unittest.TestCase):
    """Test the main function for coverage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    @patch('rag_store.store_embeddings.process_documents_from_directory')
    @patch('rag_store.store_embeddings.store_to_chroma')
    @patch('rag_store.store_embeddings.Path')
    def test_main_function_success(self, mock_path, mock_store_to_chroma, mock_process_docs):
        """Test main function successful execution."""
        from rag_store.store_embeddings import main
        
        # Mock path for data_source directory
        mock_data_source_dir = Mock()
        mock_path.return_value.parent.__truediv__.return_value = mock_data_source_dir
        
        # Mock successful document processing
        mock_doc = Mock()
        mock_doc.page_content = "test content"
        mock_doc.metadata = {"source": "test.txt"}
        mock_process_docs.return_value = [mock_doc]
        
        # Mock vectorstore with search capability
        mock_vectorstore = Mock()
        mock_vectorstore.similarity_search.return_value = [mock_doc, mock_doc]
        mock_store_to_chroma.return_value = mock_vectorstore
        
        # Call main function
        main()
        
        # Verify function calls
        mock_process_docs.assert_called_once()
        mock_store_to_chroma.assert_called_once()
        
        # Verify search calls
        self.assertEqual(mock_vectorstore.similarity_search.call_count, 2)

    @patch('rag_store.store_embeddings.process_documents_from_directory')
    @patch('rag_store.store_embeddings.get_document_processor_registry')
    @patch('rag_store.store_embeddings.Path')
    def test_main_function_no_documents(self, mock_path, mock_get_registry, mock_process_docs):
        """Test main function when no documents found."""
        from rag_store.store_embeddings import main
        
        # Mock path for data_source directory
        mock_data_source_dir = Mock()
        mock_path.return_value.parent.__truediv__.return_value = mock_data_source_dir
        
        # Mock no documents found
        mock_process_docs.return_value = []
        
        # Mock registry for format listing
        mock_registry = Mock()
        mock_processor = Mock()
        mock_processor.file_type_description = "Test files"
        mock_registry.get_all_processors.return_value = {"test": mock_processor}
        mock_get_registry.return_value = mock_registry
        
        # Call main function
        main()
        
        # Verify it handles no documents case
        mock_process_docs.assert_called_once()
        mock_get_registry.assert_called_once()

    @patch('rag_store.store_embeddings.process_documents_from_directory')
    @patch('rag_store.store_embeddings.Path')
    def test_main_function_exception(self, mock_path, mock_process_docs):
        """Test main function exception handling."""
        from rag_store.store_embeddings import main
        
        # Mock path for data_source directory
        mock_data_source_dir = Mock()
        mock_path.return_value.parent.__truediv__.return_value = mock_data_source_dir
        
        # Mock exception during processing
        mock_process_docs.side_effect = Exception("Processing failed")
        
        # Call main function - should not raise exception
        main()
        
        # Verify it attempted processing
        mock_process_docs.assert_called_once()


class TestChromaDBClientCreation(unittest.TestCase):
    """Test ChromaDB client creation functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.persist_dir = Path(self.temp_dir) / "chroma_db"

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_chroma_client_mode_enum(self):
        """Test ChromaClientMode enum values."""
        self.assertEqual(ChromaClientMode.EMBEDDED.value, "embedded")
        self.assertEqual(ChromaClientMode.CLIENT_SERVER.value, "client_server")

    @patch('rag_store.store_embeddings.chromadb.Client')
    def test_create_chroma_client_embedded_with_persistence(self, mock_client_class):
        """Test creating embedded ChromaDB client with persistence."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = create_chroma_client(
            client_mode="embedded",
            persist_directory=self.persist_dir
        )
        
        self.assertEqual(result, mock_client)
        mock_client_class.assert_called_once()

    @patch('rag_store.store_embeddings.chromadb.Client')
    def test_create_chroma_client_embedded_in_memory(self, mock_client_class):
        """Test creating embedded ChromaDB client in memory."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = create_chroma_client(client_mode="embedded")
        
        self.assertEqual(result, mock_client)
        mock_client_class.assert_called_once()

    @patch('rag_store.store_embeddings.chromadb.HttpClient')
    def test_create_chroma_client_server_mode(self, mock_http_client_class):
        """Test creating ChromaDB client in server mode."""
        mock_client = Mock()
        mock_http_client_class.return_value = mock_client
        
        result = create_chroma_client(
            client_mode="client_server",
            server_host="test-host",
            server_port=9000
        )
        
        self.assertEqual(result, mock_client)
        mock_http_client_class.assert_called_once_with(host="test-host", port=9000)

    def test_create_chroma_client_invalid_mode(self):
        """Test creating ChromaDB client with invalid mode."""
        with self.assertRaises(ValueError) as context:
            create_chroma_client(client_mode="invalid_mode")
        
        self.assertIn("Invalid client mode: invalid_mode", str(context.exception))

    def test_get_chroma_collection_name_custom(self):
        """Test getting ChromaDB collection name with custom name."""
        result = get_chroma_collection_name(ModelVendor.OPENAI, "custom_collection")
        self.assertEqual(result, "custom_collection")

    def test_get_chroma_collection_name_openai_default(self):
        """Test getting default ChromaDB collection name for OpenAI."""
        result = get_chroma_collection_name(ModelVendor.OPENAI)
        self.assertEqual(result, "documents_openai")

    def test_get_chroma_collection_name_google_default(self):
        """Test getting default ChromaDB collection name for Google."""
        result = get_chroma_collection_name(ModelVendor.GOOGLE)
        self.assertEqual(result, "documents_google")

    def test_ensure_data_directory_openai(self):
        """Test ensuring data directory for OpenAI."""
        with patch('rag_store.store_embeddings.DATA_DIR', Path(self.temp_dir)):
            result = ensure_data_directory(ModelVendor.OPENAI)
            expected_path = Path(self.temp_dir) / "chroma_db_openai"
            self.assertEqual(result, expected_path)
            self.assertTrue(expected_path.exists())

    def test_ensure_data_directory_google(self):
        """Test ensuring data directory for Google."""
        with patch('rag_store.store_embeddings.DATA_DIR', Path(self.temp_dir)):
            result = ensure_data_directory(ModelVendor.GOOGLE)
            expected_path = Path(self.temp_dir) / "chroma_db_google"
            self.assertEqual(result, expected_path)
            self.assertTrue(expected_path.exists())


class TestStoreToChroma(unittest.TestCase):
    """Test store_to_chroma functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.persist_dir = Path(self.temp_dir) / "chroma_db"
        self.mock_docs = [
            Mock(page_content="Test content 1", metadata={"source": "test1.txt"}),
            Mock(page_content="Test content 2", metadata={"source": "test2.txt"})
        ]

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    @patch('rag_store.store_embeddings.Chroma.from_documents')
    @patch('rag_store.store_embeddings.load_embedding_model')
    @patch('rag_store.store_embeddings.ensure_data_directory')
    def test_store_to_chroma_embedded_mode(self, mock_ensure_dir, mock_load_model, mock_chroma):
        """Test storing documents to ChromaDB in embedded mode."""
        # Mock setup
        mock_embedding = Mock()
        mock_load_model.return_value = mock_embedding
        mock_ensure_dir.return_value = self.persist_dir
        mock_vectorstore = Mock()
        mock_chroma.return_value = mock_vectorstore
        
        # Call function
        result = store_to_chroma(
            documents=self.mock_docs,
            model_vendor=ModelVendor.GOOGLE,
            client_mode="embedded"
        )
        
        # Assertions
        self.assertEqual(result, mock_vectorstore)
        mock_load_model.assert_called_once_with(ModelVendor.GOOGLE)
        mock_ensure_dir.assert_called_once_with(ModelVendor.GOOGLE)
        mock_chroma.assert_called_once_with(
            documents=self.mock_docs,
            embedding=mock_embedding,
            persist_directory=str(self.persist_dir),
            collection_name="documents_google"
        )

    @patch('rag_store.store_embeddings.Chroma.from_documents')
    @patch('rag_store.store_embeddings.load_embedding_model')
    @patch('rag_store.store_embeddings.create_chroma_client')
    def test_store_to_chroma_client_server_mode(self, mock_create_client, mock_load_model, mock_chroma):
        """Test storing documents to ChromaDB in client-server mode."""
        # Mock setup
        mock_embedding = Mock()
        mock_load_model.return_value = mock_embedding
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_vectorstore = Mock()
        mock_chroma.return_value = mock_vectorstore
        
        # Call function
        result = store_to_chroma(
            documents=self.mock_docs,
            model_vendor=ModelVendor.OPENAI,
            client_mode="client_server",
            server_host="test-host",
            server_port=9000,
            collection_name="test_collection"
        )
        
        # Assertions
        self.assertEqual(result, mock_vectorstore)
        mock_load_model.assert_called_once_with(ModelVendor.OPENAI)
        mock_create_client.assert_called_once_with(
            client_mode="client_server",
            server_host="test-host",
            server_port=9000
        )
        mock_chroma.assert_called_once_with(
            documents=self.mock_docs,
            embedding=mock_embedding,
            client=mock_client,
            collection_name="test_collection"
        )

    @patch('rag_store.store_embeddings.load_embedding_model')
    def test_store_to_chroma_invalid_mode(self, mock_load_model):
        """Test store_to_chroma with invalid client mode."""
        mock_load_model.return_value = Mock()
        
        with self.assertRaises(ValueError) as context:
            store_to_chroma(
                documents=self.mock_docs,
                model_vendor=ModelVendor.GOOGLE,
                client_mode="invalid_mode"
            )
        
        self.assertIn("Invalid client mode: invalid_mode", str(context.exception))

    @patch('rag_store.store_embeddings.Chroma.from_documents')
    @patch('rag_store.store_embeddings.load_embedding_model')
    def test_store_to_chroma_with_custom_persist_directory(self, mock_load_model, mock_chroma):
        """Test store_to_chroma with custom persist directory."""
        mock_embedding = Mock()
        mock_load_model.return_value = mock_embedding
        mock_vectorstore = Mock()
        mock_chroma.return_value = mock_vectorstore
        custom_dir = Path(self.temp_dir) / "custom_chroma"
        
        result = store_to_chroma(
            documents=self.mock_docs,
            model_vendor=ModelVendor.GOOGLE,
            client_mode="embedded",
            persist_directory=custom_dir
        )
        
        self.assertEqual(result, mock_vectorstore)
        mock_chroma.assert_called_once_with(
            documents=self.mock_docs,
            embedding=mock_embedding,
            persist_directory=str(custom_dir),
            collection_name="documents_google"
        )


class TestAdditionalFunctions(unittest.TestCase):
    """Test additional functions for improved coverage."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_load_documents_from_directory_legacy_function(self):
        """Test the legacy load_documents_from_directory function."""
        with patch('rag_store.store_embeddings.process_documents_from_directory') as mock_process:
            mock_docs = [Mock(page_content="test", metadata={"source": "test.txt"})]
            mock_process.return_value = mock_docs
            
            result = load_documents_from_directory(Path(self.temp_dir))
            
            mock_process.assert_called_once_with(Path(self.temp_dir))
            self.assertEqual(result, mock_docs)

    def test_process_documents_from_directory_file_not_found(self):
        """Test process_documents_from_directory with non-existent directory."""
        non_existent_dir = Path(self.temp_dir) / "nonexistent"
        
        with self.assertRaises(FileNotFoundError) as context:
            process_documents_from_directory(non_existent_dir)
        
        self.assertIn(str(non_existent_dir), str(context.exception))

    @patch('rag_store.store_embeddings.get_document_processor_registry')
    def test_process_text_files_processing_error(self, mock_registry_func):
        """Test process_text_files with processing error."""
        # Create text file
        txt_file = Path(self.temp_dir) / "test.txt"
        txt_file.write_text("test content")
        
        # Mock registry to raise exception
        mock_registry = Mock()
        mock_registry_func.return_value = mock_registry
        mock_registry.process_document.side_effect = Exception("Processing error")
        
        result = process_text_files(Path(self.temp_dir))
        
        # Should return empty list due to error
        self.assertEqual(result, [])
        mock_registry.process_document.assert_called_once()

    @patch('rag_store.store_embeddings.get_document_processor_registry')
    def test_process_pdf_files_processing_error(self, mock_registry_func):
        """Test process_pdf_files with processing error."""
        # Create PDF file
        pdf_file = Path(self.temp_dir) / "test.pdf"
        pdf_file.write_bytes(b"fake pdf content")
        
        # Mock registry to raise exception
        mock_registry = Mock()
        mock_registry_func.return_value = mock_registry
        mock_registry.process_document.side_effect = Exception("PDF processing error")
        
        result = process_pdf_files(Path(self.temp_dir))
        
        # Should return empty list due to error
        self.assertEqual(result, [])
        mock_registry.process_document.assert_called_once()

    @patch('rag_store.store_embeddings.get_document_processor_registry')
    def test_process_documents_from_directory_no_processor_returned(self, mock_registry_func):
        """Test process_documents_from_directory when processor returns None."""
        # Create a file
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        # Mock registry
        mock_registry = Mock()
        mock_registry_func.return_value = mock_registry
        mock_registry.get_supported_extensions.return_value = {'.txt'}
        mock_registry.get_processor_for_file.return_value = None  # No processor found
        
        result = process_documents_from_directory(Path(self.temp_dir))
        
        # Should return empty list
        self.assertEqual(result, [])
        mock_registry.get_processor_for_file.assert_called_once()


class TestStoreEmbeddingsIntegration(unittest.TestCase):
    """Integration tests for store_embeddings functionality."""

    def test_model_vendor_integration(self):
        """Test that ModelVendor enum works with actual functions."""
        # This test verifies the enum can be used with the functions
        vendors = [ModelVendor.GOOGLE, ModelVendor.OPENAI]

        for vendor in vendors:
            self.assertIn(vendor.value, ["google", "openai"])
            self.assertIsInstance(vendor, ModelVendor)


if __name__ == "__main__":
    unittest.main(verbosity=2)
