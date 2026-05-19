"""
registry.py
-----------
The Department Registry.
Indexes all available departments and routes messages to the right ones
using semantic similarity — not hardcoded if/else logic.
This is what makes LifeOS scale to 250 departments cleanly.
"""

import os
import yaml
import chromadb
from core.department_factory import DepartmentFactory
from core.config import CHROMA_DB_PATH


class DepartmentRegistry:
    """
    Maintains an index of all departments.
    Routes any message to the top-N most relevant departments.

    How it works:
    1. At startup, scan all department config.yaml files
    2. Embed each department's name + domain + keywords into ChromaDB
    3. When a message arrives, embed it and find closest departments
    4. Return the top matches above a confidence threshold
    """

    def __init__(self):
        self.factory = DepartmentFactory()
        self.chroma = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.chroma.get_or_create_collection("department_registry")
        self._department_map = {}  # name → config path

    def register(self, config_path: str):
        """
        Register a single department into the registry index.

        Parameters:
            config_path : path to the department's config.yaml
        """
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        name = config["name"]
        domain = config["domain"]
        keywords = " ".join(config.get("keywords", []))

        # The text we embed = name + domain + keywords
        index_text = f"{name}. {domain}. {keywords}"

        # Store in ChromaDB
        self.collection.upsert(
            documents=[index_text],
            metadatas=[{"config_path": config_path, "name": name}],
            ids=[name]
        )

        self._department_map[name] = config_path

    def register_all(self, departments_root: str = "departments"):
        """
        Scan the departments folder and register every department found.
        Call this once at startup.

        Parameters:
            departments_root : the root folder containing all department subfolders
        """
        registered = 0
        for dept_folder in os.listdir(departments_root):
            config_path = os.path.join(departments_root, dept_folder, "config.yaml")
            if os.path.exists(config_path):
                self.register(config_path)
                registered += 1

        return registered

    def route(self, message: str, top_k: int = 3, threshold: float = 0.4) -> list:
        """
        Find the most relevant departments for a given message.

        Parameters:
            message   : the user's input
            top_k     : max departments to return
            threshold : minimum relevance score (0-1). Below this = ignored.

        Returns:
            List of (department_name, config_path, score) tuples
        """
        if not self._department_map:
            return []

        results = self.collection.query(
            query_texts=[message],
            n_results=min(top_k, len(self._department_map))
        )

        if not results["documents"][0]:
            return []

        matches = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i]
            # ChromaDB returns distances (lower = more similar)
            # Convert to a 0-1 similarity score
            distance = results["distances"][0][i]
            score = max(0, 1 - distance)

            if score >= threshold:
                matches.append({
                    "name": metadata["name"],
                    "config_path": metadata["config_path"],
                    "score": round(score, 3)
                })

        return sorted(matches, key=lambda x: x["score"], reverse=True)

    def get_agent(self, department_name: str):
        """
        Load and return the agent for a registered department.
        """
        config_path = self._department_map.get(department_name)
        if not config_path:
            raise ValueError(f"Department '{department_name}' not found in registry.")
        return self.factory.create(config_path)

    def list_all(self) -> list:
        """Returns names of all registered departments."""
        return list(self._department_map.keys())