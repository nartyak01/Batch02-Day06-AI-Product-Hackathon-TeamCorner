from __future__ import annotations

import re
from typing import Any

from .ports import AgentTools, LLMClient
from ..domain.constants import (
    STATE_ESCALATION,
    STATE_NEED_MORE_INFO,
    STATE_PII_BLOCKED,
    STATE_READY_FOR_FORM,
    STATE_SUGGESTING_SLOTS,
)
from src.utils.flow_log import log_react_step

from ..domain.privacy import detect_pii
from ..domain.response import base_response, coerce_float
from ..domain.text import contains_normalized_keyword, normalize_vietnamese


AVAILABLE_LLM_TOOLS = [
    "ask_clarifying_question",
    "analyze_intake",
    "suggest_specialty",
    "get_available_slots",
    "create_booking_draft",
    "final_answer",
]


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

        if not message:
            return base_response(
                reply="Bạn vui lòng mô tả ngắn gọn triệu chứng hiện tại để tôi hỗ trợ gợi ý chuyên khoa.",
                state=STATE_NEED_MORE_INFO,
                needs_more_info=True,
                questions=["Bạn đang gặp triệu chứng gì và triệu chứng bắt đầu từ khi nào?"],
            )

        pii_hits = detect_pii(message)
        if pii_hits:
            return base_response(
                reply=(
                    "Phát hiện thông tin cá nhân trong tin nhắn. Vui lòng xóa SĐT/email/CCCD khỏi chat. "
                    "AI chỉ cần biết triệu chứng; thông tin cá nhân sẽ được nhập ở form đặt lịch riêng."
                ),
                state=STATE_PII_BLOCKED,
                needs_more_info=False,
                meta={"pii_types": pii_hits, "guard": "rule_first_pii"},
            )

        red_flag_result = self.tools.detect_red_flags(message)
        if red_flag_result["red_flag_risk"]:
            response = self._build_escalation_response(message, red_flag_result, context)
            response.setdefault("meta", {})
            response["meta"]["guard"] = "rule_first_red_flag"
            return response

        if context.get("selected_slot_id") and context.get("selected_specialty_id"):
            return self._build_ready_for_form_response(
                message,
                context["selected_specialty_id"],
                context["selected_slot_id"],
                context,
            )

        react_state: dict[str, Any] = {
            "message": message,
            "history": history,
            "context": context,
            "observations": {},
            "trace": [],
        }

        for step_index in range(6):
            plan = self.llm_client.plan_next_action(
                user_message=message,
                history=history,
                context=context,
                observations=react_state["observations"],
                available_tools=AVAILABLE_LLM_TOOLS,
            )
            action, action_input, planner = self._select_planned_action(plan, react_state)
            observation = self._run_tool_action(action, action_input, react_state)
            step_summary = observation.get("summary", "ok")
            react_state["trace"].append(
                {
                    "step": step_index + 1,
                    "planner": planner,
                    "action": action,
                    "observation": step_summary,
                }
            )
            log_react_step(step_index + 1, action, planner, str(step_summary))

            final_response = observation.get("final_response")
            if final_response:
                final_response.setdefault("meta", {})
                final_response["meta"]["react_trace"] = react_state["trace"]
                return final_response

        return self._build_final_booking_response(
            react_state,
            fallback_reply="Agent chưa hoàn tất được vòng ReAct. Vui lòng thử lại hoặc chuyển sang callback.",
            fallback_state=STATE_NEED_MORE_INFO,
        )

    def _select_planned_action(
        self,
        plan: dict[str, Any] | None,
        react_state: dict[str, Any],
    ) -> tuple[str, dict[str, Any], str]:
        raw_action = plan.get("action") if isinstance(plan, dict) else None
        raw_input = plan.get("action_input") if isinstance(plan, dict) else None
        action_input = dict(raw_input) if isinstance(raw_input, dict) else {}
        if isinstance(plan, dict) and plan.get("assistant_reply") and "assistant_reply" not in action_input:
            action_input["assistant_reply"] = plan["assistant_reply"]
        if raw_action in AVAILABLE_LLM_TOOLS and self._action_preconditions_met(str(raw_action), react_state):
            observations = react_state["observations"]
            if isinstance(plan, dict) and plan.get("planner_model"):
                observations["planner_model"] = plan["planner_model"]
            return str(raw_action), action_input, "gemini"
        return self._fallback_next_action(react_state), {}, "fallback"

    def _action_preconditions_met(self, action: str, react_state: dict[str, Any]) -> bool:
        observations = react_state["observations"]
        if action == "suggest_specialty":
            return bool(observations.get("symptom_summary"))
        if action == "get_available_slots":
            return bool(observations.get("suggestions"))
        if action == "create_booking_draft":
            return bool(observations.get("symptom_summary") and observations.get("suggestions") and observations.get("slots"))
        if action == "final_answer":
            return bool(observations.get("booking_draft"))
        if action == "ask_clarifying_question":
            return self._should_ask_more_info(
                react_state["message"],
                react_state["history"],
                react_state["context"],
            )
        if action == "analyze_intake":
            return "symptom_summary" not in observations
        return False

    def _intake_flags(self, user_message: str, context: dict[str, Any]) -> dict[str, bool]:
        normalized = normalize_vietnamese(user_message)
        has_obvious_symptom = any(
            contains_normalized_keyword(normalized, keyword)
            for keyword in [
                "dau",
                "sot",
                "ho",
                "kho tho",
                "chong mat",
                "buon non",
                "met",
                "tieu chay",
                "ngat",
                "te",
                "phat ban",
                "dau bung",
                "dau nguc",
                "dau dau",
            ]
        )
        has_duration = any(
            contains_normalized_keyword(normalized, keyword)
            for keyword in [
                "hom nay",
                "hom qua",
                "toi qua",
                "sang nay",
                "chieu nay",
                "dem qua",
                "ngay",
                "gio",
                "tuan",
                "vai ngay",
                "vai gio",
                "vai tuan",
                "may ngay",
                "keo dai",
                "tu dau",
                "lap lai",
            ]
        )
        has_severity = any(
            contains_normalized_keyword(normalized, keyword)
            for keyword in [
                "nhe",
                "vua",
                "nang",
                "rat nang",
                "am i",
                "nhoi",
                "tung dot",
                "1-10",
                "diem",
                "kho chiu",
            ]
        )
        has_location = any(
            contains_normalized_keyword(normalized, keyword)
            for keyword in [
                "bung",
                "ron",
                "quanh ron",
                "nguc",
                "dau dau",
                "co",
                "gay",
                "vai",
                "lung",
                "khop",
                "chan",
                "tay",
                "mat",
                "mui",
                "hong",
                "tai",
                "da",
            ]
        )
        has_associated_symptoms = any(
            contains_normalized_keyword(normalized, keyword)
            for keyword in [
                "sot",
                "buon non",
                "non",
                "kho tho",
                "chong mat",
                "dau dau",
                "di ngoai",
                "tieu chay",
                "non nao",
                "te tay",
                "yeu chi",
                "ho",
                "dam",
                "met moi",
            ]
        )
        has_age = bool(context.get("age_or_birth_year")) or bool(
            re.search(r"\b(?:19|20)\d{2}\b|\b\d{1,2}\s*tuoi\b", normalized)
        )
        has_facility = bool(context.get("preferred_facility_id") or context.get("facility_id")) or any(
            keyword in normalized
            for keyword in [
                "times city",
                "smart city",
                "vinmec",
            ]
        )
        return {
            "has_obvious_symptom": has_obvious_symptom,
            "has_duration": has_duration,
            "has_severity": has_severity,
            "has_location": has_location,
            "has_associated_symptoms": has_associated_symptoms,
            "has_age": has_age,
            "has_facility": has_facility,
        }

    def _fallback_next_action(self, react_state: dict[str, Any]) -> str:
        message = react_state["message"]
        history = react_state["history"]
        context = react_state["context"]
        observations = react_state["observations"]

        if not observations.get("clarifying_checked"):
            observations["clarifying_checked"] = True
            if self._should_ask_more_info(message, history, context):
                return "ask_clarifying_question"
        if "symptom_summary" not in observations:
            return "analyze_intake"
        if "suggestions" not in observations:
            return "suggest_specialty"
        if "slots" not in observations:
            return "get_available_slots"
        if "booking_draft" not in observations:
            return "create_booking_draft"
        return "final_answer"

    def _run_tool_action(
        self,
        action: str,
        action_input: dict[str, Any],
        react_state: dict[str, Any],
    ) -> dict[str, Any]:
        message = react_state["message"]
        history = react_state["history"]
        context = react_state["context"]
        observations = react_state["observations"]

        if action == "ask_clarifying_question":
            questions = action_input.get("questions")
            if not isinstance(questions, list) or not questions:
                questions = self._build_clarifying_questions(message, context)
            reply = action_input.get("assistant_reply") or "Để gợi ý đúng chuyên khoa hơn, tôi cần thêm một chút thông tin."
            return {
                "summary": "asked_clarifying_questions",
                "final_response": base_response(
                    reply=str(reply),
                    state=STATE_NEED_MORE_INFO,
                    needs_more_info=True,
                    questions=[str(question) for question in questions[:2]],
                ),
            }

        if action == "analyze_intake":
            gemini_result = self.llm_client.analyze_intake(message, history, context)
            observations["gemini_result"] = gemini_result
            input_confidence = coerce_float(action_input.get("confidence"), default=0.0)
            observations["symptom_summary"] = (
                str(action_input.get("symptom_summary"))
                if action_input.get("symptom_summary")
                else gemini_result.get("symptom_summary")
                if gemini_result
                else self._build_fallback_symptom_summary(message)
            )
            observations["confidence"] = (
                input_confidence
                or (coerce_float(gemini_result.get("confidence"), default=0.68) if gemini_result else 0.62)
                if gemini_result
                else input_confidence or 0.62
            )
            observations["facility_id"] = (
                action_input.get("facility_id")
                or context.get("preferred_facility_id")
                or context.get("facility_id")
                or self.tools.infer_facility_id(message, context)
            )
            if gemini_result and gemini_result.get("needs_more_info"):
                questions = gemini_result.get("questions")
                if not isinstance(questions, list) or not questions:
                    questions = self._build_clarifying_questions(message, context)
                reply = gemini_result.get("assistant_reply") or "Để chọn đúng chuyên khoa hơn, tôi cần thêm vài chi tiết ngắn."
                return {
                    "summary": "intake_needs_more_info",
                    "final_response": base_response(
                        reply=str(reply),
                        state=STATE_NEED_MORE_INFO,
                        needs_more_info=True,
                        questions=[str(question) for question in questions[:2]],
                    ),
                }
            return {"summary": "symptom_summary_created"}

        if action == "suggest_specialty":
            suggestions = self.tools.suggest_specialty(
                symptom_summary=observations["symptom_summary"],
                user_message=message,
                age_or_birth_year=context.get("age_or_birth_year"),
                facility_id=observations.get("facility_id"),
                gemini_result=observations.get("gemini_result"),
            )
            if not suggestions:
                suggestions = [
                    {
                        "specialty_id": "suc_khoe_tong_quat",
                        "name": "Sức khoẻ tổng quát",
                        "reason": "Phù hợp khi triệu chứng còn chung chung và cần bác sĩ sàng lọc ban đầu.",
                        "confidence": 0.52,
                    }
                ]
            observations["suggestions"] = suggestions
            return {"summary": f"suggestions={len(suggestions)}"}

        if action == "get_available_slots":
            specialty_id = action_input.get("specialty_id") or observations["suggestions"][0]["specialty_id"]
            observations["slots"] = self.tools.get_available_slots(
                str(specialty_id),
                observations.get("facility_id") or self.tools.infer_facility_id(message, context),
            )
            return {"summary": f"slots={len(observations['slots'])}"}

        if action == "create_booking_draft":
            top_specialty = observations["suggestions"][0]
            slots = observations["slots"]
            selected_slot_id = action_input.get("slot_id") or slots[0]["slot_id"] if slots else None
            observations["booking_draft"] = self.tools.create_booking_draft(
                symptom_summary=observations["symptom_summary"],
                facility_id=observations.get("facility_id"),
                specialty_id=action_input.get("specialty_id") or top_specialty["specialty_id"],
                slot_id=selected_slot_id if len(slots) == 1 else action_input.get("slot_id"),
                status=action_input.get("status") or "draft",
            )
            return {
                "summary": "booking_draft_created",
                "final_response": self._build_final_booking_response(react_state),
            }

        if action == "final_answer":
            return {
                "summary": "returned_final_answer",
                "final_response": self._build_final_booking_response(
                    react_state,
                    fallback_reply=action_input.get("assistant_reply") or "Tôi cần thêm thông tin để gợi ý lịch khám phù hợp.",
                    fallback_state=STATE_NEED_MORE_INFO,
                ),
            }

        return {"summary": f"unknown_action={action}"}

    def _build_final_booking_response(
        self,
        react_state: dict[str, Any],
        fallback_reply: str | None = None,
        fallback_state: str = STATE_NEED_MORE_INFO,
    ) -> dict[str, Any]:
        observations = react_state["observations"]
        slots = observations.get("slots", [])
        suggestions = observations.get("suggestions", [])
        booking_draft = observations.get("booking_draft")

        if booking_draft and suggestions:
            state = STATE_READY_FOR_FORM if len(slots) == 1 else STATE_SUGGESTING_SLOTS
            return {
                **base_response(
                    reply=self._build_booking_reply(suggestions, slots, observations.get("facility_id")),
                    state=state,
                    symptom_summary=observations.get("symptom_summary", ""),
                    confidence=coerce_float(observations.get("confidence"), 0.0),
                    red_flag_risk=False,
                    suggested_specialties=suggestions,
                    slots=slots,
                    booking_draft=booking_draft,
                    needs_more_info=False,
                    meta={
                        "planner_model": observations.get("planner_model"),
                        "model_used": observations.get("gemini_result", {}).get("model_used")
                        if observations.get("gemini_result")
                        else "fallback_rules",
                        "fallback_used": observations.get("gemini_result") is None,
                    },
                )
            }

        return base_response(
            reply=fallback_reply or "Tôi cần thêm thông tin để gợi ý lịch khám phù hợp.",
            state=fallback_state,
            symptom_summary=observations.get("symptom_summary", ""),
            confidence=coerce_float(observations.get("confidence"), 0.0),
            suggested_specialties=suggestions,
            slots=slots,
            needs_more_info=True,
            questions=self._build_clarifying_questions(react_state["message"], react_state["context"]),
            meta={"fallback_used": True},
        )

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
            "Hiện chưa có slot trống từ dữ liệu hiện có, bạn có thể đổi cơ sở hoặc để lại yêu cầu callback."
        )

    def _should_ask_more_info(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> bool:
        if context.get("skip_clarifying_questions"):
            return False

        previous_questions = int(context.get("clarifying_questions_asked", 0) or 0)
        if previous_questions >= 2:
            return False

        flags = self._intake_flags(user_message, context)
        if not flags["has_obvious_symptom"]:
            return True
        normalized = normalize_vietnamese(user_message)
        if len(normalized.split()) <= 4 and previous_questions < 1:
            return True
        missing_core_details = any(
            not flags[key]
            for key in ("has_duration", "has_severity", "has_location", "has_associated_symptoms", "has_age")
        )
        if previous_questions < 1 and missing_core_details:
            return True
        if previous_questions < 1 and not flags["has_facility"] and len(normalized.split()) <= 12:
            return True
        return False

    def _build_clarifying_questions(self, user_message: str, context: dict[str, Any]) -> list[str]:
        flags = self._intake_flags(user_message, context)
        questions: list[str] = []

        if not flags["has_duration"] or not flags["has_severity"]:
            questions.append(
                "Triệu chứng bắt đầu từ khi nào, mức độ hiện tại thế nào, và có tăng dần hay từng cơn không?"
            )

        if not flags["has_location"] or not flags["has_associated_symptoms"]:
            questions.append(
                "Triệu chứng nằm ở vị trí nào, có lan đi đâu, và có kèm sốt, buồn nôn, nôn, khó thở, chóng mặt, tiêu chảy hoặc tê yếu không?"
            )

        if not flags["has_age"]:
            questions.append("Bạn cho mình biết tuổi hoặc năm sinh để mình chọn khoa sát hơn?")

        if not flags["has_facility"]:
            questions.append("Bạn muốn khám ở cơ sở nào của Vinmec, ví dụ Times City hay Smart City?")

        if not questions:
            questions.append("Bạn có bệnh nền, thuốc đang dùng hoặc triệu chứng nào khác cần lưu ý không?")

        return questions[:2]

    def _build_fallback_symptom_summary(self, user_message: str) -> str:
        clean = re.sub(r"\s+", " ", user_message).strip()
        if len(clean) <= 220:
            return clean
        return clean[:217].rstrip() + "..."
