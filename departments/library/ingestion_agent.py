"""
departments/library/ingestion_agent.py
---------------------------------------
LangGraph nodes for the ingestion pipeline.

Flow:
    extract_text → chunk_text → embed_and_store

Each function is a node: takes LibraryState, returns partial state update.
The graph wires them together in library_graph.py.
"""

import os
import uuid
import hashlib
import logging
from typing import List

from pypdf import PdfReader
from langchain_groq import ChatGroq
from core.config import GROQ_API_KEY, MODEL_NAME, CHROMA_DB_PATH, LOGS_PATH
from departments.library.state import LibraryState
import chromadb

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs(LOGS_PATH, exist_ok=True)
logger = logging.getLogger("library.ingestion")

# ── ChromaDB ─────────────────────────────────────────────────────────────────
_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
BOOKS_COLLECTION = "library_books"


def _get_books_collection():
    return _chroma_client.get_or_create_collection(
        name=BOOKS_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )


# ── Node 1: extract_text ──────────────────────────────────────────────────────

def extract_text(state: LibraryState) -> dict:
    """
    Node 1 of the ingestion pipeline.
    Reads a PDF or EPUB and extracts raw text + metadata.

    Supports:
        - PDF  (via pypdf)
        - EPUB (via ebooklib + html2text)
        - TXT  (plain read)
    """
    file_path = state.get("file_path")

    if not file_path or not os.path.exists(file_path):
        return {
            "ingestion_status": "failed",
            "ingestion_error": f"File not found: {file_path}",
        }

    ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)
    logger.info(f"Extracting text from: {filename} ({ext})")

    try:
        if ext == ".pdf":
            return _extract_pdf(file_path, filename)

        elif ext == ".epub":
            return _extract_epub(file_path, filename)

        elif ext == ".txt":
            return _extract_txt(file_path, filename)

        else:
            return {
                "ingestion_status": "failed",
                "ingestion_error": f"Unsupported format: {ext}. Supported: .pdf, .epub, .txt",
            }

    except Exception as e:
        logger.error(f"Extraction failed for {filename}: {e}")
        return {
            "ingestion_status": "failed",
            "ingestion_error": str(e),
        }


def _extract_pdf(file_path: str, filename: str) -> dict:
    reader = PdfReader(file_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text.strip())

    raw_text = "\n\n".join(pages_text)

    # Try to extract title from PDF metadata
    meta = reader.metadata or {}
    title = meta.get("/Title", filename.replace(".pdf", "")).strip() or filename
    author = meta.get("/Author", "Unknown").strip()

    return {
        "raw_text": raw_text,
        "book_metadata": {
            "title": title,
            "author": author,
            "source": file_path,
            "pages": len(reader.pages),
            "format": "pdf",
            "filename": filename,
        },
    }


def _extract_epub(file_path: str, filename: str) -> dict:
    try:
        import ebooklib
        from ebooklib import epub
        import html2text
    except ImportError:
        return {
            "ingestion_status": "failed",
            "ingestion_error": "ebooklib and html2text required. Run: pip install ebooklib html2text",
        }

    book = epub.read_epub(file_path)
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True

    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="ignore")
        text = converter.handle(content).strip()
        if len(text) > 50:  # skip tiny/empty chapters
            chapters.append(text)

    raw_text = "\n\n".join(chapters)

    # EPUB metadata
    title = book.get_metadata("DC", "title")
    author = book.get_metadata("DC", "creator")
    title = title[0][0] if title else filename.replace(".epub", "")
    author = author[0][0] if author else "Unknown"

    return {
        "raw_text": raw_text,
        "book_metadata": {
            "title": title,
            "author": author,
            "source": file_path,
            "pages": len(chapters),
            "format": "epub",
            "filename": filename,
        },
    }


