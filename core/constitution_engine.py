"""
constitution_engine.py
----------------------
Central manager for the LifeOS Constitution.
Handles reading, versioning, and updating constitution rules.
All agents and governance layers access constitution through this.

The Constitution has two tiers:
- Hard Laws : immutable, no agent can change these
- Soft Laws : evolve over time via Legislature proposals + your approval
"""

import yaml
import json
import os
import shutil
from datetime import datetime
from core.config import BASE_DIR, CONSTITUTION_PATH

CONSTITUTION_VERSION_DIR = os.path.join(BASE_DIR, "constitution", "versions")
CHANGELOG_PATH = os.path.join(BASE_DIR, "constitution", "changelog.json")


class ConstitutionEngine:
    """
    Single source of truth for all constitutional rules.
    Provides read/write access to the constitution with full versioning.
    Every change is logged with timestamp and reasoning.
    """

    def __init__(self):
        os.makedirs(CONSTITUTION_VERSION_DIR, exist_ok=True)
        self._constitution = self._load()
        self._changelog = self._load_changelog()

    def _load(self) -> dict:
        """Load current constitution from disk."""
        with open(CONSTITUTION_PATH, "r") as f:
            return yaml.safe_load(f)

    def _save(self):
        """Save current constitution to disk."""
        with open(CONSTITUTION_PATH, "w") as f:
            yaml.dump(self._constitution, f, default_flow_style=False, allow_unicode=True)

    def _load_changelog(self) -> list:
        if os.path.exists(CHANGELOG_PATH):
            with open(CHANGELOG_PATH, "r") as f:
                return json.load(f)
        return []

    def _save_changelog(self):
        with open(CHANGELOG_PATH, "w") as f:
            json.dump(self._changelog, f, indent=2)

    def _snapshot(self, reason: str):
        """
        Save a versioned snapshot of the current constitution.
        Called before every change so you can always roll back.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_path = os.path.join(
            CONSTITUTION_VERSION_DIR,
            f"constitution_{timestamp}.yaml"
        )
        shutil.copy(CONSTITUTION_PATH, version_path)

        # Log the change
        self._changelog.append({
            "timestamp": str(datetime.now()),
            "reason": reason,
            "snapshot": version_path,
            "version": timestamp,
        })
        self._save_changelog()

    # ─────────────────────────────────────────
    # READ METHODS
    # ─────────────────────────────────────────

    def get_hard_laws(self) -> list:
        """Returns list of hard law dicts."""
        return self._constitution.get("hard_laws", [])

    def get_soft_laws(self) -> list:
        """Returns list of soft law dicts."""
        return self._constitution.get("soft_laws", [])

    def get_core_values(self) -> list:
        return self._constitution.get("core_values", [])

    def get_goals(self) -> dict:
        return self._constitution.get("goals", {})

    def get_feedback_codex(self) -> dict:
        return self._constitution.get("feedback", {})

    def get_hard_laws_text(self) -> str:
        """Formatted hard laws for agent system prompts."""
        laws = self.get_hard_laws()
        return "\n".join([f"- [{l['id']}] {l['law']}" for l in laws])

    def get_soft_laws_text(self) -> str:
        """Formatted soft laws for agent system prompts."""
        laws = self.get_soft_laws()
        return "\n".join([f"- [{l['id']}] {l['law']}" for l in laws])

    def get_core_values_text(self) -> str:
        values = self.get_core_values()
        return "\n".join([f"- {v}" for v in values])

    def get_full_text(self) -> str:
        """Full constitution as formatted text for agent consumption."""
        return f"""
=== HARD LAWS (NEVER VIOLATE) ===
{self.get_hard_laws_text()}

=== SOFT LAWS (FOLLOW BY DEFAULT) ===
{self.get_soft_laws_text()}

=== CORE VALUES ===
{self.get_core_values_text()}
""".strip()

    # ─────────────────────────────────────────
    # WRITE METHODS (Soft Laws Only)
    # ─────────────────────────────────────────

    def add_soft_law(self, law_text: str, reason: str = "") -> str:
        """
        Add a new soft law to the constitution.
        Only soft laws can be added — hard laws are immutable.

        Parameters:
            law_text : the new rule text
            reason   : why this law is being added

        Returns:
            The new law ID
        """
        self._snapshot(f"Adding soft law: {law_text[:50]}")

        existing = self.get_soft_laws()
        # Generate next ID
        existing_ids = [l["id"] for l in existing]
        next_num = len(existing) + 1
        new_id = f"SL-{next_num:03d}"
        while new_id in existing_ids:
            next_num += 1
            new_id = f"SL-{next_num:03d}"

        new_law = {
            "id": new_id,
            "law": law_text,
            "added": str(datetime.now()),
            "reason": reason,
        }

        self._constitution["soft_laws"].append(new_law)
        self._save()
        return new_id

    def update_soft_law(self, law_id: str, new_text: str, reason: str = "") -> bool:
        """
        Update an existing soft law by ID.

        Returns:
            True if updated, False if ID not found
        """
        self._snapshot(f"Updating soft law {law_id}")

        laws = self.get_soft_laws()
        for law in laws:
            if law["id"] == law_id:
                law["law"] = new_text
                law["updated"] = str(datetime.now())
                law["update_reason"] = reason
                self._constitution["soft_laws"] = laws
                self._save()
                return True
        return False

    def remove_soft_law(self, law_id: str, reason: str = "") -> bool:
        """
        Remove a soft law by ID.
        Hard laws cannot be removed.
        """
        self._snapshot(f"Removing soft law {law_id}")

        laws = self.get_soft_laws()
        original_count = len(laws)
        laws = [l for l in laws if l["id"] != law_id]

        if len(laws) < original_count:
            self._constitution["soft_laws"] = laws
            self._save()
            return True
        return False

    def update_goals(self, term: str, goals: list, reason: str = "") -> bool:
        """
        Update goals for a term (short_term, medium_term, long_term).
        """
        self._snapshot(f"Updating {term} goals")
        if "goals" not in self._constitution:
            self._constitution["goals"] = {}
        self._constitution["goals"][term] = goals
        self._save()
        return True

    # ─────────────────────────────────────────
    # VERSION CONTROL
    # ─────────────────────────────────────────

    def get_changelog(self, last_n: int = 10) -> list:
        """Returns last N changelog entries."""
        return self._changelog[-last_n:]

    def list_versions(self) -> list:
        """Returns list of all saved constitution versions."""
        versions = []
        for f in sorted(os.listdir(CONSTITUTION_VERSION_DIR)):
            if f.endswith(".yaml"):
                versions.append(f)
        return versions

    def rollback(self, version_filename: str) -> bool:
        """
        Roll back constitution to a previous version.

        Parameters:
            version_filename : filename from list_versions()
        """
        version_path = os.path.join(CONSTITUTION_VERSION_DIR, version_filename)
        if not os.path.exists(version_path):
            return False

        self._snapshot("Pre-rollback snapshot")
        shutil.copy(version_path, CONSTITUTION_PATH)
        self._constitution = self._load()
        return True

    def format_changelog(self) -> str:
        """Formatted changelog for CLI display."""
        entries = self.get_changelog()
        if not entries:
            return "No constitution changes recorded yet."

        lines = ["=== Constitution Changelog ==="]
        for e in reversed(entries):
            lines.append(f"\n[{e['timestamp'][:19]}]")
            lines.append(f"  {e['reason']}")
            lines.append(f"  Snapshot: {os.path.basename(e['snapshot'])}")
        return "\n".join(lines)