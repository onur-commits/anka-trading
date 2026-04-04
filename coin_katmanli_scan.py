"""
🪙 COIN KATMANLI TARAMA — 500 Coin, 2 Katman, Paralel
========================================================
Katman 1: 300 büyük coin → Uzman ajanlar (detaylı analiz)
Katman 2: 200 küçük/yeni coin → Keşif ajanları (10x potansiyel)

Her katman farklı strateji:
  Katman 1: Sıkışma + birikim + teknik → güvenli giriş
  Katman 2: Hacim anomali + fiyat keşfi → yüksek risk/ödül
"""

import requests
import numpy as np
import pandas as pd
import json
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def coin_katmanlari_yukle():
    """Binance'den tüm coinleri çek, katmanlara ayır."""
    r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=15)
    data = r.json()

    usdt = []
    for d in data:
        if d["symbol"].endswith("USDT"):
            hacim = float(d["quoteVolume"])
            fiyat = float(d["lastPrice"])
            degisim = float(d["priceChangePercent"])
            if hacim > 100000:  # Min $100K hacim
                usdt.append({
                    "symbol": d["symbol"],
                    "hacim": hacim,
                    "fiyat": fiyat,
                    "degisim_24s": degisim,
                })

    usdt.sort(key=lambda x: x["hacim"], reverse=True)
    return usdt[:300], usdt[300:500]


# ================================================================
# KATMAN 1: UZMAN AJAN (Büyük coinler — detaylı analiz)
# ================================================================
def uzman_analiz(symbol):
    """
    Büyük coin için detaylı analiz:
    - Teknik (EMA, RSI, MACD, Bollinger)
    - Hacim profili (birikim/dağıtım)
    - Funding rate (futures)
    - Emir defteri dengesi
    """
    try:
        # Kline
        r = requests.get("https://api.binance.com/api/v3/klines",
                        params={"symbol": symbol, "interval": "1h", "limit": 72}, timeout=5)
        data = r.json()
        if len(data) < 50:
            return None

        closes = np.array([float(k[4]) for k in data])
        volumes = np.array([float(k[5]) for k in data])
        highs = np.array([float(k[2]) for k in data])
        lows = np.array([float(k[3]) for k in data])

        son = closes[-1]
        if son == 0: return None

        # Teknik
        ema10 = pd.Series(closes).ewm(span=10).mean().iloc[-1]
        ema20 = pd.Series(closes).ewm(span=20).mean().iloc[-1]
        ema50 = pd.Series(closes).ewm(span=50).mean().iloc[-1]
        ema_ok = ema10 > ema20
        trend_gucu = (ema10 > ema20 > ema50)  # Altın sıralama

        # RSI
        delta = np.diff(closes)
        gain = np.mean([d for d in delta[-14:] if d > 0]) if any(d > 0 for d in delta[-14:]) else 0
        loss = abs(np.mean([d for d in delta[-14:] if d < 0])) if any(d < 0 for d in delta[-14:]) else 0.001
        rsi = 100 - (100 / (1 + gain / loss))

        # MACD
        ema12 = pd.Series(closes).ewm(span=12).mean().iloc[-1]
        ema26 = pd.Series(closes).ewm(span=26).mean().iloc[-1]
        macd = ema12 - ema26
        macd_signal = pd.Series(closes).ewm(span=12).mean().ewm(span=9).mean().iloc[-1] - pd.Series(closes).ewm(span=26).mean().ewm(span=9).mean().iloc[-1]
        macd_ok = macd > 0

        # Bollinger
        sma20 = np.mean(closes[-20:])
        std20 = np.std(closes[-20:])
        bb_width = (4 * std20 / sma20 * 100) if sma20 > 0 else 0
        sikisma = bb_width < 5

        # Hacim profili
        vol_son6 = np.mean(volumes[-6:])
        vol_onceki = np.mean(volumes[-24:-6])
        vol_oran = vol_son6 / vol_onceki if vol_onceki > 0 else 0

        # OBV trendi
        obv = np.cumsum(np.sign(np.diff(closes)) * volumes[1:])
        obv_trend = obv[-1] > np.mean(obv[-20:]) if len(obv) >= 20 else False

        # Kapanış gücü
        kapanis = son / highs[-1] if highs[-1] > 0 else 0

        # Değişimler
        degisim_24s = (closes[-1] / closes[-24] - 1) * 100 if len(closes) >= 24 else 0
        degisim_1s = (closes[-1] / closes[-2] - 1) * 100

        # Funding rate (futures — hata olursa atla)
        funding = 0
        try:
            fr = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                            params={"symbol": symbol, "limit": 1}, timeout=3)
            fd = fr.json()
            if fd: funding = float(fd[0]["fundingRate"])
        except:
            pass

        # Emir defteri dengesi
        bid_ask_oran = 1.0
        try:
            ob = requests.get("https://api.binance.com/api/v3/depth",
                            params={"symbol": symbol, "limit": 10}, timeout=3)
            ob_data = ob.json()
            bid_vol = sum(float(b[1]) for b in ob_data.get("bids", []))
            ask_vol = sum(float(a[1]) for a in ob_data.get("asks", []))
            bid_ask_oran = bid_vol / (ask_vol + 1e-10)
        except:
            pass

        # ═══ UZMAN SKOR (0-100) ═══
        skor = 0
        evre = "?"

        # Evre tespiti
        if sikisma and 1.0 <= vol_oran <= 2.5 and abs(degisim_24s) < 5:
            evre = "SIKISMA"
            skor += 35
        elif vol_oran >= 1.3 and vol_oran < 3.5 and degisim_24s < 3 and ema_ok:
            evre = "BIRIKIM"
            skor += 30
        elif vol_oran >= 2 and 3 <= degisim_24s < 10:
            evre = "ERKEN_HAREKET"
            skor += 20
        elif degisim_24s >= 10 or vol_oran >= 5:
            evre = "GEC_KALDIK"
            skor += 5

        # Teknik bonus
        if trend_gucu: skor += 15  # Altın sıralama
        elif ema_ok: skor += 8
        if 40 < rsi < 60: skor += 8
        if macd_ok: skor += 5
        if obv_trend: skor += 5

        # Hacim kalitesi
        if 1.2 <= vol_oran < 2.5: skor += 10
        elif vol_oran >= 2.5: skor += 5

        # Funding (negatif = dip potansiyeli)
        if funding < -0.001: skor += 8
        elif funding > 0.005: skor -= 5

        # Emir defteri
        if bid_ask_oran > 1.3: skor += 5
        elif bid_ask_oran < 0.7: skor -= 5

        # Kapanış
        if kapanis >= 0.98: skor += 5

        # Ceza
        if degisim_24s > 15: skor -= 15
        elif degisim_24s > 10: skor -= 10

        skor = max(0, min(100, skor))

        return {
            "symbol": symbol,
            "katman": 1,
            "fiyat": round(son, 8 if son < 0.01 else 4 if son < 1 else 2),
            "skor": skor,
            "evre": evre,
            "degisim_24s": round(degisim_24s, 1),
            "degisim_1s": round(degisim_1s, 1),
            "hacim_x": round(vol_oran, 1),
            "rsi": round(rsi, 0),
            "ema_ok": bool(ema_ok),
            "trend_gucu": bool(trend_gucu),
            "sikisma": bool(sikisma),
            "funding": round(funding, 5),
            "bid_ask": round(bid_ask_oran, 1),
            "obv_trend": bool(obv_trend),
        }
    except:
        return None


