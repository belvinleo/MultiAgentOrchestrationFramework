"""
scheduler.py
------------
Background task scheduler for LifeOS proactive mode.
Runs tasks on defined intervals without blocking the main CLI.

Uses Python threading — lightweight, no external dependencies.
Tasks run in the background while you interact normally.
"""

import threading
import time
import logging
from datetime import datetime
from core.config import LOGS_PATH
import os

logging.basicConfig(
    filename=os.path.join(LOGS_PATH, "scheduler.log"),
    level=logging.INFO,
    format="%(asctime)s | SCHEDULER | %(message)s"
)


class ScheduledTask:
    """A single recurring task."""

    def __init__(self, name: str, func, interval_seconds: int, run_immediately: bool = False):
        self.name = name
        self.func = func
        self.interval = interval_seconds
        self.last_run = None
        self.run_count = 0
        self.run_immediately = run_immediately

    def is_due(self) -> bool:
        if self.run_immediately and self.last_run is None:
            return True
        if self.last_run is None:
            return False
        elapsed = (datetime.now() - self.last_run).total_seconds()
        return elapsed >= self.interval

    def run(self):
        try:
            self.func()
            self.last_run = datetime.now()
            self.run_count += 1
            logging.info(f"Task '{self.name}' completed. Run #{self.run_count}")
        except Exception as e:
            logging.error(f"Task '{self.name}' failed: {e}")


class Scheduler:
    """
    Background task runner.
    Tasks are checked every tick_interval seconds.
    Due tasks are run in separate threads to avoid blocking.
    """

    def __init__(self, tick_interval: int = 30):
        self.tick_interval = tick_interval
        self._tasks = []
        self._running = False
        self._thread = None

    def add_task(self, name: str, func, interval_seconds: int,
                 run_immediately: bool = False):
        """
        Register a background task.

        Parameters:
            name             : human-readable task name
            func             : callable to run
            interval_seconds : how often to run it
            run_immediately  : run on first tick without waiting
        """
        task = ScheduledTask(name, func, interval_seconds, run_immediately)
        self._tasks.append(task)

    def _tick(self):
        """Check all tasks and run any that are due."""
        for task in self._tasks:
            if task.is_due():
                thread = threading.Thread(target=task.run, daemon=True)
                thread.start()

    def start(self):
        """Start the scheduler in a background thread."""
        self._running = True

        def loop():
            while self._running:
                self._tick()
                time.sleep(self.tick_interval)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        logging.info("Scheduler started.")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        logging.info("Scheduler stopped.")

    def list_tasks(self) -> list:
        """Returns info about all registered tasks."""
        return [
            {
                "name": t.name,
                "interval_seconds": t.interval,
                "run_count": t.run_count,
                "last_run": str(t.last_run) if t.last_run else "Never",
            }
            for t in self._tasks
        ]

    def format_tasks(self) -> str:
        """Formatted task list for CLI display."""
        tasks = self.list_tasks()
        if not tasks:
            return "No scheduled tasks."

        lines = ["=== Scheduled Background Tasks ==="]
        for t in tasks:
            interval_min = t["interval_seconds"] // 60
            lines.append(
                f"  {t['name']:<35} "
                f"every {interval_min}min | "
                f"runs: {t['run_count']} | "
                f"last: {t['last_run'][:19] if t['last_run'] != 'Never' else 'Never'}"
            )
        return "\n".join(lines)