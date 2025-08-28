# RAG Store - Document Ingestion Service

A professional document processing and storage service for RAG (Retrieval-Augmented Generation) systems with **universal document processor interface**. Converts PDF, Word, MHT/MHTML, text, and markdown documents into searchable vector embeddings using ChromaDB.

## 🎯 Purpose

RAG Store is the **ingestion microservice** that:
- Processes PDF, Word, MHT/MHTML, text, and markdown documents using universal interface
- Converts them into vector embeddings
- Stores them in ChromaDB for semantic search
- Optimizes chunking for better search quality
- Supports extensible document processor architecture
- Features robust error handling with fallback parsing for problematic files

## 🚀 Quick Start

### 1. Environment Setup

Create a `.env` file in this directory:
```bash
# Required for Google embeddings
GOOGLE_API_KEY=your_google_api_key_here

# Optional for OpenAI embeddings
OPENAI_API_KEY=your_openai_api_key_here

# Optional for OCR debugging
# OCR_INVESTIGATE=false
# OCR_INVESTIGATE_DIR=./ocr_debug
```

### 2. Install System Dependencies

The RAG Store requires several system dependencies for full document processing capabilities:

#### Tesseract OCR (Optional - PDF Image Processing)

For OCR support on image-based PDFs:

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr

# Windows (Chocolatey)
choco install tesseract

# Or download Windows installer from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

#### Pandoc (Required - RTF Processing)

For RTF document processing:

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt-get install pandoc

# Windows
# Download from https://pandoc.org/installing.html
# Or use chocolatey:
choco install pandoc
```

#### LibreOffice (Required - Legacy .doc Processing)

For legacy Microsoft Word (.doc) file processing:

```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Debian
sudo apt-get install libreoffice

# Windows
# Download from https://www.libreoffice.org/download/download-libreoffice/
# Or use chocolatey:
choco install libreoffice
```

#### libmagic (Optional - Enhanced File Type Detection)

For improved file type detection by the `unstructured` library:

```bash
# macOS
brew install libmagic

# Ubuntu/Debian
sudo apt-get install libmagic1

# Windows
# Windows users: libmagic is not readily available, but file processing will still work
# The unstructured library will fall back to extension-based detection
```

**Verify installations:**
```bash
tesseract --version    # Should output: tesseract 5.x.x
pandoc --version       # Should output: pandoc 3.x.x
libreoffice --version  # Should output: LibreOffice 7.x.x
file --version         # Should show libmagic availability
```

**Notes**: 
- Without Tesseract: PDFs will still process but won't perform OCR on image-based content
- Without Pandoc: RTF files will fail to process
- Without LibreOffice: Legacy .doc files will fail to process (modern .docx files will still work)
- Without libmagic: File type detection relies on extensions only, may show warnings but processing continues

### 3. Add Documents

Place your documents in the `data_source/` directory:
```
src/rag_store/data_source/
├── your_document.pdf
├── report.docx
├── legacy_doc.doc
├── rich_text.rtf
├── web_archive.mht
├── facts.txt
├── documentation.md
└── plain_text.text
```

Supported formats:
- **PDF files** (`.pdf`) - Processed with PyMuPDF + OCR support + RecursiveCharacterTextSplitter
- **Microsoft Word documents** (`.docx`, `.doc`) - Processed with UnstructuredLoader + RecursiveCharacterTextSplitter
- **Rich Text Format** (`.rtf`) - Processed with UnstructuredRTFLoader + RecursiveCharacterTextSplitter  
- **MHT/MHTML web archives** (`.mht`, `.mhtml`) - Processed with UnstructuredLoader + manual MIME parser fallback + RecursiveCharacterTextSplitter
- **Text documents** (`.txt`, `.md`, `.text`) - Processed with TextLoader + CharacterTextSplitter

### 4. Run Document Ingestion

```bash
# From project root
python main.py store

# Or directly
python src/rag_store/store_embeddings.py

