"""Industry sector mapping lookups for listed Indian stocks.

Fetches data from stock-industry-map-in repository and caches it locally.
"""

import json
import logging
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import HTTPError

logger = logging.getLogger(__name__)

_industry_cache: Optional[Dict[str, List[str]]] = None


def get_industry_map() -> Dict[str, List[str]]:
    """Fetch and return the industry data mapping (symbol -> industry list).

    Uses local cache and ETag header to avoid redundant downloads.

    Returns:
        A dictionary mapping ticker symbols to lists of industry sectors.
    """
    global _industry_cache
    if _industry_cache is not None:
        return _industry_cache

    cache_dir = Path.home() / ".indiainc_today"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "industry_cache.json"
    url = "https://raw.githubusercontent.com/eggmasonvalue/stock-industry-map-in/main/out/industry_data.json"

    cached_data = {"metadata": [], "data": {}, "etag": None}
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read industry cache: {e}")

    headers = {}
    if cached_data.get("etag"):
        headers["If-None-Match"] = cached_data["etag"]

    logger.info("Checking for industry data updates...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            # If request returns successfully with 200 OK:
            new_data = json.loads(response.read().decode("utf-8"))
            etag = response.headers.get("ETag")

            # Update cache file
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "metadata": new_data.get("metadata", []),
                        "data": new_data.get("data", {}),
                        "etag": etag,
                    },
                    f,
                    indent=2,
                )

            logger.info("Industry data updated and cached.")
            _industry_cache = new_data.get("data", {})
            return _industry_cache
    except Exception as e:
        # In urllib, a 304 raises an HTTPError
        if isinstance(e, HTTPError) and e.code == 304:
            logger.info("Industry data is up to date (304 Not Modified)")
            _industry_cache = cached_data.get("data", {})
            return _industry_cache

        logger.error(f"Failed to fetch/update industry data: {e}")
        if cached_data.get("data"):
            logger.info("Falling back to local industry cache.")
            _industry_cache = cached_data.get("data", {})
            return _industry_cache

        _industry_cache = {}
        return _industry_cache


def get_company_industry(symbol: str) -> Optional[str]:
    """Get the industry sector name (e.g., Basic Industry) for a symbol.

    Args:
        symbol: The stock symbol to search.

    Returns:
        The matched industry name or None if not found.
    """
    if not symbol:
        return None
    industry_map = get_industry_map()
    sym_key = symbol.strip().upper()

    industry_list = industry_map.get(sym_key)
    if not industry_list and sym_key not in industry_map:
        # Fallback to standard check
        industry_list = industry_map.get(symbol.strip())

    if industry_list and isinstance(industry_list, list) and len(industry_list) > 0:
        # The final industry level is the last item in the list
        return industry_list[-1]
    return None
