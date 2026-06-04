"""Agent tool: open slots only — for suggesting doctors/times in chat."""

from __future__ import annotations

from typing import Any, TypedDict

from .catalog import get_slots


class SlotResult(TypedDict):
    slot_id: str
    facility_id: str
    specialty_id: str
    doctor_id: str
    date: str
    time: str
    available: bool


class GetAvailableSlotsResult(TypedDict):
    specialty_id: str
    facility_id: str | None
    doctor_id: str | None
    slots: list[SlotResult]


def get_available_slots(
    specialty_id: str,
    facility_id: str | None = None,
    doctor_id: str | None = None,
) -> GetAvailableSlotsResult:
    """Return only bookable slots (available=true) for agent suggestions."""
    raw: list[dict[str, Any]] = get_slots(
        specialty_id=specialty_id,
        facility_id=facility_id,
        doctor_id=doctor_id,
        available_only=True,
    )
    slots: list[SlotResult] = [
        {
            "slot_id": s["slot_id"],
            "facility_id": s["facility_id"],
            "specialty_id": s["specialty_id"],
            "doctor_id": s["doctor_id"],
            "date": s["date"],
            "time": s["time"],
            "available": s["available"],
        }
        for s in raw
    ]
    return {
        "specialty_id": specialty_id,
        "facility_id": facility_id,
        "doctor_id": doctor_id,
        "slots": slots,
    }
