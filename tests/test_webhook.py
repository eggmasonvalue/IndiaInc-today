import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

import send_discord_webhook

def test_fmt_price():
    assert send_discord_webhook._fmt_price(None) == "N/A"
    assert send_discord_webhook._fmt_price(1234.56) == "₹1,234.56"
    assert send_discord_webhook._fmt_price("hello") == "hello"

def test_range_bar():
    res = send_discord_webhook._range_bar(100.0, 200.0, 150.0, width=10)
    assert res is not None
    bar, pct = res
    assert bar == "▓▓▓▓▓░░░░░"
    assert pct == 50.0

def test_format_price_field():
    # Test non-historical (should just return LTP)
    p_field_today = send_discord_webhook._format_price_field(150.0, 2.5, 140.0, is_historical=False)
    assert p_field_today == "₹150.00"

    # Test historical with current price and percentage change
    p_field = send_discord_webhook._format_price_field(150.0, 2.5, None, is_historical=True)
    assert "₹150.00" in p_field
    assert "📈 +2.50%" in p_field

    # Test historical with current price and negative percentage change
    p_field_neg = send_discord_webhook._format_price_field(150.0, -1.25, None, is_historical=True)
    assert "₹150.00" in p_field_neg
    assert "📉 -1.25%" in p_field_neg

    # Test historical with current price and previous close
    p_field_prev = send_discord_webhook._format_price_field(150.0, None, 100.0, is_historical=True)
    assert "₹100.00 → ₹150.00" in p_field_prev
    assert "📈 +50.00%" in p_field_prev

def test_build_header_embed():
    embed = send_discord_webhook.build_header_embed(
        "NSE Mainboard", "10-06-2026", 5, {"Press Release": 3, "Others": 2}
    )
    assert embed["title"] == "📋  NSE Mainboard"
    assert "5" in embed["description"]
    assert "Press Release" in embed["description"]
    assert "Others" in embed["description"]

def test_build_filing_embed():
    filing = {
        "symbol": "TATA",
        "company_name": "Tata Motors",
        "event_type": "Outcome of board meeting",
        "broadcast_dt": "10-Jun-2026 12:00:00",
        "xbrl_url": "https://example.com/file.xml",
        "ixbrl_url": "https://example.com/file.html",
        "enrichment": {
            "current_price": 500.0,
            "current_mkt_cap_cr": 15000.0,
            "week_52_high": 600.0,
            "week_52_low": 400.0,
            "p_change": 1.5,
            "industry": "Automobiles"
        }
    }
    embed = send_discord_webhook.build_filing_embed(filing, "Others")
    assert embed["title"] == "Tata Motors"
    assert embed["url"] == "https://example.com/file.html"
    assert embed["color"] == 0x95A5A6  # Others category color

    # Test with different category
    embed_restr = send_discord_webhook.build_filing_embed(filing, "Restructuring (Reg 30)")
    assert embed_restr["color"] == 0x9B59B6  # Restructuring category color
    
    # Assert fields are present
    field_names = [f["name"] for f in embed["fields"]]
    assert "Symbol" in field_names
    assert "Price" in field_names
    assert "Market Cap" in field_names
    assert "52W Range" in field_names
