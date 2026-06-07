"""BSE XBRL Subcategory Census — run from FirstFilingsIN dir: uv run python bse_xbrl_census.py"""

from bse import BSE
from collections import defaultdict
import time
import json
import datetime

b = BSE(".")
url = f"{b.api_url}/XbrlAnnouncementCategory/w"

# BSE API chokes on large date ranges. Fetch week-by-week.
# 3 months = ~13 weeks
weeks = []
start = datetime.date(2026, 3, 1)
end = datetime.date(2026, 6, 6)
cur = start

while cur < end:
    week_end = min(cur + datetime.timedelta(days=6), end)
    weeks.append((cur.strftime("%Y%m%d"), week_end.strftime("%Y%m%d")))
    cur = week_end + datetime.timedelta(days=1)

print(f"Will fetch {len(weeks)} weekly chunks from {start} to {end}")

all_items = []
for wi, (from_dt, to_dt) in enumerate(weeks):
    print(f"\n[{wi + 1}/{len(weeks)}] {from_dt} to {to_dt}")
    page = 1
    chunk_total = None

    while True:
        params = {
            "pageno": page,
            "strCat": -1,
            "strPrevDate": from_dt,
            "strScrip": "",
            "strSearch": "P",
            "strToDate": to_dt,
            "strType": "C",
            "subcategory": -1,
        }

        data = None
        for attempt in range(1, 4):
            try:
                data = b._BSE__req(url, params).json()
                break
            except Exception as e:
                print(f"  Page {page} attempt {attempt}/3: {type(e).__name__}")
                if attempt < 3:
                    time.sleep(3 * attempt)

        if data is None:
            print(f"  FAILED page {page}, skipping rest of this week")
            break

        items = data.get("Table", [])
        if not items:
            break

        all_items.extend(items)
        if chunk_total is None:
            chunk_total = data.get("Table1", [{}])[0].get("ROWCNT", 0)
            print(f"  {chunk_total} filings this week")

        if len(all_items) - (len(all_items) - len(items)) >= chunk_total:
            break
        # Check if we got all for this chunk
        chunk_so_far = sum(1 for _ in range(len(items)))  # just len
        if page * 50 >= chunk_total:
            break

        page += 1
        time.sleep(0.35)

    time.sleep(0.5)

print(f"\n{'=' * 60}")
print(f"Fetched {len(all_items)} total items across {len(weeks)} weeks\n")

# ── Analysis ──
subcats = defaultdict(int)
cats = defaultdict(lambda: defaultdict(int))
for item in all_items:
    sc = item.get("SUBCATNAME", "").strip()
    c = item.get("CATEGORYNAME", "").strip()
    subcats[sc] += 1
    cats[c][sc] += 1

print(f"===== UNIQUE SUBCATEGORIES: {len(subcats)} =====\n")
for sc, count in sorted(subcats.items(), key=lambda x: -x[1]):
    print(f"{count:5d}  {sc}")

print("\n===== BY PARENT CATEGORY =====")
for cat in sorted(cats.keys()):
    print(f"\n  [{cat}] ({sum(cats[cat].values())} filings, {len(cats[cat])} subcats)")
    for sc, count in sorted(cats[cat].items(), key=lambda x: -x[1]):
        print(f"    {count:5d}  {sc}")

if all_items:
    print("\n===== SAMPLE ITEM (first) =====")
    print(json.dumps(all_items[0], indent=2, default=str))
else:
    print("\nNo items fetched!")
