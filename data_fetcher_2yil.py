"""
2 Yıllık BTC + ETH saatlik veri indir (Binance public klines API).
Grid backtest için kullanılacak.

Çıktı: data/price_history_2yil.csv
"""
from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

OUT = Path(__file__).parent / "data" / "price_history_2yil.csv"
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1h"
# 2 yıl = 730 gün * 24 = 17520 bar (her sembol için)
BASLANGIC = int(datetime(2024, 4, 19, tzinfo=timezone.utc).timestamp() * 1000)
BITIS = int(datetime(2026, 4, 19, tzinfo=timezone.utc).timestamp() * 1000)
LIMIT = 1000  # Binance max


def fetch_klines(symbol: str, start_ms: int, end_ms: int):
    url = "https://api.binance.com/api/v3/klines"
    rows = []
    cursor = start_ms
    while cursor < end_ms:
        params = {
            "symbol": symbol,
            "interval": INTERVAL,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": LIMIT,
        }
        for attempt in range(3):
            try:
                r = requests.get(url, params=params, timeout=30)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                print(f"  retry {attempt+1}: {e}")
                time.sleep(2)
        else:
            raise RuntimeError(f"{symbol} fetch failed at {cursor}")
        if not data:
            break
        for k in data:
            # k = [openTime, open, high, low, close, volume, closeTime, ...]
            dt = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc)
            rows.append([symbol, dt.isoformat(), k[1], k[2], k[3], k[4], k[5]])
        cursor = data[-1][6] + 1  # closeTime + 1 ms
        print(f"  {symbol}: {len(rows)} bar ({dt.strftime('%Y-%m-%d %H:%M')})")
        time.sleep(0.2)  # rate limit nazik
    return rows


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for sym in SYMBOLS:
        print(f"=== {sym} ===")
        rows = fetch_klines(sym, BASLANGIC, BITIS)
        all_rows.extend(rows)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "datetime", "open", "high", "low", "close", "volume"])
        w.writerows(all_rows)
    print(f"\nYazıldı: {OUT} ({len(all_rows)} satır)")


if __name__ == "__main__":
    main()
