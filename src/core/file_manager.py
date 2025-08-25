"""
File Manager module for handling file operations with folder structure preservation.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
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
        Move a successfully processed file to the saved folder.
        
        Preserves the original folder structure relative to the source folder.
        
        Args:
            file_path: Absolute path to the file to move
            
        Returns:
            bool: True if move was successful, False otherwise
        """
        try:
            source_path = Path(file_path).resolve()
            dest_path = self._preserve_folder_structure(source_path, self.saved_folder)
            
            # Ensure destination directory exists
            self._ensure_directory_exists(dest_path.parent)
            
            # Move the file
            shutil.move(str(source_path), str(dest_path))
            
            self.logger.info(f"Successfully moved file to saved folder: {dest_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move file {file_path} to saved folder: {e}")
            return False
    
    def move_to_error(self, file_path: str) -> bool:
        """
        Move a failed file to the error folder.
        
        Preserves the original folder structure relative to the source folder.
        
        Args:
            file_path: Absolute path to the file to move
            
        Returns:
            bool: True if move was successful, False otherwise
        """
        try:
            source_path = Path(file_path).resolve()
            dest_path = self._preserve_folder_structure(source_path, self.error_folder)
            
            # Ensure destination directory exists
            self._ensure_directory_exists(dest_path.parent)
            
            # Move the file
            shutil.move(str(source_path), str(dest_path))
            
            self.logger.info(f"Successfully moved file to error folder: {dest_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move file {file_path} to error folder: {e}")
            return False
    
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