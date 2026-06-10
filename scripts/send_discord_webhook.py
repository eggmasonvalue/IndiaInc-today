#!/usr/bin/env python3
"""Send IndiaInc Today JSON output to Discord via Webhook with rich embeds."""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
import requests

# Discord message limits
MAX_EMBEDS_PER_MESSAGE = 10
MAX_TOTAL_CHARS = 5800
MAX_FIELD_VALUE = 1024

# ── Colours ────────────────────────────────────────────────────────
COLOR_GAIN = 0x2ECC71     # green
COLOR_LOSS = 0xE74C3C     # red
COLOR_NEUTRAL = 0x95A5A6  # grey
COLOR_HEADER = 0x3498DB   # blue

# Category details (Emoji, Color)
CATEGORY_THEMES: Dict[str, Tuple[str, int]] = {
    "Restructuring (Reg 30)": ("🔀", 0x9B59B6),  # Purple
    "Issuance of Securities": ("💰", 0x2ECC71),  # Green
    "Agreements / Contracts": ("📝", 0xF1C40F),  # Yellow
    "Orders & Contracts": ("🏗️", 0x3498DB),  # Blue
    "Fraud / Default": ("🚨", 0xE74C3C),  # Red
    "Corporate Debt Restructuring": ("🤝", 0xE67E22),  # Orange
    "Insolvency (IBC)": ("⚖️", 0x7F8C8D),  # Grey
    "One Time Settlement": ("💸", 0x1ABC9C),  # Turquoise
    "Others": ("📋", 0x95A5A6),  # Light Grey
}


def _fmt_price(p: Any) -> str:
    """Format price as currency with separator."""
    if p is None:
        return "N/A"
    return f"₹{p:,.2f}" if isinstance(p, (int, float)) else str(p)


def _range_bar(low: float, high: float, current: float, width: int = 10) -> Optional[Tuple[str, float]]:
    """Text-based progress bar for 52-week range position."""
    if not all(isinstance(v, (int, float)) for v in (low, high, current)):
        return None
    if high <= low:
        return None
    pct = max(0.0, min(100.0, ((current - low) / (high - low)) * 100))
    filled = round(pct / 100 * width)
    bar = "▓" * filled + "░" * (width - filled)
    return bar, pct


def _format_price_field(curr_price: Any, p_change: Any, prev_close: Any, is_historical: bool = False) -> str:
    """Format Price field. If historical, shows change from previous close. If today's, just LTP."""
    if not is_historical:
        return _fmt_price(curr_price)

    parts = []
    if prev_close is not None and curr_price is not None:
        parts.append(f"{_fmt_price(prev_close)} → {_fmt_price(curr_price)}")
    elif curr_price is not None:
        parts.append(_fmt_price(curr_price))
    
    # Compute or display percentage change
    change_val = None
    if p_change is not None:
        try:
            change_val = float(p_change)
        except ValueError:
            pass
    elif prev_close is not None and curr_price is not None:
        try:
            pc = float(prev_close)
            cc = float(curr_price)
            if pc > 0:
                change_val = ((cc - pc) / pc) * 100
        except ValueError:
            pass

    if change_val is not None:
        sign = "+" if change_val >= 0 else ""
        arrow = "📈" if change_val >= 0 else "📉"
        parts.append(f"{arrow} {sign}{change_val:.2f}%")

    return "\n".join(parts) if parts else "N/A"


def format_money(val: Any) -> str:
    """Format numeric values as Indian Rupees in Crores or Lakhs."""
    if val is None:
        return ""

    if isinstance(val, str):
        clean_val = re.sub(r"[^\d\.\-]", "", val)
        try:
            val_num = float(clean_val)
        except ValueError:
            return val
    elif isinstance(val, (int, float)):
        val_num = float(val)
    else:
        return str(val)

    if val_num >= 10000000:
        return f"₹{val_num / 10000000:.2f} Cr"
    elif val_num >= 100000:
        return f"₹{val_num / 100000:.2f} L"
    elif val_num >= 1000:
        return f"₹{val_num:,.2f}"
    else:
        return f"₹{val_num:.2f}"


