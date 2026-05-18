"""
orchestrator.py
---------------
The entry point of LifeOS. Every message you send goes here first.
The orchestrator decides which agent handles it and returns the response.
Right now it handles direct conversation. Department routing comes in Phase 2.
"""

from core.base_agent import BaseAgent
from core.memory import short_term, long_term
from datetime import datetime


class Orchestrator(BaseAgent):
    """
    The Chief of Staff of LifeOS.
    Receives your message, thinks about it, routes it, returns a response.
    """

    def __init__(self):
        super().__init__(
            name="Orchestrator",
            role="Chief of Staff of LifeOS. You are the first agent to receive every message from Belvin.",
            domain="Routing, coordination, synthesis, general intelligence",
            extra_prompt="""
You are the master coordinator. For now, handle all requests directly and
intelligently. As more departments come online, you will route to them.

At the start of every response, briefly acknowledge what type of request
this is (health, finance, knowledge, social, productivity, or general).
Then respond helpfully and concisely.

If you don't know something, say so honestly. Never fabricate.
"""
        )

    def process(self, user_message: str) -> str:
        """
        Main method. Takes user input, returns LifeOS response.
        Also updates short-term memory with session context.
        """
        # Update session context
        short_term.update_context({
            "last_message": user_message,
            "last_active": str(datetime.now()),
        })

        # Retrieve any relevant long-term memory
        relevant_memory = long_term.search("general", user_message, top_k=2)
        context = short_term.get_all()

        if relevant_memory:
            context["relevant_memory"] = " | ".join(relevant_memory)

        # Think and respond
        response = self.think(user_message, context=context)

        # Store this interaction in long-term memory
        long_term.store(
            namespace="general",
            content=f"User: {user_message} | LifeOS: {response}",
            metadata={"type": "conversation", "date": str(datetime.now())}
        )

        return response