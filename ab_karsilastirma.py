"""
A/B Karşılaştırma — Bot vs BTC Buy & Hold
30 gün boyunca her akşam çalışır, snapshot alır.
İlk çalıştırmada T0 belirlenir, sonraki çalıştırmalarda günlük fark hesaplanır.

Kullanım:
  python ab_karsilastirma.py             # snapshot al + tabloyu yazdır
  python ab_karsilastirma.py --rapor     # sadece rapor üret (data/ab_rapor.md)
  python ab_karsilastirma.py --reset     # T0'ı sıfırla (DİKKAT)

Ayar: BAŞLANGIÇ_USDT (her iki taraf için aynı sermaye)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import hashlib
import hmac
import time
from urllib.parse import urlencode

BASLANGIC_USDT = 100.0  # Her iki taraf için sermaye
STATE_DOSYA = Path(__file__).parent / "data" / "ab_karsilastirma.json"
RAPOR_DOSYA = Path(__file__).parent / "data" / "ab_rapor.md"
BINANCE_API = "https://api.binance.com"


def binance_fiyat(symbol="BTCUSDT") -> float:
    """Binance public API — auth'suz, anlık fiyat."""
    r = requests.get(f"{BINANCE_API}/api/v3/ticker/price",
                     params={"symbol": symbol}, timeout=10)
    r.raise_for_status()
    return float(r.json()["price"])


