"""Fetch NECC suggested egg prices (daily rate sheet, current month) and store them.

Usage:  python scripts/fetch_eggs.py [YYYY MM]
Writes: data/eggs/YYYY-MM.json  ->  {zone: {day: price_per_100_eggs}}

NECC requires anyone disseminating its suggested prices to also show its clarification
(see NECC_NOTE in the site footer for egg pages).
"""
import calendar
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "eggs"
URL = "https://www.e2necc.com/home/eggprice"


def fetch(year, month):
    # The page shows the current month by default; the form posts month/year for older sheets.
    data = urllib.parse.urlencode({"ddlMonth": f"{month:02d}", "ddlYear": str(year), "rblReportType": "DailyReport"}).encode()
    req = urllib.request.Request(URL, data=data, headers={"User-Agent": "Mozilla/5.0 (aajkamandi data fetcher)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="ignore")


def parse(page, year, month):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S | re.I)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.S | re.I)
    out = {}
    for row in rows:
        cells = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)]
        if len(cells) < 30 or not cells[0] or cells[0].lower().startswith(("name of zone", "necc")):
            continue
        zone = cells[0]
        # only real calendar days; in shorter months the "Average" column follows the last day
        days = cells[1:1 + calendar.monthrange(year, month)[1]]
        prices = {}
        for i, v in enumerate(days, start=1):
            if re.fullmatch(r"\d+(\.\d+)?", v):
                prices[str(i)] = float(v)
        if prices:
            out[zone] = prices
    return out


def main():
    today = date.today()
    year, month = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (today.year, today.month)
    zones = parse(fetch(year, month), year, month)
    if not zones:
        raise SystemExit("No egg price rows parsed - NECC page layout may have changed.")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{year}-{month:02d}.json"
    path.write_text(json.dumps(zones, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path.name}: {len(zones)} zones")


if __name__ == "__main__":
    main()
