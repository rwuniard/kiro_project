"""
RTF Processing Module for RAG System

This module provides functionality to extract text from RTF (Rich Text Format) documents
and convert them into LangChain Document objects for embedding storage.
"""

import time

from pathlib import Path

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_community.document_loaders import UnstructuredRTFLoader
except ImportError:
    UnstructuredRTFLoader = None

try:
    from .document_processor import DocumentProcessor
    from .logging_config import (
        get_logger,
        log_document_processing_complete,
        log_document_processing_start,
        log_processing_error,
    )
except ImportError:
    from document_processor import DocumentProcessor
    from logging_config import (
        get_logger,
        log_document_processing_complete,
        log_document_processing_start,
        log_processing_error,
    )

logger = get_logger("rtf_processor")


class RTFProcessor(DocumentProcessor):
    """Process RTF (Rich Text Format) documents and extract content for RAG storage."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = {".rtf"}
        # RTF documents are typically simpler than Word docs but may contain formatting
        # Use parameters similar to text processor but with slightly larger chunks
        self.default_chunk_size = 800  # Medium chunks for RTF content
        self.default_chunk_overlap = 120  # 15% overlap ratio
        
        # Check if UnstructuredRTFLoader is available
        if UnstructuredRTFLoader is None:
            logger.error(
                "UnstructuredRTFLoader not found. Please install langchain-community with RTF support."
            )
            raise ImportError(
                "langchain_community with RTF support is required for RTF processing. "
                "Ensure unstructured library version >= 0.5.12 is installed."
            )

    @property
    def file_type_description(self) -> str:
        """Return a human-readable description of supported file types."""
        return "Rich Text Format documents (.rtf)"

    def is_supported_file(self, file_path: Path) -> bool:
        """Check if the file is a supported RTF document."""
        extension = file_path.suffix.lower()
        
        # Normal RTF files are always supported
        if extension in self.supported_extensions:
            return True
            
        # .doc files are supported if we're explicitly handling RTF content in .doc files
        if extension == '.doc' and getattr(self, '_handling_doc_with_rtf_content', False):
            return True
            
        return False

    def process_document(
        self,
        file_path: Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        **kwargs,
    ) -> list[Document]:
        """
        Process an RTF document and return LangChain Document objects.

        Args:
            file_path: Path to the RTF document
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Number of characters to overlap between chunks
            **kwargs: Additional processing parameters

        Returns:
            List of LangChain Document objects with content and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file type is not supported
            Exception: For other processing errors
        """
        self.validate_file(file_path)
        try:
            return self._process_rtf_internal(file_path, chunk_size, chunk_overlap)
        finally:
            # Clear the flag after processing
            if hasattr(self, '_handling_doc_with_rtf_content'):
                delattr(self, '_handling_doc_with_rtf_content')

    def _process_rtf_internal(
        self,
        file_path: Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[Document]:
        """Internal RTF document processing method."""
        start_time = time.time()
        chunk_size, chunk_overlap = self.get_processing_params(
            chunk_size, chunk_overlap
        )

        # Log processing start
        file_size = file_path.stat().st_size if file_path.exists() else 0
        context = log_document_processing_start(
            processor_name=self.processor_name,
            file_path=str(file_path),
            file_size=file_size,
            file_type=file_path.suffix,
        )

        try:
            # Use UnstructuredRTFLoader for RTF file processing
            # Use "elements" mode for better structured content extraction
            loader = UnstructuredRTFLoader(
                str(file_path),
                mode="elements",  # Extract structured elements like titles, paragraphs
                strategy="fast",   # Use fast strategy for better performance
            )

            # Load the RTF document
            raw_documents = loader.load()
            
            # Clean metadata to remove complex types that ChromaDB can't handle
            for doc in raw_documents:
                # Filter out any non-simple metadata values (lists, dicts, etc.)
                clean_metadata = {}
                for key, value in doc.metadata.items():
                    # Keep only simple types that ChromaDB supports
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        clean_metadata[key] = value
                    # Convert simple lists to strings if needed
                    elif isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
                        clean_metadata[key] = value[0]  # Extract single string from list
                    # Skip complex types
                doc.metadata = clean_metadata

            if not raw_documents:
                log_document_processing_complete(
                    context=context,
                    chunks_created=0,
                    processing_time_seconds=time.time() - start_time,
                    status="success_empty",
                )
                return []

            # Use RecursiveCharacterTextSplitter for better text boundary handling
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=[
                    "\n\n",  # Split on paragraphs first
                    "\n",    # Then lines
                    ". ",    # Then sentences
                    " ",     # Then words
                    "",      # Finally characters
                ],
            )

            # Split the loaded documents
            documents = text_splitter.split_documents(raw_documents)

            if not documents:
                log_document_processing_complete(
                    context=context,
                    chunks_created=0,
                    processing_time_seconds=time.time() - start_time,
                    status="success_empty",
                )
                return []

            # Enhance metadata with processing information
            base_metadata = self.get_metadata_template(file_path)
            for i, doc in enumerate(documents):
                # Preserve original metadata and add our enhancements
                doc.metadata.update(base_metadata)
                doc.metadata.update({
                    "chunk_id": f"chunk_{i}",
                    "document_id": f"{file_path.stem}_rtf",
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "splitting_method": "RecursiveCharacterTextSplitter",
                    "separators": "paragraphs,lines,sentences,words,chars",
                    "total_chunks": len(documents),
                    "document_format": "RTF",
                    "loader_type": "UnstructuredRTFLoader",
                    "supports_rich_formatting": True,
                    "extraction_mode": "elements",
                    "extraction_strategy": "fast",
                })

            # Log successful completion
            processing_time = time.time() - start_time
            log_document_processing_complete(
                context=context,
                chunks_created=len(documents),
                processing_time_seconds=processing_time,
                status="success",
            )

            return documents

        except Exception as e:
            # Log processing error with specific context
            log_processing_error(
                context=context, error=e, error_type="rtf_processing_error"
            )

            # Provide helpful error information
            error_msg = f"Error processing RTF document {file_path}: {e!s}"
            if "unstructured" in str(e).lower():
                error_msg += "\nNote: UnstructuredRTFLoader requires proper system dependencies. Ensure unstructured library version >= 0.5.12 is installed."
            elif "permission" in str(e).lower():
                error_msg += "\nNote: Permission denied accessing the RTF file."
            elif "rtf" in str(e).lower() and "not supported" in str(e).lower():
                error_msg += "\nNote: The RTF file may use unsupported features or be corrupted."

            raise Exception(error_msg)

    def detect_rtf_content(self, file_path: Path) -> bool:
        """
        Detect if a file contains RTF content by examining its header.
        
        This is useful for files with incorrect extensions (e.g., .doc files that are actually RTF).
        
        Args:
            file_path: Path to the file to examine
            
        Returns:
            True if file appears to contain RTF content, False otherwise
        """
        try:
            with open(file_path, 'rb') as file:
                # Read first 1024 bytes to check for RTF signature
                header = file.read(1024)
                
                # Convert to string, ignoring encoding errors
                header_str = header.decode('utf-8', errors='ignore')
                
                # RTF files start with {\rtf followed by version number
                if header_str.strip().startswith('{\\rtf'):
                    return True
                    
                # Also check for common RTF patterns in the header
                rtf_patterns = [
                    '{\\rtf1',  # RTF version 1
                    '{\\*\\generator',  # RTF generator info
                    '\\ansi',   # ANSI character set
                    '\\deff',   # Default font
                ]
                
                return any(pattern in header_str for pattern in rtf_patterns)
                
        except Exception as e:
            logger.warning(f"Error detecting RTF content in {file_path}: {e}")
            return False