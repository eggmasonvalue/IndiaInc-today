# DESIGN

## Features Status

| Feature | Status | Justification / Notes |
|---------|--------|-----------------------|
| **Daily Digest** | Done | Implemented via the orchestrator `core.py` and clicked CLI `indiainc-today digest`. |
| **XBRL Parsing** | Done | Direct XML elements extraction in `xbrl_parser.py` with type conversion (`int`, `float`, `bool`) and `config.py` blocklist filtering. Omit dependencies like Arelle. |
| **Market Enrichment** | Done | Integrated `nse` quote details lookup in `enrichment.py` supporting both Mainboard & SME segments, with symbol-level caching. |
| **Industry Mapping** | Done | Ported update-checking industry downloader mapping from stock-industry-map-in in `industry.py` using user-level cache. |
| **Discord Delivery** | Done | Implemented in `scripts/send_discord_webhook.py` which dynamically groups and constructs embeds, respecting Discord char limits. |

## Implementation Details & Trade-offs
- **Blocklist-based parsing**: Hardcoding fields per filing type is fragile because companies use diverse schema variations. Instead, we parse all XML elements, drop redundant/identity tags via a blocklist, and dynamically display the rest.
- **Urllib & Requests dual dep**: The CLI and parser logic reuse `nse.NSE` client which wraps HTTPX for servers, while `scripts/send_discord_webhook.py` uses lightweight `requests` which is standard for webhook posts.
- **Mock-based Unit Tests**: Network queries are mocked out for unit testing CLI, parser, and industry layers.
