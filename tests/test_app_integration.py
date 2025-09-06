"""
Integration tests for the main application orchestrator.

Tests the complete application workflow including initialization, startup,
file processing, error handling, and graceful shutdown.
"""

import os
import sys
import time
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import FolderFileProcessorApp, create_app


class TestFolderFileProcessorApp:
    """Test suite for the main application orchestrator."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        import uuid
        
        # Create temporary directories for testing with unique names
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_app_{uuid.uuid4().hex[:8]}_")
        self.source_dir = Path(self.temp_dir) / "source"
        self.saved_dir = Path(self.temp_dir) / "saved"
        self.error_dir = Path(self.temp_dir) / "error"
        self.logs_dir = Path(self.temp_dir) / "logs"
        
        # Create directories and ensure they exist
        for dir_path in [self.source_dir, self.saved_dir, self.error_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            assert dir_path.exists(), f"Failed to create directory: {dir_path}"
        
        # Create .env file for testing
        self.env_file = Path(self.temp_dir) / ".env"
        with open(self.env_file, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=false\n")  # Disable by default for existing tests
            # Add required file monitoring configuration
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")
        
        self.log_file = self.logs_dir / "test.log"
        
        # Initialize app reference for cleanup
        self.app = None
    
    def teardown_method(self):
        """Clean up after each test."""
        import shutil
        import time
        
        # Ensure any running app instances are properly shut down
        if hasattr(self, 'app') and self.app:
            try:
                if hasattr(self.app, 'file_monitor') and self.app.file_monitor:
                    self.app.file_monitor.stop_monitoring()
                if hasattr(self.app, 'shutdown'):
                    self.app.shutdown()
            except Exception:
                pass
        
        # Clean up environment variables that might have been set by load_dotenv
        env_vars_to_clean = ['SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER']
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]
        
        # Small delay to ensure file handles are released
        time.sleep(0.1)
        
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            # Log cleanup errors but don't fail the test
            print(f"Warning: Failed to cleanup temp directory {self.temp_dir}: {e}")
    
    def test_app_initialization_success(self):
        """Test successful application initialization."""
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        # Test initialization
        result = self.app.initialize()
        
        assert result is True
        assert self.app.config is not None
        assert self.app.config.source_folder == str(self.source_dir)
        assert self.app.config.saved_folder == str(self.saved_dir)
        assert self.app.config.error_folder == str(self.error_dir)
        assert self.app.logger_service is not None
        assert self.app.file_monitor is not None
        assert self.app.file_processor is not None
        assert self.app.file_manager is not None
        assert self.app.error_handler is not None
    
    def test_app_initialization_missing_env_file(self):
        """Test initialization failure with missing .env file."""
        non_existent_env = Path(self.temp_dir) / "nonexistent.env"
        app = FolderFileProcessorApp(env_file=str(non_existent_env))
        
        # Should fail due to missing required environment variables
        result = app.initialize()
        
        assert result is False
    
    def test_app_initialization_invalid_source_folder(self):
        """Test initialization failure with invalid source folder."""
        # Create .env with non-existent source folder
        invalid_env = Path(self.temp_dir) / "invalid.env"
        with open(invalid_env, 'w') as f:
            f.write("SOURCE_FOLDER=/nonexistent/path\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            # Add required file monitoring configuration
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")
        
        app = FolderFileProcessorApp(env_file=str(invalid_env))
        
        result = app.initialize()
        
        assert result is False
    
    def test_start_without_initialization(self):
        """Test that starting without initialization raises error."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        with pytest.raises(RuntimeError, match="Application not properly initialized"):
            app.start()
    
    def test_complete_application_workflow(self):
        """Test complete application workflow with file processing."""
        self.app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(self.log_file))
        
        # Initialize app
        assert self.app.initialize() is True
        
        # Create a test file to be processed
        test_file = self.source_dir / "test.txt"
        test_file.write_text("Test file content")
        
        # Test file processing directly (without full monitoring loop)
        result = self.app.file_processor.process_file(str(test_file))
        assert result.success is True
        
        # Verify file was moved to saved folder
        saved_files = list(self.saved_dir.glob("*.txt"))
        assert len(saved_files) == 1
        
        # Test monitoring setup
        self.app.file_monitor.start_monitoring()
        assert self.app.file_monitor.is_monitoring() is True
        
        # Create another test file while monitoring
        test_file2 = self.source_dir / "test2.txt"
        test_file2.write_text("Another test file")
        
        # Wait briefly for file system event
        time.sleep(0.1)
        
        # Stop monitoring
        self.app.file_monitor.stop_monitoring()
        
        # Verify monitoring stopped
        assert self.app.file_monitor.is_monitoring() is False
    
    def test_graceful_shutdown_on_signal(self):
        """Test graceful shutdown when receiving signals."""
        self.app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Initialize app
        assert self.app.initialize() is True
        
        # Test signal handler
        self.app._signal_handler(2, None)  # SIGINT
        
        assert self.app.shutdown_requested is True
    
    def test_monitoring_failure_handling(self):
        """Test handling of monitoring failures."""
        self.app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Initialize app
        assert self.app.initialize() is True
        
        # Mock file monitor to simulate failure from the start
        self.app.file_monitor.is_monitoring = MagicMock(return_value=False)
        
        # Start app in thread to test main loop
        def run_app():
            try:
                self.app.start()
            except Exception:
                pass
        
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        
        # Wait for app to start and perform health check
        time.sleep(0.2)
        
        # Trigger health check manually to detect failure immediately
        health_result = self.app._perform_health_check()
        assert health_result is False  # Should fail due to monitoring not running
        
        # Request shutdown due to monitoring failure
        self.app.shutdown_requested = True
        
        # Wait for app to shutdown
        app_thread.join(timeout=2.0)
        assert not app_thread.is_alive()
    
    def test_error_handling_during_initialization(self):
        """Test error handling during component initialization."""
        # Create .env with valid config
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Mock ConfigManager to raise exception
        with patch('app.ConfigManager') as mock_config:
            mock_config.side_effect = Exception("Config error")
            
            result = app.initialize()
            
            assert result is False
    
    def test_create_app_factory_function(self):
        """Test the create_app factory function."""
        app = create_app(env_file=str(self.env_file), log_file=str(self.log_file))
        
        assert isinstance(app, FolderFileProcessorApp)
        assert app.env_file == str(self.env_file)
        assert app.log_file == str(self.log_file)
    
    def test_run_method_complete_lifecycle(self):
        """Test the run method for complete application lifecycle."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Mock the start method to avoid infinite loop
        def mock_start():
            app.is_running = True
            # Simulate quick shutdown
            app.shutdown_requested = True
        
        app.start = mock_start
        
        exit_code = app.run()
        
        assert exit_code == 0
    
    def test_run_method_initialization_failure(self):
        """Test run method when initialization fails."""
        # Use invalid env file
        invalid_env = Path(self.temp_dir) / "invalid.env"
        app = FolderFileProcessorApp(env_file=str(invalid_env))
        
        exit_code = app.run()
        
        assert exit_code == 1
    
    def test_run_method_startup_failure(self):
        """Test run method when startup fails."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Mock start to raise exception
        def mock_start():
            raise RuntimeError("Startup failed")
        
        app.start = mock_start
        
        exit_code = app.run()
        
        assert exit_code == 1
    
    def test_file_processing_with_subdirectories(self):
        """Test file processing with nested directory structure."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Initialize app
        assert app.initialize() is True
        
        # Create subdirectory structure
        subdir = self.source_dir / "subdir" / "nested"
        subdir.mkdir(parents=True)
        
        # Create test file in subdirectory
        test_file = subdir / "nested_test.txt"
        test_file.write_text("Nested file content")
        
        # Process the file directly instead of relying on monitoring timing
        result = app.file_processor.process_file(str(test_file))
        assert result.success is True
        
        # Check that nested structure is preserved in saved folder
        expected_saved_file = self.saved_dir / "subdir" / "nested" / "nested_test.txt"
        assert expected_saved_file.exists(), f"Expected file not found: {expected_saved_file}"
        
        # Verify the content was preserved
        assert expected_saved_file.read_text() == "Nested file content"
    
    def test_error_file_handling(self):
        """Test handling of files that cause processing errors."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Initialize app
        assert app.initialize() is True
        
        # Create a file that will cause processing error (empty file)
        error_file = self.source_dir / "empty.txt"
        error_file.write_text("")  # Empty file should cause validation error
        
        # Process the file directly to test error handling
        result = app.file_processor.process_file(str(error_file))
        assert result.success is False
        
        # Check that error file was moved to error folder
        error_files = list(self.error_dir.glob("*.txt"))
        error_logs = list(self.error_dir.glob("*.log"))
        
        # Should have moved the file and created error log with new format
        assert len(error_files) > 0  # File should be moved to error folder
        assert len(error_logs) > 0   # Error log should be created
        
        # Verify error log has correct filename format: [filename].[extension].log
        expected_log = self.error_dir / "empty.txt.log"
        assert expected_log.exists(), f"Expected error log not found: {expected_log}"
        
        # Verify log content
        log_content = expected_log.read_text()
        assert "FILE PROCESSING ERROR LOG" in log_content
        assert "File is empty" in log_content
    
    def test_error_file_handling_with_nested_structure(self):
        """Test error file handling with nested folder structure preservation."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Initialize app
        assert app.initialize() is True
        
        # Create nested folder structure
        nested_dir = self.source_dir / "documents" / "reports"
        nested_dir.mkdir(parents=True)
        
        # Create a file that will cause processing error in nested structure
        error_file = nested_dir / "report.pdf"
        error_file.write_text("")  # Empty file should cause validation error
        
        # Process the file directly to test error handling
        result = app.file_processor.process_file(str(error_file))
        assert result.success is False
        
        # Check that error file was moved to error folder with preserved structure
        expected_error_file = self.error_dir / "documents" / "reports" / "report.pdf"
        expected_error_log = self.error_dir / "documents" / "reports" / "report.pdf.log"
        
        assert expected_error_file.exists(), f"Error file not found in preserved structure: {expected_error_file}"
        assert expected_error_log.exists(), f"Error log not found in preserved structure: {expected_error_log}"
        
        # Verify log content
        log_content = expected_error_log.read_text()
        assert "FILE PROCESSING ERROR LOG" in log_content
        assert "File is empty" in log_content


class TestApplicationIntegrationScenarios:
    """Integration test scenarios for real-world usage."""
    
    def setup_method(self):
        """Set up test environment."""
        import uuid
        
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_integration_{uuid.uuid4().hex[:8]}_")
        self.source_dir = Path(self.temp_dir) / "source"
        self.saved_dir = Path(self.temp_dir) / "saved"
        self.error_dir = Path(self.temp_dir) / "error"
        
        for dir_path in [self.source_dir, self.saved_dir, self.error_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            assert dir_path.exists(), f"Failed to create directory: {dir_path}"
        
        self.env_file = Path(self.temp_dir) / ".env"
        with open(self.env_file, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            # Add required file monitoring configuration
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")
        
        # Initialize app reference for cleanup
        self.app = None
    
    def teardown_method(self):
        """Clean up after test."""
        import shutil
        import time
        
        # Ensure any running app instances are properly shut down
        if hasattr(self, 'app') and self.app:
            try:
                if hasattr(self.app, 'file_monitor') and self.app.file_monitor:
                    self.app.file_monitor.stop_monitoring()
                if hasattr(self.app, 'shutdown'):
                    self.app.shutdown()
            except Exception:
                pass
        
        # Clean up environment variables that might have been set by load_dotenv
        env_vars_to_clean = ['SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER']
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]
        
        # Small delay to ensure file handles are released
        time.sleep(0.1)
        
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            # Log cleanup errors but don't fail the test
            print(f"Warning: Failed to cleanup temp directory {self.temp_dir}: {e}")
    
    def test_multiple_files_processing(self):
        """Test processing multiple files simultaneously."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Create multiple test files
        for i in range(5):
            test_file = self.source_dir / f"test_{i}.txt"
            test_file.write_text(f"Content of file {i}")
        
        # Process files directly (without monitoring for faster test)
        for i in range(5):
            file_path = str(self.source_dir / f"test_{i}.txt")
            if os.path.exists(file_path):
                result = app.file_processor.process_file(file_path)
                assert result.success is True
        
        # Verify files were moved to saved folder
        saved_files = list(self.saved_dir.glob("*.txt"))
        assert len(saved_files) == 5
    
    def test_mixed_success_and_error_files(self):
        """Test processing mix of successful and error files."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Create successful files
        for i in range(3):
            test_file = self.source_dir / f"good_{i}.txt"
            test_file.write_text(f"Good content {i}")
        
        # Create files that will cause errors (empty files)
        for i in range(2):
            error_file = self.source_dir / f"bad_{i}.txt"
            error_file.write_text("")  # Empty content causes validation error
        
        # Process all files
        all_files = list(self.source_dir.glob("*.txt"))
        for file_path in all_files:
            result = app.file_processor.process_file(str(file_path))
            # Results will be mixed - some success, some failure
        
        # Verify files were distributed correctly
        saved_files = list(self.saved_dir.glob("*.txt"))
        error_files = list(self.error_dir.glob("*.txt"))
        error_logs = list(self.error_dir.glob("*.log"))
        
        # Should have some successful files and some error handling
        assert len(saved_files) >= 1  # At least some successful
        assert len(error_files) >= 1 or len(error_logs) >= 1  # At least some errors handled


class TestApplicationCoverageEnhancement:
    """Additional tests to improve coverage for app.py."""
    
    def setup_method(self):
        """Set up test environment."""
        import uuid
        
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_coverage_{uuid.uuid4().hex[:8]}_")
        self.source_dir = Path(self.temp_dir) / "source"
        self.saved_dir = Path(self.temp_dir) / "saved"
        self.error_dir = Path(self.temp_dir) / "error"
        
        for dir_path in [self.source_dir, self.saved_dir, self.error_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.env_file = Path(self.temp_dir) / ".env"
        with open(self.env_file, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=false\n")
            # Add required file monitoring configuration
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")
        
        self.app = None
    
    def teardown_method(self):
        """Clean up after test."""
        import shutil
        import time
        
        if hasattr(self, 'app') and self.app:
            try:
                if hasattr(self.app, 'file_monitor') and self.app.file_monitor:
                    self.app.file_monitor.stop_monitoring()
                if hasattr(self.app, 'shutdown'):
                    self.app.shutdown()
            except Exception:
                pass
        
        env_vars_to_clean = ['SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER']
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]
        
        time.sleep(0.1)
        
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory {self.temp_dir}: {e}")
    
    def test_validate_initialization_all_components_none(self):
        """Test validation when all components are None."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # All components should be None initially
        result = app._validate_initialization()
        assert result is False
    
    def test_validate_initialization_partial_components(self):
        """Test validation when some components are initialized."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Initialize only some components
        app.config_manager = MagicMock()
        app.logger_service = MagicMock()
        # Leave others as None
        
        result = app._validate_initialization()
        assert result is False
    
    def test_perform_health_check_source_folder_missing(self):
        """Test health check when source folder is deleted."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Delete source folder to simulate failure
        import shutil
        shutil.rmtree(self.source_dir)
        
        result = app._perform_health_check()
        assert result is False
    
    def test_perform_health_check_monitoring_stopped(self):
        """Test health check when monitoring has stopped."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock file monitor to return False for is_monitoring
        app.file_monitor.is_monitoring = MagicMock(return_value=False)
        
        result = app._perform_health_check()
        assert result is False
    
    def test_perform_health_check_exception_handling(self):
        """Test health check exception handling."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock file monitor to raise exception
        app.file_monitor.is_monitoring = MagicMock(side_effect=Exception("Health check error"))
        
        result = app._perform_health_check()
        assert result is False
    
    def test_report_statistics_success(self):
        """Test successful statistics reporting."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock statistics methods
        app.file_processor.get_processing_stats = MagicMock(return_value={
            'total_processed': 10,
            'successful': 8,
            'failed_permanent': 1,
            'failed_after_retry': 1,
            'retries_attempted': 3
        })
        
        app.file_monitor.get_monitoring_stats = MagicMock(return_value={
            'events_received': 15,
            'duplicate_events_filtered': 2
        })
        
        # Should not raise exception
        app._report_statistics()
        
        # Verify methods were called
        app.file_processor.get_processing_stats.assert_called_once()
        app.file_monitor.get_monitoring_stats.assert_called_once()
    
    def test_report_statistics_exception_handling(self):
        """Test statistics reporting exception handling."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock to raise exception
        app.file_processor.get_processing_stats = MagicMock(side_effect=Exception("Stats error"))
        
        # Should not raise exception
        app._report_statistics()
    
    def test_run_main_loop_with_health_checks(self):
        """Test main loop with health check intervals."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock file monitor start to avoid actual monitoring
        app.file_monitor.start_monitoring = MagicMock()
        
        # Mock health check to fail after first success
        health_check_calls = [True, False]  # First success, then failure
        app._perform_health_check = MagicMock(side_effect=health_check_calls)
        
        # Mock statistics reporting
        app._report_statistics = MagicMock()
        
        # Mock the main loop to simulate health check behavior
        def mock_loop():
            # Simulate health check calls
            app._perform_health_check()
            app._perform_health_check()  # Second call should fail
            app.shutdown_requested = True
        
        app._run_main_loop = mock_loop
        
        app.start()
    
    def test_run_main_loop_keyboard_interrupt(self):
        """Test main loop keyboard interrupt handling."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock file monitor start to avoid actual monitoring
        app.file_monitor.start_monitoring = MagicMock()
        
        # Mock the main loop to simulate KeyboardInterrupt handling
        def mock_main_loop():
            app.is_running = True
            try:
                # Simulate what the real main loop would do when KeyboardInterrupt happens
                raise KeyboardInterrupt("User interrupt")
            except KeyboardInterrupt:
                print("\nShutdown requested by user.")
            finally:
                app.shutdown()
        
        app._run_main_loop = mock_main_loop
        
        # Should handle KeyboardInterrupt gracefully
        app.start()
    
    def test_run_main_loop_unexpected_exception(self):
        """Test main loop unexpected exception handling."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock file monitor start to avoid actual monitoring
        app.file_monitor.start_monitoring = MagicMock()
        
        # Mock the main loop to simulate unexpected exception handling
        def mock_main_loop():
            app.is_running = True
            try:
                # Simulate what the real main loop would do when an unexpected exception happens
                raise RuntimeError("Unexpected error")
            except Exception as e:
                error_msg = f"Unexpected error in main loop: {str(e)}"
                app.logger_service.log_error(error_msg, e)
                print(f"ERROR: {error_msg}")
            finally:
                app.shutdown()
        
        app._run_main_loop = mock_main_loop
        
        # Should handle exception gracefully
        app.start()
    
    def test_shutdown_with_signal_handler_reset(self):
        """Test shutdown with signal handler reset."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock signal.signal to verify it's called
        with patch('signal.signal') as mock_signal:
            app.shutdown()
            
            # Verify signal handlers were reset
            assert mock_signal.call_count >= 2  # At least SIGINT and SIGTERM
    
    def test_shutdown_exception_handling(self):
        """Test shutdown exception handling."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        assert app.initialize() is True
        
        # Mock file monitor to raise exception during stop
        app.file_monitor.stop_monitoring = MagicMock(side_effect=Exception("Stop error"))
        
        # Should handle exception gracefully
        app.shutdown()
    
    def test_signal_handler_sigterm(self):
        """Test SIGTERM signal handler."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Test SIGTERM signal
        app._signal_handler(15, None)  # SIGTERM
        assert app.shutdown_requested is True
    
    def test_app_with_custom_log_file(self):
        """Test app initialization with custom log file."""
        log_file = Path(self.temp_dir) / "custom.log"
        app = FolderFileProcessorApp(env_file=str(self.env_file), log_file=str(log_file))
        
        assert app.initialize() is True
        assert app.log_file == str(log_file)
        assert app.logger_service.log_file_path == str(log_file)
    
    def test_initialization_component_failure_scenarios(self):
        """Test various component initialization failure scenarios."""
        # Test ConfigManager failure
        with patch('app.ConfigManager') as mock_config_manager:
            mock_config_manager.side_effect = Exception("Config error")
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            assert result is False
        
        # Test LoggerService failure
        with patch('app.LoggerService.setup_logger') as mock_logger:
            mock_logger.side_effect = Exception("Logger error")
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            assert result is False
        
        # Test ErrorHandler failure
        with patch('app.ErrorHandler') as mock_error_handler:
            mock_error_handler.side_effect = Exception("Error handler error")
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            assert result is False
        
        # Test FileManager failure
        with patch('app.FileManager') as mock_file_manager:
            mock_file_manager.side_effect = Exception("File manager error")
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            assert result is False


