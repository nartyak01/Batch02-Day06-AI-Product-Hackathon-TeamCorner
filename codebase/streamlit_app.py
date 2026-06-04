from __future__ import annotations

from datetime import date, datetime
from typing import Any

import streamlit as st

from vinmec_agent import run_agent_turn
from vinmec_agent.domain.constants import STATE_ESCALATION, STATE_PII_BLOCKED, STATE_READY_FOR_FORM, STATE_SUGGESTING_SLOTS
from vinmec_agent.domain.privacy import detect_pii
from vinmec_agent.infrastructure.mock_data import FACILITIES, SPECIALTIES
from vinmec_agent.infrastructure.mock_tools import MockMedicalTools


tools = MockMedicalTools()


def init_state() -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("context", {})
    st.session_state.setdefault("latest_result", None)
    st.session_state.setdefault("bookings", [])


def append_message(role: str, content: str) -> None:
    st.session_state.messages.append({"role": role, "content": content})


def run_chat_turn(message: str) -> dict[str, Any]:
    result = run_agent_turn(
        user_message=message,
        history=st.session_state.messages,
        context=st.session_state.context,
    )
    st.session_state.latest_result = result
    if result.get("symptom_summary"):
        st.session_state.context["symptom_summary"] = result["symptom_summary"]
    if result.get("booking_draft"):
        st.session_state.context["booking_draft"] = result["booking_draft"]
    return result


def render_sidebar() -> None:
    st.sidebar.header("Test context")
    facility_options = {facility["name"]: facility["facility_id"] for facility in FACILITIES}
    selected_facility_name = st.sidebar.selectbox("Cơ sở mong muốn", list(facility_options.keys()))
    st.session_state.context["preferred_facility_id"] = facility_options[selected_facility_name]

    birth_year = st.sidebar.text_input("Năm sinh/tuổi (không bắt buộc)", value=st.session_state.context.get("age_or_birth_year", ""))
    if birth_year:
        st.session_state.context["age_or_birth_year"] = birth_year

    st.session_state.context["skip_clarifying_questions"] = st.sidebar.checkbox(
        "Bỏ qua câu hỏi làm rõ",
        value=bool(st.session_state.context.get("skip_clarifying_questions", False)),
    )

    if st.sidebar.button("Reset demo"):
        for key in ["messages", "context", "latest_result", "bookings"]:
            st.session_state.pop(key, None)
        st.rerun()


def render_chat() -> None:
    st.subheader("Chat agent")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("Mô tả triệu chứng, ví dụ: Tôi bị đau bụng âm ỉ từ hôm qua...")
    if not prompt:
        return

    with st.chat_message("user"):
        st.write(prompt)
    append_message("user", prompt)

    if detect_pii(prompt):
        result = run_agent_turn(prompt, st.session_state.messages, st.session_state.context)
    else:
        result = run_chat_turn(prompt)

    with st.chat_message("assistant"):
        st.write(result["reply"])
        if result.get("questions"):
            for question in result["questions"]:
                st.info(question)
    append_message("assistant", result["reply"])


def render_agent_result(result: dict[str, Any] | None) -> None:
    if not result:
        return

    state = result.get("state")
    if state == STATE_PII_BLOCKED:
        st.warning("PII guard đã chặn tin nhắn trước khi đưa vào LLM.")
    elif state == STATE_ESCALATION:
        st.error("Red flag: chuyển hotline/callback, không tạo booking thường.")
    elif state in {STATE_SUGGESTING_SLOTS, STATE_READY_FOR_FORM}:
        st.success("Agent đã tạo gợi ý khoa/slot và booking draft.")

    if result.get("suggested_specialties"):
        st.markdown("#### Chuyên khoa gợi ý")
        cols = st.columns(min(3, len(result["suggested_specialties"])))
        for index, specialty in enumerate(result["suggested_specialties"]):
            with cols[index % len(cols)]:
                st.metric(specialty["name"], f"{specialty.get('confidence', 0):.0%}")
                st.caption(specialty.get("reason", ""))

    if result.get("slots"):
        st.markdown("#### Slot trống")
        for slot in result["slots"]:
            cols = st.columns([2, 2, 2, 1])
            cols[0].write(f"**{slot['date']} {slot['time']}**")
            cols[1].write(slot.get("doctor_name") or "Bác sĩ")
            cols[2].write(slot.get("facility_name") or "")
            if cols[3].button("Chọn", key=f"slot_{slot['slot_id']}"):
                st.session_state.context["selected_slot_id"] = slot["slot_id"]
                st.session_state.context["selected_specialty_id"] = slot["specialty_id"]
                result = run_chat_turn("Tôi chọn slot này")
                append_message("assistant", result["reply"])
                st.rerun()

    with st.expander("JSON agent output"):
        st.json(result)


