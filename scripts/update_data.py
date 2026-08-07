#!/usr/bin/env python3
"""Fetch STRC price + dividend history from Yahoo Finance v8 chart API, merge, bake.

Usage:
    python scripts/update_data.py            # fetch + merge into data/strc_data.json
    python scripts/update_data.py --bake     # also inject into index.html (window.STRC_DATA)

Stdlib only. Idempotent: manual entries in data/strc_data.json (matched by date)
survive refreshes.
"""
import json
import os
import sys
import urllib.request
import datetime

BASE = "https://query1.finance.yahoo.com/v8/finance/chart/STRC?range=1y&interval=1d&events=div"
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "strc_data.json")
INDEX = os.path.join(ROOT, "index.html")
MARKER_START = "/*__DATA_START__*/"
MARKER_END = "/*__DATA_END__*/"


def fetch():
    req = urllib.request.Request(BASE, headers=HDRS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["chart"]["result"][0]


def main():
    res = fetch()
    meta = res["meta"]
    ts, quotes = res["timestamp"], res["indicators"]["quote"][0]
    prices = []
    for i, t in enumerate(ts):
        o, h, l, c, v = (quotes["open"][i], quotes["high"][i],
                         quotes["low"][i], quotes["close"][i], quotes["volume"][i])
        if c is None:
            continue
        prices.append({
            "date": datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"),
            "open": round(o, 2), "high": round(h, 2), "low": round(l, 2),
            "close": round(c, 2), "volume": int(v or 0),
        })
    divs = [{
        "date": datetime.datetime.utcfromtimestamp(d["date"]).strftime("%Y-%m-%d"),
        "amount": round(d["amount"], 4),
    } for d in sorted(res.get("events", {}).get("dividends", {}).values(),
                      key=lambda x: x["date"])]

    old = (json.load(open(DATA, encoding="utf-8"))
           if os.path.exists(DATA) else {"prices": [], "dividends": []})

    def merge(new, old_rows):
        by_date = {x["date"]: x for x in old_rows}
        for x in new:
            by_date.setdefault(x["date"], x)  # manual entries survive
        return sorted(by_date.values(), key=lambda x: x["date"])

    out = {
        "meta": {
            "symbol": meta["symbol"],
            "name": meta.get("shortName", "STRC"),
            "par": 100.0,
            "currency": meta.get("currency", "USD"),
            "as_of": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "yahoo v8 chart API",
            "last_close": round(meta.get("regularMarketPrice") or 0.0, 2),
            "last_close_date": (datetime.datetime.utcfromtimestamp(meta["regularMarketTime"])
                                .strftime("%Y-%m-%d") if meta.get("regularMarketTime") else None),
            "fifty_two_week": {
                "high": round(meta.get("fiftyTwoWeekHigh") or 0.0, 2),
                "low": round(meta.get("fiftyTwoWeekLow") or 0.0, 2),
            },
        },
        "prices": merge(prices, old.get("prices", [])),
        "dividends": merge(divs, old.get("dividends", [])),
    }
    tmp = DATA + ".tmp"
    json.dump(out, open(tmp, "w", encoding="utf-8"), indent=2)
    os.replace(tmp, DATA)
    print(f"OK: {len(out['prices'])} price rows, {len(out['dividends'])} dividends, "
          f"last_close=${out['meta']['last_close']} ({out['meta']['last_close_date']}), "
          f"as_of={out['meta']['as_of']}")

    if "--bake" in sys.argv:
        bake(out)
    return 0


def bake(data):
    if not os.path.exists(INDEX):
        print("WARN: index.html not found — data saved but not baked")
        return
    html = open(INDEX, encoding="utf-8").read()
    block = f"{MARKER_START}\nwindow.STRC_DATA = {json.dumps(data)};\n{MARKER_END}"
    if MARKER_START not in html or MARKER_END not in html:
        print("WARN: bake markers not found in index.html — data saved but not baked")
        return
    start = html.index(MARKER_START)
    end = html.index(MARKER_END) + len(MARKER_END)
    html = html[:start] + block + html[end:]
    # Inline the engine (single-file artifact); idempotent — only when the src tag is present
    src_tag = '<script src="js/engine.js"></script>'
    if src_tag in html:
        engine = open(os.path.join(ROOT, "js", "engine.js"), encoding="utf-8").read()
        html = html.replace(src_tag, f"<script>\n{engine}\n</script>")
    open(INDEX, "w", encoding="utf-8").write(html)
    print(f"Baked {len(json.dumps(data))} bytes of data + engine into index.html")


if __name__ == "__main__":
    sys.exit(main())
