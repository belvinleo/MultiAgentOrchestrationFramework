# Ministry of Knowledge — Library Department

A LangGraph-powered RAG library integrated into LifeOS.
Ingests books, answers questions from them, and proactively surfaces insights.

---

## Architecture

```
departments/library/
├── state.py             # LibraryState TypedDict — flows through the graph
├── ingestion_agent.py   # Nodes: extract_text → chunk_text → embed_and_store
├── query_agent.py       # Nodes: retrieve_chunks → generate_answer
├── insight_agent.py     # Node: generate_insight + list_books() + book_summary()
├── library_graph.py     # LangGraph StateGraph wiring all three pipelines
├── library_manager.py   # Department head — bridges to existing LifeOS orchestrator
├── config.yaml          # Department registration for DepartmentRegistry
└── __init__.py
```

## LangGraph Pipeline

```
          ┌─────────────────────────────────────┐
          │         LibraryState (shared)        │
          └─────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   [file_path?]      [query?]     [insight_trigger?]
          │               │               │
   INGESTION          QUERY           INSIGHT
   PIPELINE           PIPELINE        PIPELINE
          │               │               │
   extract_text    retrieve_chunks  generate_insight
          │               │               │
   chunk_text      generate_answer       END
          │               │
   embed_and_store        END
          │
         END
```

## CLI Commands

| Command | What it does |
|---|---|
| `ingest ~/Books/atomic_habits.pdf` | Ingest a book into the library |
| `library books` | List all ingested books |
| `summarize Atomic Habits` | Generate a summary of a specific book |
| Any question | Queries the library via RAG |

## Folder Watcher

Drop any `.pdf`, `.epub`, or `.txt` into `~/Books/` and it will be automatically
ingested in the background. No manual command needed.

## Supported Formats

- **PDF** — via `pypdf`
- **EPUB** — via `ebooklib` + `html2text`
- **TXT** — plain text files

## Install Dependencies

```bash
pip install langgraph langchain langchain-groq langchain-community \
            chromadb pypdf ebooklib html2text watchdog
```

## How RAG Works Here

1. Books are chunked into ~500-word overlapping segments
2. ChromaDB embeds and stores each chunk (using `all-MiniLM-L6-v2`)
3. When you ask a question, your query is embedded and the closest chunks are retrieved
4. Groq (Llama3) receives the retrieved chunks as context and generates a grounded answer
5. The answer always cites the source book — no fabrication

## Proactive Insights

Every 4 hours, the Scheduler triggers `generate_insight()` which:
- Picks a random theme (mental models, habits, philosophy, etc.)
- Retrieves relevant passages across ALL your books
- Synthesizes a short, actionable insight
- Queues it as a LifeOS alert (shown between your messages)
