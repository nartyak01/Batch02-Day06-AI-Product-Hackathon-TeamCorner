from __future__ import annotations

import json
import os
import sys
from typing import Any

from vinmec_agent.application.ports import LLMClient
from vinmec_agent.application.prompt import SYSTEM_PROMPT
from vinmec_agent.domain.privacy import build_safe_history
from vinmec_agent.domain.text import parse_json_object
from vinmec_agent.infrastructure.mock_data import SPECIALTIES


class GeminiClient(LLMClient):
    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.model_name = (model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")).strip()

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
                "description": item["description"],
            }
            for item in SPECIALTIES
        ]
        return f"""
{SYSTEM_PROMPT}

Hãy phân tích lượt chat hiện tại và trả về JSON với schema:
{{
  "symptom_summary": "tóm tắt triệu chứng, không chứa PII",
  "confidence": 0.0,
  "red_flag_risk": false,
  "suggested_specialties": [
    {{"specialty_id": "gastro|general_internal|cardiology|respiratory|neurology|emergency", "name": "...", "reason": "...", "confidence": 0.0}}
  ],
  "needs_more_info": false,
  "questions": []
}}

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
