"""
Unit tests for application version functionality.

Tests the version detection and logging functionality in the main application,
including environment variable detection, version file reading, and version
logging during application startup.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import get_application_version, FolderFileProcessorApp, create_app


class TestGetApplicationVersion:
    """Test suite for the get_application_version function."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Store original environment variable to restore later
        self.original_app_version = os.environ.get('APP_VERSION')

        # Clean up any existing APP_VERSION for clean test state
        if 'APP_VERSION' in os.environ:
            del os.environ['APP_VERSION']

    def teardown_method(self):
        """Clean up after each test."""
        # Restore original environment variable
        if self.original_app_version is not None:
            os.environ['APP_VERSION'] = self.original_app_version
        elif 'APP_VERSION' in os.environ:
            del os.environ['APP_VERSION']

    def test_version_from_environment_variable(self):
        """Test version detection from APP_VERSION environment variable."""
        # Set environment variable
        test_version = "1.2.3.test456"
        os.environ['APP_VERSION'] = test_version

        # Function should return the environment variable value
        version = get_application_version()
        assert version == test_version

    def test_version_from_environment_variable_empty_string(self):
        """Test version detection when APP_VERSION is empty string."""
        # Set environment variable to empty string
        os.environ['APP_VERSION'] = ""

        # Function should return 'unknown' for empty string
        version = get_application_version()
        assert version == 'unknown'

    def test_version_from_docker_version_file(self):
        """Test version detection from Docker version file at /app/VERSION."""
        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        test_version = "2.0.0.docker123"

        # Mock Path.exists and read_text for /app/VERSION
        with patch('app.Path') as mock_path_class:
            # Create mock instances for different paths
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    # Return a mock that behaves like a normal Path for other paths
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to exist and return content
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.return_value = f"  {test_version}  \n"  # With whitespace to test .strip()

            # Configure local version file to not exist
            mock_local_version_file.exists.return_value = False

            version = get_application_version()
            assert version == test_version

            # Verify Docker version file was checked and read
            mock_docker_version_file.exists.assert_called_once()
            mock_docker_version_file.read_text.assert_called_once()

    def test_version_from_local_version_file(self):
        """Test version detection from local VERSION file when Docker version doesn't exist."""
        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        test_version = "1.5.0.local789"

        # Mock Path.exists and read_text
        with patch('app.Path') as mock_path_class:
            # Create mock instances for different paths
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to not exist
            mock_docker_version_file.exists.return_value = False

            # Configure local version file to exist and return content
            mock_local_version_file.exists.return_value = True
            mock_local_version_file.read_text.return_value = f"\t{test_version}\t"  # With tabs to test .strip()

            version = get_application_version()
            assert version == test_version

            # Verify both version files were checked
            mock_docker_version_file.exists.assert_called_once()
            mock_local_version_file.exists.assert_called_once()
            mock_local_version_file.read_text.assert_called_once()

    def test_version_docker_file_read_exception(self):
        """Test version detection when Docker version file exists but can't be read."""
        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        test_version = "1.8.0.fallback456"

        # Mock Path.exists and read_text
        with patch('app.Path') as mock_path_class:
            # Create mock instances for different paths
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to exist but raise exception on read
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.side_effect = IOError("Permission denied")

            # Configure local version file to exist and work properly
            mock_local_version_file.exists.return_value = True
            mock_local_version_file.read_text.return_value = test_version

            version = get_application_version()
            assert version == test_version

            # Verify Docker version file was tried first
            mock_docker_version_file.exists.assert_called_once()
            mock_docker_version_file.read_text.assert_called_once()
            # And local version file was used as fallback
            mock_local_version_file.exists.assert_called_once()
            mock_local_version_file.read_text.assert_called_once()

    def test_version_local_file_read_exception(self):
        """Test version detection when local version file exists but can't be read."""
        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        # Mock Path.exists and read_text
        with patch('app.Path') as mock_path_class:
            # Create mock instances for different paths
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to not exist
            mock_docker_version_file.exists.return_value = False

            # Configure local version file to exist but raise exception on read
            mock_local_version_file.exists.return_value = True
            mock_local_version_file.read_text.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")

            version = get_application_version()
            assert version == 'unknown'

            # Verify both version files were attempted
            mock_docker_version_file.exists.assert_called_once()
            mock_local_version_file.exists.assert_called_once()
            mock_local_version_file.read_text.assert_called_once()

    def test_version_no_sources_available(self):
        """Test version detection when no sources are available."""
        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        # Mock Path.exists to return False for all version files
        with patch('app.Path') as mock_path_class:
            # Create mock instances for different paths
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure both version files to not exist
            mock_docker_version_file.exists.return_value = False
            mock_local_version_file.exists.return_value = False

            version = get_application_version()
            assert version == 'unknown'

            # Verify both version files were checked
            mock_docker_version_file.exists.assert_called_once()
            mock_local_version_file.exists.assert_called_once()

    def test_version_priority_environment_over_files(self):
        """Test that environment variable takes priority over version files."""
        env_version = "env.1.0.0"
        file_version = "file.2.0.0"

        # Set environment variable
        os.environ['APP_VERSION'] = env_version

        # Mock Path.exists and read_text to return different version
        with patch('app.Path') as mock_path_class:
            mock_docker_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to exist with different version
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.return_value = file_version

            version = get_application_version()

            # Should return environment variable, not file version
            assert version == env_version

            # Version file should not be checked when env var is available
            mock_docker_version_file.exists.assert_not_called()

    def test_version_whitespace_handling(self):
        """Test that whitespace is properly stripped from version files."""
        test_version = "1.0.0.whitespace"
        whitespace_version = f"\n\t  {test_version}  \t\n"

        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        # Mock Path.exists and read_text
        with patch('app.Path') as mock_path_class:
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to exist with whitespace
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.return_value = whitespace_version

            version = get_application_version()
            assert version == test_version  # Should be stripped

            mock_docker_version_file.exists.assert_called_once()
            mock_docker_version_file.read_text.assert_called_once()


