"""
Office Document Processing Module for RAG System

This module provides unified functionality to extract text from various office document formats
and convert them into LangChain Document objects for embedding storage.
Supports Microsoft Office, OpenDocument, and related formats.
"""

import time

from pathlib import Path

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_unstructured import UnstructuredLoader

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

logger = get_logger("office_processor")


class OfficeProcessor(DocumentProcessor):
    """Process various office document formats and extract content for RAG storage."""

    def __init__(self):
        super().__init__()
        # Comprehensive set of supported office document formats
        self.supported_extensions = {
            # Microsoft Word
            ".doc", ".docx",
            # Microsoft PowerPoint  
            ".ppt", ".pptx",
            # Microsoft Excel
            ".xls", ".xlsx",
            # OpenDocument formats
            ".odt", ".odp", ".ods",
            # Rich Text Format
            ".rtf",
            # eBooks
            ".epub"
        }
        
        # Format-specific chunking strategies optimized for different document types
        self.format_chunk_configs = {
            # Word documents: balanced chunking for structured text
            ".doc": {"chunk_size": 1000, "chunk_overlap": 150},
            ".docx": {"chunk_size": 1000, "chunk_overlap": 150},
            # PowerPoint: smaller chunks for slide-based content
            ".ppt": {"chunk_size": 800, "chunk_overlap": 120},
            ".pptx": {"chunk_size": 800, "chunk_overlap": 120},
            # Excel: larger chunks for tabular data
            ".xls": {"chunk_size": 1200, "chunk_overlap": 180},
            ".xlsx": {"chunk_size": 1200, "chunk_overlap": 180},
            # OpenDocument: similar to Microsoft Office equivalents
            ".odt": {"chunk_size": 1000, "chunk_overlap": 150},  # Like Word
            ".odp": {"chunk_size": 800, "chunk_overlap": 120},   # Like PowerPoint
            ".ods": {"chunk_size": 1200, "chunk_overlap": 180},  # Like Excel
            # RTF: medium chunks for formatted text
            ".rtf": {"chunk_size": 800, "chunk_overlap": 120},
            # eBooks: medium chunks for continuous text
            ".epub": {"chunk_size": 1000, "chunk_overlap": 150}
        }
        
        # Default fallback values
        self.default_chunk_size = 1000
        self.default_chunk_overlap = 150

    @property
    def file_type_description(self) -> str:
        """Return a human-readable description of supported file types."""
        return ("Office documents (Word, PowerPoint, Excel), "
                "OpenDocument formats, RTF, and eBooks "
                "(.doc, .docx, .ppt, .pptx, .xls, .xlsx, .odt, .odp, .ods, "
                ".rtf, .epub)")

    def is_supported_file(self, file_path: Path) -> bool:
        """Check if the file is a supported office document format."""
        extension = file_path.suffix.lower()
        
        # Normal supported formats
        if extension in self.supported_extensions:
            return True
            
        # Special handling for .doc files that might contain RTF content
        if extension == '.doc' and getattr(self, '_handling_doc_with_rtf_content', False):
            return True
            
        return False

    def get_processing_params(
        self, 
        chunk_size: int | None = None, 
        chunk_overlap: int | None = None,
        file_path: Path | None = None
    ) -> tuple[int, int]:
        """
        Get processing parameters with format-specific optimization.
        
        Args:
            chunk_size: Requested chunk size (overrides format-specific defaults)
            chunk_overlap: Requested chunk overlap (overrides format-specific defaults)
            file_path: Path to file for format-specific optimization
            
        Returns:
            Tuple of (chunk_size, chunk_overlap)
        """
        # If explicit parameters provided, use them
        if chunk_size is not None and chunk_overlap is not None:
            return chunk_size, chunk_overlap
            
        # Try to use format-specific configuration
        if file_path:
            extension = file_path.suffix.lower()
            if extension in self.format_chunk_configs:
                config = self.format_chunk_configs[extension]
                final_chunk_size = chunk_size if chunk_size is not None else config["chunk_size"]
                final_chunk_overlap = chunk_overlap if chunk_overlap is not None else config["chunk_overlap"]
                return final_chunk_size, final_chunk_overlap
        
        # Fallback to defaults
        final_chunk_size = chunk_size if chunk_size is not None else self.default_chunk_size
        final_chunk_overlap = chunk_overlap if chunk_overlap is not None else self.default_chunk_overlap
        
        return final_chunk_size, final_chunk_overlap

    def process_document(
        self,
        file_path: Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        **kwargs,
    ) -> list[Document]:
        """
        Process an office document and return LangChain Document objects.

        Args:
            file_path: Path to the office document
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
            return self._process_office_internal(file_path, chunk_size, chunk_overlap)
        finally:
            # Clear the flag after processing
            if hasattr(self, '_handling_doc_with_rtf_content'):
                delattr(self, '_handling_doc_with_rtf_content')

    def _process_office_internal(
        self,
        file_path: Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> list[Document]:
        """Internal office document processing method."""
        start_time = time.time()
        
        # Get format-specific processing parameters
        chunk_size, chunk_overlap = self.get_processing_params(
            chunk_size, chunk_overlap, file_path
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
            # Use UnstructuredLoader with all-docs support for unified processing
            # Container environment already has TMPDIR=/tmp/unstructured configured
            loader = UnstructuredLoader(
                file_path=str(file_path),
                mode="elements",  # Extract structured elements for better content organization
                strategy="fast",   # Use fast strategy for better performance
            )

            # Load the document
            raw_documents = loader.load()
            
            # Clean metadata to remove complex types that ChromaDB can't handle
            for doc in raw_documents:
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

            # Use RecursiveCharacterTextSplitter optimized for office documents
            separators = self._get_separators_for_format(file_path)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=separators,
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
            document_format = self._get_document_format_description(file_path)
            
            for i, doc in enumerate(documents):
                # Preserve original metadata and add our enhancements
                doc.metadata.update(base_metadata)
                doc.metadata.update({
                    "chunk_id": f"chunk_{i}",
                    "document_id": f"{file_path.stem}_office",
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "splitting_method": "RecursiveCharacterTextSplitter",
                    "separators": ",".join(separators[:4]),  # Store first few separators
                    "total_chunks": len(documents),
                    "document_format": document_format,
                    "loader_type": "UnstructuredLoader",
                    "processor_version": "unified_office_processor",
                    "supports_all_office_formats": True,
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
                context=context, error=e, error_type="office_processing_error"
            )

            # Provide helpful error information
            error_msg = f"Error processing office document {file_path}: {e!s}"
            extension = file_path.suffix.lower()
            
            if "unstructured" in str(e).lower():
                error_msg += f"\nNote: UnstructuredLoader with all-docs support may require additional system dependencies for {extension} files."
            elif "permission" in str(e).lower():
                error_msg += f"\nNote: Permission denied accessing the {extension} file."
            elif any(fmt in str(e).lower() for fmt in ["word", "excel", "powerpoint", "office"]):
                error_msg += f"\nNote: The {extension} file may be corrupted or use unsupported features."

            raise Exception(error_msg)

    def _get_separators_for_format(self, file_path: Path) -> list[str]:
        """Get optimal text separators based on document format."""
        extension = file_path.suffix.lower()
        
        # Format-specific separators
        if extension in [".ppt", ".pptx", ".odp"]:
            # PowerPoint: slide breaks are important
            return ["\n\n\n", "\n\n", "\n", ". ", " ", ""]
        elif extension in [".xls", ".xlsx", ".ods"]:
            # Excel: table structure is important
            return ["\n\n", "\n", "\t", ". ", " ", ""]
        elif extension == ".epub":
            # eBooks: chapter and paragraph breaks
            return ["\n\n\n", "\n\n", "\n", ". ", " ", ""]
        else:
            # Default for Word, RTF, and other text-heavy formats
            return ["\n\n", "\n", ". ", " ", ""]

    def _get_document_format_description(self, file_path: Path) -> str:
        """Get human-readable document format description."""
        extension = file_path.suffix.lower()
        
        format_descriptions = {
            ".doc": "Microsoft Word (Legacy)",
            ".docx": "Microsoft Word",
            ".ppt": "Microsoft PowerPoint (Legacy)",
            ".pptx": "Microsoft PowerPoint",
            ".xls": "Microsoft Excel (Legacy)",
            ".xlsx": "Microsoft Excel",
            ".odt": "OpenDocument Text",
            ".odp": "OpenDocument Presentation", 
            ".ods": "OpenDocument Spreadsheet",
            ".rtf": "Rich Text Format",
            ".epub": "Electronic Publication"
        }
        
        return format_descriptions.get(extension, extension.upper().replace(".", ""))

    def detect_rtf_content(self, file_path: Path) -> bool:
        """
        Detect if a file contains RTF content by examining its header.
        
        Useful for files with incorrect extensions (e.g., .doc files that are actually RTF).
        
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

    # Legacy method compatibility
    def load_docx_documents(self, file_path: Path) -> list[Document]:
        """
        Load documents from Word files using the legacy interface.
        Maintained for backward compatibility.

        Args:
            file_path: Path to the Word document

        Returns:
            List of LangChain Document objects
        """
        return self.process_document(file_path)

    def process_mht_file(self, file_path: Path) -> list[Document]:
        """
        Process MHT file using the legacy interface.
        Maintained for backward compatibility.

        Args:
            file_path: Path to the MHT file

        Returns:
            List of LangChain Document objects
        """
        return self.process_document(file_path)