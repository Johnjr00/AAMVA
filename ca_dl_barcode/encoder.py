"""
AAMVA PDF417 payload encoder.

Assembles the raw byte string that gets encoded into the PDF417 barcode,
following AAMVA DL/ID Card Design Standard Annex D:

    * D.12.3 Header            (21 fixed bytes)
    * D.12.4 Subfile Designator (10 bytes each: type + offset + length)
    * D.12.5 Data elements      (subfile body = type + LF-joined elements + CR)

The implementation is verified byte-for-byte against the standard's own
worked example (Annex D.13) in the test suite.
"""

from __future__ import annotations

from typing import List, Tuple

from . import constants as C
from .model import Element, LicenseData


class SubfileBlock:
    """A subfile's type plus its ordered data elements."""

    def __init__(self, subfile_type: str, elements: List[Element]):
        self.subfile_type = subfile_type
        self.elements = elements

    def body(self) -> str:
        """
        Encode the subfile body:  ``TYPE`` + element0 + LF + element1 + LF ...
        + elementN + CR.  The 2-char type and the terminating CR are part of
        the byte length reported in the designator (D.12.4).
        """
        pieces = [f"{eid}{value}" for eid, value in self.elements]
        return (
            self.subfile_type
            + C.DATA_ELEMENT_SEPARATOR.join(pieces)
            + C.SEGMENT_TERMINATOR
        )


def build_header(iin: str, aamva_version: str, jurisdiction_version: str,
                 num_entries: int) -> str:
    """Assemble the fixed 21-byte header (D.12.3), zero-filled numerics."""
    return (
        C.COMPLIANCE_INDICATOR
        + C.DATA_ELEMENT_SEPARATOR
        + C.RECORD_SEPARATOR
        + C.SEGMENT_TERMINATOR
        + C.FILE_TYPE
        + f"{iin:>6}"
        + f"{int(aamva_version):02d}"
        + f"{int(jurisdiction_version):02d}"
        + f"{num_entries:02d}"
    )


def build_designators(blocks: List[SubfileBlock]) -> Tuple[str, List[str]]:
    """
    Build the concatenated subfile designators and the ordered subfile bodies.

    Offsets are measured from byte 0 of the whole symbol (D.12.4): the first
    subfile body starts immediately after the header and every designator.
    """
    bodies = [b.body() for b in blocks]
    first_offset = C.HEADER_FIXED_BYTES + C.SUBFILE_DESIGNATOR_BYTES * len(blocks)

    designators: List[str] = []
    offset = first_offset
    for block, body in zip(blocks, bodies):
        length = len(body)
        designators.append(f"{block.subfile_type}{offset:04d}{length:04d}")
        offset += length
    return "".join(designators), bodies


def encode(data: LicenseData) -> str:
    """
    Encode a :class:`LicenseData` into the full AAMVA PDF417 payload string.

    Includes the California ``ZC`` jurisdiction subfile when it carries data;
    the mandatory ``DL`` subfile is always present and always first.
    """
    blocks: List[SubfileBlock] = [
        SubfileBlock(C.SUBFILE_TYPE_DL, data.dl_elements())
    ]

    zc_elements = data.zc_elements()
    if zc_elements:
        blocks.append(SubfileBlock(C.SUBFILE_TYPE_CA_JURISDICTION, zc_elements))

    header = build_header(
        data.iin, data.aamva_version, data.jurisdiction_version, len(blocks)
    )
    designators, bodies = build_designators(blocks)
    return header + designators + "".join(bodies)


def encode_bytes(data: LicenseData) -> bytes:
    """The payload as Latin-1 bytes (each AAMVA character is a single byte)."""
    return encode(data).encode("latin-1")
