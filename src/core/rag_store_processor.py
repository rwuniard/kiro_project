"""
RAG Store Processor implementation for document processing integration.

This module provides a concrete implementation of DocumentProcessingInterface
that integrates with the existing RAG store functionality for processing
documents and storing embeddings in ChromaDB.
"""

import os
import time
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Set

from .document_processing import (
    DocumentProcessingInterface,
    ProcessingResult,
    DocumentProcessingError
)

try:
    from ..rag_store.document_processor import ProcessorRegistry
    from ..rag_store.pdf_processor import PDFProcessor
    from ..rag_store.text_processor import TextProcessor
    from ..rag_store.word_processor import WordProcessor
    from ..rag_store.store_embeddings import (
        ModelVendor,
        load_embedding_model,
        ensure_data_directory,
        store_to_chroma
    )
    from ..rag_store.logging_config import get_logger
except ImportError:
    # Fallback for testing or direct execution
    from src.rag_store.document_processor import ProcessorRegistry
    from src.rag_store.pdf_processor import PDFProcessor
    from src.rag_store.text_processor import TextProcessor
    from src.rag_store.word_processor import WordProcessor
    from src.rag_store.store_embeddings import (
        ModelVendor,
        load_embedding_model,
        ensure_data_directory,
        store_to_chroma
    )
    from src.rag_store.logging_config import get_logger


