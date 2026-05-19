"""
department_factory.py
---------------------
Reads a department YAML config and returns a live BaseAgent instance.
This is how LifeOS scales to 250 departments without writing 250 classes.
"""

import yaml
import os
from core.base_agent import BaseAgent


class DepartmentFactory:
    """
    Turns a YAML department config into a working agent.

    Usage:
        factory = DepartmentFactory()
        health_dept = factory.create("departments/health/config.yaml")
        response = health_dept.think("How is my sleep trend?")
    """

    def __init__(self):
        self._loaded = {}  # cache: avoid reloading same department twice

    def create(self, config_path: str) -> BaseAgent:
        """
        Load a department config and return a BaseAgent instance.

        Parameters:
            config_path : path to the department's config.yaml

        Returns:
            A fully initialized BaseAgent for that department
        """
        # Return cached instance if already loaded
        if config_path in self._loaded:
            return self._loaded[config_path]

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Department config not found: {config_path}")

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required = ["name", "domain", "role", "supervisor_prompt"]
        for field in required:
            if field not in config:
                raise ValueError(f"Department config missing required field: '{field}'")

        # Build the agent
        agent = BaseAgent(
            name=config["name"],
            role=config["role"],
            domain=config["domain"],
            extra_prompt=config["supervisor_prompt"],
        )

        # Attach config metadata to the agent for registry use
        agent.config = config

        # Cache it
        self._loaded[config_path] = agent
        return agent

    def create_from_dict(self, config: dict) -> BaseAgent:
        """
        Create a department directly from a dict (no file needed).
        Useful for testing or dynamic department creation.
        """
        agent = BaseAgent(
            name=config["name"],
            role=config["role"],
            domain=config["domain"],
            extra_prompt=config.get("supervisor_prompt", ""),
        )
        agent.config = config
        return agent

    def list_loaded(self) -> list:
        """Returns names of all currently loaded departments."""
        return [agent.name for agent in self._loaded.values()]