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


class TestFileManagerCoverageEnhancement:
    """Additional tests to improve FileManager coverage."""
    
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
    
    def test_move_file_with_resilience_source_file_not_exists(self):
        """Test resilient move when source file doesn't exist."""
        nonexistent_file = str(self.source_folder / "nonexistent.txt")
        
        result = self.file_manager._move_file_with_resilience(
            nonexistent_file, self.saved_folder, "saved"
        )
        
        assert result is False
    
    def test_move_file_with_resilience_source_not_file(self):
        """Test resilient move when source is not a file."""
        # Create a directory instead of file
        test_dir = self.source_folder / "test_directory"
        test_dir.mkdir()
        
        result = self.file_manager._move_file_with_resilience(
            str(test_dir), self.saved_folder, "saved"
        )
        
        assert result is False
    
    def test_resolve_destination_conflict_multiple_conflicts(self):
        """Test destination conflict resolution with multiple existing files."""
        # Create original file and several conflicts
        original_file = self.saved_folder / "conflict.txt"
        original_file.write_text("original")
        
        conflict1 = self.saved_folder / "conflict_001.txt"
        conflict1.write_text("conflict1")
        
        conflict2 = self.saved_folder / "conflict_002.txt"
        conflict2.write_text("conflict2")
        
        # Should resolve to conflict_003.txt
        resolved_path = self.file_manager._resolve_destination_conflict(original_file)
        
        expected_path = self.saved_folder / "conflict_003.txt"
        assert resolved_path == expected_path
    
    def test_resolve_destination_conflict_counter_overflow(self):
        """Test destination conflict resolution counter overflow protection."""
        original_file = self.saved_folder / "overflow.txt"
        original_file.write_text("original")
        
        # Mock Path.exists to always return True to simulate infinite conflicts
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(RuntimeError, match="Cannot resolve file conflict"):
                self.file_manager._resolve_destination_conflict(original_file)
    
    def test_validate_destination_writable_permission_error(self):
        """Test destination writable validation with permission error."""
        # Mock os.access to return False (not writable)
        with patch('os.access', return_value=False):
            with pytest.raises(PermissionError, match="Destination directory is not writable"):
                self.file_manager._validate_destination_writable(self.saved_folder)
    
    def test_atomic_move_copy_delete_fallback_success(self):
        """Test atomic move fallback to copy+delete when move fails."""
        # Create test file
        test_file = self.source_folder / "atomic_test.txt"
        test_file.write_text("test content")
        
        dest_file = self.saved_folder / "atomic_test.txt"
        
        # Mock shutil.move to fail, but copy2 to succeed
        with patch('shutil.move', side_effect=OSError("Move failed")), \
             patch('shutil.copy2') as mock_copy, \
             patch.object(Path, 'unlink') as mock_unlink:
            
            self.file_manager._atomic_move(test_file, dest_file)
            
            # Verify copy2 was called and unlink was called
            mock_copy.assert_called_once_with(str(test_file), str(dest_file))
            mock_unlink.assert_called_once()
    
    def test_atomic_move_copy_delete_fallback_copy_fails(self):
        """Test atomic move fallback when both move and copy fail."""
        # Create test file
        test_file = self.source_folder / "atomic_fail_test.txt"
        test_file.write_text("test content")
        
        dest_file = self.saved_folder / "atomic_fail_test.txt"
        
        # Mock both shutil.move and shutil.copy2 to fail
        with patch('shutil.move', side_effect=OSError("Move failed")), \
             patch('shutil.copy2', side_effect=OSError("Copy failed")):
            
            with pytest.raises(OSError, match="Copy failed"):
                self.file_manager._atomic_move(test_file, dest_file)
    
    def test_atomic_move_copy_delete_fallback_cleanup_on_failure(self):
        """Test atomic move cleanup when copy succeeds but delete fails."""
        # Create test file
        test_file = self.source_folder / "cleanup_test.txt"
        test_file.write_text("test content")
        
        dest_file = self.saved_folder / "cleanup_test.txt"
        
        # Mock shutil.move to fail, copy2 to succeed, but unlink to fail
        with patch('shutil.move', side_effect=OSError("Move failed")), \
             patch('shutil.copy2'), \
             patch.object(Path, 'unlink', side_effect=OSError("Delete failed")), \
             patch.object(Path, 'exists', return_value=True) as mock_exists:
            
            with pytest.raises(OSError, match="Delete failed"):
                self.file_manager._atomic_move(test_file, dest_file)
    
    def test_move_file_with_resilience_retry_logic(self):
        """Test resilient move retry logic with transient failures."""
        # Create test file
        test_file = self.source_folder / "retry_test.txt"
        test_file.write_text("test content")
        
        # Mock _atomic_move to fail twice then succeed
        call_count = 0
        def mock_atomic_move(source_path, dest_path):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise OSError("Transient error")
            # Success on third attempt - actually move the file for verification
            dest_path.write_text("test content")
            source_path.unlink()
        
        with patch.object(self.file_manager, '_atomic_move', side_effect=mock_atomic_move):
            result = self.file_manager._move_file_with_resilience(
                str(test_file), self.saved_folder, "saved"
            )
            
            assert result is True
            assert call_count == 3  # Should have retried twice
    
    def test_move_file_with_resilience_max_retries_exceeded(self):
        """Test resilient move when max retries are exceeded."""
        # Create test file
        test_file = self.source_folder / "max_retry_test.txt"
        test_file.write_text("test content")
        
        # Mock _atomic_move to always fail
        with patch.object(self.file_manager, '_atomic_move', side_effect=OSError("Persistent error")):
            result = self.file_manager._move_file_with_resilience(
                str(test_file), self.saved_folder, "saved"
            )
            
            assert result is False
    
    def test_move_file_with_resilience_verification_failure(self):
        """Test resilient move when verification fails."""
        # Create test file
        test_file = self.source_folder / "verify_test.txt"
        test_file.write_text("test content")
        
        # Mock atomic move to succeed but verification to fail
        with patch.object(self.file_manager, '_atomic_move'), \
             patch.object(Path, 'exists', return_value=False):  # Dest doesn't exist after move
            
            result = self.file_manager._move_file_with_resilience(
                str(test_file), self.saved_folder, "saved"
            )
            
            assert result is False