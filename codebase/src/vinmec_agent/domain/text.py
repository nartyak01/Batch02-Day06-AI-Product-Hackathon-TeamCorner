from __future__ import annotations

import re
import unicodedata


def normalize_vietnamese(text: str) -> str:
    lowered = text.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    no_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    no_marks = no_marks.replace("đ", "d")
    return re.sub(r"\s+", " ", no_marks).strip()


def contains_normalized_keyword(normalized_text: str, keyword: str) -> bool:
    normalized_keyword = normalize_vietnamese(keyword)
    if not normalized_keyword:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def parse_json_object(text: str) -> dict | None:
    if not text:
        return None

    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()

    import json

    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None
