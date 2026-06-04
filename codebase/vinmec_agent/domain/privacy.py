from __future__ import annotations

import re
from typing import Any


PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "phone": re.compile(r"(?:\+?84|0)(?:\d[\s.\-]?){9}\b"),
    "email": re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE),
    "national_id": re.compile(r"\b\d{9}\b|\b\d{12}\b"),
}


def detect_pii(text: str) -> list[str]:
    hits: list[str] = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            hits.append(pii_type)
    return hits


def build_safe_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    safe: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user"))[:20]
        content = str(item.get("content", ""))
        if detect_pii(content):
            content = "[PII_REMOVED]"
        safe.append({"role": role, "content": content[:500]})
    return safe
