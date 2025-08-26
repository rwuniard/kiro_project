# RAG Integration Comprehensive Test Suite

This directory contains comprehensive integration tests for the RAG (Retrieval-Augmented Generation) document processing integration with the folder file processor application.

## Overview

The test suite verifies that the RAG document processing integration works correctly end-to-end, maintains backward compatibility with existing functionality, and performs well under various conditions.

## Test Structure

### Base Test Infrastructure (`base_test_classes.py`)

Provides common test infrastructure including:

- **BaseRAGIntegrationTest**: Base class for all integration tests with setup/teardown
- **MockDocumentProcessor**: Mock implementation of DocumentProcessingInterface for testing
- **MockRAGStoreComponents**: Mock RAG store components (registry, embedding model, ChromaDB)
- **TestFileFixture**: Data class for test file definitions
- **IntegrationTestFixtures**: Common test file fixtures for different scenarios

### End-to-End Workflow Tests (`test_end_to_end_workflow.py`)

Tests the complete document processing pipeline:

- **Complete workflow with mock processor**: Tests full pipeline with controlled mock
- **Workflow with RAG store processor**: Tests with actual RAGStoreProcessor using mocked components
- **Nested directory structure**: Tests directory structure preservation
- **Mixed success/failure scenarios**: Tests handling of both successful and failed processing
- **File monitoring integration**: Tests integration with file monitoring system
- **Error recovery**: Tests system continues after individual file failures
- **Processor initialization failures**: Tests handling of initialization errors
- **Runtime failures**: Tests handling of processing runtime errors
- **Performance with multiple files**: Tests processing multiple files efficiently

### Regression Tests (`test_regression.py`)

Ensures existing functionality continues to work:

- **File monitoring unchanged**: Verifies file monitoring behavior is preserved
- **Error handling preserved**: Verifies error handling and logging behavior unchanged
- **Configuration management**: Verifies configuration loading still works
- **File movement logic**: Verifies folder cleanup and file movement preserved
- **Backward compatibility**: Verifies compatibility with existing test patterns
- **Document processing disabled mode**: Tests system works when RAG processing is disabled
- **Signal handling**: Verifies signal handling and shutdown functionality preserved

### Performance and Stress Tests (`test_performance_stress.py`)

Tests system performance and stability:

- **Large file processing**: Tests performance with files of various sizes (1MB, 5MB, 10MB)
- **High volume processing**: Tests processing many files (50+ files)
- **Concurrent processing simulation**: Tests system under concurrent-like load
- **Memory usage monitoring**: Tests memory usage doesn't grow excessively
- **Resource cleanup**: Tests proper cleanup of resources after processing
- **Memory stability**: Tests memory remains stable during extended processing
- **Error recovery under stress**: Tests system stability with high failure rates
- **System stability with exceptions**: Tests handling of processor exceptions
- **Monitoring responsiveness**: Tests monitoring remains responsive during heavy processing
- **ChromaDB performance simulation**: Tests ChromaDB storage and embedding performance

### Comprehensive Integration Tests (`test_comprehensive_integration.py`)

High-level integration scenarios:

- **Complete integration workflow**: Tests full successful integration scenario
- **Mixed scenario workflow**: Tests integration with mixed success/failure
- **Existing functionality preserved**: Tests integration doesn't break existing features
- **Error scenarios and recovery**: Tests various error scenarios and recovery
- **Performance and scalability**: Tests integration performance with multiple files
- **Monitoring and health checks**: Tests integration with monitoring systems
- **Test infrastructure validation**: Tests the test infrastructure itself

## Running Tests

### Prerequisites

Install required dependencies:

```bash
pip install pytest psutil
```

### Run All Tests

```bash
# Run all integration tests
python tests/test_rag_integration_comprehensive/run_integration_tests.py

# Run all tests except performance tests (faster)
python tests/test_rag_integration_comprehensive/run_integration_tests.py --quick

# Run with verbose output
python tests/test_rag_integration_comprehensive/run_integration_tests.py --verbose
```

### Run Specific Test Suites

```bash
# Run end-to-end workflow tests only
python tests/test_rag_integration_comprehensive/run_integration_tests.py --test workflow

# Run regression tests only
python tests/test_rag_integration_comprehensive/run_integration_tests.py --test regression

# Run performance tests only
python tests/test_rag_integration_comprehensive/run_integration_tests.py --test performance

# Run comprehensive integration tests only
python tests/test_rag_integration_comprehensive/run_integration_tests.py --test comprehensive
```

