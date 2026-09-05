"""
Data model for a California driver-license / ID PDF417 barcode.

`LicenseData` holds the semantic fields a user enters.  It knows how to turn
itself into the ordered lists of AAMVA data elements that make up the ``DL``
subfile and the California ``ZC`` jurisdiction subfile.  The element *order*
mirrors the AAMVA standard's own normative example (Annex D.13), which groups
each name with its truncation flag.

All formatting (dates -> MMDDCCYY, height -> "0NN in", postal padding, etc.)
lives in :mod:`ca_dl_barcode.formatting` so the model stays declarative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from . import constants as C
from . import formatting as F

# An AAMVA data element is just an (element-id, value) pair.
Element = Tuple[str, str]


@dataclass
class ZCSubfile:
    """
    California jurisdiction-specific ``ZC`` subfile (authoritative CA layout).

    Real California cards encode, in this order:

        * ``ZCB`` - hair colour (California colour code; see constants)
        * ``ZCC`` - present but blank on issued cards
        * ``ZCD`` - present but blank on issued cards

    There is **no** ``ZCA`` element.  When the subfile is emitted, ``ZCC`` and
    ``ZCD`` are always written as empty-valued elements to match issued cards.
    ``ZCB`` (hair colour) is supplied from :attr:`LicenseData.hair_color`, so
    this object only carries the two trailing placeholder elements.
    """

    zcc: str = ""
    zcd: str = ""

    def elements(self, hair_color: str) -> List[Element]:
        """Return the ZC elements (ZCB hair, then blank ZCC and ZCD)."""
        return [
            ("ZCB", hair_color),
            ("ZCC", self.zcc),
            ("ZCD", self.zcd),
        ]


@dataclass
class LicenseData:
    """All fields for one California DL/ID barcode."""

    # -- Header / standard ---------------------------------------------------
    iin: str = C.CALIFORNIA_IIN
    aamva_version: str = C.DEFAULT_AAMVA_VERSION
    jurisdiction_version: str = C.DEFAULT_JURISDICTION_VERSION

    # -- Name (DCS/DAC/DAD/DCU + truncation DDE/DDF/DDG) ---------------------
    family_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    name_suffix: str = ""            # DCU (optional)
    family_truncation: str = "N"     # DDE
    first_truncation: str = "N"      # DDF
    middle_truncation: str = "N"     # DDG

    # -- Dates (MMDDCCYY) ----------------------------------------------------
    issue_date: str = ""             # DBD
    expiry_date: str = ""            # DBA
    dob: str = ""                    # DBB

    # -- Physical description -----------------------------------------------
    sex: str = ""                    # DBC (1/2/9)
    eye_color: str = ""              # DAY (California colour code)
    hair_color: str = ""             # DAZ (DL subfile) AND ZCB (ZC subfile)
    height_value: str = ""           # numeric part of DAU
    height_unit: str = C.HEIGHT_UNIT_INCHES
    weight_lb: str = ""              # DAW (optional)

    # -- Address -------------------------------------------------------------
    street1: str = ""                # DAG
    street2: str = ""                # DAH (optional)
    city: str = ""                   # DAI
    state: str = "CA"                # DAJ
    postal_code: str = ""            # DAK

    # -- License / document --------------------------------------------------
    dl_number: str = ""              # DAQ
    vehicle_class: str = ""          # DCA
    restrictions: str = ""           # DCB
    endorsements: str = ""           # DCD
    document_discriminator: str = "" # DCF
    inventory_control: str = ""      # DCK (optional)
    country: str = C.COUNTRY_USA     # DCG

    # -- REAL ID / DHS -------------------------------------------------------
    compliance_type: str = ""        # DDA (F/N, optional)
    card_revision_date: str = ""     # DDB (optional)
    limited_duration: bool = False   # DDD (optional -> "1")
    organ_donor: bool = False        # DDK (optional -> "1")
    veteran: bool = False            # DDL (optional -> "1")

    # -- California ZC subfile ----------------------------------------------
    zc: ZCSubfile = field(default_factory=ZCSubfile)

    # ----------------------------------------------------------------------- #
    # Element construction
    # ----------------------------------------------------------------------- #
    def _mandatory_value(self, value: str) -> str:
        """Mandatory elements with no data are encoded as the sentinel NONE."""
        return value if value else C.VALUE_NONE

    def dl_elements(self) -> List[Element]:
        """
        Build the ordered ``DL`` subfile elements.

        The 22 mandatory elements (Table D.3) are always present; optional
        elements (Table D.4) are included only when the user supplied a value.
        Ordering follows the AAMVA normative example in Annex D.13.
        """
        e: List[Element] = []

        def add(eid: str, value: str) -> None:
            e.append((eid, value))

        def add_optional(eid: str, value: str) -> None:
            if value:
                e.append((eid, value))

        # Customer id + names, each name paired with its truncation flag.
        add("DAQ", self._mandatory_value(self.dl_number))
        add("DCS", self._mandatory_value(self.family_name))
        add("DDE", self.family_truncation or "N")
        add("DAC", self._mandatory_value(self.first_name))
        add("DDF", self.first_truncation or "N")
        add("DAD", self._mandatory_value(self.middle_name))
        add("DDG", self.middle_truncation or "N")
        add_optional("DCU", self.name_suffix)

        # Driving privileges.
        add("DCA", self._mandatory_value(self.vehicle_class))
        add("DCB", self._mandatory_value(self.restrictions))
        add("DCD", self._mandatory_value(self.endorsements))

        # Dates (MMDDCCYY).
        add("DBD", F.format_date(self.issue_date))
        add("DBB", F.format_date(self.dob))
        add("DBA", F.format_date(self.expiry_date))

        # Physical description.
        add("DBC", self._mandatory_value(self.sex))
        add("DAU", F.format_height(self.height_value, self.height_unit))
        add("DAY", self._mandatory_value(self.eye_color))

        # Address.
        add("DAG", self._mandatory_value(self.street1))
        add_optional("DAH", self.street2)
        add("DAI", self._mandatory_value(self.city))
        add("DAJ", self._mandatory_value(self.state))
        add("DAK", F.format_postal(self.postal_code))

        # Optional physical extras.  California emits hair colour BOTH as the
        # standard AAMVA DAZ element here AND as ZCB in the jurisdiction ZC
        # subfile (see zc_elements); both carry the same California colour code.
        add_optional("DAZ", self.hair_color)
        add_optional("DAW", F.format_weight(self.weight_lb))

        # Document discriminator + country (mandatory).
        add("DCF", self._mandatory_value(self.document_discriminator))
        add("DCG", self._mandatory_value(self.country))
        add_optional("DCK", self.inventory_control)

        # REAL ID / DHS optional block.
        add_optional("DDA", self.compliance_type)
        add_optional("DDB", F.format_date(self.card_revision_date) if self.card_revision_date else "")
        if self.limited_duration:
            add("DDD", "1")
        if self.organ_donor:
            add("DDK", "1")
        if self.veteran:
            add("DDL", "1")

        return e

    def zc_elements(self) -> List[Element]:
        """
        California ZC subfile elements: ZCB (hair colour) then blank ZCC/ZCD.

        Emitted whenever a hair colour (or a ZCC/ZCD override) is supplied,
        matching real California cards.  Returns an empty list - which omits
        the ZC subfile entirely - only when there is nothing to encode.
        """
        if not (self.hair_color or self.zc.zcc or self.zc.zcd):
            return []
        return self.zc.elements(self.hair_color)
