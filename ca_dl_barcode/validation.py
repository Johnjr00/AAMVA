"""
Input validation for :class:`~ca_dl_barcode.model.LicenseData`.

Validation is split into hard *errors* (block barcode generation) and softer
*warnings* (unusual but encodable).  Length limits and value sets come straight
from AAMVA Tables D.3 / D.4.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from . import constants as C
from .formatting import parse_date
from .model import LicenseData

# Maximum lengths for the free-text elements (from the "Length/type" column).
_MAX_LENGTHS = {
    "family_name": 40,   # DCS V40
    "first_name": 40,    # DAC V40
    "middle_name": 40,   # DAD V40
    "name_suffix": 5,    # DCU V5
    "street1": 35,       # DAG V35
    "street2": 35,       # DAH V35
    "city": 20,          # DAI V20
    "dl_number": 25,     # DAQ V25
    "vehicle_class": 6,  # DCA V6
    "restrictions": 12,  # DCB V12
    "endorsements": 5,   # DCD V5
    "document_discriminator": 25,  # DCF V25
    "inventory_control": 25,       # DCK V25
}

_LABELS = {
    "family_name": "Family name (DCS)",
    "first_name": "First name (DAC)",
    "middle_name": "Middle name (DAD)",
    "name_suffix": "Name suffix (DCU)",
    "street1": "Street address (DAG)",
    "street2": "Street address 2 (DAH)",
    "city": "City (DAI)",
    "dl_number": "DL/ID number (DAQ)",
    "vehicle_class": "Vehicle class (DCA)",
    "restrictions": "Restrictions (DCB)",
    "endorsements": "Endorsements (DCD)",
    "document_discriminator": "Document discriminator (DCF)",
    "inventory_control": "Inventory control (DCK)",
}


@dataclass
class ValidationResult:
    errors: List[str]
    warnings: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def _check_date(label: str, value: str, errors: List[str], *, required: bool) -> None:
    value = (value or "").strip()
    if not value:
        if required:
            errors.append(f"{label} is required.")
        return
    try:
        parse_date(value)
    except ValueError:
        errors.append(f"{label}: '{value}' is not a valid date (use MM/DD/YYYY).")


def validate(data: LicenseData) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    # --- Header ------------------------------------------------------------
    if not re.fullmatch(r"\d{6}", data.iin or ""):
        errors.append("IIN must be exactly 6 digits (California = 636014).")
    elif data.iin != C.CALIFORNIA_IIN:
        warnings.append(
            f"IIN {data.iin} is not California's 636014 - the card will not "
            "read as a California document."
        )
    for label, val in (("AAMVA version", data.aamva_version),
                       ("Jurisdiction version", data.jurisdiction_version)):
        if not re.fullmatch(r"\d{1,2}", str(val or "")):
            errors.append(f"{label} must be a 1-2 digit number.")

    # --- Required text -----------------------------------------------------
    for field_name in ("family_name", "first_name", "dl_number", "street1",
                       "city", "vehicle_class"):
        if not (getattr(data, field_name) or "").strip():
            errors.append(f"{_LABELS[field_name]} is required.")

    # --- Length limits -----------------------------------------------------
    for field_name, limit in _MAX_LENGTHS.items():
        value = getattr(data, field_name) or ""
        if len(value) > limit:
            errors.append(
                f"{_LABELS[field_name]} is too long "
                f"({len(value)} > {limit} characters)."
            )

    # --- Dates -------------------------------------------------------------
    _check_date("Issue date (DBD)", data.issue_date, errors, required=True)
    _check_date("Expiration date (DBA)", data.expiry_date, errors, required=True)
    _check_date("Date of birth (DBB)", data.dob, errors, required=True)
    _check_date("Card revision date (DDB)", data.card_revision_date, errors,
                required=False)

    # --- Enumerations ------------------------------------------------------
    if data.sex not in C.SEX_CODES:
        errors.append("Sex (DBC) must be 1 (male), 2 (female) or 9 (not specified).")
    if data.eye_color and data.eye_color not in C.EYE_COLORS:
        errors.append(
            f"Eye colour (DAY) '{data.eye_color}' is not a valid D-20 code."
        )
    elif not data.eye_color:
        errors.append("Eye colour (DAY) is required.")
    if data.hair_color and data.hair_color not in C.HAIR_COLORS:
        errors.append(
            f"Hair colour (DAZ) '{data.hair_color}' is not a valid D-20 code."
        )
    for label, val in (("Family", data.family_truncation),
                       ("First", data.first_truncation),
                       ("Middle", data.middle_truncation)):
        if val not in C.TRUNCATION_CODES:
            errors.append(f"{label} name truncation must be N, T or U.")
    if data.compliance_type and data.compliance_type not in C.COMPLIANCE_TYPES:
        errors.append("Compliance type (DDA) must be F or N.")

    # --- Physical ----------------------------------------------------------
    if data.height_value:
        digits = re.sub(r"\D", "", data.height_value)
        if not digits:
            errors.append("Height (DAU) must contain a number.")
        elif data.height_unit == C.HEIGHT_UNIT_INCHES and not (30 <= int(digits) <= 96):
            warnings.append("Height in inches looks out of range (expected ~30-96).")
    else:
        errors.append("Height (DAU) is required.")

    # --- Address -----------------------------------------------------------
    if not re.fullmatch(r"[A-Za-z]{2}", data.state or ""):
        errors.append("State (DAJ) must be a 2-letter jurisdiction code.")
    if not (data.postal_code or "").strip():
        errors.append("Postal code (DAK) is required.")

    return ValidationResult(errors=errors, warnings=warnings)
