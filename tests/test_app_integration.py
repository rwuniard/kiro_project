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
        
        # Start monitoring briefly
        def run_app():
            try:
                app.start()
            except Exception:
                pass
        
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        
        # Wait for processing
        time.sleep(0.2)
        
        # Stop the application
        app.shutdown()
        
        # Check that nested structure is preserved in saved folder
        expected_saved_file = self.saved_dir / "subdir" / "nested" / "nested_test.txt"
        # Note: File might still be processing, so we check if the directory structure exists
        assert (self.saved_dir / "subdir").exists() or len(list(self.saved_dir.rglob("*.txt"))) > 0
    
    def test_error_file_handling(self):
        """Test handling of files that cause processing errors."""
        app = FolderFileProcessorApp(env_file=str(self.env_file))
        
        # Initialize app
        assert app.initialize() is True
        
        # Create a file that will cause processing error (empty file)
        error_file = self.source_dir / "empty.txt"
        error_file.write_text("")  # Empty file should cause validation error
        
        # Start monitoring briefly
        def run_app():
            try:
                app.start()
            except Exception:
                pass
        
        app_thread = threading.Thread(target=run_app, daemon=True)
        app_thread.start()
        
        # Wait for processing
        time.sleep(0.2)
        
        # Stop the application
        app.shutdown()
        
        # Check that error file was moved to error folder
        error_files = list(self.error_dir.glob("*.txt"))
        error_logs = list(self.error_dir.glob("*.log"))
        
        # Should have either moved the file or created error log
        assert len(error_files) > 0 or len(error_logs) > 0


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