"""Structured flow logging — no PII in log lines."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CODEBASE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LOG_FILE = _CODEBASE_ROOT / "log" / "log.json"

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "phone": re.compile(r"(?:\+?84|0)(?:\d[\s.\-]?){9}\b"),
    "email": re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE),
    "national_id": re.compile(r"\b\d{9}\b|\b\d{12}\b"),
}


def _detect_pii(text: str) -> list[str]:
    return [name for name, pattern in _PII_PATTERNS.items() if pattern.search(text)]


def _build_safe_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
    safe: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "user"))[:20]
        content = str(item.get("content", ""))
        if _detect_pii(content):
            content = "[PII_REMOVED]"
        safe.append({"role": role, "content": content[:500]})
    return safe

_CONFIGURED = False


def flow_log_enabled() -> bool:
    return os.getenv("FLOW_LOG", "1").strip().lower() in ("1", "true", "yes")


def _event_source(event: str) -> str:
    if event.startswith("agent_") or event == "gemini_debug":
        return "agent"
    return "backend"


def _should_persist_event(event: str) -> bool:
    """Only agent + backend API events go to log.json (no frontend)."""
    if event.startswith("agent_") or event.startswith("api_") or event.startswith("booking_"):
        return True
    return event in ("gemini_debug",)


def flow_log_file_path() -> Path:
    raw = (os.getenv("FLOW_LOG_FILE") or "").strip()
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else _CODEBASE_ROOT / path
    return _DEFAULT_LOG_FILE


def _append_log_file(event: str, fields: dict[str, Any]) -> None:
    if not _should_persist_event(event):
        return
    path = flow_log_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": _event_source(event),
        "event": event,
        **fields,
    }
    records: list[Any] = []
    if path.exists() and path.stat().st_size > 0:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                records = loaded
        except json.JSONDecodeError:
            records = []
    records.append(entry)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logger = logging.getLogger("vinmec.flow")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [vinmec.flow] %(message)s", datefmt="%H:%M:%S")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO if flow_log_enabled() else logging.WARNING)
    logger.propagate = False
    _CONFIGURED = True


def redact_text(text: str, *, max_len: int = 160) -> str:
    if not text or _detect_pii(text):
        return "[PII_REDACTED]" if text else ""
    compact = " ".join(text.strip().split())
    if len(compact) <= max_len:
        return compact
    return f"{compact[:max_len]}…"


def log_event(event: str, **fields: Any) -> None:
    if not flow_log_enabled():
        return
    _configure()
    payload = json.dumps(fields, ensure_ascii=False, default=str)
    logging.getLogger("vinmec.flow").info("%s %s", event, payload)
    try:
        _append_log_file(event, fields)
    except OSError as exc:
        logging.getLogger("vinmec.flow").warning("flow log file write failed: %s", exc)


def summarize_agent_response(result: dict[str, Any]) -> dict[str, Any]:
    meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
    return {
        "state": result.get("state"),
        "reply_preview": redact_text(str(result.get("reply", ""))),
        "needs_more_info": result.get("needs_more_info"),
        "red_flag_risk": result.get("red_flag_risk"),
        "specialties_count": len(result.get("suggested_specialties") or []),
        "slots_count": len(result.get("slots") or []),
        "has_booking_draft": bool(result.get("booking_draft")),
        "has_callback_draft": bool(result.get("callback_draft")),
        "guard": meta.get("guard"),
        "react_trace": meta.get("react_trace"),
        "pii_types": meta.get("pii_types"),
    }


def log_agent_request(
    user_message: str,
    history: list[dict[str, Any]] | None,
    context: dict[str, Any] | None,
) -> float:
    history = history or []
    context = context or {}
    safe_context = {
        k: v
        for k, v in context.items()
        if k
        not in ("name", "phone", "email", "dob", "patient_name", "patient_phone", "patient_email")
    }
    log_event(
        "agent_turn_request",
        input_preview=redact_text(user_message),
        input_len=len(user_message or ""),
        history_turns=len(history),
        safe_history_tail=_build_safe_history(history[-4:]),
        context=safe_context,
    )
    return time.perf_counter()


def log_agent_response(result: dict[str, Any], *, started_at: float) -> None:
    duration_ms = round((time.perf_counter() - started_at) * 1000)
    log_event("agent_turn_response", duration_ms=duration_ms, **summarize_agent_response(result))


def log_react_step(step: int, action: str, planner: str, observation: str) -> None:
    log_event(
        "agent_react_step",
        step=step,
        action=action,
        planner=planner,
        observation=observation[:200] if observation else "ok",
    )
