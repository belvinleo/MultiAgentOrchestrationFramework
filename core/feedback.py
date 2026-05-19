"""
feedback.py
-----------
The Reward/Penalty Engine.
Every interaction can be scored by you (+1 reward, -1 penalty).
Scores are stored per department and used by the High Council
to measure performance and trigger audits.
"""

import json
import os
from datetime import datetime
from core.config import BASE_DIR

FEEDBACK_PATH = os.path.join(BASE_DIR, "logs", "feedback.json")


class FeedbackEngine:
    """
    Stores and retrieves feedback scores per department.

    Scoring:
        +1  = reward (response was good)
        -1  = penalty (response was bad)
         0  = neutral (no feedback given)

    Over time, departments accumulate a trust score based on
    their feedback history. High trust = more autonomy.
    Low trust = more confirmation steps before acting.
    """

    def __init__(self):
        os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        """Load existing feedback data from disk."""
        if os.path.exists(FEEDBACK_PATH):
            with open(FEEDBACK_PATH, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        """Persist feedback data to disk."""
        with open(FEEDBACK_PATH, "w") as f:
            json.dump(self._data, f, indent=2)

    def record(self, department: str, score: int, reason: str = ""):
        """
        Record a feedback score for a department.

        Parameters:
            department : name of the department being scored
            score      : +1 (reward) or -1 (penalty)
            reason     : optional note about why
        """
        if score not in [1, -1]:
            raise ValueError("Score must be +1 (reward) or -1 (penalty)")

        if department not in self._data:
            self._data[department] = {"history": [], "trust_score": 1.0}

        entry = {
            "score": score,
            "reason": reason,
            "timestamp": str(datetime.now())
        }

        self._data[department]["history"].append(entry)
        self._update_trust_score(department)
        self._save()

    def _update_trust_score(self, department: str):
        """
        Recalculate trust score from feedback history.
        Trust score ranges from 0.0 (no trust) to 2.0 (high trust).
        Starts at 1.0 (neutral).
        Recent feedback is weighted more than old feedback.
        """
        history = self._data[department]["history"]
        if not history:
            return

        # Use last 20 interactions with recency weighting
        recent = history[-20:]
        weighted_sum = 0
        weight_total = 0

        for i, entry in enumerate(recent):
            weight = i + 1  # more recent = higher weight
            weighted_sum += entry["score"] * weight
            weight_total += weight

        # Normalize to 0-2 range centered at 1.0
        raw = weighted_sum / weight_total if weight_total else 0
        trust = 1.0 + raw  # raw is -1 to +1, so trust is 0 to 2
        self._data[department]["trust_score"] = round(max(0.0, min(2.0, trust)), 3)

    def get_trust_score(self, department: str) -> float:
        """Returns current trust score for a department. Default 1.0."""
        return self._data.get(department, {}).get("trust_score", 1.0)

    def get_history(self, department: str) -> list:
        """Returns full feedback history for a department."""
        return self._data.get(department, {}).get("history", [])

    def get_all_scores(self) -> dict:
        """Returns trust scores for all departments."""
        return {
            dept: data["trust_score"]
            for dept, data in self._data.items()
        }

    def summary(self) -> str:
        """Human-readable summary of all department trust scores."""
        scores = self.get_all_scores()
        if not scores:
            return "No feedback recorded yet."

        lines = ["Department Trust Scores:"]
        for dept, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(score * 5)
            lines.append(f"  {dept:<30} {score:.2f} {bar}")
        return "\n".join(lines)