# ================================================================
# KATMAN 2: KEŞİF AJANI (Küçük/yeni coinler — 10x potansiyel)
# ================================================================
def kesif_analiz(symbol):
    """
    Küçük coin için keşif analizi:
    - Anormal hacim artışı (birisi keşfetti mi?)
    - Fiyat yapısı (dip mi, tavan mı?)
    - Momentum ivmesi
    """
    try:
        r = requests.get("https://api.binance.com/api/v3/klines",
                        params={"symbol": symbol, "interval": "1h", "limit": 48}, timeout=5)
        data = r.json()
        if len(data) < 24:
            return None

        closes = np.array([float(k[4]) for k in data])
        volumes = np.array([float(k[5]) for k in data])

        son = closes[-1]
        if son == 0: return None

        degisim_24s = (closes[-1] / closes[-24] - 1) * 100 if len(closes) >= 24 else 0
        degisim_1s = (closes[-1] / closes[-2] - 1) * 100

        # Hacim anomali
        vol_son6 = np.mean(volumes[-6:])
        vol_ort = np.mean(volumes)
        vol_oran = vol_son6 / vol_ort if vol_ort > 0 else 0

        # Fiyat pozisyonu (son 48 saatte nerede?)
        fiyat_min = np.min(closes)
        fiyat_max = np.max(closes)
        fiyat_range = fiyat_max - fiyat_min
        if fiyat_range > 0:
            fiyat_poz = (son - fiyat_min) / fiyat_range  # 0=dip, 1=tepe
        else:
            fiyat_poz = 0.5

        # Momentum ivmesi (son 6 saat vs önceki 6 saat)
        if len(closes) >= 12:
            mom_son = (closes[-1] / closes[-6] - 1) * 100
            mom_onceki = (closes[-6] / closes[-12] - 1) * 100
            ivme = mom_son - mom_onceki  # Pozitif = hızlanıyor
        else:
            ivme = 0

        # ═══ KEŞİF SKORU (0-100) ═══
        skor = 0

        # Hacim keşfi (birileri bu coini keşfetti!)
        if vol_oran >= 3 and degisim_24s < 5:
            skor += 40  # Hacim patlamış ama fiyat henüz oynamamış → ERKEN!
        elif vol_oran >= 2:
            skor += 25
        elif vol_oran >= 1.5:
            skor += 15

        # Dip pozisyonu (ucuzken al)
        if fiyat_poz < 0.3:
            skor += 20  # Dipte
        elif fiyat_poz < 0.5:
            skor += 10

        # İvme (hızlanıyor mu?)
        if ivme > 2:
            skor += 15
        elif ivme > 0:
            skor += 5

        # Momentum
        if 3 <= degisim_24s < 10:
            skor += 10
        elif degisim_24s >= 10:
            skor += 5  # Zaten çıkmış

        # Ceza
        if degisim_24s > 20: skor -= 20
        if fiyat_poz > 0.9: skor -= 10  # Tepede → riskli

        skor = max(0, min(100, skor))

        return {
            "symbol": symbol,
            "katman": 2,
            "fiyat": round(son, 8 if son < 0.01 else 6 if son < 0.1 else 4 if son < 1 else 2),
            "skor": skor,
            "evre": "KESIF" if vol_oran >= 2 and degisim_24s < 5 else "MOMENTUM" if degisim_24s > 5 else "DIP" if fiyat_poz < 0.3 else "IZLE",
            "degisim_24s": round(degisim_24s, 1),
            "hacim_x": round(vol_oran, 1),
            "fiyat_poz": round(fiyat_poz, 2),
            "ivme": round(ivme, 1),
        }
    except:
        return None


