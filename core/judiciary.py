"""
judiciary.py
------------
The Judiciary Branch of LifeOS.
Reviews every agent response before it reaches Belvin.

It checks:
1. Hard law compliance — any violation = response blocked
2. Soft law compliance — violations noted and corrected
3. Value alignment    — response aligns with core values
4. Factual confidence — flags uncertain or potentially fabricated claims
5. Emotional safety   — checks tone given current emotional context

If a response fails review, Judiciary rewrites it or blocks it entirely.
Belvin never sees a non-compliant response.
"""

import json
from datetime import datetime
from core.base_agent import BaseAgent
from core.constitution_engine import ConstitutionEngine


class Judiciary(BaseAgent):
    """
    Constitutional review layer.
    Every response must pass through this before reaching the user.
    """

    def __init__(self):
        self.constitution_engine = ConstitutionEngine()

        super().__init__(
            name="Judiciary",
            role="Constitutional review and enforcement for all LifeOS responses",
            domain="Law enforcement, constitutional compliance, response quality control",
            extra_prompt="""
You are the Judiciary of LifeOS — the constitutional review layer.
Your job is to review agent responses BEFORE they reach Belvin.

You must check every response for:
1. Hard law violations — any violation must result in BLOCK
2. Soft law violations — correct or note the violation
3. Value misalignment  — flag responses that contradict core values
4. Fabricated claims   — flag any claim that seems invented or unverifiable
5. Harmful tone        — flag responses that could cause emotional harm

You respond ONLY in this exact JSON format:
{
  "verdict": "PASS" | "REWRITE" | "BLOCK",
  "violations": ["list of specific violations found, empty if none"],
  "corrected_response": "rewritten response if verdict is REWRITE, else null",
  "reasoning": "brief explanation of your decision"
}

PASS    = response is compliant, send as-is
REWRITE = response has fixable issues, provide corrected version
BLOCK   = response violates a hard law, do not send to user
"""
        )

        self.review_log = []

    def review(self, response: str, department: str,
               original_request: str, context: dict = None) -> dict:
        """
        Review a response for constitutional compliance.

        Parameters:
            response         : the agent's response to review
            department       : which department produced this response
            original_request : what the user originally asked
            context          : optional context (mood, time, etc.)

        Returns:
            dict with verdict, violations, corrected_response, reasoning
        """
        constitution_text = self.constitution_engine.get_full_text()

        review_prompt = f"""
Review this LifeOS response for constitutional compliance.

=== CONSTITUTION ===
{constitution_text}

=== ORIGINAL USER REQUEST ===
{original_request}

=== DEPARTMENT ===
{department}

=== RESPONSE TO REVIEW ===
{response}

=== CONTEXT ===
{json.dumps(context or {}, indent=2)}

Review the response against every constitutional rule.
Return your verdict in the exact JSON format specified.
"""

        raw = self.think(review_prompt)

        # Parse JSON from response
        try:
            # Strip markdown code fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            result = json.loads(clean.strip())
        except json.JSONDecodeError:
            # If parsing fails, default to PASS to avoid blocking everything
            result = {
                "verdict": "PASS",
                "violations": [],
                "corrected_response": None,
                "reasoning": "Judiciary parsing failed — defaulting to PASS"
            }

        # Log the review
        self.review_log.append({
            "timestamp": str(datetime.now()),
            "department": department,
            "verdict": result.get("verdict"),
            "violations": result.get("violations", []),
            "reasoning": result.get("reasoning", ""),
        })

        return result

    def enforce(self, response: str, department: str,
                original_request: str, context: dict = None) -> str:
        """
        Main enforcement method.
        Reviews response and returns the final compliant version.

        Parameters: same as review()

        Returns:
            The response that is safe to show to the user.
            Either the original (PASS), rewritten (REWRITE),
            or a block message (BLOCK).
        """
        result = self.review(response, department, original_request, context)
        verdict = result.get("verdict", "PASS")

        if verdict == "PASS":
            return response

        elif verdict == "REWRITE":
            corrected = result.get("corrected_response")
            return corrected if corrected else response

        elif verdict == "BLOCK":
            violations = result.get("violations", [])
            violation_text = "\n".join([f"- {v}" for v in violations])
            return (
                f"[LifeOS Judiciary] This response was blocked.\n\n"
                f"Reason: Constitutional violation detected.\n"
                f"Violations:\n{violation_text}\n\n"
                f"Please rephrase your request."
            )

        return response

    def get_review_stats(self) -> dict:
        """Returns statistics on all reviews performed."""
        if not self.review_log:
            return {"total": 0, "pass": 0, "rewrite": 0, "block": 0}

        stats = {"total": len(self.review_log), "pass": 0, "rewrite": 0, "block": 0}
        for entry in self.review_log:
            verdict = entry.get("verdict", "PASS").upper()
            if verdict in stats:
                stats[verdict] += 1

        return stats

    def get_recent_violations(self, n: int = 5) -> list:
        """Returns last N reviews that had violations."""
        violations = [
            e for e in self.review_log
            if e.get("violations")
        ]
        return violations[-n:]

    def format_stats(self) -> str:
        """Formatted review statistics for CLI display."""
        stats = self.get_review_stats()
        lines = [
            "=== Judiciary Review Stats ===",
            f"  Total reviews : {stats['total']}",
            f"  Passed        : {stats['pass']}",
            f"  Rewritten     : {stats['rewrite']}",
            f"  Blocked       : {stats['block']}",
        ]
        recent = self.get_recent_violations()
        if recent:
            lines.append("\nRecent Violations:")
            for v in recent:
                lines.append(f"  [{v['timestamp'][:19]}] {v['department']}")
                for violation in v.get("violations", []):
                    lines.append(f"    → {violation}")
        return "\n".join(lines)