class RAGStoreProcessor(DocumentProcessingInterface):
    """
    RAG Store implementation of DocumentProcessingInterface.
    
    This processor integrates with the existing RAG store functionality
    to process documents and store embeddings in ChromaDB for semantic search.
    """
    
    def __init__(self):
        """Initialize the RAG Store Processor."""
        self.registry: Optional[ProcessorRegistry] = None
        self.model_vendor: ModelVendor = ModelVendor.GOOGLE
        self.embedding_model = None
        self.chroma_db_path: Optional[Path] = None
        self.initialized: bool = False
        self.logger = get_logger("rag_store_processor")
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the RAG store components.
        
        Args:
            config: Configuration dictionary containing:
                - model_vendor: "google" or "openai" (default: "google")
                - google_api_key: Google API key (if using Google)
                - openai_api_key: OpenAI API key (if using OpenAI)
                - chroma_db_path: Path for ChromaDB storage (optional)
                
        Returns:
            bool: True if initialization successful, False otherwise
            
        Raises:
            Exception: If initialization fails with unrecoverable error
        """
        try:
            self.logger.info("Initializing RAG Store Processor", config_keys=list(config.keys()))
            
            # Set model vendor
            vendor_str = config.get("model_vendor", "google").lower()
            if vendor_str == "openai":
                self.model_vendor = ModelVendor.OPENAI
            elif vendor_str == "google":
                self.model_vendor = ModelVendor.GOOGLE
            else:
                raise ValueError(f"Unsupported model vendor: {vendor_str}")
            
            # Load environment variables for API keys
            self._load_environment_variables(config)
            
            # Initialize processor registry
            self._initialize_processor_registry()
            
            # Initialize embedding model
            self._initialize_embedding_model()
            
            # Setup ChromaDB path
            self._setup_chroma_db_path(config)
            
            self.initialized = True
            self.logger.info(
                "RAG Store Processor initialized successfully",
                model_vendor=self.model_vendor.value,
                supported_extensions=list(self.get_supported_extensions()),
                chroma_db_path=str(self.chroma_db_path)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize RAG Store Processor",
                error=str(e),
                error_type=type(e).__name__,
                stack_trace=traceback.format_exc()
            )
            self.initialized = False
            raise
    
    def _load_environment_variables(self, config: Dict[str, Any]) -> None:
        """Load and validate required environment variables."""
        if self.model_vendor == ModelVendor.GOOGLE:
            api_key = config.get("google_api_key") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY is required for Google model vendor")
            os.environ["GOOGLE_API_KEY"] = api_key
            
        elif self.model_vendor == ModelVendor.OPENAI:
            api_key = config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI model vendor")
            os.environ["OPENAI_API_KEY"] = api_key
    
    def _initialize_processor_registry(self) -> None:
        """Initialize the document processor registry with all supported processors."""
        self.registry = ProcessorRegistry()
        
        # Register all available processors
        self.registry.register_processor(PDFProcessor())
        self.registry.register_processor(TextProcessor())
        self.registry.register_processor(WordProcessor())
        
        # Get registry info for logging
        try:
            all_processors = self.registry.get_all_processors()
            supported_extensions = self.registry.get_supported_extensions()
            
            self.logger.info(
                "Processor registry initialized",
                registered_processors=list(all_processors.keys()) if all_processors else [],
                supported_extensions=list(supported_extensions) if supported_extensions else []
            )
        except Exception as e:
            self.logger.warning(
                "Could not log registry details",
                error=str(e)
            )
    
    def _initialize_embedding_model(self) -> None:
        """Initialize the embedding model."""
        self.embedding_model = load_embedding_model(self.model_vendor)
        self.logger.info(
            "Embedding model initialized",
            model_vendor=self.model_vendor.value
        )
    
    def _setup_chroma_db_path(self, config: Dict[str, Any]) -> None:
        """Setup ChromaDB storage path."""
        custom_path = config.get("chroma_db_path")
        if custom_path:
            self.chroma_db_path = Path(custom_path)
        else:
            # Use default path from store_embeddings
            self.chroma_db_path = ensure_data_directory(self.model_vendor)
        
        # Ensure directory exists
        self.chroma_db_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            "ChromaDB path configured",
            chroma_db_path=str(self.chroma_db_path)
        )
    
    def is_supported_file(self, file_path: Path) -> bool:
        """
        Check if the given file type is supported by the RAG store processors.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file type is supported, False otherwise
        """
        if not self.initialized or not self.registry:
            return False
        
        processor = self.registry.get_processor_for_file(file_path)
        return processor is not None
    
    def process_document(self, file_path: Path) -> ProcessingResult:
        """
        Process a document through the RAG store pipeline.
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            ProcessingResult: Standardized processing result
            
        Raises:
            DocumentProcessingError: If processing fails
        """
        if not self.initialized:
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                processor_used=self.get_processor_name(),
                processing_time=0.0,
                error_message="Processor not initialized",
                error_type="initialization_error"
            )
        
        start_time = time.time()
        
        try:
            # Validate file path
            self.validate_file_path(file_path)
            
            # Collect file metadata early to avoid race conditions
            file_size = file_path.stat().st_size
            file_extension = file_path.suffix
            
            # Check if file is supported
            if not self.is_supported_file(file_path):
                return ProcessingResult(
                    success=False,
                    file_path=str(file_path),
                    processor_used=self.get_processor_name(),
                    processing_time=time.time() - start_time,
                    error_message=f"Unsupported file type: {file_path.suffix}",
                    error_type="unsupported_file_type",
                    metadata={
                        "file_extension": file_extension,
                        "supported_extensions": list(self.get_supported_extensions())
                    }
                )
            
            # Process document through registry
            self.logger.info(
                "Starting document processing",
                file_path=str(file_path),
                file_size=file_size
            )
            
            documents = self.registry.process_document(file_path)
            
            if not documents:
                return ProcessingResult(
                    success=False,
                    file_path=str(file_path),
                    processor_used=self.get_processor_name(),
                    processing_time=time.time() - start_time,
                    error_message="No content extracted from document",
                    error_type="empty_document",
                    metadata={"file_size": file_size}
                )
            
            # Store embeddings in ChromaDB
            self.logger.info(
                "Storing embeddings to ChromaDB",
                file_path=str(file_path),
                chunks_count=len(documents)
            )
            
            vectorstore = store_to_chroma(documents, self.model_vendor)
            
            processing_time = time.time() - start_time
            
            # Get processor name for metadata
            processor = self.registry.get_processor_for_file(file_path)
            processor_name = processor.processor_name if processor else "unknown"
            
            self.logger.info(
                "Document processing completed successfully",
                file_path=str(file_path),
                chunks_created=len(documents),
                processing_time=processing_time,
                processor_name=processor_name
            )
            
            return ProcessingResult(
                success=True,
                file_path=str(file_path),
                processor_used=self.get_processor_name(),
                chunks_created=len(documents),
                processing_time=processing_time,
                metadata={
                    "model_vendor": self.model_vendor.value,
                    "chroma_db_path": str(self.chroma_db_path),
                    "document_processor": processor_name,
                    "file_size": file_size,
                    "file_extension": file_extension
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)
            error_type = type(e).__name__
            
            self.logger.error(
                "Document processing failed",
                file_path=str(file_path),
                error=error_message,
                error_type=error_type,
                processing_time=processing_time,
                stack_trace=traceback.format_exc()
            )
            
            # Create DocumentProcessingError for detailed error information
            processing_error = DocumentProcessingError(
                file_path=str(file_path),
                processor_type=self.get_processor_name(),
                error_message=error_message,
                error_type=error_type,
                stack_trace=traceback.format_exc(),
                file_metadata={
                    "file_size": locals().get('file_size', file_path.stat().st_size if file_path.exists() else 0),
                    "file_extension": locals().get('file_extension', file_path.suffix)
                },
                processing_context={
                    "model_vendor": self.model_vendor.value,
                    "chroma_db_path": str(self.chroma_db_path) if self.chroma_db_path else None,
                    "processing_time": processing_time
                }
            )
            
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                processor_used=self.get_processor_name(),
                processing_time=processing_time,
                error_message=error_message,
                error_type=error_type,
                metadata={
                    "processing_error": processing_error,
                    "model_vendor": self.model_vendor.value,
                    "file_extension": file_path.suffix
                }
            )
    
    def get_supported_extensions(self) -> Set[str]:
        """
        Get the set of file extensions supported by the RAG store processors.
        
        Returns:
            Set[str]: Set of supported file extensions (including the dot, e.g., '.pdf')
        """
        if not self.initialized or not self.registry:
            return set()
        
        return self.registry.get_supported_extensions()
    
    def cleanup(self) -> None:
        """
        Cleanup resources used by the RAG store processor.
        
        This method cleans up any resources and resets the processor state.
        """
        self.logger.info("Cleaning up RAG Store Processor resources")
        
        self.registry = None
        self.embedding_model = None
        self.chroma_db_path = None
        self.initialized = False
        
        self.logger.info("RAG Store Processor cleanup completed")
    
    def get_processor_name(self) -> str:
        """
        Get the name of this processor implementation.
        
        Returns:
            str: Name of the processor
        """
        return "RAGStoreProcessor"