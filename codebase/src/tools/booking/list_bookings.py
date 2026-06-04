"""List / get bookings for FE — tab Lịch đã đặt."""

from __future__ import annotations

from typing import Any, TypedDict

from src.tools.medical.catalog import get_doctors, get_facilities, get_slots, get_specialties

from .storage import find_by_ticket_id, load_all_bookings


class EnrichedBooking(TypedDict, total=False):
    ticket_id: str
    created_at: str
    updated_at: str
    name: str
    phone: str
    email: str
    dob: str
    facility_id: str
    facility_name: str
    specialty_id: str
    specialty_name: str
    doctor_id: str
    doctor_name: str
    slot_id: str
    slot_date: str
    slot_time: str
    symptom_summary: str
    status: str
    notes: str


def _lookup_maps() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    facilities = {f["facility_id"]: f for f in get_facilities()}
    specialties = {s["specialty_id"]: s for s in get_specialties()}
    doctors = {d["doctor_id"]: d for d in get_doctors(active_only=False)}
    slots = {s["slot_id"]: s for s in get_slots()}
    return facilities, specialties, doctors, slots


def enrich_booking(row: dict[str, str]) -> EnrichedBooking:
    facilities, specialties, doctors, slots = _lookup_maps()
    fid = row.get("facility_id", "")
    sid = row.get("specialty_id", "")
    did = row.get("doctor_id", "")
    slot_id = row.get("slot_id", "")
    slot = slots.get(slot_id, {})
    return {
        "ticket_id": row.get("ticket_id", ""),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
        "name": row.get("name", ""),
        "phone": row.get("phone", ""),
        "email": row.get("email", ""),
        "dob": row.get("dob", ""),
        "facility_id": fid,
        "facility_name": facilities.get(fid, {}).get("name", ""),
        "specialty_id": sid,
        "specialty_name": specialties.get(sid, {}).get("name", ""),
        "doctor_id": did,
        "doctor_name": doctors.get(did, {}).get("name", ""),
        "slot_id": slot_id,
        "slot_date": slot.get("date", ""),
        "slot_time": slot.get("time", ""),
        "symptom_summary": row.get("symptom_summary", ""),
        "status": row.get("status", ""),
        "notes": row.get("notes", ""),
    }


def list_bookings(
    *,
    phone: str | None = None,
    status: str | None = None,
) -> list[EnrichedBooking]:
    rows = load_all_bookings()
    if phone:
        phone_norm = phone.strip()
        rows = [r for r in rows if r.get("phone", "").strip() == phone_norm]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return [enrich_booking(r) for r in rows]


def get_booking(ticket_id: str) -> EnrichedBooking | None:
    row = find_by_ticket_id(ticket_id)
    if not row:
        return None
    return enrich_booking(row)
