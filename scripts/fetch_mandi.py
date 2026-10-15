"""Fetch complete daily mandi prices from data.gov.in and store one snapshot per day.

Source: "Variety-wise Daily Market Prices Data of Commodity" (Agmarknet, Ministry of Agriculture),
        updated nightly, full history back to 2009. A day is complete the morning after.
        (The "Current Daily Price" feed only holds a partial, still-filling view of today, with
        very little Madhya Pradesh / Rajasthan data, so we don't use it.)

Usage:  python scripts/fetch_mandi.py                 # yesterday (run every morning)
        python scripts/fetch_mandi.py 2026-10-13      # one date
        python scripts/fetch_mandi.py --backfill 90   # the last 90 days (skips dates already stored)
Env:    DATA_GOV_API_KEY  (required - your own free key from data.gov.in)

Writes: data/daily/YYYY-MM-DD.json.gz  (compact gzip JSON; Agmarknet prices are Rs per quintal)
"""
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "data" / "daily"
PAGE = 1000
PAUSE = 1.5  # seconds between requests; data.gov.in returns 429 if hit faster
FIELDS = {"State": "state", "District": "district", "Market": "market", "Commodity": "commodity",
          "Variety": "variety", "Grade": "grade", "Min_Price": "min_price", "Max_Price": "max_price",
          "Modal_Price": "modal_price"}


def get(params, key, retries=6):
    params = {"api-key": key, "format": "json", **params}
    url = f"https://api.data.gov.in/resource/{RESOURCE}?" + urllib.parse.urlencode(params)
    # data.gov.in stalls requests carrying Python's default User-Agent, so always send our own.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; aajkamandi-fetcher/1.0)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            wait = 2 ** attempt * (15 if "429" in str(e) else 3)
            print(f"  retry {attempt + 1} after error: {e} (sleep {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("data.gov.in request failed repeatedly")


def fetch_day(d: date, key: str):
    path = DAILY / f"{d.isoformat()}.json.gz"
    ddmmyyyy = d.strftime("%d/%m/%Y")
    first = get({"limit": PAGE, "offset": 0, "filters[Arrival_Date]": ddmmyyyy}, key)
    total = int(first.get("total", 0))
    records = list(first.get("records", []))
    offset = PAGE
    while offset < total:
        time.sleep(PAUSE)
        batch = get({"limit": PAGE, "offset": offset, "filters[Arrival_Date]": ddmmyyyy}, key).get("records", [])
        if not batch:
            break
        records.extend(batch)
        offset += PAGE
    rows = []
    for r in records:
        row = {v: r.get(k) for k, v in FIELDS.items()}
        for p in ("min_price", "max_price", "modal_price"):
            try:
                row[p] = float(row[p])
            except (TypeError, ValueError):
                row[p] = None
        if row["modal_price"]:
            rows.append(row)
    if rows:
        DAILY.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
    print(f"{d.isoformat()}: {len(rows)} rows (api total {total})")
    return len(rows)


def main():
    key = os.environ.get("DATA_GOV_API_KEY")
    if not key:
        raise SystemExit("Set DATA_GOV_API_KEY (your own data.gov.in key).")
    args = sys.argv[1:]
    if args[:1] == ["--backfill"]:
        days = int(args[1]) if len(args) > 1 else 30
        for i in range(1, days + 1):
            d = date.today() - timedelta(days=i)
            if (DAILY / f"{d.isoformat()}.json.gz").exists() or (DAILY / f"{d.isoformat()}.json").exists():
                continue
            fetch_day(d, key)
            time.sleep(PAUSE)
    else:
        d = date.fromisoformat(args[0]) if args else date.today() - timedelta(days=1)
        fetch_day(d, key)


if __name__ == "__main__":
    main()
