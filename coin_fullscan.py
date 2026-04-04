"""
🪙 COIN FULL SCAN — Tüm Binance Paralel Tarayıcı
===================================================
533+ coin'i paralel tarar, skora göre sıralar.
4 worker aynı anda çalışır — 1-2 dakikada biter.

Kullanım:
  python coin_fullscan.py              # Tüm coinleri tara
  python coin_fullscan.py --usdt       # Sadece USDT
  python coin_fullscan.py --try        # Sadece TRY
  python coin_fullscan.py --top 20     # En iyi 20
  python coin_fullscan.py --roket      # Sadece roketler
"""

import requests
import numpy as np
import pandas as pd
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"


def tum_coinleri_cek(min_hacim_usdt=1000000, min_hacim_try=100000):
    """Binance'deki tüm aktif coinleri çek."""
    r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=15)
    data = r.json()

    coins = []
    for d in data:
        sym = d["symbol"]
        hacim = float(d["quoteVolume"])

        if sym.endswith("USDT") and hacim > min_hacim_usdt:
            coins.append({"symbol": sym, "hacim": hacim, "tip": "USDT"})
        elif sym.endswith("TRY") and hacim > min_hacim_try:
            coins.append({"symbol": sym, "hacim": hacim, "tip": "TRY"})

    return coins


def coin_analiz(symbol):
    """Tek coin için tam analiz — thread-safe."""
    try:
        # Kline verisi çek
        r = requests.get("https://api.binance.com/api/v3/klines",
                        params={"symbol": symbol, "interval": "1h", "limit": 50}, timeout=5)
        data = r.json()
        if len(data) < 25:
            return None

        closes = np.array([float(k[4]) for k in data])
        volumes = np.array([float(k[5]) for k in data])
        highs = np.array([float(k[2]) for k in data])
        lows = np.array([float(k[3]) for k in data])

        son = closes[-1]
        if son == 0:
            return None

        # 24s değişim
        degisim_24s = (closes[-1] / closes[-24] - 1) * 100 if len(closes) >= 24 else 0
        degisim_1s = (closes[-1] / closes[-2] - 1) * 100

        # EMA
        ema10 = pd.Series(closes).ewm(span=10).mean().iloc[-1]
        ema20 = pd.Series(closes).ewm(span=20).mean().iloc[-1]
        ema_ok = ema10 > ema20

        # RSI
        delta = np.diff(closes)
        gain = np.mean(delta[delta > 0][-14:]) if len(delta[delta > 0]) > 0 else 0
        loss = abs(np.mean(delta[delta < 0][-14:])) if len(delta[delta < 0]) > 0 else 0.001
        rsi = 100 - (100 / (1 + gain / loss))

        # Hacim
        vol_oran = volumes[-1] / np.mean(volumes[-24:-1]) if np.mean(volumes[-24:-1]) > 0 else 0

        # MACD
        ema12 = pd.Series(closes).ewm(span=12).mean().iloc[-1]
        ema26 = pd.Series(closes).ewm(span=26).mean().iloc[-1]
        macd_ok = ema12 > ema26

        # Bollinger
        sma20 = np.mean(closes[-20:])
        std20 = np.std(closes[-20:])
        bb_width = (4 * std20 / sma20 * 100) if sma20 > 0 else 0
        sikisma = bb_width < 5

        # Kapanış gücü
        kapanis_gucu = son / highs[-1] if highs[-1] > 0 else 0

        # SKOR HESAPLA (0-100) — PATLAMA ÖNCESİ YAKALA
        skor = 0
        evre = "?"

        # ═══ EVRE TESPİTİ ═══
        # Evre 1: SIKIŞMA (patlama öncesi) — EN DEĞERLİ
        # Evre 2: ERKEN BİRİKİM (hacim artıyor, fiyat henüz oynamadı)
        # Evre 3: PATLAMA BAŞLANGICI (ilk hareket)
        # Evre 4: GEÇ KALDIK (zaten patlamış)

        if sikisma and vol_oran >= 1.2 and vol_oran < 3 and abs(degisim_24s) < 5:
            # SIKIŞMA + hafif hacim artışı + fiyat henüz oynamamış
            evre = "SIKISMA"
            skor += 40  # EN YÜKSEK — patlama yakın!

        elif vol_oran >= 1.5 and vol_oran < 4 and degisim_24s < 3 and ema_ok:
            # Hacim artıyor ama fiyat henüz az hareket etmiş
            evre = "BIRIKIM"
            skor += 35

        elif vol_oran >= 2 and degisim_24s >= 3 and degisim_24s < 10:
            # İlk hareket başlamış — hâlâ erken
            evre = "ERKEN_HAREKET"
            skor += 25

        elif vol_oran >= 5 or degisim_24s >= 10:
            # ZATEN PATLADI — geç kaldık
            evre = "GEC_KALDIK"
            skor += 10  # Düşük skor — kovalama

        # ═══ TEKNIK BONUS (30 puan) ═══
        if ema_ok: skor += 10
        if 40 < rsi < 60: skor += 10  # RSI orta = henüz aşırı alım değil
        elif rsi > 70: skor -= 5  # Aşırı alım = GEÇ
        if macd_ok: skor += 5
        if sikisma: skor += 5

        # ═══ HACİM KALİTESİ (20 puan) ═══
        # Yavaş artan hacim > ani patlama
        if 1.2 <= vol_oran < 2.5:
            skor += 20  # Sessiz birikim — EN İYİ
        elif 2.5 <= vol_oran < 5:
            skor += 10  # Orta
        elif vol_oran >= 5:
            skor += 5   # Zaten patlamış

        # ═══ KAPANIŞ (10 puan) ═══
        if kapanis_gucu >= 0.98: skor += 10
        elif kapanis_gucu >= 0.95: skor += 5

        # CEZA: Zaten çok yükselmiş → skor düşür
        if degisim_24s > 15:
            skor -= 15  # Fomo tuzağı
        elif degisim_24s > 10:
            skor -= 10

        skor = max(0, min(100, skor))

        # Roket tespiti (bilgi amaçlı, skor artırmaz)
        roket = vol_oran >= 5 or degisim_24s >= 15 or degisim_1s >= 5

        return {
            "symbol": symbol,
            "fiyat": round(son, 8 if son < 0.01 else 4 if son < 1 else 2),
            "skor": min(100, skor),
            "degisim_24s": round(degisim_24s, 1),
            "degisim_1s": round(degisim_1s, 1),
            "hacim_x": round(vol_oran, 1),
            "rsi": round(rsi, 0),
            "ema_ok": ema_ok,
            "roket": roket,
            "bb_sikisma": sikisma,
            "evre": evre,
        }

    except:
        return None


