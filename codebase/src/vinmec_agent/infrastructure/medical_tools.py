from __future__ import annotations

from typing import Any

from ...tools.medical import (
    check_red_flags,
    get_available_slots as backend_available_slots,
    get_doctors,
    get_facilities,
    get_slots,
    get_specialties,
    suggest_specialty as backend_suggest_specialty,
)
from ..domain.response import coerce_float
from ..domain.text import contains_normalized_keyword, normalize_vietnamese


LEGACY_SPECIALTY_ALIASES = {
    "gastro": "tieu_hoa_gan_mat",
    "general_internal": "suc_khoe_tong_quat",
    "cardiology": "tim_mach",
    "respiratory": "mien_dich_di_ung",
    "neurology": "than_kinh",
    "emergency": "cap_cuu",
}


class MedicalTools:
    """Adapter for Dat's agent, backed by the shared CSV/tool layer."""

    def detect_red_flags(self, text: str) -> dict[str, Any]:
        result = check_red_flags(text)
        return {
            "red_flag_risk": bool(result.get("is_red_flag")),
            "matched_keywords": result.get("matched_keywords", []),
            "reason": result.get("message", ""),
            "hotline": result.get("hotline", ""),
        }

    def detect_specialty_override(self, text: str) -> dict[str, Any] | None:
        normalized = normalize_vietnamese(text)
        override_markers = [
            "toi muon kham",
            "muon kham",
            "doi sang",
            "chuyen sang",
            "chon khoa",
            "kham khoa",
        ]
        if not any(marker in normalized for marker in override_markers):
            return None

        for specialty in get_specialties():
            sid = str(specialty["specialty_id"])
            if sid == "cap_cuu":
                continue
            keywords = [str(specialty.get("name", "")), sid]
            if any(contains_normalized_keyword(normalized, keyword) for keyword in keywords):
                return self._specialty_response(specialty, "User chủ động đổi/chọn chuyên khoa này.", 1.0)
        return None

    def infer_facility_id(self, text: str, context: dict[str, Any]) -> str:
        explicit = context.get("preferred_facility_id") or context.get("facility_id")
        if explicit:
            return str(explicit)

        normalized = normalize_vietnamese(text)
        for facility in get_facilities():
            fields = [
                facility.get("facility_id", ""),
                facility.get("name", ""),
                facility.get("city", ""),
                facility.get("district", ""),
                facility.get("address", ""),
            ]
            if any(normalize_vietnamese(str(field)) in normalized for field in fields if field):
                return str(facility["facility_id"])
        return "times_city"

    def suggest_specialty(
        self,
        symptom_summary: str,
        user_message: str,
        age_or_birth_year: str | int | None = None,
        facility_id: str | None = None,
        gemini_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        del age_or_birth_year
        text = f"{symptom_summary} {user_message}"
        override = self.detect_specialty_override(user_message)
        if override:
            return [override]
        agent_choices = self._agent_choices_from_gemini(gemini_result)

        if agent_choices:
            validated = backend_suggest_specialty(
                symptom_summary,
                agent_choices=agent_choices,
                facility_id=facility_id,
            )
            suggestions = [
                {
                    "specialty_id": item["specialty_id"],
                    "name": item["name"],
                    "reason": item["reason"],
                    "confidence": min(0.95, 0.58 + coerce_float(item.get("score"), 0.0) * 0.12),
                }
                for item in validated.get("suggested_specialties", [])
            ]
            if suggestions:
                return suggestions[:3]

        return self._score_specialties(text)[:3]

    def get_available_slots(self, specialty_id: str, facility_id: str | None = None) -> list[dict[str, Any]]:
        canonical_specialty_id = self._canonical_specialty_id(specialty_id)
        facility_id = facility_id or "times_city"
        result = backend_available_slots(canonical_specialty_id, facility_id)
        slots = result.get("slots", [])

        if not slots:
            fallback_facility = self._first_facility_for_specialty(canonical_specialty_id)
            if fallback_facility and fallback_facility != facility_id:
                result = backend_available_slots(canonical_specialty_id, fallback_facility)
                slots = result.get("slots", [])

        return [self._enrich_slot(slot) for slot in slots]

    def create_booking_draft(
        self,
        symptom_summary: str,
        facility_id: str | None,
        specialty_id: str,
        slot_id: str | None = None,
        status: str = "draft",
    ) -> dict[str, Any]:
        canonical_specialty_id = self._canonical_specialty_id(specialty_id)
        selected_facility_id = facility_id or self._first_facility_for_specialty(canonical_specialty_id) or "times_city"
        return {
            "facility_id": selected_facility_id,
            "facility_name": self.facility_name(selected_facility_id),
            "specialty_id": canonical_specialty_id,
            "specialty_name": self.specialty_name(canonical_specialty_id),
            "slot_id": slot_id,
            "reason_for_visit": symptom_summary,
            "status": status,
        }

    def specialty_name(self, specialty_id: str) -> str:
        canonical_id = self._canonical_specialty_id(specialty_id)
        for specialty in get_specialties():
            if specialty["specialty_id"] == canonical_id:
                return str(specialty["name"])
        return "Sức khoẻ tổng quát"

    def facility_name(self, facility_id: str | None) -> str:
        for facility in get_facilities():
            if facility["facility_id"] == facility_id:
                return str(facility["name"])
        return get_facilities()[0]["name"]

    def _agent_choices_from_gemini(self, gemini_result: dict[str, Any] | None) -> list[dict[str, str]]:
        raw = gemini_result.get("suggested_specialties", []) if gemini_result else []
        if not isinstance(raw, list):
            return []

        choices: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            specialty_id = self._canonical_specialty_id(str(item.get("specialty_id", "")))
            if not specialty_id:
                specialty_id = self._infer_specialty_id_from_text(str(item.get("name", "")))
            if specialty_id:
                choices.append(
                    {
                        "specialty_id": specialty_id,
                        "reason": str(item.get("reason", "")),
                    }
                )
        return choices

    def _score_specialties(self, text: str) -> list[dict[str, Any]]:
        normalized = normalize_vietnamese(text)
        scored: list[dict[str, Any]] = []

        for specialty in get_specialties():
            if specialty["specialty_id"] == "cap_cuu":
                continue

            searchable = normalize_vietnamese(
                f"{specialty.get('name', '')} {specialty.get('description', '')}"
            )
            tokens = [token for token in normalized.split() if len(token) >= 3]
            score = sum(1 for token in tokens if token in searchable)

            for keyword in self._keyword_hints(str(specialty["specialty_id"])):
                if contains_normalized_keyword(normalized, keyword):
                    score += 3 if " " in normalize_vietnamese(keyword) else 2

            if score > 0:
                scored.append(self._specialty_response(specialty, specialty.get("description", ""), min(0.9, 0.48 + score * 0.08)))

        if not scored:
            default = next(
                (item for item in get_specialties() if item["specialty_id"] == "suc_khoe_tong_quat"),
                get_specialties()[0],
            )
            scored.append(
                self._specialty_response(
                    default,
                    "Triệu chứng còn chung chung, nên khám tổng quát để được sàng lọc ban đầu.",
                    0.52,
                )
            )

        scored.sort(key=lambda item: item.get("confidence", 0), reverse=True)
        return scored

    def _specialty_response(self, specialty: dict[str, Any], reason: str, confidence: float) -> dict[str, Any]:
        return {
            "specialty_id": specialty["specialty_id"],
            "name": specialty["name"],
            "reason": reason or specialty.get("description", ""),
            "confidence": round(confidence, 2),
        }

    def _enrich_slot(self, slot: dict[str, Any]) -> dict[str, Any]:
        doctors = {doctor["doctor_id"]: doctor for doctor in get_doctors(active_only=False)}
        facilities = {facility["facility_id"]: facility for facility in get_facilities()}
        doctor = doctors.get(slot.get("doctor_id"), {})
        facility = facilities.get(slot.get("facility_id"), {})
        return {
            **slot,
            "available": bool(slot.get("available")),
            "doctor_name": doctor.get("name", ""),
            "doctor_title": doctor.get("title", ""),
            "facility_name": facility.get("name", ""),
        }

    def _first_facility_for_specialty(self, specialty_id: str) -> str | None:
        for slot in get_slots(specialty_id=specialty_id, available_only=True):
            return str(slot["facility_id"])
        return None

    def _canonical_specialty_id(self, specialty_id: str) -> str:
        candidate = LEGACY_SPECIALTY_ALIASES.get(specialty_id, specialty_id)
        valid_ids = {specialty["specialty_id"] for specialty in get_specialties(active_only=False)}
        return candidate if candidate in valid_ids else ""

    def _infer_specialty_id_from_text(self, text: str) -> str:
        normalized = normalize_vietnamese(text)
        for specialty in get_specialties():
            sid = str(specialty["specialty_id"])
            if any(contains_normalized_keyword(normalized, keyword) for keyword in self._keyword_hints(sid) + [str(specialty.get("name", "")), sid]):
                return str(specialty["specialty_id"])
        return ""

    def _keyword_hints(self, specialty_id: str) -> list[str]:
        return {
            "tim_mach": ["đau ngực", "hồi hộp", "tim", "huyết áp", "khó thở"],
            "tieu_hoa_gan_mat": ["đau bụng", "tiêu chảy", "buồn nôn", "nôn", "ợ chua"],
            "nhi": ["trẻ em", "bé", "con tôi", "sốt", "ho"],
            "mien_dich_di_ung": ["dị ứng", "phát ban", "mày đay", "ngứa", "hen"],
            "than_kinh": ["đau đầu", "chóng mặt", "tê bì", "run"],
            "suc_khoe_tong_quat": ["mệt mỏi", "khám sức khỏe", "không rõ", "tổng quát"],
            "chan_thuong_the_thao": ["chấn thương", "đau gối", "đau vai", "gãy xương"],
            "suc_khoe_phu_nu": ["phụ khoa", "kinh nguyệt", "mang thai"],
            "vacxin": ["vaccine", "vacxin", "tiêm chủng"],
            "nha_khoa_view": ["đau răng", "nha khoa", "sâu răng"],
        }.get(specialty_id, [])