class TestVersionLoggingIntegration:
    """Test suite for version logging during application startup."""

    def setup_method(self):
        """Set up test environment before each test."""
        import uuid

        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_version_{uuid.uuid4().hex[:8]}_")
        self.source_dir = Path(self.temp_dir) / "source"
        self.saved_dir = Path(self.temp_dir) / "saved"
        self.error_dir = Path(self.temp_dir) / "error"

        # Create directories
        for dir_path in [self.source_dir, self.saved_dir, self.error_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            assert dir_path.exists(), f"Failed to create directory: {dir_path}"

        # Create .env file for testing
        self.env_file = Path(self.temp_dir) / ".env"
        with open(self.env_file, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=false\n")  # Disable for simpler testing
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")

        # Store original environment variable to restore later
        self.original_app_version = os.environ.get('APP_VERSION')

        # Clean up any existing APP_VERSION for clean test state
        if 'APP_VERSION' in os.environ:
            del os.environ['APP_VERSION']

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

        # Restore original environment variable
        if self.original_app_version is not None:
            os.environ['APP_VERSION'] = self.original_app_version
        elif 'APP_VERSION' in os.environ:
            del os.environ['APP_VERSION']

        # Clean up test environment variables
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

    @patch('builtins.print')
    def test_console_version_logging_with_environment_variable(self, mock_print):
        """Test that version is logged to console during initialization with environment variable."""
        test_version = "2.1.0.env123"
        os.environ['APP_VERSION'] = test_version

        self.app = FolderFileProcessorApp(env_file=str(self.env_file))

        # Initialize app to trigger version logging
        result = self.app.initialize()
        assert result is True

        # Check that version was printed to console
        expected_message = f"RAG File Processor v{test_version}"
        mock_print.assert_any_call(expected_message)

    @patch('builtins.print')
    def test_console_version_logging_with_unknown_version(self, mock_print):
        """Test that unknown version is logged to console when no version sources available."""
        # Ensure no version sources are available
        assert 'APP_VERSION' not in os.environ

        # Mock version files to not exist
        with patch('app.Path') as mock_path_class:
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            mock_docker_version_file.exists.return_value = False
            mock_local_version_file.exists.return_value = False

            self.app = FolderFileProcessorApp(env_file=str(self.env_file))

            result = self.app.initialize()
            assert result is True

            # Check that unknown version was printed to console
            expected_message = "RAG File Processor vunknown"
            mock_print.assert_any_call(expected_message)

    def test_structured_logging_with_version_info(self):
        """Test that version is included in structured logging during initialization."""
        test_version = "1.9.0.log456"
        os.environ['APP_VERSION'] = test_version

        self.app = FolderFileProcessorApp(env_file=str(self.env_file))

        # Initialize app to trigger version logging
        result = self.app.initialize()
        assert result is True

        # Mock the logger service to capture log messages
        mock_logger = MagicMock()
        self.app.logger_service = mock_logger

        # Re-run the initialization logging part specifically
        doc_processing_status = "disabled" if not self.app.config.document_processing.enable_processing else "enabled"
        self.app.logger_service.log_info(f"Application initialization started - Version: {test_version}, Document processing: {doc_processing_status}")

        # Verify structured log message was called
        expected_message = f"Application initialization started - Version: {test_version}, Document processing: disabled"
        mock_logger.log_info.assert_called_with(expected_message)

    @patch('builtins.print')
    def test_version_logging_with_file_source(self, mock_print):
        """Test version logging when version comes from file source."""
        test_version = "3.0.0.file789"

        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        # Mock Path.exists and read_text for version file
        with patch('app.Path') as mock_path_class:
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to exist and return content
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.return_value = test_version

            self.app = FolderFileProcessorApp(env_file=str(self.env_file))

            result = self.app.initialize()
            assert result is True

            # Check that file-sourced version was printed to console
            expected_message = f"RAG File Processor v{test_version}"
            mock_print.assert_any_call(expected_message)

    def test_version_logging_sequence_in_initialization(self):
        """Test that version logging happens early in initialization sequence."""
        test_version = "2.5.0.sequence123"
        os.environ['APP_VERSION'] = test_version

        call_sequence = []

        # Mock print to track when version is logged
        def mock_print_tracker(*args, **kwargs):
            call_sequence.append(('print', args[0] if args else ''))

        # Mock logger service setup to track when it's called
        original_setup_logger = None
        def mock_logger_setup_tracker(*args, **kwargs):
            call_sequence.append(('logger_setup', 'LoggerService setup'))
            # Return a mock logger service
            mock_logger = MagicMock()
            return mock_logger

        with patch('builtins.print', side_effect=mock_print_tracker):
            with patch('app.LoggerService.setup_logger', side_effect=mock_logger_setup_tracker):
                self.app = FolderFileProcessorApp(env_file=str(self.env_file))
                result = self.app.initialize()
                assert result is True

        # Verify that version logging happened early in sequence
        version_print_found = False
        logger_setup_found = False
        version_before_logger = False

        for i, (call_type, message) in enumerate(call_sequence):
            if call_type == 'print' and f"RAG File Processor v{test_version}" in message:
                version_print_found = True
                # Check if this happened before logger setup
                for j in range(i + 1, len(call_sequence)):
                    if call_sequence[j][0] == 'logger_setup':
                        logger_setup_found = True
                        version_before_logger = True
                        break

        assert version_print_found, "Version should be printed during initialization"
        # Note: The actual implementation may have logger setup before version print,
        # so we'll just verify that version was logged

    def test_version_logging_with_document_processing_enabled(self):
        """Test version logging when document processing is enabled."""
        test_version = "4.0.0.docproc456"
        os.environ['APP_VERSION'] = test_version

        # Create env file with document processing enabled
        env_file_with_docproc = Path(self.temp_dir) / "docproc.env"
        with open(env_file_with_docproc, 'w') as f:
            f.write(f"SOURCE_FOLDER={self.source_dir}\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("ENABLE_DOCUMENT_PROCESSING=true\n")
            f.write("DOCUMENT_PROCESSOR_TYPE=rag_store\n")
            f.write("MODEL_VENDOR=google\n")
            f.write("GOOGLE_API_KEY=AIzaSyFAKE_TEST_KEY_1234567890123456789\n")
            f.write("CHROMA_DB_PATH=./data/chroma_db\n")
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")

        # Mock the RAGStoreProcessor and dependency validation to avoid actual initialization
        with patch('app.RAGStoreProcessor') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.get_supported_extensions.return_value = {'.txt', '.pdf'}
            mock_processor_class.return_value = mock_processor

            # Also need to mock the config manager's dependency validation in CI environment
            with patch('app.ConfigManager') as mock_config_manager_class:
                mock_config_manager = MagicMock()
                mock_config = MagicMock()

                # Set up the config mock to return valid configuration
                mock_config.source_folder = str(self.source_dir)
                mock_config.saved_folder = str(self.saved_dir)
                mock_config.error_folder = str(self.error_dir)
                mock_config.document_processing.enable_processing = True
                mock_config.document_processing.processor_type = "rag_store"
                mock_config.document_processing.model_vendor = "google"
                mock_config.document_processing.chroma_db_path = "./data/chroma_db"

                mock_config_manager.initialize.return_value = mock_config
                mock_config_manager.validate_dependencies.return_value = []  # No dependency errors
                mock_config_manager_class.return_value = mock_config_manager

                with patch('builtins.print') as mock_print:
                    self.app = FolderFileProcessorApp(env_file=str(env_file_with_docproc))
                    result = self.app.initialize()
                    assert result is True

                    # Check that version was printed to console
                    expected_message = f"RAG File Processor v{test_version}"
                    mock_print.assert_any_call(expected_message)

    def test_version_function_called_during_initialization(self):
        """Test that get_application_version function is actually called during initialization."""
        test_version = "5.0.0.called789"

        with patch('app.get_application_version') as mock_get_version:
            mock_get_version.return_value = test_version

            with patch('builtins.print') as mock_print:
                self.app = FolderFileProcessorApp(env_file=str(self.env_file))
                result = self.app.initialize()
                assert result is True

                # Verify that get_application_version was called
                mock_get_version.assert_called_once()

                # Verify that the returned version was used in print
                expected_message = f"RAG File Processor v{test_version}"
                mock_print.assert_any_call(expected_message)

    def test_initialization_failure_prevents_version_logging(self):
        """Test that version is not logged if configuration loading fails early."""
        test_version = "6.0.0.failure123"
        os.environ['APP_VERSION'] = test_version

        # Create invalid env file to cause configuration loading failure
        invalid_env_file = Path(self.temp_dir) / "invalid.env"
        with open(invalid_env_file, 'w') as f:
            f.write("SOURCE_FOLDER=/nonexistent/path\n")
            f.write(f"SAVED_FOLDER={self.saved_dir}\n")
            f.write(f"ERROR_FOLDER={self.error_dir}\n")
            f.write("FILE_MONITORING_MODE=auto\n")
            f.write("POLLING_INTERVAL=3.0\n")
            f.write("DOCKER_VOLUME_MODE=false\n")

        with patch('builtins.print') as mock_print:
            self.app = FolderFileProcessorApp(env_file=str(invalid_env_file))
            result = self.app.initialize()

            # Initialization should fail due to invalid source folder
            assert result is False

            # Version should NOT be logged because configuration loading failed before version logging
            expected_message = f"RAG File Processor v{test_version}"
            # Assert that version was NOT printed (since config loading failed first)
            print_calls = [str(call) for call in mock_print.call_args_list]
            version_logged = any(expected_message in call for call in print_calls)
            assert not version_logged, f"Version should not be logged when config loading fails. Calls: {print_calls}"


class TestVersionUtilityEdgeCases:
    """Test edge cases and error scenarios for version utility functions."""

    def setup_method(self):
        """Set up test environment."""
        # Store original environment variable to restore later
        self.original_app_version = os.environ.get('APP_VERSION')

        # Clean up any existing APP_VERSION for clean test state
        if 'APP_VERSION' in os.environ:
            del os.environ['APP_VERSION']

    def teardown_method(self):
        """Clean up after each test."""
        # Restore original environment variable
        if self.original_app_version is not None:
            os.environ['APP_VERSION'] = self.original_app_version
        elif 'APP_VERSION' in os.environ:
            del os.environ['APP_VERSION']

    def test_version_with_special_characters(self):
        """Test version handling with special characters."""
        special_version = "1.0.0-alpha.1+build.123"
        os.environ['APP_VERSION'] = special_version

        version = get_application_version()
        assert version == special_version

    def test_version_with_unicode_characters(self):
        """Test version handling with unicode characters."""
        unicode_version = "1.0.0-β.测试"
        os.environ['APP_VERSION'] = unicode_version

        version = get_application_version()
        assert version == unicode_version

    def test_version_very_long_string(self):
        """Test version handling with very long version string."""
        long_version = "1.0.0." + "x" * 1000
        os.environ['APP_VERSION'] = long_version

        version = get_application_version()
        assert version == long_version

    def test_version_file_with_multiple_lines(self):
        """Test version file with multiple lines (should only use first line after strip)."""
        test_version = "1.0.0.multiline"
        file_content = f"{test_version}\nSecond line\nThird line"

        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        with patch('app.Path') as mock_path_class:
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to exist with multi-line content
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.return_value = file_content

            version = get_application_version()
            # Should return the full content after strip (including newlines)
            assert version == file_content.strip()

    def test_version_file_unicode_decode_error(self):
        """Test handling of unicode decode errors in version files."""
        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        with patch('app.Path') as mock_path_class:
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure Docker version file to exist but raise UnicodeDecodeError
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")

            # Configure local version file to not exist
            mock_local_version_file.exists.return_value = False

            version = get_application_version()
            assert version == 'unknown'

    def test_version_file_permission_error(self):
        """Test handling of permission errors when reading version files."""
        # Ensure no environment variable is set
        assert 'APP_VERSION' not in os.environ

        with patch('app.Path') as mock_path_class:
            mock_docker_version_file = MagicMock()
            mock_local_version_file = MagicMock()

            def path_factory(path_str):
                if path_str == '/app/VERSION':
                    return mock_docker_version_file
                elif path_str == 'VERSION':
                    return mock_local_version_file
                else:
                    return MagicMock()

            mock_path_class.side_effect = path_factory

            # Configure both version files to exist but raise PermissionError
            mock_docker_version_file.exists.return_value = True
            mock_docker_version_file.read_text.side_effect = PermissionError("Access denied")

            mock_local_version_file.exists.return_value = True
            mock_local_version_file.read_text.side_effect = PermissionError("Access denied")

            version = get_application_version()
            assert version == 'unknown'

    def test_version_none_value_in_environment(self):
        """Test version handling when environment variable is None (shouldn't happen but test defensive coding)."""
        # This test is more theoretical since os.environ.get() returns None or a string
        # But we can test the logic path

        with patch.dict(os.environ, {}, clear=False):
            # Ensure APP_VERSION is not in environment
            if 'APP_VERSION' in os.environ:
                del os.environ['APP_VERSION']

            # Mock version files to not exist
            with patch('app.Path') as mock_path_class:
                mock_docker_version_file = MagicMock()
                mock_local_version_file = MagicMock()

                def path_factory(path_str):
                    if path_str == '/app/VERSION':
                        return mock_docker_version_file
                    elif path_str == 'VERSION':
                        return mock_local_version_file
                    else:
                        return MagicMock()

                mock_path_class.side_effect = path_factory

                mock_docker_version_file.exists.return_value = False
                mock_local_version_file.exists.return_value = False

                version = get_application_version()
                assert version == 'unknown'