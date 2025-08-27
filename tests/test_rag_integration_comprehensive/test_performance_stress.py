"""
Performance and stress tests for document processing integration.

This module tests document processing performance with large files and high volume,
memory usage and resource cleanup, ChromaDB performance, error recovery,
and system stability under stress conditions.
"""

import os
import sys
import time
import threading
import psutil
import gc
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.app import FolderFileProcessorApp
from .base_test_classes import (
    BaseRAGIntegrationTest,
    MockDocumentProcessor,
    MockRAGStoreComponents,
    IntegrationTestFixtures,
    FileFixture
)


class TestDocumentProcessingPerformance(BaseRAGIntegrationTest):
    """Test document processing performance with various file sizes and volumes."""
    
    def test_large_file_processing_performance(self):
        """Test processing performance with large files."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create large test files
        large_fixtures = [
            FileFixture(
                name="small_1mb",
                content="Small file content. " * 50000,  # ~1MB
                extension="txt",
                expected_success=True
            ),
            FileFixture(
                name="medium_5mb",
                content="Medium file content. " * 250000,  # ~5MB
                extension="txt",
                expected_success=True
            ),
            FileFixture(
                name="large_10mb",
                content="Large file content. " * 500000,  # ~10MB
                extension="txt",
                expected_success=True
            )
        ]
        
        test_files = self.create_test_files(large_fixtures)
        
        # Create mock processor with realistic processing delay
        self.mock_processor = MockDocumentProcessor(processing_delay=0.1)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Measure processing time for each file size
            processing_times = {}
            
            for fixture, file_path in zip(large_fixtures, test_files):
                if file_path.exists():
                    start_time = time.time()
                    result = self.app.file_processor.process_file(str(file_path))
                    processing_time = time.time() - start_time
                    
                    processing_times[fixture.name] = processing_time
                    
                    assert result.success is True
                    assert result.processing_time > 0
                    self.assert_file_moved_to_saved(fixture.filename)
            
            # Performance assertions
            # Processing time should scale reasonably with file size
            assert processing_times["small_1mb"] < 5.0, "Small file processing too slow"
            assert processing_times["medium_5mb"] < 15.0, "Medium file processing too slow"
            assert processing_times["large_10mb"] < 30.0, "Large file processing too slow"
            
            # Verify all files processed successfully
            assert len(self.mock_processor.processed_files) == len(large_fixtures)
    
    def test_high_volume_file_processing(self):
        """Test processing performance with high volume of files."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create many small files
        num_files = 50
        fixtures = []
        for i in range(num_files):
            fixture = FileFixture(
                name=f"volume_test_{i:03d}",
                content=f"Content for file {i}. " * 100,
                extension="txt",
                expected_success=True
            )
            fixtures.append(fixture)
        
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor with small delay
        self.mock_processor = MockDocumentProcessor(processing_delay=0.01)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Measure total processing time
            start_time = time.time()
            
            # Process all files
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is True
            
            total_time = time.time() - start_time
            
            # Performance assertions
            assert total_time < 30.0, f"High volume processing too slow: {total_time}s"
            
            # Verify throughput
            throughput = num_files / total_time
            assert throughput > 2.0, f"Throughput too low: {throughput} files/sec"
            
            # Verify all files processed
            assert len(self.mock_processor.processed_files) == num_files
            
            # Verify all files moved correctly
            saved_files = list(self.saved_dir.glob("*.txt"))
            assert len(saved_files) == num_files
    
    def test_concurrent_file_processing_performance(self):
        """Test performance with concurrent file processing simulation."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create test files for concurrent processing
        num_files = 20
        fixtures = []
        for i in range(num_files):
            fixture = FileFixture(
                name=f"concurrent_{i:02d}",
                content=f"Concurrent processing test {i}. " * 50,
                extension="txt",
                expected_success=True
            )
            fixtures.append(fixture)
        
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor with realistic delay
        self.mock_processor = MockDocumentProcessor(processing_delay=0.05)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Simulate concurrent processing by processing files rapidly
            start_time = time.time()
            results = []
            
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    results.append(result)
            
            total_time = time.time() - start_time
            
            # Verify all processing succeeded
            successful_results = [r for r in results if r.success]
            assert len(successful_results) == num_files
            
            # Performance assertion
            assert total_time < 15.0, f"Concurrent processing simulation too slow: {total_time}s"
            
            # Verify system handled concurrent-like load
            assert len(self.mock_processor.processed_files) == num_files


class TestMemoryUsageAndResourceCleanup(BaseRAGIntegrationTest):
    """Test memory usage and resource cleanup during document processing."""
    
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def test_memory_usage_with_large_files(self):
        """Test memory usage doesn't grow excessively with large files."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create large test file
        large_fixture = FileFixture(
            name="memory_test_large",
            content="Large content for memory test. " * 100000,  # ~2.5MB
            extension="txt",
            expected_success=True
        )
        
        # Create mock processor
        self.mock_processor = MockDocumentProcessor(processing_delay=0.1)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Measure initial memory usage
            initial_memory = self.get_memory_usage()
            
            # Process the large file multiple times
            for i in range(5):
                # Create new file each time
                file_path = self.create_test_file(FileFixture(
                    name=f"memory_test_{i}",
                    content=large_fixture.content,
                    extension="txt",
                    expected_success=True
                ))
                
                result = self.app.file_processor.process_file(str(file_path))
                assert result.success is True
                
                # Force garbage collection
                gc.collect()
            
            # Measure final memory usage
            final_memory = self.get_memory_usage()
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB for this test)
            assert memory_increase < 100, f"Excessive memory usage: {memory_increase}MB increase"
    
    def test_resource_cleanup_after_processing(self):
        """Test that resources are properly cleaned up after processing."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create test files
        fixtures = [
            FileFixture(
                name=f"cleanup_test_{i}",
                content=f"Cleanup test content {i}. " * 100,
                extension="txt",
                expected_success=True
            )
            for i in range(10)
        ]
        
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor
        self.mock_processor = MockDocumentProcessor()
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process all files
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is True
            
            # Verify processor cleanup can be called
            self.mock_processor.cleanup()
            assert self.mock_processor.cleanup_called is True
            assert self.mock_processor.initialized is False
            
            # Verify app shutdown cleans up resources
            self.app.shutdown()
    
    def test_memory_stability_during_extended_processing(self):
        """Test memory stability during extended processing periods."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create mock processor
        self.mock_processor = MockDocumentProcessor(processing_delay=0.01)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Measure memory at intervals during extended processing
            memory_measurements = []
            initial_memory = self.get_memory_usage()
            memory_measurements.append(initial_memory)
            
            # Process files in batches
            for batch in range(5):
                # Create batch of files
                batch_fixtures = [
                    FileFixture(
                        name=f"extended_{batch}_{i}",
                        content=f"Extended test content {batch}-{i}. " * 50,
                        extension="txt",
                        expected_success=True
                    )
                    for i in range(10)
                ]
                
                batch_files = self.create_test_files(batch_fixtures)
                
                # Process batch
                for file_path in batch_files:
                    if file_path.exists():
                        result = self.app.file_processor.process_file(str(file_path))
                        assert result.success is True
                
                # Measure memory after batch
                gc.collect()
                current_memory = self.get_memory_usage()
                memory_measurements.append(current_memory)
            
            # Analyze memory stability
            max_memory = max(memory_measurements)
            min_memory = min(memory_measurements)
            memory_variation = max_memory - min_memory
            
            # Memory should remain relatively stable
            assert memory_variation < 50, f"Memory too unstable: {memory_variation}MB variation"


