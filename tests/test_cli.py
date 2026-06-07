from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from indiainc_today.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "digest" in result.output
    assert "fetch" in result.output


def test_cli_digest_bse():
    runner = CliRunner()
    result = runner.invoke(cli, ["digest", "--exchange", "bse"])
    assert result.exit_code == 0
    assert "BSE support is currently deferred/unimplemented" in result.output


def test_cli_fetch_bse():
    runner = CliRunner()
    result = runner.invoke(cli, ["fetch", "--exchange", "bse"])
    assert result.exit_code == 0
    assert "BSE support is currently deferred/unimplemented" in result.output


@patch("indiainc_today.cli.generate_digest")
def test_cli_digest_success(mock_generate_digest):
    # Setup mock return value
    mock_generate_digest.return_value = {
        "meta": {
            "exchange": "NSE Mainboard",
            "date": "05-06-2026",
            "total_announcements": 10,
        },
        "data": {},
    }

    runner = CliRunner()
    result = runner.invoke(
        cli, ["digest", "--exchange", "nse-main", "--date", "05-06-2026"]
    )
    assert result.exit_code == 0
    assert "Processing segment: nse-main" in result.output
    assert "Successfully completed nse-main. Found 10 announcements." in result.output
    mock_generate_digest.assert_called_once_with(
        segment="nse-main", target_date="05-06-2026", output_file=None
    )


@patch("indiainc_today.cli.XBRLFetcher")
def test_cli_fetch_success(mock_fetcher_class):
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_all_listings.return_value = [
        {"symbol": "INFY", "appId": "12345"}
    ]
    mock_fetcher_class.return_value = mock_fetcher

    runner = CliRunner()
    result = runner.invoke(
        cli, ["fetch", "--exchange", "nse-main", "--date", "05-06-2026"]
    )
    assert result.exit_code == 0
    assert "Fetching raw listings for nse-main on 05-06-2026..." in result.output
    assert "INFY" in result.output
    mock_fetcher.fetch_all_listings.assert_called_once_with(
        segment="nse-main", from_date="05-06-2026", to_date="05-06-2026"
    )
