"""Red-flag keyword rules — run before normal booking routing."""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict


class RedFlagResult(TypedDict):
    is_red_flag: bool
    message: str
    hotline: str
    matched_keywords: list[str]


HOTLINE = "1900 232389"

_RED_FLAG_RULES: list[tuple[str, list[str]]] = [
    (
        "Triệu chứng có dấu hiệu nguy hiểm. Vui lòng gọi cấp cứu hoặc đến khoa Cấp cứu ngay.",
        [
            "đau ngực dữ",
            "đau ngực",
            "khó thở",
            "khó thở nặng",
            "choáng",
            "ngất",
            "yếu liệt",
            "chảy máu nhiều",
            "co giật",
            "mất ý thức",
        ],
    ),
]


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def check_red_flags(text: str) -> RedFlagResult:
    normalized = _normalize(text)
    matched: list[str] = []
    message = ""

    for rule_message, keywords in _RED_FLAG_RULES:
        for kw in keywords:
            if _normalize(kw) in normalized:
                matched.append(kw)
                if not message:
                    message = rule_message

    is_red_flag = len(matched) > 0
    return {
        "is_red_flag": is_red_flag,
        "message": message if is_red_flag else "",
        "hotline": HOTLINE if is_red_flag else "",
        "matched_keywords": matched,
    }