class TestErrorRecoveryAndSystemStability(BaseRAGIntegrationTest):
    """Test error recovery and system stability under stress conditions."""
    
    def test_error_recovery_under_high_failure_rate(self):
        """Test system stability when many files fail processing."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create mix of files - many will fail
        fixtures = []
        for i in range(30):
            if i % 3 == 0:  # Every third file succeeds
                fixture = FileFixture(
                    name=f"success_{i}",
                    content=f"Successful content {i}. " * 10,
                    extension="txt",
                    expected_success=True
                )
            else:  # Others fail
                fixture = FileFixture(
                    name=f"failure_{i}",
                    content="",  # Empty content causes failure
                    extension="txt",
                    expected_success=False
                )
            fixtures.append(fixture)
        
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor that fails on empty files
        fail_on_files = {f.filename for f in fixtures if not f.expected_success}
        self.mock_processor = MockDocumentProcessor(fail_on_files=fail_on_files)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process all files - system should remain stable despite high failure rate
            successful_count = 0
            failed_count = 0
            
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    if result.success:
                        successful_count += 1
                    else:
                        failed_count += 1
            
            # Verify system handled high failure rate gracefully
            expected_successes = sum(1 for f in fixtures if f.expected_success)
            expected_failures = sum(1 for f in fixtures if not f.expected_success)
            
            assert successful_count == expected_successes
            assert failed_count == expected_failures
            
            # Verify all files were moved appropriately
            saved_files = list(self.saved_dir.glob("*.txt"))
            error_files = list(self.error_dir.glob("*.txt"))
            
            assert len(saved_files) == expected_successes
            assert len(error_files) == expected_failures
    
    def test_system_stability_with_processor_exceptions(self):
        """Test system stability when document processor raises exceptions."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create test files
        fixtures = [
            FileFixture(
                name=f"exception_test_{i}",
                content=f"Exception test content {i}. " * 10,
                extension="txt",
                expected_success=True
            )
            for i in range(20)
        ]
        
        test_files = self.create_test_files(fixtures)
        
        # Create mock processor that randomly raises exceptions
        class ExceptionMockProcessor(MockDocumentProcessor):
            def __init__(self):
                super().__init__()
                self.exception_count = 0
            
            def process_document(self, file_path):
                self.exception_count += 1
                # Raise exception on every 3rd file
                if self.exception_count % 3 == 0:
                    raise RuntimeError(f"Simulated processing exception for {file_path.name}")
                return super().process_document(file_path)
        
        self.mock_processor = ExceptionMockProcessor()
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Process all files - system should handle exceptions gracefully
            results = []
            for file_path in test_files:
                if file_path.exists():
                    # Should not raise unhandled exceptions
                    result = self.app.file_processor.process_file(str(file_path))
                    results.append(result)
            
            # Verify system remained stable
            assert len(results) == len(fixtures)
            
            # Some files should have failed due to exceptions
            failed_results = [r for r in results if not r.success]
            assert len(failed_results) > 0, "Expected some failures due to exceptions"
            
            # Verify error handling worked
            error_files = list(self.error_dir.glob("*.txt"))
            error_logs = list(self.error_dir.glob("*.log"))
            
            assert len(error_files) == len(failed_results)
            assert len(error_logs) == len(failed_results)
    
    def test_monitoring_responsiveness_during_heavy_processing(self):
        """Test that monitoring remains responsive during heavy processing load."""
        # Create environment configuration
        self.create_env_file(enable_document_processing=True)
        
        # Create mock processor with significant delay
        self.mock_processor = MockDocumentProcessor(processing_delay=0.1)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.app.RAGStoreProcessor', return_value=self.mock_processor):
            assert self.app.initialize() is True
            
            # Start monitoring
            self.app.file_monitor.start_monitoring()
            assert self.app.file_monitor.is_monitoring() is True
            
            # Create files during monitoring to simulate load
            def create_files_continuously():
                for i in range(10):
                    fixture = FileFixture(
                        name=f"monitoring_test_{i}",
                        content=f"Monitoring test {i}. " * 20,
                        extension="txt",
                        expected_success=True
                    )
                    self.create_test_file(fixture)
                    time.sleep(0.05)  # Small delay between file creations
            
            # Start file creation in background
            file_thread = threading.Thread(target=create_files_continuously, daemon=True)
            file_thread.start()
            
            # Monitor health checks during processing
            health_checks = []
            for _ in range(5):
                time.sleep(0.2)
                health_result = self.app._perform_health_check()
                health_checks.append(health_result)
            
            # Stop monitoring
            self.app.file_monitor.stop_monitoring()
            file_thread.join(timeout=2.0)
            
            # Verify monitoring remained responsive
            assert all(health_checks), "Health checks failed during processing"
            
            # Verify some files were processed
            processed_files = list(self.saved_dir.glob("*.txt"))
            assert len(processed_files) > 0, "No files were processed"