# ================================================================
# ANA TARAMA
# ================================================================
def katmanli_tara():
    """500 coin, 2 katman, paralel tarama."""
    katman1, katman2 = coin_katmanlari_yukle()

    print(f"\n🪙 KATMANLI TARAMA")
    print(f"   Katman 1 (büyük): {len(katman1)} coin → Uzman analiz")
    print(f"   Katman 2 (küçük): {len(katman2)} coin → Keşif analiz")
    print("=" * 70)

    baslangic = time.time()

    # Katman 1: Uzman analiz (paralel)
    sonuc1 = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(uzman_analiz, c["symbol"]): c for c in katman1}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sonuc1.append(result)

    # Katman 2: Keşif analiz (paralel)
    sonuc2 = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(kesif_analiz, c["symbol"]): c for c in katman2}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sonuc2.append(result)

    sure = time.time() - baslangic

    # Sırala
    sonuc1.sort(key=lambda x: x["skor"], reverse=True)
    sonuc2.sort(key=lambda x: x["skor"], reverse=True)

    # Göster
    print(f"\n⏱️ {len(sonuc1)+len(sonuc2)} coin {sure:.1f} saniyede tarandı")

    print(f"\n{'='*70}")
    print(f"📊 KATMAN 1 — TOP 15 BÜYÜK COİN (Uzman Analiz)")
    print(f"{'='*70}")
    for i, s in enumerate(sonuc1[:15]):
        emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔥" if s["skor"] >= 70 else "⚪"
        funding_txt = f" F:{s['funding']:+.4f}" if s.get('funding', 0) != 0 else ""
        ba_txt = f" B/A:{s['bid_ask']}" if s.get('bid_ask', 1) != 1 else ""
        print(f"  {i+1:3}. {emoji} {s['symbol']:15} ${s['fiyat']:>10} | Skor:{s['skor']:3} | {s['evre']:14} | 24s:{s['degisim_24s']:+5.1f}% | Hcm:x{s['hacim_x']:4.1f}{funding_txt}{ba_txt}")

    print(f"\n{'='*70}")
    print(f"💎 KATMAN 2 — TOP 15 KÜÇÜK/YENİ COİN (Keşif)")
    print(f"{'='*70}")
    for i, s in enumerate(sonuc2[:15]):
        emoji = "💎" if s["skor"] >= 60 else "🔍" if s["skor"] >= 40 else "⚪"
        print(f"  {i+1:3}. {emoji} {s['symbol']:15} ${s['fiyat']:>10} | Skor:{s['skor']:3} | {s['evre']:10} | 24s:{s['degisim_24s']:+5.1f}% | Hcm:x{s['hacim_x']:4.1f} | Poz:{s['fiyat_poz']:.0%}")

    # Kaydet
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / "katmanli_sonuc.json", "w") as f:
        json.dump({
            "zaman": datetime.now().isoformat(),
            "katman1_toplam": len(sonuc1),
            "katman2_toplam": len(sonuc2),
            "katman1_top20": [{k: (bool(v) if isinstance(v, np.bool_) else v) for k,v in s.items()} for s in sonuc1[:20]],
            "katman2_top20": [{k: (bool(v) if isinstance(v, np.bool_) else v) for k,v in s.items()} for s in sonuc2[:20]],
        }, f, indent=2, ensure_ascii=False)

    return sonuc1, sonuc2


if __name__ == "__main__":
    katmanli_tara()
