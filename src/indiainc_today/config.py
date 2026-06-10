"""Configuration settings for IndiaInc Today.

Contains retry parameters, exchange settings, XBRL type codes, and blocklists.
"""

from typing import Set, Dict, List

# Retry configuration
TOTAL_RETRIES: int = 5
RETRY_MIN_DELAY: float = 1.0  # Minimum delay in seconds
RETRY_MAX_DELAY: float = 30.0  # Maximum delay in seconds
RETRY_MULTIPLIER: float = 2.0  # Multiplier for exponential backoff

# Request delay (to avoid rate limits)
REQUEST_DELAY: float = 0.5  # Seconds between XML downloads

# Logging configuration
LOG_FILE: str = "indiainc_today.log"

# Supported exchange segments
EXCHANGE_SEGMENTS: List[str] = ["nse-main", "nse-sme"]

# Feature Flags
PARSE_XBRL_XML: bool = False


# NSE XBRL Type Codes mapping to descriptive names
XBRL_TYPE_CODES: Dict[str, str] = {
    "Reg30": "Restructuring (Reg 30)",
    "fundRaising": "Issuance of Securities",
    "agr": "Agreements / Contracts",
    "award": "Orders & Contracts",
    "annFraud": "Fraud / Default",
    "cdr": "Corporate Debt Restructuring",
    "CIRP": "Insolvency (IBC)",
    "annOts": "One Time Settlement",
}

# Fields to filter out from raw XBRL parse to avoid boilerplate/redundant info
XBRL_FIELD_BLOCKLIST: Set[str] = {
    # XML plumbing
    "identifier",
    "instant",
    "startDate",
    "endDate",
    "measure",
    "explicitMember",
    # Identity (already captured in enrichment or header)
    "ScripCode",
    "NSESymbol",
    "MSEISymbol",
    "ISIN",
    "NameOfTheCompany",
    # Timestamps & metadata (handled separately)
    "DateOfReport",
    "TypeOfAnnouncement",
    # Domain markers (dimensional axis labels)
    "RestructuringEntityDomain",
    "UnitOrDivisionOrSubsidiaryDomain",
    "PartiesOfTheAgreementDomain",
    "AgendaDomain",
}
