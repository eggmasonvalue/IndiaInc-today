# ARCHITECTURE

## Structure & Data Flow

```mermaid
graph TD
    A["⏰ GitHub Actions / CLI"] --> B["xbrl_fetcher.py (Fetch announcements list)"]
    B --> C["xbrl_parser.py (Download & Parse XBRL XML)"]
    C --> D["enrichment.py (Add Stock Quote details)"]
    D --> E["industry.py (Add Stock Industry details)"]
    E --> F["core.py (Orchestrator to tie components together)"]
    F --> G["utils.py (Formatting & JSON I/O)"]
    F --> H["cli.py (Command Line Interface)"]
    H --> I["send_discord_webhook.py (Discord publication)"]
```

## Directory Structure
```
indiainc-today/
├── src/
│   └── indiainc_today/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── core.py
│       ├── enrichment.py
│       ├── industry.py
│       ├── retries.py
│       ├── utils.py
│       ├── xbrl_fetcher.py
│       └── xbrl_parser.py
├── scripts/
│   └── send_discord_webhook.py
└── tests/
```
