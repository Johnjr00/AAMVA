"""
California Driver-License / ID PDF417 (AAMVA) barcode generator.

Generates AAMVA-compliant PDF417 barcode payloads and images for the
California DL/ID card design in production from 2018 through October 2025,
using AAMVA Card Design Standard version 09 (2016) and California IIN 636014.

Intended for testing and development of barcode-reading / ID-verification
software.  See the project README for the full compliance notice.
"""

from .model import LicenseData, ZCSubfile
from .encoder import encode, encode_bytes
from .validation import validate, ValidationResult
from . import barcode, parser, constants

__all__ = [
    "LicenseData",
    "ZCSubfile",
    "encode",
    "encode_bytes",
    "validate",
    "ValidationResult",
    "barcode",
    "parser",
    "constants",
]

__version__ = "1.0.0"
