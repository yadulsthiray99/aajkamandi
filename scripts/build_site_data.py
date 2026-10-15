"""Turn stored daily mandi snapshots + NECC egg sheets into the JSON the site renders.

Reads:  data/daily/*.json, data/eggs/*.json
Writes: src/data/mandi.json, src/data/eggs.json

Agmarknet prices are Rs per quintal (100 kg). NECC egg prices are Rs per 100 eggs.
"""
import gzip
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAILY, EGGS, OUT = ROOT / "data" / "daily", ROOT / "data" / "eggs", ROOT / "src" / "data"

# Programmatic SEO gate: publish in batches. Raise the limits only after the last batch is indexed
# and showing impressions in Search Console.
# Batch 1 = 50 mandi-town pages + 15 crop pages + egg-rate pages (~35) = ~100 pages.
TOWN_LIMIT, CROP_LIMIT = 50, 15
MIN_TOWN_DAYS = 3        # a town page needs prices on at least this many of the stored days
MIN_TOWN_ROWS = 8        # ...and at least this many price rows on its latest day
HISTORY_DAYS = 30

# Crop pages, in order of measured search demand inside "mandi bhav" keywords (India, Oct 2026).
# Each entry: (page slug, regex matched against the lower-cased Agmarknet commodity name)
CROPS = [
    ("mustard", r"^mustard$"), ("garlic", r"^garlic$"), ("maize", r"^maize$"), ("onion", r"^onion$"),
    ("wheat", r"^wheat$"), ("cumin", r"^cummin seed"), ("paddy", r"^paddy"), ("soyabean", r"^soyabean$"),
    ("guar", r"^guar seed"), ("chana", r"^bengal gram\(gram\)"), ("cotton", r"^cotton$"), ("groundnut", r"^groundnut$"),
    ("bajra", r"^bajra"), ("moong", r"^green gram ?\(moong\)"), ("coriander-seed", r"^corriander seed"),
]

# Hindi names. Matched against the Agmarknet commodity name (longest key wins).
HINDI = {
    "onion": "प्याज", "potato": "आलू", "tomato": "टमाटर", "wheat": "गेहूं", "paddy": "धान", "rice": "चावल",
    "soyabean": "सोयाबीन", "cotton": "कपास", "mustard": "सरसों", "bengal gram": "चना", "kabuli chana": "काबुली चना",
    "maize": "मक्का", "bajra": "बाजरा", "jowar": "ज्वार", "garlic": "लहसुन", "ginger": "अदरक", "green chilli": "हरी मिर्च",
    "dry chillies": "लाल मिर्च", "cauliflower": "फूलगोभी", "cabbage": "पत्ता गोभी", "brinjal": "बैंगन", "banana": "केला",
    "apple": "सेब", "groundnut": "मूंगफली", "arhar": "अरहर (तुअर)", "green gram": "मूंग", "black gram": "उड़द",
    "lentil": "मसूर", "coriander": "धनिया", "corriander": "धनिया", "cummin": "जीरा", "turmeric": "हल्दी", "lemon": "नींबू",
    "bhindi": "भिंडी", "bottle gourd": "लौकी", "bitter gourd": "करेला", "cucumbar": "खीरा", "pumpkin": "कद्दू",
    "carrot": "गाजर", "raddish": "मूली", "peas": "मटर", "spinach": "पालक", "methi": "मेथी", "pomegranate": "अनार",
    "grapes": "अंगूर", "mango": "आम", "orange": "संतरा", "papaya": "पपीता", "guava": "अमरूद", "sugarcane": "गन्ना",
    "castor seed": "अरंडी", "sesamum": "तिल", "barley": "जौ", "copra": "खोपरा", "coconut": "नारियल", "arecanut": "सुपारी",
    "black pepper": "काली मिर्च", "cardamom": "इलायची", "sweet potato": "शकरकंद", "tapioca": "टैपिओका", "colacasia": "अरबी",
    "capsicum": "शिमला मिर्च", "beans": "बीन्स", "cowpea": "लोबिया", "ridgeguard": "तोरई", "little gourd": "कुंदरू",
    "mousambi": "मौसमी", "water melon": "तरबूज", "pineapple": "अनानास", "chikoos": "चीकू", "amaranthus": "चौलाई",
    "drumstick": "सहजन", "elephant yam": "सूरन", "ashgourd": "पेठा", "tinda": "टिंडा", "sponge gourd": "गिल्की",
    "jaggery": "गुड़", "guar": "ग्वार", "ajwan": "अजवाइन", "soanf": "सौंफ", "tamarind": "इमली", "isabgul": "ईसबगोल",
    "moath": "मोठ", "field pea": "मटर", "linseed": "अलसी", "sunflower": "सूरजमुखी", "ragi": "रागी", "safflower": "कुसुम",
    "kulthi": "कुलथी", "pear": "नाशपाती", "lime": "नींबू", "plum": "आलूबुखारा", "litchi": "लीची", "karbuja": "खरबूजा",
    "mint": "पुदीना", "spring onion": "हरा प्याज", "knool khol": "गांठ गोभी", "beetroot": "चुकंदर", "squash": "स्क्वैश",
    "sweet pumpkin": "मीठा कद्दू", "snakeguard": "चिचिंडा", "round gourd": "टिंडा", "pointed gourd": "परवल",
    "chow chow": "चाऊ चाऊ", "ratalu": "रतालू", "amla": "आंवला", "sweet corn": "स्वीट कॉर्न", "baby corn": "बेबी कॉर्न",
    "mushroom": "मशरूम", "turnip": "शलजम", "betal leaves": "पान", "marigold": "गेंदा", "jasmine": "चमेली", "rose": "गुलाब",
    "firewood": "जलाऊ लकड़ी", "wood": "लकड़ी", "tube rose": "रजनीगंधा", "avare": "सेम", "thondekai": "कुंदरू", "poppy": "खसखस (अफीम दाना)", "nigella": "कलौंजी",
    "ashwagandha": "अश्वगंधा", "giloy": "गिलोय", "basil": "तुलसी", "saffron": "केसर", "asparagus": "शतावरी",
    "muesli": "मूसली", "absinthe": "चिरायता", "kalonji": "कलौंजी", "lentil": "मसूर",
}


