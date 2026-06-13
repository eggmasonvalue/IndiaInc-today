# DESIGN

## Features Status

| Feature | Status | Justification / Notes |
|---------|--------|-----------------------|
| **Daily Digest** | Done | Implemented via the orchestrator `core.py` and clicked CLI `indiainc-today digest`. |
| **XBRL Parsing** | Done | Feature-flagged (`PARSE_XBRL_XML: bool = False`) XML parsing. When disabled, XML fetching/parsing is bypassed. |
| **Market Enrichment** | Done | Integrated `nse` quote details lookup in `enrichment.py` supporting both Mainboard & SME segments, with symbol-level caching. Enriched with percent change and previous close. |
| **Industry Mapping** | Done | Ported update-checking industry downloader mapping from stock-industry-map-in in `industry.py` using user-level cache. |
| **Discord Delivery** | Done | Redesigned Discord embeds in `scripts/send_discord_webhook.py` using the premium FirstFilings layout style (progress bars, price trends, directional color coding). |
| **BSE XBRL Support** | Deferred | Parked for future implementation. Detailed analysis of challenges in [bse_xbrl_deferred.md](./bse_xbrl_deferred.md). |

## Implementation Details & Trade-offs
- **Feature-flagged XBRL parsing**: Parsing of XBRL XMLs is disabled by default via `config.PARSE_XBRL_XML = False` to favor linking the rich HTML filings directly, matching FirstFilings behavior.
- **Embed Redesign**: Mimics FirstFilings layout, using the filing type category to determine embed colors (matching the color themes defined in the configuration), progress bars for 52W ranges, and clean metadata headers.
- **Urllib & Requests dual dep**: The CLI and parser logic reuse `nse.NSE` client which wraps HTTPX for servers, while `scripts/send_discord_webhook.py` uses lightweight `requests` which is standard for webhook posts.
- **Mock-based Unit Tests**: Network queries are mocked out for unit testing CLI, parser, industry, and webhook helper layers.
- **BSE Support Deferred**: BSE integration is parked due to key API barriers (severe read timeouts on ranges over 2 weeks, block on direct HTTP requests, strict rate limits, and incomplete mapping of rare subcategories). A full analysis, workaround details, and implementation plan are preserved in [bse_xbrl_deferred.md](file:///D:/Misc2/06_backups/IndiaInc-today/.context/bse_xbrl_deferred.md).
