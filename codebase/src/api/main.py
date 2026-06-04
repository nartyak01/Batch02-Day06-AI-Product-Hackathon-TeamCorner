"""FastAPI — /tools/* for agent, /form/* for manual booking form."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from ..vinmec_agent import run_agent_turn
from ..tools.medical import (
    check_red_flags,
    get_available_slots,
    get_facilities,
    get_specialties,
    suggest_specialty,
    get_specialty_catalog,
    format_specialty_catalog_for_prompt,
    list_doctors_by_specialty,
    list_facilities_for_specialty,
    suggest_booking_package,
    get_form_facilities,
    get_form_doctors,
    get_form_slots,
    get_booking_form_context,
)
from ..tools.booking import submit_booking, list_bookings, get_booking, update_booking

app = FastAPI(title="VinmecCare API", version="0.2.0")


# --- Tool A: specialty / symptoms ---


class TextBody(BaseModel):
    text: str


class AgentChoice(BaseModel):
    specialty_id: str
    reason: str = ""


class SuggestSpecialtyBody(BaseModel):
    symptom_summary: str = Field(..., description="Tóm tắt triệu chứng từ chat")
    agent_choices: list[AgentChoice] | None = Field(
        None,
        description="2-3 khoa do Gemini chọn sau khi đọc description trong catalog",
    )


# --- Tool B: agent booking suggest ---


class AvailableSlotsBody(BaseModel):
    specialty_id: str
    facility_id: str | None = None
    doctor_id: str | None = None


class AgentTurnBody(BaseModel):
    user_message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/reference-data")
def api_reference_data():
    return {
        "facilities": get_facilities(),
        "specialties": get_specialties(),
    }


@app.post("/agent/turn")
def api_agent_turn(body: AgentTurnBody):
    return run_agent_turn(
        user_message=body.user_message,
        history=body.history,
        context=body.context,
    )


@app.get("/tools/specialty-catalog")
def api_specialty_catalog():
    return {
        "specialties": get_specialty_catalog(),
        "prompt_block": format_specialty_catalog_for_prompt(),
    }


@app.post("/tools/check-red-flags")
def api_check_red_flags(body: TextBody):
    return check_red_flags(body.text)


@app.post("/tools/suggest-specialty")
def api_suggest_specialty(body: SuggestSpecialtyBody):
    choices = None
    if body.agent_choices:
        choices = [c.model_dump() for c in body.agent_choices]
    return suggest_specialty(body.symptom_summary, agent_choices=choices)


@app.get("/tools/facilities")
def api_tools_facilities(specialty_id: str):
    return {"facilities": list_facilities_for_specialty(specialty_id)}


@app.get("/tools/doctors")
def api_tools_doctors(specialty_id: str, facility_id: str | None = None):
    return {"doctors": list_doctors_by_specialty(specialty_id, facility_id=facility_id)}


@app.post("/tools/available-slots")
def api_available_slots(body: AvailableSlotsBody):
    """Agent only: open slots for suggesting BS/time."""
    return get_available_slots(
        body.specialty_id,
        body.facility_id,
        body.doctor_id,
    )


@app.get("/tools/booking-suggest")
def api_booking_suggest(specialty_id: str, facility_id: str | None = None):
    return suggest_booking_package(specialty_id, facility_id=facility_id)


# --- Form: cascade for manual edit ---


@app.get("/form/facilities")
def api_form_facilities(specialty_id: str):
    return {"facilities": get_form_facilities(specialty_id)}


@app.get("/form/doctors")
def api_form_doctors(specialty_id: str, facility_id: str):
    return {"doctors": get_form_doctors(specialty_id, facility_id)}


@app.get("/form/slots")
def api_form_slots(specialty_id: str, facility_id: str, doctor_id: str):
    return {
        "slots": get_form_slots(specialty_id, facility_id, doctor_id=doctor_id),
    }


@app.get("/form/booking-context")
def api_booking_context(
    specialty_id: str,
    facility_id: str | None = None,
    doctor_id: str | None = None,
    slot_id: str | None = None,
):
    """
    Full form payload: facilities + doctors (if facility set) + slots_by_doctor.
    FE: đổi facility_id → gọi lại để refresh doctors/slots.
    """
    if doctor_id and not facility_id:
        raise HTTPException(400, "facility_id required when doctor_id is set")
    if slot_id and not (facility_id and doctor_id):
        raise HTTPException(400, "facility_id and doctor_id required when slot_id is set")
    return get_booking_form_context(
        specialty_id,
        facility_id=facility_id,
        doctor_id=doctor_id,
        slot_id=slot_id,
    )


# --- Bookings: FE submit / check (no agent, PII không qua LLM) ---


class SubmitBookingBody(BaseModel):
    name: str
    phone: str
    email: str = ""
    dob: str = ""
    facility_id: str
    specialty_id: str
    doctor_id: str
    slot_id: str
    symptom_summary: str = ""
    status: str = "confirmed"
    notes: str = ""


class UpdateBookingBody(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    dob: str | None = None
    notes: str | None = None
    status: str | None = None


@app.post("/bookings")
def api_submit_booking(body: SubmitBookingBody):
    """Đặt lịch — ghi PII vào bookings.csv, không qua agent."""
    result = submit_booking(body.model_dump())
    if not result["ok"]:
        raise HTTPException(400, result["message"])
    return result


@app.get("/bookings")
def api_list_bookings(
    ticket_id: str | None = None,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    dob: str | None = None,
    status: str | None = None,
):
    """Tab Lịch đã đặt — có thể lọc theo ticket / thông tin cá nhân."""
    return {
        "bookings": list_bookings(
            ticket_id=ticket_id,
            name=name,
            phone=phone,
            email=email,
            dob=dob,
            status=status,
        )
    }


@app.get("/bookings/{ticket_id}")
def api_get_booking(ticket_id: str):
    booking = get_booking(ticket_id)
    if not booking:
        raise HTTPException(404, "Không tìm thấy ticket")
    return {"booking": booking}


@app.patch("/bookings/{ticket_id}")
def api_update_booking(ticket_id: str, body: UpdateBookingBody):
    """Sửa thông tin liên hệ — không gọi LLM."""
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    result = update_booking(ticket_id, patch)
    if not result["ok"]:
        raise HTTPException(400, result["message"])
    return result
