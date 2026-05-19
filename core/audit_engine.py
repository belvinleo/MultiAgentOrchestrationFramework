"""
audit_engine.py
---------------
The Audit Engine monitors department performance and
triggers reviews when trust scores drop below thresholds.

It works silently in the background — you only hear from it
when something needs your attention.
"""

import json
import os
from datetime import datetime
from core.feedback import FeedbackEngine
from core.base_agent import BaseAgent
from core.config import BASE_DIR

AUDIT_LOG_PATH = os.path.join(BASE_DIR, "logs", "audit_log.json")

# Thresholds
AUDIT_THRESHOLD = 0.6      # Trust score below this triggers audit
CRITICAL_THRESHOLD = 0.3   # Trust score below this triggers urgent review


class AuditEngine:
    """
    Continuously monitors department trust scores.
    Triggers audits when performance drops.
    Logs all audit events with reasoning.
    """

    def __init__(self):
        self.feedback = FeedbackEngine()
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        self._log = self._load_log()

    def _load_log(self) -> list:
        if os.path.exists(AUDIT_LOG_PATH):
            with open(AUDIT_LOG_PATH, "r") as f:
                return json.load(f)
        return []

    def _save_log(self):
        with open(AUDIT_LOG_PATH, "w") as f:
            json.dump(self._log, f, indent=2)

    def _record_audit(self, department: str, score: float,
                      severity: str, finding: str):
        """Log an audit event."""
        entry = {
            "department": department,
            "trust_score": score,
            "severity": severity,
            "finding": finding,
            "timestamp": str(datetime.now()),
        }
        self._log.append(entry)
        self._save_log()
        return entry

    def run_scan(self) -> list:
        """
        Scan all departments for performance issues.
        Returns list of audit findings.

        Call this periodically or on demand.
        """
        all_scores = self.feedback.get_all_scores()
        findings = []

        for dept, score in all_scores.items():
            if score < CRITICAL_THRESHOLD:
                finding = self._record_audit(
                    department=dept,
                    score=score,
                    severity="CRITICAL",
                    finding=f"{dept} trust score critically low ({score:.2f}). Immediate review required."
                )
                findings.append(finding)

            elif score < AUDIT_THRESHOLD:
                finding = self._record_audit(
                    department=dept,
                    score=score,
                    severity="WARNING",
                    finding=f"{dept} trust score below threshold ({score:.2f}). Performance review recommended."
                )
                findings.append(finding)

        return findings

    def get_audit_history(self, department: str = None) -> list:
        """
        Returns audit history, optionally filtered by department.
        """
        if department:
            return [e for e in self._log if e["department"] == department]
        return self._log

    def get_departments_under_review(self) -> list:
        """
        Returns list of departments currently below audit threshold.
        """
        all_scores = self.feedback.get_all_scores()
        return [
            {"department": dept, "score": score, "status": "CRITICAL" if score < CRITICAL_THRESHOLD else "WARNING"}
            for dept, score in all_scores.items()
            if score < AUDIT_THRESHOLD
        ]

    def format_findings(self, findings: list) -> str:
        """Format audit findings for display."""
        if not findings:
            return "✓ All departments within acceptable performance range."

        lines = ["=== AUDIT FINDINGS ==="]
        for f in findings:
            icon = "🔴" if f["severity"] == "CRITICAL" else "🟡"
            lines.append(f"{icon} [{f['severity']}] {f['finding']}")
        return "\n".join(lines)