class TestChromaDBPerformanceSimulation(BaseRAGIntegrationTest):
    """Test ChromaDB performance simulation and storage efficiency."""
    
    def test_chroma_db_storage_simulation(self):
        """Test ChromaDB storage simulation with mock components."""
        # Create environment configuration
        self.create_env_file(
            enable_document_processing=True,
            GOOGLE_API_KEY="test_key_123"
        )
        
        # Create test files of various sizes
        fixtures = IntegrationTestFixtures.get_performance_test_fixtures()
        test_files = self.create_test_files(fixtures)
        
        # Mock ChromaDB components
        mock_registry = MockRAGStoreComponents.mock_processor_registry()
        mock_model = MockRAGStoreComponents.mock_embedding_model()
        mock_vectorstore = MockRAGStoreComponents.mock_chroma_vectorstore()
        
        # Track storage operations
        storage_operations = []
        
        def track_storage(*args, **kwargs):
            storage_operations.append({
                'timestamp': time.time(),
                'args': args,
                'kwargs': kwargs
            })
            return mock_vectorstore
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.core.rag_store_processor.ProcessorRegistry', return_value=mock_registry), \
             patch('src.core.rag_store_processor.load_embedding_model', return_value=mock_model), \
             patch('src.core.rag_store_processor.store_to_chroma', side_effect=track_storage):
            
            assert self.app.initialize() is True
            
            # Process files and measure storage performance
            start_time = time.time()
            
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is True
            
            total_time = time.time() - start_time
            
            # Verify storage operations
            assert len(storage_operations) == len(fixtures)
            
            # Verify performance
            assert total_time < 10.0, f"ChromaDB simulation too slow: {total_time}s"
            
            # Verify storage efficiency (all operations completed)
            for operation in storage_operations:
                assert 'timestamp' in operation
                assert operation['args']  # Should have documents to store
    
    def test_embedding_generation_performance_simulation(self):
        """Test embedding generation performance simulation."""
        # Create environment configuration
        self.create_env_file(
            enable_document_processing=True,
            GOOGLE_API_KEY="test_key_123"
        )
        
        # Create files with varying content sizes
        fixtures = [
            FileFixture(
                name="small_content",
                content="Small content. " * 10,
                extension="txt",
                expected_success=True
            ),
            FileFixture(
                name="medium_content",
                content="Medium content. " * 100,
                extension="txt",
                expected_success=True
            ),
            FileFixture(
                name="large_content",
                content="Large content. " * 1000,
                extension="txt",
                expected_success=True
            )
        ]
        
        test_files = self.create_test_files(fixtures)
        
        # Mock components with performance tracking
        mock_registry = MockRAGStoreComponents.mock_processor_registry()
        
        embedding_calls = []
        
        def track_embedding_model():
            mock_model = Mock()
            
            def track_embed_documents(documents):
                embedding_calls.append({
                    'timestamp': time.time(),
                    'document_count': len(documents),
                    'total_length': sum(len(doc) for doc in documents)
                })
                return [[0.1, 0.2, 0.3]] * len(documents)
            
            mock_model.embed_documents = track_embed_documents
            return mock_model
        
        mock_vectorstore = MockRAGStoreComponents.mock_chroma_vectorstore()
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        with patch('src.core.rag_store_processor.ProcessorRegistry', return_value=mock_registry), \
             patch('src.core.rag_store_processor.load_embedding_model', side_effect=track_embedding_model), \
             patch('src.core.rag_store_processor.store_to_chroma', return_value=mock_vectorstore):
            
            assert self.app.initialize() is True
            
            # Process files
            for file_path in test_files:
                if file_path.exists():
                    result = self.app.file_processor.process_file(str(file_path))
                    assert result.success is True
            
            # Verify embedding generation was called
            assert len(embedding_calls) == len(fixtures)
            
            # Verify performance scales with content size
            small_call = next(call for call in embedding_calls if call['document_count'] <= 5)
            large_call = next(call for call in embedding_calls if call['document_count'] >= 10)
            
            assert small_call['total_length'] < large_call['total_length']


if __name__ == "__main__":
    pytest.main([__file__])