# Or using the CLI command (if installed)
rag-store-cli store
```

## 📁 Project Structure

```
src/rag_store/
├── README.md                 # This file
├── .env                     # Environment variables
├── data_source/            # Input documents directory
│   ├── *.pdf              # PDF documents
│   ├── *.docx             # Word documents  
│   ├── *.mht              # MHT/MHTML web archives
│   ├── *.txt              # Text documents
│   └── *.md               # Markdown documents
├── document_processor.py   # Universal document processor interface
├── pdf_processor.py        # PDF processing and chunking
├── word_processor.py       # Word document processing and chunking
├── mht_processor.py        # MHT/MHTML web archive processing
├── text_processor.py       # Text and markdown processing
├── logging_config.py       # Structured logging configuration
├── store_embeddings.py     # Main ingestion script
└── cli.py                 # Command-line interface
```

## 📊 Structured Logging

RAG Store features comprehensive structured logging with JSON output and Prometheus metrics for observability:

### **Logging Features**
- **Structured JSON logging** with `structlog` for machine-readable logs
- **Prometheus metrics** for document processing metrics
- **Performance tracking** with processing times and file sizes
- **Error tracking** with detailed error context
- **Registry operations** logging for processor management

### **Log Examples**

**Document Processing Start:**
```json
{
  "processor_name": "PDFProcessor",
  "file_path": "/path/to/document.pdf", 
  "file_size": 834685,
  "file_type": ".pdf",
  "operation": "document_processing",
  "event": "Document processing started",
  "logger": "rag_store",
  "level": "info",
  "timestamp": "2025-08-19T02:44:16.642198Z"
}
```

**Document Processing Complete:**
```json
{
  "chunks_created": 394,
  "processing_time_seconds": 1.19,
  "status": "success",
  "processor_name": "PDFProcessor",
  "file_path": "/path/to/document.pdf",
  "file_size": 834685,
  "file_type": ".pdf",
  "operation": "document_processing", 
  "event": "Document processing completed",
  "logger": "rag_store",
  "level": "info",
  "timestamp": "2025-08-19T02:44:17.830945Z"
}
```

**Error Handling:**
```json
{
  "error": "PDF loading failed",
  "error_type": "pdf_processing_error",
  "processor_name": "PDFProcessor",
  "file_path": "/path/to/error.pdf",
  "operation": "document_processing",
  "event": "Document processing failed",
  "logger": "rag_store", 
  "level": "error",
  "timestamp": "2025-08-19T02:44:28.853742Z"
}
```

### **Prometheus Metrics**

The logging system includes built-in Prometheus metrics:

- `rag_documents_processed_total` - Counter of processed documents by processor and status
- `rag_chunks_created_total` - Counter of chunks created by processor type
- `rag_processing_errors_total` - Counter of processing errors by type
- `rag_document_processing_duration_seconds` - Histogram of processing times
- `rag_document_size_bytes` - Histogram of document sizes
- `rag_active_processors` - Gauge of active processor instances

### **Integration Ready**

The structured logging is designed for:
- **LangSmith**: JSON logs can be ingested for LLM observability
- **Prometheus + Grafana**: Built-in metrics for monitoring dashboards
- **ELK Stack**: Structured JSON for log aggregation
- **Cloud Logging**: AWS CloudWatch, Google Cloud Logging, etc.

## 🔧 Components

### **Universal Document Processor** (`document_processor.py`)
- **Purpose**: Abstract base class and registry for all document processors
- **Architecture**: Strategy pattern with processor registry
- **Features**: Dynamic processor selection, extensible interface, metadata enhancement
- **Benefits**: Easy to add new document types (Word, Excel, etc.)

### **PDF Processor** (`pdf_processor.py`)
- **Purpose**: Extract and chunk text from PDF documents with advanced OCR support for image-based PDFs
- **Technology**: PyMuPDF + Tesseract OCR + RecursiveCharacterTextSplitter
- **Parameters**: 1800 chars with 270 overlap (industry best practices)
- **Features**: 
  - **True OCR Support**: Tesseract OCR engine for scanned documents and image-based PDFs
  - **Multi-layer Text Extraction**: 
    - Primary: Direct text extraction from PDF structure
    - Secondary: Structured text blocks for complex layouts  
    - Tertiary: Tesseract OCR for image content (<50 chars triggers OCR)
  - **Intelligent Fallback**: Automatic detection and processing of image-based content
  - **Page Tracking**: Maintains page numbers and document structure
  - **Enhanced Metadata**: Extraction method tracking (pymupdf_text, pymupdf_blocks, tesseract_ocr)

### **Word Processor** (`word_processor.py`)
- **Purpose**: Extract and chunk text from Microsoft Word documents
- **Technology**: UnstructuredLoader + RecursiveCharacterTextSplitter
- **Parameters**: 1000 chars with 150 overlap (balanced for Word content)
- **Features**: Legacy .doc and modern .docx support, LibreOffice conversion for .doc files, metadata enhancement, error handling

### **MHT Processor** (`mht_processor.py`)
- **Purpose**: Extract and chunk text from MHT/MHTML web archive files with robust error handling
- **Technology**: Dual-parser architecture with UnstructuredLoader + manual MIME parser fallback + RecursiveCharacterTextSplitter  
- **Parameters**: 1200 chars with 180 overlap (optimized for HTML content)
- **Features**: 
  - **Primary Parser**: UnstructuredLoader with element mode and fast strategy
  - **Fallback Parser**: Manual MIME email parser for problematic MHT files with email-style headers
  - **HTML Text Extraction**: BeautifulSoup and regex-based conversion with proper entity decoding
  - **Enhanced Metadata**: Extraction method tracking, title preservation, content type detection
  - **Error Recovery**: Graceful fallback when UnstructuredLoader fails with FileType.UNK errors
- **Troubleshooting**: Resolves issues with MHT files that have email-style headers causing UnstructuredLoader failures

### **RTF Processor** (`rtf_processor.py`)
- **Purpose**: Extract and chunk text from Rich Text Format documents
- **Technology**: UnstructuredRTFLoader + RecursiveCharacterTextSplitter
- **Parameters**: 800 chars with 120 overlap (balanced for RTF content)
- **Features**: RTF format support, smart .doc file detection (RTF content with .doc extension), metadata enhancement, requires Pandoc

### **Text Processor** (`text_processor.py`)
- **Purpose**: Extract and chunk text from text and markdown files
- **Technology**: TextLoader + CharacterTextSplitter
- **Parameters**: 300 chars with 50 overlap (optimized for text content)
- **Features**: Multiple encoding support (.txt, .md, .text), markdown processing, chunk metadata

### **Logging Configuration** (`logging_config.py`)
- **Purpose**: Centralized logging configuration with structured JSON output
- **Features**: Prometheus metrics integration, configurable log levels, context tracking
- **Integration**: Ready for LangSmith, Grafana, ELK stack, and cloud logging services

### **Store Embeddings** (`store_embeddings.py`)
- **Purpose**: Convert documents to vectors and store in ChromaDB using unified interface
- **Models**: Google (`text-embedding-004`) and OpenAI support
- **Database**: ChromaDB with separate collections per model
- **Output**: Stored in `../../../data/chroma_db_google/` or `chroma_db_openai/`

### **CLI Interface** (`cli.py`)
- **Purpose**: Command-line entry point for document ingestion
- **Usage**: `rag-store-cli store`
- **Features**: Usage help, environment validation

## 📊 Processing Details

### **PDF Processing**
- **Loader**: PyMuPDF (fitz) with Tesseract OCR integration
- **Splitter**: RecursiveCharacterTextSplitter
- **Chunk Size**: 1800 characters
- **Overlap**: 270 characters (15% overlap ratio)
- **OCR Features**: 
  - **Primary Text Extraction**: Direct text extraction from PDF structure
  - **Block Extraction**: Structured text block parsing for complex layouts
  - **Tesseract OCR**: True OCR for image-based content (<50 chars triggers OCR)
  - **Intelligent Detection**: Automatic identification of image-based pages
  - **High-Quality Processing**: 300 DPI rendering for optimal OCR accuracy
- **Metadata**: Page numbers, extraction method (pymupdf_text/blocks/tesseract_ocr), processing details

### **Word Processing**
- **Loader**: UnstructuredLoader (with LibreOffice backend for .doc conversion)
- **Splitter**: RecursiveCharacterTextSplitter
- **Chunk Size**: 1000 characters
- **Overlap**: 150 characters
- **Separators**: Paragraphs, lines, words, characters
- **Supported**: `.docx`, `.doc` files (requires LibreOffice for legacy .doc)

### **MHT/MHTML Processing**
- **Primary Loader**: UnstructuredLoader (element mode, fast strategy)
- **Fallback Parser**: Python email library for MIME structure parsing
- **Text Extractor**: BeautifulSoup with regex fallback for HTML-to-text conversion
- **Splitter**: RecursiveCharacterTextSplitter
- **Chunk Size**: 1200 characters
- **Overlap**: 180 characters (15% overlap ratio)
- **Separators**: HTML-friendly separators (`\n\n`, `\n`, ` `, `""`)
- **Supported**: `.mht`, `.mhtml` files
- **Error Handling**: Automatic fallback for files with email-style headers that cause UnstructuredLoader FileType.UNK errors
- **Metadata**: Extraction method, title preservation, content type, source format

### **RTF Processing**
- **Loader**: UnstructuredRTFLoader (LangChain Community)
- **Splitter**: RecursiveCharacterTextSplitter
- **Chunk Size**: 800 characters
- **Overlap**: 120 characters (15% overlap ratio)
- **Separators**: Paragraphs, lines, words, characters
- **Supported**: `.rtf` files
- **Smart Detection**: Automatically detects RTF content in files with `.doc` extensions
- **Requirements**: Pandoc system dependency for RTF parsing

### **Text Processing** 
- **Loader**: TextLoader (LangChain)
- **Splitter**: CharacterTextSplitter
- **Chunk Size**: 300 characters
- **Overlap**: 50 characters
- **Separator**: Double newlines (`\n\n`)
- **Supported**: `.txt`, `.md`, `.text` files

### **Document Registry**
- **Pattern**: Registry pattern for processor management
- **Selection**: Automatic by file extension
- **Extensibility**: Easy to add new processors (Word, Excel, etc.)
- **Metadata**: Enhanced metadata with processor information

### **Embedding Models**

| Model | Provider | Dimensions | Use Case |
|-------|----------|------------|----------|
| `text-embedding-004` | Google | 768 | Default, high quality |
| `text-embedding-ada-002` | OpenAI | 1536 | Alternative option |

## 🗄️ Database Structure

Documents are stored in ChromaDB collections:

```
data/
├── chroma_db_google/       # Google embeddings
│   ├── chroma.sqlite3     # SQLite database
│   └── [collection data]  # Vector data
└── chroma_db_openai/      # OpenAI embeddings (if used)
    ├── chroma.sqlite3
    └── [collection data]
