"""
Minimal AAMVA PDF417 payload parser.

Decodes a raw payload string back into its header fields and per-subfile data
elements.  Used to verify round-trips in the test suite and to power the
"decoded" view in the GUI, so a user can confirm what a scanner will read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from . import constants as C


@dataclass
class ParsedHeader:
    compliance_indicator: str
    file_type: str
    iin: str
    aamva_version: str
    jurisdiction_version: str
    num_entries: int


@dataclass
class ParsedSubfile:
    subfile_type: str
    offset: int
    length: int
    elements: List[Tuple[str, str]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, str]:
        return {eid: value for eid, value in self.elements}


@dataclass
class ParsedBarcode:
    header: ParsedHeader
    subfiles: List[ParsedSubfile]

    def subfile(self, subfile_type: str) -> ParsedSubfile:
        for sf in self.subfiles:
            if sf.subfile_type == subfile_type:
                return sf
        raise KeyError(subfile_type)


def parse(payload: str) -> ParsedBarcode:
    """Parse an AAMVA payload string; raises ValueError on malformed input."""
    if not payload or payload[0] != C.COMPLIANCE_INDICATOR:
        raise ValueError("payload does not start with the '@' compliance indicator")

    # Fixed header (D.12.3).  Bytes: @ LF RS CR, then "ANSI ", IIN(6), ver(2),
    # jurisdiction(2), entries(2) = 21 bytes total.
    if payload[4:9] != C.FILE_TYPE:
        raise ValueError("missing 'ANSI ' file-type marker in header")
    iin = payload[9:15]
    aamva_version = payload[15:17]
    jurisdiction_version = payload[17:19]
    num_entries = int(payload[19:21])

    header = ParsedHeader(
        compliance_indicator=payload[0],
        file_type=C.FILE_TYPE,
        iin=iin,
        aamva_version=aamva_version,
        jurisdiction_version=jurisdiction_version,
        num_entries=num_entries,
    )

    # Subfile designators (D.12.4): each 10 bytes = type(2) + offset(4) + len(4).
    subfiles: List[ParsedSubfile] = []
    pos = C.HEADER_FIXED_BYTES
    for _ in range(num_entries):
        designator = payload[pos:pos + C.SUBFILE_DESIGNATOR_BYTES]
        subfiles.append(ParsedSubfile(
            subfile_type=designator[0:2],
            offset=int(designator[2:6]),
            length=int(designator[6:10]),
        ))
        pos += C.SUBFILE_DESIGNATOR_BYTES

    # Subfile bodies.
    for sf in subfiles:
        body = payload[sf.offset:sf.offset + sf.length]
        if body[:2] != sf.subfile_type:
            raise ValueError(
                f"subfile at offset {sf.offset} does not begin with "
                f"'{sf.subfile_type}'"
            )
        body = body[2:]                        # drop the repeated type prefix
        body = body.rstrip(C.SEGMENT_TERMINATOR)  # drop the terminating CR
        for chunk in body.split(C.DATA_ELEMENT_SEPARATOR):
            if len(chunk) >= 3:
                sf.elements.append((chunk[:3], chunk[3:]))
            elif chunk:
                sf.elements.append((chunk, ""))

    return ParsedBarcode(header=header, subfiles=subfiles)


def to_readable(payload: str) -> str:
    """Return a human-readable dump of the payload for display/debugging."""
    parsed = parse(payload)
    h = parsed.header
    lines = [
        "HEADER",
        f"  Compliance indicator : {h.compliance_indicator}",
        f"  File type            : {h.file_type!r}",
        f"  IIN                  : {h.iin}",
        f"  AAMVA version        : {h.aamva_version}",
        f"  Jurisdiction version : {h.jurisdiction_version}",
        f"  Number of entries    : {h.num_entries}",
    ]
    for sf in parsed.subfiles:
        lines.append("")
        lines.append(f"SUBFILE {sf.subfile_type}  (offset {sf.offset}, length {sf.length})")
        for eid, value in sf.elements:
            lines.append(f"  {eid} : {value}")
    return "\n".join(lines)
