"""Print a fingerprint of the site's input data, so the hourly job only rebuilds when something changed.

Covers: the site code (src, public, scripts, build config - so a design push deploys on the next run),
stored complete days (data/daily/_totals.json), this month's egg rates, and today's partial
prices (rows only - not the fetch time, which changes every run). Compared against the live site's
/live.json, which each deploy writes.
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
h = hashlib.sha256()
# site code; generated files are skipped and line endings normalised (Windows checkout vs Linux runner)
code = [ROOT / "astro.config.mjs", ROOT / "package-lock.json"]
for d in ("src", "public", "scripts"):
    code += [f for f in (ROOT / d).rglob("*") if f.is_file()]
skip = ("src/data/", "public/cards/", "public/live.json")
for f in sorted(code, key=lambda f: f.relative_to(ROOT).as_posix()):
    rel = f.relative_to(ROOT).as_posix()
    if rel.startswith(skip) or "__pycache__" in rel:
        continue
    h.update(rel.encode())
    h.update(f.read_bytes().replace(b"\r\n", b"\n"))
totals = ROOT / "data" / "daily" / "_totals.json"
if totals.exists():
    h.update(totals.read_bytes())
eggs = sorted((ROOT / "data" / "eggs").glob("*.json"))
if eggs:
    h.update(eggs[-1].read_bytes())
today = ROOT / "data" / "today.json.gz"
if today.exists():
    t = json.loads(gzip.decompress(today.read_bytes()))
    h.update(t["date"].encode())
    h.update(json.dumps(t["rows"], sort_keys=True, ensure_ascii=False).encode("utf-8"))
digest = h.hexdigest()[:16]

if sys.argv[1:2] == ["--write"]:
    # public/live.json ships with the deploy; the next run compares against it
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    (ROOT / "public" / "live.json").write_text(json.dumps({"digest": digest, "built": now.strftime("%Y-%m-%d %H:%M IST")}), encoding="utf-8")
print(digest)
