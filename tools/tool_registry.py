"""
tool_registry.py
----------------
Central registry of all tools available to agents.
Departments declare which tools they need in their config.yaml
and the registry provides them.
"""

from tools.finance_api import FinanceAPI
from tools.web_search import WebSearch
from tools.health_input import HealthInput


class ToolRegistry:
    """
    Single source of truth for all tools.
    Agents request tools by name — registry returns the instance.
    Tools are singletons — one instance shared across all agents.
    """

    _instances = {}

    AVAILABLE_TOOLS = {
        "finance_api":   FinanceAPI,
        "web_search":    WebSearch,
        "health_input":  HealthInput,
    }

    @classmethod
    def get(cls, tool_name: str):
        """
        Get a tool instance by name.
        Creates on first call, returns cached instance after.

        Parameters:
            tool_name : one of the AVAILABLE_TOOLS keys

        Returns:
            Tool instance

        Raises:
            ValueError if tool_name not found
        """
        if tool_name not in cls.AVAILABLE_TOOLS:
            raise ValueError(
                f"Tool '{tool_name}' not found. "
                f"Available: {list(cls.AVAILABLE_TOOLS.keys())}"
            )

        if tool_name not in cls._instances:
            cls._instances[tool_name] = cls.AVAILABLE_TOOLS[tool_name]()

        return cls._instances[tool_name]

    @classmethod
    def get_many(cls, tool_names: list) -> dict:
        """
        Get multiple tools at once.

        Returns:
            dict of {tool_name: tool_instance}
        """
        return {name: cls.get(name) for name in tool_names}

    @classmethod
    def list_available(cls) -> list:
        return list(cls.AVAILABLE_TOOLS.keys())