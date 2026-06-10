"""Core orchestration logic for IndiaInc Today.

Integrates fetching, parsing, enrichment, and output generation.
"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional
from . import config, utils
from .enrichment import StockEnricher
from .industry import get_company_industry
from .xbrl_fetcher import XBRLFetcher
from .xbrl_parser import XBRLParser

logger = logging.getLogger(__name__)


def generate_digest(
    segment: str,
    target_date: str,
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch, parse, enrich, and save XBRL announcements for a segment and date.

    Args:
        segment: Exchange segment ('nse-main' or 'nse-sme').
        target_date: Target date string (DD-MM-YYYY).
        output_file: Optional path to save the JSON output to. If None, it will
          be auto-determined based on the segment.

    Returns:
        The generated digest dictionary.
    """
    logger.info(f"Starting digest generation for {segment} on date {target_date}")

    # Set default output file if not provided
    if not output_file:
        if segment == "nse-sme":
            output_file = "nse_sme_output.json"
        else:
            output_file = "nse_main_output.json"

    # Initialize shared components
    fetcher = XBRLFetcher()
    # Share the fetcher's nse client session
    parser = XBRLParser(fetcher.nse)
    enricher = StockEnricher(fetcher.nse)

    # 1. Fetch raw listings
    raw_listings = fetcher.fetch_all_listings(
        segment=segment,
        from_date=target_date,
        to_date=target_date,
    )

    logger.info(f"Total listings fetched: {len(raw_listings)}")

    # 2. Process and Enrich listings
    grouped_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    is_sme = segment == "nse-sme"

    for idx, item in enumerate(raw_listings):
        symbol = item.get("symbol", "").strip()
        company_name = item.get("companyName", "").strip()
        event_type = item.get("eventType") or item.get("subOfAnn") or "Unknown Event"
        broadcast_dt = (
            item.get("broadcastDateTime") or item.get("disseminationDateTime") or ""
        )
        xbrl_type = item.get("xbrl_type_code", "Unknown")
        app_id = item.get("appId")

        # Clean up event type from suffix if present
        if event_type.endswith("-XBRL"):
            event_type = event_type[:-5]

        # Determine XBRL URL
        xbrl_url = item.get("xbrl") or item.get("attachment")
        ixbrl_url = item.get("ixbrl")

        # Download & parse XBRL XML if available and feature flag is enabled
        xbrl_data = {}
        if config.PARSE_XBRL_XML and xbrl_url and xbrl_url.lower().endswith(".xml"):
            logger.info(f"[{idx + 1}/{len(raw_listings)}] Parsing XBRL for {symbol}")
            xbrl_data = parser.download_and_parse(xbrl_url)
            # Polite pause to avoid rate limits
            time.sleep(config.REQUEST_DELAY)
        elif xbrl_url and xbrl_url.lower().endswith(".xml"):
            logger.info(
                f"[{idx + 1}/{len(raw_listings)}] Skipping XBRL parsing for {symbol} (feature flag disabled)"
            )
        else:
            logger.warning(
                f"[{idx + 1}/{len(raw_listings)}] No valid XBRL XML URL found for {symbol}"
            )

        # Fetch market enrichment
        enrichment_data = {}
        if symbol:
            try:
                stock_details = enricher.get_stock_details(symbol, is_sme=is_sme)
                industry = get_company_industry(symbol)

                enrichment_data = {
                    "current_price": stock_details.get("current_price"),
                    "current_mkt_cap_cr": stock_details.get("current_mkt_cap_cr"),
                    "week_52_high": stock_details.get("week_52_high"),
                    "week_52_low": stock_details.get("week_52_low"),
                    "p_change": stock_details.get("p_change"),
                    "previous_close": stock_details.get("previous_close"),
                    "industry": industry,
                }

                # Update company name from quote if available and more complete
                if stock_details.get("company_name"):
                    company_name = stock_details["company_name"]
            except Exception as e:
                logger.error(f"Failed to enrich stock {symbol}: {e}")

        # Build clean record
        record = {
            "symbol": symbol,
            "company_name": company_name,
            "event_type": event_type,
            "broadcast_dt": broadcast_dt,
            "xbrl_url": xbrl_url,
            "ixbrl_url": ixbrl_url,
            "app_id": app_id,
            "enrichment": enrichment_data,
            "xbrl_data": xbrl_data,
        }

        # Group by category name
        category_name = config.XBRL_TYPE_CODES.get(xbrl_type, "Others")
        grouped_data[category_name].append(record)

    # Sort filings within each category by broadcast date descending (latest first)
    for category in grouped_data:
        grouped_data[category].sort(
            key=lambda x: x.get("broadcast_dt", ""), reverse=True
        )

    # Determine human-readable exchange name
    exchange_name = "NSE SME" if is_sme else "NSE Mainboard"

    # Save output to disk
    utils.save_output(
        data=dict(grouped_data),
        exchange_name=exchange_name,
        target_date=target_date,
        filename=output_file,
    )

    logger.info(f"Digest generation completed for {exchange_name}")
    return {
        "meta": {
            "exchange": exchange_name,
            "date": target_date,
            "total_announcements": len(raw_listings),
        },
        "data": dict(grouped_data),
    }
