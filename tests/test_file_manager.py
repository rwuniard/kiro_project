"""
Unit tests for FileManager class.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from src.core.file_manager import FileManager


class TestFileManager:
    """Test cases for FileManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_folder = Path(self.temp_dir) / "source"
        self.saved_folder = Path(self.temp_dir) / "saved"
        self.error_folder = Path(self.temp_dir) / "error"
        
        # Create the directories
        self.source_folder.mkdir(parents=True)
        self.saved_folder.mkdir(parents=True)
        self.error_folder.mkdir(parents=True)
        
        # Initialize FileManager
        self.file_manager = FileManager(
            str(self.source_folder),
            str(self.saved_folder),
            str(self.error_folder)
        )
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        # Remove temporary directory and all contents
        shutil.rmtree(self.temp_dir)
    
    def test_init_file_manager(self):
        """Test FileManager initialization."""
        assert self.file_manager.source_folder == self.source_folder.resolve()
        assert self.file_manager.saved_folder == self.saved_folder.resolve()
        assert self.file_manager.error_folder == self.error_folder.resolve()
    
    def test_move_to_saved_simple_file(self):
        """Test moving a file from source root to saved folder."""
        # Create test file in source folder
        test_file = self.source_folder / "test.txt"
        test_file.write_text("test content")
        
        # Move file to saved folder
        result = self.file_manager.move_to_saved(str(test_file))
        
        # Verify move was successful
        assert result is True
        assert not test_file.exists()
        
        # Verify file exists in saved folder with same name
        saved_file = self.saved_folder / "test.txt"
        assert saved_file.exists()
        assert saved_file.read_text() == "test content"
    
    def test_move_to_saved_with_folder_structure(self):
        """Test moving a file with nested folder structure preservation."""
        # Create nested folder structure in source
        nested_folder = self.source_folder / "subfolder" / "deep"
        nested_folder.mkdir(parents=True)
        
        # Create test file in nested folder
        test_file = nested_folder / "nested_test.txt"
        test_file.write_text("nested content")
        
        # Move file to saved folder
        result = self.file_manager.move_to_saved(str(test_file))
        
        # Verify move was successful
        assert result is True
        assert not test_file.exists()
        
        # Verify file exists in saved folder with preserved structure
        saved_file = self.saved_folder / "subfolder" / "deep" / "nested_test.txt"
        assert saved_file.exists()
        assert saved_file.read_text() == "nested content"
        
        # Verify folder structure was created
        assert (self.saved_folder / "subfolder").exists()
        assert (self.saved_folder / "subfolder" / "deep").exists()
    
    def test_move_to_error_simple_file(self):
        """Test moving a file from source root to error folder."""
        # Create test file in source folder
        test_file = self.source_folder / "error_test.txt"
        test_file.write_text("error content")
        
        # Move file to error folder
        result = self.file_manager.move_to_error(str(test_file))
        
        # Verify move was successful
        assert result is True
        assert not test_file.exists()
        
        # Verify file exists in error folder with same name
        error_file = self.error_folder / "error_test.txt"
        assert error_file.exists()
        assert error_file.read_text() == "error content"
    
    def test_move_to_error_with_folder_structure(self):
        """Test moving a file to error folder with nested structure preservation."""
        # Create nested folder structure in source
        nested_folder = self.source_folder / "errors" / "critical"
        nested_folder.mkdir(parents=True)
        
        # Create test file in nested folder
        test_file = nested_folder / "critical_error.txt"
        test_file.write_text("critical error content")
        
        # Move file to error folder
        result = self.file_manager.move_to_error(str(test_file))
        
        # Verify move was successful
        assert result is True
        assert not test_file.exists()
        
        # Verify file exists in error folder with preserved structure
        error_file = self.error_folder / "errors" / "critical" / "critical_error.txt"
        assert error_file.exists()
        assert error_file.read_text() == "critical error content"
        
        # Verify folder structure was created
        assert (self.error_folder / "errors").exists()
        assert (self.error_folder / "errors" / "critical").exists()
    
    def test_preserve_folder_structure_relative_path(self):
        """Test folder structure preservation calculation."""
        # Create nested file path
        nested_folder = self.source_folder / "level1" / "level2"
        nested_folder.mkdir(parents=True)
        test_file = nested_folder / "test.txt"
        test_file.write_text("test")
        
        # Calculate preserved path
        dest_path = self.file_manager._preserve_folder_structure(
            test_file, self.saved_folder
        )
        
        expected_path = self.saved_folder / "level1" / "level2" / "test.txt"
        assert dest_path == expected_path
    
    def test_preserve_folder_structure_file_outside_source(self):
        """Test handling of files outside source folder."""
        # Create file outside source folder
        external_file = Path(self.temp_dir) / "external.txt"
        external_file.write_text("external content")
        
        # Calculate preserved path (should use filename only)
        dest_path = self.file_manager._preserve_folder_structure(
            external_file, self.saved_folder
        )
        
        expected_path = self.saved_folder / "external.txt"
        assert dest_path == expected_path
    
    def test_ensure_directory_exists_new_directory(self):
        """Test directory creation functionality."""
        new_dir = self.saved_folder / "new" / "nested" / "directory"
        
        # Ensure directory doesn't exist initially
        assert not new_dir.exists()
        
        # Create directory
        self.file_manager._ensure_directory_exists(new_dir)
        
        # Verify directory was created
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_ensure_directory_exists_existing_directory(self):
        """Test directory creation with existing directory."""
        existing_dir = self.saved_folder / "existing"
        existing_dir.mkdir()
        
        # Should not raise error for existing directory
        self.file_manager._ensure_directory_exists(existing_dir)
        
        # Directory should still exist
        assert existing_dir.exists()
    
    def test_get_relative_path_valid_file(self):
        """Test getting relative path for file under source folder."""
        # Create nested file
        nested_folder = self.source_folder / "sub1" / "sub2"
        nested_folder.mkdir(parents=True)
        test_file = nested_folder / "file.txt"
        test_file.write_text("test")
        
        relative_path = self.file_manager.get_relative_path(str(test_file))
        
        expected_path = "sub1/sub2/file.txt"
        assert relative_path == expected_path
    
    def test_get_relative_path_file_outside_source(self):
        """Test getting relative path for file outside source folder."""
        external_file = Path(self.temp_dir) / "external.txt"
        external_file.write_text("external")
        
        relative_path = self.file_manager.get_relative_path(str(external_file))
        
        assert relative_path is None
    
    @patch('shutil.copy2')
    @patch('shutil.move')
    def test_move_to_saved_file_operation_error(self, mock_move, mock_copy2):
        """Test error handling when both atomic move and copy fallback fail."""
        # Mock both shutil.move and shutil.copy2 to raise exceptions
        mock_move.side_effect = OSError("Permission denied")
        mock_copy2.side_effect = OSError("Permission denied")
        
        # Create test file
        test_file = self.source_folder / "test.txt"
        test_file.write_text("test content")
        
        # Attempt to move file (should handle error gracefully)
        result = self.file_manager.move_to_saved(str(test_file))
        
        # Verify error was handled
        assert result is False
        # Original file should still exist since move failed
        assert test_file.exists()
    
    @patch('shutil.copy2')
    @patch('shutil.move')
    def test_move_to_error_file_operation_error(self, mock_move, mock_copy2):
        """Test error handling when both atomic move and copy fallback fail."""
        # Mock both shutil.move and shutil.copy2 to raise exceptions
        mock_move.side_effect = OSError("Disk full")
        mock_copy2.side_effect = OSError("Disk full")
        
        # Create test file
        test_file = self.source_folder / "test.txt"
        test_file.write_text("test content")
        
        # Attempt to move file (should handle error gracefully)
        result = self.file_manager.move_to_error(str(test_file))
        
        # Verify error was handled
        assert result is False
        # Original file should still exist since move failed
        assert test_file.exists()
    
    @patch('pathlib.Path.mkdir')
    def test_ensure_directory_exists_creation_error(self, mock_mkdir):
        """Test error handling when directory creation fails."""
        # Mock mkdir to raise an exception
        mock_mkdir.side_effect = OSError("Permission denied")
        
        new_dir = self.saved_folder / "new_dir"
        
        # Should raise the exception
        with pytest.raises(OSError):
            self.file_manager._ensure_directory_exists(new_dir)
    
    def test_move_multiple_files_same_structure(self):
        """Test moving multiple files with same folder structure."""
        # Create multiple files in same nested structure
        nested_folder = self.source_folder / "batch" / "files"
        nested_folder.mkdir(parents=True)
        
        files = ["file1.txt", "file2.txt", "file3.txt"]
        for filename in files:
            test_file = nested_folder / filename
            test_file.write_text(f"content of {filename}")
        
        # Move all files to saved folder
        for filename in files:
            test_file = nested_folder / filename
            result = self.file_manager.move_to_saved(str(test_file))
            assert result is True
        
        # Verify all files were moved with preserved structure
        for filename in files:
            saved_file = self.saved_folder / "batch" / "files" / filename
            assert saved_file.exists()
            assert saved_file.read_text() == f"content of {filename}"
        
        # Verify original files are gone
        for filename in files:
            original_file = nested_folder / filename
            assert not original_file.exists()