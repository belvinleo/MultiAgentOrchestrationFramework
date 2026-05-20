"""
departments/library/library_manager.py
----------------------------------------
The Library Department Head — the bridge between LifeOS's existing
orchestrator/registry system and the new LangGraph-powered library.

This is what the orchestrator calls when a message is routed to
'Ministry of Knowledge'. It:
  1. Parses the user's intent (ingest / query / list / summary)
  2. Delegates to the appropriate LangGraph pipeline
  3. Returns a formatted string response the orchestrator can use

It also exposes the folder watcher for the Scheduler to hook into.

Integration with existing LifeOS:
  - Inherits from BaseAgent (constitution-aware, Groq-powered)
  - Works with DepartmentFactory via config.yaml
  - Plugs into ProactiveEngine via get_proactive_insight()
  - Plugs into Scheduler via start_folder_watcher()
"""

import os
import logging
from core.base_agent import BaseAgent
from core.config import BASE_DIR
from departments.library.library_graph import run_ingestion, run_query, run_insight
from departments.library.insight_agent import list_books, book_summary

logger = logging.getLogger("library.manager")

# Default folder to watch for new books
DEFAULT_BOOKS_FOLDER = os.path.join(os.path.expanduser("~"), "Books")


class LibraryManager(BaseAgent):
    """
    The Library Department's supervisor agent.
    Routed to by the orchestrator when messages match 'Ministry of Knowledge'.

    Also provides:
        start_folder_watcher()    → call from main.py Scheduler
        get_proactive_insight()   → call from ProactiveEngine
    """

    def __init__(self, books_folder: str = DEFAULT_BOOKS_FOLDER):
        super().__init__(
            name="Library Manager",
            role="Supervisor of the Ministry of Knowledge. Manages book ingestion, queries, and insights.",
            domain="books, reading, knowledge, research, learning, philosophy, science",
            extra_prompt="""
You are the Library Manager inside LifeOS.
You have access to Belvin's personal library — a RAG database of books he has ingested.

When Belvin asks a question:
- If it's about a book topic, query the library and surface relevant passages
- If he wants to add a book, guide him on how to use the ingest command
- If he wants to know what's in his library, list the books
- If he wants a summary, generate one from stored content

Always be intellectually rich, cite sources from the library, and suggest connections.
"""
        )
        self.books_folder = books_folder
        os.makedirs(books_folder, exist_ok=True)

    def think(self, user_message: str, context: dict = None) -> str:
        """
        Override BaseAgent.think() to route through LangGraph pipelines
        instead of calling Groq directly.

        The orchestrator calls this method — it expects a string back.
        """
        msg = user_message.lower().strip()

        # ── Intent: ingest a specific file ───────────────────────────────────
        if any(kw in msg for kw in ["ingest", "add book", "add this book", "load book"]):
            # Extract file path if mentioned
            file_path = self._extract_file_path(user_message)
            if file_path:
                return self._handle_ingestion(file_path)
            else:
                return (
                    f"To add a book to your library, drop the PDF or EPUB into:\n"
                    f"  {self.books_folder}\n\n"
                    f"The folder watcher will automatically ingest it. "
                    f"Or type: 'ingest /path/to/your/book.pdf'"
                )

        # ── Intent: list books ────────────────────────────────────────────────
        if any(kw in msg for kw in ["list books", "my library", "what books", "show books", "library books"]):
            return self._handle_list_books()

        # ── Intent: book summary ──────────────────────────────────────────────
        if "summary" in msg or "summarize" in msg:
            # Try to extract book title from message
            title = self._extract_book_title(user_message)
            if title:
                return self._handle_summary(title)
            else:
                books = list_books()
                if not books:
                    return "Your library is empty. Add books to get summaries."
                book_list = "\n".join([f"- {b['title']} by {b['author']}" for b in books[:10]])
                return f"Which book would you like a summary of?\n\n{book_list}"

        # ── Intent: knowledge query (default) ────────────────────────────────
        return self._handle_query(user_message)

    def _handle_ingestion(self, file_path: str) -> str:
        result = run_ingestion(file_path)
        status = result.get("ingestion_status")
        meta = result.get("book_metadata") or {}
        error = result.get("ingestion_error")

        if status == "success":
            chunks = result.get("chunks") or []
            return (
                f"✓ '{meta.get('title', 'Book')}' by {meta.get('author', 'Unknown')} "
                f"has been added to your library.\n"
                f"  {len(chunks)} knowledge chunks stored | Format: {meta.get('format', '?').upper()}\n\n"
                f"You can now ask me anything about it."
            )
        elif status == "already_exists":
            return f"'{meta.get('title', 'This book')}' is already in your library."
        else:
            return f"Ingestion failed: {error}"

    def _handle_query(self, query: str) -> str:
        result = run_query(query)
        return result.get("answer", "I could not find an answer in your library.")

    def _handle_list_books(self) -> str:
        books = list_books()
        if not books:
            return (
                "Your library is empty. Add books by dropping PDFs or EPUBs into:\n"
                f"  {self.books_folder}\n\n"
                "The folder watcher will automatically ingest them."
            )
        lines = [f"📚 Your Library ({len(books)} books)\n"]
        for b in books:
            lines.append(f"  • {b['title']}  —  {b['author']}  [{b['format'].upper()}]")
        return "\n".join(lines)

    def _handle_summary(self, title: str) -> str:
        return book_summary(title)

    def _extract_file_path(self, message: str) -> str | None:
        """Extract a file path from a message if one is present."""
        import re
        # Match /path/to/file.pdf or ~/Books/file.epub etc.
        match = re.search(r'([~/][\w\-./\\]+\.(pdf|epub|txt))', message, re.IGNORECASE)
        if match:
            path = match.group(1)
            return os.path.expanduser(path)
        return None

    def _extract_book_title(self, message: str) -> str | None:
        """Try to match a known book title from the message."""
        books = list_books()
        msg_lower = message.lower()
        for book in books:
            if book["title"].lower() in msg_lower:
                return book["title"]
        return None

    # ── Folder Watcher ────────────────────────────────────────────────────────

    def start_folder_watcher(self):
        """
        Starts a watchdog observer that monitors the Books folder.
        When a new PDF/EPUB/TXT is dropped in, it auto-ingests.

        Called from main.py via the Scheduler or as a standalone thread.
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            manager = self  # capture self for the handler

            class BookHandler(FileSystemEventHandler):
                SUPPORTED = {".pdf", ".epub", ".txt"}

                def on_created(self, event):
                    if event.is_directory:
                        return
                    ext = os.path.splitext(event.src_path)[1].lower()
                    if ext in self.SUPPORTED:
                        logger.info(f"New book detected: {event.src_path}")
                        result = run_ingestion(event.src_path)
                        status = result.get("ingestion_status")
                        meta = result.get("book_metadata") or {}
                        if status == "success":
                            logger.info(f"Auto-ingested: {meta.get('title')}")
                        else:
                            logger.error(f"Auto-ingest failed: {result.get('ingestion_error')}")

            observer = Observer()
            observer.schedule(BookHandler(), self.books_folder, recursive=False)
            observer.start()
            logger.info(f"Folder watcher started: {self.books_folder}")
            return observer

        except ImportError:
            logger.warning("watchdog not installed. Folder watcher disabled.")
            return None

    # ── ProactiveEngine integration ───────────────────────────────────────────

    def get_proactive_insight(self, trigger: str = "") -> str:
        """
        Called by ProactiveEngine to get a library insight for Belvin.
        Returns a short insight string ready for the alert queue.
        """
        result = run_insight(trigger)
        return result.get("insight_result", "")
