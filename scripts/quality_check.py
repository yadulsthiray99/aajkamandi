"""Pre-deploy quality gate for programmatic pages (run after `astro build`).

Checks, for every page under dist/<section>/:
  * strict unique %   = share of the page's 3-word shingles found on no other page in the section
                        (header/footer/nav excluded; template text included). Warn below 40%.
                        Pages that cross-reference each other (A lists B and B lists A) lose points here
                        even though that text is page-specific, so this is reported, not gated.
  * boilerplate %     = share of shingles repeated on >= BOILER_MIN_PAGES pages (true template text).
                        Hard stop above 60% (the /seo-programmatic "mad-libs" rule); warn above 50%.
  * word count        (warn below 300)
  * broken internal links across the whole dist/ (hard stop)

Usage: python scripts/quality_check.py [--holdback FILE] [section ...]
       --holdback FILE  write the paths of hard-stop pages to FILE (JSON list) so the next build skips them
Exit code 1 if any hard-stop rule fails.
"""
import html
import re
import sys
from collections import Counter
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist"
WARN_UNIQUE, MIN_WORDS = 40.0, 300
STOP_BOILER, WARN_BOILER, BOILER_MIN_PAGES = 60.0, 50.0, 5


def main_text(page: str) -> str:
    m = re.search(r"<main[^>]*>(.*?)</main>", page, flags=re.S | re.I)
    body = m.group(1) if m else page
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", " ", body, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def shingles(text: str, n=3):
    w = re.findall(r"[\w.%/\"″-]+", text.lower())
    return [" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))], len(w)


def check_links():
    pages = {p.relative_to(DIST).as_posix() for p in DIST.rglob("*.html")}
    broken = []
    for p in DIST.rglob("*.html"):
        for href in re.findall(r'href="(/[^"#?]*)"', p.read_text(encoding="utf-8")):
            if href.endswith((".xml", ".svg", ".txt", ".ico", ".png", ".css", ".js")):
                if not (DIST / href.lstrip("/")).exists():
                    broken.append((p, href))
                continue
            target = href.lstrip("/") + ("index.html" if href.endswith("/") else "/index.html")
            if target not in pages:
                broken.append((p.relative_to(DIST).as_posix(), href))
    return broken


def main():
    args = sys.argv[1:]
    holdback_file = None
    if args[:1] == ["--holdback"]:
        holdback_file, args = Path(args[1]), args[2:]
    sections = args or ["tire-size"]
    fail = False
    held = []
    for section in sections:
        # every page below the section (nested folders too), excluding the section index itself
        files = sorted(f for f in (DIST / section).rglob("index.html") if f.parent != DIST / section)
        if not files:
            print(f"[{section}] no pages found")
            continue
        data = {f.parent.relative_to(DIST).as_posix(): shingles(main_text(f.read_text(encoding="utf-8"))) for f in files}
        doc_freq = Counter()
        for sh, _ in data.values():
            doc_freq.update(set(sh))
        rows = []
        for name, (sh, words) in data.items():
            n = max(1, len(sh))
            uniq = sum(1 for s in sh if doc_freq[s] == 1) / n * 100
            boiler = sum(1 for s in sh if doc_freq[s] >= BOILER_MIN_PAGES) / n * 100
            rows.append((boiler, uniq, words, name))
        rows.sort(reverse=True)
        stops = [r for r in rows if r[0] > STOP_BOILER]
        warns = [r for r in rows if WARN_BOILER < r[0] <= STOP_BOILER]
        low_unique = [r for r in rows if r[1] < WARN_UNIQUE]
        thin = [r for r in rows if r[2] < MIN_WORDS]
        k = max(1, len(rows))
        print(f"[{section}] {len(rows)} pages | boilerplate avg {sum(r[0] for r in rows)/k:.1f}% max {rows[0][0]:.1f}% ({rows[0][3]})"
              f" | strict-unique avg {sum(r[1] for r in rows)/k:.1f}% min {min(r[1] for r in rows):.1f}%")
        print(f"   hard-stop boilerplate >{STOP_BOILER:.0f}%: {len(stops)} | warn >{WARN_BOILER:.0f}%: {len(warns)}"
              f" | strict-unique <{WARN_UNIQUE:.0f}%: {len(low_unique)} | <{MIN_WORDS} words: {len(thin)}")
        for r in (stops + warns)[:10]:
            print(f"   {r[3]}: boilerplate {r[0]:.1f}%, strict-unique {r[1]:.1f}%, {r[2]} words")
        fail |= bool(stops)
        held += [r[3] for r in stops]
    broken = check_links()
    print(f"broken internal links: {len(broken)}")
    for b in broken[:10]:
        print("   ", b)
    fail |= bool(broken)
    if holdback_file is not None:
        holdback_file.write_text(__import__("json").dumps(sorted(held), indent=1), encoding="utf-8")
        print(f"held back {len(held)} page(s) -> {holdback_file}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
