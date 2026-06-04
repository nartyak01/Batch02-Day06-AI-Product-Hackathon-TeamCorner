"""Form fill: cascade facility → doctor → slots (all slots for FE enable/disable)."""

from __future__ import annotations

from typing import Any, TypedDict

from .booking_suggest import list_facilities_for_specialty, FacilityOption
from .catalog import get_slots
from .doctors import list_doctors_by_specialty


class FormSlotOption(TypedDict):
    slot_id: str
    facility_id: str
    specialty_id: str
    doctor_id: str
    date: str
    time: str
    available: bool
    selectable: bool


class FormDoctorOption(TypedDict):
    doctor_id: str
    name: str
    title: str
    specialty_id: str
    facility_id: str
    availability_status: str
    has_open_slot: bool
    open_slot_count: int
    selectable: bool
    disabled_reason: str | None
    needs_check: bool


class BookingFormContextResult(TypedDict):
    specialty_id: str
    selected: dict[str, str | None]
    facilities: list[FacilityOption]
    doctors: list[FormDoctorOption]
    slots_by_doctor: dict[str, list[FormSlotOption]]


def _doctor_disabled_reason(doc: dict[str, Any]) -> str | None:
    status = (doc.get("availability_status") or "").strip()
    if status == "full":
        return "Bác sĩ đã hết lịch"
    if not doc.get("has_open_slot"):
        return "Không còn khung giờ trống"
    return None


def get_form_facilities(specialty_id: str) -> list[FacilityOption]:
    return list_facilities_for_specialty(specialty_id)


def get_form_doctors(specialty_id: str, facility_id: str) -> list[FormDoctorOption]:
    """Only doctors at the selected facility."""
    raw = list_doctors_by_specialty(specialty_id, facility_id=facility_id)
    out: list[FormDoctorOption] = []
    for doc in raw:
        reason = _doctor_disabled_reason(doc)
        out.append(
            {
                "doctor_id": doc["doctor_id"],
                "name": doc["name"],
                "title": doc["title"],
                "specialty_id": doc["specialty_id"],
                "facility_id": doc["facility_id"],
                "availability_status": doc["availability_status"],
                "has_open_slot": doc["has_open_slot"],
                "open_slot_count": doc["open_slot_count"],
                "selectable": reason is None,
                "disabled_reason": reason,
                "needs_check": doc["needs_check"],
            }
        )
    return out


def get_form_slots(
    specialty_id: str,
    facility_id: str,
    doctor_id: str | None = None,
) -> list[FormSlotOption]:
    """All slots (including booked) for dropdown disable logic."""
    raw = get_slots(
        specialty_id=specialty_id,
        facility_id=facility_id,
        doctor_id=doctor_id,
        available_only=False,
    )
    return [
        {
            "slot_id": s["slot_id"],
            "facility_id": s["facility_id"],
            "specialty_id": s["specialty_id"],
            "doctor_id": s["doctor_id"],
            "date": s["date"],
            "time": s["time"],
            "available": bool(s.get("available")),
            "selectable": bool(s.get("available")),
        }
        for s in raw
    ]


def get_booking_form_context(
    specialty_id: str,
    *,
    facility_id: str | None = None,
    doctor_id: str | None = None,
    slot_id: str | None = None,
) -> BookingFormContextResult:
    """
    Nested payload for FE: change facility → doctors filtered; change doctor → slots.
    """
    facilities = get_form_facilities(specialty_id)
    doctors: list[FormDoctorOption] = []
    slots_by_doctor: dict[str, list[FormSlotOption]] = {}

    if facility_id:
        doctors = get_form_doctors(specialty_id, facility_id)
        for doc in doctors:
            did = doc["doctor_id"]
            slots_by_doctor[did] = get_form_slots(
                specialty_id, facility_id, doctor_id=did
            )

    if doctor_id and facility_id and doctor_id not in slots_by_doctor:
        slots_by_doctor[doctor_id] = get_form_slots(
            specialty_id, facility_id, doctor_id=doctor_id
        )

    if slot_id and facility_id and doctor_id:
        slots = slots_by_doctor.get(doctor_id) or get_form_slots(
            specialty_id, facility_id, doctor_id=doctor_id
        )
        if not any(s["slot_id"] == slot_id for s in slots):
            slot_id = None

    return {
        "specialty_id": specialty_id,
        "selected": {
            "facility_id": facility_id,
            "doctor_id": doctor_id,
            "slot_id": slot_id,
        },
        "facilities": facilities,
        "doctors": doctors,
        "slots_by_doctor": slots_by_doctor,
    }
