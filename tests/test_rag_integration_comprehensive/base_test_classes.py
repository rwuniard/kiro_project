"""
Base test classes and fixtures for RAG integration testing.

This module provides common test infrastructure including base test classes,
fixtures, mocks, and utilities for comprehensive RAG integration testing.
"""

import os
import sys
import time
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Set
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.document_processing import (
    DocumentProcessingInterface,
    ProcessingResult,
    DocumentProcessingError
)


@dataclass
class FileFixture:
    """Test file fixture with metadata."""
    name: str
    content: str
    extension: str
    expected_success: bool
    expected_chunks: int = 0
    file_size: Optional[int] = None
    
    @property
    def filename(self) -> str:
        """Get full filename with extension."""
        return f"{self.name}.{self.extension}"


class MockDocumentProcessor(DocumentProcessingInterface):
    """Mock document processor for testing."""
    
    def __init__(self, 
                 supported_extensions: Optional[Set[str]] = None,
                 should_fail: bool = False,
                 fail_on_files: Optional[Set[str]] = None,
                 processing_delay: float = 0.0):
        """
        Initialize mock processor.
        
        Args:
            supported_extensions: Set of supported extensions (default: {'.txt', '.pdf', '.docx'})
            should_fail: Whether all processing should fail
            fail_on_files: Specific files that should fail processing
            processing_delay: Delay to simulate processing time
        """
        self.supported_extensions = supported_extensions or {'.txt', '.pdf', '.docx', '.md'}
        self.should_fail = should_fail
        self.fail_on_files = fail_on_files or set()
        self.processing_delay = processing_delay
        self.initialized = False
        self.initialization_config = {}
        self.processed_files = []
        self.cleanup_called = False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Mock initialization."""
        self.initialization_config = config.copy()
        
        # Simulate initialization failure if requested
        if config.get('force_init_failure', False):
            raise Exception("Forced initialization failure")
        
        self.initialized = True
        return True
    
    def is_supported_file(self, file_path: Path) -> bool:
        """Check if file is supported."""
        return file_path.suffix.lower() in self.supported_extensions
    
    def process_document(self, file_path: Path) -> ProcessingResult:
        """Mock document processing."""
        if not self.initialized:
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                processor_used="MockDocumentProcessor",
                error_message="Processor not initialized",
                error_type="initialization_error"
            )
        
        # Add processing delay if specified
        if self.processing_delay > 0:
            time.sleep(self.processing_delay)
        
        # Track processed files
        self.processed_files.append(str(file_path))
        
        # Check if this file should fail
        should_fail = (
            self.should_fail or 
            file_path.name in self.fail_on_files or
            str(file_path) in self.fail_on_files
        )
        
        if should_fail:
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                processor_used="MockDocumentProcessor",
                error_message=f"Mock processing failure for {file_path.name}",
                error_type="mock_processing_error",
                processing_time=self.processing_delay,
                metadata={
                    "file_size": file_path.stat().st_size if file_path.exists() else 0,
                    "file_extension": file_path.suffix
                }
            )
        
        # Simulate successful processing
        file_size = file_path.stat().st_size if file_path.exists() else 0
        chunks_created = max(1, file_size // 100)  # Simulate chunk creation based on file size
        
        return ProcessingResult(
            success=True,
            file_path=str(file_path),
            processor_used="MockDocumentProcessor",
            chunks_created=chunks_created,
            processing_time=self.processing_delay,
            metadata={
                "file_size": file_size,
                "file_extension": file_path.suffix,
                "mock_processor": True
            }
        )
    
    def get_supported_extensions(self) -> Set[str]:
        """Get supported extensions."""
        return self.supported_extensions.copy()
    
    def cleanup(self) -> None:
        """Mock cleanup."""
        self.cleanup_called = True
        self.initialized = False
        self.processed_files.clear()
    
    def get_processor_name(self) -> str:
        """Get processor name."""
        return "MockDocumentProcessor"


class BaseRAGIntegrationTest:
    """Base class for RAG integration tests."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        import uuid
        
        # Create unique temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_rag_integration_{uuid.uuid4().hex[:8]}_")
        self.source_dir = Path(self.temp_dir) / "source"
        self.saved_dir = Path(self.temp_dir) / "saved"
        self.error_dir = Path(self.temp_dir) / "error"
        self.logs_dir = Path(self.temp_dir) / "logs"
        
        # Create directories
        for dir_path in [self.source_dir, self.saved_dir, self.error_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            assert dir_path.exists(), f"Failed to create directory: {dir_path}"
        
        # Create .env file for testing
        self.env_file = Path(self.temp_dir) / ".env"
        self.log_file = self.logs_dir / "test.log"
        
        # Initialize app reference for cleanup
        self.app = None
        self.mock_processor = None
        
        # Store original environment variables for restoration
        self.original_env_vars = {}
        env_vars_to_backup = [
            'SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER',
            'GOOGLE_API_KEY', 'OPENAI_API_KEY', 'ENABLE_DOCUMENT_PROCESSING'
        ]
        for var in env_vars_to_backup:
            if var in os.environ:
                self.original_env_vars[var] = os.environ[var]
    
    def teardown_method(self):
        """Clean up after each test."""
        import shutil
        
        # Shutdown app if running
        if hasattr(self, 'app') and self.app:
            try:
                if hasattr(self.app, 'file_monitor') and self.app.file_monitor:
                    self.app.file_monitor.stop_monitoring()
                if hasattr(self.app, 'shutdown'):
                    self.app.shutdown()
            except Exception:
                pass
        
        # Cleanup mock processor
        if hasattr(self, 'mock_processor') and self.mock_processor:
            try:
                self.mock_processor.cleanup()
            except Exception:
                pass
        
        # Restore original environment variables
        for var, value in self.original_env_vars.items():
            os.environ[var] = value
        
        # Remove any environment variables that weren't originally set
        env_vars_to_clean = [
            'SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER',
            'GOOGLE_API_KEY', 'OPENAI_API_KEY', 'ENABLE_DOCUMENT_PROCESSING'
        ]
        for var in env_vars_to_clean:
            if var not in self.original_env_vars and var in os.environ:
                del os.environ[var]
        
        # Small delay to ensure file handles are released
        time.sleep(0.1)
        
        # Clean up temporary directory
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory {self.temp_dir}: {e}")
    
    def create_env_file(self, enable_document_processing: bool = True, **extra_vars):
        """Create .env file with standard configuration."""
        with open(self.env_file, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write(f"ENABLE_DOCUMENT_PROCESSING={str(enable_document_processing).lower()}\n")
            
            # Add extra variables
            for key, value in extra_vars.items():
                f.write(f"{key}={value}\n")
    
    def create_test_file(self, fixture: FileFixture, directory: Optional[Path] = None) -> Path:
        """Create a test file from fixture."""
        target_dir = directory or self.source_dir
        file_path = target_dir / fixture.filename
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        file_path.write_text(fixture.content)
        
        return file_path
    
    def create_test_files(self, fixtures: list[FileFixture], directory: Optional[Path] = None) -> list[Path]:
        """Create multiple test files from fixtures."""
        return [self.create_test_file(fixture, directory) for fixture in fixtures]
    
    def get_standard_test_fixtures(self) -> list[FileFixture]:
        """Get standard set of test file fixtures."""
        return [
            FileFixture(
                name="simple_text",
                content="This is a simple text file for testing.",
                extension="txt",
                expected_success=True,
                expected_chunks=1
            ),
            FileFixture(
                name="markdown_doc",
                content="# Test Document\n\nThis is a markdown document with **bold** text.",
                extension="md",
                expected_success=True,
                expected_chunks=1
            ),
            FileFixture(
                name="large_text",
                content="Large content. " * 1000,  # Create larger content
                extension="txt",
                expected_success=True,
                expected_chunks=10
            ),
            FileFixture(
                name="empty_file",
                content="",
                extension="txt",
                expected_success=False,
                expected_chunks=0
            ),
            FileFixture(
                name="unsupported_file",
                content="Binary content",
                extension="bin",
                expected_success=False,
                expected_chunks=0
            )
        ]
    
    def wait_for_file_processing(self, timeout: float = 5.0) -> None:
        """Wait for file processing to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if source directory is empty (all files processed)
            if not any(self.source_dir.rglob("*")):
                break
            time.sleep(0.1)
    
    def assert_file_moved_to_saved(self, filename: str, preserve_structure: bool = False):
        """Assert that a file was moved to the saved directory."""
        if preserve_structure:
            # Look for file anywhere in saved directory tree
            saved_files = list(self.saved_dir.rglob(filename))
            assert len(saved_files) > 0, f"File {filename} not found in saved directory tree"
        else:
            saved_file = self.saved_dir / filename
            assert saved_file.exists(), f"File {filename} not found in saved directory: {saved_file}"
    
    def assert_file_moved_to_error(self, filename: str, preserve_structure: bool = False):
        """Assert that a file was moved to the error directory."""
        if preserve_structure:
            # Look for file anywhere in error directory tree
            error_files = list(self.error_dir.rglob(filename))
            assert len(error_files) > 0, f"File {filename} not found in error directory tree"
        else:
            error_file = self.error_dir / filename
            assert error_file.exists(), f"File {filename} not found in error directory: {error_file}"
    
    def assert_error_log_created(self, filename: str, preserve_structure: bool = False):
        """Assert that an error log was created for a file."""
        log_filename = f"{filename}.log"
        if preserve_structure:
            # Look for log anywhere in error directory tree
            log_files = list(self.error_dir.rglob(log_filename))
            assert len(log_files) > 0, f"Error log {log_filename} not found in error directory tree"
        else:
            log_file = self.error_dir / log_filename
            assert log_file.exists(), f"Error log {log_filename} not found in error directory: {log_file}"
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics from the app."""
        if not self.app or not hasattr(self.app, 'file_processor'):
            return {}
        
        try:
            return self.app.file_processor.get_processing_stats()
        except Exception:
            return {}
    
    def create_nested_directory_structure(self) -> Dict[str, Path]:
        """Create nested directory structure for testing."""
        structure = {
            'documents': self.source_dir / "documents",
            'reports': self.source_dir / "documents" / "reports",
            'images': self.source_dir / "images",
            'temp': self.source_dir / "temp"
        }
        
        for path in structure.values():
            path.mkdir(parents=True, exist_ok=True)
        
        return structure


class MockRAGStoreComponents:
    """Mock RAG store components for testing."""
    
    @staticmethod
    def mock_processor_registry():
        """Create mock ProcessorRegistry."""
        mock_registry = Mock()
        mock_registry.get_supported_extensions.return_value = {'.txt', '.pdf', '.docx', '.md'}
        mock_registry.get_all_processors.return_value = {
            'TextProcessor': Mock(),
            'PDFProcessor': Mock(),
            'WordProcessor': Mock()
        }
        
        def mock_get_processor_for_file(file_path):
            if file_path.suffix.lower() in {'.txt', '.md'}:
                processor = Mock()
                processor.processor_name = 'TextProcessor'
                return processor
            elif file_path.suffix.lower() == '.pdf':
                processor = Mock()
                processor.processor_name = 'PDFProcessor'
                return processor
            elif file_path.suffix.lower() in {'.docx', '.doc'}:
                processor = Mock()
                processor.processor_name = 'WordProcessor'
                return processor
            return None
        
        mock_registry.get_processor_for_file = mock_get_processor_for_file
        
        def mock_process_document(file_path):
            # Simulate document processing
            content = file_path.read_text() if file_path.exists() else ""
            if not content.strip():
                return []  # Empty document
            
            # Create mock documents (chunks)
            chunks = []
            chunk_size = 100
            for i in range(0, len(content), chunk_size):
                chunk = Mock()
                chunk.page_content = content[i:i+chunk_size]
                chunk.metadata = {
                    'source': str(file_path),
                    'chunk_index': len(chunks)
                }
                chunks.append(chunk)
            
            return chunks
        
        mock_registry.process_document = mock_process_document
        return mock_registry
    
    @staticmethod
    def mock_embedding_model():
        """Create mock embedding model."""
        mock_model = Mock()
        mock_model.embed_documents.return_value = [[0.1, 0.2, 0.3]] * 10  # Mock embeddings
        return mock_model
    
    @staticmethod
    def mock_chroma_vectorstore():
        """Create mock ChromaDB vectorstore."""
        mock_vectorstore = Mock()
        mock_vectorstore.add_documents.return_value = None
        return mock_vectorstore


class IntegrationTestFixtures:
    """Common test fixtures for integration testing."""
    
    @staticmethod
    def get_performance_test_fixtures() -> list[FileFixture]:
        """Get fixtures for performance testing."""
        return [
            FileFixture(
                name="small_file",
                content="Small file content.",
                extension="txt",
                expected_success=True,
                expected_chunks=1
            ),
            FileFixture(
                name="medium_file",
                content="Medium file content. " * 500,
                extension="txt",
                expected_success=True,
                expected_chunks=5
            ),
            FileFixture(
                name="large_file",
                content="Large file content. " * 5000,
                extension="txt",
                expected_success=True,
                expected_chunks=50
            )
        ]
    
    @staticmethod
    def get_error_test_fixtures() -> list[FileFixture]:
        """Get fixtures for error testing."""
        return [
            FileFixture(
                name="empty_file",
                content="",
                extension="txt",
                expected_success=False
            ),
            FileFixture(
                name="unsupported_type",
                content="Binary content",
                extension="bin",
                expected_success=False
            ),
            FileFixture(
                name="permission_test",
                content="Test content",
                extension="txt",
                expected_success=True  # Will be modified in test
            )
        ]
    
    @staticmethod
    def get_mixed_file_fixtures() -> list[FileFixture]:
        """Get mixed success/failure fixtures."""
        return [
            FileFixture(
                name="success_1",
                content="Successful file 1",
                extension="txt",
                expected_success=True
            ),
            FileFixture(
                name="success_2",
                content="Successful file 2",
                extension="md",
                expected_success=True
            ),
            FileFixture(
                name="failure_1",
                content="",
                extension="txt",
                expected_success=False
            ),
            FileFixture(
                name="failure_2",
                content="Binary",
                extension="bin",
                expected_success=False
            )
        ]


# Pytest fixtures for common use
@pytest.fixture
def temp_test_environment():
    """Pytest fixture for temporary test environment."""
    base_test = BaseRAGIntegrationTest()
    base_test.setup_method()
    
    yield base_test
    
    base_test.teardown_method()


@pytest.fixture
def mock_document_processor():
    """Pytest fixture for mock document processor."""
    processor = MockDocumentProcessor()
    yield processor
    processor.cleanup()


@pytest.fixture
def standard_test_files(temp_test_environment):
    """Pytest fixture for standard test files."""
    fixtures = temp_test_environment.get_standard_test_fixtures()
    file_paths = temp_test_environment.create_test_files(fixtures)
    return list(zip(fixtures, file_paths))