def _extract_txt(file_path: str, filename: str) -> dict:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    return {
        "raw_text": raw_text,
        "book_metadata": {
            "title": filename.replace(".txt", ""),
            "author": "Unknown",
            "source": file_path,
            "pages": raw_text.count("\n\n"),
            "format": "txt",
            "filename": filename,
        },
    }


# ── Node 2: chunk_text ────────────────────────────────────────────────────────

CHUNK_SIZE    = 500    # words per chunk
CHUNK_OVERLAP = 80     # word overlap between consecutive chunks

def chunk_text(state: LibraryState) -> dict:
    """
    Node 2 of the ingestion pipeline.
    Splits raw text into overlapping chunks for embedding.

    Uses word-level splitting with overlap so context is never lost
    at chunk boundaries.
    """
    raw_text = state.get("raw_text", "")
    metadata = state.get("book_metadata", {})

    if not raw_text:
        return {
            "ingestion_status": "failed",
            "ingestion_error": "No text to chunk — extraction may have failed.",
        }

    # Deduplicate whitespace
    import re
    raw_text = re.sub(r'\s+', ' ', raw_text).strip()

    words = raw_text.split()
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunk_words = words[start:end]
        chunk_text_str = " ".join(chunk_words)

        # Unique ID: hash of (title + chunk_index) so re-ingesting same book
        # produces the same IDs → ChromaDB upsert is idempotent
        chunk_id = hashlib.md5(
            f"{metadata.get('title', '')}_chunk_{chunk_index}".encode()
        ).hexdigest()

        chunks.append({
            "text": chunk_text_str,
            "chunk_id": chunk_id,
            "metadata": {
                "book_title":  metadata.get("title", "Unknown"),
                "book_author": metadata.get("author", "Unknown"),
                "source":      metadata.get("source", ""),
                "format":      metadata.get("format", ""),
                "chunk_index": chunk_index,
                "word_count":  len(chunk_words),
            },
        })

        chunk_index += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP  # slide with overlap

    logger.info(
        f"Chunked '{metadata.get('title')}' → {len(chunks)} chunks "
        f"(~{CHUNK_SIZE} words each, {CHUNK_OVERLAP} overlap)"
    )
    return {"chunks": chunks}


# ── Node 3: embed_and_store ───────────────────────────────────────────────────

BATCH_SIZE = 50   # ChromaDB upsert batch size

def embed_and_store(state: LibraryState) -> dict:
    """
    Node 3 of the ingestion pipeline.
    Embeds all chunks and stores them in ChromaDB.

    ChromaDB handles the embedding internally using its default
    sentence-transformers model (all-MiniLM-L6-v2) — no extra API cost.
    Upsert is idempotent: re-ingesting the same book is safe.
    """
    chunks = state.get("chunks", [])
    metadata = state.get("book_metadata", {})

    if not chunks:
        return {
            "ingestion_status": "failed",
            "ingestion_error": "No chunks to embed.",
        }

    collection = _get_books_collection()
    title = metadata.get("title", "Unknown")

    # Check if this book is already fully ingested
    existing = collection.get(where={"book_title": title})
    if existing and len(existing["ids"]) >= len(chunks) * 0.9:
        logger.info(f"Book '{title}' already in library. Skipping re-ingestion.")
        return {
            "ingestion_status": "already_exists",
            "ingestion_error": None,
        }

    # Batch upsert
    try:
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            collection.upsert(
                documents=[c["text"] for c in batch],
                metadatas=[c["metadata"] for c in batch],
                ids=[c["chunk_id"] for c in batch],
            )
            logger.info(f"  Stored batch {i//BATCH_SIZE + 1}: chunks {i}–{i+len(batch)-1}")

        logger.info(f"✓ '{title}' fully ingested: {len(chunks)} chunks stored.")
        return {
            "ingestion_status": "success",
            "ingestion_error": None,
        }

    except Exception as e:
        logger.error(f"ChromaDB store failed for '{title}': {e}")
        return {
            "ingestion_status": "failed",
            "ingestion_error": str(e),
        }
