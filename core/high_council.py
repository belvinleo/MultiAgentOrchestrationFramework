"""
high_council.py
---------------
The High Council — the supreme monitoring body of LifeOS.

It sits above all departments and cluster governors.
It does not handle user requests directly — it governs the system.

Responsibilities:
- Monitor all clusters and departments
- Generate periodic performance reports
- Escalate critical issues to the user
- Run cross-department intelligence synthesis
- Maintain the overall health of LifeOS
"""

import os
import json
from datetime import datetime
from core.base_agent import BaseAgent
from core.feedback import FeedbackEngine
from core.audit_engine import AuditEngine
from core.cluster_governor import ClusterGovernor
from core.config import BASE_DIR

REPORT_PATH = os.path.join(BASE_DIR, "logs", "council_reports.json")


class HighCouncil(BaseAgent):
    """
    The supreme governing body of LifeOS.
    Instantiated once at startup. Runs governance in background.
    """

    def __init__(self, department_root: str = "departments"):
        super().__init__(
            name="High Council",
            role="Supreme governing body of LifeOS. Monitor, evaluate, and advise.",
            domain="Governance, performance monitoring, cross-department intelligence, system health",
            extra_prompt="""
You are the High Council of LifeOS — the supreme oversight body.
You do not handle Belvin's personal requests directly.
Your job is to:
1. Monitor the health and performance of all departments
2. Generate honest, analytical reports
3. Identify systemic issues across departments
4. Provide strategic recommendations to improve LifeOS
5. Surface cross-department patterns that individual departments miss

Be analytical, objective, and concise. Think like a board of directors
reviewing the performance of an organization. Belvin is the CEO.
"""
        )

        self.feedback = FeedbackEngine()
        self.audit = AuditEngine()
        self.department_root = department_root
        self.clusters = self._initialize_clusters()

        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        self._reports = self._load_reports()

    def _initialize_clusters(self) -> dict:
        """
        Auto-detect department clusters from folder structure.
        Groups departments by their cluster field in config.yaml,
        or by folder name if cluster not specified.
        """
        import yaml

        clusters = {}

        if not os.path.exists(self.department_root):
            return clusters

        for dept_folder in os.listdir(self.department_root):
            config_path = os.path.join(
                self.department_root, dept_folder, "config.yaml"
            )
            if not os.path.exists(config_path):
                continue

            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Use 'cluster' field if defined, else use folder name
            cluster_name = config.get("cluster", dept_folder.capitalize())

            if cluster_name not in clusters:
                clusters[cluster_name] = []
            clusters[cluster_name].append(config_path)

        # Create ClusterGovernor for each cluster
        governors = {}
        for cluster_name, config_paths in clusters.items():
            governors[cluster_name] = ClusterGovernor(cluster_name, config_paths)

        return governors

    def _load_reports(self) -> list:
        if os.path.exists(REPORT_PATH):
            with open(REPORT_PATH, "r") as f:
                return json.load(f)
        return []

    def _save_reports(self):
        with open(REPORT_PATH, "w") as f:
            json.dump(self._reports, f, indent=2)

    def get_system_overview(self) -> dict:
        """
        Full snapshot of LifeOS system health.
        Returns structured data covering all clusters and departments.
        """
        overview = {
            "timestamp": str(datetime.now()),
            "clusters": {},
            "overall_health": 0,
            "total_departments": 0,
            "departments_under_review": [],
        }

        all_scores = []

        for cluster_name, governor in self.clusters.items():
            performance = governor.get_cluster_performance()
            overview["clusters"][cluster_name] = performance
            all_scores.append(performance["average_trust"])
            overview["total_departments"] += performance["department_count"]

        # Calculate overall system health
        if all_scores:
            overview["overall_health"] = round(
                sum(all_scores) / len(all_scores), 3
            )

        # Departments under review
        overview["departments_under_review"] = self.audit.get_departments_under_review()

        return overview

    def generate_report(self) -> str:
        """
        Generate a full LifeOS performance report.
        Saves to disk and returns formatted string.
        """
        overview = self.get_system_overview()
        audit_findings = self.audit.run_scan()

        # Collect cluster briefings
        cluster_briefings = {}
        for cluster_name, governor in self.clusters.items():
            try:
                cluster_briefings[cluster_name] = governor.cluster_briefing()
            except Exception as e:
                cluster_briefings[cluster_name] = f"Briefing unavailable: {e}"

        # Build report prompt
        report_prompt = f"""
Generate a comprehensive LifeOS Performance Report for Belvin.

SYSTEM OVERVIEW:
- Overall health score: {overview['overall_health']}
- Total departments: {overview['total_departments']}
- Departments under review: {len(overview['departments_under_review'])}
- Clusters monitored: {list(overview['clusters'].keys())}

CLUSTER PERFORMANCE:
{json.dumps(overview['clusters'], indent=2)}

AUDIT FINDINGS:
{self.audit.format_findings(audit_findings)}

CLUSTER BRIEFINGS:
{json.dumps(cluster_briefings, indent=2)}

Write a structured report with these sections:
1. Executive Summary (3 sentences max)
2. System Health Score with interpretation
3. Top performing area
4. Area needing most attention
5. Three specific recommendations

Be direct and honest. This report helps Belvin improve LifeOS.
"""
        report_text = self.think(report_prompt)

        # Save report
        report_entry = {
            "timestamp": str(datetime.now()),
            "overview": overview,
            "audit_findings": audit_findings,
            "report": report_text,
        }
        self._reports.append(report_entry)
        self._save_reports()

        return report_text

    def cross_department_intelligence(self, topic: str) -> str:
        """
        Synthesize intelligence across all departments on a topic.
        This is what makes the High Council more than just a monitor.

        Example: "burnout risk" → pulls from Health, Finance, Productivity,
        Social all at once and finds the cross-cutting pattern.
        """
        all_scores = self.feedback.get_all_scores()
        overview = self.get_system_overview()

        prompt = f"""
Perform a cross-department intelligence analysis on: "{topic}"

You have access to the full LifeOS system state:
- Department trust scores: {all_scores}
- Cluster performance: {overview['clusters']}

Based on this system-wide view, provide a deep analysis of "{topic}"
that no single department could produce alone. Look for:
- Patterns that span multiple departments
- Conflicting signals between departments
- Systemic risks or opportunities
- What the data suggests about Belvin's current life situation

Be insightful, specific, and actionable.
"""
        return self.think(prompt)

    def get_resource_priority(self, competing_depts: list) -> str:
        """
        When multiple departments compete for attention simultaneously,
        the High Council decides who gets priority.

        Parameters:
            competing_depts : list of department names all triggered at once

        Returns:
            Ordered priority list with reasoning
        """
        scores = {d: self.feedback.get_trust_score(d) for d in competing_depts}

        prompt = f"""
Multiple departments are requesting attention simultaneously.
Decide the priority order for Belvin right now.

Competing departments: {competing_depts}
Their trust scores: {scores}
Current time: {datetime.now().strftime('%H:%M')}

Consider:
- Which domain is most time-sensitive right now?
- Which department has the highest trust score?
- What is the likely context given the time of day?

Return a prioritized list with a one-line reason for each.
"""
        return self.think(prompt)

    def get_latest_report(self) -> str:
        """Return the most recent council report."""
        if not self._reports:
            return "No reports generated yet. Type 'report' to generate one."
        return self._reports[-1]["report"]

    def format_overview_table(self) -> str:
        """
        Format system overview as a clean text table for CLI display.
        """
        overview = self.get_system_overview()
        lines = []

        lines.append(f"╔══ LifeOS System Health ══╗")
        lines.append(f"  Overall Score: {overview['overall_health']:.2f} / 2.00")
        lines.append(f"  Departments:   {overview['total_departments']}")
        lines.append(f"  Under Review:  {len(overview['departments_under_review'])}")
        lines.append(f"  Clusters:      {len(overview['clusters'])}")
        lines.append("")

        for cluster_name, data in overview["clusters"].items():
            avg = data.get("average_trust", 1.0)
            bar = "█" * int(avg * 5)
            lines.append(f"  {cluster_name:<20} {avg:.2f} {bar}")
            for dept, score in data.get("departments", {}).items():
                dept_bar = "▓" * int(score * 5)
                lines.append(f"    └─ {dept:<18} {score:.2f} {dept_bar}")

        if overview["departments_under_review"]:
            lines.append("\n  ⚠ Departments Under Review:")
            for d in overview["departments_under_review"]:
                lines.append(f"    {d['department']} — {d['status']} ({d['score']:.2f})")

        return "\n".join(lines)