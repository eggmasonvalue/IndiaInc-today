"""Fetch multiple Reg30 samples across different event types.
Run from KnowledgeLM dir: uv run python reg30_samples.py
"""
from nse import NSE
import json, time
import xml.etree.ElementTree as ET

n = NSE(".", server=True)
base = n.base_url + "/XBRL-announcements"

params = {"index": "equities", "type": "Reg30", "from_date": "20-05-2026", "to_date": "06-06-2026"}
resp = n._req(base, params=params)
data = resp.json()

print(f"Total Reg30 filings: {len(data)}\n")

# Group by eventType
from collections import defaultdict
by_event = defaultdict(list)
for d in data:
    et = d.get("eventType", "unknown")
    by_event[et].append(d)

print("Event types found:")
for et, items in sorted(by_event.items(), key=lambda x: -len(x[1])):
    print(f"  {len(items):3d}  {et}")

# Pick one Original from each event type
seen = set()
samples = []
for et, items in by_event.items():
    if et in seen:
        continue
    seen.add(et)
    pick = None
    for item in items:
        if item.get("typeOfAnn") == "Original":
            pick = item
            break
    if not pick:
        pick = items[0]
    samples.append((et, pick))

print(f"\nFetching XML for {len(samples)} unique event types...\n")

for et, filing in samples:
    print(f"\n{'='*70}")
    print(f"EVENT: {et}")
    print(f"{'='*70}")
    print(f"  Company: {filing.get('companyName')} ({filing.get('symbol')})")
    print(f"  AppId: {filing.get('appId')}")
    print(f"  Type: {filing.get('typeOfAnn')}")

    xbrl_url = filing.get("xbrl") or filing.get("attachment")
    if not xbrl_url:
        print("  No XBRL URL")
        continue

    time.sleep(0.4)
    try:
        xml_resp = n._req(xbrl_url)
        raw = xml_resp.content.decode("utf-8", errors="replace")
        root = ET.fromstring(raw)
        fields = {}
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            text = (elem.text or "").strip()
            if text:
                if tag not in fields:
                    fields[tag] = text[:300]
        print(f"  Fields ({len(fields)}):")
        for tag, val in fields.items():
            print(f"    {tag}: {val}")
    except Exception as e:
        print(f"  XML error: {e}")