```

**Collection Schema**:
- **Document Content**: Chunked text content
- **Metadata**: Source file, page numbers, chunk IDs
- **Embeddings**: Vector representations (768d for Google, 1536d for OpenAI)

## 🎛️ Configuration

### **Environment Variables**
```bash
# Required
GOOGLE_API_KEY=your_key_here

# Optional  
OPENAI_API_KEY=your_key_here
```

### **Model Selection**
```python
# In store_embeddings.py
from rag_store.store_embeddings import ModelVendor

# Use Google (default)
load_embedding_model(ModelVendor.GOOGLE)

# Use OpenAI
load_embedding_model(ModelVendor.OPENAI)
```

## 🔍 Usage Examples

### **Basic Document Processing**
```bash
# Add documents to data_source/
cp ~/Documents/*.pdf src/rag_store/data_source/

# Process all documents
python main.py store
```

### **Check Processing Results**
```bash
# View processed documents count
ls data/chroma_db_google/
```

### **Programmatic Usage**
```python
# Using the universal interface (recommended)
from rag_store.store_embeddings import process_documents_from_directory
from pathlib import Path

# Process all supported documents in directory
all_docs = process_documents_from_directory(Path("my_documents/"))

# Legacy individual processing
from rag_store.store_embeddings import process_pdf_files, process_text_files
pdf_docs = process_pdf_files(Path("my_pdfs/"))
text_docs = process_text_files(Path("my_texts/"))

# Using processor registry directly
from rag_store.store_embeddings import get_document_processor_registry
registry = get_document_processor_registry()
documents = registry.process_document(Path("document.pdf"))
```

### **Logging Usage**
```python
# Get structured logger
from rag_store.logging_config import get_logger
logger = get_logger("my_module")

# Log with structured data
logger.info("Processing started", file_path="document.pdf", size=1024)

# Access Prometheus metrics
from rag_store.logging_config import get_metrics_registry
metrics = get_metrics_registry()

# View metrics in console (development)
python -c "from prometheus_client import generate_latest; print(generate_latest().decode())"
```

## 🏗️ Architecture Integration

RAG Store is designed as an **independent microservice**:

- **Input**: Documents in `data_source/`
- **Output**: Vector database in `data/chroma_db_*/`
- **Consumers**: RAG Fetch service, MCP servers, other search services

**Microservices Flow**:
```
Documents → RAG Store → ChromaDB → RAG Fetch → Search Results
```

## 🧪 Quality Features

### **Optimized Chunking**
- **Evidence-based parameters** from 2024 industry benchmarks
- **RecursiveCharacterTextSplitter** for natural language boundaries
- **3% better relevance** vs. custom chunking methods

### **Error Handling**
- Graceful handling of corrupted PDFs
- Detailed logging and progress tracking
- Validation of environment variables

### **Performance**
- Efficient batch processing
- Memory-optimized for large documents
- Progress indicators for long operations

## 📝 Development

### **Testing**
```bash
# Run all store-specific tests
python -m unittest tests.test_rag_store.test_document_processor -v
python -m unittest tests.test_rag_store.test_pdf_processor -v
python -m unittest tests.test_rag_store.test_store_embeddings -v

