# Data Source Directory

This directory contains documents for processing and ingestion into the RAG system.

## 📁 Supported File Types

Place your documents here for processing:

- **📄 Text Files**: `.txt`, `.md`, `.text`
- **📕 PDF Files**: `.pdf` 
- **📘 Word Documents**: `.docx`

## 🚀 Processing Documents

```bash
# From project root
python main.py store

# Or directly
cd src/rag_store
python store_embeddings.py
```

## 📊 Current Files

This directory contains sample documents for testing and demonstration:

- `facts.txt` - Sample text facts
- `test_document.txt` - Basic test document  
- `thinkpython.pdf` - Sample PDF (394 chunks)
- Legal documents (.docx) - Word document examples
- Regulatory documents (.pdf) - PDF examples

## 🔧 Processing Details

- **Chunk Sizes**: 300 chars (text), 1000 chars (Word), 1800 chars (PDF)
- **Overlap**: Optimized for each document type
- **Metadata**: Includes file info, processing method, and document properties
- **Error Handling**: Graceful handling of corrupted files

Documents are processed with universal document processor interface and stored in ChromaDB with Google embeddings.