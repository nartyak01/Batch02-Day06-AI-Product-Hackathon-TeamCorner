from __future__ import annotations

from typing import Any, Protocol


class AgentTools(Protocol):
    def detect_red_flags(self, text: str) -> dict[str, Any]: ...

    def detect_specialty_override(self, text: str) -> dict[str, Any] | None: ...

    def infer_facility_id(self, text: str, context: dict[str, Any]) -> str: ...

    def suggest_specialty(
        self,
        symptom_summary: str,
        user_message: str,
        age_or_birth_year: str | int | None = None,
        facility_id: str | None = None,
        gemini_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_available_slots(self, specialty_id: str, facility_id: str | None = None) -> list[dict[str, Any]]: ...

    def create_booking_draft(
        self,
        symptom_summary: str,
        facility_id: str | None,
        specialty_id: str,
        slot_id: str | None = None,
        status: str = "draft",
    ) -> dict[str, Any]: ...

    def specialty_name(self, specialty_id: str) -> str: ...

    def facility_name(self, facility_id: str | None) -> str: ...


class LLMClient(Protocol):
    def analyze_intake(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any] | None: ...
