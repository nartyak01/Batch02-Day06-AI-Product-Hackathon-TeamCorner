from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from ..application.ports import LLMClient
from ..application.prompt import SYSTEM_PROMPT
from ..domain.privacy import build_safe_history
from ..domain.text import parse_json_object
from ...tools.medical import get_specialties


class GeminiClient(LLMClient):
    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        env_file = _load_backend_env()
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY") or env_file.get("GEMINI_API_KEY", "")).strip()
        self.model_name = (
            model_name
            or os.getenv("GEMINI_MODEL")
            or env_file.get("GEMINI_MODEL")
            or "gemini-3.1-flash-lite"
        ).strip()

    def plan_next_action(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
        observations: dict[str, Any],
        available_tools: list[str],
    ) -> dict[str, Any] | None:
        if not self.api_key:
            return None

        prompt = self._build_planner_prompt(user_message, history, context, observations, available_tools)
        try:
            result_text = self._call_google_genai(prompt)
            parsed = parse_json_object(result_text)
            if not isinstance(parsed, dict):
                return None
            parsed["planner_model"] = self.model_name
            return parsed
        except Exception as exc:  # pragma: no cover - external service safety
            self._debug_log(f"Gemini planner failed: {exc}")
            return None

    def analyze_intake(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.api_key:
            return None

        prompt = self._build_prompt(user_message, history, context)
        try:
            result_text = self._call_google_genai(prompt)
            parsed = parse_json_object(result_text)
            if not isinstance(parsed, dict):
                return None
            parsed["model_used"] = self.model_name
            return parsed
        except Exception as exc:  # pragma: no cover - external service safety
            self._debug_log(f"Gemini failed: {exc}")
            return None

    def _build_planner_prompt(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
        observations: dict[str, Any],
        available_tools: list[str],
    ) -> str:
        safe_history = build_safe_history(history)
        return f"""
{SYSTEM_PROMPT}

Bạn đang là planner trong vòng ReAct. Hệ thống Python đã kiểm tra PII/red flag trước khi gọi bạn.
Hãy chọn đúng 1 action tiếp theo từ danh sách available_tools.

available_tools:
{json.dumps(available_tools, ensure_ascii=False)}

observations an toàn hiện có:
{json.dumps(observations, ensure_ascii=False)}

context hiện có:
{json.dumps(context, ensure_ascii=False)}

history đã lọc PII:
{json.dumps(safe_history[-6:], ensure_ascii=False)}

user_message:
{user_message}

Chỉ trả JSON action, không markdown, không giải thích ngoài JSON.
"""

    def _build_prompt(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> str:
        safe_history = build_safe_history(history)
        specialties = [
            {
                "specialty_id": item["specialty_id"],
                "name": item["name"],
                "description": item.get("description", ""),
            }
            for item in get_specialties()
        ]
        specialty_ids = ", ".join(f'"{item["specialty_id"]}"' for item in specialties)
        return f"""
{SYSTEM_PROMPT}

Routing notes:
- If the symptom intake is missing key clinical routing details, set needs_more_info=true and ask 1-2 detailed Vietnamese questions.
- Key routing details: main symptom, body location, onset/duration, severity, progression, associated symptoms, age/birth year, relevant conditions/medications, preferred facility/time.
- When enough detail is available, choose suggested_specialties from the valid catalog yourself. Do not rely on keyword-only routing.

Hãy phân tích lượt chat hiện tại và trả về JSON với schema:
{{
  "symptom_summary": "tóm tắt triệu chứng, không chứa PII",
  "confidence": 0.0,
  "red_flag_risk": false,
  "suggested_specialties": [
    {{"specialty_id": "một trong các id bên dưới", "name": "...", "reason": "...", "confidence": 0.0}}
  ],
  "needs_more_info": false,
  "questions": []
}}

Valid specialty_id:
{specialty_ids}

Danh sách khoa hợp lệ:
{json.dumps(specialties, ensure_ascii=False)}

Context hiện có:
{json.dumps(context, ensure_ascii=False)}

History đã lọc PII:
{json.dumps(safe_history[-6:], ensure_ascii=False)}

User message:
{user_message}
"""

    def _call_google_genai(self, prompt: str) -> str:
        try:
            from google import genai  # type: ignore

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(model=self.model_name, contents=prompt)
            text = getattr(response, "text", None)
            if text:
                return text
        except ImportError:
            pass

        try:
            import google.generativeai as legacy_genai  # type: ignore

            legacy_genai.configure(api_key=self.api_key)
            model = legacy_genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
            if text:
                return text
        except ImportError as exc:
            raise RuntimeError("Missing Gemini SDK. Install google-genai or google-generativeai.") from exc

        raise RuntimeError("Gemini response did not include text.")

    def _debug_log(self, message: str) -> None:
        if os.getenv("AGENT_DEBUG") == "1":
            print(f"[agent-debug] {message}", file=sys.stderr)


def _load_backend_env() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