### Run Individual Test Files

```bash
# Run specific test file with pytest directly
python -m pytest tests/test_rag_integration_comprehensive/test_end_to_end_workflow.py -v

# Run specific test class
python -m pytest tests/test_rag_integration_comprehensive/test_end_to_end_workflow.py::TestEndToEndDocumentProcessingWorkflow -v

# Run specific test method
python -m pytest tests/test_rag_integration_comprehensive/test_end_to_end_workflow.py::TestEndToEndDocumentProcessingWorkflow::test_complete_workflow_with_mock_processor -v
```

### Debug Mode

```bash
# Run without capturing output (useful for debugging)
python tests/test_rag_integration_comprehensive/run_integration_tests.py --no-capture

# Run specific test without capture
python tests/test_rag_integration_comprehensive/run_integration_tests.py --test workflow --no-capture
```

## Test Configuration

### Environment Variables

Tests create temporary environments but may use these variables if set:

- `GOOGLE_API_KEY`: Google API key for RAG store (mocked in tests)
- `OPENAI_API_KEY`: OpenAI API key for RAG store (mocked in tests)
- `ENABLE_DOCUMENT_PROCESSING`: Enable/disable document processing (controlled by tests)

### Test Data

Tests create temporary directories and files:

- Temporary source, saved, and error directories
- Test files with various content types and sizes
- Mock configuration files

All test data is automatically cleaned up after each test.

## Mock Components

### MockDocumentProcessor

Configurable mock that simulates document processing:

- Supports configurable file extensions
- Can simulate processing failures on specific files
- Can simulate processing delays
- Tracks processed files for verification

### MockRAGStoreComponents

Provides mocked RAG store components:

- **ProcessorRegistry**: Mock document processor registry
- **EmbeddingModel**: Mock embedding model with fake embeddings
- **ChromaVectorstore**: Mock ChromaDB vectorstore

## Test Patterns

### File Fixtures

Tests use `TestFileFixture` objects to define test files:

```python
fixture = TestFileFixture(
    name="test_document",
    content="Document content here",
    extension="txt",
    expected_success=True,
    expected_chunks=5
)
```

### Base Test Class Usage

Extend `BaseRAGIntegrationTest` for integration tests:

```python
class TestMyIntegration(BaseRAGIntegrationTest):
    def test_my_scenario(self):
        # Setup environment
        self.create_env_file(enable_document_processing=True)
        
        # Create test files
        fixtures = self.get_standard_test_fixtures()
        test_files = self.create_test_files(fixtures)
        
        # Initialize and test app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file))
        # ... test logic
```

### Assertions

Common assertion patterns:

```python
# Verify file movement
self.assert_file_moved_to_saved("test.txt")
self.assert_file_moved_to_error("failed.txt")
self.assert_error_log_created("failed.txt")

# Verify processing results
assert result.success is True
assert result.chunks_created > 0
assert result.processor_used == "RAGStoreProcessor"

# Verify statistics
stats = self.get_processing_statistics()
assert stats.get('successful', 0) > 0
```

## Coverage

The test suite aims for comprehensive coverage of:

- ✅ Document processing interface implementation
- ✅ RAG store processor integration
- ✅ File processing workflow integration
- ✅ Error handling and logging
- ✅ Configuration management
- ✅ File monitoring integration
- ✅ Performance characteristics
- ✅ Memory usage and resource cleanup
- ✅ Backward compatibility
- ✅ System stability under stress

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `src` directory is in Python path
2. **Permission Errors**: Ensure write permissions for temporary directories
3. **Memory Issues**: Performance tests may require sufficient RAM
4. **Timeout Issues**: Increase timeouts for slower systems

### Debug Tips

1. Use `--no-capture` flag to see print statements
2. Use `--verbose` flag for detailed test output
3. Run individual test methods for focused debugging
4. Check temporary directories if tests fail cleanup

### Performance Considerations

- Performance tests may take several minutes to complete
- Use `--quick` flag to skip performance tests during development
- Memory usage tests require `psutil` package
- Large file tests create files up to 10MB in size

## Contributing

When adding new integration tests:

1. Extend `BaseRAGIntegrationTest` for common functionality
2. Use `TestFileFixture` for consistent test file creation
3. Follow existing naming conventions
4. Add appropriate cleanup in teardown methods
5. Update this README if adding new test categories
6. Ensure tests are deterministic and don't depend on external services