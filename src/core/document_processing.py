"""
Document Processing module for handling pluggable document processing systems.

This module contains the abstract interface for document processing systems
and related data classes for standardized processing results and error handling.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProcessingResult:
    """
    Standardized result object for document processing operations.
    
    This class provides a consistent interface for returning processing results
    from any document processing system implementation.
    """
    success: bool
    file_path: str
    processor_used: Optional[str] = None
    chunks_created: int = 0
    processing_time: float = 0.0
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize metadata as empty dict if None."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DocumentProcessingError:
    """
    Enhanced error information for document processing failures.
    
    This class provides detailed error context for document processing
    failures to enable better debugging and error handling.
    """
    file_path: str
    processor_type: str
    error_message: str
    error_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: Optional[str] = None
    file_metadata: Dict[str, Any] = field(default_factory=dict)
    processing_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize dictionaries as empty if None."""
        if self.file_metadata is None:
            self.file_metadata = {}
        if self.processing_context is None:
            self.processing_context = {}


class DocumentProcessingInterface(ABC):
    """
    Abstract interface for pluggable document processing systems.
    
    This interface defines the contract that all document processing
    implementations must follow, enabling modular and extensible
    document processing capabilities.
    """
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the document processing system.
        
        Args:
            config: Configuration dictionary containing system-specific settings
            
        Returns:
            bool: True if initialization successful, False otherwise
            
        Raises:
            Exception: If initialization fails with unrecoverable error
        """
        pass
    
    @abstractmethod
    def is_supported_file(self, file_path: Path) -> bool:
        """
        Check if the given file type is supported by this processor.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file type is supported, False otherwise
        """
        pass
    
    @abstractmethod
    def process_document(self, file_path: Path) -> ProcessingResult:
        """
        Process a document and return standardized result.
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            ProcessingResult: Standardized processing result
            
        Raises:
            DocumentProcessingError: If processing fails
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> Set[str]:
        """
        Get the set of file extensions supported by this processor.
        
        Returns:
            Set[str]: Set of supported file extensions (including the dot, e.g., '.pdf')
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Cleanup resources used by the document processing system.
        
        This method should be called when the processor is no longer needed
        to ensure proper resource cleanup and prevent memory leaks.
        """
        pass
    
    def get_processor_name(self) -> str:
        """
        Get the name of this processor implementation.
        
        Returns:
            str: Name of the processor (defaults to class name)
        """
        return self.__class__.__name__
    
    def validate_file_path(self, file_path: Path) -> None:
        """
        Validate that a file path exists and is accessible.
        
        Args:
            file_path: Path to validate
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is not a file
            PermissionError: If file is not accessible
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Test read access
        try:
            with open(file_path, 'rb') as f:
                # Just test that we can open the file
                pass
        except PermissionError as e:
            raise PermissionError(f"Cannot access file: {e}")