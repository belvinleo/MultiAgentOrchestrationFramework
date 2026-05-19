"""
health_input.py
---------------
Manual health data logging and retrieval.
Since we don't have wearable API access yet, this is the
input layer for health data — you log it, LifeOS tracks it.
"""

import json
import os
from datetime import datetime, date
from core.config import BASE_DIR

HEALTH_LOG_PATH = os.path.join(BASE_DIR, "logs", "health_log.json")


class HealthInput:
    """
    Log and retrieve personal health data.

    Tracks:
    - Sleep duration and quality
    - Mood (1-10 scale)
    - Energy levels (1-10 scale)
    - Water intake
    - Exercise
    - Meals
    - Custom notes
    """

    def __init__(self):
        os.makedirs(os.path.dirname(HEALTH_LOG_PATH), exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(HEALTH_LOG_PATH):
            with open(HEALTH_LOG_PATH, "r") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(HEALTH_LOG_PATH, "w") as f:
            json.dump(self._data, f, indent=2)

    def _today(self) -> str:
        return str(date.today())

    def log(self, **kwargs) -> dict:
        """
        Log health data for today.

        Accepted kwargs:
            sleep_hours   : float (e.g. 7.5)
            sleep_quality : int 1-10
            mood          : int 1-10
            energy        : int 1-10
            water_ml      : int (millilitres)
            exercise_min  : int (minutes)
            meals         : list of strings
            notes         : str (free text)

        Returns:
            Today's full health log after update
        """
        today = self._today()
        if today not in self._data:
            self._data[today] = {}

        self._data[today].update(kwargs)
        self._data[today]["last_updated"] = str(datetime.now())
        self._save()
        return self._data[today]

    def get_today(self) -> dict:
        """Returns today's health log."""
        return self._data.get(self._today(), {})

    def get_date(self, date_str: str) -> dict:
        """Returns health log for a specific date (YYYY-MM-DD)."""
        return self._data.get(date_str, {})

    def get_last_n_days(self, n: int = 7) -> list:
        """
        Returns health logs for the last N days.
        Most recent first.
        """
        from datetime import timedelta
        results = []
        today = date.today()
        for i in range(n):
            d = str(today - timedelta(days=i))
            entry = self._data.get(d, {})
            if entry:
                results.append({"date": d, **entry})
        return results

    def get_averages(self, days: int = 7) -> dict:
        """
        Calculate average health metrics over last N days.
        """
        logs = self.get_last_n_days(days)
        if not logs:
            return {}

        metrics = ["sleep_hours", "sleep_quality", "mood", "energy", "water_ml", "exercise_min"]
        averages = {}

        for metric in metrics:
            values = [l[metric] for l in logs if metric in l]
            if values:
                averages[metric] = round(sum(values) / len(values), 1)

        return averages

    def format_for_agent(self, days: int = 7) -> str:
        """
        Format recent health data as clean text for agent consumption.
        """
        today_log = self.get_today()
        averages = self.get_averages(days)
        recent = self.get_last_n_days(days)

        lines = ["=== HEALTH DATA ==="]

        if today_log:
            lines.append(f"\nToday ({self._today()}):")
            for k, v in today_log.items():
                if k != "last_updated":
                    lines.append(f"  {k}: {v}")
        else:
            lines.append("\nToday: No data logged yet.")

        if averages:
            lines.append(f"\n{days}-Day Averages:")
            for k, v in averages.items():
                lines.append(f"  {k}: {v}")

        if recent:
            lines.append(f"\nLast {min(3, len(recent))} Days:")
            for entry in recent[:3]:
                d = entry.get("date", "")
                mood = entry.get("mood", "?")
                energy = entry.get("energy", "?")
                sleep = entry.get("sleep_hours", "?")
                lines.append(f"  {d}: mood={mood}, energy={energy}, sleep={sleep}h")

        return "\n".join(lines)