"""
cluster_governor.py
-------------------
The Cluster Governor manages a group of related departments.
It sits between the High Council and individual departments.

Responsibilities:
- Coordinate departments within its cluster
- Aggregate performance metrics for its cluster
- Resolve conflicts between departments in the same cluster
- Report cluster health up to the High Council
"""

import yaml
import os
from datetime import datetime
from core.base_agent import BaseAgent
from core.feedback import FeedbackEngine
from core.department_factory import DepartmentFactory


class ClusterGovernor(BaseAgent):
    """
    Manages a named cluster of departments.

    Parameters:
        cluster_name  : e.g. 'Wellbeing', 'Finance', 'Knowledge'
        department_configs : list of config.yaml paths under this cluster
    """

    def __init__(self, cluster_name: str, department_configs: list):
        super().__init__(
            name=f"Governor of {cluster_name}",
            role=f"Cluster Governor responsible for all {cluster_name} departments",
            domain=f"Governance, performance monitoring, conflict resolution within {cluster_name} cluster",
            extra_prompt=f"""
You are the Cluster Governor for the {cluster_name} cluster inside LifeOS.
Your responsibilities:
1. Monitor the performance of all departments under you
2. Identify which department is best suited for each request
3. Resolve conflicts when departments in your cluster disagree
4. Report cluster health and issues to the High Council
5. Recommend department audits when performance drops

Always be analytical and objective. You serve Belvin's best interests,
not the interests of individual departments.
"""
        )

        self.cluster_name = cluster_name
        self.department_configs = department_configs
        self.feedback = FeedbackEngine()
        self.factory = DepartmentFactory()
        self._departments = {}
        self._load_departments()

    def _load_departments(self):
        """Load all department configs in this cluster."""
        for config_path in self.department_configs:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                name = config.get("name", "Unknown")
                self._departments[name] = {
                    "config_path": config_path,
                    "config": config,
                }

    def get_cluster_performance(self) -> dict:
        """
        Aggregate performance metrics for all departments in this cluster.

        Returns dict with per-department trust scores and cluster average.
        """
        scores = {}
        total = 0
        count = 0

        for dept_name in self._departments:
            score = self.feedback.get_trust_score(dept_name)
            scores[dept_name] = score
            total += score
            count += 1

        avg = round(total / count, 3) if count else 1.0

        return {
            "cluster": self.cluster_name,
            "departments": scores,
            "average_trust": avg,
            "department_count": count,
            "timestamp": str(datetime.now()),
        }

    def get_weakest_department(self) -> tuple:
        """
        Returns (name, score) of the lowest-performing department.
        Used by audit engine to decide what to review.
        """
        performance = self.get_cluster_performance()
        scores = performance["departments"]
        if not scores:
            return None, None
        weakest = min(scores, key=scores.get)
        return weakest, scores[weakest]

    def get_strongest_department(self) -> tuple:
        """Returns (name, score) of the highest-performing department."""
        performance = self.get_cluster_performance()
        scores = performance["departments"]
        if not scores:
            return None, None
        strongest = max(scores, key=scores.get)
        return strongest, scores[strongest]

    def resolve_conflict(self, dept_a: str, response_a: str,
                         dept_b: str, response_b: str,
                         original_request: str) -> str:
        """
        When two departments give conflicting answers,
        the governor arbitrates and returns the best response.
        """
        conflict_prompt = f"""
Two departments under your governance have given conflicting responses.
Your job is to arbitrate and produce the single best answer.

Original request: {original_request}

{dept_a} responded:
{response_a}

{dept_b} responded:
{response_b}

Analyze both responses. Identify the conflict. Produce one unified,
accurate response that serves Belvin best. Explain briefly which
perspective you sided with and why.
"""
        return self.think(conflict_prompt)

    def cluster_briefing(self) -> str:
        """
        Generate a short briefing on this cluster's current state.
        Used in the High Council's overall report.
        """
        performance = self.get_cluster_performance()
        weakest, weak_score = self.get_weakest_department()

        prompt = f"""
Generate a brief cluster briefing for the High Council.

Cluster: {self.cluster_name}
Department count: {performance['department_count']}
Average trust score: {performance['average_trust']}
Department scores: {performance['departments']}
Weakest department: {weakest} (score: {weak_score})

Write a 3-4 sentence executive summary covering:
1. Overall cluster health
2. Any departments needing attention
3. One recommendation for improvement
"""
        return self.think(prompt)

    def list_departments(self) -> list:
        """Returns list of department names in this cluster."""
        return list(self._departments.keys())