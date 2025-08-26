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


class TestFileManagerEmptyFolderDetection:
    """Test cases for empty folder detection functionality."""
    
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
    
    def test_is_folder_empty_truly_empty_folder(self):
        """Test empty folder detection for a completely empty folder."""
        empty_folder = self.source_folder / "empty"
        empty_folder.mkdir()
        
        result = self.file_manager._is_folder_empty(empty_folder)
        
        assert result is True
    
    def test_is_folder_empty_folder_with_file(self):
        """Test empty folder detection for folder containing a file."""
        folder_with_file = self.source_folder / "with_file"
        folder_with_file.mkdir()
        
        # Add a file to the folder
        test_file = folder_with_file / "test.txt"
        test_file.write_text("content")
        
        result = self.file_manager._is_folder_empty(folder_with_file)
        
        assert result is False
    
    def test_is_folder_empty_folder_with_empty_subfolders(self):
        """Test empty folder detection for folder with only empty subfolders."""
        folder_with_empty_subs = self.source_folder / "with_empty_subs"
        folder_with_empty_subs.mkdir()
        
        # Create empty subfolders
        (folder_with_empty_subs / "empty1").mkdir()
        (folder_with_empty_subs / "empty2").mkdir()
        (folder_with_empty_subs / "nested" / "empty3").mkdir(parents=True)
        
        result = self.file_manager._is_folder_empty(folder_with_empty_subs)
        
        assert result is True
    
    def test_is_folder_empty_folder_with_file_in_subfolder(self):
        """Test empty folder detection for folder with file in subfolder."""
        folder_with_nested_file = self.source_folder / "with_nested_file"
        folder_with_nested_file.mkdir()
        
        # Create nested structure with file
        nested_folder = folder_with_nested_file / "level1" / "level2"
        nested_folder.mkdir(parents=True)
        
        # Add file in nested folder
        nested_file = nested_folder / "nested.txt"
        nested_file.write_text("nested content")
        
        result = self.file_manager._is_folder_empty(folder_with_nested_file)
        
        assert result is False
    
    def test_is_folder_empty_mixed_empty_and_non_empty_subfolders(self):
        """Test empty folder detection with mix of empty and non-empty subfolders."""
        mixed_folder = self.source_folder / "mixed"
        mixed_folder.mkdir()
        
        # Create empty subfolder
        (mixed_folder / "empty_sub").mkdir()
        
        # Create non-empty subfolder
        non_empty_sub = mixed_folder / "non_empty_sub"
        non_empty_sub.mkdir()
        (non_empty_sub / "file.txt").write_text("content")
        
        result = self.file_manager._is_folder_empty(mixed_folder)
        
        assert result is False
    
    def test_is_folder_empty_nonexistent_folder(self):
        """Test empty folder detection for non-existent folder."""
        nonexistent_folder = self.source_folder / "nonexistent"
        
        result = self.file_manager._is_folder_empty(nonexistent_folder)
        
        assert result is False
    
    def test_is_folder_empty_file_instead_of_folder(self):
        """Test empty folder detection when path points to a file."""
        test_file = self.source_folder / "test_file.txt"
        test_file.write_text("content")
        
        result = self.file_manager._is_folder_empty(test_file)
        
        assert result is False
    
    def test_is_folder_empty_permission_error(self):
        """Test empty folder detection with permission error."""
        test_folder = self.source_folder / "permission_test"
        test_folder.mkdir()
        
        # Mock iterdir to raise PermissionError
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
            result = self.file_manager._is_folder_empty(test_folder)
            
            assert result is False
    
    def test_check_folder_contents_recursive_deeply_nested_empty(self):
        """Test recursive folder content checking with deeply nested empty structure."""
        deep_folder = self.source_folder / "deep"
        deep_folder.mkdir()
        
        # Create deeply nested empty structure
        current = deep_folder
        for i in range(5):
            current = current / f"level{i}"
            current.mkdir()
        
        result = self.file_manager._check_folder_contents_recursive(deep_folder)
        
        assert result is True
    
    def test_check_folder_contents_recursive_deeply_nested_with_file(self):
        """Test recursive folder content checking with file at deep level."""
        deep_folder = self.source_folder / "deep_with_file"
        deep_folder.mkdir()
        
        # Create deeply nested structure with file at the end
        current = deep_folder
        for i in range(3):
            current = current / f"level{i}"
            current.mkdir()
        
        # Add file at deepest level
        (current / "deep_file.txt").write_text("deep content")
        
        result = self.file_manager._check_folder_contents_recursive(deep_folder)
        
        assert result is False
    
    def test_check_folder_contents_recursive_permission_error(self):
        """Test recursive folder content checking with permission error."""
        test_folder = self.source_folder / "recursive_permission_test"
        test_folder.mkdir()
        
        # Mock iterdir to raise PermissionError
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
            result = self.file_manager._check_folder_contents_recursive(test_folder)
            
            assert result is False
    
    def test_check_folder_contents_recursive_os_error(self):
        """Test recursive folder content checking with OS error."""
        test_folder = self.source_folder / "recursive_os_error_test"
        test_folder.mkdir()
        
        # Mock iterdir to raise OSError
        with patch.object(Path, 'iterdir', side_effect=OSError("Disk error")):
            result = self.file_manager._check_folder_contents_recursive(test_folder)
            
            assert result is False
    
    def test_is_folder_empty_complex_nested_structure(self):
        """Test empty folder detection with complex nested structure."""
        complex_folder = self.source_folder / "complex"
        complex_folder.mkdir()
        
        # Create complex structure with multiple levels and empty folders
        (complex_folder / "branch1" / "subbranch1").mkdir(parents=True)
        (complex_folder / "branch1" / "subbranch2").mkdir(parents=True)
        (complex_folder / "branch2" / "deep" / "deeper").mkdir(parents=True)
        (complex_folder / "branch3").mkdir()
        
        # All folders are empty, so should return True
        result = self.file_manager._is_folder_empty(complex_folder)
        
        assert result is True
        
        # Now add a file deep in the structure
        (complex_folder / "branch2" / "deep" / "deeper" / "hidden.txt").write_text("hidden")
        
        # Should now return False
        result = self.file_manager._is_folder_empty(complex_folder)
        
        assert result is False


