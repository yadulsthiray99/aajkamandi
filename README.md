# aajkamandi.com

Daily mandi prices (Agmarknet) + NECC egg rates, Hindi/English. Static Astro site, rebuilt every morning.

## Data
- `scripts/fetch_mandi.py` — Agmarknet "Variety-wise Daily Market Prices" (data.gov.in). Needs `DATA_GOV_API_KEY`.
  Complete days only (fetches yesterday). `--backfill N` fills the last N days. Stored as `data/daily/YYYY-MM-DD.json.gz`.
  Do not use the "Current Daily Price" feed: it is a partial, still-filling view of today with almost no MP/Rajasthan data.
- `scripts/fetch_eggs.py [YYYY MM]` — NECC daily egg rate sheet → `data/eggs/YYYY-MM.json`.
- `data/town_demand.json` / `data/mandi_bhav_keywords_in.csv` — India search demand for "[town] mandi bhav" (DataForSEO, 2026-10-15).
  Batch 1 publishes the 50 towns with the most demand (Betul, Neemuch, Indore, Mandsaur, Kota, …).
- `scripts/build_site_data.py` — builds `src/data/mandi.json` + `eggs.json`. Batch limits at the top (`TOWN_LIMIT`, `CROP_LIMIT`).

## Build + quality gate
```
npm run build:gated
```
Builds, runs `scripts/quality_check.py`, writes any page over 60% boilerplate to `src/data/holdback.json`,
rebuilds without them and re-checks. Held-back pages and links to them are skipped automatically.

## Daily automation
`.github/workflows/daily.yml` (07:00 IST): fetch → gated build → deploy to Cloudflare Pages → commit new data.
GitHub repo secrets needed: `DATA_GOV_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.

## Notes
- Prices are ₹/quintal; "change" compares the same yard + crop + variety with its previous report.
- NECC requires its clarification to be shown with egg prices (it is on every egg page).
- Hindi names: `HINDI`, `TOWN_HI`, `STATE_HI` in `build_site_data.py`. Add names before publishing new towns.
