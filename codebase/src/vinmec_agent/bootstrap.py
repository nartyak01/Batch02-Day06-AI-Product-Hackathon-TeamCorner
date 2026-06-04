from __future__ import annotations

from functools import lru_cache
from typing import Any

from .application.agent_service import BookingAgent
from .infrastructure.gemini_client import GeminiClient
from .infrastructure.medical_tools import MedicalTools


@lru_cache(maxsize=1)
def get_agent() -> BookingAgent:
    return BookingAgent(
        tools=MedicalTools(),
        llm_client=GeminiClient(),
    )


def run_agent_turn(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return get_agent().run_turn(user_message=user_message, history=history, context=context)
