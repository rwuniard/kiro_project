import os

from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings
import chromadb
from chromadb.config import Settings

try:
    from .document_processor import ProcessorRegistry
    from .logging_config import get_logger
    from .pdf_processor import PDFProcessor
    from .office_processor import OfficeProcessor
    from .text_processor import TextProcessor
except ImportError:
    # Fallback for direct execution
    from document_processor import ProcessorRegistry
    from logging_config import get_logger
    from pdf_processor import PDFProcessor
    from office_processor import OfficeProcessor
    from text_processor import TextProcessor

# Load .env from the same directory as this script
load_dotenv(Path(__file__).parent / ".env")

# Initialize logger
logger = get_logger("store_embeddings")
logger.info(
    "Environment configuration loaded", env_path=str(Path(__file__).parent / ".env")
)

# Configuration - use same structure as search_similarity.py
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class ModelVendor(Enum):
    OPENAI = "openai"
    GOOGLE = "google"


class ChromaClientMode(Enum):
    EMBEDDED = "embedded"
    CLIENT_SERVER = "client_server"


def create_chroma_client(
    client_mode: str = "embedded",
    server_host: str = "localhost", 
    server_port: int = 8000,
    persist_directory: Optional[Path] = None
) -> chromadb.Client:
    """
    Create a ChromaDB client based on the specified mode.
    
    Args:
        client_mode: "embedded" or "client_server"
        server_host: Host for client-server mode
        server_port: Port for client-server mode  
        persist_directory: Directory for embedded mode
        
    Returns:
        ChromaDB client instance
    """
    if client_mode == ChromaClientMode.EMBEDDED.value:
        if persist_directory:
            # Embedded mode with persistence
            settings = Settings(
                persist_directory=str(persist_directory),
                is_persistent=True
            )
            return chromadb.Client(settings)
        else:
            # In-memory embedded mode
            return chromadb.Client()
    
    elif client_mode == ChromaClientMode.CLIENT_SERVER.value:
        # Client-server mode
        return chromadb.HttpClient(
            host=server_host,
            port=server_port
        )
    
    else:
        raise ValueError(f"Invalid client mode: {client_mode}. Must be 'embedded' or 'client_server'")


def get_chroma_collection_name(model_vendor: ModelVendor, custom_name: Optional[str] = None) -> str:
    """
    Generate ChromaDB collection name based on model vendor.
    
    Args:
        model_vendor: The embedding model vendor
        custom_name: Optional custom collection name
        
    Returns:
        Collection name string
    """
    if custom_name:
        return custom_name
    
    # Default collection names based on vendor
    if model_vendor == ModelVendor.OPENAI:
        return "documents_openai"
    elif model_vendor == ModelVendor.GOOGLE:
        return "documents_google"
    else:
        return "documents_default"


def get_document_processor_registry() -> ProcessorRegistry:
    """
    Initialize and return a document processor registry with all supported processors.

    Returns:
        ProcessorRegistry configured with PDF, Text, and Office processors
    """
    registry = ProcessorRegistry()

    # Register all available processors
    registry.register_processor(PDFProcessor())
    registry.register_processor(TextProcessor())
    registry.register_processor(OfficeProcessor())

    return registry


def process_documents_from_directory(directory_path: Path) -> list[Document]:
    """
    Process all supported documents from directory using the processor registry.

    Args:
        directory_path: Path to directory containing documents

    Returns:
        List of processed Document objects
    """
    directory = Path(directory_path)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    registry = get_document_processor_registry()
    supported_extensions = registry.get_supported_extensions()

    all_documents = []

    # Process all files with supported extensions
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                processor = registry.get_processor_for_file(file_path)
                if processor:
                    logger.info(
                        "Processing document",
                        file_type=processor.file_type_description,
                        file_name=file_path.name,
                        processor_name=processor.processor_name,
                    )
                    docs = registry.process_document(file_path)
                    all_documents.extend(docs)
                    logger.info(
                        "Document processed successfully",
                        file_name=file_path.name,
                        chunks_extracted=len(docs),
                        processor_name=processor.processor_name,
                    )
                else:
                    logger.warning(
                        "No processor found for file",
                        file_name=file_path.name,
                        file_extension=file_path.suffix,
                    )
            except Exception as e:
                logger.error(
                    "Error processing document",
                    file_name=file_path.name,
                    error=str(e),
                    error_type=type(e).__name__,
                )

    if not all_documents:
        logger.warning(
            "No supported documents found",
            directory_path=str(directory_path),
            supported_extensions=sorted(supported_extensions),
        )

    return all_documents


