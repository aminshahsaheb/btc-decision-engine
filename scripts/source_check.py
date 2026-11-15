import json
import os
import sys
import time
import urllib.parse
import urllib.request

NOW_MS = int(time.time() * 1000)
HOUR = 3_600_000


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "btc-source-check/0.1"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def binance_spot():
    rows = get("https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=3")
    closed = [x for x in rows if x[6] < NOW_MS]
    return closed[-1][0], float(closed[-1][4])


def okx_swap():
    rows = get("https://www.okx.com/api/v5/market/candles?instId=BTC-USDT-SWAP&bar=1H&limit=3")["data"]
    closed = [x for x in rows if x[8] == "1"]
    return int(closed[0][0]), float(closed[0][4])


def coinbase():
    rows = get("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600")
    closed = [x for x in rows if x[0] * 1000 + HOUR <= NOW_MS]
    newest = max(closed, key=lambda x: x[0])
    return newest[0] * 1000, float(newest[4])


def kraken():
    result = get("https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60")["result"]
    key = [k for k in result if k != "last"][0]
    closed = [x for x in result[key] if x[0] * 1000 + HOUR <= NOW_MS]
    return closed[-1][0] * 1000, float(closed[-1][4])


SOURCES = [("binance_spot_BTCUSDT", binance_spot), ("okx_swap_BTC-USDT", okx_swap),
           ("coinbase_BTC-USD", coinbase), ("kraken_XBTUSD", kraken)]


def stamp(ms):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ms / 1000))


results = []
for name, fetch in SOURCES:
    try:
        opened, close = fetch()
        results.append({"name": name, "open_ms": opened, "close": close,
                        "age_min": (NOW_MS - (opened + HOUR)) / 60000})
    except Exception as exc:
        results.append({"name": name, "error": f"{type(exc).__name__}: {exc}"})

ref = next((r for r in results if r["name"].startswith("binance") and "error" not in r), None)
lines = []
for r in results:
    if "error" in r:
        lines.append(f"{r['name']}: ERROR {r['error']}")
        continue
    note = ""
    if ref is not None and r is not ref:
        if r["open_ms"] == ref["open_ms"]:
            note = f" | vs binance spot {100 * (r['close'] / ref['close'] - 1):+.3f}%"
        else:
            note = " | candle time differs from binance spot"
    lines.append(f"{r['name']}: 1h candle {stamp(r['open_ms'])} UTC close {r['close']:.1f} | age {r['age_min']:.1f} min{note}")

text = "Source check (NOT a trading signal)\n" + "\n".join(lines)
print(text)

token, chat = os.environ.get("TOKEN"), os.environ.get("CHAT")
if token and chat:
    try:
        payload = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
        urllib.request.urlopen(request, timeout=20).read()
        print("telegram: sent")
    except Exception as exc:
        print(f"telegram: FAILED {type(exc).__name__}")
        sys.exit(1)
else:
    print("telegram: skipped (no credentials in the environment)")

if all("error" in r for r in results):
    sys.exit(1)
