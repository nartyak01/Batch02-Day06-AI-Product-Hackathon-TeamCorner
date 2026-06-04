from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from vinmec_agent.domain.response import coerce_float
from vinmec_agent.domain.text import contains_normalized_keyword, normalize_vietnamese
from vinmec_agent.infrastructure.mock_data import DOCTORS, FACILITIES, RED_FLAG_KEYWORDS, SPECIALTIES


class MockMedicalTools:
    """Temporary tools that mimic the teammate-owned tools/database layer."""

    def detect_red_flags(self, text: str) -> dict[str, Any]:
        normalized = normalize_vietnamese(text)
        matched = [keyword for keyword in RED_FLAG_KEYWORDS if contains_normalized_keyword(normalized, keyword)]
        return {
            "red_flag_risk": bool(matched),
            "matched_keywords": [normalize_vietnamese(keyword) for keyword in matched],
            "reason": "Có dấu hiệu nguy hiểm cần được tư vấn/hỗ trợ y tế sớm." if matched else "",
        }

    def detect_specialty_override(self, text: str) -> dict[str, Any] | None:
        normalized = normalize_vietnamese(text)
        override_markers = ["toi muon kham", "muon kham", "doi sang", "chuyen sang", "khong", "chon khoa"]
        if not any(marker in normalized for marker in override_markers):
            return None

        aliases = {
            "gastro": ["tieu hoa", "khoa tieu hoa"],
            "general_internal": ["noi tong quat", "khoa noi tong quat", "noi khoa"],
            "cardiology": ["tim mach", "khoa tim mach"],
            "respiratory": ["ho hap", "khoa ho hap"],
            "neurology": ["than kinh", "khoa than kinh"],
            "emergency": ["cap cuu", "khoa cap cuu"],
        }
        for specialty in SPECIALTIES:
            if any(alias in normalized for alias in aliases.get(specialty["specialty_id"], [])):
                return {
                    "specialty_id": specialty["specialty_id"],
                    "name": specialty["name"],
                    "reason": "User chủ động đổi/chọn chuyên khoa này.",
                    "confidence": 1.0,
                }
        return None

    def infer_facility_id(self, text: str, context: dict[str, Any]) -> str:
        explicit = context.get("preferred_facility_id") or context.get("facility_id")
        if explicit:
            return str(explicit)

        normalized = normalize_vietnamese(text)
        if "smart" in normalized or "tay mo" in normalized or "nam tu liem" in normalized:
            return "smart_city"
        if "ha long" in normalized or "quang ninh" in normalized:
            return "vinmec_halong"
        return "times_city"

    def suggest_specialty(
        self,
        symptom_summary: str,
        user_message: str,
        age_or_birth_year: str | int | None = None,
        facility_id: str | None = None,
        gemini_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        rule_suggestions = self._score_specialties(f"{symptom_summary} {user_message}")
        gemini_suggestions = self._normalize_specialty_suggestions(
            gemini_result.get("suggested_specialties", []) if gemini_result else []
        )
        merged = self._merge_suggestions(rule_suggestions, gemini_suggestions)
        return merged[:3]

    def get_available_slots(self, specialty_id: str, facility_id: str | None = None) -> list[dict[str, Any]]:
        facility_id = facility_id or "times_city"
        doctors = [
            doctor
            for doctor in DOCTORS
            if doctor["specialty_id"] == specialty_id and doctor["facility_id"] == facility_id and doctor["active"]
        ]
        if not doctors:
            doctors = [doctor for doctor in DOCTORS if doctor["specialty_id"] == specialty_id and doctor["active"]]
        if not doctors:
            doctors = [doctor for doctor in DOCTORS if doctor["specialty_id"] == "general_internal" and doctor["active"]]

        today = datetime.now().date()
        times = ["09:00", "14:00", "16:30", "10:30"]
        slots: list[dict[str, Any]] = []
        for index in range(4):
            doctor = doctors[index % len(doctors)]
            day = today + timedelta(days=index)
            slots.append(
                {
                    "slot_id": f"{facility_id}_{specialty_id}_{day.isoformat()}_{times[index].replace(':', '')}",
                    "facility_id": doctor["facility_id"],
                    "facility_name": self.facility_name(doctor["facility_id"]),
                    "specialty_id": specialty_id,
                    "doctor_id": doctor["doctor_id"],
                    "doctor_name": doctor["name"],
                    "date": day.isoformat(),
                    "time": times[index],
                    "available": True,
                }
            )
        return slots

    def create_booking_draft(
        self,
        symptom_summary: str,
        facility_id: str | None,
        specialty_id: str,
        slot_id: str | None = None,
        status: str = "draft",
    ) -> dict[str, Any]:
        return {
            "facility_id": facility_id or "times_city",
            "facility_name": self.facility_name(facility_id),
            "specialty_id": specialty_id,
            "specialty_name": self.specialty_name(specialty_id),
            "slot_id": slot_id,
            "reason_for_visit": symptom_summary,
            "status": status,
        }

    def specialty_name(self, specialty_id: str) -> str:
        for specialty in SPECIALTIES:
            if specialty["specialty_id"] == specialty_id:
                return specialty["name"]
        return "Nội tổng quát"

    def facility_name(self, facility_id: str | None) -> str:
        for facility in FACILITIES:
            if facility["facility_id"] == facility_id:
                return facility["name"]
        return FACILITIES[0]["name"]

    def _score_specialties(self, text: str) -> list[dict[str, Any]]:
        normalized = normalize_vietnamese(text)
        scored: list[dict[str, Any]] = []

        for specialty in SPECIALTIES:
            if specialty["specialty_id"] == "emergency":
                continue
            score = 0
            matched_keywords: list[str] = []
            for keyword in specialty["keywords"]:
                normalized_keyword = normalize_vietnamese(keyword)
                if contains_normalized_keyword(normalized, normalized_keyword):
                    score += 2 if len(normalized_keyword.split()) > 1 else 1
                    matched_keywords.append(keyword)

            if score > 0:
                confidence = min(0.9, 0.48 + score * 0.12)
                scored.append(
                    {
                        "specialty_id": specialty["specialty_id"],
                        "name": specialty["name"],
                        "reason": self._build_reason(specialty, matched_keywords),
                        "confidence": round(confidence, 2),
                    }
                )

        if not scored:
            scored.append(
                {
                    "specialty_id": "general_internal",
                    "name": "Nội tổng quát",
                    "reason": "Triệu chứng còn chung chung, nên khám Nội tổng quát để được sàng lọc ban đầu.",
                    "confidence": 0.52,
                }
            )

        scored.sort(key=lambda item: item.get("confidence", 0), reverse=True)
        return scored

    def _build_reason(self, specialty: dict[str, Any], matched_keywords: list[str]) -> str:
        if matched_keywords:
            keywords = ", ".join(matched_keywords[:3])
            return f"Phù hợp với các dấu hiệu bạn mô tả: {keywords}."
        return specialty["description"]

    def _normalize_specialty_suggestions(self, raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            return []

        valid_ids = {item["specialty_id"]: item for item in SPECIALTIES}
        normalized: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            specialty_id = str(item.get("specialty_id", "")).strip()
            if specialty_id not in valid_ids:
                specialty_id = self._infer_specialty_id_from_name(str(item.get("name", "")))
            if specialty_id not in valid_ids:
                continue
            specialty = valid_ids[specialty_id]
            normalized.append(
                {
                    "specialty_id": specialty_id,
                    "name": item.get("name") or specialty["name"],
                    "reason": item.get("reason") or specialty["description"],
                    "confidence": round(coerce_float(item.get("confidence"), 0.62), 2),
                }
            )
        return normalized

    def _infer_specialty_id_from_name(self, name: str) -> str:
        normalized_name = normalize_vietnamese(name)
        for specialty in SPECIALTIES:
            if normalize_vietnamese(specialty["name"]) in normalized_name:
                return specialty["specialty_id"]
        return ""

    def _merge_suggestions(
        self,
        rule_suggestions: list[dict[str, Any]],
        gemini_suggestions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged_by_id: dict[str, dict[str, Any]] = {}
        for item in rule_suggestions + gemini_suggestions:
            specialty_id = item.get("specialty_id")
            if not specialty_id:
                continue
            if specialty_id not in merged_by_id:
                merged_by_id[specialty_id] = item
            else:
                existing = merged_by_id[specialty_id]
                existing["confidence"] = max(
                    coerce_float(existing.get("confidence"), 0.0),
                    coerce_float(item.get("confidence"), 0.0),
                )
                if not existing.get("reason") and item.get("reason"):
                    existing["reason"] = item["reason"]

        result = list(merged_by_id.values())
        result.sort(key=lambda item: item.get("confidence", 0), reverse=True)
        return result
