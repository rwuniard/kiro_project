"""
MHT/MHTML Document Processing Module for RAG System

This module provides functionality to extract text from MHT/MHTML web archive files
and convert them into LangChain Document objects for embedding storage.
MHT files use MIME multipart format and require special handling.
"""

import email
import time
from pathlib import Path
from typing import List, Dict, Any

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from bs4 import BeautifulSoup
import quopri
import base64

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

logger = get_logger("mht_processor")


class MHTProcessor(DocumentProcessor):
    """Process MHT/MHTML web archive files and extract content for RAG storage."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = {".mht", ".mhtml"}
        self.default_chunk_size = 1200
        self.default_chunk_overlap = 180

    @property
    def file_type_description(self) -> str:
        """Return a human-readable description of supported file types."""
        return "Web Archive files (MHT/MHTML) - .mht, .mhtml"

    def is_supported_file(self, file_path: Path) -> bool:
        """Check if the file is a supported MHT/MHTML format."""
        return file_path.suffix.lower() in self.supported_extensions

    def process_document(
        self,
        file_path: Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        **kwargs,
    ) -> List[Document]:
        """
        Process an MHT/MHTML document and return LangChain Document objects.

        Args:
            file_path: Path to the MHT/MHTML file
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
        return self._process_mht_internal(file_path, chunk_size, chunk_overlap)

    def _process_mht_internal(
        self,
        file_path: Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> List[Document]:
        """Internal MHT document processing method."""
        start_time = time.time()
        
        # Get processing parameters
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
            # Extract text content from MHT file
            text_content = self._extract_text_from_mht(file_path)

            if not text_content.strip():
                log_document_processing_complete(
                    context=context,
                    chunks_created=0,
                    processing_time_seconds=time.time() - start_time,
                    status="success_empty",
                )
                return []

            # Create a single document with the extracted text
            temp_doc = Document(
                page_content=text_content,
                metadata=self.get_metadata_template(file_path)
            )

            # Split the document into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],  # Web content separators
            )

            documents = text_splitter.split_documents([temp_doc])

            if not documents:
                log_document_processing_complete(
                    context=context,
                    chunks_created=0,
                    processing_time_seconds=time.time() - start_time,
                    status="success_empty",
                )
                return []

            # Enhance metadata for each chunk
            base_metadata = self.get_metadata_template(file_path)
            
            for i, doc in enumerate(documents):
                doc.metadata.update(base_metadata)
                doc.metadata.update({
                    "chunk_id": f"chunk_{i}",
                    "document_id": f"{file_path.stem}_mht",
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "splitting_method": "RecursiveCharacterTextSplitter",
                    "total_chunks": len(documents),
                    "document_format": "Web Archive (MHT/MHTML)",
                    "processor_version": "mht_processor_v1.0",
                    "original_encoding": "MIME multipart",
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
            # Log processing error
            log_processing_error(
                context=context, error=e, error_type="mht_processing_error"
            )

            error_msg = f"Error processing MHT file {file_path}: {e!s}"
            if "encoding" in str(e).lower():
                error_msg += "\nNote: The MHT file may have encoding issues or use unsupported character sets."
            elif "parse" in str(e).lower():
                error_msg += "\nNote: The MHT file may have malformed MIME structure."

            raise Exception(error_msg)

    def _extract_text_from_mht(self, file_path: Path) -> str:
        """
        Extract text content from MHT file using email parser and BeautifulSoup.
        
        Args:
            file_path: Path to the MHT file
            
        Returns:
            Extracted text content
        """
        try:
            # Read the MHT file
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            # Try different encodings
            content = None
            for encoding in ['utf-8', 'cp1252', 'iso-8859-1', 'ascii']:
                try:
                    content = raw_data.decode(encoding, errors='ignore')
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError("Could not decode MHT file with any supported encoding")

            # Parse as email message (MHT files use MIME format)
            msg = email.message_from_string(content)
            
            # Extract HTML content from multipart message
            html_content = self._extract_html_from_message(msg)
            
            if not html_content:
                # Fallback: try to extract any text content
                return self._extract_text_fallback(content)
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            
            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up extra whitespace
            text = ' '.join(text.split())
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from MHT file {file_path}: {e}")
            # Try fallback method
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return self._extract_text_fallback(content)
            except Exception as fallback_error:
                raise Exception(f"Failed to extract text: {e}. Fallback also failed: {fallback_error}")

    def _extract_html_from_message(self, msg: email.message.Message) -> str:
        """
        Extract HTML content from email message parts.
        
        Args:
            msg: Email message object
            
        Returns:
            HTML content string
        """
        html_content = ""
        
        if msg.is_multipart():
            # Process each part of the multipart message
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        # Handle different encodings
                        encoding = part.get_content_charset() or 'utf-8'
                        try:
                            html_content += payload.decode(encoding, errors='ignore')
                        except (UnicodeDecodeError, LookupError):
                            html_content += payload.decode('utf-8', errors='ignore')
        else:
            # Single part message
            if msg.get_content_type() == 'text/html':
                payload = msg.get_payload(decode=True)
                if payload:
                    encoding = msg.get_content_charset() or 'utf-8'
                    try:
                        html_content = payload.decode(encoding, errors='ignore')
                    except (UnicodeDecodeError, LookupError):
                        html_content = payload.decode('utf-8', errors='ignore')
        
        return html_content

    def _extract_text_fallback(self, content: str) -> str:
        """
        Fallback method to extract text when MIME parsing fails.
        
        Args:
            content: Raw file content
            
        Returns:
            Extracted text
        """
        # Look for HTML content in the raw data
        html_start = content.find('<html')
        if html_start == -1:
            html_start = content.find('<HTML')
        
        if html_start != -1:
            html_end = content.rfind('</html>')
            if html_end == -1:
                html_end = content.rfind('</HTML>')
            
            if html_end != -1:
                html_content = content[html_start:html_end + 7]
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Get text content
                text = soup.get_text(separator=' ', strip=True)
                return ' '.join(text.split())
        
        # Final fallback: return raw content with some cleanup
        # Remove MIME headers and common MHT artifacts
        lines = content.split('\n')
        text_lines = []
        skip_headers = True
        
        for line in lines:
            line = line.strip()
            
            # Skip MIME headers
            if skip_headers:
                if line.startswith('------=') or not line:
                    continue
                if ':' in line and any(header in line.lower() for header in 
                                     ['content-type', 'content-transfer', 'mime-version', 'content-location']):
                    continue
                skip_headers = False
            
            # Skip empty lines and common artifacts
            if line and not line.startswith('------='):
                text_lines.append(line)
        
        return ' '.join(text_lines)

    # Legacy compatibility methods
    def process_mht_file(self, file_path: Path) -> List[Document]:
        """
        Legacy method for processing MHT files.
        Maintained for backward compatibility.
        
        Args:
            file_path: Path to the MHT file
            
        Returns:
            List of LangChain Document objects
        """
        return self.process_document(file_path)