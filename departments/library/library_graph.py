"""
departments/library/library_graph.py
--------------------------------------
The LangGraph StateGraph that wires all Library agent nodes together.

Three pipelines, one graph:

  INGESTION pipeline:
    extract_text → chunk_text → embed_and_store

  QUERY pipeline:
    retrieve_chunks → generate_answer

  INSIGHT pipeline:
    generate_insight

The entry point is decided by which fields are populated in LibraryState:
  - file_path present      → ingestion pipeline
  - query present          → query pipeline
  - insight_trigger present → insight pipeline

Each pipeline is independent — they share the same ChromaDB
collection but don't interfere with each other.

Usage:
    from departments.library.library_graph import run_ingestion, run_query, run_insight
"""

from langgraph.graph import StateGraph, END

from departments.library.state import LibraryState
from departments.library.ingestion_agent import extract_text, chunk_text, embed_and_store
from departments.library.query_agent import retrieve_chunks, generate_answer
from departments.library.insight_agent import generate_insight


# ── Route function ────────────────────────────────────────────────────────────

def _route_entry(state: LibraryState) -> str:
    """
    Decides which pipeline to execute based on what's in the state.
    This is the conditional edge from the START node.
    """
    if state.get("file_path"):
        return "extract_text"
    elif state.get("query"):
        return "retrieve_chunks"
    elif state.get("insight_trigger") is not None:  # can be empty string
        return "generate_insight"
    else:
        return END


# ── Build the graph ───────────────────────────────────────────────────────────

def build_library_graph() -> StateGraph:
    """
    Constructs and compiles the Library StateGraph.
    Call once at startup and cache the result.
    """
    graph = StateGraph(LibraryState)

    # ── Register all nodes ──────────────────────────────────────────────────
    # Ingestion pipeline
    graph.add_node("extract_text",    extract_text)
    graph.add_node("chunk_text",      chunk_text)
    graph.add_node("embed_and_store", embed_and_store)

    # Query pipeline
    graph.add_node("retrieve_chunks", retrieve_chunks)
    graph.add_node("generate_answer", generate_answer)

    # Insight pipeline
    graph.add_node("generate_insight", generate_insight)

    # ── Entry point: conditional routing ───────────────────────────────────
    graph.set_conditional_entry_point(
        _route_entry,
        {
            "extract_text":    "extract_text",
            "retrieve_chunks": "retrieve_chunks",
            "generate_insight":"generate_insight",
            END:               END,
        }
    )

    # ── Ingestion pipeline edges ────────────────────────────────────────────
    graph.add_edge("extract_text",    "chunk_text")
    graph.add_edge("chunk_text",      "embed_and_store")
    graph.add_edge("embed_and_store", END)

    # ── Query pipeline edges ────────────────────────────────────────────────
    graph.add_edge("retrieve_chunks", "generate_answer")
    graph.add_edge("generate_answer", END)

    # ── Insight pipeline edges ──────────────────────────────────────────────
    graph.add_edge("generate_insight", END)

    return graph.compile()


# ── Compiled graph singleton ──────────────────────────────────────────────────
# Import and use this directly — don't call build_library_graph() every time.
library_graph = build_library_graph()


# ── Convenience runners ───────────────────────────────────────────────────────

def run_ingestion(file_path: str) -> dict:
    """
    Ingest a book into the library.

    Args:
        file_path: absolute or relative path to a .pdf, .epub, or .txt file

    Returns:
        Final state dict with ingestion_status and book_metadata
    """
    initial_state: LibraryState = {
        "file_path":       file_path,
        "query":           None,
        "insight_trigger": None,
        "raw_text":        None,
        "book_metadata":   None,
        "chunks":          None,
        "ingestion_status": None,
        "ingestion_error": None,
        "retrieved_chunks": None,
        "answer":          None,
        "insight_result":  None,
        "error":           None,
    }
    return library_graph.invoke(initial_state)


def run_query(query: str) -> dict:
    """
    Query the library with a natural language question.

    Args:
        query: the user's question

    Returns:
        Final state dict with answer and retrieved_chunks
    """
    initial_state: LibraryState = {
        "file_path":       None,
        "query":           query,
        "insight_trigger": None,
        "raw_text":        None,
        "book_metadata":   None,
        "chunks":          None,
        "ingestion_status": None,
        "ingestion_error": None,
        "retrieved_chunks": None,
        "answer":          None,
        "insight_result":  None,
        "error":           None,
    }
    return library_graph.invoke(initial_state)


def run_insight(trigger: str = "") -> dict:
    """
    Generate a proactive insight from the library.
    Called by the LifeOS Scheduler on a schedule.

    Args:
        trigger: optional topic hint (empty = random theme)

    Returns:
        Final state dict with insight_result
    """
    initial_state: LibraryState = {
        "file_path":       None,
        "query":           None,
        "insight_trigger": trigger,
        "raw_text":        None,
        "book_metadata":   None,
        "chunks":          None,
        "ingestion_status": None,
        "ingestion_error": None,
        "retrieved_chunks": None,
        "answer":          None,
        "insight_result":  None,
        "error":           None,
    }
    return library_graph.invoke(initial_state)
