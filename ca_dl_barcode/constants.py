"""
AAMVA / California DL-ID constants for the 2017-2025 California REAL ID design.

Everything in this module is sourced directly from the AAMVA DL/ID Card Design
Standard (the PDF417 / 2D barcode annex, Annex D).  The California-specific
values (IIN, AAMVA version, class/restriction conventions) reflect the design
that was in production from 2018 through October 2025.

References
---------
* AAMVA DL/ID Card Design Standard, Annex D "PDF417 bar code"
  - D.12.3 Header
  - D.12.4 Subfile Designator
  - D.12.5 Data elements (Tables D.3 mandatory, D.4 optional)
  - D.13 Example of raw PDF417 data (used as the golden test vector)
* California IIN 636014 (AAMVA Issuer Identification Number registry)
* AAMVA D-20 data dictionary (eye / hair colour 3-letter codes)
"""

# --------------------------------------------------------------------------- #
# AAMVA control characters (D.12.3)
# --------------------------------------------------------------------------- #
COMPLIANCE_INDICATOR = "@"          # ASCII 0x40
DATA_ELEMENT_SEPARATOR = "\n"       # LF,  ASCII 0x0A  (between data elements)
RECORD_SEPARATOR = "\x1e"           # RS,  ASCII 0x1E  (header only)
SEGMENT_TERMINATOR = "\r"           # CR,  ASCII 0x0D  (ends each subfile)
FILE_TYPE = "ANSI "                 # 5 bytes, note the trailing space

# --------------------------------------------------------------------------- #
# California header values
# --------------------------------------------------------------------------- #
CALIFORNIA_IIN = "636014"           # 6-digit Issuer Identification Number
DEFAULT_AAMVA_VERSION = "09"        # AAMVA Card Design Standard 09-2016 (v09)
DEFAULT_JURISDICTION_VERSION = "00" # CA jurisdiction revision within v09
COUNTRY_USA = "USA"                 # DCG value for the United States

# Subfile type designators (D.12.4)
SUBFILE_TYPE_DL = "DL"              # Driver-license data
SUBFILE_TYPE_ID = "ID"             # Non-driver identification card
SUBFILE_TYPE_CA_JURISDICTION = "ZC"  # "Z" + first letter of "California"

# Fixed header sizes (bytes) - used to compute subfile offsets (D.12.3 / D.12.4)
HEADER_FIXED_BYTES = 21            # @, LF, RS, CR, "ANSI ", IIN(6), ver(2),
#                                   jurisdiction(2), entries(2)
SUBFILE_DESIGNATOR_BYTES = 10      # type(2) + offset(4) + length(4)

# Sentinels the standard defines for mandatory elements (D.12.5)
VALUE_NONE = "NONE"                # mandatory element that legitimately has no data
VALUE_UNAVAILABLE = "unavl"        # mandatory element whose data is not available

# --------------------------------------------------------------------------- #
# Enumerated value sets
# --------------------------------------------------------------------------- #
# DBC Physical Description - Sex (Table D.3, F1N)
SEX_CODES = {
    "1": "Male",
    "2": "Female",
    "9": "Not specified",
}

# DAY Eye colour - AAMVA D-20 three-letter codes (Table D.3, F3A)
EYE_COLORS = {
    "BLK": "Black",
    "BLU": "Blue",
    "BRO": "Brown",
    "DIC": "Dichromatic",
    "GRY": "Gray",
    "GRN": "Green",
    "HAZ": "Hazel",
    "MAR": "Maroon",
    "PNK": "Pink",
    "UNK": "Unknown",
}

# DAZ Hair colour - AAMVA D-20 three-letter codes (Table D.4, V12A)
HAIR_COLORS = {
    "BAL": "Bald",
    "BLK": "Black",
    "BLN": "Blond",
    "BRO": "Brown",
    "GRY": "Gray",
    "RED": "Red/Auburn",
    "SDY": "Sandy",
    "WHI": "White",
    "UNK": "Unknown",
}

# DDE / DDF / DDG Name truncation (Table D.3, F1A)
TRUNCATION_CODES = {
    "N": "Not truncated",
    "T": "Truncated",
    "U": "Unknown",
}

# DDA Compliance type - DHS / REAL ID (Table D.4, F1A)
COMPLIANCE_TYPES = {
    "F": "REAL ID compliant",
    "N": "Non-compliant (federal limits apply)",
}

# DCE Physical Description - Weight range (Table D.4, F1N)
WEIGHT_RANGES = {
    "0": "up to 31 kg (up to 70 lbs)",
    "1": "32-45 kg (71-100 lbs)",
    "2": "46-59 kg (101-130 lbs)",
    "3": "60-70 kg (131-160 lbs)",
    "4": "71-86 kg (161-190 lbs)",
    "5": "87-100 kg (191-220 lbs)",
    "6": "101-113 kg (221-250 lbs)",
    "7": "114-127 kg (251-280 lbs)",
    "8": "128-145 kg (281-320 lbs)",
    "9": "146+ kg (321+ lbs)",
}

# US state / territory codes accepted for DAJ (Address - Jurisdiction Code).
# California is the only value a real CA card carries, but the field is a
# standard 2-letter jurisdiction code, so the full set is offered.
US_JURISDICTIONS = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
]

# Height units accepted for DAU (Table D.3 -> "073 in" / "181 cm")
HEIGHT_UNIT_INCHES = "in"
HEIGHT_UNIT_CM = "cm"
