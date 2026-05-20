"""
departments/library/query_agent.py
------------------------------------
LangGraph nodes for the query pipeline.

Flow:
    retrieve_chunks → generate_answer

Given a natural language question, this pipeline:
1. Embeds the query and retrieves the most relevant book chunks from ChromaDB
2. Feeds those chunks to Groq (Llama3) to generate a grounded answer

The agent ONLY answers from retrieved chunks — it never fabricates.
If nothing is found, it says so clearly.
"""

import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from core.config import GROQ_API_KEY, MODEL_NAME, CHROMA_DB_PATH
from departments.library.state import LibraryState
import chromadb

logger = logging.getLogger("library.query")

# ── ChromaDB ──────────────────────────────────────────────────────────────────
_chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
BOOKS_COLLECTION = "library_books"

def _get_books_collection():
    return _chroma_client.get_or_create_collection(
        name=BOOKS_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )

# ── LLM ───────────────────────────────────────────────────────────────────────
_llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL_NAME, temperature=0.3)

TOP_K = 5   # number of chunks to retrieve


# ── Node 1: retrieve_chunks ───────────────────────────────────────────────────

def retrieve_chunks(state: LibraryState) -> dict:
    """
    Node 1 of the query pipeline.
    Embeds the user's query and retrieves the top-K most relevant
    chunks from the library's ChromaDB collection.

    Returns chunks with their source book info so the answer
    agent can cite them.
    """
    query = state.get("query", "").strip()
    if not query:
        return {"retrieved_chunks": [], "error": "No query provided."}

    try:
        collection = _get_books_collection()
        total_docs = collection.count()

        if total_docs == 0:
            logger.info("Library is empty — no books ingested yet.")
            return {"retrieved_chunks": []}

        results = collection.query(
            query_texts=[query],
            n_results=min(TOP_K, total_docs),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                score = max(0.0, 1.0 - distance)
                meta = results["metadatas"][0][i]

                chunks.append({
                    "text": doc,
                    "score": round(score, 3),
                    "book_title":  meta.get("book_title", "Unknown"),
                    "book_author": meta.get("book_author", "Unknown"),
                    "chunk_index": meta.get("chunk_index", 0),
                })

        # Sort by relevance score
        chunks.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"Retrieved {len(chunks)} chunks for query: '{query[:60]}'")
        return {"retrieved_chunks": chunks}

    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {"retrieved_chunks": [], "error": str(e)}


# ── Node 2: generate_answer ───────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are the Library Agent inside LifeOS — Belvin's personal AI knowledge system.

Your job is to answer questions ONLY using the book excerpts provided below.
Do not fabricate information. If the excerpts don't contain enough to answer,
say so honestly and suggest which type of book might cover the topic.

Always:
- Cite the book title and author when referencing a passage
- Be concise but complete — lead with the direct answer
- Connect ideas across different books when relevant
- End with one actionable insight or follow-up suggestion for Belvin

You are talking to Belvin directly. Be warm, intellectual, and precise.
"""

def generate_answer(state: LibraryState) -> dict:
    """
    Node 2 of the query pipeline.
    Uses retrieved chunks as context to generate a grounded answer
    via Groq (Llama3). The LLM is prompted to cite sources and
    never go beyond the provided context.
    """
    query = state.get("query", "")
    chunks = state.get("retrieved_chunks", [])

    if not chunks:
        return {
            "answer": (
                "Your library doesn't have any books ingested yet, or none of your "
                "current books cover this topic. Try adding a relevant book using "
                "the 'ingest' command — drop it in your ~/Books/ folder."
            )
        }

    # Build context block from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Excerpt {i} — '{chunk['book_title']}' by {chunk['book_author']}]\n"
            f"{chunk['text']}"
        )
    context_block = "\n\n---\n\n".join(context_parts)

    human_message = (
        f"BOOK EXCERPTS FROM BELVIN'S LIBRARY:\n\n"
        f"{context_block}\n\n"
        f"---\n\n"
        f"BELVIN'S QUESTION: {query}"
    )

    try:
        response = _llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_message),
        ])
        answer = response.content
        logger.info(f"Generated answer for: '{query[:60]}'")
        return {"answer": answer}

    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        return {"answer": f"[Library Agent Error] Could not generate answer: {e}"}
