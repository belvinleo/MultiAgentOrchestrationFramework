"""
departments/library/insight_agent.py
--------------------------------------
LangGraph node for the proactive insight pipeline.

This agent runs on a schedule (via LifeOS Scheduler) and:
1. Scans what books are in the library
2. Picks a topic or theme to synthesize
3. Generates a short, valuable insight for Belvin

It's the "you can't read every book" problem solved:
the insight agent reads across all your books and surfaces
connections, patterns, and wisdom you'd otherwise miss.

Also provides:
    - list_books()  : what's in the library
    - book_summary(): quick summary of a specific book
"""

import logging
import random
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from core.config import GROQ_API_KEY, MODEL_NAME, CHROMA_DB_PATH
from departments.library.state import LibraryState
import chromadb

logger = logging.getLogger("library.insight")

_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
BOOKS_COLLECTION = "library_books"

def _get_books_collection():
    return _chroma_client.get_or_create_collection(
        name=BOOKS_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )

_llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL_NAME, temperature=0.6)


# ── Utility: list all books in the library ────────────────────────────────────

def list_books() -> list[dict]:
    """
    Returns metadata for all unique books currently in the library.
    Used by the CLI 'library books' command and the insight agent.
    """
    try:
        collection = _get_books_collection()
        if collection.count() == 0:
            return []

        # Get all metadata (no documents, just metadata for efficiency)
        results = collection.get(include=["metadatas"])
        seen_titles = set()
        books = []

        for meta in results["metadatas"]:
            title = meta.get("book_title", "Unknown")
            if title not in seen_titles:
                seen_titles.add(title)
                books.append({
                    "title":  title,
                    "author": meta.get("book_author", "Unknown"),
                    "format": meta.get("format", "unknown"),
                    "source": meta.get("source", ""),
                })

        return sorted(books, key=lambda x: x["title"])

    except Exception as e:
        logger.error(f"list_books failed: {e}")
        return []


# ── Utility: get book summary ─────────────────────────────────────────────────

def book_summary(title: str) -> str:
    """
    Generates a concise summary of a specific book from its stored chunks.
    Pulls the first few chunks (intro material) and asks the LLM to summarize.
    """
    try:
        collection = _get_books_collection()
        results = collection.get(
            where={"book_title": title},
            include=["documents", "metadatas"],
        )

        if not results["ids"]:
            return f"'{title}' not found in your library."

        # Sort by chunk index, take first 5 (intro/early material)
        paired = sorted(
            zip(results["metadatas"], results["documents"]),
            key=lambda x: x[0].get("chunk_index", 0)
        )
        sample_chunks = [doc for _, doc in paired[:5]]
        context = "\n\n---\n\n".join(sample_chunks)

        author = paired[0][0].get("book_author", "Unknown")

        response = _llm.invoke([
            SystemMessage(content=(
                "You are the Library Agent in LifeOS. Summarize the following book "
                "excerpts into a clear, useful 3-5 sentence summary. Include: "
                "what the book is about, its core argument or insight, and why it "
                "might be valuable to read. Be concise and direct."
            )),
            HumanMessage(content=(
                f"Book: '{title}' by {author}\n\n"
                f"Excerpts:\n{context}\n\n"
                f"Provide a 3-5 sentence summary."
            )),
        ])
        return response.content

    except Exception as e:
        logger.error(f"book_summary failed for '{title}': {e}")
        return f"Could not generate summary for '{title}': {e}"


# ── Node: generate_insight ────────────────────────────────────────────────────

# Rotating insight themes — cycles through these on each proactive run
INSIGHT_THEMES = [
    "key life principles or mental models",
    "decision-making and avoiding cognitive biases",
    "habits, productivity, and deep work",
    "wealth, money, and financial independence",
    "human psychology and relationships",
    "creativity, learning, and skill acquisition",
    "philosophy of a good life and meaning",
    "leadership, communication, and influence",
    "health, longevity, and peak performance",
    "technology, AI, and the future",
]

INSIGHT_SYSTEM_PROMPT = """\
You are the Library Insight Agent in LifeOS — Belvin's personal knowledge synthesis engine.

Your job is to generate a short, genuinely valuable insight from Belvin's library.
The insight must:
- Be under 80 words
- Connect ideas from at least 2 different books if possible
- Lead with the most surprising or useful idea
- End with one concrete action Belvin can take today
- Feel like a message from a brilliant friend, not a textbook

Never be generic. Every insight should feel personal and immediately useful.
"""

def generate_insight(state: LibraryState) -> dict:
    """
    Proactive insight node.
    Picks a random theme, retrieves relevant chunks across all books,
    and synthesizes a short insight for Belvin.

    Called by the LifeOS Scheduler every few hours.
    Result goes into the ProactiveEngine alert queue.
    """
    trigger = state.get("insight_trigger") or random.choice(INSIGHT_THEMES)

    try:
        collection = _get_books_collection()
        if collection.count() == 0:
            return {
                "insight_result": (
                    "Your library is empty. Add your first book by dropping a PDF or EPUB "
                    "into your Books folder — the ingestion agent will handle the rest."
                )
            }

        # Retrieve relevant chunks for this theme
        results = collection.query(
            query_texts=[trigger],
            n_results=min(6, collection.count()),
            include=["documents", "metadatas"],
        )

        if not results["documents"] or not results["documents"][0]:
            return {"insight_result": "Not enough library content yet to generate insights."}

        # Build context
        context_parts = []
        for i, (doc, meta) in enumerate(
            zip(results["documents"][0], results["metadatas"][0]), 1
        ):
            context_parts.append(
                f"[From '{meta.get('book_title', 'Unknown')}' by {meta.get('book_author', 'Unknown')}]\n{doc}"
            )
        context = "\n\n---\n\n".join(context_parts)

        response = _llm.invoke([
            SystemMessage(content=INSIGHT_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"THEME: {trigger}\n\n"
                f"LIBRARY EXCERPTS:\n{context}\n\n"
                f"Generate one powerful insight for Belvin on this theme."
            )),
        ])

        insight = response.content
        logger.info(f"Generated insight on theme: '{trigger}'")
        return {"insight_result": insight}

    except Exception as e:
        logger.error(f"Insight generation failed: {e}")
        return {"insight_result": f"[Insight Agent Error] {e}"}
