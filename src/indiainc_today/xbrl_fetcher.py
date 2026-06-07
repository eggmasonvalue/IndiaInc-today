"""Fetches corporate XBRL announcement listings from NSE."""

import logging
import time
from typing import Any, Dict, List
from nse import NSE
from . import config
from .retries import retry_exchange

logger = logging.getLogger(__name__)


class XBRLFetcher:
    """Fetcher for NSE XBRL announcements."""

    def __init__(self) -> None:
        """Initialize the fetcher with a server-enabled NSE client."""
        self.nse = NSE(download_folder=".", server=True)
        self.base_url = f"{self.nse.base_url}/XBRL-announcements"

    @retry_exchange
    def fetch_listings_for_type(
        self, index: str, type_code: str, from_date: str, to_date: str
    ) -> List[Dict[str, Any]]:
        """Fetch announcement listings for a single type code.

        Args:
            index: Segment (either 'equities' or 'sme').
            type_code: The type of announcement (e.g., 'Reg30').
            from_date: Start date string (DD-MM-YYYY).
            to_date: End date string (DD-MM-YYYY).

        Returns:
            A list of dictionary objects representing the raw filings.
        """
        params = {
            "index": index,
            "type": type_code,
            "from_date": from_date,
            "to_date": to_date,
        }
        logger.info(
            f"Fetching {type_code} listings for {index} from {from_date} to {to_date}"
        )
        response = self.nse._req(self.base_url, params=params)
        data = response.json()
        if not isinstance(data, list):
            logger.warning(
                f"Unexpected response format for {type_code}: expected list, got {type(data)}"
            )
            return []
        logger.info(f"Fetched {len(data)} listings for {type_code}")
        return data

    def fetch_all_listings(
        self, segment: str, from_date: str, to_date: str
    ) -> List[Dict[str, Any]]:
        """Fetch announcement listings for all configured types.

        Args:
            segment: The exchange segment flag (e.g., 'nse-main', 'nse-sme').
            from_date: Start date string (DD-MM-YYYY).
            to_date: End date string (DD-MM-YYYY).

        Returns:
            A combined flat list of filings across all type codes.
        """
        # Map exchange CLI segment to NSE API index parameter
        index = "sme" if segment == "nse-sme" else "equities"

        all_listings: List[Dict[str, Any]] = []
        for type_code in config.XBRL_TYPE_CODES.keys():
            try:
                listings = self.fetch_listings_for_type(
                    index=index,
                    type_code=type_code,
                    from_date=from_date,
                    to_date=to_date,
                )
                for item in listings:
                    # Enrich the item with the type code we fetched it under
                    item["xbrl_type_code"] = type_code
                all_listings.extend(listings)
                # Polite rate limiting between type fetches
                time.sleep(0.25)
            except Exception as e:
                logger.error(
                    f"Failed to fetch listings for type {type_code} on segment {segment}: {e}"
                )

        return all_listings