# Run comprehensive tests (42 total)
python -m unittest tests.test_rag_store -v
```

### **Dependencies**
```toml
# Core dependencies
chromadb = ">=1.0.17"
langchain = ">=0.3.27"
langchain-chroma = ">=0.2.5"
langchain-community = ">=0.3.27"
langchain-google-genai = ">=2.0.10"
langchain-openai = ">=0.2.0"
pymupdf = ">=1.26.4"
pytesseract = ">=0.3.13"
pillow = ">=11.3.0"
python-dotenv = ">=1.1.1"

# Document processing dependencies
unstructured = ">=0.18.14"
langchain-unstructured = ">=0.1.6"
beautifulsoup4 = ">=4.13.5"

# Additional dependencies for compatibility
docx2txt = ">=0.8"           # Legacy compatibility (not actively used)
google-generativeai = ">=0.3.0"
PyPDF2 = ">=3.0.0"          # Backup PDF processor
python-docx = ">=0.8.11"    # Backup Word processor
cryptography = ">=3.1"      # Security for embeddings

# Logging and observability
structlog = ">=24.1.0"
prometheus-client = ">=0.21.0"
```

## 🔗 Related Services

- **RAG Fetch**: Semantic search and retrieval service
- **MCP Server**: Model Context Protocol integration
- **Main CLI**: Unified command interface

## 📄 License

Part of the MCP RAG project - MIT License