"""
proactive_engine.py
-------------------
The Proactive Engine — LifeOS's ability to speak without being asked.

It runs in the background via the Scheduler and monitors:
- Health patterns (sleep streak, mood trend, energy dips)
- Financial signals (market movements, SIP dates)
- Cross-domain patterns (stress + poor sleep + social withdrawal)
- Constitution compliance (soft law reminders)

When it detects something worth surfacing, it adds an alert
to a queue. The CLI checks this queue and displays alerts
between your messages — non-intrusively.

Design principle: speak only when genuinely useful.
Never be noisy. Quality over quantity.
"""

import json
import os
from datetime import datetime, date, timedelta
from core.base_agent import BaseAgent
from core.emotion_engine import EmotionEngine
from core.feedback import FeedbackEngine
from tools.health_input import HealthInput
from tools.finance_api import FinanceAPI
from core.config import BASE_DIR

ALERTS_PATH = os.path.join(BASE_DIR, "logs", "proactive_alerts.json")

# Alert priority levels
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH     = "high"
PRIORITY_MEDIUM   = "medium"
PRIORITY_LOW      = "low"


class ProactiveEngine(BaseAgent):
    """
    Monitors life signals and generates proactive alerts.
    Runs on a schedule via the Scheduler.
    Alerts are queued and shown between user messages.
    """

    def __init__(self):
        super().__init__(
            name="Proactive Engine",
            role="Background monitor that surfaces insights without being asked",
            domain="Pattern detection, proactive alerting, life signal monitoring",
            extra_prompt="""
You are the Proactive Engine of LifeOS. You monitor Belvin's life
signals and surface insights ONLY when genuinely useful.

Rules for proactive alerts:
1. Only alert when you have something specific and actionable to say
2. Be brief — proactive alerts must be under 60 words
3. Lead with the insight, not the data
4. Include one clear action or recommendation
5. Never be alarmist. Be calm and supportive.
6. Don't repeat the same alert within 24 hours
"""
        )

        self.emotion = EmotionEngine()
        self.feedback = FeedbackEngine()
        self.health = HealthInput()
        self.finance = FinanceAPI()
        self._alerts = self._load_alerts()
        self._alert_queue = []  # In-memory queue for pending display

    def _load_alerts(self) -> list:
        if os.path.exists(ALERTS_PATH):
            with open(ALERTS_PATH, "r") as f:
                return json.load(f)
        return []

    def _save_alerts(self):
        with open(ALERTS_PATH, "w") as f:
            json.dump(self._alerts, f, indent=2)

    def _already_alerted_today(self, alert_type: str) -> bool:
        """Check if this type of alert was already sent today."""
        today = str(date.today())
        for alert in self._alerts:
            if alert.get("type") == alert_type and alert.get("date") == today:
                return True
        return False

    def _create_alert(self, alert_type: str, message: str,
                      priority: str = PRIORITY_MEDIUM) -> dict:
        """Create and queue an alert."""
        alert = {
            "id": f"ALERT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": alert_type,
            "message": message,
            "priority": priority,
            "date": str(date.today()),
            "timestamp": str(datetime.now()),
            "shown": False,
        }
        self._alerts.append(alert)
        self._alert_queue.append(alert)
        self._save_alerts()
        return alert

    # ── Health Monitors ───────────────────────────────────────────

    def _check_sleep_pattern(self):
        """Alert if sleep has been consistently poor."""
        logs = self.health.get_last_n_days(5)
        if len(logs) < 3:
            return

        poor_sleep_days = [
            l for l in logs
            if l.get("sleep_hours") and l["sleep_hours"] < 6
        ]

        if len(poor_sleep_days) >= 3 and not self._already_alerted_today("poor_sleep_streak"):
            prompt = f"""
Generate a brief proactive health alert about poor sleep.
Data: {len(poor_sleep_days)} out of last {len(logs)} days had under 6 hours sleep.
Average: {sum(l['sleep_hours'] for l in poor_sleep_days) / len(poor_sleep_days):.1f} hours.
Under 60 words. Calm and supportive tone.
"""
            message = self.think(prompt)
            self._create_alert("poor_sleep_streak", message, PRIORITY_HIGH)

    def _check_mood_trend(self):
        """Alert if mood has been declining."""
        logs = self.health.get_last_n_days(5)
        mood_scores = [l.get("mood") for l in logs if l.get("mood")]

        if len(mood_scores) < 3:
            return

        # Check if mood is trending down
        recent_avg = sum(mood_scores[:2]) / 2
        older_avg = sum(mood_scores[2:]) / len(mood_scores[2:])

        if recent_avg < older_avg - 1.5 and not self._already_alerted_today("mood_decline"):
            prompt = f"""
Generate a brief proactive alert about declining mood trend.
Recent mood average: {recent_avg:.1f}/10
Previous mood average: {older_avg:.1f}/10
Under 60 words. Warm, supportive tone. Suggest one small action.
"""
            message = self.think(prompt)
            self._create_alert("mood_decline", message, PRIORITY_HIGH)

    def _check_no_health_log(self):
        """Remind to log health data if not done today."""
        today_log = self.health.get_today()
        current_hour = datetime.now().hour

        if not today_log and current_hour >= 10 and not self._already_alerted_today("no_health_log"):
            self._create_alert(
                "no_health_log",
                "📋 Quick check-in: You haven't logged today's health data yet. "
                "Type 'log health' to record your mood, sleep, and energy — takes 30 seconds.",
                PRIORITY_LOW
            )

    def _check_energy_dip(self):
        """Alert on very low energy today."""
        today = self.health.get_today()
        energy = today.get("energy")

        if energy and energy <= 3 and not self._already_alerted_today("low_energy"):
            prompt = f"""
Generate a brief proactive alert. Energy level logged today: {energy}/10.
Suggest one immediate action to restore energy.
Under 50 words. Practical and direct.
"""
            message = self.think(prompt)
            self._create_alert("low_energy", message, PRIORITY_MEDIUM)

    # ── Finance Monitors ──────────────────────────────────────────

    def _check_market_movement(self):
        """Alert on significant Nifty movement."""
        try:
            nifty = self.finance.get_index("nifty")
            change_pct = nifty.get("change_pct")

            if change_pct is None:
                return

            if abs(change_pct) >= 1.5 and not self._already_alerted_today("market_movement"):
                direction = "up" if change_pct > 0 else "down"
                prompt = f"""
Generate a brief market alert. Nifty 50 is {direction} {abs(change_pct):.1f}% today.
Current level: {nifty.get('current_price', 'N/A')}.
Under 50 words. Informational only, not investment advice.
"""
                message = self.think(prompt)
                priority = PRIORITY_HIGH if abs(change_pct) >= 2.5 else PRIORITY_MEDIUM
                self._create_alert("market_movement", message, priority)
        except Exception:
            pass

    # ── Cross-Domain Monitors ─────────────────────────────────────

    def _check_burnout_signals(self):
        """
        The most powerful proactive check.
        Looks for burnout pattern across health + feedback + time.
        """
        logs = self.health.get_last_n_days(7)
        if len(logs) < 4:
            return

        # Count stress signals
        stress_signals = 0
        low_mood_days = sum(1 for l in logs if l.get("mood", 10) <= 4)
        low_sleep_days = sum(1 for l in logs if l.get("sleep_hours", 10) < 6)
        low_energy_days = sum(1 for l in logs if l.get("energy", 10) <= 3)

        stress_signals = low_mood_days + low_sleep_days + low_energy_days

        if stress_signals >= 6 and not self._already_alerted_today("burnout_risk"):
            prompt = f"""
Generate a compassionate proactive burnout risk alert.
Data from last 7 days:
- Low mood days (≤4/10): {low_mood_days}
- Poor sleep days (<6h): {low_sleep_days}
- Low energy days (≤3/10): {low_energy_days}

Under 70 words. Compassionate, not alarming.
Acknowledge the pattern. Suggest one meaningful action.
"""
            message = self.think(prompt)
            self._create_alert("burnout_risk", message, PRIORITY_CRITICAL)

    # ── Main Monitor Runner ───────────────────────────────────────

    def run_all_monitors(self):
        """
        Run all monitoring checks.
        Called by the Scheduler on a regular interval.
        """
        checks = [
            self._check_no_health_log,
            self._check_sleep_pattern,
            self._check_mood_trend,
            self._check_energy_dip,
            self._check_market_movement,
            self._check_burnout_signals,
        ]

        for check in checks:
            try:
                check()
            except Exception:
                pass

    def get_pending_alerts(self) -> list:
        """
        Returns alerts waiting to be shown to the user.
        Marks them as shown after retrieval.
        """
        pending = [a for a in self._alert_queue if not a.get("shown")]
        for alert in pending:
            alert["shown"] = True
        self._alert_queue = []
        return pending

    def get_alert_history(self, days: int = 7) -> list:
        """Returns alerts from the last N days."""
        cutoff = date.today() - timedelta(days=days)
        return [
            a for a in self._alerts
            if datetime.fromisoformat(a["timestamp"]).date() >= cutoff
        ]

    def format_alert(self, alert: dict) -> str:
        """Format a single alert for CLI display."""
        icons = {
            PRIORITY_CRITICAL: "🔴",
            PRIORITY_HIGH:     "🟠",
            PRIORITY_MEDIUM:   "🟡",
            PRIORITY_LOW:      "🔵",
        }
        icon = icons.get(alert["priority"], "●")
        return f"{icon} {alert['message']}"