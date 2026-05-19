"""
orchestrator.py
---------------
Phase 5 Orchestrator — Constitution-enforced.
Every department response passes through Judiciary before reaching user.
"""

from core.base_agent import BaseAgent
from core.registry import DepartmentRegistry
from core.memory import short_term, long_term
from core.feedback import FeedbackEngine
from core.judiciary import Judiciary
from tools.tool_registry import ToolRegistry
from datetime import datetime
import yaml


class Orchestrator(BaseAgent):

    def __init__(self):
        super().__init__(
            name="Orchestrator",
            role="Chief of Staff of LifeOS. Route requests to departments and synthesize responses.",
            domain="Routing, coordination, synthesis, general intelligence",
            extra_prompt="""
You are the master coordinator of LifeOS. Synthesize department responses
into one clean, helpful, unified reply for Belvin.
Be concise. Lead with the most important insight.
Never mention internal routing or department names unless asked.
"""
        )
        self.registry = DepartmentRegistry()
        self.feedback = FeedbackEngine()
        self.judiciary = Judiciary()

        count = self.registry.register_all("departments")
        from rich.console import Console
        Console().print(f"[dim]Registry loaded {count} departments.[/dim]")

    def _get_tool_context(self, message: str, tools: list) -> str:
        context_parts = []
        for tool_name in tools:
            try:
                tool = ToolRegistry.get(tool_name)
                if tool_name == "finance_api":
                    msg_lower = message.lower()
                    finance_data = []
                    nifty = tool.get_index("nifty")
                    sensex = tool.get_index("sensex")
                    finance_data.append("=== MARKET SNAPSHOT ===")
                    finance_data.append(tool.format_for_agent(nifty))
                    finance_data.append(tool.format_for_agent(sensex))
                    stock_keywords = {
                        "reliance": "RELIANCE.NS", "tcs": "TCS.NS",
                        "infosys": "INFY.NS", "hdfc": "HDFCBANK.NS",
                        "sbi": "SBIN.NS", "icici": "ICICIBANK.NS",
                        "wipro": "WIPRO.NS", "apple": "AAPL",
                        "tesla": "TSLA", "google": "GOOGL",
                    }
                    for keyword, ticker in stock_keywords.items():
                        if keyword in msg_lower:
                            stock = tool.get_stock_price(ticker)
                            finance_data.append(tool.format_for_agent(stock))
                    if any(w in msg_lower for w in ["gainer", "loser", "mover", "top", "market"]):
                        gl = tool.get_top_gainers_losers()
                        finance_data.append("\n=== TOP GAINERS ===")
                        for g in gl["gainers"]:
                            finance_data.append(tool.format_for_agent(g))
                        finance_data.append("\n=== TOP LOSERS ===")
                        for l in gl["losers"]:
                            finance_data.append(tool.format_for_agent(l))
                    context_parts.append("\n".join(finance_data))
                elif tool_name == "health_input":
                    context_parts.append(tool.format_for_agent(days=7))
                elif tool_name == "web_search":
                    news = tool.search_news(message, max_results=3)
                    formatted = tool.format_for_agent(news, max_chars=1500)
                    context_parts.append(f"=== CURRENT NEWS ===\n{formatted}")
            except Exception as e:
                context_parts.append(f"[Tool {tool_name} error: {str(e)}]")
        return "\n\n".join(context_parts)

    def _get_department_tools(self, config_path: str) -> list:
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f).get("tools", [])
        except Exception:
            return []

    def process(self, user_message: str) -> tuple:
        short_term.update_context({
            "last_message": user_message,
            "last_active": str(datetime.now()),
        })

        matches = self.registry.route(user_message, top_k=3, threshold=0.3)
        department_responses = []

        if matches:
            for match in matches:
                try:
                    agent = self.registry.get_agent(match["name"])
                    trust = self.feedback.get_trust_score(match["name"])
                    namespace = agent.config.get("memory_namespace", "general")
                    tools = self._get_department_tools(match["config_path"])

                    tool_context = ""
                    if tools:
                        tool_context = self._get_tool_context(user_message, tools)

                    relevant_memory = long_term.search(namespace, user_message, top_k=2)
                    context = {"current_time": str(datetime.now()), "trust_score": trust}
                    if tool_context:
                        context["live_data"] = tool_context
                    if relevant_memory:
                        context["memory"] = " | ".join(relevant_memory)

                    raw_response = agent.think(user_message, context=context)

                    # ── JUDICIARY REVIEW ──────────────────────────────
                    final_response = self.judiciary.enforce(
                        response=raw_response,
                        department=match["name"],
                        original_request=user_message,
                        context=context,
                    )
                    # ─────────────────────────────────────────────────

                    department_responses.append({
                        "department": match["name"],
                        "score": match["score"],
                        "response": final_response,
                    })

                    long_term.store(
                        namespace=namespace,
                        content=f"User: {user_message} | Response: {final_response}",
                        metadata={"type": "interaction", "date": str(datetime.now())}
                    )

                except Exception as e:
                    department_responses.append({
                        "department": match["name"],
                        "score": match["score"],
                        "response": f"[Error: {str(e)}]"
                    })

        if len(department_responses) > 1:
            synthesis_input = "\n\n".join([
                f"[{r['department']}]: {r['response']}"
                for r in department_responses
            ])
            final_response = self.think(
                f"Synthesize these into one unified reply:\n\n{synthesis_input}",
                context={"original_request": user_message}
            )
        elif len(department_responses) == 1:
            final_response = department_responses[0]["response"]
        else:
            final_response = self.think(user_message)

        return final_response, matches

    def record_feedback(self, department_name: str, score: int, reason: str = ""):
        self.feedback.record(department_name, score, reason)

    def get_trust_scores(self) -> str:
        return self.feedback.summary()

    def get_judiciary_stats(self) -> str:
        return self.judiciary.format_stats()