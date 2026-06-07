"""Enriches NSE corporate announcements with stock quotes and market data."""

import logging
from typing import Any, Dict, Optional
from nse import NSE
from .retries import retry_exchange

logger = logging.getLogger(__name__)

MAINBOARD_SERIES = ("EQ", "BE", "BZ")
SME_SERIES = ("SM", "ST", "SZ")


class StockEnricher:
    """Enriches announcements with real-time stock details from NSE."""

    def __init__(self, nse_client: NSE) -> None:
        """Initialize the enricher with a shared NSE client.

        Args:
            nse_client: The shared NSE client instance.
        """
        self.nse = nse_client
        self._cache: Dict[str, Dict[str, Any]] = {}

    @retry_exchange
    def fetch_quote_for_series(
        self, symbol: str, series: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch quote for a specific series.

        Args:
            symbol: The stock ticker symbol.
            series: The series name (e.g., 'EQ').

        Returns:
            The quote dictionary if successful and valid, otherwise None.
        """
        try:
            q = self.nse.quote(symbol, series=series)
            if (
                q
                and isinstance(q, dict)
                and any(
                    isinstance(q.get(k), dict) and q.get(k)
                    for k in ("metaData", "tradeInfo", "priceInfo")
                )
            ):
                return q
        except Exception as e:
            logger.debug(f"Quote fetch for {symbol} ({series}) failed: {e}")
        return None

    def get_stock_details(self, symbol: str, is_sme: bool = False) -> Dict[str, Any]:
        """Retrieve enriched stock details, using local cache if available.

        Args:
            symbol: The stock symbol.
            is_sme: True if the stock is listed on the SME segment.

        Returns:
            A dictionary containing current price, market cap, and 52-week high/low.
        """
        if symbol in self._cache:
            logger.debug(f"Cache hit for symbol: {symbol}")
            return self._cache[symbol]

        logger.info(f"Fetching stock quote for: {symbol}")
        quote: Optional[Dict[str, Any]] = None
        series_to_try = SME_SERIES if is_sme else MAINBOARD_SERIES

        for series in series_to_try:
            quote = self.fetch_quote_for_series(symbol, series)
            if quote:
                break

        details: Dict[str, Any] = {
            "current_price": None,
            "current_mkt_cap_cr": None,
            "week_52_high": None,
            "week_52_low": None,
            "company_name": None,
        }

        if quote:
            try:
                meta = quote.get("metaData", {})
                details["company_name"] = meta.get("companyName")

                price_info = quote.get("priceInfo", {})
                details["current_price"] = price_info.get("lastPrice") or quote.get(
                    "orderBook", {}
                ).get("lastPrice")
                details["week_52_high"] = price_info.get("yearHigh")
                details["week_52_low"] = price_info.get("yearLow")

                trade_info = quote.get("tradeInfo", {})
                issued_size = trade_info.get("issuedSize")

                if details["current_price"] and issued_size:
                    mkt_cap_raw = float(details["current_price"]) * float(issued_size)
                    details["current_mkt_cap_cr"] = round(mkt_cap_raw / 10000000.0, 2)
            except Exception as e:
                logger.error(f"Error parsing quote data for {symbol}: {e}")

        self._cache[symbol] = details
        return details
