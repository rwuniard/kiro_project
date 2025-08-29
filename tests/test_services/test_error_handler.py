"""
Unit tests for ErrorHandler service.

Tests error log file creation, formatting, and error handling scenarios.
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open

from src.services.error_handler import ErrorHandler


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    @pytest.fixture
    def temp_error_folder(self):
        """Create a temporary directory for error logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def temp_source_folder(self):
        """Create a temporary directory for source files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def error_handler(self, temp_error_folder):
        """Create ErrorHandler instance with temporary folder."""
        return ErrorHandler(temp_error_folder)
    
    @pytest.fixture
    def error_handler_with_source(self, temp_error_folder, temp_source_folder):
        """Create ErrorHandler instance with source folder for structure preservation."""
        return ErrorHandler(temp_error_folder, temp_source_folder)
    
    @pytest.fixture
    def sample_file(self, temp_error_folder):
        """Create a sample file for testing."""
        sample_file_path = Path(temp_error_folder) / "sample.txt"
        sample_file_path.write_text("Sample content")
        return str(sample_file_path)
    
    def test_error_handler_initialization(self, temp_error_folder):
        """Test ErrorHandler initialization with error folder."""
        handler = ErrorHandler(temp_error_folder)
        assert handler.error_folder == Path(temp_error_folder)
    
    def test_create_error_log_basic(self, error_handler, sample_file):
        """Test basic error log creation."""
        error_message = "Test error message"
        
        error_handler.create_error_log(sample_file, error_message)
        
        # Check that error log file was created
        expected_log_path = error_handler.error_folder / "sample.txt.log"
        assert expected_log_path.exists()
        
        # Verify log content
        log_content = expected_log_path.read_text()
        assert "FILE PROCESSING ERROR LOG" in log_content
        assert error_message in log_content
        assert sample_file in log_content
        assert "Timestamp:" in log_content
    
    def test_create_error_log_with_exception(self, error_handler, sample_file):
        """Test error log creation with exception details."""
        error_message = "File processing failed"
        test_exception = ValueError("Invalid file format")
        
        error_handler.create_error_log(sample_file, error_message, test_exception)
        
        expected_log_path = error_handler.error_folder / "sample.txt.log"
        log_content = expected_log_path.read_text()
        
        assert error_message in log_content
        assert "ValueError" in log_content
        assert "Stack Trace:" in log_content
        assert "Invalid file format" in log_content
    
    def test_get_error_log_path_simple_file(self, error_handler):
        """Test error log path generation for simple filename."""
        file_path = "/source/document.txt"
        
        log_path = error_handler._get_error_log_path(file_path)
        
        assert log_path.name == "document.txt.log"
        assert log_path.parent == error_handler.error_folder
    
    def test_get_error_log_path_nested_structure(self, error_handler):
        """Test error log path generation for nested files."""
        file_path = "/source/subfolder/nested/file.pdf"
        
        log_path = error_handler._get_error_log_path(file_path)
        
        assert log_path.name == "file.pdf.log"
        # Log files are placed directly in error folder
        assert log_path.parent == error_handler.error_folder
    
    def test_get_error_log_path_creates_directory(self, error_handler):
        """Test that error log path creation creates necessary directories."""
        file_path = "/source/newdir/file.txt"
        
        log_path = error_handler._get_error_log_path(file_path)
        
        # Error folder should be created and log placed there
        assert log_path.parent.exists()
        assert log_path.parent == error_handler.error_folder
        assert log_path.name == "file.txt.log"
    
    def test_build_error_info_basic(self, error_handler, sample_file):
        """Test building basic error information."""
        error_message = "Processing failed"
        
        error_info = error_handler._build_error_info(sample_file, error_message)
        
        assert error_info['file_path'] == sample_file
        assert error_info['error_message'] == error_message
        assert 'timestamp' in error_info
        assert 'file_size' in error_info
        assert 'last_modified' in error_info
        
        # Verify timestamp format
        datetime.fromisoformat(error_info['timestamp'])
    
    def test_build_error_info_with_exception(self, error_handler, sample_file):
        """Test building error info with exception details."""
        error_message = "Processing failed"
        test_exception = RuntimeError("Runtime error occurred")
        
        error_info = error_handler._build_error_info(
            sample_file, error_message, test_exception
        )
        
        assert error_info['exception_type'] == 'RuntimeError'
        assert 'stack_trace' in error_info
        assert isinstance(error_info['stack_trace'], list)
    
    def test_build_error_info_nonexistent_file(self, error_handler):
        """Test building error info for non-existent file."""
        nonexistent_file = "/path/to/nonexistent/file.txt"
        error_message = "File not found"
        
        error_info = error_handler._build_error_info(nonexistent_file, error_message)
        
        assert error_info['file_path'] == nonexistent_file
        assert error_info['file_size'] == 'Unknown'
        assert error_info['last_modified'] == 'Unknown'
    
    def test_write_error_log_format(self, error_handler, temp_error_folder):
        """Test error log file format and content structure."""
        log_path = Path(temp_error_folder) / "test.log"
        error_info = {
            'timestamp': '2025-01-23T10:30:45.123456',
            'file_path': '/source/test.txt',
            'error_message': 'Test error',
            'file_size': 1024,
            'last_modified': '2025-01-23T10:29:12.000000',
            'exception_type': 'ValueError',
            'stack_trace': ['Traceback (most recent call last):\n', '  ValueError: Test\n']
        }
        
        error_handler._write_error_log(log_path, error_info)
        
        content = log_path.read_text()
        
        # Check required sections
        assert "FILE PROCESSING ERROR LOG" in content
        assert "Timestamp: 2025-01-23T10:30:45.123456" in content
        assert "File: /source/test.txt" in content
        assert "Error: Test error" in content
        assert "Size: 1024 bytes" in content
        assert "Last Modified: 2025-01-23T10:29:12.000000" in content
        assert "Exception Type: ValueError" in content
        assert "Stack Trace:" in content
        assert "ValueError: Test" in content
    
    def test_write_error_log_minimal_info(self, error_handler, temp_error_folder):
        """Test error log with minimal information (no exception)."""
        log_path = Path(temp_error_folder) / "minimal.log"
        error_info = {
            'timestamp': '2025-01-23T10:30:45.123456',
            'file_path': '/source/minimal.txt',
            'error_message': 'Simple error',
            'file_size': 512,
            'last_modified': '2025-01-23T10:29:12.000000'
        }
        
        error_handler._write_error_log(log_path, error_info)
        
        content = log_path.read_text()
        
        # Should have basic info but no exception details
        assert "Simple error" in content
        assert "Exception Type:" not in content
        assert "Stack Trace:" not in content
    
    def test_create_error_log_handles_write_failure(self, error_handler, sample_file):
        """Test error log creation handles write failures gracefully."""
        # Mock open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('builtins.print') as mock_print:
                error_handler.create_error_log(sample_file, "Test error")
                
                # Should print error message instead of crashing
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                assert "Failed to create error log" in call_args
                assert sample_file in call_args
    
    def test_error_log_file_extension(self, error_handler):
        """Test that error log files always have .log extension."""
        test_cases = [
            "/source/document.txt",
            "/source/image.jpg", 
            "/source/data.csv",
            "/source/file_without_extension"
        ]
        
        for file_path in test_cases:
            log_path = error_handler._get_error_log_path(file_path)
            assert log_path.suffix == ".log"
    
    def test_error_log_timestamp_format(self, error_handler, sample_file):
        """Test that error log timestamps are properly formatted."""
        with patch('src.services.error_handler.datetime') as mock_datetime:
            mock_now = datetime(2025, 1, 23, 10, 30, 45, 123456)
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromtimestamp.return_value = mock_now
            
            error_info = error_handler._build_error_info(sample_file, "Test error")
            
            assert error_info['timestamp'] == '2025-01-23T10:30:45.123456'
    
    def test_multiple_error_logs_same_directory(self, error_handler, temp_error_folder):
        """Test creating multiple error logs in the same directory."""
        # Create multiple sample files
        file1 = Path(temp_error_folder) / "file1.txt"
        file2 = Path(temp_error_folder) / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Create error logs for both
        error_handler.create_error_log(str(file1), "Error 1")
        error_handler.create_error_log(str(file2), "Error 2")
        
        # Both log files should exist
        log1 = error_handler.error_folder / "file1.txt.log"
        log2 = error_handler.error_folder / "file2.txt.log"
        
        assert log1.exists()
        assert log2.exists()
        
        # Verify content is different
        content1 = log1.read_text()
        content2 = log2.read_text()
        
        assert "Error 1" in content1
        assert "Error 2" in content2
        assert content1 != content2
    
    def test_enhanced_error_log_filename_format(self, error_handler):
        """Test enhanced error log filename format: [filename].[extension].log"""
        test_cases = [
            # (input_file, expected_log_name)
            ("/source/abc.pdf", "abc.pdf.log"),
            ("/source/document.txt", "document.txt.log"),
            ("/source/data.csv", "data.csv.log"),
            ("/source/image.jpg", "image.jpg.log"),
            ("/source/debug.log", "debug.log.log"),
            ("/source/backup.tar.gz", "backup.tar.gz.log"),
            ("/source/file_without_extension", "file_without_extension.log"),
            ("/source/config.json", "config.json.log"),
            ("/source/script.py", "script.py.log"),
            ("/source/archive.zip", "archive.zip.log")
        ]
        
        for file_path, expected_log_name in test_cases:
            log_path = error_handler._get_error_log_path(file_path)
            assert log_path.name == expected_log_name, f"Failed for {file_path}: expected {expected_log_name}, got {log_path.name}"
    
    def test_enhanced_error_log_multiple_extensions(self, error_handler):
        """Test error log naming for files with multiple extensions."""
        test_cases = [
            ("/source/backup.tar.gz", "backup.tar.gz.log"),
            ("/source/data.sql.bak", "data.sql.bak.log"),
            ("/source/config.yaml.template", "config.yaml.template.log"),
            ("/source/archive.tar.bz2", "archive.tar.bz2.log"),
            ("/source/file.min.js", "file.min.js.log")
        ]
        
        for file_path, expected_log_name in test_cases:
            log_path = error_handler._get_error_log_path(file_path)
            assert log_path.name == expected_log_name, f"Failed for {file_path}: expected {expected_log_name}, got {log_path.name}"
    
    def test_enhanced_error_log_edge_cases(self, error_handler):
        """Test error log naming for edge case filenames."""
        test_cases = [
            # Files without extensions
            ("/source/README", "README.log"),
            ("/source/Makefile", "Makefile.log"),
            ("/source/dockerfile", "dockerfile.log"),
            # Files with dots in name but no extension
            ("/source/file.name.without.ext", "file.name.without.ext.log"),
            # Files starting with dots
            ("/source/.hidden", ".hidden.log"),
            ("/source/.gitignore", ".gitignore.log"),
            # Files with special characters
            ("/source/file-name_with.special.chars.txt", "file-name_with.special.chars.txt.log"),
            # Very long filenames
            ("/source/very_long_filename_that_might_cause_issues.txt", "very_long_filename_that_might_cause_issues.txt.log")
        ]
        
        for file_path, expected_log_name in test_cases:
            log_path = error_handler._get_error_log_path(file_path)
            assert log_path.name == expected_log_name, f"Failed for {file_path}: expected {expected_log_name}, got {log_path.name}"
    
    def test_enhanced_error_log_creation_with_new_format(self, error_handler, temp_error_folder):
        """Test actual error log file creation with enhanced filename format."""
        # Create test files with various extensions
        test_files = [
            ("document.pdf", "PDF processing error"),
            ("data.csv", "CSV parsing error"),
            ("debug.log", "Log file corruption"),
            ("backup.tar.gz", "Archive extraction failed"),
            ("no_extension", "Unknown file type")
        ]
        
        for filename, error_msg in test_files:
            # Create the test file
            test_file_path = Path(temp_error_folder) / filename
            test_file_path.write_text("test content")
            
            # Create error log
            error_handler.create_error_log(str(test_file_path), error_msg)
            
            # Verify log file was created with correct name
            expected_log_path = error_handler.error_folder / f"{filename}.log"
            assert expected_log_path.exists(), f"Log file not created for {filename}"
            
            # Verify log content
            log_content = expected_log_path.read_text()
            assert error_msg in log_content
            assert str(test_file_path) in log_content
    
    def test_error_log_folder_structure_preservation(self, error_handler_with_source, temp_source_folder, temp_error_folder):
        """Test that error logs preserve folder structure when source folder is provided."""
        # Create nested folder structure in source
        nested_folder = Path(temp_source_folder) / "subfolder" / "nested"
        nested_folder.mkdir(parents=True)
        
        # Create test file in nested structure
        test_file = nested_folder / "document.pdf"
        test_file.write_text("test content")
        
        # Create error log
        error_handler_with_source.create_error_log(str(test_file), "Processing failed")
        
        # Verify log file was created in preserved structure
        expected_log_path = Path(temp_error_folder) / "subfolder" / "nested" / "document.pdf.log"
        assert expected_log_path.exists(), f"Log file not created at expected path: {expected_log_path}"
        
        # Verify log content
        log_content = expected_log_path.read_text()
        assert "Processing failed" in log_content
        assert str(test_file) in log_content
    
    def test_error_log_without_source_folder(self, temp_error_folder):
        """Test error log creation when no source folder is provided (backward compatibility)."""
        # Create ErrorHandler without source folder
        error_handler = ErrorHandler(temp_error_folder)
        
        # Create test file
        test_file_path = "/some/path/document.txt"
        
        # Create error log
        error_handler.create_error_log(test_file_path, "Test error")
        
        # Verify log file was created in error folder root
        expected_log_path = Path(temp_error_folder) / "document.txt.log"
        assert expected_log_path.exists()
        
        # Verify log content
        log_content = expected_log_path.read_text()
        assert "Test error" in log_content
        assert test_file_path in log_content
    
    def test_error_log_file_outside_source_folder(self, error_handler_with_source, temp_source_folder, temp_error_folder):
        """Test error log creation for files outside the source folder."""
        # Create test file outside source folder
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write("test content")
            temp_file_path = temp_file.name
        
        try:
            # Create error log
            error_handler_with_source.create_error_log(temp_file_path, "File outside source")
            
            # Verify log file was created in error folder root (fallback behavior)
            expected_log_path = Path(temp_error_folder) / f"{Path(temp_file_path).name}.log"
            assert expected_log_path.exists()
            
            # Verify log content
            log_content = expected_log_path.read_text()
            assert "File outside source" in log_content
            assert temp_file_path in log_content
            
        finally:
            # Clean up temp file
            Path(temp_file_path).unlink(missing_ok=True)
    
    def test_error_log_deep_nested_structure(self, error_handler_with_source, temp_source_folder, temp_error_folder):
        """Test error log creation with deeply nested folder structure."""
        # Create deeply nested structure
        deep_path = Path(temp_source_folder) / "level1" / "level2" / "level3" / "level4"
        deep_path.mkdir(parents=True)
        
        # Create test file in deep structure
        test_file = deep_path / "deep_file.json"
        test_file.write_text('{"test": "data"}')
        
        # Create error log
        error_handler_with_source.create_error_log(str(test_file), "Deep nesting error")
        
        # Verify log file was created in preserved deep structure
        expected_log_path = Path(temp_error_folder) / "level1" / "level2" / "level3" / "level4" / "deep_file.json.log"
        assert expected_log_path.exists()
        
        # Verify all intermediate directories were created
        assert expected_log_path.parent.exists()
        assert expected_log_path.parent.is_dir()
        
        # Verify log content
        log_content = expected_log_path.read_text()
        assert "Deep nesting error" in log_content
        assert str(test_file) in log_content


class TestEnhancedErrorLogNaming:
    """Test cases for enhanced error log naming functionality (Task 15.1)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.error_folder = Path(self.temp_dir) / "error"
        self.source_folder = Path(self.temp_dir) / "source"
        
        self.error_folder.mkdir(parents=True)
        self.source_folder.mkdir(parents=True)
        
        # Initialize ErrorHandler with source folder for structure preservation
        self.error_handler = ErrorHandler(
            str(self.error_folder),
            str(self.source_folder)
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_error_log_naming_various_file_formats(self):
        """Test error log creation with various filename formats."""
        test_cases = [
            # (input_file, expected_log_name, file_content)
            ("document.pdf", "document.pdf.log", "PDF content"),
            ("spreadsheet.xlsx", "spreadsheet.xlsx.log", "Excel data"),
            ("image.jpg", "image.jpg.log", "JPEG data"),
            ("video.mp4", "video.mp4.log", "Video data"),
            ("archive.zip", "archive.zip.log", "Archive data"),
            ("script.py", "script.py.log", "Python code"),
            ("config.json", "config.json.log", '{"config": "data"}'),
            ("style.css", "style.css.log", "CSS styles"),
            ("page.html", "page.html.log", "<html></html>"),
            ("data.xml", "data.xml.log", "<xml></xml>")
        ]
        
        for filename, expected_log_name, content in test_cases:
            # Create test file
            test_file = self.source_folder / filename
            test_file.write_text(content)
            
            # Create error log
            self.error_handler.create_error_log(str(test_file), f"Processing failed for {filename}")
            
            # Verify log file was created with correct name
            expected_log_path = self.error_folder / expected_log_name
            assert expected_log_path.exists(), f"Log file not created for {filename}"
            
            # Verify log content
            log_content = expected_log_path.read_text()
            assert f"Processing failed for {filename}" in log_content
            assert str(test_file) in log_content
            assert "FILE PROCESSING ERROR LOG" in log_content
    
    def test_error_log_naming_complex_extensions(self):
        """Test error log naming for files with complex extensions."""
        test_cases = [
            # (input_file, expected_log_name)
            ("backup.tar.gz", "backup.tar.gz.log"),
            ("database.sql.bak", "database.sql.bak.log"),
            ("template.html.twig", "template.html.twig.log"),
            ("config.yaml.template", "config.yaml.template.log"),
            ("archive.tar.bz2", "archive.tar.bz2.log"),
            ("minified.min.js", "minified.min.js.log"),
            ("compressed.tar.xz", "compressed.tar.xz.log"),
            ("data.csv.gz", "data.csv.gz.log"),
            ("log.2024.01.txt", "log.2024.01.txt.log"),
            ("version.1.2.3.json", "version.1.2.3.json.log")
        ]
        
        for filename, expected_log_name in test_cases:
            # Create test file
            test_file = self.source_folder / filename
            test_file.write_text("test content")
            
            # Create error log
            self.error_handler.create_error_log(str(test_file), "Complex extension test")
            
            # Verify log file was created with correct name
            expected_log_path = self.error_folder / expected_log_name
            assert expected_log_path.exists(), f"Log file not created for {filename}"
            
            # Verify log content
            log_content = expected_log_path.read_text()
            assert "Complex extension test" in log_content
    
    def test_error_log_naming_edge_cases(self):
        """Test error log naming for edge case filenames."""
        test_cases = [
            # Files without extensions
            ("README", "README.log"),
            ("Makefile", "Makefile.log"),
            ("dockerfile", "dockerfile.log"),
            ("LICENSE", "LICENSE.log"),
            ("CHANGELOG", "CHANGELOG.log"),
            # Files with dots but no extension
            ("file.name.without.ext", "file.name.without.ext.log"),
            ("my.special.file", "my.special.file.log"),
            # Hidden files
            (".gitignore", ".gitignore.log"),
            (".env", ".env.log"),
            (".hidden", ".hidden.log"),
            (".bashrc", ".bashrc.log"),
            # Files with special characters
            ("file-with-dashes.txt", "file-with-dashes.txt.log"),
            ("file_with_underscores.txt", "file_with_underscores.txt.log"),
            ("file with spaces.txt", "file with spaces.txt.log"),
            ("file(with)parentheses.txt", "file(with)parentheses.txt.log"),
            ("file[with]brackets.txt", "file[with]brackets.txt.log")
        ]
        
        for filename, expected_log_name in test_cases:
            # Create test file
            test_file = self.source_folder / filename
            test_file.write_text("edge case content")
            
            # Create error log
            self.error_handler.create_error_log(str(test_file), f"Edge case test for {filename}")
            
            # Verify log file was created with correct name
            expected_log_path = self.error_folder / expected_log_name
            assert expected_log_path.exists(), f"Log file not created for {filename}"
            
            # Verify log content
            log_content = expected_log_path.read_text()
            assert f"Edge case test for {filename}" in log_content
    
    def test_error_log_placement_in_error_folder_structure(self):
        """Test that error logs are placed in correct locations within error folder structure."""
        # Create nested folder structure in source
        nested_levels = [
            "level1",
            "level1/level2", 
            "level1/level2/level3",
            "branch1/subbranch1",
            "branch2/deep/deeper"
        ]
        
        for level_path in nested_levels:
            # Create nested folder
            nested_folder = self.source_folder / level_path
            nested_folder.mkdir(parents=True, exist_ok=True)
            
            # Create test file in nested structure
            test_file = nested_folder / "nested_test.pdf"
            test_file.write_text("nested content")
            
            # Create error log
            self.error_handler.create_error_log(str(test_file), "Nested structure test")
            
            # Verify log file was created in preserved structure
            expected_log_path = self.error_folder / level_path / "nested_test.pdf.log"
            assert expected_log_path.exists(), f"Log file not created at expected path: {expected_log_path}"
            
            # Verify all intermediate directories were created
            assert expected_log_path.parent.exists()
            assert expected_log_path.parent.is_dir()
            
            # Verify log content
            log_content = expected_log_path.read_text()
            assert "Nested structure test" in log_content
            assert str(test_file) in log_content
    
    def test_error_log_naming_very_long_filenames(self):
        """Test error log naming for very long filenames."""
        # Create a very long filename (but within filesystem limits)
        long_base_name = "a" * 200  # 200 characters
        long_filename = f"{long_base_name}.txt"
        expected_log_name = f"{long_filename}.log"
        
        # Create test file
        test_file = self.source_folder / long_filename
        test_file.write_text("long filename content")
        
        # Create error log
        self.error_handler.create_error_log(str(test_file), "Long filename test")
        
        # Verify log file was created with correct name
        expected_log_path = self.error_folder / expected_log_name
        assert expected_log_path.exists(), "Log file not created for long filename"
        
        # Verify log content
        log_content = expected_log_path.read_text()
        assert "Long filename test" in log_content
    
    def test_error_log_naming_unicode_filenames(self):
        """Test error log naming for filenames with unicode characters."""
        test_cases = [
            ("файл.txt", "файл.txt.log"),  # Cyrillic
            ("文件.pdf", "文件.pdf.log"),    # Chinese
            ("ファイル.jpg", "ファイル.jpg.log"),  # Japanese
            ("αρχείο.doc", "αρχείο.doc.log"),  # Greek
            ("café.txt", "café.txt.log"),    # Accented characters
            ("naïve.csv", "naïve.csv.log"),  # More accented characters
        ]
        
        for filename, expected_log_name in test_cases:
            # Create test file
            test_file = self.source_folder / filename
            test_file.write_text("unicode content", encoding='utf-8')
            
            # Create error log
            self.error_handler.create_error_log(str(test_file), f"Unicode test for {filename}")
            
            # Verify log file was created with correct name
            expected_log_path = self.error_folder / expected_log_name
            assert expected_log_path.exists(), f"Log file not created for unicode filename {filename}"
            
            # Verify log content
            log_content = expected_log_path.read_text(encoding='utf-8')
            assert f"Unicode test for {filename}" in log_content
    
    def test_error_log_multiple_files_same_directory(self):
        """Test creating multiple error logs in the same directory with different formats."""
        # Create multiple files with different extensions in same directory
        test_files = [
            ("document.pdf", "PDF error"),
            ("spreadsheet.xlsx", "Excel error"), 
            ("image.png", "Image error"),
            ("video.mp4", "Video error"),
            ("archive.tar.gz", "Archive error"),
            ("no_extension", "No extension error")
        ]
        
        for filename, error_msg in test_files:
            # Create test file
            test_file = self.source_folder / filename
            test_file.write_text("test content")
            
            # Create error log
            self.error_handler.create_error_log(str(test_file), error_msg)
        
        # Verify all log files were created with correct names
        for filename, error_msg in test_files:
            expected_log_name = f"{filename}.log"
            expected_log_path = self.error_folder / expected_log_name
            assert expected_log_path.exists(), f"Log file not created for {filename}"
            
            # Verify content is unique for each file
            log_content = expected_log_path.read_text()
            assert error_msg in log_content
            assert filename in log_content or str(self.source_folder / filename) in log_content
    
    def test_error_log_naming_case_sensitivity(self):
        """Test error log naming preserves case sensitivity."""
        test_cases = [
            ("Document.PDF", "Document.PDF.log"),
            ("IMAGE.JPG", "IMAGE.JPG.log"),
            ("MixedCase.TxT", "MixedCase.TxT.log"),
            ("lowercase.pdf", "lowercase.pdf.log"),
            ("UPPERCASE.TXT", "UPPERCASE.TXT.log")
        ]
        
        for filename, expected_log_name in test_cases:
            # Create test file
            test_file = self.source_folder / filename
            test_file.write_text("case sensitivity test")
            
            # Create error log
            self.error_handler.create_error_log(str(test_file), "Case sensitivity test")
            
            # Verify log file was created with exact case preserved
            expected_log_path = self.error_folder / expected_log_name
            assert expected_log_path.exists(), f"Log file not created with correct case for {filename}"
            
            # Verify the actual filename matches exactly
            assert expected_log_path.name == expected_log_name


class TestErrorHandlerEmptyFolderLog:
    """Test cases for ErrorHandler empty folder log creation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.error_folder = Path(self.temp_dir) / "error"
        self.source_folder = Path(self.temp_dir) / "source"
        
        self.error_folder.mkdir(parents=True)
        self.source_folder.mkdir(parents=True)
        
        # Initialize ErrorHandler with source folder for structure preservation
        self.error_handler = ErrorHandler(
            str(self.error_folder),
            str(self.source_folder)
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_empty_folder_log_success(self):
        """Test successful creation of empty folder log."""
        # Create empty folder path (simulating original location)
        empty_folder_path = self.source_folder / "subfolder" / "empty"
        
        # Create the corresponding moved folder in error directory
        moved_folder = self.error_folder / "subfolder" / "empty"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        self.error_handler.create_empty_folder_log(str(empty_folder_path))
        
        # Verify log file was created
        log_file = moved_folder / "empty_folder.log"
        assert log_file.exists()
        
        # Verify log file content
        log_content = log_file.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert str(empty_folder_path) in log_content
        assert "Completely empty folder detected" in log_content
        assert str(moved_folder) in log_content
        assert "Timestamp:" in log_content
    
    def test_create_empty_folder_log_root_level(self):
        """Test empty folder log creation for root level folder."""
        # Create empty folder path at root level
        empty_folder_path = self.source_folder / "empty_root"
        
        # Create the corresponding moved folder in error directory
        moved_folder = self.error_folder / "empty_root"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        self.error_handler.create_empty_folder_log(str(empty_folder_path))
        
        # Verify log file was created
        log_file = moved_folder / "empty_folder.log"
        assert log_file.exists()
        
        # Verify log file content
        log_content = log_file.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert str(empty_folder_path) in log_content
        assert str(moved_folder) in log_content
    
    def test_create_empty_folder_log_no_source_folder(self):
        """Test empty folder log creation without source folder configured."""
        # Create ErrorHandler without source folder
        error_handler_no_source = ErrorHandler(str(self.error_folder))
        
        # Create empty folder path
        empty_folder_path = Path("/some/external/empty")
        
        # Create the corresponding moved folder in error directory (just folder name)
        moved_folder = self.error_folder / "empty"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        error_handler_no_source.create_empty_folder_log(str(empty_folder_path))
        
        # Verify log file was created
        log_file = moved_folder / "empty_folder.log"
        assert log_file.exists()
        
        # Verify log file content
        log_content = log_file.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert str(empty_folder_path) in log_content
    
    def test_create_empty_folder_log_folder_outside_source(self):
        """Test empty folder log creation for folder outside source."""
        # Create empty folder path outside source folder
        external_folder = Path(self.temp_dir) / "external" / "empty"
        
        # Create the corresponding moved folder in error directory (just folder name)
        moved_folder = self.error_folder / "empty"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        self.error_handler.create_empty_folder_log(str(external_folder))
        
        # Verify log file was created
        log_file = moved_folder / "empty_folder.log"
        assert log_file.exists()
        
        # Verify log file content
        log_content = log_file.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert str(external_folder) in log_content
    
    def test_create_empty_folder_log_write_error(self):
        """Test empty folder log creation with write error."""
        # Create empty folder path
        empty_folder_path = self.source_folder / "empty"
        
        # Don't create the moved folder, so write will fail
        # This should be handled gracefully
        
        # Mock print to capture error output
        with patch('builtins.print') as mock_print:
            self.error_handler.create_empty_folder_log(str(empty_folder_path))
            
            # Should have printed error message
            mock_print.assert_called_once()
            error_message = mock_print.call_args[0][0]
            assert "Failed to create empty folder log" in error_message
            assert str(empty_folder_path) in error_message
    
    def test_write_empty_folder_log_content_format(self):
        """Test the format and content of empty folder log file."""
        # Create test log info
        log_info = {
            'timestamp': '2025-01-23T10:30:45.123456',
            'original_path': '/source/test/empty',
            'moved_to': '/error/test/empty',
            'reason': 'Completely empty folder detected (no files, no subfolders) and moved to error folder'
        }
        
        # Create log file path
        log_file_path = self.error_folder / "test_log.log"
        
        # Write log
        self.error_handler._write_empty_folder_log(log_file_path, log_info)
        
        # Verify file was created and has correct content
        assert log_file_path.exists()
        content = log_file_path.read_text()
        
        # Check all required elements are present
        assert "EMPTY FOLDER LOG" in content
        assert "Timestamp: 2025-01-23T10:30:45.123456" in content
        assert "Folder: /source/test/empty" in content
        assert "Original Path: /source/test/empty" in content
        assert "Moved To: /error/test/empty" in content
        assert "Completely empty folder detected" in content
        
        # Check formatting
        assert content.startswith("=" * 50)
        assert content.endswith("=" * 50 + "\n")
    
    def test_create_empty_folder_log_deep_nested_structure(self):
        """Test empty folder log creation with deeply nested folder structure."""
        # Create deeply nested empty folder path
        empty_folder_path = self.source_folder / "level1" / "level2" / "level3" / "empty"
        
        # Create the corresponding moved folder in error directory
        moved_folder = self.error_folder / "level1" / "level2" / "level3" / "empty"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        self.error_handler.create_empty_folder_log(str(empty_folder_path))
        
        # Verify log file was created in correct location
        log_file = moved_folder / "empty_folder.log"
        assert log_file.exists()
        
        # Verify log file content includes full paths
        log_content = log_file.read_text()
        assert str(empty_folder_path) in log_content
        assert str(moved_folder) in log_content


class TestEmptyFolderLogHandling:
    """Test cases for empty folder log handling functionality (Task 15.2)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.error_folder = Path(self.temp_dir) / "error"
        self.source_folder = Path(self.temp_dir) / "source"
        
        self.error_folder.mkdir(parents=True)
        self.source_folder.mkdir(parents=True)
        
        # Initialize ErrorHandler with source folder for structure preservation
        self.error_handler = ErrorHandler(
            str(self.error_folder),
            str(self.source_folder)
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_empty_folder_log_basic(self):
        """Test basic empty folder log creation."""
        # Create empty folder path (simulating original location)
        original_folder_path = str(self.source_folder / "empty_test")
        
        # Simulate that the folder has been moved to error folder
        moved_folder = self.error_folder / "empty_test"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        self.error_handler.create_empty_folder_log(original_folder_path)
        
        # Verify log file was created
        log_file_path = moved_folder / "empty_folder.log"
        assert log_file_path.exists(), "Empty folder log file was not created"
        
        # Verify log content
        log_content = log_file_path.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert original_folder_path in log_content
        assert "Completely empty folder detected" in log_content
        assert "Timestamp:" in log_content
        assert str(moved_folder) in log_content
    
    def test_create_empty_folder_log_with_structure_preservation(self):
        """Test empty folder log creation with folder structure preservation."""
        # Create nested empty folder path (simulating original location)
        original_folder_path = str(self.source_folder / "level1" / "level2" / "empty_nested")
        
        # Simulate that the folder has been moved to error folder with structure preservation
        moved_folder = self.error_folder / "level1" / "level2" / "empty_nested"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        self.error_handler.create_empty_folder_log(original_folder_path)
        
        # Verify log file was created in correct location
        log_file_path = moved_folder / "empty_folder.log"
        assert log_file_path.exists(), "Empty folder log file was not created in nested structure"
        
        # Verify log content
        log_content = log_file_path.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert original_folder_path in log_content
        assert "level1/level2/empty_nested" in log_content
        assert "Completely empty folder detected" in log_content
    
    def test_create_empty_folder_log_without_source_folder(self):
        """Test empty folder log creation when no source folder is configured."""
        # Create ErrorHandler without source folder
        error_handler_no_source = ErrorHandler(str(self.error_folder))
        
        # Create empty folder path
        original_folder_path = "/some/path/empty_folder"
        
        # Simulate that the folder has been moved to error folder root
        moved_folder = self.error_folder / "empty_folder"
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        error_handler_no_source.create_empty_folder_log(original_folder_path)
        
        # Verify log file was created
        log_file_path = moved_folder / "empty_folder.log"
        assert log_file_path.exists(), "Empty folder log file was not created"
        
        # Verify log content
        log_content = log_file_path.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert original_folder_path in log_content
    
    def test_create_empty_folder_log_folder_outside_source(self):
        """Test empty folder log creation for folder outside source folder."""
        # Create folder path outside source folder
        with tempfile.TemporaryDirectory() as external_temp:
            original_folder_path = str(Path(external_temp) / "external_empty")
            
            # Simulate that the folder has been moved to error folder root (fallback behavior)
            moved_folder = self.error_folder / "external_empty"
            moved_folder.mkdir(parents=True)
            
            # Create empty folder log
            self.error_handler.create_empty_folder_log(original_folder_path)
            
            # Verify log file was created in error folder root
            log_file_path = moved_folder / "empty_folder.log"
            assert log_file_path.exists(), "Empty folder log file was not created for external folder"
            
            # Verify log content
            log_content = log_file_path.read_text()
            assert "EMPTY FOLDER LOG" in log_content
            assert original_folder_path in log_content
    
    def test_create_empty_folder_log_content_format(self):
        """Test empty folder log file content format and structure."""
        # Create empty folder path
        original_folder_path = str(self.source_folder / "format_test")
        
        # Simulate that the folder has been moved to error folder
        moved_folder = self.error_folder / "format_test"
        moved_folder.mkdir(parents=True)
        
        # Mock datetime to get predictable timestamp
        with patch('src.services.error_handler.datetime') as mock_datetime:
            mock_now = datetime(2025, 1, 23, 10, 30, 45, 123456)
            mock_datetime.now.return_value = mock_now
            
            # Create empty folder log
            self.error_handler.create_empty_folder_log(original_folder_path)
        
        # Verify log file content format
        log_file_path = moved_folder / "empty_folder.log"
        log_content = log_file_path.read_text()
        
        # Check required sections and format
        assert "=" * 50 in log_content  # Header separator
        assert "EMPTY FOLDER LOG" in log_content
        assert "Timestamp: 2025-01-23T10:30:45.123456" in log_content
        assert f"Folder: {original_folder_path}" in log_content
        assert "Reason: Completely empty folder detected (no files, no subfolders) and moved to error folder" in log_content
        assert f"Original Path: {original_folder_path}" in log_content
        assert f"Moved To: {moved_folder}" in log_content
        
        # Verify proper line structure
        lines = log_content.split('\n')
        assert any("Timestamp:" in line for line in lines)
        assert any("Folder:" in line for line in lines)
        assert any("Reason:" in line for line in lines)
        assert any("Original Path:" in line for line in lines)
        assert any("Moved To:" in line for line in lines)
    
    def test_create_empty_folder_log_multiple_folders(self):
        """Test creating empty folder logs for multiple folders."""
        # Create multiple empty folder paths
        folder_names = ["empty1", "empty2", "empty3"]
        
        for folder_name in folder_names:
            original_folder_path = str(self.source_folder / folder_name)
            
            # Simulate that the folder has been moved to error folder
            moved_folder = self.error_folder / folder_name
            moved_folder.mkdir(parents=True)
            
            # Create empty folder log
            self.error_handler.create_empty_folder_log(original_folder_path)
            
            # Verify log file was created
            log_file_path = moved_folder / "empty_folder.log"
            assert log_file_path.exists(), f"Empty folder log file was not created for {folder_name}"
            
            # Verify log content is unique for each folder
            log_content = log_file_path.read_text()
            assert original_folder_path in log_content
            assert folder_name in log_content
    
    def test_create_empty_folder_log_handles_write_failure(self):
        """Test empty folder log creation handles write failures gracefully."""
        # Create empty folder path
        original_folder_path = str(self.source_folder / "write_failure_test")
        
        # Simulate that the folder has been moved to error folder
        moved_folder = self.error_folder / "write_failure_test"
        moved_folder.mkdir(parents=True)
        
        # Mock open to raise PermissionError
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            with patch('builtins.print') as mock_print:
                # Should not raise exception, but print error message
                self.error_handler.create_empty_folder_log(original_folder_path)
                
                # Should print error message instead of crashing
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                assert "Failed to create empty folder log" in call_args
                assert original_folder_path in call_args
    
    def test_create_empty_folder_log_unicode_folder_names(self):
        """Test empty folder log creation with unicode folder names."""
        # Test with various unicode folder names
        unicode_names = [
            "пустая_папка",  # Cyrillic
            "空文件夹",       # Chinese
            "空のフォルダ",   # Japanese
            "κενός_φάκελος", # Greek
            "dossier_vide"   # French with accents
        ]
        
        for folder_name in unicode_names:
            original_folder_path = str(self.source_folder / folder_name)
            
            # Simulate that the folder has been moved to error folder
            moved_folder = self.error_folder / folder_name
            moved_folder.mkdir(parents=True)
            
            # Create empty folder log
            self.error_handler.create_empty_folder_log(original_folder_path)
            
            # Verify log file was created
            log_file_path = moved_folder / "empty_folder.log"
            assert log_file_path.exists(), f"Empty folder log file was not created for unicode folder {folder_name}"
            
            # Verify log content with proper encoding
            log_content = log_file_path.read_text(encoding='utf-8')
            assert original_folder_path in log_content
            assert folder_name in log_content
    
    def test_create_empty_folder_log_deep_nested_structure(self):
        """Test empty folder log creation with deeply nested folder structure."""
        # Create deeply nested empty folder path
        deep_path = "level1/level2/level3/level4/level5/deep_empty"
        original_folder_path = str(self.source_folder / deep_path)
        
        # Simulate that the folder has been moved to error folder with structure preservation
        moved_folder = self.error_folder / deep_path
        moved_folder.mkdir(parents=True)
        
        # Create empty folder log
        self.error_handler.create_empty_folder_log(original_folder_path)
        
        # Verify log file was created in correct deep location
        log_file_path = moved_folder / "empty_folder.log"
        assert log_file_path.exists(), "Empty folder log file was not created in deep nested structure"
        
        # Verify all intermediate directories exist
        assert log_file_path.parent.exists()
        assert log_file_path.parent.is_dir()
        
        # Verify log content
        log_content = log_file_path.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert original_folder_path in log_content
        assert "level5/deep_empty" in log_content
    
    def test_empty_folder_log_timestamp_format(self):
        """Test that empty folder log timestamps are properly formatted."""
        # Create empty folder path
        original_folder_path = str(self.source_folder / "timestamp_test")
        
        # Simulate that the folder has been moved to error folder
        moved_folder = self.error_folder / "timestamp_test"
        moved_folder.mkdir(parents=True)
        
        # Mock datetime for predictable timestamp
        with patch('src.services.error_handler.datetime') as mock_datetime:
            mock_now = datetime(2025, 1, 23, 15, 45, 30, 987654)
            mock_datetime.now.return_value = mock_now
            
            # Create empty folder log
            self.error_handler.create_empty_folder_log(original_folder_path)
        
        # Verify timestamp format in log
        log_file_path = moved_folder / "empty_folder.log"
        log_content = log_file_path.read_text()
        
        assert "Timestamp: 2025-01-23T15:45:30.987654" in log_content