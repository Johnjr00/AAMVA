"""
End-to-end scannability test: encode -> render PDF417 image -> decode it back
and confirm the payload survives byte-for-byte.

Requires the optional ``pdf417decoder`` dev dependency (which pulls in OpenCV);
the test is skipped automatically when it is not installed, so the core suite
runs without it.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ca_dl_barcode import barcode, encoder
from ca_dl_barcode.model import LicenseData, ZCSubfile

pytest.importorskip("pdf417decoder", reason="pdf417decoder not installed")
pytest.importorskip("PIL", reason="Pillow not installed")


def _sample() -> LicenseData:
    return LicenseData(
        family_name="CARDHOLDER", first_name="JANE", middle_name="QUINCY",
        issue_date="01/15/2020", expiry_date="03/22/2028", dob="05/12/1985",
        sex="2", eye_color="BRN", hair_color="BRN", height_value="65",
        street1="1234 MAIN ST", city="LOS ANGELES", state="CA",
        postal_code="90001", dl_number="D1234567", vehicle_class="C",
        restrictions="NONE", endorsements="NONE",
        document_discriminator="ABCD1234567890", compliance_type="F",
        card_revision_date="01/01/2018", organ_donor=True,
        zc=ZCSubfile(),
    )


def test_rendered_png_decodes_to_original_payload(tmp_path):
    from PIL import Image
    from pdf417decoder import PDF417Decoder

    payload = encoder.encode(_sample())
    png = tmp_path / "barcode.png"
    barcode.save_png(payload, str(png))

    decoder = PDF417Decoder(Image.open(str(png)))
    assert decoder.decode() == 1, "exactly one PDF417 symbol expected"
    assert decoder.barcode_data_index_to_string(0) == payload


def test_svg_is_written(tmp_path):
    payload = encoder.encode(_sample())
    svg = tmp_path / "barcode.svg"
    barcode.save_svg(payload, str(svg))
    content = svg.read_text(encoding="utf-8")
    assert content.lstrip().startswith("<?xml")
    assert "<svg" in content
