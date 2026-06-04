"""Persist bookings to data/bookings.csv — PII stays here only."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

_CODEBASE_ROOT = Path(__file__).resolve().parents[3]
BOOKINGS_PATH = _CODEBASE_ROOT / "data" / "bookings.csv"

BOOKING_COLUMNS = [
    "ticket_id",
    "created_at",
    "name",
    "phone",
    "email",
    "dob",
    "facility_id",
    "specialty_id",
    "doctor_id",
    "slot_id",
    "symptom_summary",
    "status",
    "notes",
    "updated_at",
]


def _ensure_file() -> None:
    if not BOOKINGS_PATH.exists():
        with BOOKINGS_PATH.open("w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=BOOKING_COLUMNS).writeheader()


def load_all_bookings() -> list[dict[str, str]]:
    _ensure_file()
    with BOOKINGS_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader if row.get("ticket_id")]


def save_all_bookings(rows: list[dict[str, str]]) -> None:
    _ensure_file()
    with BOOKINGS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=BOOKING_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in BOOKING_COLUMNS})


def append_booking(row: dict[str, str]) -> dict[str, str]:
    rows = load_all_bookings()
    rows.append({col: row.get(col, "") for col in BOOKING_COLUMNS})
    save_all_bookings(rows)
    return row


def find_by_ticket_id(ticket_id: str) -> dict[str, str] | None:
    for row in load_all_bookings():
        if row.get("ticket_id") == ticket_id:
            return row
    return None


def update_by_ticket_id(ticket_id: str, patch: dict[str, str]) -> dict[str, str] | None:
    rows = load_all_bookings()
    updated: dict[str, str] | None = None
    for i, row in enumerate(rows):
        if row.get("ticket_id") != ticket_id:
            continue
        merged = {**row, **{k: v for k, v in patch.items() if k in BOOKING_COLUMNS}}
        rows[i] = merged
        updated = merged
        break
    if updated is None:
        return None
    save_all_bookings(rows)
    return updated