def render_booking_form(result: dict[str, Any] | None) -> None:
    if not result:
        return

    booking_draft = result.get("booking_draft")
    callback_draft = result.get("callback_draft")

    st.subheader("Form đặt lịch/callback mock")
    if callback_draft:
        st.warning("Trường hợp red flag: chỉ tạo callback ticket, không tạo lịch khám thường.")
        with st.form("callback_form"):
            contact_name = st.text_input("Họ tên")
            phone = st.text_input("SĐT")
            note = st.text_area("Ghi chú cho tư vấn viên", value=callback_draft.get("reason_for_callback", ""))
            submitted = st.form_submit_button("Tạo callback ticket")
            if submitted:
                ticket = {
                    "ticket_id": f"CALLBACK-{len(st.session_state.bookings) + 1:04d}",
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "status": "callback",
                    "name": contact_name,
                    "phone": phone,
                    "notes": note,
                    "hotline": callback_draft.get("hotline"),
                }
                st.session_state.bookings.append(ticket)
                st.success(f"Đã tạo {ticket['ticket_id']}")
        return

    if not booking_draft:
        st.info("Chưa có booking draft. Hãy chat để agent gợi ý khoa/slot trước.")
        return

    specialty_options = {specialty["name"]: specialty["specialty_id"] for specialty in SPECIALTIES if specialty["specialty_id"] != "emergency"}
    current_specialty_name = tools.specialty_name(booking_draft["specialty_id"])

    with st.form("booking_form"):
        st.caption("PII chỉ nhập ở form này, không đưa quay lại LLM.")
        facility = st.text_input("Cơ sở", value=booking_draft.get("facility_name", ""))
        specialty_name = st.selectbox(
            "Chuyên khoa",
            list(specialty_options.keys()),
            index=list(specialty_options.keys()).index(current_specialty_name) if current_specialty_name in specialty_options else 0,
        )
        slot_id = st.text_input("Slot ID", value=booking_draft.get("slot_id") or "")
        reason = st.text_area("Lý do khám", value=booking_draft.get("reason_for_visit", ""))

        name = st.text_input("Họ tên")
        phone = st.text_input("SĐT")
        email = st.text_input("Email")
        dob = st.date_input("Ngày sinh", value=date(2004, 1, 1))
        gender = st.selectbox("Giới tính", ["Không nêu", "Nam", "Nữ", "Khác"])

        submitted = st.form_submit_button("Submit mock booking")
        if submitted:
            ticket = {
                "ticket_id": f"BOOK-{len(st.session_state.bookings) + 1:04d}",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "status": booking_draft.get("status", "draft"),
                "facility": facility,
                "specialty_id": specialty_options[specialty_name],
                "specialty_name": specialty_name,
                "slot_id": slot_id,
                "reason_for_visit": reason,
                "name": name,
                "phone": phone,
                "email": email,
                "dob": dob.isoformat(),
                "gender": gender,
            }
            st.session_state.bookings.append(ticket)
            st.success(f"Đã tạo ticket {ticket['ticket_id']}")


def render_bookings() -> None:
    st.subheader("Lịch đã đặt")
    if not st.session_state.bookings:
        st.info("Chưa có ticket nào.")
        return

    for index, booking in enumerate(st.session_state.bookings):
        with st.expander(f"{booking['ticket_id']} - {booking.get('status', 'draft')}"):
            st.json(booking)
            with st.form(f"edit_booking_{index}"):
                phone = st.text_input("Sửa SĐT", value=booking.get("phone", ""), key=f"phone_{index}")
                email = st.text_input("Sửa email", value=booking.get("email", ""), key=f"email_{index}")
                saved = st.form_submit_button("Lưu thông tin")
                if saved:
                    booking["phone"] = phone
                    booking["email"] = email
                    booking["updated_at"] = datetime.now().isoformat(timespec="seconds")
                    st.success("Đã cập nhật ticket. Không gọi LLM.")


def main() -> None:
    st.set_page_config(page_title="VinmecCare Agent Test", layout="wide")
    init_state()
    render_sidebar()

    st.title("VinmecCare AI Agent - Streamlit test harness")
    st.caption("UI tạm để test agent core trước khi ghép Next.js.")

    chat_tab, form_tab, bookings_tab = st.tabs(["Chat", "Form", "Lịch đã đặt"])
    with chat_tab:
        render_chat()
        render_agent_result(st.session_state.latest_result)
    with form_tab:
        render_booking_form(st.session_state.latest_result)
    with bookings_tab:
        render_bookings()


if __name__ == "__main__":
    main()
