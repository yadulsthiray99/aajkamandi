"""Fetch TODAY's mandi prices from data.gov.in's "Current Daily Price" feed (fills up during the day).

The variety-wise dataset we store (fetch_mandi.py) is only complete the next morning; this feed lets
town pages show "aaj ke bhav - ab tak" as prices arrive. It is a partial, changing view, so it is NOT
committed to git: every hourly run fetches it fresh.

Usage:  python scripts/fetch_today.py
Env:    DATA_GOV_API_KEY (required), FETCH_RELAY (optional, as in fetch_mandi.py)
Writes: data/today.json.gz  {"date": "YYYY-MM-DD", "fetched_at": "HH:MM" (IST), "rows": [...]}
"""
import gzip
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_mandi as fm  # reuses get() (relay, User-Agent, retries) and India-time helpers

RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
OUT = fm.ROOT / "data" / "today.json.gz"


def main():
    key = os.environ.get("DATA_GOV_API_KEY")
    if not key:
        raise SystemExit("Set DATA_GOV_API_KEY (your own data.gov.in key).")
    fm.RESOURCE = RESOURCE  # get() builds its URL from this module-level name
    today = fm.today_ist()
    ddmmyyyy = today.strftime("%d/%m/%Y")
    first = fm.get({"limit": fm.PAGE, "offset": 0}, key)
    total = int(first.get("total", 0))
    records = list(first.get("records", []))
    offset = fm.PAGE
    while offset < total:
        time.sleep(fm.PAUSE)
        batch = fm.get({"limit": fm.PAGE, "offset": offset}, key).get("records", [])
        if not batch:
            break
        records.extend(batch)
        offset += fm.PAGE
    rows = []
    for r in records:
        if r.get("arrival_date") != ddmmyyyy:
            continue  # the feed can still hold yesterday's rows just after midnight
        row = {k: r.get(k) for k in ("state", "district", "market", "commodity", "variety", "grade")}
        for p in ("min_price", "max_price", "modal_price"):
            try:
                row[p] = float(r.get(p))
            except (TypeError, ValueError):
                row[p] = None
        if row["modal_price"]:
            rows.append(row)
    now = datetime.now(fm.IST)
    OUT.write_bytes(gzip.compress(json.dumps(
        {"date": today.isoformat(), "fetched_at": now.strftime("%H:%M"), "rows": rows},
        ensure_ascii=False, separators=(",", ":")).encode("utf-8"), mtime=0))
    print(f"today {today.isoformat()} {now:%H:%M} IST: {len(rows)} rows (feed total {total})")


if __name__ == "__main__":
    main()
