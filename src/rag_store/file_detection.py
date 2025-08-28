"""
File Content Detection Utilities

This module provides utilities to detect the actual file type based on content
rather than just file extension, which is useful for handling files with
incorrect or misleading extensions.
"""

from pathlib import Path
from typing import Literal

try:
    from .logging_config import get_logger
except ImportError:
    from logging_config import get_logger

logger = get_logger("file_detection")


class FileContentDetector:
    """Detect actual file types based on content analysis."""
    
    @staticmethod
    def detect_doc_file_type(file_path: Path) -> Literal["doc", "rtf", "unknown"]:
        """
        Detect whether a .doc file is actually a DOC format or RTF format.
        
        Some RTF files are saved with .doc extension, which can cause processing
        issues if sent to the wrong processor.
        
        Args:
            file_path: Path to the .doc file to analyze
            
        Returns:
            "doc" if it's a genuine MS Word DOC file
            "rtf" if it's an RTF file with .doc extension
            "unknown" if the format cannot be determined
        """
        try:
            with open(file_path, 'rb') as file:
                # Read first 2KB to analyze file signature and content
                header = file.read(2048)
                
                # Convert to string for text-based analysis, ignoring encoding errors
                header_str = header.decode('utf-8', errors='ignore')
                
                # Check for RTF signature first (most definitive)
                if FileContentDetector._is_rtf_content(header, header_str):
                    logger.info(f"File {file_path} detected as RTF format despite .doc extension")
                    return "rtf"
                
                # Check for DOC format signatures
                if FileContentDetector._is_doc_content(header, header_str):
                    logger.debug(f"File {file_path} confirmed as DOC format")
                    return "doc"
                
                # If we can't determine, default to unknown
                logger.warning(f"Cannot determine format of {file_path} - treating as unknown")
                return "unknown"
                
        except Exception as e:
            logger.error(f"Error detecting file type for {file_path}: {e}")
            return "unknown"
    
    @staticmethod
    def _is_rtf_content(header_bytes: bytes, header_str: str) -> bool:
        """
        Check if content appears to be RTF format.
        
        Args:
            header_bytes: Raw bytes from file header
            header_str: Header converted to string
            
        Returns:
            True if content appears to be RTF
        """
        # RTF files start with {\rtf followed by version number
        if header_str.strip().startswith('{\\rtf'):
            return True
            
        # Check for RTF control words in the beginning of the file
        rtf_patterns = [
            '{\\rtf1',      # RTF version 1 (most common)
            '{\\*\\generator',  # RTF generator information
            '\\ansi',       # ANSI character set declaration
            '\\deff',       # Default font declaration
            '\\fonttbl',    # Font table
            '\\colortbl',   # Color table
        ]
        
        # RTF files should have at least 2-3 of these patterns in the header
        pattern_count = sum(1 for pattern in rtf_patterns if pattern in header_str)
        if pattern_count >= 2:
            return True
            
        return False
    
    @staticmethod
    def _is_doc_content(header_bytes: bytes, header_str: str) -> bool:
        """
        Check if content appears to be MS Word DOC format.
        
        Args:
            header_bytes: Raw bytes from file header
            header_str: Header converted to string
            
        Returns:
            True if content appears to be DOC format
        """
        # Check for MS Word DOC file signatures
        # DOC files are OLE2/Compound Document files
        
        # OLE2 signature: D0CF11E0A1B11AE1 (first 8 bytes)
        ole2_signature = b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
        if header_bytes.startswith(ole2_signature):
            return True
        
        # Check for Word-specific OLE streams
        word_indicators = [
            b'Microsoft Office Word',
            b'Word.Document',
            b'WordDocument',
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Microsoft Office Word',  # With padding
        ]
        
        for indicator in word_indicators:
            if indicator in header_bytes:
                return True
        
        # Check for DOC-specific text patterns (less reliable)
        doc_text_patterns = [
            'Microsoft Office Word',
            'Word.Document',
            'Normal.dot',
        ]
        
        for pattern in doc_text_patterns:
            if pattern in header_str:
                return True
                
        return False
    
    @staticmethod
    def should_use_rtf_processor(file_path: Path) -> bool:
        """
        Determine if a file should be processed by the RTF processor.
        
        This checks both the file extension and content to handle cases where
        RTF files have incorrect extensions.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file should be processed as RTF
        """
        # If it's already an .rtf file, use RTF processor
        if file_path.suffix.lower() == '.rtf':
            return True
            
        # If it's a .doc file, check if it's actually RTF content
        if file_path.suffix.lower() == '.doc':
            detection_result = FileContentDetector.detect_doc_file_type(file_path)
            return detection_result == "rtf"
            
        return False
    
    @staticmethod
    def should_use_word_processor(file_path: Path) -> bool:
        """
        Determine if a file should be processed by the Word processor.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file should be processed as Word document
        """
        file_ext = file_path.suffix.lower()
        
        # .docx files always go to Word processor
        if file_ext == '.docx':
            return True
            
        # For .doc files, check if they're actually DOC format (not RTF)
        if file_ext == '.doc':
            detection_result = FileContentDetector.detect_doc_file_type(file_path)
            return detection_result in ("doc", "unknown")  # Default to Word processor if uncertain
            
        return False