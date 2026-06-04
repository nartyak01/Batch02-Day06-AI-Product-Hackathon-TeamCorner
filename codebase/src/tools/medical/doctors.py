"""Doctor listing with slot availability summary."""

from __future__ import annotations

from typing import Any, TypedDict

from .catalog import get_doctors, get_slots


class DoctorWithAvailability(TypedDict):
    doctor_id: str
    name: str
    title: str
    specialty_id: str
    facility_id: str
    availability_status: str
    has_open_slot: bool
    open_slot_count: int
    total_slot_count: int
    needs_check: bool


def _slot_summary(doctor_id: str) -> tuple[bool, int, int]:
    slots = get_slots(doctor_id=doctor_id)
    total = len(slots)
    open_count = sum(1 for s in slots if s.get("available"))
    return open_count > 0, open_count, total


def list_doctors_by_specialty(
    specialty_id: str,
    *,
    facility_id: str | None = None,
) -> list[DoctorWithAvailability]:
    """3 doctors per specialty; availability_status: available | full."""
    result: list[DoctorWithAvailability] = []
    for doc in get_doctors(specialty_id=specialty_id, facility_id=facility_id):
        has_open, open_count, total = _slot_summary(doc["doctor_id"])
        status = (doc.get("availability_status") or "").strip()
        needs_check = status == "available" and total > 0 and 0 < open_count < total
        result.append(
            {
                "doctor_id": doc["doctor_id"],
                "name": doc["name"],
                "title": doc.get("title", ""),
                "specialty_id": doc["specialty_id"],
                "facility_id": doc["facility_id"],
                "availability_status": status,
                "has_open_slot": has_open,
                "open_slot_count": open_count,
                "total_slot_count": total,
                "needs_check": needs_check,
            }
        )
    return result
