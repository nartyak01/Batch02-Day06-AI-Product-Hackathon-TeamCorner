from __future__ import annotations

import re
from typing import Any

from vinmec_agent.application.ports import AgentTools, LLMClient
from vinmec_agent.domain.constants import (
    STATE_ESCALATION,
    STATE_NEED_MORE_INFO,
    STATE_PII_BLOCKED,
    STATE_READY_FOR_FORM,
    STATE_SUGGESTING_SLOTS,
)
from vinmec_agent.domain.privacy import detect_pii
from vinmec_agent.domain.response import base_response, coerce_float
from vinmec_agent.domain.text import contains_normalized_keyword, normalize_vietnamese


class BookingAgent:
    def __init__(self, tools: AgentTools, llm_client: LLMClient) -> None:
        self.tools = tools
        self.llm_client = llm_client

    def run_turn(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        history = history or []
        context = context or {}
        message = (user_message or "").strip()

        react_state: dict[str, Any] = {
            "message": message,
            "history": history,
            "context": context,
            "observations": {},
            "trace": [],
        }

        # Explicit ReAct loop:
        # 1. Decide the next action from current observations.
        # 2. Run that tool/action.
        # 3. Store observation.
        # 4. Repeat until a final response is produced.
        for step_index in range(12):
            action = self._decide_next_action(react_state)
            observation = self._run_react_action(action, react_state)
            react_state["trace"].append(
                {
                    "step": step_index + 1,
                    "action": action,
                    "observation": observation.get("summary", "ok"),
                }
            )

            final_response = observation.get("final_response")
            if final_response:
                final_response.setdefault("meta", {})
                final_response["meta"]["react_trace"] = react_state["trace"]
                return final_response

        return base_response(
            reply="Agent chưa hoàn tất được vòng xử lý. Vui lòng thử lại hoặc chuyển sang callback.",
            state=STATE_NEED_MORE_INFO,
            needs_more_info=True,
            meta={"react_trace": react_state["trace"], "error": "max_react_steps_reached"},
        )

    def _decide_next_action(self, react_state: dict[str, Any]) -> str:
        message = react_state["message"]
        context = react_state["context"]
        observations = react_state["observations"]

        if not message:
            return "final_empty_message"
        if "pii_hits" not in observations:
            return "check_pii"
        if observations["pii_hits"]:
            return "final_pii_blocked"
        if "red_flag_result" not in observations:
            return "check_red_flags"
        if observations["red_flag_result"]["red_flag_risk"]:
            return "final_escalation"
        if "override_specialty" not in observations:
            return "check_specialty_override"
        if observations["override_specialty"]:
            return "final_specialty_override"
        if context.get("selected_slot_id") and context.get("selected_specialty_id"):
            return "final_ready_for_form"
        if "needs_more_info" not in observations:
            return "check_clarifying_need"
        if observations["needs_more_info"]:
            return "final_clarifying_question"
        if "gemini_result" not in observations:
            return "llm_analyze_intake"
        if "facility_id" not in observations:
            return "infer_facility"
        if "suggestions" not in observations:
            return "suggest_specialty"
        if "slots" not in observations:
            return "get_available_slots"
        if "booking_draft" not in observations:
            return "create_booking_draft"
        return "final_booking_suggestion"

    def _run_react_action(self, action: str, react_state: dict[str, Any]) -> dict[str, Any]:
        message = react_state["message"]
        history = react_state["history"]
        context = react_state["context"]
        observations = react_state["observations"]

        if action == "final_empty_message":
            return {
                "summary": "asked_user_for_initial_symptom",
                "final_response": base_response(
                    reply="Bạn vui lòng mô tả ngắn gọn triệu chứng hiện tại để tôi hỗ trợ gợi ý chuyên khoa.",
                    state=STATE_NEED_MORE_INFO,
                    needs_more_info=True,
                    questions=["Bạn đang gặp triệu chứng gì và triệu chứng bắt đầu từ khi nào?"],
                ),
            }

        if action == "check_pii":
            pii_hits = detect_pii(message)
            observations["pii_hits"] = pii_hits
            return {"summary": "pii_detected" if pii_hits else "pii_clear"}

        if action == "final_pii_blocked":
            return {
                "summary": "blocked_before_llm",
                "final_response": base_response(
                    reply=(
                        "Phát hiện thông tin cá nhân trong tin nhắn. Vui lòng xóa SĐT/email/CCCD khỏi chat. "
                        "AI chỉ cần biết triệu chứng; thông tin cá nhân sẽ được nhập ở form đặt lịch riêng."
                    ),
                    state=STATE_PII_BLOCKED,
                    needs_more_info=False,
                    meta={"pii_types": observations["pii_hits"]},
                ),
            }

        if action == "check_red_flags":
            red_flag_result = self.tools.detect_red_flags(message)
            observations["red_flag_result"] = red_flag_result
            return {"summary": "red_flag_detected" if red_flag_result["red_flag_risk"] else "red_flag_clear"}

        if action == "final_escalation":
            return {
                "summary": "escalated_to_callback",
                "final_response": self._build_escalation_response(message, observations["red_flag_result"], context),
            }

        if action == "check_specialty_override":
            override_specialty = self.tools.detect_specialty_override(message)
            observations["override_specialty"] = override_specialty
            return {"summary": "override_detected" if override_specialty else "no_override"}

        if action == "final_specialty_override":
            return {
                "summary": "refreshed_slots_for_user_override",
                "final_response": self._build_override_response(message, observations["override_specialty"], context),
            }

        if action == "final_ready_for_form":
            return {
                "summary": "selected_slot_ready_for_form",
                "final_response": self._build_ready_for_form_response(
                    message,
                    context["selected_specialty_id"],
                    context["selected_slot_id"],
                    context,
                ),
            }

        if action == "check_clarifying_need":
            needs_more_info = self._should_ask_more_info(message, history, context)
            observations["needs_more_info"] = needs_more_info
            observations["questions"] = self._build_clarifying_questions(message, context) if needs_more_info else []
            return {"summary": "needs_more_info" if needs_more_info else "enough_info"}

        if action == "final_clarifying_question":
            return {
                "summary": "asked_clarifying_questions",
                "final_response": base_response(
                    reply="Để gợi ý đúng chuyên khoa hơn, tôi cần thêm một chút thông tin.",
                    state=STATE_NEED_MORE_INFO,
                    needs_more_info=True,
                    questions=observations["questions"],
                ),
            }

        if action == "llm_analyze_intake":
            gemini_result = self.llm_client.analyze_intake(message, history, context)
            observations["gemini_result"] = gemini_result
            observations["symptom_summary"] = (
                gemini_result.get("symptom_summary")
                if gemini_result
                else self._build_fallback_symptom_summary(message)
            )
            observations["confidence"] = (
                coerce_float(gemini_result.get("confidence"), default=0.68)
                if gemini_result
                else 0.62
            )
            return {"summary": "llm_result" if gemini_result else "fallback_symptom_summary"}

        if action == "infer_facility":
            observations["facility_id"] = self.tools.infer_facility_id(message, context)
            return {"summary": f"facility={observations['facility_id']}"}

        if action == "suggest_specialty":
            suggestions = self.tools.suggest_specialty(
                symptom_summary=observations["symptom_summary"],
                user_message=message,
                age_or_birth_year=context.get("age_or_birth_year"),
                facility_id=observations["facility_id"],
                gemini_result=observations["gemini_result"],
            )
            if not suggestions:
                suggestions = [
                    {
                        "specialty_id": "general_internal",
                        "name": "Nội tổng quát",
                        "reason": "Phù hợp khi triệu chứng còn chung chung và cần bác sĩ sàng lọc ban đầu.",
                        "confidence": 0.52,
                    }
                ]
            observations["suggestions"] = suggestions
            return {"summary": f"suggestions={len(suggestions)}"}

        if action == "get_available_slots":
            top_specialty = observations["suggestions"][0]
            observations["slots"] = self.tools.get_available_slots(
                top_specialty["specialty_id"],
                observations["facility_id"],
            )
            return {"summary": f"slots={len(observations['slots'])}"}

        if action == "create_booking_draft":
            top_specialty = observations["suggestions"][0]
            slots = observations["slots"]
            observations["booking_draft"] = self.tools.create_booking_draft(
                symptom_summary=observations["symptom_summary"],
                facility_id=observations["facility_id"],
                specialty_id=top_specialty["specialty_id"],
                slot_id=slots[0]["slot_id"] if len(slots) == 1 else None,
                status="draft",
            )
            return {"summary": "booking_draft_created"}

        if action == "final_booking_suggestion":
            slots = observations["slots"]
            state = STATE_READY_FOR_FORM if len(slots) == 1 else STATE_SUGGESTING_SLOTS
            return {
                "summary": "returned_booking_suggestion",
                "final_response": base_response(
                    reply=self._build_booking_reply(observations["suggestions"], slots, observations["facility_id"]),
                    state=state,
                    symptom_summary=observations["symptom_summary"],
                    confidence=observations["confidence"],
                    red_flag_risk=False,
                    suggested_specialties=observations["suggestions"],
                    slots=slots,
                    booking_draft=observations["booking_draft"],
                    needs_more_info=False,
                    meta={
                        "model_used": observations["gemini_result"].get("model_used")
                        if observations["gemini_result"]
                        else "fallback_rules",
                        "fallback_used": observations["gemini_result"] is None,
                    },
                ),
            }

        return {"summary": f"unknown_action={action}"}

    def _build_escalation_response(
        self,
        user_message: str,
        red_flag_result: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        symptom_summary = self._build_fallback_symptom_summary(user_message)
        callback_draft = {
            "type": "callback",
            "status": "callback",
            "reason_for_callback": symptom_summary,
            "red_flag_risk": True,
            "matched_keywords": red_flag_result.get("matched_keywords", []),
            "facility_id": self.tools.infer_facility_id(user_message, context),
            "hotline": "1900 56 56 56",
        }
        return base_response(
            reply=(
                "Triệu chứng bạn mô tả có dấu hiệu cần được hỗ trợ y tế sớm. "
                "Prototype sẽ không tạo lịch khám ngoại trú thông thường cho trường hợp này. "
                "Vui lòng liên hệ hotline 1900 56 56 56 hoặc để lại yêu cầu callback trong form riêng."
            ),
            state=STATE_ESCALATION,
            symptom_summary=symptom_summary,
            confidence=0.9,
            red_flag_risk=True,
            callback_draft=callback_draft,
            needs_more_info=False,
        )

    def _build_override_response(
        self,
        user_message: str,
        specialty: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        facility_id = self.tools.infer_facility_id(user_message, context)
        symptom_summary = context.get("symptom_summary") or self._build_fallback_symptom_summary(user_message)
        slots = self.tools.get_available_slots(specialty["specialty_id"], facility_id)
        status = "pending_review" if context.get("mark_override_pending_review", True) else "draft"
        booking_draft = self.tools.create_booking_draft(
            symptom_summary=symptom_summary,
            facility_id=facility_id,
            specialty_id=specialty["specialty_id"],
            slot_id=None,
            status=status,
        )
        return base_response(
            reply=(
                f"Được, tôi sẽ chuyển sang Khoa {specialty['name']} và cập nhật lại các lịch trống. "
                "Nếu thông tin triệu chứng cần bác sĩ sàng lọc thêm, lịch sẽ được đánh dấu Pending_Doctor_Review."
            ),
            state=STATE_SUGGESTING_SLOTS,
            symptom_summary=symptom_summary,
            confidence=0.74,
            suggested_specialties=[specialty],
            slots=slots,
            booking_draft=booking_draft,
            needs_more_info=False,
            meta={"override": True},
        )

    def _build_ready_for_form_response(
        self,
        user_message: str,
        specialty_id: str,
        slot_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        facility_id = context.get("preferred_facility_id") or context.get("facility_id") or self.tools.infer_facility_id(user_message, context)
        symptom_summary = context.get("symptom_summary") or self._build_fallback_symptom_summary(user_message)
        booking_draft = self.tools.create_booking_draft(
            symptom_summary=symptom_summary,
            facility_id=facility_id,
            specialty_id=specialty_id,
            slot_id=slot_id,
            status="draft",
        )
        return base_response(
            reply="Tôi đã giữ thông tin khoa và slot bạn chọn. Bạn có thể mở form đặt lịch để nhập thông tin cá nhân riêng.",
            state=STATE_READY_FOR_FORM,
            symptom_summary=symptom_summary,
            confidence=0.8,
            suggested_specialties=[
                {
                    "specialty_id": specialty_id,
                    "name": self.tools.specialty_name(specialty_id),
                    "reason": "User đã chọn chuyên khoa này.",
                    "confidence": 1.0,
                }
            ],
            slots=[slot for slot in self.tools.get_available_slots(specialty_id, facility_id) if slot["slot_id"] == slot_id],
            booking_draft=booking_draft,
            needs_more_info=False,
        )

    def _build_booking_reply(
        self,
        suggestions: list[dict[str, Any]],
        slots: list[dict[str, Any]],
        facility_id: str | None,
    ) -> str:
        top = suggestions[0]
        facility = self.tools.facility_name(facility_id)
        if slots:
            first_slot = slots[0]
            return (
                f"Dựa trên triệu chứng, gợi ý phù hợp nhất là Khoa {top['name']} tại {facility}. "
                f"Lý do: {top.get('reason', 'phù hợp với mô tả hiện tại')} "
                f"Hiện có slot gần nhất vào {first_slot['time']} ngày {first_slot['date']}. "
                "Bạn có thể chọn slot này, chọn slot khác hoặc đổi chuyên khoa trước khi mở form."
            )
        return (
            f"Dựa trên triệu chứng, gợi ý phù hợp nhất là Khoa {top['name']} tại {facility}. "
            "Hiện chưa có slot trống từ mock data, bạn có thể đổi cơ sở hoặc để lại yêu cầu callback."
        )

    def _should_ask_more_info(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> bool:
        normalized = normalize_vietnamese(user_message)
        if context.get("skip_clarifying_questions"):
            return False

        previous_questions = int(context.get("clarifying_questions_asked", 0) or 0)
        if previous_questions >= 2:
            return False

        has_obvious_symptom = any(
            contains_normalized_keyword(normalized, keyword)
            for keyword in [
                "đau",
                "sốt",
                "ho",
                "khó thở",
                "chóng mặt",
                "buồn nôn",
                "mệt",
                "tiêu chảy",
                "ngất",
                "tê",
            ]
        )
        has_time_or_severity = any(
            contains_normalized_keyword(normalized, keyword)
            for keyword in [
                "hôm nay",
                "hôm qua",
                "ngày",
                "giờ",
                "tuần",
                "âm ỉ",
                "dữ dội",
                "nhẹ",
                "nặng",
                "kéo dài",
            ]
        )

        if not has_obvious_symptom:
            return True
        if len(normalized.split()) <= 4 and previous_questions < 1:
            return True
        if not has_time_or_severity and previous_questions < 1:
            return True
        return False

    def _build_clarifying_questions(self, user_message: str, context: dict[str, Any]) -> list[str]:
        normalized = normalize_vietnamese(user_message)
        questions: list[str] = []

        if not any(word in normalized for word in ["hom nay", "hom qua", "ngay", "gio", "tuan", "keo dai"]):
            questions.append("Triệu chứng bắt đầu từ khi nào và mức độ hiện tại nhẹ, vừa hay nặng?")

        if not context.get("preferred_facility_id") and not context.get("facility_id"):
            questions.append("Bạn muốn khám ở cơ sở nào của Vinmec, ví dụ Times City hay Smart City?")

        if not questions:
            questions.append("Bạn có triệu chứng đi kèm nào khác không, ví dụ sốt, buồn nôn, khó thở hoặc chóng mặt?")

        return questions[:2]

    def _build_fallback_symptom_summary(self, user_message: str) -> str:
        clean = re.sub(r"\s+", " ", user_message).strip()
        if len(clean) <= 220:
            return clean
        return clean[:217].rstrip() + "..."
