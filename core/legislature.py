"""
legislature.py
--------------
The Legislature Branch of LifeOS.
Mines feedback patterns and proposes new soft law amendments.

How it works:
1. Analyzes your reward/penalty history
2. Detects behavioral patterns (e.g. always penalize long responses at night)
3. Drafts new soft law proposals
4. Presents proposals to you for approval or rejection
5. Approved proposals are written into the constitution automatically

This is what makes LifeOS genuinely learn your preferences over time.
"""

import json
import os
from datetime import datetime
from core.base_agent import BaseAgent
from core.feedback import FeedbackEngine
from core.constitution_engine import ConstitutionEngine
from core.config import BASE_DIR

PROPOSALS_PATH = os.path.join(BASE_DIR, "logs", "law_proposals.json")


class Legislature(BaseAgent):
    """
    Proposes new soft laws based on observed behavioral patterns.
    Works with ConstitutionEngine to enact approved laws.
    """

    def __init__(self):
        self.feedback = FeedbackEngine()
        self.constitution_engine = ConstitutionEngine()

        super().__init__(
            name="Legislature",
            role="Pattern analyst and law proposer for LifeOS soft law evolution",
            domain="Behavioral pattern analysis, soft law drafting, preference learning",
            extra_prompt="""
You are the Legislature of LifeOS. Your job is to study Belvin's
feedback patterns and propose improvements to the soft laws.

When analyzing patterns:
- Look for consistent reward/penalty triggers
- Identify timing patterns (time of day, context)
- Notice department-specific preferences
- Find gaps in current soft laws

When proposing laws:
- Be specific and actionable
- Explain the pattern that motivated the proposal
- Predict how the law will improve Belvin's experience

Respond ONLY in this exact JSON format when proposing:
{
  "proposals": [
    {
      "draft": "The exact law text",
      "motivation": "Pattern observed that motivated this proposal",
      "predicted_impact": "How this will improve LifeOS",
      "confidence": 0.0-1.0
    }
  ]
}
"""
        )

        self._proposals = self._load_proposals()

    def _load_proposals(self) -> list:
        if os.path.exists(PROPOSALS_PATH):
            with open(PROPOSALS_PATH, "r") as f:
                return json.load(f)
        return []

    def _save_proposals(self):
        with open(PROPOSALS_PATH, "w") as f:
            json.dump(self._proposals, f, indent=2)

    def analyze_and_propose(self) -> list:
        """
        Analyze feedback history and generate law proposals.

        Returns:
            List of proposal dicts
        """
        # Gather all feedback data
        all_scores = self.feedback.get_all_scores()
        all_history = {}
        for dept in all_scores:
            history = self.feedback.get_history(dept)
            if history:
                all_history[dept] = history

        # Get current soft laws to avoid duplicates
        current_soft_laws = self.constitution_engine.get_soft_laws_text()

        if not all_history:
            return []

        analysis_prompt = f"""
Analyze this feedback history from LifeOS and propose new soft laws.

=== CURRENT SOFT LAWS (avoid duplicating these) ===
{current_soft_laws}

=== FEEDBACK HISTORY BY DEPARTMENT ===
{json.dumps(all_history, indent=2)}

=== DEPARTMENT TRUST SCORES ===
{json.dumps(all_scores, indent=2)}

Look for patterns in the feedback. Consider:
- Which departments get consistent penalties?
- Are there timing patterns?
- Are there response style patterns?
- What is working well that could be formalized?

Propose 1-3 new soft laws that would improve Belvin's experience.
Return in the exact JSON format specified.
Only propose laws with confidence >= 0.6.
If no clear patterns exist yet, return: {{"proposals": []}}
"""

        raw = self.think(analysis_prompt)

        # Parse proposals
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            result = json.loads(clean.strip())
            proposals = result.get("proposals", [])
        except json.JSONDecodeError:
            proposals = []

        # Tag proposals with metadata
        for p in proposals:
            p["id"] = f"PROP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self._proposals)}"
            p["status"] = "pending"
            p["created"] = str(datetime.now())

        self._proposals.extend(proposals)
        self._save_proposals()

        return proposals

    def get_pending_proposals(self) -> list:
        """Returns all proposals awaiting your decision."""
        return [p for p in self._proposals if p.get("status") == "pending"]

    def approve_proposal(self, proposal_id: str) -> bool:
        """
        Approve a proposal — writes it into the constitution.

        Parameters:
            proposal_id : the proposal ID string

        Returns:
            True if approved and enacted, False if not found
        """
        for p in self._proposals:
            if p["id"] == proposal_id:
                # Enact the law
                new_id = self.constitution_engine.add_soft_law(
                    law_text=p["draft"],
                    reason=f"Legislature proposal approved. Motivation: {p['motivation']}"
                )
                p["status"] = "approved"
                p["enacted_as"] = new_id
                p["decided_at"] = str(datetime.now())
                self._save_proposals()
                return True
        return False

    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """
        Reject a proposal — it will not be added to the constitution.
        """
        for p in self._proposals:
            if p["id"] == proposal_id:
                p["status"] = "rejected"
                p["rejection_reason"] = reason
                p["decided_at"] = str(datetime.now())
                self._save_proposals()
                return True
        return False

    def format_proposals(self, proposals: list) -> str:
        """Format proposals for CLI display."""
        if not proposals:
            return "No new law proposals at this time."

        lines = ["=== Pending Law Proposals ===\n"]
        for i, p in enumerate(proposals, 1):
            confidence_bar = "█" * int(p.get("confidence", 0) * 10)
            lines.append(f"Proposal {i} [{p['id']}]")
            lines.append(f"  Draft    : {p['draft']}")
            lines.append(f"  Why      : {p['motivation']}")
            lines.append(f"  Impact   : {p['predicted_impact']}")
            lines.append(f"  Confidence: {p.get('confidence', 0):.0%} {confidence_bar}")
            lines.append("")

        lines.append("To approve: 'approve <proposal_id>'")
        lines.append("To reject:  'reject <proposal_id>'")
        return "\n".join(lines)

    def get_history(self) -> list:
        """Returns all proposals (pending, approved, rejected)."""
        return self._proposals

    def format_history(self) -> str:
        """Formatted proposal history."""
        if not self._proposals:
            return "No proposals in history."

        lines = ["=== Law Proposal History ==="]
        for p in reversed(self._proposals[-10:]):
            status_color = {
                "pending": "⏳",
                "approved": "✓",
                "rejected": "✗"
            }.get(p.get("status", "pending"), "?")
            lines.append(f"\n{status_color} [{p.get('status', '?').upper()}] {p['draft'][:60]}...")
            lines.append(f"   Created: {p['created'][:19]}")
            if p.get("status") == "approved":
                lines.append(f"   Enacted as: {p.get('enacted_as', '?')}")
        return "\n".join(lines)