"""
memory.py
---------
Two-layer memory for LifeOS:
- Short-term : current session (Python dict, lives in RAM)
- Long-term  : persistent vector store (ChromaDB, lives on disk)
"""

import chromadb
from datetime import datetime
from core.config import CHROMA_DB_PATH


class ShortTermMemory:
    """
    Session-level memory. Cleared when LifeOS restarts.
    Stores current context: mood, recent topics, active departments.
    """

    def __init__(self):
        self._store = {}

    def set(self, key: str, value):
        self._store[key] = value

    def get(self, key: str, default=None):
        return self._store.get(key, default)

    def update_context(self, updates: dict):
        """Merge a dict of updates into memory."""
        self._store.update(updates)

    def get_all(self) -> dict:
        return dict(self._store)

    def clear(self):
        self._store = {}


class LongTermMemory:
    """
    Persistent vector memory using ChromaDB.
    Stores facts, insights, and knowledge that survive restarts.
    Each department has its own namespace (collection).
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    def store(self, namespace: str, content: str, metadata: dict = None):
        """
        Store a piece of knowledge in a namespace.

        Parameters:
            namespace : department name e.g. 'health', 'finance'
            content   : the text to store
            metadata  : optional tags like source, date, type
        """
        collection = self.client.get_or_create_collection(name=namespace)
        doc_id = f"{namespace}_{datetime.now().timestamp()}"
        collection.add(
            documents=[content],
            metadatas=[metadata or {"stored_at": str(datetime.now())}],
            ids=[doc_id]
        )

    def search(self, namespace: str, query: str, top_k: int = 3) -> list:
        """
        Retrieve the most relevant stored knowledge for a query.

        Returns list of matching text strings.
        """
        try:
            collection = self.client.get_or_create_collection(name=namespace)
            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )
            return results["documents"][0] if results["documents"] else []
        except Exception:
            return []

    def list_namespaces(self) -> list:
        """Returns all existing namespaces (departments with stored memory)."""
        return [col.name for col in self.client.list_collections()]


# Global memory instances — imported by any agent that needs them
short_term = ShortTermMemory()
long_term = LongTermMemory()