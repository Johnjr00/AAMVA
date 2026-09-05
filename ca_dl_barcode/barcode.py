"""
PDF417 rendering for the AAMVA payload.

Thin wrapper over :mod:`pdf417gen` that:

* encodes the payload as Latin-1 (one byte per AAMVA character, so the LF / RS /
  CR control characters survive intact via PDF417 byte compaction), and
* renders to a PIL image (for the on-screen preview and PNG export) or to an
  SVG vector file.

Defaults (13 data columns, error-correction/security level 5) produce a wide,
card-shaped symbol similar to a real driver-license barcode.  Both are
adjustable for callers that need a different size or robustness.
"""

from __future__ import annotations

from typing import Optional

from pdf417gen import encode, render_image, render_svg

# AAMVA characters are all single bytes; Latin-1 keeps them 1:1.
_PAYLOAD_ENCODING = "latin-1"

DEFAULT_COLUMNS = 13
DEFAULT_SECURITY_LEVEL = 5      # PDF417 error-correction level (0-8)
DEFAULT_SCALE = 3
DEFAULT_RATIO = 3               # module height : width


def build_codes(payload: str, columns: int = DEFAULT_COLUMNS,
                security_level: int = DEFAULT_SECURITY_LEVEL):
    """Encode the AAMVA payload string into PDF417 codewords."""
    return encode(
        payload,
        columns=columns,
        security_level=security_level,
        encoding=_PAYLOAD_ENCODING,
    )


def render_png_image(payload: str, *, columns: int = DEFAULT_COLUMNS,
                     security_level: int = DEFAULT_SECURITY_LEVEL,
                     scale: int = DEFAULT_SCALE, ratio: int = DEFAULT_RATIO,
                     padding: int = 20, fg_color: str = "#000000",
                     bg_color: str = "#FFFFFF"):
    """Render the payload to a PIL ``Image`` (used for preview and PNG save)."""
    codes = build_codes(payload, columns, security_level)
    return render_image(
        codes, scale=scale, ratio=ratio, padding=padding,
        fg_color=fg_color, bg_color=bg_color,
    )


def save_png(payload: str, path: str, *, columns: int = DEFAULT_COLUMNS,
             security_level: int = DEFAULT_SECURITY_LEVEL,
             scale: int = DEFAULT_SCALE, ratio: int = DEFAULT_RATIO,
             padding: int = 20, fg_color: str = "#000000",
             bg_color: str = "#FFFFFF") -> str:
    """Render and write a PNG file; returns the path written."""
    image = render_png_image(
        payload, columns=columns, security_level=security_level,
        scale=scale, ratio=ratio, padding=padding,
        fg_color=fg_color, bg_color=bg_color,
    )
    image.save(path, "PNG")
    return path


def save_svg(payload: str, path: str, *, columns: int = DEFAULT_COLUMNS,
             security_level: int = DEFAULT_SECURITY_LEVEL,
             scale: int = DEFAULT_SCALE, ratio: int = DEFAULT_RATIO,
             color: str = "#000000",
             description: Optional[str] = None) -> str:
    """Render and write a scalable SVG vector file; returns the path written."""
    codes = build_codes(payload, columns, security_level)
    tree = render_svg(codes, scale=scale, ratio=ratio, color=color,
                      description=description)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path
