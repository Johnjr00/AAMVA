"""
Test suite for the AAMVA encoder.

The centrepiece is a byte-for-byte reproduction of the AAMVA DL/ID Card Design
Standard's own worked example (Annex D.13), which pins the header layout,
subfile offset/length arithmetic, element ordering and terminators.  The rest
exercise California-specific formatting, validation and round-tripping.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ca_dl_barcode import constants as C
from ca_dl_barcode import parser
from ca_dl_barcode.encoder import (
    SubfileBlock, build_header, build_designators, encode,
)
from ca_dl_barcode.model import LicenseData, ZCSubfile
from ca_dl_barcode.validation import validate

LF = C.DATA_ELEMENT_SEPARATOR
RS = C.RECORD_SEPARATOR
CR = C.SEGMENT_TERMINATOR


# --------------------------------------------------------------------------- #
# Golden vector: AAMVA standard Annex D.13 example (Virginia, version 10)
# --------------------------------------------------------------------------- #
# The exact DL subfile elements from the standard's example, in order.
AAMVA_EXAMPLE_DL_ELEMENTS = [
    ("DAQ", "T64235789"),
    ("DCS", "SAMPLE"),
    ("DDE", "N"),
    ("DAC", "MICHAEL"),
    ("DDF", "N"),
    ("DAD", "JOHN"),
    ("DDG", "N"),
    ("DCU", "JR"),
    ("DCA", "D"),
    ("DCB", "K"),
    ("DCD", "PH"),
    ("DBD", "06062019"),
    ("DBB", "06061986"),
    ("DBA", "12102024"),
    ("DBC", "1"),
    ("DAU", "068 in"),
    ("DAY", "BRO"),
    ("DAG", "2300 WEST BROAD STREET"),
    ("DAI", "RICHMOND"),
    ("DAJ", "VA"),
    ("DAK", "232690000  "),
    ("DCF", "2424244747474786102204"),
    ("DCG", "USA"),
    ("DCK", "123456789"),
    ("DDA", "F"),
    ("DDB", "06062018"),
    ("DDC", "06062020"),
    ("DDD", "1"),
]
AAMVA_EXAMPLE_ZV_ELEMENTS = [("ZVA", "01")]


def _build_example_payload():
    """Reproduce the D.13 example payload from its elements via the encoder."""
    dl = SubfileBlock("DL", AAMVA_EXAMPLE_DL_ELEMENTS)
    zv = SubfileBlock("ZV", AAMVA_EXAMPLE_ZV_ELEMENTS)
    header = build_header("636000", "10", "00", 2)
    designators, bodies = build_designators([dl, zv])
    return header + designators + "".join(bodies)


def test_dl_subfile_length_is_278():
    """The DL body must be exactly 278 bytes, as the standard reports."""
    dl = SubfileBlock("DL", AAMVA_EXAMPLE_DL_ELEMENTS)
    assert len(dl.body()) == 278


def test_zv_subfile_length_is_8():
    zv = SubfileBlock("ZV", AAMVA_EXAMPLE_ZV_ELEMENTS)
    assert len(zv.body()) == 8


def test_header_is_21_bytes():
    header = build_header("636000", "10", "00", 2)
    assert len(header) == C.HEADER_FIXED_BYTES == 21


def test_designator_offsets_match_standard():
    dl = SubfileBlock("DL", AAMVA_EXAMPLE_DL_ELEMENTS)
    zv = SubfileBlock("ZV", AAMVA_EXAMPLE_ZV_ELEMENTS)
    designators, _ = build_designators([dl, zv])
    # DL at offset 0041 length 0278; ZV at offset 0319 length 0008.
    assert designators == "DL00410278ZV03190008"


def test_full_example_payload_byte_exact():
    """The whole payload must equal the standard's example, byte for byte."""
    expected = (
        C.COMPLIANCE_INDICATOR + LF + RS + CR + "ANSI "
        + "636000" + "10" + "00" + "02"
        + "DL00410278" + "ZV03190008"
        + "DL"
        + LF.join(f"{e}{v}" for e, v in AAMVA_EXAMPLE_DL_ELEMENTS) + CR
        + "ZV" + "ZVA01" + CR
    )
    assert _build_example_payload() == expected
    # And its length is the sum of all parts.
    assert len(_build_example_payload()) == 21 + 20 + 278 + 8


