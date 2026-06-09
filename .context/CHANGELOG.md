# CHANGELOG

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
