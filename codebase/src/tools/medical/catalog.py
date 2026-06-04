"""Load medical catalog from data/*.csv."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

_CODEBASE_ROOT = Path(__file__).resolve().parents[3]
_DB_DIR = _CODEBASE_ROOT / "data"

_catalog_cache: dict[str, list[dict[str, Any]]] | None = None

_CATALOG_FILES = ("facilities", "specialties", "doctors", "slots")


def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in ("true", "1", "yes", "y")


def _normalize_row(name: str, row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = dict(row)
    if name in ("facilities", "doctors", "specialties"):
        out["active"] = _parse_bool(row.get("active"))
    if name == "doctors":
        out["availability_status"] = (row.get("availability_status") or "").strip()
    if name == "slots":
        out["available"] = _parse_bool(row.get("available"))
    return out


def _load_csv(name: str) -> list[dict[str, Any]]:
    path = _DB_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [_normalize_row(name, row) for row in reader]


def load_catalog(force_reload: bool = False) -> dict[str, list[dict[str, Any]]]:
    global _catalog_cache
    if _catalog_cache is not None and not force_reload:
        return _catalog_cache
    _catalog_cache = {name: _load_csv(name) for name in _CATALOG_FILES}
    return _catalog_cache


def get_facilities(*, active_only: bool = True) -> list[dict[str, Any]]:
    items = load_catalog()["facilities"]
    if active_only:
        return [f for f in items if f.get("active", True)]
    return items


def get_specialties(*, active_only: bool = True) -> list[dict[str, Any]]:
    items = load_catalog()["specialties"]
    if active_only:
        return [s for s in items if s.get("active", True)]
    return items


def get_doctors(
    *,
    specialty_id: str | None = None,
    facility_id: str | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    items = load_catalog()["doctors"]
    if active_only:
        items = [d for d in items if d.get("active", True)]
    if specialty_id:
        items = [d for d in items if d.get("specialty_id") == specialty_id]
    if facility_id:
        items = [d for d in items if d.get("facility_id") == facility_id]
    return items


def get_slots(
    *,
    specialty_id: str | None = None,
    facility_id: str | None = None,
    doctor_id: str | None = None,
    available_only: bool = False,
) -> list[dict[str, Any]]:
    items = load_catalog()["slots"]
    if specialty_id:
        items = [s for s in items if s.get("specialty_id") == specialty_id]
    if facility_id:
        items = [s for s in items if s.get("facility_id") == facility_id]
    if doctor_id:
        items = [s for s in items if s.get("doctor_id") == doctor_id]
    if available_only:
        items = [s for s in items if s.get("available", False)]
    return items
