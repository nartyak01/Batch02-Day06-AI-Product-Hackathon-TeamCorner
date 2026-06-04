"""Validate and enrich specialty choices from the AI agent (not keyword routing)."""

from __future__ import annotations

from typing import Any, TypedDict

from .catalog import get_specialties
from .red_flags import check_red_flags
from .specialty_catalog import get_specialty_catalog, format_specialty_catalog_for_prompt


class AgentSpecialtyChoice(TypedDict, total=False):
    specialty_id: str
    reason: str


class SuggestedSpecialty(TypedDict):
    specialty_id: str
    name: str
    reason: str
    score: float


class SuggestSpecialtyResult(TypedDict):
    red_flag_risk: bool
    suggested_specialties: list[SuggestedSpecialty]
    confidence: str
    specialty_catalog: list[dict[str, str]]
    routing_mode: str


def _catalog_by_id() -> dict[str, dict[str, Any]]:
    return {s["specialty_id"]: s for s in get_specialties()}


def suggest_specialty(
    symptom_summary: str,
    *,
    agent_choices: list[AgentSpecialtyChoice] | None = None,
    facility_id: str | None = None,
    max_results: int = 3,
) -> SuggestSpecialtyResult:
    """
    Routing flow:
    1. check_red_flags(symptom_summary) — rule layer, always first.
    2. If no agent_choices: return specialty_catalog for Gemini to decide (routing_mode=agent).
    3. If agent_choices: validate specialty_id against CSV, return enriched suggestions.
    """
    del facility_id

    catalog = get_specialty_catalog()
    red = check_red_flags(symptom_summary)

    if red["is_red_flag"]:
        return {
            "red_flag_risk": True,
            "suggested_specialties": [],
            "confidence": "high",
            "specialty_catalog": catalog,
            "routing_mode": "red_flag",
        }

    if not agent_choices:
        return {
            "red_flag_risk": False,
            "suggested_specialties": [],
            "confidence": "defer_to_agent",
            "specialty_catalog": catalog,
            "routing_mode": "agent",
        }

    by_id = _catalog_by_id()
    suggestions: list[SuggestedSpecialty] = []

    for i, choice in enumerate(agent_choices[:max_results]):
        sid = (choice.get("specialty_id") or "").strip()
        if not sid or sid not in by_id:
            continue
        spec = by_id[sid]
        if sid == "cap_cuu":
            continue
        reason = (choice.get("reason") or "").strip() or spec.get("description", "")
        suggestions.append(
            {
                "specialty_id": sid,
                "name": spec.get("name", ""),
                "reason": reason,
                "score": float(max_results - i),
            }
        )

    confidence = "high" if len(suggestions) >= 2 else ("medium" if suggestions else "low")

    return {
        "red_flag_risk": False,
        "suggested_specialties": suggestions,
        "confidence": confidence,
        "specialty_catalog": catalog,
        "routing_mode": "agent_validated",
    }
