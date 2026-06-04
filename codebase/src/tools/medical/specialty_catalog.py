"""Specialty catalog for AI agent — descriptions drive routing, not keywords."""

from __future__ import annotations

from typing import Any, TypedDict

from .catalog import get_specialties


class SpecialtyForAgent(TypedDict):
    specialty_id: str
    name: str
    description: str


def get_specialty_catalog(*, include_emergency: bool = False) -> list[SpecialtyForAgent]:
    """Return active specialties with clinical descriptions for Gemini / tool context."""
    out: list[SpecialtyForAgent] = []
    for spec in get_specialties():
        sid = spec.get("specialty_id", "")
        if sid == "cap_cuu" and not include_emergency:
            continue
        out.append(
            {
                "specialty_id": sid,
                "name": spec.get("name", ""),
                "description": spec.get("description", ""),
            }
        )
    return out


def format_specialty_catalog_for_prompt(*, include_emergency: bool = False) -> str:
    """Plain-text block to inject into system prompt or tool result."""
    lines = ["Danh sách chuyên khoa (đọc mô tả để khớp triệu chứng):"]
    for item in get_specialty_catalog(include_emergency=include_emergency):
        lines.append(f"- [{item['specialty_id']}] {item['name']}: {item['description']}")
    return "\n".join(lines)
