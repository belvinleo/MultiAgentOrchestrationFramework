"""
base_agent.py
-------------
The parent class for every agent in LifeOS.
All agents inherit from this. It handles:
- LLM communication via Groq
- Constitution awareness
- Conversation history
- Logging
"""

import json
import logging
import os
from datetime import datetime
from groq import Groq
from core.config import (
    GROQ_API_KEY,
    MODEL_NAME,
    LOGS_PATH,
    load_constitution,
    get_hard_laws,
    get_soft_laws,
    get_core_values,
)

# Setup logging
os.makedirs(LOGS_PATH, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_PATH, "lifeos.log"),
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


class BaseAgent:
    """
    Every agent in LifeOS inherits from this class.

    Parameters:
        name        : Human-readable name of the agent
        role        : One-line description of what this agent does
        domain      : The subject area this agent specializes in
        extra_prompt: Any additional instructions specific to this agent
    """

    def __init__(
        self,
        name: str,
        role: str,
        domain: str,
        extra_prompt: str = "",
    ):
        self.name = name
        self.role = role
        self.domain = domain
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = MODEL_NAME
        self.conversation_history = []
        self.logger = logging.getLogger(self.name)

        # Load the constitution once at agent startup
        self.constitution = load_constitution()
        self.hard_laws = get_hard_laws(self.constitution)
        self.soft_laws = get_soft_laws(self.constitution)
        self.core_values = get_core_values(self.constitution)

        # Build the system prompt
        self.system_prompt = self._build_system_prompt(extra_prompt)
        self.logger.info(f"Agent '{self.name}' initialized.")

    def _build_system_prompt(self, extra_prompt: str) -> str:
        """
        Constructs the system prompt from constitution + agent role.
        Every agent knows the laws before it does anything.
        """
        return f"""
You are {self.name}, an agent inside LifeOS — a personal AI operating system.

YOUR ROLE: {self.role}
YOUR DOMAIN: {self.domain}

=== CONSTITUTION: HARD LAWS (NEVER VIOLATE) ===
{self.hard_laws}

=== CONSTITUTION: SOFT LAWS (FOLLOW BY DEFAULT) ===
{self.soft_laws}

=== CORE VALUES ===
{self.core_values}

=== ADDITIONAL INSTRUCTIONS ===
{extra_prompt}

Always act in the best interest of Belvin. Be concise, honest, and aligned
with the constitution above. If a request violates a hard law, refuse clearly
and explain why.
""".strip()

    def think(self, user_message: str, context: dict = None) -> str:
        """
        Send a message to the LLM and get a response.

        Parameters:
            user_message : The task or query for this agent
            context      : Optional dict of extra context (mood, time, etc.)

        Returns:
            The agent's response as a string
        """
        # Inject context into the message if provided
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            full_message = f"[CONTEXT]\n{context_str}\n\n[REQUEST]\n{user_message}"
        else:
            full_message = user_message

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": full_message
        })

        # Call the LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=1024,
            )

            reply = response.choices[0].message.content

            # Store the reply in history
            self.conversation_history.append({
                "role": "assistant",
                "content": reply
            })

            self.logger.info(f"Input: {user_message[:80]}... | Output: {reply[:80]}...")
            return reply

        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return f"[{self.name}] Error: {str(e)}"

    def reset_conversation(self):
        """Clear conversation history. Call between sessions."""
        self.conversation_history = []
        self.logger.info("Conversation history cleared.")

    def get_identity(self) -> dict:
        """Returns agent metadata. Used by the registry."""
        return {
            "name": self.name,
            "role": self.role,
            "domain": self.domain,
        }