def prettify_label(name: str) -> str:
    """Convert camelCase/PascalCase field name into spaced, readable title."""
    overrides = {
        "WhetherTheAcquisitionWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherSaleOrDisposalWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherTheAmalgamationOrMergerWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherTheAgreementWouldFallWithinRelatedPartyTransactions": "Related Party Transaction",
        "WhetherEventOrInformationDisclosedIsAnOutcomeOfBoardMeeting": "Outcome Of Board Meeting",
    }
    if name in overrides:
        return overrides[name]

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1 \2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1 \2", s1)
    res = re.sub(r"\s+", " ", s2).strip()
    return res


def format_value(key: str, val: Any) -> str:
    """Format an individual field value based on key type."""
    if isinstance(val, bool):
        return "Yes" if val else "No"

    # If key implies money and value is numeric
    money_keywords = [
        "amount",
        "turnover",
        "networth",
        "consideration",
        "value",
        "deal",
        "price",
        "capital",
        "assets",
    ]
    key_lower = key.lower()
    if any(kw in key_lower for kw in money_keywords):
        if isinstance(val, (int, float)) or (
            isinstance(val, str) and val.replace(".", "", 1).isdigit()
        ):
            return format_money(val)

    return str(val)


def build_fields_summary(xbrl_data: Dict[str, Any]) -> str:
    """Build a beautifully formatted markdown summary of XBRL data."""
    if not xbrl_data:
        return "*No structured XBRL data parsed.*"

    lines: List[str] = []

    # 1. Target Entity / Buyer / Awarder
    target = (
        xbrl_data.get("NameOfTheTargetEntity")
        or xbrl_data.get("NameOfUnitOrDivisionOrSubsidiary")
        or xbrl_data.get("NameOfRestructuringEntity")
    )
    if target:
        lines.append(f"🎯 **Target**: {target}")

    awarder = xbrl_data.get("NameOfTheEntityAwardingTheOrdersOrContracts")
    if awarder:
        lines.append(f"🏢 **Awarded By**: {awarder}")

    buyer = xbrl_data.get("BriefDetailsOfBuyers")
    if buyer:
        lines.append(f"👤 **Buyer**: {buyer}")

    # 2. Industry
    target_ind = xbrl_data.get("IndustryToWhichTheEntityBeingAcquiredBelongs")
    if target_ind:
        lines.append(f"🏭 **Target Industry**: {target_ind}")

    # 3. Deal Size / Consideration
    deal = (
        xbrl_data.get("AmountOfCashConsiderationForAcquisitionEvent")
        or xbrl_data.get("DetailsOfConsiderationForSaleOrDisposal")
        or xbrl_data.get("AmountOfTheOrdersOrContracts")
        or xbrl_data.get("TotalAmountForWhichTheSecuritiesWillBeIssued")
        or xbrl_data.get("EstimatedAmountInvolvedInFraud")
        or xbrl_data.get("AmountOfTransactionCompleted")
    )
    if deal:
        lines.append(f"💰 **Deal Size**: {format_value('deal', deal)}")

    # 4. Financials grouping (Revenue, PAT, Net Worth)
    rev = xbrl_data.get("TurnoverOfTargetEntity") or xbrl_data.get(
        "PreviousYearTurnoverOfUnitOrDivisionOrSubsidiary"
    )
    pat = xbrl_data.get("ProfitAfterTaxOfTargetEntity")
    nw = xbrl_data.get("NetWorthOfTargetEntity") or xbrl_data.get(
        "PreviousYearNetWorthOfUnitOrDivisionOrSubsidiary"
    )

    if rev is not None or pat is not None or nw is not None:
        fin_parts = []
        if rev is not None:
            fin_parts.append(f"Rev: {format_value('turnover', rev)}")
        if pat is not None:
            fin_parts.append(f"PAT: {format_value('profit', pat)}")
        if nw is not None:
            fin_parts.append(f"NW: {format_value('networth', nw)}")
        lines.append(f"📊 **Financials**: {' | '.join(fin_parts)}")

    # 5. Purpose / Rationale / Nature
    purpose = (
        xbrl_data.get(
            "ObjectsAndImpactOfAcquisitionIncludingButNotLimitedToDisclosureOfReasonsForAcquisitionOfTargetEntityIfItsBusinessIsOutsideTheMainLineOfBusinessOfTheListedEntity"
        )
        or xbrl_data.get("RationaleForAmalgamationOrMerger")
        or xbrl_data.get("DetailsAndReasonForOtherRestructuring")
        or xbrl_data.get("NatureOfOrdersOrContracts")
        or xbrl_data.get("PurposeOfEnteringIntoTheAgreement")
        or xbrl_data.get("NatureOfFraudOrDefaultOrArrest")
        or xbrl_data.get("AgendaItem")
    )
    if purpose:
        # Truncate to avoid extremely long texts
        p_str = str(purpose)
        if len(p_str) > 250:
            p_str = p_str[:247] + "..."
        lines.append(f"📝 **Details**: {p_str}")

    # 6. Timeline / Dates
    timeline = (
        xbrl_data.get("IndicativeTimePeriodForCompletionOfTheAcquisition")
        or xbrl_data.get("TheExpectedDateOfCompletionOfSaleOrDisposal")
        or xbrl_data.get("TimePeriodByWhichTheOrdersOrContractsIsToBeExecuted")
        or xbrl_data.get("DateOfMeetingsOfCommitteeOfCreditors")
    )
    if timeline:
        lines.append(f"📅 **Timeline**: {timeline}")

    # 7. RPT & Relationship
    rpt = (
        xbrl_data.get("WhetherTheAcquisitionWouldFallWithinRelatedPartyTransactions")
        or xbrl_data.get("WhetherSaleOrDisposalWouldFallWithinRelatedPartyTransactions")
        or xbrl_data.get(
            "WhetherTheAmalgamationOrMergerWouldFallWithinRelatedPartyTransactions"
        )
        or xbrl_data.get("WhetherTheAgreementWouldFallWithinRelatedPartyTransactions")
    )
    rel = xbrl_data.get("RelationshipOfAcquirerWithTheListedEntity") or xbrl_data.get(
        "RestructuringEntityRelationshipWithListedEntity"
    )

    rpt_rel = []
    if rpt is not None:
        rpt_rel.append(f"RPT: {'Yes' if rpt else 'No'}")
    if rel:
        rpt_rel.append(f"Rel: {rel}")
    if rpt_rel:
        lines.append(f"🔗 **Info**: {' | '.join(rpt_rel)}")

    # 8. Unhandled Fields Fallback
    handled_keys = {
        "NameOfTheTargetEntity",
        "NameOfUnitOrDivisionOrSubsidiary",
        "NameOfRestructuringEntity",
        "NameOfTheEntityAwardingTheOrdersOrContracts",
        "BriefDetailsOfBuyers",
        "IndustryToWhichTheEntityBeingAcquiredBelongs",
        "AmountOfCashConsiderationForAcquisitionEvent",
        "DetailsOfConsiderationForSaleOrDisposal",
        "AmountOfTheOrdersOrContracts",
        "TotalAmountForWhichTheSecuritiesWillBeIssued",
        "EstimatedAmountInvolvedInFraud",
        "AmountOfTransactionCompleted",
        "TurnoverOfTargetEntity",
        "PreviousYearTurnoverOfUnitOrDivisionOrSubsidiary",
        "ProfitAfterTaxOfTargetEntity",
        "NetWorthOfTargetEntity",
        "PreviousYearNetWorthOfUnitOrDivisionOrSubsidiary",
        "ObjectsAndImpactOfAcquisitionIncludingButNotLimitedToDisclosureOfReasonsForAcquisitionOfTargetEntityIfItsBusinessIsOutsideTheMainLineOfBusinessOfTheListedEntity",
        "RationaleForAmalgamationOrMerger",
        "DetailsAndReasonForOtherRestructuring",
        "NatureOfOrdersOrContracts",
        "PurposeOfEnteringIntoTheAgreement",
        "NatureOfFraudOrDefaultOrArrest",
        "AgendaItem",
        "IndicativeTimePeriodForCompletionOfTheAcquisition",
        "TheExpectedDateOfCompletionOfSaleOrDisposal",
        "TimePeriodByWhichTheOrdersOrContractsIsToBeExecuted",
        "DateOfMeetingsOfCommitteeOfCreditors",
        "WhetherTheAcquisitionWouldFallWithinRelatedPartyTransactions",
        "WhetherSaleOrDisposalWouldFallWithinRelatedPartyTransactions",
        "WhetherTheAmalgamationOrMergerWouldFallWithinRelatedPartyTransactions",
        "WhetherTheAgreementWouldFallWithinRelatedPartyTransactions",
        "RelationshipOfAcquirerWithTheListedEntity",
        "RestructuringEntityRelationshipWithListedEntity",
        "TypeOfEvent",
        "TypeOfEventOfAnnouncementPertainingToRegulation30Restructuring",
        "TypeOfAgreement",
        "DetailsOfOtherTypeOfAnnouncement",
        "TypeOfSecuritiesProposedToBeIssuedUnder",
    }

    remaining_lines = []
    for key, val in xbrl_data.items():
        if key in handled_keys:
            continue
        label = prettify_label(key)
        formatted_val = format_value(key, val)
        if formatted_val:
            remaining_lines.append(f"• **{label}**: {formatted_val}")

    if remaining_lines:
        lines.append("")
        lines.extend(
            remaining_lines[:5]
        )  # Cap at 5 additional fields to prevent overflow
        if len(remaining_lines) > 5:
            lines.append(f"*... and {len(remaining_lines) - 5} more fields.*")

    return "\n".join(lines)