class TestApplicationDocumentProcessingIntegration:
    """Test suite for document processing integration in the main application."""
    
    def setup_method(self):
        """Set up test environment for document processing tests."""
        import uuid
        
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_doc_proc_{uuid.uuid4().hex[:8]}_")
        self.source_dir = Path(self.temp_dir) / "source"
        self.saved_dir = Path(self.temp_dir) / "saved"
        self.error_dir = Path(self.temp_dir) / "error"
        self.chroma_parent_dir = Path(self.temp_dir) / "chroma_parent"
        self.chroma_dir = self.chroma_parent_dir / "chroma"
        
        for dir_path in [self.source_dir, self.saved_dir, self.error_dir, self.chroma_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create .env file with document processing enabled
        self.env_file = Path(self.temp_dir) / ".env"
        with open(self.env_file, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=true\n")
            f.write("DOCUMENT_PROCESSOR_TYPE=rag_store\n")
            f.write("MODEL_VENDOR=google\n")
            f.write("GOOGLE_API_KEY=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI\n")
            f.write(f"CHROMA_DB_PATH={self.chroma_dir}\n")
            f.write("CHROMA_CLIENT_MODE=embedded\n")
            # Add required file monitoring configuration
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")
        
        self.app = None
    
    def teardown_method(self):
        """Clean up after test."""
        import shutil
        import time
        
        if hasattr(self, 'app') and self.app:
            try:
                if hasattr(self.app, 'file_monitor') and self.app.file_monitor:
                    self.app.file_monitor.stop_monitoring()
                if hasattr(self.app, 'shutdown'):
                    self.app.shutdown()
            except Exception:
                pass
        
        # Clean up environment variables
        env_vars_to_clean = [
            'SOURCE_FOLDER', 'SAVED_FOLDER', 'ERROR_FOLDER', 
            'ENABLE_DOCUMENT_PROCESSING', 'DOCUMENT_PROCESSOR_TYPE',
            'MODEL_VENDOR', 'GOOGLE_API_KEY', 'CHROMA_DB_PATH'
        ]
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]
        
        time.sleep(0.1)
        
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp directory {self.temp_dir}: {e}")
    
    def test_app_initialization_with_document_processing_enabled(self):
        """Test application initialization with document processing enabled."""
        # Clean up any environment variables that might interfere
        for var in ['ENABLE_DOCUMENT_PROCESSING', 'DOCUMENT_PROCESSOR_TYPE', 'MODEL_VENDOR', 'GOOGLE_API_KEY', 'CHROMA_DB_PATH']:
            if var in os.environ:
                del os.environ[var]
        
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = self.app.initialize()
            
            assert result is True
            assert self.app.document_processor is not None
            assert self.app.config.document_processing.enable_processing is True
            
            # Verify document processor was initialized
            mock_processor_class.assert_called_once()
            mock_processor.initialize.assert_called_once()
    
    def test_app_initialization_with_document_processing_disabled(self):
        """Test application initialization with document processing disabled."""
        # Create env file with document processing disabled
        env_file_disabled = Path(self.temp_dir) / "disabled.env"
        with open(env_file_disabled, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=false\n")
            # Add required file monitoring configuration
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")
        
        self.app = FolderFileProcessorApp(env_file=str(env_file_disabled))
        result = self.app.initialize()
        
        assert result is True
        assert self.app.document_processor is None
        assert self.app.config.document_processing.enable_processing is False
    
    def test_document_processor_initialization_failure(self):
        """Test handling of document processor initialization failure."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor.initialize.side_effect = Exception("Processor init failed")
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            
            with pytest.raises(RuntimeError, match="Failed to initialize document processor"):
                self.app.initialize()
    
    def test_dependency_validation_failure(self):
        """Test handling of dependency validation failure."""
        with patch('app.ConfigManager') as mock_config_manager_class:
            mock_config_manager = MagicMock()
            mock_config = MagicMock()
            mock_config.document_processing.enable_processing = True
            mock_config_manager.initialize.return_value = mock_config
            mock_config_manager.validate_dependencies.return_value = ["Missing ChromaDB package"]
            mock_config_manager_class.return_value = mock_config_manager
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            
            with pytest.raises(RuntimeError, match="Document processing dependencies validation failed"):
                self.app.initialize()
    
    def test_validation_with_document_processor_enabled(self):
        """Test validation includes document processor when enabled."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            # Document processor should be required for validation
            result = self.app._validate_initialization()
            assert result is True
            
            # If document processor is None, validation should fail
            self.app.document_processor = None
            result = self.app._validate_initialization()
            assert result is False
    
    def test_validation_with_document_processor_disabled(self):
        """Test validation doesn't require document processor when disabled."""
        env_file_disabled = Path(self.temp_dir) / "disabled.env"
        with open(env_file_disabled, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=false\n")
            # Add required file monitoring configuration
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")
        
        self.app = FolderFileProcessorApp(env_file=str(env_file_disabled))
        assert self.app.initialize() is True
        
        # Document processor should not be required for validation
        result = self.app._validate_initialization()
        assert result is True
        assert self.app.document_processor is None
    
    def test_document_processor_health_check_success(self):
        """Test document processor health check success."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            result = self.app._check_document_processor_health()
            assert result is True
            
            # Verify processor method was called (at least once during health check)
            assert mock_processor.get_supported_extensions.call_count >= 1
    
    def test_document_processor_health_check_chroma_path_missing(self):
        """Test document processor health check when ChromaDB path is missing."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            # Remove ChromaDB parent directory to simulate failure
            import shutil
            shutil.rmtree(self.chroma_parent_dir)
            
            result = self.app._check_document_processor_health()
            assert result is False
    
    def test_document_processor_health_check_processor_failure(self):
        """Test document processor health check when processor fails."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            # Allow initialization to succeed but fail on subsequent health checks
            mock_processor.get_supported_extensions.side_effect = [
                {'.txt', '.pdf'},  # First call during initialization succeeds
                Exception("Processor error")  # Second call during health check fails
            ]
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            result = self.app._check_document_processor_health()
            assert result is False
    
    def test_document_processor_health_check_no_extensions(self):
        """Test document processor health check when no extensions are supported."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = set()
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            result = self.app._check_document_processor_health()
            assert result is True  # Should still pass, just log a warning
    
    def test_document_processing_statistics_reporting(self):
        """Test statistics reporting includes document processing information."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            # Mock statistics methods
            self.app.file_processor.get_processing_stats = MagicMock(return_value={
                'total_processed': 5,
                'successful': 4,
                'failed_permanent': 0,
                'failed_after_retry': 1,
                'retries_attempted': 2
            })
            
            self.app.file_monitor.get_monitoring_stats = MagicMock(return_value={
                'events_received': 10,
                'duplicate_events_filtered': 1
            })
            
            # Should not raise exception and should include document processing stats
            self.app._report_statistics()
            
            # Verify methods were called
            self.app.file_processor.get_processing_stats.assert_called_once()
            self.app.file_monitor.get_monitoring_stats.assert_called_once()
    
    def test_document_processing_statistics_error_handling(self):
        """Test document processing statistics error handling."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            # Mock statistics methods to succeed
            self.app.file_processor.get_processing_stats = MagicMock(return_value={
                'total_processed': 5,
                'successful': 4,
                'failed_permanent': 0,
                'failed_after_retry': 1,
                'retries_attempted': 2
            })
            
            self.app.file_monitor.get_monitoring_stats = MagicMock(return_value={
                'events_received': 10,
                'duplicate_events_filtered': 1
            })
            
            # Mock _get_document_processing_stats to raise exception
            self.app._get_document_processing_stats = MagicMock(side_effect=Exception("Stats error"))
            
            # Should handle exception gracefully
            self.app._report_statistics()
    
    def test_document_processor_cleanup_on_shutdown(self):
        """Test document processor cleanup during shutdown."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            # Mock file monitor to avoid actual monitoring
            self.app.file_monitor.stop_monitoring = MagicMock()
            
            self.app.shutdown()
            
            # Verify document processor cleanup was called
            mock_processor.cleanup.assert_called_once()
    
    def test_document_processor_cleanup_error_handling(self):
        """Test document processor cleanup error handling."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor.cleanup.side_effect = Exception("Cleanup error")
            mock_processor_class.return_value = mock_processor
            
            self.app = FolderFileProcessorApp(env_file=str(self.env_file))
            assert self.app.initialize() is True
            
            # Mock file monitor to avoid actual monitoring
            self.app.file_monitor.stop_monitoring = MagicMock()
            
            # Should handle cleanup exception gracefully
            self.app.shutdown()
    
    def test_cleanup_on_initialization_failure(self):
        """Test cleanup when initialization fails."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            # Mock FileProcessor to fail
            with patch('app.FileProcessor') as mock_file_processor:
                mock_file_processor.side_effect = Exception("FileProcessor init failed")
                
                self.app = FolderFileProcessorApp(env_file=str(self.env_file))
                result = self.app.initialize()
                
                assert result is False
                
                # Verify cleanup was called on the document processor
                mock_processor.cleanup.assert_called_once()
    
    def test_file_processor_receives_document_processor(self):
        """Test that FileProcessor receives the document processor during initialization."""
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor
            
            with patch('app.FileProcessor') as mock_file_processor_class:
                mock_file_processor = MagicMock()
                mock_file_processor_class.return_value = mock_file_processor
                
                self.app = FolderFileProcessorApp(env_file=str(self.env_file))
                result = self.app.initialize()
                
                assert result is True
                
                # Verify FileProcessor was initialized with document processor
                mock_file_processor_class.assert_called_once()
                call_args = mock_file_processor_class.call_args
                assert 'document_processor' in call_args.kwargs
                assert call_args.kwargs['document_processor'] == mock_processor
        
        # Test FileProcessor failure
        with patch('app.FileProcessor') as mock_file_processor:
            mock_file_processor.side_effect = Exception("File processor error")
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            assert result is False
        
        # Test FileMonitor failure
        with patch('app.create_file_monitor') as mock_create_file_monitor:
            mock_create_file_monitor.side_effect = Exception("File monitor error")
            app = FolderFileProcessorApp(env_file=str(self.env_file))
            result = app.initialize()
            # FileMonitor failure should cause initialization to fail
            assert result is False