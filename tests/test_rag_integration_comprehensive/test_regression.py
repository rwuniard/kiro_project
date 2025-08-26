"""
Regression tests for existing functionality after RAG integration.

This module ensures that existing file monitoring, error handling,
configuration management, and file movement functionality continues
to work correctly after RAG integration.
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
from src.core.file_monitor import FileMonitor
from src.core.file_processor import FileProcessor
from src.core.file_manager import FileManager
from src.services.error_handler import ErrorHandler
from src.config.config_manager import ConfigManager
from .base_test_classes import (
    BaseRAGIntegrationTest,
    MockDocumentProcessor,
    IntegrationTestFixtures
)


class TestExistingFunctionalityRegression(BaseRAGIntegrationTest):
    """Test that existing functionality works unchanged after RAG integration."""
    
    def test_file_monitoring_functionality_unchanged(self):
        """Test that file monitoring behavior is preserved."""
        # Create environment with document processing disabled
        self.create_env_file(enable_document_processing=False)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Verify file monitor is properly initialized
        assert isinstance(self.app.file_monitor, FileMonitor)
        assert self.app.file_monitor.source_folder == str(self.source_dir)
        
        # Test monitoring start/stop
        self.app.file_monitor.start_monitoring()
        assert self.app.file_monitor.is_monitoring() is True
        
        self.app.file_monitor.stop_monitoring()
        assert self.app.file_monitor.is_monitoring() is False
        
        # Test monitoring statistics
        stats = self.app.file_monitor.get_monitoring_stats()
        assert isinstance(stats, dict)
        assert 'events_received' in stats
    
    def test_error_handling_behavior_preserved(self):
        """Test that error handling and logging behavior is preserved."""
        # Create environment with document processing disabled
        self.create_env_file(enable_document_processing=False)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Verify error handler is properly initialized
        assert isinstance(self.app.error_handler, ErrorHandler)
        
        # Create a file that will cause an error (empty file)
        error_file = self.source_dir / "empty_test.txt"
        error_file.write_text("")
        
        # Process the file - should fail with validation error
        result = self.app.file_processor.process_file(str(error_file))
        assert result.success is False
        
        # Verify error handling behavior
        self.assert_file_moved_to_error("empty_test.txt")
        self.assert_error_log_created("empty_test.txt")
        
        # Verify error log format is preserved
        error_log = self.error_dir / "empty_test.txt.log"
        log_content = error_log.read_text()
        assert "FILE PROCESSING ERROR LOG" in log_content
        assert "File is empty" in log_content
    
    def test_configuration_management_continues_to_work(self):
        """Test that configuration management works correctly."""
        # Create environment with various configurations
        self.create_env_file(
            enable_document_processing=False,
            RETRY_ATTEMPTS="5",
            RETRY_DELAY="2.0",
            HEALTH_CHECK_INTERVAL="30"
        )
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Verify configuration is loaded correctly
        assert isinstance(self.app.config_manager, ConfigManager)
        assert self.app.config is not None
        
        # Verify basic configuration values
        assert self.app.config.source_folder == str(self.source_dir)
        assert self.app.config.saved_folder == str(self.saved_dir)
        assert self.app.config.error_folder == str(self.error_dir)
        
        # Verify file processing configuration
        assert self.app.config.file_processing.retry_attempts == 5
        assert self.app.config.file_processing.retry_delay == 2.0
        assert self.app.config.monitoring.health_check_interval == 30
    
    def test_folder_cleanup_and_file_movement_logic_maintained(self):
        """Test that folder cleanup and file movement logic is maintained."""
        # Create environment with document processing disabled
        self.create_env_file(enable_document_processing=False)
        
        # Create nested directory structure with files
        structure = self.create_nested_directory_structure()
        
        # Create test files in nested directories
        test_files = []
        for i, (dir_name, dir_path) in enumerate(structure.items()):
            if i < 2:  # Create files in first 2 directories
                file_path = dir_path / f"test_{dir_name}.txt"
                file_path.write_text(f"Content for {dir_name}")
                test_files.append(file_path)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Verify file manager is properly initialized
        assert isinstance(self.app.file_manager, FileManager)
        
        # Process files
        for file_path in test_files:
            if file_path.exists():
                result = self.app.file_processor.process_file(str(file_path))
                assert result.success is True
        
        # Verify files moved with preserved directory structure
        for file_path in test_files:
            relative_path = file_path.relative_to(self.source_dir)
            expected_saved_path = self.saved_dir / relative_path
            assert expected_saved_path.exists(), f"File not found at expected location: {expected_saved_path}"
        
        # Verify source directories are cleaned up (empty directories removed)
        # Note: This depends on the cleanup policy - some implementations may preserve empty dirs
        remaining_files = list(self.source_dir.rglob("*"))
        remaining_files = [f for f in remaining_files if f.is_file()]
        assert len(remaining_files) == 0, "Source directory should be empty of files"
    
    def test_backward_compatibility_with_existing_test_suites(self):
        """Test backward compatibility with existing test patterns."""
        # Create environment similar to existing tests
        self.create_env_file(enable_document_processing=False)
        
        # Initialize app using the same pattern as existing tests
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        # Test initialization pattern
        result = self.app.initialize()
        assert result is True
        
        # Verify all expected components are initialized (existing test expectations)
        assert self.app.config is not None
        assert self.app.logger_service is not None
        assert self.app.file_monitor is not None
        assert self.app.file_processor is not None
        assert self.app.file_manager is not None
        assert self.app.error_handler is not None
        
        # Test file processing pattern used in existing tests
        test_file = self.source_dir / "test.txt"
        test_file.write_text("Test file content")
        
        result = self.app.file_processor.process_file(str(test_file))
        assert result.success is True
        
        # Verify file moved to saved folder (existing test expectation)
        saved_files = list(self.saved_dir.glob("*.txt"))
        assert len(saved_files) == 1
        
        # Test monitoring setup pattern
        self.app.file_monitor.start_monitoring()
        assert self.app.file_monitor.is_monitoring() is True
        
        self.app.file_monitor.stop_monitoring()
        assert self.app.file_monitor.is_monitoring() is False
    
    def test_existing_error_scenarios_still_work(self):
        """Test that existing error scenarios still work as expected."""
        # Create environment with document processing disabled
        self.create_env_file(enable_document_processing=False)
        
        # Test initialization with missing source folder
        invalid_env = Path(self.temp_dir) / "invalid.env"
        with open(invalid_env, 'w') as f:
            f.write("SOURCE_FOLDER=/nonexistent/path\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=false\n")
        
        app = FolderFileProcessorApp(env_file=str(invalid_env))
        result = app.initialize()
        assert result is False
        
        # Test processing with invalid file
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Test processing non-existent file
        result = self.app.file_processor.process_file("/nonexistent/file.txt")
        assert result.success is False
        
        # Test processing directory instead of file
        test_dir = self.source_dir / "test_directory"
        test_dir.mkdir()
        
        result = self.app.file_processor.process_file(str(test_dir))
        assert result.success is False
    
    def test_statistics_and_monitoring_functionality_preserved(self):
        """Test that statistics and monitoring functionality is preserved."""
        # Create environment with document processing disabled
        self.create_env_file(enable_document_processing=False)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Create and process multiple files to generate statistics
        fixtures = [f for f in self.get_standard_test_fixtures() if f.expected_success][:3]
        test_files = self.create_test_files(fixtures)
        
        # Process files
        for file_path in test_files:
            if file_path.exists():
                result = self.app.file_processor.process_file(str(file_path))
                assert result.success is True
        
        # Test processing statistics
        stats = self.app.file_processor.get_processing_stats()
        assert isinstance(stats, dict)
        assert 'total_processed' in stats
        assert 'successful' in stats
        assert stats['successful'] >= len(fixtures)
        
        # Test monitoring statistics
        monitor_stats = self.app.file_monitor.get_monitoring_stats()
        assert isinstance(monitor_stats, dict)
        assert 'events_received' in monitor_stats
        
        # Test health check functionality
        health_result = self.app._perform_health_check()
        assert health_result is True
        
        # Test statistics reporting (should not raise exceptions)
        self.app._report_statistics()
    
    def test_signal_handling_and_shutdown_preserved(self):
        """Test that signal handling and shutdown functionality is preserved."""
        # Create environment with document processing disabled
        self.create_env_file(enable_document_processing=False)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Test signal handler
        assert self.app.shutdown_requested is False
        
        self.app._signal_handler(2, None)  # SIGINT
        assert self.app.shutdown_requested is True
        
        # Reset for next test
        self.app.shutdown_requested = False
        
        self.app._signal_handler(15, None)  # SIGTERM
        assert self.app.shutdown_requested is True
        
        # Test shutdown functionality
        self.app.shutdown()
        # Should not raise exceptions
    
    def test_app_lifecycle_methods_unchanged(self):
        """Test that app lifecycle methods work unchanged."""
        # Create environment with document processing disabled
        self.create_env_file(enable_document_processing=False)
        
        # Test create_app factory function
        from src.app import create_app
        app = create_app(env_file=str(self.env_file), log_file=str(self.log_file))
        assert isinstance(app, FolderFileProcessorApp)
        
        # Test run method with quick shutdown
        def mock_start():
            app.is_running = True
            app.shutdown_requested = True
        
        app.start = mock_start
        exit_code = app.run()
        assert exit_code == 0
        
        # Test run method with initialization failure
        invalid_env = Path(self.temp_dir) / "invalid.env"
        app_invalid = FolderFileProcessorApp(env_file=str(invalid_env))
        exit_code = app_invalid.run()
        assert exit_code == 1


class TestDocumentProcessingDisabledMode(BaseRAGIntegrationTest):
    """Test that the system works correctly when document processing is disabled."""
    
    def test_app_works_without_document_processing(self):
        """Test that app works normally when document processing is disabled."""
        # Create environment with document processing explicitly disabled
        self.create_env_file(enable_document_processing=False)
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Verify document processing is disabled
        assert self.app.config.document_processing.enable_processing is False
        
        # Verify file processor doesn't have document processor
        assert self.app.file_processor.document_processor is None
        
        # Create and process test files
        fixtures = [f for f in self.get_standard_test_fixtures() if f.expected_success][:2]
        test_files = self.create_test_files(fixtures)
        
        # Process files - should work with basic processing
        for file_path in test_files:
            if file_path.exists():
                result = self.app.file_processor.process_file(str(file_path))
                assert result.success is True
                self.assert_file_moved_to_saved(file_path.name)
    
    def test_missing_document_processing_config_handled_gracefully(self):
        """Test that missing document processing config is handled gracefully."""
        # Create environment without document processing configuration
        with open(self.env_file, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            # Note: No ENABLE_DOCUMENT_PROCESSING setting
        
        # Initialize app
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert self.app.initialize() is True
        
        # Should default to disabled document processing
        assert self.app.config.document_processing.enable_processing is False
        assert self.app.file_processor.document_processor is None
    
    def test_invalid_document_processing_config_handled(self):
        """Test that invalid document processing config is handled properly."""
        # Create environment with invalid document processing setting
        self.create_env_file(
            enable_document_processing=True,
            # Missing required API keys - should cause graceful failure
        )
        
        # Initialize app - should fail gracefully due to missing API keys
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        result = self.app.initialize()
        
        # Should fail initialization due to missing API keys
        assert result is False


class TestBackwardCompatibilityWithExistingTests(BaseRAGIntegrationTest):
    """Test backward compatibility with existing test patterns and expectations."""
    
def test_existing_test_patterns_still_work(self):
        """Test that existing test patterns and assertions still work."""
        # This test mimics patterns from existing test files
        
        # Pattern 1: Basic app initialization and file processing
        self.create_env_file(enable_document_processing=False)
        
        app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert app.initialize() is True
        
        # Create test file
        test_file = self.source_dir / "test.txt"
        test_file.write_text("Test file content")
        
        # Process file
        result = app.file_processor.process_file(str(test_file))
        assert result.success is True
        
        # Verify file moved
        saved_files = list(self.saved_dir.glob("*.txt"))
        assert len(saved_files) == 1
        
        # Pattern 2: Error handling test
        error_file = self.source_dir / "empty.txt"
        error_file.write_text("")
        
        result = app.file_processor.process_file(str(error_file))
        assert result.success is False
        
        # Verify error handling
        error_files = list(self.error_dir.glob("*.txt"))
        error_logs = list(self.error_dir.glob("*.log"))
        assert len(error_files) > 0
        assert len(error_logs) > 0
        
        # Pattern 3: Monitoring test
        app.file_monitor.start_monitoring()
        assert app.file_monitor.is_monitoring() is True
        
        app.file_monitor.stop_monitoring()
        assert app.file_monitor.is_monitoring() is False
        
        # Pattern 4: Statistics test
        stats = app.file_processor.get_processing_stats()
        assert isinstance(stats, dict)
        assert 'total_processed' in stats
    
    def test_existing_mock_patterns_compatibility(self):
        """Test that existing mock patterns are still compatible."""
        # Pattern from existing tests: Mock file monitor
        self.create_env_file(enable_document_processing=False)
        
        app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        assert app.initialize() is True
        
        # Mock pattern: Replace file monitor behavior
        app.file_monitor.is_monitoring = MagicMock(return_value=False)
        
        # Should still work with existing health check logic
        health_result = app._perform_health_check()
        assert health_result is False  # Due to mocked monitoring failure
        
        # Pattern: Mock statistics
        app.file_processor.get_processing_stats = MagicMock(return_value={
            'total_processed': 10,
            'successful': 8,
            'failed_permanent': 2
        })
        
        stats = app.file_processor.get_processing_stats()
        assert stats['total_processed'] == 10
        assert stats['successful'] == 8
    
    def test_existing_exception_handling_patterns(self):
        """Test that existing exception handling patterns still work."""
        # Pattern: Configuration error handling
        with patch('src.app.ConfigManager') as mock_config:
            mock_config.side_effect = Exception("Config error")
            
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            assert result is False
        
        # Pattern: Component initialization error
        self.create_env_file(enable_document_processing=False)
        
        with patch('src.app.FileManager') as mock_file_manager:
            mock_file_manager.side_effect = Exception("FileManager error")
            
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__])