NON_FOOD = {"wood", "firewood", "rose(local)", "marigold(calcutta)", "jasmine", "tube rose(loose)", "betal leaves"}


def slugify(s):
    s = re.sub(r"\(.*?\)", " ", s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def display_name(commodity):
    # "Paddy(Dhan)(Common)" -> "Paddy (Dhan) (Common)";  "poppy seeds" -> "Poppy seeds"
    s = re.sub(r"\s*\(", " (", commodity).strip()
    return s[:1].upper() + s[1:]


def hindi_for(commodity):
    c = commodity.lower()
    for key in sorted(HINDI, key=len, reverse=True):
        if key in c:
            return HINDI[key]
    return None


def med(xs):
    return round(statistics.median(xs)) if xs else None


TOWN_HI = {
    "betul": "बैतूल", "neemuch": "नीमच", "indore": "इंदौर", "mandsaur": "मंदसौर", "kota": "कोटा", "dhamnod": "धामनोद",
    "chhindwara": "छिंदवाड़ा", "khargone": "खरगोन", "harda": "हरदा", "khandwa": "खंडवा", "morena": "मुरैना", "jaora": "जावरा",
    "unjha": "ऊंझा", "ashta": "आष्टा", "sikar": "सीकर", "sagar": "सागर", "timarni": "टिमरनी", "jaipur": "जयपुर",
    "surajgarh": "सूरजगढ़", "baran": "बारां", "auraiya": "औरैया", "damoh": "दमोह", "guna": "गुना", "dabra": "डबरा",
    "sehore": "सीहोर", "adampur": "आदमपुर", "nimbahera": "निम्बाहेड़ा", "vidisha": "विदिशा", "shajapur": "शाजापुर",
    "ashoknagar": "अशोकनगर", "katni": "कटनी", "bhind": "भिंड", "jabalpur": "जबलपुर", "kanpur": "कानपुर",
    "bhikangaon": "भीकनगांव", "lalitpur": "ललितपुर", "bundi": "बूंदी", "khirkiya": "खिरकिया", "shujalpur": "शुजालपुर",
    "pipariya": "पिपरिया", "banapura": "बानापुरा", "itarsi": "इटारसी", "khategaon": "खातेगांव", "mahoba": "महोबा",
    "gohad": "गोहद", "etawah": "इटावा", "kareli": "करेली", "satna": "सतना", "ratlam": "रतलाम", "merta city": "मेड़ता सिटी",
    "nagaur": "नागौर", "bharatpur": "भरतपुर", "alwar": "अलवर", "nohar": "नोहर", "sheopur": "श्योपुर",
    "ganj basoda": "गंज बासौदा", "khairthal": "खैरथल", "jodhpur": "जोधपुर", "bikaner": "बीकानेर", "nokha": "नोखा",
    "siwani": "सिवानी", "bhopal": "भोपाल", "ujjain": "उज्जैन", "dewas": "देवास", "hoshangabad": "होशंगाबाद",
    "gwalior": "ग्वालियर", "bina": "बीना", "jhansi": "झांसी", "rewa": "रीवा", "shivpuri": "शिवपुरी", "rajgarh": "राजगढ़", "badnawar": "बदनावर",
    "sanawad": "सनावद", "piparia": "पिपरिया", "agar": "आगर", "susner": "सुसनेर", "jhalawar": "झालावाड़",
    "ramganj mandi": "रामगंज मंडी", "chittorgarh": "चित्तौड़गढ़", "sri ganganagar": "श्रीगंगानगर", "hanumangarh": "हनुमानगढ़",
}
STATE_HI = {
    "Madhya Pradesh": "मध्य प्रदेश", "Rajasthan": "राजस्थान", "Uttar Pradesh": "उत्तर प्रदेश", "Gujarat": "गुजरात",
    "Punjab": "पंजाब", "Haryana": "हरियाणा", "Maharashtra": "महाराष्ट्र", "Bihar": "बिहार", "Chhattisgarh": "छत्तीसगढ़",
    "Uttarakhand": "उत्तराखंड", "Himachal Pradesh": "हिमाचल प्रदेश", "NCT of Delhi": "दिल्ली", "Karnataka": "कर्नाटक",
    "Telangana": "तेलंगाना", "Andhra Pradesh": "आंध्र प्रदेश", "Tamil Nadu": "तमिलनाडु", "West Bengal": "पश्चिम बंगाल",
    "Odisha": "ओडिशा", "Jharkhand": "झारखंड", "Keralam": "केरल", "Kerala": "केरल",
}


PRIORITY = ["soyabean", "wheat", "garlic", "mustard", "maize", "onion", "bengal gram", "paddy", "cotton", "guar",
            "cummin", "groundnut", "bajra", "green gram", "black gram", "arhar", "methi seeds", "corriander seed",
            "potato", "tomato"]


def priority(commodity):
    c = commodity.lower()
    for i, key in enumerate(PRIORITY):
        if c.startswith(key):
            return i
    return len(PRIORITY)


def town_of(market):
    """'Betul(F&V) APMC' -> 'Betul';  'Merta City APMC' -> 'Merta City'."""
    m = re.sub(r"\(.*?\)", " ", market)
    m = re.sub(r"\b(APMC|Mandi|Market|Grain)\b|Sub[- ]?yard.*$", " ", m, flags=re.I)
    return " ".join(m.split()).strip(" -,") or market


def load_town_demand():
    p = ROOT / "data" / "town_demand.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def build_mandi():
    days = {}
    for f in sorted(DAILY.glob("*.json*")):
        day = f.name.split(".")[0]
        raw = gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes()
        days[day] = json.loads(raw.decode("utf-8"))
    if not days:
        raise SystemExit("No daily snapshots yet - run scripts/fetch_mandi.py first.")
    dates = sorted(days)
    latest = dates[-1]
    demand = load_town_demand()

    # --- per town: (state, district, town); a town can have several yards (grain, F&V) ---
    towns = defaultdict(lambda: {"by_day": defaultdict(list), "yards": set()})
    for d in dates:
        for r in days[d]:
            key = (r["state"], r["district"], town_of(r["market"]))
            towns[key]["by_day"][d].append(r)
            towns[key]["yards"].add(r["market"])

    town_items = []
    for (state, district, town), t in towns.items():
        # identical duplicate rows exist in the source; drop them
        for d in list(t["by_day"]):
            seen_rows, uniq = set(), []
            for r in t["by_day"][d]:
                k = (r["market"], r["commodity"], r["variety"], r["grade"], r["min_price"], r["max_price"], r["modal_price"])
                if k not in seen_rows:
                    seen_rows.add(k)
                    uniq.append(r)
            t["by_day"][d] = uniq
        tdates = sorted(t["by_day"])
        last = tdates[-1]
        hist = defaultdict(dict)   # commodity -> {date: median modal}   (trend charts)
        vhist = defaultdict(dict)  # (yard, commodity, variety) -> {date: median modal}   (change column)
        for d in tdates:
            g, gv = defaultdict(list), defaultdict(list)
            for r in t["by_day"][d]:
                g[r["commodity"]].append(r["modal_price"])
                gv[(r["market"], r["commodity"], r["variety"])].append(r["modal_price"])
            for c, xs in g.items():
                hist[c][d] = med(xs)
            for k, xs in gv.items():
                vhist[k][d] = med(xs)
        rows = []
        for r in sorted(t["by_day"][last], key=lambda r: (priority(r["commodity"]), r["commodity"], r["variety"] or "")):
            h = vhist[(r["market"], r["commodity"], r["variety"])]
            prev_dates = [d for d in sorted(h) if d < last]
            prev = prev_dates[-1] if prev_dates else None
            rows.append({"commodity": r["commodity"], "label": display_name(r["commodity"]),
                         "hindi": hindi_for(r["commodity"]), "yard": r["market"], "variety": r["variety"],
                         "grade": r["grade"], "min": r["min_price"], "max": r["max_price"], "modal": r["modal_price"],
                         "prev_date": prev, "prev_modal": h.get(prev) if prev else None})
        hist_out = {display_name(c): [{"date": d, "modal": v} for d, v in sorted(h.items())][-HISTORY_DAYS:]
                    for c, h in sorted(hist.items(), key=lambda kv: (priority(kv[0]), kv[0])) if len(h) >= 2}
        tl = town.lower()
        dem = demand.get(tl) or demand.get(tl.split()[0], 0) if tl else 0
        town_items.append({"town": town, "town_hi": TOWN_HI.get(tl), "state_hi": STATE_HI.get(state),
                           "slug": slugify(town), "state": state, "state_slug": slugify(state),
                           "district": district, "yards": sorted(t["yards"]), "date": last,
                           "days_reporting": len(tdates), "demand": dem, "rows": rows, "history": hist_out})

    # Publish towns with measured search demand first, only if they report regularly
    eligible = [x for x in town_items if x["days_reporting"] >= min(MIN_TOWN_DAYS, len(dates))
                and len(x["rows"]) >= MIN_TOWN_ROWS]
    ranked = sorted(eligible, key=lambda x: (-x["demand"], -len(x["rows"])))
    pub = set()
    for x in ranked:
        if len(pub) >= TOWN_LIMIT:
            break
        key = (x["state_slug"], x["slug"])
        if key in pub:
            continue  # same town name twice in one state (different districts): keep the first-ranked
        pub.add(key)
        x["published"] = True
    for x in town_items:
        x.setdefault("published", False)

    # --- per crop (national, latest complete day) ---
    crop_items = []
    for slug, pattern in CROPS[:CROP_LIMIT]:
        hist_nat, latest_rows = {}, []
        for d in dates:
            xs = [r for r in days[d] if re.search(pattern, r["commodity"].lower())]
            if xs:
                hist_nat[d] = med([r["modal_price"] for r in xs])
                if d == latest:
                    latest_rows = xs
        if not latest_rows:
            continue
        names = defaultdict(int)
        for r in latest_rows:
            names[r["commodity"]] += 1
        main = max(names, key=names.get)
        by_state = defaultdict(list)
        for r in latest_rows:
            by_state[r["state"]].append(r)
        ordered = sorted(latest_rows, key=lambda r: r["modal_price"])
        towns_trading = sorted({(x["town"], x["state_slug"], x["slug"]) for x in town_items if x["published"]
                                and any(re.search(pattern, rr["commodity"].lower()) for rr in x["rows"])})
        crop_items.append({
            "slug": slug, "name": main, "label": display_name(main), "hindi": hindi_for(main), "date": latest,
            "markets": len({r["market"] for r in latest_rows}), "states": len(by_state),
            "modal_median": med([r["modal_price"] for r in latest_rows]),
            "min": min(r["min_price"] for r in latest_rows if r["min_price"]),
            "max": max(r["max_price"] for r in latest_rows if r["max_price"]),
            "cheapest": {k: ordered[0][k] for k in ("market", "district", "state", "modal_price")},
            "dearest": {k: ordered[-1][k] for k in ("market", "district", "state", "modal_price")},
            "by_state": sorted(({"state": s, "markets": len({x["market"] for x in v}),
                                 "modal_median": med([x["modal_price"] for x in v]),
                                 "min": min(x["min_price"] for x in v if x["min_price"]),
                                 "max": max(x["max_price"] for x in v if x["max_price"])}
                                for s, v in by_state.items()), key=lambda s: -s["markets"]),
            "rows": [{k: r[k] for k in ("state", "district", "market", "variety", "min_price", "max_price", "modal_price")}
                     for r in sorted(latest_rows, key=lambda r: (r["state"], r["district"], r["market"]))],
            "towns": [{"town": a, "state_slug": b, "slug": c} for a, b, c in towns_trading],
            "history": [{"date": d, "modal": v} for d, v in sorted(hist_nat.items())][-HISTORY_DAYS:],
        })

    states = sorted({x["state"] for x in town_items})
    return {"latest": latest, "days_stored": len(dates), "total_reports": len(days[latest]),
            "towns": sorted(town_items, key=lambda x: (-x["demand"], x["town"])),
            "crops": crop_items, "states": [{"name": s, "slug": slugify(s)} for s in states]}


def build_eggs():
    files = sorted(EGGS.glob("*.json"))
    if not files:
        return {"zones": [], "latest": None}
    series = defaultdict(dict)
    for f in files:
        ym = f.stem
        for zone, days in json.loads(f.read_text(encoding="utf-8")).items():
            for day, price in days.items():
                series[zone][f"{ym}-{int(day):02d}"] = price
    zones = []
    for zone, s in series.items():
        dates = sorted(s)
        last = dates[-1]
        prev = dates[-2] if len(dates) > 1 else None
        year_ago = [d for d in dates if d <= f"{int(last[:4]) - 1}{last[4:]}"]
        last365 = [d for d in dates if d > f"{int(last[:4]) - 1}{last[4:]}"]
        hi = max(last365, key=lambda d: s[d])
        lo = min(last365, key=lambda d: s[d])
        months = defaultdict(list)
        for d in dates:
            months[d[:7]].append(s[d])
        zones.append({"zone": zone, "slug": slugify(zone), "date": last, "per100": s[last],
                      "change": round(s[last] - s[prev], 2) if prev else None,
                      "year_ago": {"date": year_ago[-1], "per100": s[year_ago[-1]]} if year_ago else None,
                      "high": {"date": hi, "per100": s[hi]}, "low": {"date": lo, "per100": s[lo]},
                      "monthly": [{"month": m, "avg": round(sum(v) / len(v), 1), "days": len(v)}
                                  for m, v in sorted(months.items())][-13:],
                      "history": [{"date": d, "per100": s[d]} for d in dates][-14:],
                      "chart": [{"date": d, "modal": s[d]} for d in last365]})
    # Zones with an identical price series (NECC quotes one rate for both) share one page
    merged, seen = [], {}
    for z in sorted(zones, key=lambda z: z["zone"]):
        key = tuple((c["date"], c["modal"]) for c in z["chart"])
        if key in seen:
            seen[key]["also"].append(z["zone"])
            continue
        z["also"] = []
        seen[key] = z
        merged.append(z)
    zones = merged
    latest = max(z["date"] for z in zones)
    return {"latest": latest, "zones": sorted(zones, key=lambda z: z["zone"])}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = build_mandi()
    # Only published towns carry full detail into the site bundle
    m = dict(m, towns_total=len(m["towns"]), towns=[x for x in m["towns"] if x["published"]])
    (OUT / "mandi.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    e = build_eggs()
    (OUT / "eggs.json").write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
    pub_towns = [x for x in m["towns"] if x["published"]]
    print(f"mandi: {m['days_stored']} days stored, latest {m['latest']} ({m['total_reports']} reports) | "
          f"{m['towns_total']} towns, publish {len(pub_towns)} town pages + {len(m['crops'])} crop pages | eggs: {len(e['zones'])} zones")
    print("top published towns:", [(x["town"], x["state"], x["demand"], len(x["rows"])) for x in pub_towns[:12]])


if __name__ == "__main__":
    main()
