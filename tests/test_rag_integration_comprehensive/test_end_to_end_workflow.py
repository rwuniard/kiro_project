"""
End-to-end integration tests for document processing workflow.

This module tests the complete file processing pipeline from detection
to ChromaDB storage, including integration between FileProcessor,
RAGStoreProcessor, and ChromaDB components.
"""

import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.app import FolderFileProcessorApp
from src.core.rag_store_processor import RAGStoreProcessor
from .base_test_classes import (
    BaseRAGIntegrationTest,
    MockDocumentProcessor,
    MockRAGStoreComponents,
    IntegrationTestFixtures,
    FileFixture
)


class TestEndToEndDocumentProcessingWorkflow(BaseRAGIntegrationTest):
    """Test complete document processing workflow end-to-end."""
    
    def test_complete_workflow_with_mock_processor(self):
        """Test complete workflow using mock document processor."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create mock processor
        self.mock_processor = MockDocumentProcessor()
        
        # Create test files
        fixtures = self.get_standard_test_fixtures()
        test_files = self.create_test_files(fixtures)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        # Patch the document processor creation to use our mock
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process files directly (without monitoring for faster test)
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    
                    # Find corresponding fixture
                    fixture = next(f for f in fixtures if f.filename == file_path.name)
                    
                    if fixture.expected_success:
                        assert result.success is True
                        assert result.chunks_created > 0
                        self.assert_file_moved_to_saved(file_path.name)
                    else:
                        assert result.success is False
                        self.assert_file_moved_to_error(file_path.name)
                        self.assert_error_log_created(file_path.name)
        
        # Verify mock processor was used correctly
        assert self.mock_processor.initialized is True
        assert len(self.mock_processor.processed_files) == len(test_files)
    
    def test_workflow_with_rag_store_processor_mocked_components(self):
        """Test workflow with RAGStoreProcessor using mocked RAG components."""
        # Create environment with API keys
        self.create_env_file(
            enable_document_processing=True,
            GOOGLE_API_KEY="test_key_123"
        )
        
        # Create test files
        fixtures = [f for f in self.get_standard_test_fixtures() if f.expected_success]
        test_files = self.create_test_files(fixtures)
        
        # Mock RAG store components
        mock_registry = MockRAGStoreComponents.mock_processor_registry()
        mock_model = MockRAGStoreComponents.mock_embedding_model()
        mock_vectorstore = MockRAGStoreComponents.mock_chroma_vectorstore()
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        # Patch RAG store components
        with patch('src.core.rag_store_processor.ProcessorRegistry', return_value=mock_registry), \
             patch('src.core.rag_store_processor.load_embedding_model', return_value=mock_model), \
             patch('src.core.rag_store_processor.store_to_chroma', return_value=mock_vectorstore):
            
            assert self.app.initialize() is True
            
            # Verify document processor is RAGStoreProcessor
            assert isinstance(self.app.file_processor.document_processor, RAGStoreProcessor)
            assert self.app.file_processor.document_processor.initialized is True
            
            # Process files
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is True
                    assert result.processor_used == "RAGStoreProcessor"
                    self.assert_file_moved_to_saved(file_path.name)
            
            # Verify RAG components were called
            assert mock_registry.process_document.call_count == len(test_files)
    
    def test_workflow_with_nested_directory_structure(self):
        """Test workflow preserves nested directory structure."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create nested directory structure
        structure = self.create_nested_directory_structure()
        
        # Create test files in nested directories
        test_files = []
        fixtures = [f for f in self.get_standard_test_fixtures() if f.expected_success][:2]
        
        for i, (dir_name, dir_path) in enumerate(structure.items()):
            if i < len(fixtures):
                fixture = fixtures[i]
                file_path = self.create_test_file(fixture, dir_path)
                test_files.append((fixture, file_path))
        
        # Create mock processor
        self.mock_processor = MockDocumentProcessor()
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process files
            for fixture, file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is True
                    
                    # Verify file moved with preserved structure
                    self.assert_file_moved_to_saved(fixture.filename, preserve_structure=True)
    
    def test_workflow_with_mixed_success_and_failure_files(self):
        """Test workflow handles mixed success and failure files correctly."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create mixed test files
        fixtures = IntegrationTestFixtures.get_mixed_file_fixtures()
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor that fails on specific files
        fail_on_files = {f.filename for f in fixtures if not f.expected_success}
        self.mock_processor = MockDocumentProcessor(fail_on_files=fail_on_files)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process all files
            results = []
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    results.append(result)
            
            # Verify results match expectations
            for i, (fixture, result) in enumerate(zip(fixtures, results)):
                if fixture.expected_success:
                    assert result.success is True
                    self.assert_file_moved_to_saved(fixture.filename)
                else:
                    assert result.success is False
                    self.assert_file_moved_to_error(fixture.filename)
                    self.assert_error_log_created(fixture.filename)
            
            # Verify statistics
            stats = self.get_processing_statistics()
            if stats:
                successful_count = sum(1 for f in fixtures if f.expected_success)
                failed_count = sum(1 for f in fixtures if not f.expected_success)
                
                assert stats.get('successful', 0) >= successful_count
                assert stats.get('failed_permanent', 0) >= failed_count
    
    def test_workflow_with_file_monitoring_integration(self):
        """Test workflow with actual file monitoring integration."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create mock processor
        self.mock_processor = MockDocumentProcessor()
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Start monitoring in a separate thread
            def run_app():
                try:
                    self.app.start()
                except Exception:
                    pass
            
            app_thread = threading.Thread(target=run_app, daemon=True)
            app_thread.start()
            
            # Wait for monitoring to start
            time.sleep(0.2)
            
            # Create test files while monitoring is active
            fixtures = [f for f in self.get_standard_test_fixtures() if f.expected_success][:2]
            
            for fixture in fixtures:
                file_path = self.create_test_file(fixture)
                # Small delay between file creations
                time.sleep(0.1)
            
            # Wait for processing
            self.wait_for_file_processing(timeout=3.0)
            
            # Stop monitoring
            self.app.shutdown_requested = True
            app_thread.join(timeout=2.0)
            
            # Verify files were processed
            for fixture in fixtures:
                self.assert_file_moved_to_saved(fixture.filename)
            
            # Verify mock processor was used
            assert len(self.mock_processor.processed_files) >= len(fixtures)
    
    def test_workflow_error_recovery_and_continuation(self):
        """Test workflow continues processing after individual file errors."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create test files - mix of success and failure
        fixtures = self.get_standard_test_fixtures()
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor that fails on empty files
        fail_on_files = {f.filename for f in fixtures if not f.expected_success}
        self.mock_processor = MockDocumentProcessor(fail_on_files=fail_on_files)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process all files in sequence
            for file_path in test_files:
                if file_path.exists():
                    # Processing should not raise exceptions even for failed files
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result is not None  # Should always return a result
            
            # Verify all files were processed (moved from source)
            remaining_files = list(self.source_dir.rglob("*"))
            remaining_files = [f for f in remaining_files if f.is_file()]
            assert len(remaining_files) == 0, f"Files still in source: {remaining_files}"
            
            # Verify successful files in saved directory
            successful_fixtures = [f for f in fixtures if f.expected_success]
            for fixture in successful_fixtures:
                self.assert_file_moved_to_saved(fixture.filename)
            
            # Verify failed files in error directory with logs
            failed_fixtures = [f for f in fixtures if not f.expected_success]
            for fixture in failed_fixtures:
                self.assert_file_moved_to_error(fixture.filename)
                self.assert_error_log_created(fixture.filename)
    
    def test_workflow_with_processor_initialization_failure(self):
        """Test workflow handles document processor initialization failure."""
        # Create environment configuration without required API key
        self.create_env_file(enable_document_processing=True)
        # Note: No GOOGLE_API_KEY or OPENAI_API_KEY provided
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        # App initialization should fail due to missing API key
        result = self.app.initialize()
        assert result is False
    
    def test_workflow_with_processor_runtime_failure(self):
        """Test workflow handles document processor runtime failures."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create test files
        fixtures = [f for f in self.get_standard_test_fixtures() if f.expected_success][:2]
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor that fails all processing
        self.mock_processor = MockDocumentProcessor(should_fail=True)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process files - all should fail but not crash the system
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is False
                    assert result.error_message is not None
            
            # Verify all files moved to error directory
            for fixture in fixtures:
                self.assert_file_moved_to_error(fixture.filename)
                self.assert_error_log_created(fixture.filename)
    
    def test_workflow_performance_with_multiple_files(self):
        """Test workflow performance with multiple files."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create multiple test files
        fixtures = IntegrationTestFixtures.get_performance_test_fixtures()
        # Create multiple copies of each fixture
        all_fixtures = []
        for i in range(3):  # 3 copies of each fixture type
            for fixture in fixtures:
                new_fixture = FileFixture(
                    name=f"{fixture.name}_{i}",
                    content=fixture.content,
                    extension=fixture.extension,
                    expected_success=fixture.expected_success,
                    expected_chunks=fixture.expected_chunks
                )
                all_fixtures.append(new_fixture)
        
        test_files = self.create_test_files(all_fixtures)
        
        # Create mock processor with small processing delay
        self.mock_processor = MockDocumentProcessor(processing_delay=0.01)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Measure processing time
            start_time = time.time()
            
            # Process all files
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is True
            
            processing_time = time.time() - start_time
            
            # Verify all files processed
            for fixture in all_fixtures:
                self.assert_file_moved_to_saved(fixture.filename)
            
            # Performance assertions
            assert processing_time < 10.0, f"Processing took too long: {processing_time}s"
            assert len(self.mock_processor.processed_files) == len(all_fixtures)
            
            # Verify processing statistics
            stats = self.get_processing_statistics()
            if stats:
                assert stats.get('successful', 0) >= len(all_fixtures)


if __name__ == "__main__":
    pytest.main([__file__])