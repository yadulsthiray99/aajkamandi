"""Fetch complete daily mandi prices from data.gov.in and store one snapshot per day.

Source: "Variety-wise Daily Market Prices Data of Commodity" (Agmarknet, Ministry of Agriculture),
        updated nightly, full history back to 2009. A day is complete the morning after.
        (The "Current Daily Price" feed only holds a partial, still-filling view of today, with
        very little Madhya Pradesh / Rajasthan data, so we don't use it.)

Usage:  python scripts/fetch_mandi.py --check         # 1 request: has yesterday's data arrived or grown?
        python scripts/fetch_mandi.py                 # yesterday (run every morning)
        python scripts/fetch_mandi.py 2026-10-13      # one date
        python scripts/fetch_mandi.py --backfill 90   # the last 90 days (skips dates already stored)
Env:    DATA_GOV_API_KEY  (required - your own free key from data.gov.in)
        FETCH_RELAY       (optional - base URL of the relay Worker in relay/; used in GitHub Actions,
                           because data.gov.in refuses connections from GitHub's US runners)

Writes: data/daily/YYYY-MM-DD.json.gz  (compact gzip JSON; Agmarknet prices are Rs per quintal)
        data/daily/_totals.json        (rows data.gov.in reported per date, so later runs can tell
                                        when a day that was published in part has grown)
All dates are India time: GitHub's runners are on UTC, which is still "yesterday" before 05:30 IST.
"""
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "data" / "daily"
PAGE = 1000
PAUSE = 1.5  # seconds between requests; data.gov.in returns 429 if hit faster
TOTALS = DAILY / "_totals.json"
IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    return datetime.now(IST).date()


def load_totals() -> dict:
    try:
        return json.loads(TOTALS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_total(d: date, total: int):
    totals = load_totals()
    totals[d.isoformat()] = total
    DAILY.mkdir(parents=True, exist_ok=True)
    TOTALS.write_text(json.dumps(dict(sorted(totals.items())), indent=0), encoding="utf-8")
def _prefer_ipv4():
    """Connect over IPv4 first: on networks without working IPv6 (common on home ISPs), Python would
    otherwise wait ~21 s per Cloudflare IPv6 address before falling back."""
    import socket
    real = socket.getaddrinfo
    def v4_first(*a, **k):
        res = real(*a, **k)
        return sorted(res, key=lambda r: r[0] != socket.AF_INET)
    socket.getaddrinfo = v4_first


if os.environ.get("FETCH_RELAY"):
    _prefer_ipv4()


FIELDS = {"State": "state", "District": "district", "Market": "market", "Commodity": "commodity",
          "Variety": "variety", "Grade": "grade", "Min_Price": "min_price", "Max_Price": "max_price",
          "Modal_Price": "modal_price"}


def get(params, key, retries=6):
    params = {"api-key": key, "format": "json", **params}
    relay = os.environ.get("FETCH_RELAY", "").rstrip("/")
    base = f"{relay}/dgov/{RESOURCE}" if relay else f"https://api.data.gov.in/resource/{RESOURCE}"
    url = f"{base}?" + urllib.parse.urlencode(params)
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
    if rows:
        save_total(d, total)
    print(f"{d.isoformat()}: {len(rows)} rows (api total {total})")
    return len(rows)


def api_total(d: date, key: str) -> int:
    return int(get({"limit": 1, "offset": 0, "filters[Arrival_Date]": d.strftime("%d/%m/%Y")}, key).get("total", 0))


def stale(d: date, key: str) -> bool:
    """True when data.gov.in has more rows for d than we stored (new day, or a day that grew)."""
    return api_total(d, key) > load_totals().get(d.isoformat(), 0)


def main():
    key = os.environ.get("DATA_GOV_API_KEY")
    if not key:
        raise SystemExit("Set DATA_GOV_API_KEY (your own data.gov.in key).")
    args = sys.argv[1:]
    yesterday = today_ist() - timedelta(days=1)
    if args[:1] == ["--check"]:
        new = stale(yesterday, key)
        print(f"{yesterday.isoformat()}: {'NEW data' if new else 'nothing new'}")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"new={'true' if new else 'false'}\n")
        return
    if args[:1] == ["--backfill"]:
        days = int(args[1]) if len(args) > 1 else 30
        for i in range(1, days + 1):
            d = today_ist() - timedelta(days=i)
            stored = (DAILY / f"{d.isoformat()}.json.gz").exists() or (DAILY / f"{d.isoformat()}.json").exists()
            # always re-check the last 2 days: data.gov.in can add late rows after first publishing a day
            if stored and (i > 2 or not stale(d, key)):
                continue
            fetch_day(d, key)
            time.sleep(PAUSE)
    else:
        d = date.fromisoformat(args[0]) if args else yesterday
        fetch_day(d, key)


if __name__ == "__main__":
    main()