def _embed_char_count(embed: Dict[str, Any]) -> int:
    """Estimate total character count of an embed."""
    n = len(embed.get("title", ""))
    n += len(embed.get("description", ""))
    for f in embed.get("fields", []):
        n += len(f.get("name", ""))
        n += len(f.get("value", ""))
    if "footer" in embed:
        n += len(embed["footer"].get("text", ""))
    if "author" in embed:
        n += len(embed["author"].get("name", ""))
    return n


def build_header_embed(
    exchange_name: str,
    date_str: str,
    total_ann: int,
    category_counts: Dict[str, int],
) -> Dict[str, Any]:
    """Build summary header embed in FirstFilings layout style."""
    cat_list = "  •  ".join(f"**{c}**" for c in sorted(category_counts.keys()))

    embed = {
        "title": f"📋  {exchange_name}",
        "color": COLOR_HEADER,
        "description": (
            f"**{total_ann}** new filing(s) detected.\n"
            f"{cat_list}"
        ),
        "footer": {"text": f"IndiaInc Today  •  {date_str}"},
        "timestamp": datetime.utcnow().isoformat(),
    }
    return embed


def build_filing_embed(filing: Dict[str, Any], category: str, is_historical: bool = False) -> Dict[str, Any]:
    """Build a beautifully formatted rich embed matching FirstFilings style."""
    symbol = filing.get("symbol", "UNKNOWN")
    company_name = filing.get("company_name") or "Unknown Company"
    event_type = filing.get("event_type") or "Corporate Announcement"
    broadcast_dt = filing.get("broadcast_dt") or ""
    xbrl_url = filing.get("xbrl_url")
    ixbrl_url = filing.get("ixbrl_url")
    enrichment = filing.get("enrichment") or {}
    xbrl_data = filing.get("xbrl_data") or {}

    emoji, fallback_color = CATEGORY_THEMES.get(category, CATEGORY_THEMES["Others"])

    # Enrichment details
    current_price = enrichment.get("current_price")
    mkt_cap = enrichment.get("current_mkt_cap_cr")
    week_52_high = enrichment.get("week_52_high")
    week_52_low = enrichment.get("week_52_low")
    p_change = enrichment.get("p_change")
    prev_close = enrichment.get("previous_close")
    industry = enrichment.get("industry")

    color = fallback_color

    # Description layout
    desc_lines = []
    if industry:
        desc_lines.append(f"*{industry}*")
    desc_lines.append(f"📋 **Event**: {event_type}")

    embed = {
        "title": company_name,
        "color": color,
        "description": "\n\n".join(desc_lines),
        "fields": [],
        "footer": {"text": f"{category}  •  {broadcast_dt}"},
    }

    url_to_use = ixbrl_url or xbrl_url
    if url_to_use:
        embed["url"] = url_to_use

    # Symbol Field
    embed["fields"].append(
        {"name": "Symbol", "value": f"`{symbol}`", "inline": True}
    )

    # Price Field
    price_val = _format_price_field(current_price, p_change, prev_close, is_historical)
    embed["fields"].append(
        {"name": "Price", "value": price_val, "inline": True}
    )

    # Market Cap Field
    if mkt_cap is not None:
        mkt_str = f"₹{mkt_cap:,.2f} Cr"
        embed["fields"].append(
            {"name": "Market Cap", "value": mkt_str, "inline": True}
        )

    # 52W Range Field
    if week_52_low is not None or week_52_high is not None:
        range_parts = [f"{_fmt_price(week_52_low)} — {_fmt_price(week_52_high)}"]
        if current_price is not None:
            bar_result = _range_bar(week_52_low, week_52_high, current_price)
            if bar_result:
                bar, pct = bar_result
                range_parts.append(f"`{bar}` {pct:.0f}%")
        embed["fields"].append(
            {"name": "52W Range", "value": "\n".join(range_parts), "inline": True}
        )

    # Conditionally append parsed XBRL summary if present (from feature flag = True)
    if xbrl_data:
        xbrl_summary = build_fields_summary(xbrl_data)
        if xbrl_summary and xbrl_summary != "*No structured XBRL data parsed.*":
            embed["fields"].append(
                {"name": "XBRL Details", "value": xbrl_summary, "inline": False}
            )

    return embed


