"""
RAG Store - Document Ingestion Service

Independent service for processing and storing documents with embeddings.
Can be deployed separately from the search service.
"""

from .pdf_processor import PDFProcessor
from .office_processor import OfficeProcessor
from .store_embeddings import ModelVendor, load_embedding_model, store_to_chroma

__version__ = "0.1.0"
__all__ = ["ModelVendor", "PDFProcessor", "OfficeProcessor", "load_embedding_model", "store_to_chroma"]
