"""
Field-level formatting helpers that turn user input into the exact byte
representations required by the AAMVA standard (Annex D, Tables D.3 / D.4).

These functions are deliberately forgiving about *input* (they accept a few
common date spellings, height with or without a leading zero, etc.) but strict
about *output* — the returned strings match the standard byte-for-byte.
"""

from __future__ import annotations

import re
from datetime import datetime

from . import constants as C


# --------------------------------------------------------------------------- #
# Dates -> MMDDCCYY (US jurisdictions).  DBA / DBB / DBD / DDB / DDC / DDH...
# --------------------------------------------------------------------------- #
# Input spellings accepted, all normalised to MMDDCCYY on output.
_DATE_INPUT_FORMATS = (
    "%m/%d/%Y",   # 12/31/2024
    "%m-%d-%Y",   # 12-31-2024
    "%Y-%m-%d",   # 2024-12-31 (ISO)
    "%m%d%Y",     # 12312024   (already MMDDYYYY)
    "%Y/%m/%d",   # 2024/12/31
)


def parse_date(value: str) -> datetime:
    """Parse a user-entered date, raising ValueError if it is unusable."""
    value = (value or "").strip()
    if not value:
        raise ValueError("empty date")
    for fmt in _DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {value!r} (use MM/DD/YYYY)")


def format_date(value: str) -> str:
    """
    Format a date as MMDDCCYY (US) per Table D.3.  An empty value yields the
    mandatory-element sentinel so callers never emit a malformed date field.
    """
    value = (value or "").strip()
    if not value:
        return C.VALUE_NONE
    return parse_date(value).strftime("%m%d%Y")


# --------------------------------------------------------------------------- #
# Height -> "0NN in" / "NNN cm"  (DAU, F6ANS, Table D.3)
# --------------------------------------------------------------------------- #
def format_height(value: str, unit: str) -> str:
    """
    Height as three zero-padded digits, a single space and the two-letter unit
    ("073 in" or "181 cm"), exactly 6 bytes.  Empty input -> NONE sentinel.
    """
    value = (value or "").strip()
    if not value:
        return C.VALUE_NONE
    digits = re.sub(r"\D", "", value)
    if not digits:
        return C.VALUE_NONE
    unit = (unit or C.HEIGHT_UNIT_INCHES).strip().lower()
    if unit not in (C.HEIGHT_UNIT_INCHES, C.HEIGHT_UNIT_CM):
        unit = C.HEIGHT_UNIT_INCHES
    return f"{int(digits):03d} {unit}"


# --------------------------------------------------------------------------- #
# Weight -> "NNN"  (DAW pounds / DAX kg, F3N, Table D.4)
# --------------------------------------------------------------------------- #
def format_weight(value: str) -> str:
    """Weight as three zero-padded digits; empty input -> empty (optional)."""
    value = (value or "").strip()
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""
    return f"{int(digits):03d}"


# --------------------------------------------------------------------------- #
# Postal code -> F11ANS  (DAK, Table D.3)
# --------------------------------------------------------------------------- #
def format_postal(value: str) -> str:
    """
    Format a US ZIP for DAK.  Per Table D.3 the trailing portion is zero-filled
    to nine digits when the +4 is unknown; the field is a fixed 11 bytes, so it
    is right-padded with spaces (matching the standard's "232690000  " example).
    Canadian / alphanumeric postal codes are passed through and space-padded.
    """
    value = (value or "").strip().upper()
    if not value:
        return C.VALUE_NONE
    compact = value.replace("-", "").replace(" ", "")
    if compact.isdigit():
        # US ZIP or ZIP+4: pad the numeric portion out to 9 digits.
        compact = (compact + "000000000")[:9] if len(compact) <= 9 else compact[:9]
    # Fixed 11-byte field: right-pad with spaces (never truncate real data).
    return compact.ljust(11)[:11] if len(compact) <= 11 else compact