class TestEmptyFolderHandling:
    """Test cases for empty folder handling functionality (Task 15.2)."""
    
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
    
    def test_completely_empty_folder_detection_truly_empty(self):
        """Test completely empty folder detection (no files, no subfolders)."""
        # Create completely empty folder
        empty_folder = self.source_folder / "completely_empty"
        empty_folder.mkdir()
        
        result = self.file_manager.is_completely_empty_folder(str(empty_folder))
        
        assert result is True
    
    def test_completely_empty_folder_detection_with_files(self):
        """Test that folders with files are NOT detected as completely empty."""
        # Create folder with file
        folder_with_file = self.source_folder / "with_file"
        folder_with_file.mkdir()
        (folder_with_file / "test.txt").write_text("content")
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_file))
        
        assert result is False
    
    def test_completely_empty_folder_detection_with_empty_subfolders(self):
        """Test that folders with empty subfolders are NOT detected as completely empty."""
        # Create folder with empty subfolder
        folder_with_empty_sub = self.source_folder / "with_empty_sub"
        folder_with_empty_sub.mkdir()
        (folder_with_empty_sub / "empty_sub").mkdir()
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_empty_sub))
        
        assert result is False
    
    def test_completely_empty_folder_detection_with_nested_empty_subfolders(self):
        """Test that folders with nested empty subfolders are NOT detected as completely empty."""
        # Create folder with nested empty subfolders
        folder_with_nested = self.source_folder / "with_nested"
        folder_with_nested.mkdir()
        nested_path = folder_with_nested / "level1" / "level2" / "level3"
        nested_path.mkdir(parents=True)
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_nested))
        
        assert result is False
    
    def test_completely_empty_folder_detection_nonexistent_folder(self):
        """Test completely empty folder detection for non-existent folder."""
        nonexistent_folder = self.source_folder / "nonexistent"
        
        result = self.file_manager.is_completely_empty_folder(str(nonexistent_folder))
        
        assert result is False
    
    def test_completely_empty_folder_detection_file_instead_of_folder(self):
        """Test completely empty folder detection when path points to a file."""
        test_file = self.source_folder / "test_file.txt"
        test_file.write_text("content")
        
        result = self.file_manager.is_completely_empty_folder(str(test_file))
        
        assert result is False
    
    def test_move_empty_folder_to_error_success(self):
        """Test successful movement of completely empty folder to error folder."""
        # Create completely empty folder
        empty_folder = self.source_folder / "empty_test"
        empty_folder.mkdir()
        
        # Move to error folder
        result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        
        # Verify move was successful
        assert result is True
        assert not empty_folder.exists()
        
        # Verify folder exists in error folder
        error_folder_path = self.error_folder / "empty_test"
        assert error_folder_path.exists()
        assert error_folder_path.is_dir()
    
    def test_move_empty_folder_to_error_with_structure_preservation(self):
        """Test empty folder movement to error folder with structure preservation."""
        # Create nested empty folder
        nested_empty = self.source_folder / "level1" / "level2" / "empty_nested"
        nested_empty.mkdir(parents=True)
        
        # Move to error folder
        result = self.file_manager.move_empty_folder_to_error(str(nested_empty))
        
        # Verify move was successful
        assert result is True
        assert not nested_empty.exists()
        
        # Verify folder exists in error folder with preserved structure
        error_folder_path = self.error_folder / "level1" / "level2" / "empty_nested"
        assert error_folder_path.exists()
        assert error_folder_path.is_dir()
        
        # Verify intermediate directories were created
        assert (self.error_folder / "level1").exists()
        assert (self.error_folder / "level1" / "level2").exists()
    
    def test_move_empty_folder_to_error_fails_for_non_empty_folder(self):
        """Test that moving non-empty folder to error folder fails."""
        # Create folder with file
        folder_with_file = self.source_folder / "not_empty"
        folder_with_file.mkdir()
        (folder_with_file / "file.txt").write_text("content")
        
        # Attempt to move to error folder (should fail)
        result = self.file_manager.move_empty_folder_to_error(str(folder_with_file))
        
        # Verify move failed
        assert result is False
        assert folder_with_file.exists()  # Original folder should still exist
        
        # Verify folder was not moved to error folder
        error_folder_path = self.error_folder / "not_empty"
        assert not error_folder_path.exists()
    
    def test_move_empty_folder_to_error_fails_for_folder_with_subfolders(self):
        """Test that moving folder with subfolders to error folder fails."""
        # Create folder with empty subfolder
        folder_with_sub = self.source_folder / "with_subfolder"
        folder_with_sub.mkdir()
        (folder_with_sub / "empty_sub").mkdir()
        
        # Attempt to move to error folder (should fail)
        result = self.file_manager.move_empty_folder_to_error(str(folder_with_sub))
        
        # Verify move failed
        assert result is False
        assert folder_with_sub.exists()  # Original folder should still exist
        
        # Verify folder was not moved to error folder
        error_folder_path = self.error_folder / "with_subfolder"
        assert not error_folder_path.exists()
    
    def test_move_empty_folder_to_error_handles_destination_conflict(self):
        """Test empty folder movement handles destination conflicts."""
        # Create completely empty folder
        empty_folder = self.source_folder / "conflict_test"
        empty_folder.mkdir()
        
        # Create conflicting folder in error directory
        conflict_folder = self.error_folder / "conflict_test"
        conflict_folder.mkdir()
        (conflict_folder / "existing_file.txt").write_text("existing content")
        
        # Move to error folder (should resolve conflict)
        result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        
        # Verify move was successful
        assert result is True
        assert not empty_folder.exists()
        
        # Verify original conflict folder still exists
        assert conflict_folder.exists()
        assert (conflict_folder / "existing_file.txt").exists()
        
        # Verify new folder was created with conflict resolution
        resolved_folder = self.error_folder / "conflict_test_001"
        assert resolved_folder.exists()
        assert resolved_folder.is_dir()
    
    def test_move_empty_folder_to_error_permission_error(self):
        """Test empty folder movement handles permission errors gracefully."""
        # Create completely empty folder
        empty_folder = self.source_folder / "permission_test"
        empty_folder.mkdir()
        
        # Mock shutil.move to raise PermissionError
        with patch('shutil.move', side_effect=PermissionError("Access denied")):
            result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
            
            # Verify move failed gracefully
            assert result is False
            assert empty_folder.exists()  # Original folder should still exist
    
    def test_completely_empty_folder_detection_permission_error(self):
        """Test completely empty folder detection handles permission errors."""
        # Create test folder
        test_folder = self.source_folder / "permission_test"
        test_folder.mkdir()
        
        # Mock iterdir to raise PermissionError
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
            result = self.file_manager.is_completely_empty_folder(str(test_folder))
            
            # Should return False when permission is denied
            assert result is False
    
    def test_multiple_completely_empty_folders(self):
        """Test handling multiple completely empty folders."""
        # Create multiple completely empty folders
        empty_folders = []
        for i in range(3):
            empty_folder = self.source_folder / f"empty_{i}"
            empty_folder.mkdir()
            empty_folders.append(empty_folder)
        
        # Test detection for all folders
        for folder in empty_folders:
            result = self.file_manager.is_completely_empty_folder(str(folder))
            assert result is True
        
        # Move all to error folder
        for folder in empty_folders:
            result = self.file_manager.move_empty_folder_to_error(str(folder))
            assert result is True
            assert not folder.exists()
            
            # Verify in error folder
            error_path = self.error_folder / folder.name
            assert error_path.exists()
            assert error_path.is_dir()
    
    def test_completely_empty_folder_vs_regular_empty_folder_detection(self):
        """Test difference between completely empty and regular empty folder detection."""
        # Create folder with only empty subfolders (regular empty but not completely empty)
        regular_empty = self.source_folder / "regular_empty"
        regular_empty.mkdir()
        (regular_empty / "empty_sub1").mkdir()
        (regular_empty / "empty_sub2").mkdir()
        (regular_empty / "nested" / "empty_sub3").mkdir(parents=True)
        
        # Test completely empty detection (should be False - has subfolders)
        completely_empty_result = self.file_manager.is_completely_empty_folder(str(regular_empty))
        assert completely_empty_result is False
        
        # Test regular empty detection (should be True - no files, only empty subfolders)
        regular_empty_result = self.file_manager._is_folder_empty(regular_empty)
        assert regular_empty_result is True
        
        # Create truly completely empty folder
        completely_empty = self.source_folder / "completely_empty"
        completely_empty.mkdir()
        
        # Test both detection methods (both should be True)
        completely_empty_result = self.file_manager.is_completely_empty_folder(str(completely_empty))
        assert completely_empty_result is True
        
        regular_empty_result = self.file_manager._is_folder_empty(completely_empty)
        assert regular_empty_result is True
    
    def test_completely_empty_folder_detection_with_empty_subfolders(self):
        """Test that folders with empty subfolders are NOT moved (only completely empty folders)."""
        # Create folder with empty subfolders
        folder_with_empty_subs = self.source_folder / "with_empty_subs"
        folder_with_empty_subs.mkdir()
        (folder_with_empty_subs / "empty_sub1").mkdir()
        (folder_with_empty_subs / "empty_sub2").mkdir()
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_empty_subs))
        
        # Should return False because it contains subfolders (even if they're empty)
        assert result is False
    
    def test_completely_empty_folder_detection_with_nested_empty_subfolders(self):
        """Test that folders with nested empty subfolders are NOT detected as completely empty."""
        # Create folder with nested empty structure
        folder_with_nested = self.source_folder / "with_nested"
        folder_with_nested.mkdir()
        nested_path = folder_with_nested / "level1" / "level2" / "level3"
        nested_path.mkdir(parents=True)
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_nested))
        
        # Should return False because it contains subfolders
        assert result is False
    
    def test_completely_empty_folder_detection_nonexistent_folder(self):
        """Test completely empty folder detection for non-existent folder."""
        nonexistent_folder = self.source_folder / "nonexistent"
        
        result = self.file_manager.is_completely_empty_folder(str(nonexistent_folder))
        
        assert result is False
    
    def test_completely_empty_folder_detection_file_instead_of_folder(self):
        """Test completely empty folder detection when path points to a file."""
        test_file = self.source_folder / "test_file.txt"
        test_file.write_text("content")
        
        result = self.file_manager.is_completely_empty_folder(str(test_file))
        
        assert result is False
    
    def test_move_empty_folder_to_error_completely_empty(self):
        """Test moving completely empty folder to error folder with structure preservation."""
        # Create completely empty folder
        empty_folder = self.source_folder / "subfolder" / "empty"
        empty_folder.mkdir(parents=True)
        
        # Move empty folder to error
        result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        
        assert result is True
        
        # Verify folder was moved to error folder with preserved structure
        expected_error_path = self.error_folder / "subfolder" / "empty"
        assert expected_error_path.exists()
        assert expected_error_path.is_dir()
        
        # Verify original folder no longer exists
        assert not empty_folder.exists()
    
    def test_move_empty_folder_to_error_not_empty(self):
        """Test that non-empty folders are not moved to error folder."""
        # Create folder with file
        folder_with_file = self.source_folder / "not_empty"
        folder_with_file.mkdir()
        (folder_with_file / "file.txt").write_text("content")
        
        # Attempt to move (should fail)
        result = self.file_manager.move_empty_folder_to_error(str(folder_with_file))
        
        assert result is False
        
        # Verify folder still exists in source
        assert folder_with_file.exists()
        
        # Verify folder was not moved to error
        error_path = self.error_folder / "not_empty"
        assert not error_path.exists()
    
    def test_move_empty_folder_to_error_with_empty_subfolders(self):
        """Test that folders with empty subfolders are not moved."""
        # Create folder with empty subfolders
        folder_with_subs = self.source_folder / "with_subs"
        folder_with_subs.mkdir()
        (folder_with_subs / "empty_sub").mkdir()
        
        # Attempt to move (should fail because it has subfolders)
        result = self.file_manager.move_empty_folder_to_error(str(folder_with_subs))
        
        assert result is False
        
        # Verify folder still exists in source
        assert folder_with_subs.exists()
    
    def test_move_empty_folder_to_error_root_level(self):
        """Test moving completely empty folder at root level."""
        # Create empty folder at root level
        empty_root_folder = self.source_folder / "empty_root"
        empty_root_folder.mkdir()
        
        # Move empty folder to error
        result = self.file_manager.move_empty_folder_to_error(str(empty_root_folder))
        
        assert result is True
        
        # Verify folder was moved to error folder
        expected_error_path = self.error_folder / "empty_root"
        assert expected_error_path.exists()
        assert expected_error_path.is_dir()
        
        # Verify original folder no longer exists
        assert not empty_root_folder.exists()
    
    def test_move_empty_folder_to_error_deep_nested_structure(self):
        """Test moving completely empty folder with deeply nested structure preservation."""
        # Create deeply nested empty folder
        deep_empty_folder = self.source_folder / "level1" / "level2" / "level3" / "empty"
        deep_empty_folder.mkdir(parents=True)
        
        # Move empty folder to error
        result = self.file_manager.move_empty_folder_to_error(str(deep_empty_folder))
        
        assert result is True
        
        # Verify folder was moved with full structure preservation
        expected_error_path = self.error_folder / "level1" / "level2" / "level3" / "empty"
        assert expected_error_path.exists()
        assert expected_error_path.is_dir()
        
        # Verify all intermediate directories were created
        assert (self.error_folder / "level1").exists()
        assert (self.error_folder / "level1" / "level2").exists()
        assert (self.error_folder / "level1" / "level2" / "level3").exists()
        
        # Verify original folder no longer exists
        assert not deep_empty_folder.exists()
    
    def test_move_empty_folder_to_error_destination_conflict(self):
        """Test moving empty folder when destination already exists."""
        # Create empty folder
        empty_folder = self.source_folder / "conflict_test"
        empty_folder.mkdir()
        
        # Create conflicting folder in error directory
        conflicting_folder = self.error_folder / "conflict_test"
        conflicting_folder.mkdir()
        (conflicting_folder / "existing.txt").write_text("existing content")
        
        # Move empty folder (should resolve conflict)
        result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        
        assert result is True
        
        # Verify original folder no longer exists
        assert not empty_folder.exists()
        
        # Verify conflicting folder still exists with its content
        assert conflicting_folder.exists()
        assert (conflicting_folder / "existing.txt").exists()
        
        # Verify moved folder exists with resolved name
        resolved_folder = self.error_folder / "conflict_test_001"
        assert resolved_folder.exists()
    
    def test_move_empty_folder_to_error_permission_error(self):
        """Test handling of permission errors during empty folder move."""
        # Create empty folder
        empty_folder = self.source_folder / "permission_test"
        empty_folder.mkdir()
        
        # Mock shutil.move to raise permission error
        with patch('shutil.move', side_effect=PermissionError("Access denied")):
            result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
            
            assert result is False
            
            # Verify folder still exists in source
            assert empty_folder.exists()
    
    def test_empty_folder_detection_vs_regular_empty_detection(self):
        """Test difference between completely empty and regular empty folder detection."""
        # Create folder with only empty subfolders
        folder_with_empty_subs = self.source_folder / "mixed_empty"
        folder_with_empty_subs.mkdir()
        (folder_with_empty_subs / "empty1").mkdir()
        (folder_with_empty_subs / "empty2" / "nested_empty").mkdir(parents=True)
        
        # Regular empty detection should return True (no files anywhere)
        regular_empty = self.file_manager._is_folder_empty(folder_with_empty_subs)
        assert regular_empty is True
        
        # Completely empty detection should return False (has subfolders)
        completely_empty = self.file_manager.is_completely_empty_folder(str(folder_with_empty_subs))
        assert completely_empty is False
    
    def test_empty_folder_handling_integration_with_error_handler(self):
        """Test integration of empty folder handling with ErrorHandler for log creation."""
        from src.services.error_handler import ErrorHandler
        
        # Create ErrorHandler
        error_handler = ErrorHandler(str(self.error_folder), str(self.source_folder))
        
        # Create completely empty folder
        empty_folder = self.source_folder / "integration_test"
        empty_folder.mkdir()
        
        # Move empty folder to error
        result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        assert result is True
        
        # Create empty folder log using ErrorHandler
        error_handler.create_empty_folder_log(str(empty_folder))
        
        # Verify log file was created
        moved_folder = self.error_folder / "integration_test"
        log_file = moved_folder / "empty_folder.log"
        assert log_file.exists()
        
        # Verify log content
        log_content = log_file.read_text()
        assert "EMPTY FOLDER LOG" in log_content
        assert str(empty_folder) in log_content
        assert "Completely empty folder detected" in log_content
        assert str(moved_folder) in log_content
    
    def test_empty_folder_handling_multiple_empty_folders(self):
        """Test handling multiple completely empty folders."""
        # Create multiple completely empty folders
        empty_folders = [
            self.source_folder / "empty1",
            self.source_folder / "branch" / "empty2", 
            self.source_folder / "deep" / "nested" / "empty3"
        ]
        
        for folder in empty_folders:
            folder.mkdir(parents=True)
        
        # Move all empty folders to error
        for folder in empty_folders:
            result = self.file_manager.move_empty_folder_to_error(str(folder))
            assert result is True
        
        # Verify all folders were moved with structure preservation
        expected_paths = [
            self.error_folder / "empty1",
            self.error_folder / "branch" / "empty2",
            self.error_folder / "deep" / "nested" / "empty3"
        ]
        
        for expected_path in expected_paths:
            assert expected_path.exists()
            assert expected_path.is_dir()
        
        # Verify original folders no longer exist
        for folder in empty_folders:
            assert not folder.exists()
    
    def test_empty_folder_handling_with_regular_file_processing(self):
        """Test integration of empty folder handling with regular file processing workflow."""
        # Create a mixed structure with files and empty folders
        
        # Create file that will be processed
        test_file = self.source_folder / "subfolder" / "test.txt"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test content")
        
        # Create completely empty folder in same structure
        empty_folder = self.source_folder / "subfolder" / "empty"
        empty_folder.mkdir()
        
        # Create folder with empty subfolders (should NOT be moved)
        folder_with_subs = self.source_folder / "subfolder" / "with_subs"
        folder_with_subs.mkdir()
        (folder_with_subs / "empty_sub").mkdir()
        
        # Simulate file processing by moving file to saved
        file_move_result = self.file_manager.move_to_saved(str(test_file))
        assert file_move_result is True
        
        # Handle empty folder
        empty_move_result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        assert empty_move_result is True
        
        # Attempt to move folder with subfolders (should fail)
        subs_move_result = self.file_manager.move_empty_folder_to_error(str(folder_with_subs))
        assert subs_move_result is False
        
        # Verify final state
        # File should be in saved folder
        assert (self.saved_folder / "subfolder" / "test.txt").exists()
        
        # Completely empty folder should be in error folder
        assert (self.error_folder / "subfolder" / "empty").exists()
        
        # Folder with subfolders should still be in source
        assert folder_with_subs.exists()
        assert (folder_with_subs / "empty_sub").exists()
    
    def test_empty_folder_detection_performance_with_large_structures(self):
        """Test empty folder detection performance with large nested structures."""
        # Create a large nested structure with many empty folders
        base_folder = self.source_folder / "large_structure"
        base_folder.mkdir()
        
        # Create 50 nested levels of empty folders
        current_folder = base_folder
        for i in range(50):
            current_folder = current_folder / f"level_{i}"
            current_folder.mkdir()
        
        # Test completely empty detection (should be False due to subfolders)
        result = self.file_manager.is_completely_empty_folder(str(base_folder))
        assert result is False
        
        # Test regular empty detection (should be True as no files anywhere)
        result = self.file_manager._is_folder_empty(base_folder)
        assert result is True
        
        # Test the deepest folder (should be completely empty)
        result = self.file_manager.is_completely_empty_folder(str(current_folder))
        assert result is True   
 
    def test_cleanup_empty_folders_single_empty_folder(self):
        """Test cleanup of a single empty folder after file removal."""
        # Create nested structure with file
        nested_folder = self.source_folder / "level1" / "level2"
        nested_folder.mkdir(parents=True)
        test_file = nested_folder / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal by deleting it
        test_file.unlink()
        
        # Run cleanup
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should remove both level2 and level1 folders
        assert len(removed_folders) == 2
        
        # Use resolved paths for comparison to handle symlinks/aliases
        removed_paths = [Path(p).resolve() for p in removed_folders]
        assert nested_folder.resolve() in removed_paths
        assert nested_folder.parent.resolve() in removed_paths
        
        # Verify folders were actually removed
        assert not nested_folder.exists()
        assert not nested_folder.parent.exists()
        
        # Source folder should still exist
        assert self.source_folder.exists()
    
    def test_cleanup_empty_folders_stops_at_non_empty_folder(self):
        """Test cleanup stops when encountering a non-empty folder."""
        # Create nested structure
        level1 = self.source_folder / "level1"
        level2 = level1 / "level2"
        level3 = level2 / "level3"
        level3.mkdir(parents=True)
        
        # Add files to different levels
        (level1 / "keep.txt").write_text("keep this")
        test_file = level3 / "remove.txt"
        test_file.write_text("remove this")
        
        # Simulate file removal
        test_file.unlink()
        
        # Run cleanup
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should only remove level3 and level2, but not level1 (has keep.txt)
        assert len(removed_folders) == 2
        
        # Use resolved paths for comparison
        removed_paths = [Path(p).resolve() for p in removed_folders]
        assert level3.resolve() in removed_paths
        assert level2.resolve() in removed_paths
        assert level1.resolve() not in removed_paths
        
        # Verify correct folders were removed
        assert not level3.exists()
        assert not level2.exists()
        assert level1.exists()  # Should still exist because it has keep.txt
        assert (level1 / "keep.txt").exists()
    
    def test_cleanup_empty_folders_stops_at_source_root(self):
        """Test cleanup never removes the source root folder."""
        # Create file directly in source folder
        test_file = self.source_folder / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Run cleanup
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should not remove any folders (source root is protected)
        assert len(removed_folders) == 0
        
        # Source folder should still exist
        assert self.source_folder.exists()
    
    def test_cleanup_empty_folders_with_empty_subfolders(self):
        """Test cleanup behavior when parent folder has empty sibling folders."""
        # Create complex nested structure
        level1 = self.source_folder / "level1"
        level2 = level1 / "level2"
        level3 = level2 / "level3"
        level3.mkdir(parents=True)
        
        # Create empty sibling folders
        (level2 / "empty_sibling1").mkdir()
        (level2 / "empty_sibling2").mkdir()
        
        # Add file only at deepest level
        test_file = level3 / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Run cleanup
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should only remove level3, but not level2 (has empty siblings) or level1
        # This is correct behavior - we don't remove folders that have existing empty subfolders
        assert len(removed_folders) == 1
        
        # Use resolved paths for comparison
        removed_paths = [Path(p).resolve() for p in removed_folders]
        assert level3.resolve() in removed_paths
        
        # Verify only level3 was removed, level2 still exists with its empty siblings
        assert not level3.exists()
        assert level2.exists()
        assert (level2 / "empty_sibling1").exists()
        assert (level2 / "empty_sibling2").exists()
    
    def test_cleanup_empty_folders_permission_error(self):
        """Test cleanup handles permission errors gracefully."""
        # Create nested structure
        nested_folder = self.source_folder / "protected" / "subfolder"
        nested_folder.mkdir(parents=True)
        test_file = nested_folder / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Mock rmdir to raise PermissionError on first call
        original_rmdir = Path.rmdir
        call_count = 0
        
        def mock_rmdir(self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PermissionError("Access denied")
            return original_rmdir(self)
        
        with patch.object(Path, 'rmdir', mock_rmdir):
            removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should stop at first permission error
        assert len(removed_folders) == 0
        
        # Folders should still exist due to permission error
        assert nested_folder.exists()
    
    def test_cleanup_empty_folders_file_outside_source(self):
        """Test cleanup handles files outside source folder safely."""
        # Create file outside source folder
        external_file = Path(self.temp_dir) / "external" / "file.txt"
        external_file.parent.mkdir()
        external_file.write_text("content")
        
        # Run cleanup on external file
        removed_folders = self.file_manager.cleanup_empty_folders(str(external_file))
        
        # Should not remove any folders
        assert len(removed_folders) == 0
        
        # External folder should still exist
        assert external_file.parent.exists()
    
    def test_cleanup_empty_folders_deeply_nested_structure(self):
        """Test cleanup with deeply nested folder structure."""
        # Create deeply nested structure
        current = self.source_folder
        for i in range(5):
            current = current / f"level{i}"
            current.mkdir()
        
        # Add file at deepest level
        test_file = current / "deep.txt"
        test_file.write_text("deep content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Run cleanup
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should remove all 5 levels
        assert len(removed_folders) == 5
        
        # Verify all nested folders were removed
        level0 = self.source_folder / "level0"
        assert not level0.exists()
        
        # Source folder should still exist
        assert self.source_folder.exists()
    
    def test_cleanup_empty_folders_os_error_during_cleanup(self):
        """Test cleanup handles OS errors during folder removal."""
        # Create nested structure
        nested_folder = self.source_folder / "error_test" / "subfolder"
        nested_folder.mkdir(parents=True)
        test_file = nested_folder / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Mock rmdir to raise OSError
        with patch.object(Path, 'rmdir', side_effect=OSError("Disk error")):
            removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should handle error gracefully
        assert len(removed_folders) == 0
    
    def test_is_path_under_source_valid_path(self):
        """Test path validation for paths under source folder."""
        nested_path = self.source_folder / "sub" / "nested"
        nested_path.mkdir(parents=True)
        
        result = self.file_manager._is_path_under_source(nested_path, self.source_folder.resolve())
        
        assert result is True
    
    def test_is_path_under_source_external_path(self):
        """Test path validation for paths outside source folder."""
        external_path = Path(self.temp_dir) / "external"
        external_path.mkdir()
        
        result = self.file_manager._is_path_under_source(external_path, self.source_folder)
        
        assert result is False
    
    def test_is_path_under_source_source_folder_itself(self):
        """Test path validation for source folder itself."""
        result = self.file_manager._is_path_under_source(self.source_folder.resolve(), self.source_folder.resolve())
        
        assert result is True
    
    def test_cleanup_empty_folders_exception_handling(self):
        """Test cleanup handles unexpected exceptions gracefully."""
        nested_folder = self.source_folder / "exception_test"
        nested_folder.mkdir()
        test_file = nested_folder / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Mock Path.resolve to raise an exception early in the process
        original_resolve = Path.resolve
        def mock_resolve(self):
            if "exception_test" in str(self):
                raise Exception("Unexpected error during path resolution")
            return original_resolve(self)
        
        with patch.object(Path, 'resolve', side_effect=mock_resolve):
            removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should handle exception gracefully
        assert len(removed_folders) == 0
    
    def test_cleanup_empty_folders_source_root_protection(self):
        """Test that source root folder is never removed even if empty."""
        # Create file directly in source root
        test_file = self.source_folder / "root_file.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Run cleanup - should not remove source root even though it's empty
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should not remove any folders (source root is protected)
        assert len(removed_folders) == 0
        
        # Source folder should still exist
        assert self.source_folder.exists()
    
    def test_cleanup_empty_folders_symlink_handling(self):
        """Test cleanup handles symlinks correctly."""
        # Create nested structure
        nested_folder = self.source_folder / "symlink_test"
        nested_folder.mkdir()
        
        # Create symlink to external file
        external_file = Path(self.temp_dir) / "external.txt"
        external_file.write_text("external")
        
        symlink_path = nested_folder / "symlink.txt"
        try:
            symlink_path.symlink_to(external_file)
        except OSError:
            # Skip test if symlinks not supported
            pytest.skip("Symlinks not supported on this system")
        
        # Create regular file in same folder
        test_file = nested_folder / "regular.txt"
        test_file.write_text("content")
        
        # Remove regular file, leaving only symlink
        test_file.unlink()
        
        # Run cleanup - folder should not be removed because it contains symlink
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should not remove folder because symlink is considered content
        assert len(removed_folders) == 0
        assert nested_folder.exists()
        assert symlink_path.exists()
    
    def test_cleanup_empty_folders_concurrent_file_creation(self):
        """Test cleanup behavior when rmdir fails due to concurrent file creation."""
        # Create nested structure
        nested_folder = self.source_folder / "concurrent_test"
        nested_folder.mkdir()
        test_file = nested_folder / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Mock rmdir to simulate concurrent file creation (directory not empty error)
        original_rmdir = Path.rmdir
        def mock_rmdir(self):
            if "concurrent_test" in str(self):
                raise OSError("Directory not empty")  # Simulate concurrent file creation
            return original_rmdir(self)
        
        with patch.object(Path, 'rmdir', mock_rmdir):
            removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should handle the race condition gracefully - no folders removed due to concurrent creation
        assert len(removed_folders) == 0
    
    def test_cleanup_empty_folders_nested_permission_errors(self):
        """Test cleanup with permission errors at different nesting levels."""
        # Create deeply nested structure
        level1 = self.source_folder / "perm1"
        level2 = level1 / "perm2"
        level3 = level2 / "perm3"
        level3.mkdir(parents=True)
        
        test_file = level3 / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Mock rmdir to fail on level2 but succeed on level3
        original_rmdir = Path.rmdir
        def mock_rmdir(self):
            if "perm2" in str(self) and "perm3" not in str(self):
                raise PermissionError("Access denied to level2")
            return original_rmdir(self)
        
        with patch.object(Path, 'rmdir', mock_rmdir):
            removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should only remove level3, stop at level2 due to permission error
        assert len(removed_folders) == 1
        cleaned_paths = [Path(p).resolve() for p in removed_folders]
        assert level3.resolve() in cleaned_paths
        
        # Verify level3 was removed but level2 and level1 still exist
        assert not level3.exists()
        assert level2.exists()
        assert level1.exists()
    
    def test_cleanup_empty_folders_very_long_path(self):
        """Test cleanup with very long nested path structure."""
        # Create very deeply nested structure (10 levels)
        current = self.source_folder
        for i in range(10):
            current = current / f"very_long_path_level_{i:02d}"
            current.mkdir()
        
        test_file = current / "deep_file.txt"
        test_file.write_text("very deep content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Run cleanup
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should remove all 10 levels
        assert len(removed_folders) == 10
        
        # Verify all levels were removed
        check_path = self.source_folder / "very_long_path_level_00"
        assert not check_path.exists()
    
    def test_cleanup_empty_folders_special_characters_in_path(self):
        """Test cleanup with special characters in folder names."""
        # Create folders with special characters
        special_folder = self.source_folder / "folder with spaces" / "folder-with-dashes" / "folder_with_underscores"
        special_folder.mkdir(parents=True)
        
        test_file = special_folder / "test file.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Run cleanup
        removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
        
        # Should remove all 3 levels with special characters
        assert len(removed_folders) == 3
        
        # Verify folders were actually removed
        assert not special_folder.exists()
        assert not special_folder.parent.exists()
        assert not special_folder.parent.parent.exists()
    
    def test_cleanup_empty_folders_readonly_folder(self):
        """Test cleanup behavior with read-only folders."""
        # Create nested structure
        nested_folder = self.source_folder / "readonly_test"
        nested_folder.mkdir()
        test_file = nested_folder / "test.txt"
        test_file.write_text("content")
        
        # Simulate file removal
        test_file.unlink()
        
        # Make folder read-only (this might cause rmdir to fail)
        try:
            nested_folder.chmod(0o444)  # Read-only
            
            # Run cleanup
            removed_folders = self.file_manager.cleanup_empty_folders(str(test_file))
            
            # Behavior depends on system - might succeed or fail
            # Just verify it doesn't crash
            assert isinstance(removed_folders, list)
            
        finally:
            # Restore permissions for cleanup
            try:
                nested_folder.chmod(0o755)
            except:
                pass


class TestFileManagerCompletelyEmptyFolderDetection:
    """Test cases for completely empty folder detection and handling."""
    
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
    
    def test_is_completely_empty_folder_truly_empty(self):
        """Test detection of completely empty folder (no files, no subfolders)."""
        empty_folder = self.source_folder / "completely_empty"
        empty_folder.mkdir()
        
        result = self.file_manager.is_completely_empty_folder(str(empty_folder))
        
        assert result is True
    
    def test_is_completely_empty_folder_with_file(self):
        """Test detection when folder contains a file."""
        folder_with_file = self.source_folder / "with_file"
        folder_with_file.mkdir()
        
        # Add a file
        (folder_with_file / "test.txt").write_text("content")
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_file))
        
        assert result is False
    
    def test_is_completely_empty_folder_with_empty_subfolder(self):
        """Test detection when folder contains empty subfolders (should be False)."""
        folder_with_empty_sub = self.source_folder / "with_empty_sub"
        folder_with_empty_sub.mkdir()
        
        # Add empty subfolder
        (folder_with_empty_sub / "empty_sub").mkdir()
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_empty_sub))
        
        assert result is False  # Has subfolder, so not completely empty
    
    def test_is_completely_empty_folder_with_nested_empty_subfolders(self):
        """Test detection with nested empty subfolders (should be False)."""
        folder_with_nested = self.source_folder / "with_nested"
        folder_with_nested.mkdir()
        
        # Create nested empty structure
        (folder_with_nested / "level1" / "level2").mkdir(parents=True)
        
        result = self.file_manager.is_completely_empty_folder(str(folder_with_nested))
        
        assert result is False  # Has subfolders, so not completely empty
    
    def test_is_completely_empty_folder_nonexistent(self):
        """Test detection for non-existent folder."""
        nonexistent = self.source_folder / "nonexistent"
        
        result = self.file_manager.is_completely_empty_folder(str(nonexistent))
        
        assert result is False
    
    def test_is_completely_empty_folder_file_path(self):
        """Test detection when path points to a file."""
        test_file = self.source_folder / "test.txt"
        test_file.write_text("content")
        
        result = self.file_manager.is_completely_empty_folder(str(test_file))
        
        assert result is False
    
    def test_is_completely_empty_folder_permission_error(self):
        """Test detection with permission error."""
        test_folder = self.source_folder / "permission_test"
        test_folder.mkdir()
        
        # Mock iterdir to raise PermissionError
        with patch.object(Path, 'iterdir', side_effect=PermissionError("Access denied")):
            result = self.file_manager.is_completely_empty_folder(str(test_folder))
            
            assert result is False
    
    def test_move_empty_folder_to_error_success(self):
        """Test successful move of completely empty folder to error folder."""
        empty_folder = self.source_folder / "subfolder" / "empty"
        empty_folder.mkdir(parents=True)
        
        result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        
        assert result is True
        assert not empty_folder.exists()
        
        # Verify folder moved to error folder with structure preservation
        moved_folder = self.error_folder / "subfolder" / "empty"
        assert moved_folder.exists()
        assert moved_folder.is_dir()
    
    def test_move_empty_folder_to_error_not_empty(self):
        """Test move attempt on folder that is not completely empty."""
        folder_with_file = self.source_folder / "not_empty"
        folder_with_file.mkdir()
        (folder_with_file / "file.txt").write_text("content")
        
        result = self.file_manager.move_empty_folder_to_error(str(folder_with_file))
        
        assert result is False
        assert folder_with_file.exists()  # Should not be moved
    
    def test_move_empty_folder_to_error_with_empty_subfolder(self):
        """Test move attempt on folder with empty subfolders (should fail)."""
        folder_with_empty_sub = self.source_folder / "with_empty_sub"
        folder_with_empty_sub.mkdir()
        (folder_with_empty_sub / "empty_sub").mkdir()
        
        result = self.file_manager.move_empty_folder_to_error(str(folder_with_empty_sub))
        
        assert result is False
        assert folder_with_empty_sub.exists()  # Should not be moved
    
    def test_move_empty_folder_to_error_destination_conflict(self):
        """Test move with destination conflict resolution."""
        empty_folder = self.source_folder / "conflict_test"
        empty_folder.mkdir()
        
        # Create conflicting folder in error directory
        existing_folder = self.error_folder / "conflict_test"
        existing_folder.mkdir()
        
        result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
        
        assert result is True
        assert not empty_folder.exists()
        
        # Should create conflict_test_001 folder
        moved_folder = self.error_folder / "conflict_test_001"
        assert moved_folder.exists()
        assert moved_folder.is_dir()
    
    def test_move_empty_folder_to_error_move_failure(self):
        """Test move failure handling."""
        empty_folder = self.source_folder / "move_fail_test"
        empty_folder.mkdir()
        
        # Mock shutil.move to fail
        with patch('shutil.move', side_effect=OSError("Move failed")):
            result = self.file_manager.move_empty_folder_to_error(str(empty_folder))
            
            assert result is False
            assert empty_folder.exists()  # Should still exist after failed move