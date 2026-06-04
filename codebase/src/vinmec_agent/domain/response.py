from __future__ import annotations

from typing import Any


def base_response(
    reply: str,
    state: str,
    symptom_summary: str = "",
    confidence: float = 0.0,
    red_flag_risk: bool = False,
    suggested_specialties: list[dict[str, Any]] | None = None,
    slots: list[dict[str, Any]] | None = None,
    booking_draft: dict[str, Any] | None = None,
    callback_draft: dict[str, Any] | None = None,
    needs_more_info: bool = False,
    questions: list[str] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "reply": reply,
        "state": state,
        "symptom_summary": symptom_summary,
        "confidence": round(float(confidence), 2),
        "red_flag_risk": red_flag_risk,
        "suggested_specialties": suggested_specialties or [],
        "slots": slots or [],
        "booking_draft": booking_draft,
        "callback_draft": callback_draft,
        "needs_more_info": needs_more_info,
        "questions": questions or [],
        "meta": meta or {},
    }


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