def paralel_tara(coins, max_workers=8):
    """Paralel tarama — 8 thread aynı anda."""
    sonuclar = []
    toplam = len(coins)

    print(f"\n🪙 FULL SCAN — {toplam} coin, {max_workers} paralel worker")
    print("=" * 70)

    baslangic = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(coin_analiz, c["symbol"]): c for c in coins}

        tamamlanan = 0
        for future in as_completed(futures):
            tamamlanan += 1
            result = future.result()
            if result:
                sonuclar.append(result)

            if tamamlanan % 50 == 0:
                print(f"  [{tamamlanan}/{toplam}] {len(sonuclar)} sonuç...")

    sure = time.time() - baslangic

    # SKORA GÖRE SIRALA
    sonuclar.sort(key=lambda x: x["skor"], reverse=True)

    print(f"\n⏱️ {toplam} coin {sure:.1f} saniyede tarandı")
    print(f"{'='*70}")

    return sonuclar


def sonuclari_goster(sonuclar, top=30, sadece_roket=False):
    """Sonuçları göster."""
    if sadece_roket:
        sonuclar = [s for s in sonuclar if s["roket"]]
        print(f"\n🚀 ROKETLER ({len(sonuclar)} adet):")
    else:
        print(f"\n📊 TOP {min(top, len(sonuclar))} (skora göre):")

    print(f"{'='*70}")
    gosterilecek = sonuclar[:top]

    for i, s in enumerate(gosterilecek):
        # Emoji
        if i == 0: emoji = "🥇"
        elif i == 1: emoji = "🥈"
        elif i == 2: emoji = "🥉"
        elif s["roket"]: emoji = "🚀"
        elif s["skor"] >= 70: emoji = "🔥"
        elif s["skor"] >= 50: emoji = "🪙"
        else: emoji = "⚪"

        birim = "₺" if "TRY" in s["symbol"] else "$"
        fiyat_str = f"{birim}{s['fiyat']}"

        ek = []
        ek.append(s.get("evre", "?"))
        if s["roket"]: ek.append("ROKET")
        if s["bb_sikisma"]: ek.append("BB↓")
        if s["ema_ok"]: ek.append("EMA✅")
        ek_str = f" [{','.join(ek)}]"

        print(f"  {i+1:3}. {emoji} {s['symbol']:15} {fiyat_str:>14} | Skor:{s['skor']:3} | 24s:{s['degisim_24s']:+6.1f}% | Hacim:x{s['hacim_x']:4.1f} | RSI:{s['rsi']:3.0f}{ek_str}")

    # İstatistikler
    roketler = [s for s in sonuclar if s["roket"]]
    yukselenler = [s for s in sonuclar if s["degisim_24s"] > 0]
    print(f"\n📊 Özet: {len(sonuclar)} coin | {len(roketler)} roket | {len(yukselenler)} yükselen ({len(yukselenler)/max(1,len(sonuclar))*100:.0f}%)")

    # Kaydet
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / "fullscan_sonuc.json", "w") as f:
        json.dump({
            "zaman": datetime.now().isoformat(),
            "toplam": len(sonuclar),
            "roket": len(roketler),
            "top20": [{k: (bool(v) if isinstance(v, (np.bool_,)) else v) for k,v in s.items()} for s in sonuclar[:20]],
        }, f, indent=2)

    return sonuclar


if __name__ == "__main__":
    # Coin listesini çek
    if "--try" in sys.argv:
        coins = tum_coinleri_cek(min_hacim_usdt=999999999, min_hacim_try=50000)
    elif "--usdt" in sys.argv:
        coins = tum_coinleri_cek(min_hacim_usdt=500000, min_hacim_try=999999999)
    else:
        coins = tum_coinleri_cek()

    print(f"📡 {len(coins)} coin bulundu (Binance)")

    # Paralel tara
    sonuclar = paralel_tara(coins, max_workers=8)

    # Göster
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 30
    sadece_roket = "--roket" in sys.argv

    sonuclari_goster(sonuclar, top=top, sadece_roket=sadece_roket)
