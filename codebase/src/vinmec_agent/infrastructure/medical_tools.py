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

    def detect_specialty_override(self, text: str) -> dict[str, Any] | None:
        normalized = normalize_vietnamese(text)
        override_markers = [
            "toi muon kham",
            "muon kham",
            "doi sang",
            "chuyen sang",
            "chon khoa",
            "kham khoa",
            "kham chuyen khoa",
        ]
        if not any(marker in normalized for marker in override_markers):
            return None

        specialty_id = self._infer_specialty_id_from_text(text)
        if not specialty_id:
            return None

        specialty = next((item for item in get_specialties() if item["specialty_id"] == specialty_id), None)
        if not specialty:
            return None
        return self._specialty_response(specialty, "User chủ động đổi/chọn chuyên khoa này.", 1.0)

    def infer_specialty_hint(self, text: str) -> str | None:
        override = self.detect_specialty_override(text)
        if override:
            return str(override["specialty_id"])

        specialty_id = self._infer_specialty_id_from_text(text)
        return specialty_id or None

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
        if not agent_choices:
            inferred_specialty_id = self._infer_specialty_id_from_text(text)
            if inferred_specialty_id:
                agent_choices = [
                    {
                        "specialty_id": inferred_specialty_id,
                        "reason": self._routing_reason_for_specialty(inferred_specialty_id),
                    }
                ]

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

        default = next(
            (item for item in get_specialties() if item["specialty_id"] == "suc_khoe_tong_quat"),
            get_specialties()[0],
        )
        return [self._specialty_response(default, "Triệu chứng còn chung chung, nên khám tổng quát để được sàng lọc ban đầu.", 0.52)]

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
        valid_ids = {specialty["specialty_id"] for specialty in get_specialties(active_only=False)}
        return specialty_id if specialty_id in valid_ids else ""

    def _infer_specialty_id_from_text(self, text: str) -> str:
        normalized = normalize_vietnamese(text)
        for specialty in get_specialties():
            sid = str(specialty["specialty_id"])
            if any(contains_normalized_keyword(normalized, keyword) for keyword in [str(specialty.get("name", "")), sid]):
                return str(specialty["specialty_id"])
            if any(contains_normalized_keyword(normalized, keyword) for keyword in self._keyword_hints(sid)):
                return str(specialty["specialty_id"])
        return ""

    def _keyword_hints(self, specialty_id: str) -> list[str]:
        return {
            "tieu_hoa_gan_mat": [
                "dau bung",
                "dau da day",
                "dau thuong vi",
                "buon non",
                "non",
                "tieu chay",
                "day bung",
                "o chua",
            ],
            "tim_mach": [
                "dau nguc",
                "hoi hop",
                "tim dap nhanh",
                "tang huyet ap",
                "kho tho",
            ],
            "suc_khoe_phu_nu": [
                "mang thai",
                "thai",
                "phu khoa",
                "san khoa",
                "kinh nguyet",
                "ra mau am dao",
            ],
            "nhi": [
                "tre em",
                "be",
                "con toi",
                "tiem chung",
                "vacxin",
                "vaccine",
            ],
            "vacxin": [
                "tiem chung",
                "tiem phong",
                "vacxin",
                "vaccine",
            ],
            "nha_khoa_view": [
                "dau rang",
                "sau rang",
                "nha khoa",
                "rang",
            ],
            "chan_thuong_the_thao": [
                "chan thuong",
                "dau goi",
                "dau vai",
                "gay xuong",
                "sai khop",
            ],
            "than_kinh": [
                "dau dau",
                "chong mat",
                "te bi",
                "run",
            ],
            "mien_dich_di_ung": [
                "di ung",
                "phat ban",
                "may day",
                "ngua",
                "hen",
            ],
            "suc_khoe_tong_quat": [
                "kham tong quat",
                "suc khoe tong quat",
                "kiem tra suc khoe",
                "tong quat",
            ],
        }.get(specialty_id, [])

    def _routing_reason_for_specialty(self, specialty_id: str) -> str:
        return {
            "tieu_hoa_gan_mat": "Đau bụng, buồn nôn hoặc nôn thường phù hợp với chuyên khoa Tiêu hoá - Gan mật.",
            "tim_mach": "Đau ngực, hồi hộp hoặc khó thở cần được tim mạch đánh giá.",
            "suc_khoe_phu_nu": "Nhu cầu sản phụ khoa hoặc mang thai phù hợp với Sức khoẻ phụ nữ.",
            "nhi": "Triệu chứng ở trẻ em phù hợp với chuyên khoa Nhi.",
            "vacxin": "Nhu cầu tiêm chủng phù hợp với Trung tâm Vacxin.",
            "nha_khoa_view": "Triệu chứng răng miệng phù hợp với Nha khoa.",
            "chan_thuong_the_thao": "Chấn thương hoặc đau cơ xương khớp phù hợp với Chấn thương chỉnh hình.",
            "than_kinh": "Đau đầu, chóng mặt hoặc tê bì phù hợp với Thần kinh.",
            "mien_dich_di_ung": "Phát ban, ngứa hoặc dị ứng phù hợp với Miễn dịch - Dị ứng.",
            "suc_khoe_tong_quat": "Triệu chứng còn chung chung, nên khám tổng quát để được sàng lọc ban đầu.",
        }.get(specialty_id, "")


