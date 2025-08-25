"""
File Manager module for handling file operations with folder structure preservation.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Optional, List
import logging


class FileManager:
    """
    Handles file operations (move, copy) with folder structure preservation.
    
    This class manages moving files between source, saved, and error folders
    while maintaining the original directory structure relative to the source folder.
    """
    
    def __init__(self, source_folder: str, saved_folder: str, error_folder: str):
        """
        Initialize FileManager with folder paths.
        
        Args:
            source_folder: Path to the source folder being monitored
            saved_folder: Path to folder for successfully processed files
            error_folder: Path to folder for files that failed processing
        """
        self.source_folder = Path(source_folder).resolve()
        self.saved_folder = Path(saved_folder).resolve()
        self.error_folder = Path(error_folder).resolve()
        self.logger = logging.getLogger(__name__)
        
    def move_to_saved(self, file_path: str) -> bool:
        """
        Move a successfully processed file to the saved folder with resilience.
        
        Preserves the original folder structure relative to the source folder.
        Includes validation and error recovery mechanisms.
        
        Args:
            file_path: Absolute path to the file to move
            
        Returns:
            bool: True if move was successful, False otherwise
        """
        return self._move_file_with_resilience(file_path, self.saved_folder, "saved")
    
    def move_to_error(self, file_path: str) -> bool:
        """
        Move a failed file to the error folder with resilience.
        
        Preserves the original folder structure relative to the source folder.
        Includes validation and error recovery mechanisms.
        
        Args:
            file_path: Absolute path to the file to move
            
        Returns:
            bool: True if move was successful, False otherwise
        """
        return self._move_file_with_resilience(file_path, self.error_folder, "error")
    
    def _preserve_folder_structure(self, source_path: Path, dest_base: Path) -> Path:
        """
        Calculate destination path while preserving folder structure.
        
        Args:
            source_path: Original file path
            dest_base: Base destination folder (saved or error)
            
        Returns:
            Path: Complete destination path with preserved structure
        """
        try:
            # Resolve both paths to handle symlinks and relative paths consistently
            resolved_source = source_path.resolve()
            resolved_source_folder = self.source_folder.resolve()
            
            # Get relative path from source folder to the file
            relative_path = resolved_source.relative_to(resolved_source_folder)
            
            # Combine with destination base to preserve structure
            dest_path = dest_base / relative_path
            
            return dest_path
            
        except ValueError as e:
            # File is not under source folder - use just the filename
            self.logger.warning(f"File {source_path} is not under source folder {self.source_folder}, using filename only")
            return dest_base / source_path.name
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """
        Create directory and any necessary parent directories.
        
        Args:
            directory: Path to directory that should exist
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to create directory {directory}: {e}")
            raise
    
    def get_relative_path(self, file_path: str) -> Optional[str]:
        """
        Get the relative path of a file from the source folder.
        
        Args:
            file_path: Absolute path to the file
            
        Returns:
            str: Relative path from source folder, or None if not under source
        """
        try:
            source_path = Path(file_path).resolve()
            relative_path = source_path.relative_to(self.source_folder)
            return str(relative_path)
        except ValueError:
            return None
    
    def _move_file_with_resilience(self, file_path: str, dest_base: Path, 
                                  operation_type: str) -> bool:
        """
        Move a file with comprehensive error handling and resilience.
        
        Args:
            file_path: Source file path
            dest_base: Destination base folder
            operation_type: Type of operation for logging ("saved" or "error")
            
        Returns:
            bool: True if successful, False otherwise
        """
        max_attempts = 3
        base_delay = 0.5
        
        for attempt in range(max_attempts):
            try:
                source_path = Path(file_path).resolve()
                
                # Validate source file still exists
                if not source_path.exists():
                    self.logger.error(f"Source file no longer exists: {file_path}")
                    return False
                
                if not source_path.is_file():
                    self.logger.error(f"Source path is not a file: {file_path}")
                    return False
                
                # Calculate destination path
                dest_path = self._preserve_folder_structure(source_path, dest_base)
                
                # Handle destination file conflicts
                dest_path = self._resolve_destination_conflict(dest_path)
                
                # Ensure destination directory exists
                self._ensure_directory_exists(dest_path.parent)
                
                # Validate destination is writable
                self._validate_destination_writable(dest_path.parent)
                
                # Perform atomic move operation
                self._atomic_move(source_path, dest_path)
                
                # Verify move was successful
                if dest_path.exists() and not source_path.exists():
                    self.logger.info(f"Successfully moved file to {operation_type} folder: {dest_path}")
                    return True
                else:
                    raise RuntimeError("Move operation completed but verification failed")
                
            except Exception as e:
                if attempt == max_attempts - 1:
                    self.logger.error(f"Failed to move file {file_path} to {operation_type} folder after {max_attempts} attempts: {e}")
                    return False
                else:
                    self.logger.warning(f"Move attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(base_delay * (2 ** attempt))  # Exponential backoff
        
        return False
    
    def _resolve_destination_conflict(self, dest_path: Path) -> Path:
        """
        Resolve destination file conflicts by adding a suffix if needed.
        
        Args:
            dest_path: Original destination path
            
        Returns:
            Path: Resolved destination path that doesn't conflict
        """
        if not dest_path.exists():
            return dest_path
        
        # File already exists, create a unique name
        counter = 1
        stem = dest_path.stem
        suffix = dest_path.suffix
        parent = dest_path.parent
        
        while True:
            new_name = f"{stem}_{counter:03d}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                self.logger.info(f"Resolved file conflict: {dest_path} -> {new_path}")
                return new_path
            counter += 1
            
            # Prevent infinite loop
            if counter > 999:
                raise RuntimeError(f"Cannot resolve file conflict for {dest_path}")
    
    def _validate_destination_writable(self, dest_dir: Path) -> None:
        """
        Validate that the destination directory is writable.
        
        Args:
            dest_dir: Destination directory to validate
            
        Raises:
            PermissionError: If directory is not writable
        """
        if not os.access(dest_dir, os.W_OK):
            raise PermissionError(f"Destination directory is not writable: {dest_dir}")
    
    def _atomic_move(self, source_path: Path, dest_path: Path) -> None:
        """
        Perform an atomic move operation with fallback strategies.
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            
        Raises:
            Various exceptions if all move strategies fail
        """
        try:
            # Try atomic move first (same filesystem)
            shutil.move(str(source_path), str(dest_path))
        except OSError as e:
            # If atomic move fails, try copy + delete
            self.logger.warning(f"Atomic move failed, trying copy+delete: {e}")
            try:
                shutil.copy2(str(source_path), str(dest_path))
                source_path.unlink()  # Delete original after successful copy
            except Exception as copy_error:
                # Clean up partial copy if it exists
                if dest_path.exists():
                    try:
                        dest_path.unlink()
                    except Exception:
                        pass
                raise copy_error from e