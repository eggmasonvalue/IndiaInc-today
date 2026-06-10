# CHANGELOG

## [0.3.0] - 2026-06-10
### Added
- Feature flag `PARSE_XBRL_XML` in `config.py` (default: `False`) to disable/enable downloading and parsing of raw XBRL XML documents.
- Extraction of percent price change (`pChange`) and previous close (`previousClose`) in `enrichment.py` to enable real-time trend monitoring.
- Completely redesigned Discord delivery format in `scripts/send_discord_webhook.py` to match the premium FirstFilings aesthetic:
  - Color coding based on filing type category (using category color themes).
  - 52-week price range progress bar (`▓▓▓▓▓░░░░░`).
  - Formatted LTP and percent change with trend arrows (📈/📉) for historical digests, and only LTP for today's digests.
  - Highlighting company industry classifications.
- Added conditional price field formatting:
  - If run for today's digest (`today == digest_date`), only LTP is shown.
  - If run historically (`today > digest_date`), both prices (previous close → LTP) and the percentage change are displayed.
- Added comprehensive unit tests in `tests/test_webhook.py` to cover all formatting, range bar, and embed-building helpers.

## [0.2.0] - 2026-06-09
### Added
- Created remote GitHub repository `IndiaInc-today` using the GitHub CLI and pushed the local `main` branch.

## [0.1.0] - 2026-06-07
### Added
- Initial project scaffold with `uv`, `pytest`, `pytest-cov`, and `ruff`.
- Project structure: `src/indiainc_today/` and `tests/`.
- Context artifacts: OVERVIEW, DESIGN, ARCHITECTURE, CONVENTIONS, and CHANGELOG.
- Symbolically linked `GEMINI.md` to `AGENTS.md`.
- Implemented `config.py` with 8 type codes, exchange segments, and `XBRL_FIELD_BLOCKLIST`.
- Implemented `xbrl_fetcher.py` and `xbrl_parser.py` for downloading, parsing and formatting raw XMLs.
- Implemented `enrichment.py` for NSE stock quotes (LTP, Market Cap, 52W range) with symbol-level caching.
- Implemented `industry.py` for downloading and caching industry map from GitHub.
- Implemented `core.py` orchestrator to bind fetch-parse-enrich steps together.
- Implemented Click CLI in `cli.py` with `digest` and `fetch` commands.
- Implemented `scripts/send_discord_webhook.py` to format and post digested XBRL filings as rich Discord embeds.
- Implemented GitHub Actions daily digest workflow in `.github/workflows/daily-digest.yml`.
- Added mock-based unit tests for all components in `tests/`.
