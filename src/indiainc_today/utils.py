"""Utility functions for logging, JSON I/O, string prettification, and currency formatting."""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional
from . import config

logger = logging.getLogger(__name__)


def setup_logging(log_file: str = config.LOG_FILE) -> None:
    """Configure logging to write to a file and console.

    Overwrites the log file on each run.

    Args:
        log_file: Path to the log file.
    """
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(),
        ],
    )


def format_money(val: Any) -> str:
    """Format numeric values as Indian Rupees in Crores or Lakhs.

    Args:
        val: Numeric value or string representing a number.

    Returns:
        Formatted rupee string, or the original value if parsing fails.
    """
    if val is None:
        return ""

    if isinstance(val, str):
        # Remove commas, currency symbols, and spaces
        clean_val = re.sub(r"[^\d\.\-]", "", val)
        try:
            val_num = float(clean_val)
        except ValueError:
            return val
    elif isinstance(val, (int, float)):
        val_num = float(val)
    else:
        return str(val)

    if val_num >= 10000000:
        return f"₹{val_num / 10000000:.2f} Cr"
    elif val_num >= 100000:
        return f"₹{val_num / 100000:.2f} L"
    elif val_num >= 1000:
        return f"₹{val_num:,.2f}"
    else:
        return f"₹{val_num:.2f}"


def prettify_label(name: str) -> str:
    """Convert camelCase/PascalCase field name into spaced, readable title.

    Args:
        name: The raw camelCase/PascalCase field name.

    Returns:
        Spaced title-case version of the field name.
    """
    # Specific overrides for long/ugly fields
    overrides = {
        "WhetherTheAcquisitionWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherSaleOrDisposalWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherTheAmalgamationOrMergerWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherTheAgreementWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherEventOrInformationDisclosedIsAnOutcomeOfBoardMeeting": "Outcome Of Board Meeting",
    }
    if name in overrides:
        return overrides[name]

    # Standard camelCase split
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1 \2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1 \2", s1)
    res = re.sub(r"\s+", " ", s2).strip()
    return res


def save_output(
    data: Dict[str, Any],
    exchange_name: str,
    target_date: str,
    filename: str,
) -> Optional[str]:
    """Save structured JSON output to disk.

    Args:
        data: Nested dictionary containing category mapped to list of filings.
        exchange_name: Human readable name of exchange (e.g., 'NSE Mainboard').
        target_date: Date of the digest (DD-MM-YYYY).
        filename: Output filename to save to.

    Returns:
        The path of the saved file, or None if save failed.
    """
    total_ann = sum(len(filings) for filings in data.values())

    output = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "exchange": exchange_name,
            "date": target_date,
            "total_announcements": total_ann,
        },
        "data": data,
    }

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info(f"Digest output successfully saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save digest output to {filename}: {e}")
        return None
