"""
config.py
---------
Loads environment variables and constitution.
Every agent imports this to access system-wide settings.
"""

import os
import yaml
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# API settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3-70b-8192")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTITUTION_PATH = os.path.join(BASE_DIR, "constitution", "constitution.yaml")
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")
LOGS_PATH = os.path.join(BASE_DIR, "logs")


def load_constitution() -> dict:
    """Load and return the constitution as a dictionary."""
    with open(CONSTITUTION_PATH, "r") as f:
        return yaml.safe_load(f)


def get_hard_laws(constitution: dict) -> str:
    """Extract hard laws as a formatted string for agent system prompts."""
    laws = constitution.get("hard_laws", [])
    return "\n".join([f"- [{l['id']}] {l['law']}" for l in laws])


def get_soft_laws(constitution: dict) -> str:
    """Extract soft laws as a formatted string for agent system prompts."""
    laws = constitution.get("soft_laws", [])
    return "\n".join([f"- [{l['id']}] {l['law']}" for l in laws])


def get_core_values(constitution: dict) -> str:
    """Extract core values as a formatted string."""
    values = constitution.get("core_values", [])
    return "\n".join([f"- {v}" for v in values])