# Legacy functions for backward compatibility
def load_txt_documents(file_path):
    """Load documents from text files (legacy function)."""
    registry = get_document_processor_registry()
    return registry.process_document(Path(file_path))


def process_text_files(directory_path: Path) -> list[Document]:
    """Process all .txt files in directory (legacy function)."""
    documents = []
    registry = get_document_processor_registry()

    for txt_file in directory_path.glob("*.txt"):
        try:
            logger.info("Processing legacy text file", file_name=txt_file.name)
            docs = registry.process_document(txt_file)
            documents.extend(docs)
            logger.info(
                "Legacy text file processed",
                file_name=txt_file.name,
                chunks_loaded=len(docs),
            )
        except Exception as e:
            logger.error(
                "Error processing legacy text file",
                file_name=txt_file.name,
                error=str(e),
                error_type=type(e).__name__,
            )
    return documents


def process_pdf_files(directory_path: Path) -> list[Document]:
    """Process all .pdf files in directory (legacy function)."""
    documents = []
    registry = get_document_processor_registry()

    for pdf_file in directory_path.glob("*.pdf"):
        try:
            logger.info("Processing legacy PDF file", file_name=pdf_file.name)
            docs = registry.process_document(pdf_file)
            documents.extend(docs)
            logger.info(
                "Legacy PDF file processed",
                file_name=pdf_file.name,
                chunks_extracted=len(docs),
                splitting_method="RecursiveCharacterTextSplitter",
            )
        except Exception as e:
            logger.error(
                "Error processing legacy PDF file",
                file_name=pdf_file.name,
                error=str(e),
                error_type=type(e).__name__,
            )
    return documents


def load_documents_from_directory(directory_path: Path) -> list[Document]:
    """Load all supported documents from directory (legacy function)."""
    return process_documents_from_directory(directory_path)


def ensure_data_directory(model_vendor: ModelVendor) -> Path:
    """Ensure the data directory exists for the specified model vendor."""
    if model_vendor == ModelVendor.OPENAI:
        db_path = DATA_DIR / "chroma_db_openai"
    elif model_vendor == ModelVendor.GOOGLE:
        db_path = DATA_DIR / "chroma_db_google"

    db_path.mkdir(parents=True, exist_ok=True)
    return db_path


def load_embedding_model(model_vendor: ModelVendor):
    """Load the embedding model based on the vendor."""
    if model_vendor == ModelVendor.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return OpenAIEmbeddings(openai_api_key=api_key)
    if model_vendor == ModelVendor.GOOGLE:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        return GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", google_api_key=api_key
        )


def get_text_splitter():
    """Get optimized text splitter for mixed factual content."""
    return CharacterTextSplitter(
        separator="\n",
        chunk_size=300,  # Increased from 200 for better context
        chunk_overlap=50,  # Added overlap for better continuity
    )