def test_example_round_trips_through_parser():
    payload = _build_example_payload()
    parsed = parser.parse(payload)
    assert parsed.header.iin == "636000"
    assert parsed.header.aamva_version == "10"
    assert parsed.header.num_entries == 2
    dl = parsed.subfile("DL").as_dict()
    assert dl["DAQ"] == "T64235789"
    assert dl["DAU"] == "068 in"
    assert dl["DAK"] == "232690000  "
    assert parsed.subfile("ZV").as_dict()["ZVA"] == "01"


# --------------------------------------------------------------------------- #
# California-specific behaviour
# --------------------------------------------------------------------------- #
def _sample_ca() -> LicenseData:
    return LicenseData(
        family_name="CARDHOLDER",
        first_name="JANE",
        middle_name="QUINCY",
        issue_date="01/15/2020",
        expiry_date="03/22/2028",
        dob="05/12/1985",
        sex="2",
        eye_color="BRO",
        hair_color="BRO",
        height_value="65",
        height_unit="in",
        street1="1234 MAIN ST",
        city="LOS ANGELES",
        state="CA",
        postal_code="90001",
        dl_number="D1234567",
        vehicle_class="C",
        restrictions="NONE",
        endorsements="NONE",
        document_discriminator="ABCD1234567890",
        country="USA",
        compliance_type="F",
        card_revision_date="01/01/2018",
        organ_donor=True,
        zc=ZCSubfile(zca="", zcb="", zcc="BRO", zcd=""),
    )


def test_ca_header_uses_version_09_and_iin_636014():
    payload = encode(_sample_ca())
    parsed = parser.parse(payload)
    assert parsed.header.iin == C.CALIFORNIA_IIN == "636014"
    assert parsed.header.aamva_version == "09"


def test_ca_includes_zc_subfile_when_present():
    payload = encode(_sample_ca())
    parsed = parser.parse(payload)
    assert parsed.header.num_entries == 2
    assert parsed.subfile("ZC").as_dict()["ZCC"] == "BRO"


def test_ca_omits_zc_subfile_when_empty():
    data = _sample_ca()
    data.zc = ZCSubfile()
    parsed = parser.parse(encode(data))
    assert parsed.header.num_entries == 1
    assert [sf.subfile_type for sf in parsed.subfiles] == ["DL"]


def test_dates_formatted_mmddccyy():
    parsed = parser.parse(encode(_sample_ca()))
    dl = parsed.subfile("DL").as_dict()
    assert dl["DBB"] == "05121985"   # DOB
    assert dl["DBA"] == "03222028"   # expiry
    assert dl["DBD"] == "01152020"   # issue


def test_height_formatted_with_leading_zero_and_unit():
    parsed = parser.parse(encode(_sample_ca()))
    assert parsed.subfile("DL").as_dict()["DAU"] == "065 in"


def test_postal_padded_to_eleven_bytes():
    parsed = parser.parse(encode(_sample_ca()))
    dak = parsed.subfile("DL").as_dict()["DAK"]
    assert dak == "900010000  "
    assert len(dak) == 11


def test_mandatory_missing_middle_name_becomes_none():
    data = _sample_ca()
    data.middle_name = ""
    parsed = parser.parse(encode(data))
    assert parsed.subfile("DL").as_dict()["DAD"] == C.VALUE_NONE


def test_offsets_are_internally_consistent():
    """ZC offset must equal DL offset + DL length for any CA card."""
    payload = encode(_sample_ca())
    parsed = parser.parse(payload)
    dl, zc = parsed.subfiles
    assert zc.offset == dl.offset + dl.length
    # And each subfile body actually sits where the designator claims.
    assert payload[dl.offset:dl.offset + 2] == "DL"
    assert payload[zc.offset:zc.offset + 2] == "ZC"


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_valid_sample_passes():
    assert validate(_sample_ca()).ok


def test_missing_required_fields_flagged():
    data = LicenseData()
    result = validate(data)
    assert not result.ok
    joined = " ".join(result.errors)
    assert "Family name" in joined
    assert "required" in joined


def test_bad_date_flagged():
    data = _sample_ca()
    data.dob = "31/31/2000"
    assert not validate(data).ok


def test_bad_eye_color_flagged():
    data = _sample_ca()
    data.eye_color = "XYZ"
    assert not validate(data).ok
