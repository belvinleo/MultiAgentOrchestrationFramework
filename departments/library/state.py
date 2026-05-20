"""
departments/library/state.py
-----------------------------
Shared state object for the Library LangGraph pipeline.
Every node reads from and writes to this TypedDict.
Think of it as the "memory" that flows through the graph.
"""

from typing import TypedDict, Optional, List


class LibraryState(TypedDict):
    """
    The single state object that flows through the entire Library graph.

    Ingestion pipeline:
        file_path       → raw text → chunks → embeddings stored in ChromaDB

    Query pipeline:
        query           → retrieved chunks → answer

    Insight pipeline:
        insight_trigger → synthesis → insight_result
    """

    # ── Input ────────────────────────────────────────────────────────────────
    file_path: Optional[str]           # path to a PDF or EPUB to ingest
    query: Optional[str]               # user's question to the library
    insight_trigger: Optional[str]     # topic to generate proactive insight on

    # ── Ingestion pipeline ───────────────────────────────────────────────────
    raw_text: Optional[str]            # full extracted text from the book
    book_metadata: Optional[dict]      # {title, author, source, pages, format}
    chunks: Optional[List[dict]]       # [{text, chunk_id, metadata}, ...]
    ingestion_status: Optional[str]    # "success" | "failed" | "already_exists"
    ingestion_error: Optional[str]     # error message if ingestion failed

    # ── Query pipeline ───────────────────────────────────────────────────────
    retrieved_chunks: Optional[List[dict]]   # top-k chunks from ChromaDB
    answer: Optional[str]                    # final answer to user's query

    # ── Insight pipeline ─────────────────────────────────────────────────────
    insight_result: Optional[str]            # synthesized proactive insight

    # ── Shared ───────────────────────────────────────────────────────────────
    error: Optional[str]               # any fatal error (stops the graph)