def store_to_chroma(
    documents: list[Document], 
    model_vendor: ModelVendor,
    client_mode: str = "embedded",
    server_host: str = "localhost",
    server_port: int = 8000,
    collection_name: Optional[str] = None,
    persist_directory: Optional[Path] = None
) -> Chroma:
    """
    Store documents to ChromaDB using embedded or client-server mode.
    
    Args:
        documents: List of documents to store
        model_vendor: Embedding model vendor
        client_mode: "embedded" or "client_server"
        server_host: Host for client-server mode
        server_port: Port for client-server mode
        collection_name: Custom collection name (optional)
        persist_directory: Directory for embedded mode (optional)
        
    Returns:
        Chroma vectorstore instance
    """
    # Get the embedding model
    embedding_model = load_embedding_model(model_vendor)
    
    # Generate collection name
    collection_name = get_chroma_collection_name(model_vendor, collection_name)
    
    if client_mode == ChromaClientMode.EMBEDDED.value:
        # Embedded mode - use persist_directory or default
        if not persist_directory:
            persist_directory = ensure_data_directory(model_vendor)
        
        vectorstore = Chroma.from_documents(
            documents=documents, 
            embedding=embedding_model, 
            persist_directory=str(persist_directory),
            collection_name=collection_name
        )
        
        logger.info(
            "Documents stored to ChromaDB (embedded mode)",
            documents_count=len(documents),
            database_path=str(persist_directory),
            model_vendor=model_vendor.value,
            collection_name=collection_name,
            client_mode=client_mode
        )
        
    elif client_mode == ChromaClientMode.CLIENT_SERVER.value:
        # Client-server mode - connect to remote ChromaDB server
        chroma_client = create_chroma_client(
            client_mode=client_mode,
            server_host=server_host,
            server_port=server_port
        )
        
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embedding_model,
            client=chroma_client,
            collection_name=collection_name
        )
        
        logger.info(
            "Documents stored to ChromaDB (client-server mode)",
            documents_count=len(documents),
            server_host=server_host,
            server_port=server_port,
            model_vendor=model_vendor.value,
            collection_name=collection_name,
            client_mode=client_mode
        )
        
    else:
        raise ValueError(f"Invalid client mode: {client_mode}")
    
    return vectorstore


def main():
    """Store documents (text and PDF) to ChromaDB using Google embeddings."""
    logger.info("Starting document embedding storage process")

    # Use the new unified document processing
    # Look for data_source in the rag_store directory
    data_source_dir = Path(__file__).parent / "data_source"

    try:
        all_documents = process_documents_from_directory(data_source_dir)

        if not all_documents:
            registry = get_document_processor_registry()
            supported_formats = [
                processor.file_type_description
                for processor in registry.get_all_processors().values()
            ]
            logger.warning(
                "No documents found in data source directory",
                data_source_dir=str(data_source_dir),
                supported_formats=supported_formats,
            )
            return

        logger.info(
            "Documents loaded successfully",
            total_documents=len(all_documents),
            data_source_dir=str(data_source_dir),
        )
    except Exception as e:
        logger.error(
            "Error loading documents",
            error=str(e),
            error_type=type(e).__name__,
            data_source_dir=str(data_source_dir),
        )
        return

    # Store documents using Google embeddings
    vectorstore = store_to_chroma(all_documents, ModelVendor.GOOGLE)
    logger.info(
        "Document storage completed successfully",
        database_location=str(DATA_DIR / "chroma_db_google"),
        model_vendor="google",
        total_documents=len(all_documents),
    )

    # Test the storage by doing a quick search
    test_results = vectorstore.similarity_search("interesting fact", k=6)
    logger.info(
        "Test search completed",
        query="interesting fact",
        results_count=len(test_results),
        k=6,
    )
    for i, result in enumerate(test_results, 1):
        logger.info(
            "Test search result",
            result_number=i,
            content_preview=result.page_content[:200],
            metadata=result.metadata,
        )

    query = "Find me a python class example."
    test_results_pdf = vectorstore.similarity_search(query, k=3)
    logger.info(
        "PDF test search completed",
        query=query,
        results_count=len(test_results_pdf),
        k=3,
    )
    for i, result_pdf in enumerate(test_results_pdf, 1):
        logger.info(
            "PDF test search result",
            result_number=i,
            content_preview=result_pdf.page_content[:200],
            metadata=result_pdf.metadata,
        )


if __name__ == "__main__":
    main()
