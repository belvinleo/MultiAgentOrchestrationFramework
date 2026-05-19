"""
emotion_engine.py
-----------------
Infers Belvin's current emotional state from available signals.

Sources:
- Health log (mood score, sleep, energy)
- Recent message tone
- Time of day
- Recent feedback patterns (lots of penalties = frustration)

Every department receives the current emotional state as context
so they can adjust their tone, depth, and urgency accordingly.

Emotional states: calm, stressed, tired, focused, anxious, positive
"""

import json
from datetime import datetime, time
from tools.health_input import HealthInput
from core.feedback import FeedbackEngine


class EmotionEngine:
    """
    Infers current emotional state from multiple data sources.
    Not a diagnostic tool — a context signal for agents.
    """

    STATES = ["calm", "stressed", "tired", "focused", "anxious", "positive", "unknown"]

    def __init__(self):
        self.health = HealthInput()
        self.feedback = FeedbackEngine()
        self._current_state = "unknown"
        self._last_inferred = None
        self._signals = {}

    def infer(self, recent_message: str = "") -> dict:
        """
        Infer current emotional state from all available signals.

        Returns:
            dict with state, confidence, signals, and tone_guidance
        """
        signals = {}
        scores = []

        # ── Signal 1: Health data ──────────────────────────────
        today = self.health.get_today()
        if today:
            mood = today.get("mood")
            energy = today.get("energy")
            sleep = today.get("sleep_hours")

            if mood:
                signals["mood_score"] = mood
                if mood <= 3:
                    scores.append(("stressed", 0.8))
                elif mood <= 5:
                    scores.append(("anxious", 0.5))
                elif mood >= 8:
                    scores.append(("positive", 0.8))
                else:
                    scores.append(("calm", 0.6))

            if energy:
                signals["energy_score"] = energy
                if energy <= 3:
                    scores.append(("tired", 0.9))
                elif energy >= 8:
                    scores.append(("focused", 0.7))

            if sleep:
                signals["sleep_hours"] = sleep
                if sleep < 5:
                    scores.append(("tired", 0.8))
                    scores.append(("stressed", 0.4))
                elif sleep > 8:
                    scores.append(("calm", 0.5))

        # ── Signal 2: Time of day ──────────────────────────────
        current_hour = datetime.now().hour
        signals["hour"] = current_hour

        if 6 <= current_hour <= 9:
            scores.append(("focused", 0.4))
        elif 10 <= current_hour <= 12:
            scores.append(("focused", 0.6))
        elif 13 <= current_hour <= 15:
            scores.append(("calm", 0.3))
        elif 16 <= current_hour <= 18:
            scores.append(("stressed", 0.3))
        elif 19 <= current_hour <= 21:
            scores.append(("calm", 0.5))
        elif current_hour >= 22 or current_hour < 6:
            scores.append(("tired", 0.6))

        # ── Signal 3: Recent feedback patterns ────────────────
        all_scores = self.feedback.get_all_scores()
        if all_scores:
            avg_trust = sum(all_scores.values()) / len(all_scores)
            signals["avg_trust"] = round(avg_trust, 2)
            if avg_trust < 0.7:
                scores.append(("stressed", 0.5))
            elif avg_trust > 1.3:
                scores.append(("positive", 0.4))

        # ── Signal 4: Message tone keywords ───────────────────
        if recent_message:
            msg_lower = recent_message.lower()
            stress_words = ["stressed", "tired", "exhausted", "worried",
                           "anxious", "overwhelmed", "bad", "terrible"]
            positive_words = ["great", "good", "happy", "excited",
                             "motivated", "energized", "fantastic"]
            tired_words = ["sleepy", "tired", "fatigue", "exhausted", "drained"]

            for word in stress_words:
                if word in msg_lower:
                    scores.append(("stressed", 0.7))
                    break
            for word in positive_words:
                if word in msg_lower:
                    scores.append(("positive", 0.7))
                    break
            for word in tired_words:
                if word in msg_lower:
                    scores.append(("tired", 0.8))
                    break

        # ── Aggregate scores ───────────────────────────────────
        if not scores:
            final_state = "unknown"
            confidence = 0.0
        else:
            # Tally weighted votes per state
            tally = {}
            for state, weight in scores:
                tally[state] = tally.get(state, 0) + weight

            final_state = max(tally, key=tally.get)
            total_weight = sum(tally.values())
            confidence = round(tally[final_state] / total_weight, 2)

        self._current_state = final_state
        self._last_inferred = str(datetime.now())
        self._signals = signals

        return {
            "state": final_state,
            "confidence": confidence,
            "signals": signals,
            "tone_guidance": self._get_tone_guidance(final_state),
            "inferred_at": self._last_inferred,
        }

    def _get_tone_guidance(self, state: str) -> str:
        """
        Returns tone instructions for agents based on emotional state.
        Injected into every agent's context.
        """
        guidance = {
            "calm":     "User is calm. Normal tone and depth appropriate.",
            "stressed": "User seems stressed. Be shorter, gentler, more supportive. Avoid overwhelming with data.",
            "tired":    "User seems tired. Be very concise. Lead with the single most important point only.",
            "focused":  "User is focused. Be direct and efficient. Skip pleasantries.",
            "anxious":  "User seems anxious. Be reassuring. Avoid alarming language or negative framings.",
            "positive": "User is in a positive state. Can be slightly more detailed and enthusiastic.",
            "unknown":  "Emotional state unknown. Use neutral, balanced tone.",
        }
        return guidance.get(state, guidance["unknown"])

    def get_current(self) -> dict:
        """Returns last inferred state without re-running inference."""
        return {
            "state": self._current_state,
            "last_inferred": self._last_inferred,
            "signals": self._signals,
        }

    def format_for_context(self, recent_message: str = "") -> str:
        """
        Formatted emotional context string for agent injection.
        """
        result = self.infer(recent_message)
        return (
            f"Emotional state: {result['state']} "
            f"(confidence: {result['confidence']:.0%})\n"
            f"Tone guidance: {result['tone_guidance']}"
        )