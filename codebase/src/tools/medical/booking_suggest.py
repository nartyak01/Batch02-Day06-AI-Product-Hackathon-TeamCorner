"""Agent tools: facilities, doctors, and slot suggestions after specialty is chosen."""

from __future__ import annotations

from typing import Any, TypedDict

from .catalog import get_facilities, get_doctors
from .doctors import list_doctors_by_specialty, DoctorWithAvailability
from .get_available_slots import get_available_slots, SlotResult


class FacilityOption(TypedDict):
    facility_id: str
    name: str
    city: str
    district: str
    address: str


class SuggestBookingPackageResult(TypedDict):
    specialty_id: str
    facility_id: str | None
    facilities: list[FacilityOption]
    doctors: list[DoctorWithAvailability]
    recommended_slots: list[SlotResult]


def list_facilities_for_specialty(specialty_id: str) -> list[FacilityOption]:
    """Facilities that have at least one active doctor for this specialty."""
    docs = get_doctors(specialty_id=specialty_id, active_only=True)
    facility_ids = {d["facility_id"] for d in docs if d.get("facility_id")}
    result: list[FacilityOption] = []
    for f in get_facilities():
        fid = f.get("facility_id")
        if fid not in facility_ids:
            continue
        result.append(
            {
                "facility_id": fid,
                "name": f.get("name", ""),
                "city": f.get("city", ""),
                "district": f.get("district", ""),
                "address": f.get("address", ""),
            }
        )
    return result


def suggest_booking_package(
    specialty_id: str,
    facility_id: str | None = None,
) -> SuggestBookingPackageResult:
    """
    One-shot agent payload: facilities → doctors (filter by facility) → open slots.
    """
    facilities = list_facilities_for_specialty(specialty_id)
    doctors = list_doctors_by_specialty(specialty_id, facility_id=facility_id)

    recommended_slots: list[SlotResult] = []
    if facility_id:
        slot_result = get_available_slots(specialty_id, facility_id=facility_id)
        recommended_slots = slot_result["slots"]
    else:
        for doc in doctors:
            if not doc.get("has_open_slot"):
                continue
            slot_result = get_available_slots(
                specialty_id,
                facility_id=doc["facility_id"],
                doctor_id=doc["doctor_id"],
            )
            recommended_slots.extend(slot_result["slots"])

    return {
        "specialty_id": specialty_id,
        "facility_id": facility_id,
        "facilities": facilities,
        "doctors": doctors,
        "recommended_slots": recommended_slots,
    }