def send_embeds(webhook_url: str, embeds: List[Dict[str, Any]]) -> None:
    """Send embeds to Discord Webhook, respecting limits and chunking."""
    chunk: List[Dict[str, Any]] = []
    chunk_chars = 0

    for embed in embeds:
        ec = _embed_char_count(embed)
        if chunk and (
            len(chunk) >= MAX_EMBEDS_PER_MESSAGE or chunk_chars + ec > MAX_TOTAL_CHARS
        ):
            _post_embeds(webhook_url, chunk)
            chunk = []
            chunk_chars = 0
        chunk.append(embed)
        chunk_chars += ec

    if chunk:
        _post_embeds(webhook_url, chunk)


def _post_embeds(webhook_url: str, embeds: List[Dict[str, Any]]) -> None:
    payload = {"embeds": embeds}
    try:
        resp = requests.post(webhook_url, json=payload, timeout=20)
        if resp.status_code not in (200, 204):
            print(f"Discord error {resp.status_code}: {resp.text}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to post embeds to Discord: {e}", file=sys.stderr)


def process_digest_file(file_path: str) -> List[Dict[str, Any]]:
    """Process digest JSON file and build list of Discord embeds."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("meta", {})
    exchange = meta.get("exchange", "NSE")
    date_str = meta.get("date", "")
    total_ann = meta.get("total_announcements", 0)

    category_data = data.get("data", {})
    if not category_data:
        print("No announcement data found in file.")
        return []

    # Get category counts
    category_counts = {cat: len(filings) for cat, filings in category_data.items()}

    # Header embed
    embeds = [build_header_embed(exchange, date_str, total_ann, category_counts)]

    is_historical = False
    if date_str:
        try:
            digest_date = datetime.strptime(date_str, "%d-%m-%Y").date()
            today_date = datetime.now().date()
            if today_date > digest_date:
                is_historical = True
        except Exception:
            pass

    # Filing embeds
    for category in sorted(category_data.keys()):
        for filing in category_data[category]:
            embeds.append(build_filing_embed(filing, category, is_historical))

    return embeds


def main() -> None:
    """Main execution point for webhook sender."""
    parser = argparse.ArgumentParser(
        description="Send IndiaInc Today digest JSON to Discord as rich embeds."
    )
    parser.add_argument("file_path", help="Path to the digested JSON output file.")
    parser.add_argument(
        "--exchange",
        required=True,
        help="Exchange label (e.g. 'NSE Mainboard' or 'NSE SME')",
    )
    args = parser.parse_args()

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print(
            "Error: DISCORD_WEBHOOK_URL environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.exists(args.file_path):
        print(f"Error: File not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        embeds = process_digest_file(args.file_path)
        if embeds:
            send_embeds(webhook_url, embeds)
            print(f"Successfully sent {len(embeds)} embeds to Discord.")
        else:
            print("No embeds generated.")
    except Exception as e:
        print(f"Error processing or sending: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
