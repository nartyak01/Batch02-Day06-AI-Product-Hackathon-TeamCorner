"""Update contact info on existing booking — no LLM."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

from .list_bookings import enrich_booking, get_booking
from .storage import update_by_ticket_id


class UpdateBookingInput(TypedDict, total=False):
    name: str
    phone: str
    email: str
    dob: str
    notes: str


class UpdateBookingResult(TypedDict):
    ok: bool
    booking: dict
    message: str


ALLOWED_PATCH = frozenset({"name", "phone", "email", "dob", "notes"})


def update_booking(ticket_id: str, data: UpdateBookingInput) -> UpdateBookingResult:
    existing = get_booking(ticket_id)
    if not existing:
        return {"ok": False, "booking": {}, "message": "Không tìm thấy ticket"}

    patch: dict[str, str] = {}
    for key in ALLOWED_PATCH:
        if key in data and data[key] is not None:
            patch[key] = str(data[key]).strip()

    if not patch:
        return {"ok": False, "booking": existing, "message": "Không có trường cần cập nhật"}

    patch["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated_row = update_by_ticket_id(ticket_id, patch)
    if not updated_row:
        return {"ok": False, "booking": {}, "message": "Cập nhật thất bại"}

    return {
        "ok": True,
        "booking": enrich_booking(updated_row),
        "message": "Đã cập nhật thông tin",
    }
