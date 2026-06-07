"""Command Line Interface for IndiaInc Today.

Supports running digests and raw fetching.
"""

from datetime import datetime
import json
import logging
import sys
from typing import Optional
import click
from . import utils
from .core import generate_digest
from .xbrl_fetcher import XBRLFetcher

logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """IndiaInc Today — Daily digest of key corporate XBRL announcements."""
    pass


@cli.command()
@click.option(
    "--exchange",
    "-e",
    type=click.Choice(["nse-main", "nse-sme", "bse"], case_sensitive=False),
    default=None,
    help="Exchange segment to run. If not specified, runs both nse-main and nse-sme.",
)
@click.option(
    "--date",
    "-d",
    type=str,
    default=None,
    help="Date to digest in DD-MM-YYYY format. Defaults to today.",
)
@click.option(
    "--output",
    "-o",
    type=str,
    default=None,
    help="Output file path (ignored if running both segments).",
)
def digest(exchange: Optional[str], date: Optional[str], output: Optional[str]) -> None:
    """Generate enriched daily digest of XBRL announcements."""
    utils.setup_logging()

    # Determine date
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")
    else:
        try:
            datetime.strptime(date, "%d-%m-%Y")
        except ValueError:
            click.echo(
                f"Error: Invalid date format '{date}'. Must be DD-MM-YYYY.", err=True
            )
            sys.exit(1)

    # Error gracefully for BSE
    if exchange == "bse":
        click.echo(
            "BSE support is currently deferred/unimplemented. Exiting gracefully.",
            err=True,
        )
        sys.exit(0)

    # Determine segments to run
    segments = [exchange] if exchange else ["nse-main", "nse-sme"]

    click.echo(f"Generating digest for date: {date}...")

    for seg in segments:
        click.echo(f"Processing segment: {seg}...")
        try:
            # For multiple segments, we ignore custom output file name to avoid overwriting
            out_file = output if len(segments) == 1 else None
            result = generate_digest(
                segment=seg, target_date=date, output_file=out_file
            )
            click.echo(
                f"Successfully completed {seg}. Found {result['meta']['total_announcements']} announcements."
            )
        except Exception as e:
            logger.exception(f"Error generating digest for {seg}: {e}")
            click.echo(f"Error: Failed to process segment {seg}: {e}", err=True)
            sys.exit(1)

    click.echo("All segments completed successfully.")


@cli.command()
@click.option(
    "--exchange",
    "-e",
    type=click.Choice(["nse-main", "nse-sme", "bse"], case_sensitive=False),
    required=True,
    help="Exchange segment to fetch.",
)
@click.option(
    "--date",
    "-d",
    type=str,
    default=None,
    help="Date to fetch in DD-MM-YYYY format. Defaults to today.",
)
def fetch(exchange: str, date: Optional[str]) -> None:
    """Fetch raw announcements list only, without enrichment or parsing."""
    utils.setup_logging()

    # Determine date
    if not date:
        date = datetime.now().strftime("%d-%m-%Y")
    else:
        try:
            datetime.strptime(date, "%d-%m-%Y")
        except ValueError:
            click.echo(
                f"Error: Invalid date format '{date}'. Must be DD-MM-YYYY.", err=True
            )
            sys.exit(1)

    # Error gracefully for BSE
    if exchange == "bse":
        click.echo(
            "BSE support is currently deferred/unimplemented. Exiting gracefully.",
            err=True,
        )
        sys.exit(0)

    click.echo(f"Fetching raw listings for {exchange} on {date}...")
    try:
        fetcher = XBRLFetcher()
        listings = fetcher.fetch_all_listings(
            segment=exchange, from_date=date, to_date=date
        )
        click.echo(json.dumps(listings, indent=2))
        logger.info(f"Fetched {len(listings)} raw listings for {exchange}")
    except Exception as e:
        logger.exception(f"Error fetching listings: {e}")
        click.echo(f"Error: Failed to fetch listings: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Entry point for the console script."""
    cli()


if __name__ == "__main__":
    main()
