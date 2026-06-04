"""Submit booking — no LLM; writes PII to bookings.csv only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict

from src.tools.medical.catalog import get_doctors, get_facilities, get_slots, get_specialties

from .storage import append_booking, load_all_bookings


class SubmitBookingInput(TypedDict, total=False):
    name: str
    phone: str
    email: str
    dob: str
    facility_id: str
    specialty_id: str
    doctor_id: str
    slot_id: str
    symptom_summary: str
    status: str
    notes: str


class SubmitBookingResult(TypedDict):
    ok: bool
    ticket_id: str
    booking: dict[str, str]
    message: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_ticket_id(status: str) -> str:
    prefix = "CALLBACK" if status == "callback" else "VMC"
    seq = len(load_all_bookings()) + 1
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{date_part}-{seq:04d}"


def _validate_refs(
    facility_id: str,
    specialty_id: str,
    doctor_id: str,
    slot_id: str,
) -> str | None:
    if not any(f.get("facility_id") == facility_id for f in get_facilities()):
        return f"facility_id không hợp lệ: {facility_id}"
    if not any(s.get("specialty_id") == specialty_id for s in get_specialties()):
        return f"specialty_id không hợp lệ: {specialty_id}"
    docs = get_doctors(specialty_id=specialty_id, facility_id=facility_id)
    if not any(d.get("doctor_id") == doctor_id for d in docs):
        return f"doctor_id không thuộc khoa/cơ sở: {doctor_id}"
    slots = get_slots(
        specialty_id=specialty_id,
        facility_id=facility_id,
        doctor_id=doctor_id,
    )
    slot = next((s for s in slots if s.get("slot_id") == slot_id), None)
    if not slot:
        return f"slot_id không hợp lệ: {slot_id}"
    if not slot.get("available"):
        return "Khung giờ đã được đặt, vui lòng chọn slot khác"
    return None


def _mark_slot_unavailable(slot_id: str) -> None:
    """Demo: flip slot to booked in slots.csv."""
    from pathlib import Path
    import csv

    path = Path(__file__).resolve().parents[3] / "database" / "slots.csv"
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            if row.get("slot_id") == slot_id:
                row["available"] = "false"
            rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    from src.tools.medical.catalog import load_catalog

    load_catalog(force_reload=True)


def submit_booking(data: SubmitBookingInput) -> SubmitBookingResult:
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    dob = (data.get("dob") or "").strip()
    facility_id = (data.get("facility_id") or "").strip()
    specialty_id = (data.get("specialty_id") or "").strip()
    doctor_id = (data.get("doctor_id") or "").strip()
    slot_id = (data.get("slot_id") or "").strip()
    symptom_summary = (data.get("symptom_summary") or "").strip()
    status = (data.get("status") or "confirmed").strip()
    notes = (data.get("notes") or "").strip()

    if not name or not phone:
        return {
            "ok": False,
            "ticket_id": "",
            "booking": {},
            "message": "Thiếu họ tên hoặc số điện thoại",
        }
    if status not in ("draft", "confirmed", "callback", "pending_review", "cancelled"):
        return {
            "ok": False,
            "ticket_id": "",
            "booking": {},
            "message": f"status không hợp lệ: {status}",
        }

    if status == "confirmed":
        err = _validate_refs(facility_id, specialty_id, doctor_id, slot_id)
        if err:
            return {"ok": False, "ticket_id": "", "booking": {}, "message": err}

    now = _now_iso()
    ticket_id = _generate_ticket_id(status)
    row: dict[str, str] = {
        "ticket_id": ticket_id,
        "created_at": now,
        "name": name,
        "phone": phone,
        "email": email,
        "dob": dob,
        "facility_id": facility_id,
        "specialty_id": specialty_id,
        "doctor_id": doctor_id,
        "slot_id": slot_id,
        "symptom_summary": symptom_summary,
        "status": status,
        "notes": notes,
        "updated_at": now,
    }
    append_booking(row)

    if status == "confirmed" and slot_id:
        _mark_slot_unavailable(slot_id)

    return {
        "ok": True,
        "ticket_id": ticket_id,
        "booking": row,
        "message": "Đặt lịch thành công",
    }
