"""Tool 1 — Medical routing (2A202600922)."""

from .red_flags import check_red_flags
from .suggest_specialty import suggest_specialty
from .get_available_slots import get_available_slots
from .doctors import list_doctors_by_specialty
from .specialty_catalog import (
    get_specialty_catalog,
    format_specialty_catalog_for_prompt,
)
from .booking_suggest import (
    list_facilities_for_specialty,
    suggest_booking_package,
)
from .form_context import (
    get_form_facilities,
    get_form_doctors,
    get_form_slots,
    get_booking_form_context,
)
from .catalog import (
    load_catalog,
    get_facilities,
    get_specialties,
    get_doctors,
    get_slots,
)

__all__ = [
    "check_red_flags",
    "suggest_specialty",
    "get_available_slots",
    "list_doctors_by_specialty",
    "list_facilities_for_specialty",
    "suggest_booking_package",
    "get_specialty_catalog",
    "format_specialty_catalog_for_prompt",
    "get_form_facilities",
    "get_form_doctors",
    "get_form_slots",
    "get_booking_form_context",
    "load_catalog",
    "get_facilities",
    "get_specialties",
    "get_doctors",
    "get_slots",
]