def binance_hesap_bakiye() -> dict:
    """
    Binance Spot hesap bakiyesi. .env'den API key gerek.
    Dönüş: {asset: free_balance, ...} sadece >0 olanlar
    """
    key = os.getenv("BINANCE_API_KEY")
    secret = os.getenv("BINANCE_API_SECRET")
    if not key or not secret:
        return {}

    ts = int(time.time() * 1000)
    params = {"timestamp": ts, "recvWindow": 5000}
    qs = urlencode(params)
    sig = hmac.new(secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
    qs += f"&signature={sig}"

    r = requests.get(
        f"{BINANCE_API}/api/v3/account?{qs}",
        headers={"X-MBX-APIKEY": key},
        timeout=15,
    )
    r.raise_for_status()
    bakiyeler = {}
    for b in r.json().get("balances", []):
        free = float(b["free"])
        locked = float(b["locked"])
        if free + locked > 0:
            bakiyeler[b["asset"]] = free + locked
    return bakiyeler


def bot_portfoy_degeri() -> tuple[float, dict]:
    """
    Bot tarafının toplam portföy değeri (USDT cinsinden).
    Spot bakiyeleri × o coin'in USDT fiyatı.
    """
    bakiyeler = binance_hesap_bakiye()
    if not bakiyeler:
        return 0.0, {"hata": "Binance API bağlanamadı"}

    toplam = 0.0
    detay = {}
    for asset, miktar in bakiyeler.items():
        if asset == "USDT":
            usd = miktar
        else:
            try:
                fiyat = binance_fiyat(f"{asset}USDT")
                usd = miktar * fiyat
            except Exception:
                # Trading pair yoksa veya stable coin ise
                usd = miktar if asset in ("BUSD", "USDC", "FDUSD") else 0
        if usd > 0.5:  # toz altındakileri sayma
            detay[asset] = {"miktar": miktar, "usd": round(usd, 2)}
            toplam += usd
    return toplam, detay


def state_yukle() -> dict:
    if STATE_DOSYA.exists():
        return json.loads(STATE_DOSYA.read_text(encoding="utf-8"))
    return {"snapshots": []}


def state_kaydet(s: dict):
    STATE_DOSYA.parent.mkdir(parents=True, exist_ok=True)
    STATE_DOSYA.write_text(json.dumps(s, indent=2, ensure_ascii=False),
                            encoding="utf-8")


def snapshot_al():
    """Bot ve B&H tarafının anlık değerini kaydet."""
    s = state_yukle()
    btc_fiyat = binance_fiyat("BTCUSDT")
    bot_deger, bot_detay = bot_portfoy_degeri()

    # T0 — ilk snapshot
    if not s["snapshots"]:
        # ADİL KARŞILAŞTIRMA: B&H sermayesi = bot'un T0 değeri
        bh_baslangic = bot_deger if bot_deger > 0 else BASLANGIC_USDT
        bh_btc_miktar = bh_baslangic / btc_fiyat  # sanal BTC alımı
        s["t0"] = {
            "zaman": datetime.now(timezone.utc).isoformat(),
            "btc_fiyat": btc_fiyat,
            "bh_btc_miktar": bh_btc_miktar,
            "bh_baslangic_usdt": bh_baslangic,
            "bot_baslangic_deger": bot_deger,
        }
        print(f"[T0] Başlangıç kaydedildi (adil karşılaştırma — eşit sermaye).")
        print(f"     B&H tarafı:  ${bh_baslangic:.2f} → {bh_btc_miktar:.6f} BTC @ ${btc_fiyat:.2f}")
        print(f"     Bot tarafı:  ${bot_deger:.2f}")

    bh_simdiki_deger = s["t0"]["bh_btc_miktar"] * btc_fiyat
    snap = {
        "zaman": datetime.now(timezone.utc).isoformat(),
        "btc_fiyat": btc_fiyat,
        "bot_deger": bot_deger,
        "bot_detay": bot_detay,
        "bh_deger": bh_simdiki_deger,
    }
    s["snapshots"].append(snap)
    state_kaydet(s)

    # Hızlı tablo
    t0_bot = s["t0"]["bot_baslangic_deger"]
    bot_pct = (bot_deger / t0_bot - 1) * 100 if t0_bot > 0 else 0
    bh_pct = (bh_simdiki_deger / s["t0"]["bh_baslangic_usdt"] - 1) * 100
    fark = bot_pct - bh_pct

    print(f"\n=== Snapshot #{len(s['snapshots'])} | {snap['zaman'][:19]} ===")
    print(f"BTC fiyat:   ${btc_fiyat:,.2f}")
    print(f"Bot:         ${bot_deger:>8,.2f}  ({bot_pct:+.2f}%)")
    print(f"B&H:         ${bh_simdiki_deger:>8,.2f}  ({bh_pct:+.2f}%)")
    print(f"Fark:        {fark:+.2f} puan  ← {'BOT ÖNDE' if fark > 0 else 'B&H ÖNDE' if fark < 0 else 'BERABERE'}")
    if bot_detay and "hata" not in bot_detay:
        parcalar = [f"{k} ${v['usd']:.0f}" for k, v in bot_detay.items()]
        print("Bot içerik:  " + ", ".join(parcalar))


def rapor_uret():
    s = state_yukle()
    if not s["snapshots"]:
        print("Henüz snapshot yok.")
        return

    t0 = s["t0"]
    son = s["snapshots"][-1]
    son_bot_pct = (son["bot_deger"] / t0["bot_baslangic_deger"] - 1) * 100 if t0["bot_baslangic_deger"] > 0 else 0
    son_bh_pct = (son["bh_deger"] / t0["bh_baslangic_usdt"] - 1) * 100

    lines = []
    lines.append("# A/B Karşılaştırma Raporu — Bot vs BTC Buy & Hold")
    lines.append("")
    lines.append(f"**Başlangıç (T0):** {t0['zaman'][:19]} UTC")
    lines.append(f"**Son güncelleme:** {son['zaman'][:19]} UTC")
    lines.append(f"**Snapshot sayısı:** {len(s['snapshots'])}")
    lines.append(f"**Sermaye:** ${BASLANGIC_USDT:.2f} (her iki taraf)")
    lines.append("")
    lines.append("## Anlık Skor")
    lines.append("")
    lines.append(f"| Strateji | Başlangıç | Şu an | Getiri |")
    lines.append(f"|---|---:|---:|---:|")
    lines.append(f"| **Bot** (mevcut momentum) | ${t0['bot_baslangic_deger']:.2f} | ${son['bot_deger']:.2f} | **{son_bot_pct:+.2f}%** |")
    lines.append(f"| **BTC B&H** | ${t0['bh_baslangic_usdt']:.2f} | ${son['bh_deger']:.2f} | **{son_bh_pct:+.2f}%** |")
    lines.append(f"| **Fark** | | | {son_bot_pct - son_bh_pct:+.2f} puan |")
    lines.append("")
    if son_bot_pct > son_bh_pct:
        lines.append(f"🏆 **Bot önde** ({son_bot_pct - son_bh_pct:+.2f} puan)")
    elif son_bh_pct > son_bot_pct:
        lines.append(f"🏆 **BTC B&H önde** ({son_bh_pct - son_bot_pct:+.2f} puan)")
    else:
        lines.append("🤝 **Berabere**")
    lines.append("")
    lines.append("## Günlük tablo")
    lines.append("")
    lines.append("| # | Zaman | BTC fiyat | Bot $ | Bot % | B&H $ | B&H % | Fark |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|")
    for i, snap in enumerate(s["snapshots"], 1):
        b_pct = (snap["bot_deger"] / t0["bot_baslangic_deger"] - 1) * 100 if t0["bot_baslangic_deger"] > 0 else 0
        h_pct = (snap["bh_deger"] / t0["bh_baslangic_usdt"] - 1) * 100
        lines.append(
            f"| {i} | {snap['zaman'][:16]} | ${snap['btc_fiyat']:,.0f} | "
            f"${snap['bot_deger']:.2f} | {b_pct:+.2f}% | "
            f"${snap['bh_deger']:.2f} | {h_pct:+.2f}% | {b_pct - h_pct:+.2f} |"
        )

    RAPOR_DOSYA.parent.mkdir(parents=True, exist_ok=True)
    RAPOR_DOSYA.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapor: {RAPOR_DOSYA}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rapor", action="store_true", help="Sadece rapor üret")
    p.add_argument("--reset", action="store_true", help="State'i sıfırla")
    args = p.parse_args()

    if args.reset:
        if STATE_DOSYA.exists():
            yedek = STATE_DOSYA.with_suffix(".YEDEK.json")
            STATE_DOSYA.rename(yedek)
            print(f"Eski state yedeklendi: {yedek}")
        return

    if args.rapor:
        rapor_uret()
        return

    snapshot_al()
    rapor_uret()


if __name__ == "__main__":
    main()
