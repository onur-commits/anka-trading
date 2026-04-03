"""
V3 Bridge Writer — Python -> MatriksIQ C# arasi JSON kopru
===========================================================
Bu script her 60 saniyede bir calisir (cron veya motor_v3 icinden).
Sonucu v3_bridge.json olarak yazar, C# tarafindaki BOMBA_V3_ALPHA okur.

KURULUM:
  1. pip install yfinance requests pandas numpy
  2. Bu dosyayi motor_v3.py'den cagir veya ayri cron job olarak calistir
  3. VPS'te: C:\\Users\\onurbodur\\Desktop\\IQ_Deploy\\v3_bridge.json
     Mac'te: Parallels uzerinden ayni yola yaz

BRIDGE JSON FORMATI:
{
    "timestamp": "2026-04-01T10:15:00",
    "market_regime": "bull",
    "regime_confidence": 75.2,
    "xu100_change_pct": 0.85,
    "usdtry_change_pct": -0.12,
    "usdtry_signal": "tl_weak_bist_up",
    "vix_level": 18.5,
    "vix_signal": "risk_on",
    "foreign_flow": "inflow",
    "foreign_flow_mln": 320.5,
    "symbols": {
        "AYEN": {
            "ml_score": 0.78,
            "ml_confidence": 0.82,
            "sector": "enerji",
            "sector_momentum": 1.5,
            "signal": "strong_buy",
            "overnight_gap_pct": 0.3
        },
        ...
    }
}
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Proje root — tahmin_motoru_v2'yi import etmek icin
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

try:
    import yfinance as yf
except ImportError:
    yf = None
    print("UYARI: yfinance yuklu degil. pip install yfinance")

# tahmin_motoru_v2'den ML fonksiyonlarini al
try:
    from tahmin_motoru_v2 import (
        feature_olustur_v2,
        market_rejim_tespit,
        sektor_momentum_hesapla,
        SEKTOR_HISSELERI,
    )
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("UYARI: tahmin_motoru_v2 import edilemedi — ML katmani devre disi")

# ── KONFIGÜRASYON ────────────────────────────────────────────
VPS_MODE = os.name == "nt"  # Windows = VPS, Mac = gelistirme

if VPS_MODE:
    BRIDGE_OUTPUT = Path(r"C:\Users\onurbodur\Desktop\IQ_Deploy\v3_bridge.json")
else:
    # Mac — Parallels uzerinden Windows'a yazilacak
    # Alternatif: /tmp/v3_bridge.json + kopyalama
    BRIDGE_OUTPUT = PROJECT_DIR / "data" / "v3_bridge.json"

# Yahoo Finance ticker mapping
BIST_TICKERS = {
    "AYEN": "AYEN.IS",
    "KONTR": "KONTR.IS",
    "EREGL": "EREGL.IS",
    "SASA": "SASA.IS",
    "GESAN": "GESAN.IS",
    "GARAN": "GARAN.IS",
    "AKBNK": "AKBNK.IS",
    "THYAO": "THYAO.IS",
    "ASELS": "ASELS.IS",
    "TUPRS": "TUPRS.IS",
    "SISE": "SISE.IS",
    "TOASO": "TOASO.IS",
    "ISCTR": "ISCTR.IS",
    "TKFEN": "TKFEN.IS",
    "AKSEN": "AKSEN.IS",
}

# Sektor mapping (C# tarafina gonderilecek)
TICKER_SECTOR = {}
for sektor, hisseler in SEKTOR_HISSELERI.items() if ML_AVAILABLE else {}:
    for h in hisseler:
        short = h.replace(".IS", "")
        TICKER_SECTOR[short] = sektor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BRIDGE] %(message)s")
log = logging.getLogger("v3_bridge")


# ================================================================
# VERI CEKME KATMANI
# ================================================================

def fetch_xu100(period="5d", interval="1d"):
    """XU100 endeks verisini cek."""
    if yf is None:
        return None
    try:
        df = yf.download("XU100.IS", period=period, interval=interval, progress=False)
        return df if len(df) > 0 else None
    except Exception as e:
        log.warning(f"XU100 veri hatasi: {e}")
        return None


def fetch_usdtry():
    """USD/TRY kur verisini cek."""
    if yf is None:
        return None, 0.0
    try:
        df = yf.download("USDTRY=X", period="5d", interval="1d", progress=False)
        if df is None or len(df) < 2:
            return None, 0.0
        last = float(df["Close"].iloc[-1])
        prev = float(df["Close"].iloc[-2])
        pct = (last - prev) / prev * 100
        return last, pct
    except Exception as e:
        log.warning(f"USDTRY veri hatasi: {e}")
        return None, 0.0


def fetch_vix():
    """VIX (korku endeksi) verisini cek."""
    if yf is None:
        return 20.0, "risk_on"  # default
    try:
        df = yf.download("^VIX", period="5d", interval="1d", progress=False)
        if df is None or len(df) == 0:
            return 20.0, "risk_on"
        level = float(df["Close"].iloc[-1])
        if level < 15:
            signal = "risk_on"
        elif level < 25:
            signal = "elevated"
        else:
            signal = "risk_off"
        return level, signal
    except Exception as e:
        log.warning(f"VIX veri hatasi: {e}")
        return 20.0, "risk_on"


def fetch_foreign_flow():
    """
    Yabanci akis verisi.
    Gercek veri TCMB EDDS veya Matriks Data API'den gelir.
    Simdilik proxy: XU030 vs XU100 spread (yabanci XU030'da yogun).
    """
    try:
        if yf is None:
            return "neutral", 0.0
        xu030 = yf.download("XU030.IS", period="5d", interval="1d", progress=False)
        xu100 = yf.download("XU100.IS", period="5d", interval="1d", progress=False)
        if xu030 is None or xu100 is None or len(xu030) < 2 or len(xu100) < 2:
            return "neutral", 0.0

        # XU030 XU100'den fazla cikiyorsa yabanci girisi proxy'si
        xu030_ret = float((xu030["Close"].iloc[-1] / xu030["Close"].iloc[-2] - 1) * 100)
        xu100_ret = float((xu100["Close"].iloc[-1] / xu100["Close"].iloc[-2] - 1) * 100)
        spread = xu030_ret - xu100_ret

        if spread > 0.3:
            return "inflow", spread * 200  # kaba tahmin milyon TL
        elif spread < -0.3:
            return "outflow", spread * 200
        else:
            return "neutral", spread * 200
    except Exception as e:
        log.warning(f"Yabanci akis proxy hatasi: {e}")
        return "neutral", 0.0


def usdtry_signal(usdtry_pct):
    """
    USD/TRY korelasyon sinyali.
    TL zayifliyorsa (USDTRY yukseliyorsa) => ihracatci BIST hisseleri icin pozitif.
    TL gucluyorsa => yerli tuketim pozitif, ihracatci negatif.
    """
    if usdtry_pct > 0.5:
        return "tl_weak_bist_up"  # ihracatcilar icin pozitif
    elif usdtry_pct < -0.5:
        return "tl_strong_bist_down"  # ihracatcilar icin negatif
    else:
        return "neutral"


def overnight_gap_prediction(usdtry_pct, vix_level, xu100_pct):
    """
    Ertesi gun acilis gap tahmini.
    USD/TRY gece degisimi + VIX + global piyasalar.
    """
    # Basit lineer model — ilerleyen versiyonda ML ile degistirilecek
    gap = -usdtry_pct * 0.3 + xu100_pct * 0.2 - (vix_level - 20) * 0.01
    return round(float(gap), 2)


# ================================================================
# ML SKOR HESAPLAMA
# ================================================================

def compute_ml_scores(active_tickers):
    """
    Her hisse icin ML tahmin skoru hesapla.
    tahmin_motoru_v2 modelini kullanir.
    """
    if not ML_AVAILABLE or yf is None:
        # ML devre disi — tum hisselere 0.5 (notr) ver
        return {t: {"ml_score": 0.5, "ml_confidence": 0.0, "signal": "hold"}
                for t in active_tickers}

    scores = {}
    for ticker in active_tickers:
        yf_ticker = BIST_TICKERS.get(ticker, f"{ticker}.IS")
        try:
            df = yf.download(yf_ticker, period="6mo", interval="1d", progress=False)
            if df is None or len(df) < 120:
                scores[ticker] = {"ml_score": 0.5, "ml_confidence": 0.0, "signal": "hold"}
                continue

            features = feature_olustur_v2(df)
            if features is None:
                scores[ticker] = {"ml_score": 0.5, "ml_confidence": 0.0, "signal": "hold"}
                continue

            # Son satirin feature'larini al
            last_features = features.iloc[-1:]

            # Model dosyasi varsa yukle ve tahmin yap
            model_path = PROJECT_DIR / "models" / "ensemble_model.pkl"
            if model_path.exists():
                import joblib
                model = joblib.load(model_path)
                proba = model.predict_proba(last_features)[0]
                score = float(proba[1]) if len(proba) > 1 else float(proba[0])
                confidence = float(abs(score - 0.5) * 2)  # 0-1 arasi
            else:
                # Model yoksa basit teknik skor
                rsi = float(features["rsi_14"].iloc[-1]) if "rsi_14" in features.columns else 50
                macd_h = float(features["macd_hist"].iloc[-1]) if "macd_hist" in features.columns else 0
                score = 0.5 + (rsi - 50) / 200 + (1 if macd_h > 0 else -1) * 0.1
                score = max(0.0, min(1.0, score))
                confidence = 0.3  # dusuk guven — model degil, teknik

            # Sinyal siniflandirma
            if score > 0.75:
                signal = "strong_buy"
            elif score > 0.6:
                signal = "buy"
            elif score > 0.4:
                signal = "hold"
            else:
                signal = "sell"

            scores[ticker] = {
                "ml_score": round(score, 3),
                "ml_confidence": round(confidence, 3),
                "signal": signal,
            }

        except Exception as e:
            log.warning(f"{ticker} ML skor hatasi: {e}")
            scores[ticker] = {"ml_score": 0.5, "ml_confidence": 0.0, "signal": "hold"}

    return scores


# ================================================================
# ANA BRIDGE YAZICI
# ================================================================

def generate_bridge(active_tickers=None):
    """
    Tum verileri topla, bridge JSON olustur ve dosyaya yaz.
    """
    if active_tickers is None:
        active_tickers = list(BIST_TICKERS.keys())[:5]

    log.info(f"Bridge guncelleniyor — {len(active_tickers)} hisse")

    # ── Paralel veri cekme ────────────────────────────────────
    xu100_df = fetch_xu100(period="3mo", interval="1d")
    usdtry_val, usdtry_pct = fetch_usdtry()
    vix_level, vix_sig = fetch_vix()
    foreign_dir, foreign_mln = fetch_foreign_flow()

    # XU100 gunluk degisim
    xu100_pct = 0.0
    if xu100_df is not None and len(xu100_df) >= 2:
        xu100_pct = float(
            (xu100_df["Close"].iloc[-1] / xu100_df["Close"].iloc[-2] - 1) * 100
        )

    # Market rejim
    regime_data = {"rejim": "bilinmiyor", "guven": 0}
    if ML_AVAILABLE and xu100_df is not None:
        regime_data = market_rejim_tespit(xu100_df)

    # ML skorlari
    ml_scores = compute_ml_scores(active_tickers)

    # Sektor momentum
    sector_mom = {}
    if ML_AVAILABLE:
        try:
            tum_veri = {}
            for sektor, hisseler in SEKTOR_HISSELERI.items():
                for h in hisseler:
                    if h not in tum_veri and yf is not None:
                        try:
                            tum_veri[h] = yf.download(h, period="1mo", interval="1d", progress=False)
                        except:
                            pass
            sector_mom = sektor_momentum_hesapla(tum_veri)
        except Exception as e:
            log.warning(f"Sektor momentum hatasi: {e}")

    # ── BRIDGE JSON OLUSTUR ───────────────────────────────────
    bridge = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "market_regime": regime_data.get("rejim", "bilinmiyor"),
        "regime_confidence": regime_data.get("guven", 0),
        "xu100_change_pct": round(xu100_pct, 2),
        "usdtry_change_pct": round(usdtry_pct, 2),
        "usdtry_signal": usdtry_signal(usdtry_pct),
        "vix_level": round(vix_level, 1),
        "vix_signal": vix_sig,
        "foreign_flow": foreign_dir,
        "foreign_flow_mln": round(foreign_mln, 1),
        "symbols": {},
    }

    for ticker in active_tickers:
        sector = TICKER_SECTOR.get(ticker, "diger")
        sec_mom = 0.0
        if sector in sector_mom:
            sec_mom = sector_mom[sector].get("momentum_5", 0)

        sym_data = {
            "ml_score": ml_scores.get(ticker, {}).get("ml_score", 0.5),
            "ml_confidence": ml_scores.get(ticker, {}).get("ml_confidence", 0.0),
            "sector": sector,
            "sector_momentum": round(float(sec_mom), 2),
            "signal": ml_scores.get(ticker, {}).get("signal", "hold"),
            "overnight_gap_pct": overnight_gap_prediction(usdtry_pct, vix_level, xu100_pct),
        }
        bridge["symbols"][ticker] = sym_data

    # ── DOSYAYA YAZ (atomik) ──────────────────────────────────
    output_path = BRIDGE_OUTPUT
    temp_path = str(output_path) + ".tmp"

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(bridge, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, str(output_path))
        log.info(f"Bridge yazildi: {output_path}")
        log.info(f"  Rejim: {bridge['market_regime']} | XU100: {bridge['xu100_change_pct']:+.2f}% | VIX: {bridge['vix_level']}")
    except Exception as e:
        log.error(f"Bridge yazma hatasi: {e}")
        # Temp dosya kaldiysa temizle
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return bridge


# ================================================================
# MOTOR_V3 ENTEGRASYONU
# ================================================================

def bridge_loop(active_tickers=None, interval_sec=60):
    """
    Surekli calis, her interval_sec saniyede bridge guncelle.
    motor_v3.py icinden thread olarak cagrilabilir.
    """
    log.info(f"Bridge dongusu baslatildi — her {interval_sec}sn")
    while True:
        try:
            generate_bridge(active_tickers)
        except Exception as e:
            log.error(f"Bridge dongusu hatasi: {e}")
        time.sleep(interval_sec)


# ================================================================
# CLI
# ================================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="V3 Bridge Writer")
    parser.add_argument("--tickers", default="AYEN,KONTR,EREGL,SASA,GESAN",
                        help="Virgul ayrimli ticker listesi")
    parser.add_argument("--loop", action="store_true",
                        help="Surekli calis (60sn aralikla)")
    parser.add_argument("--interval", type=int, default=60,
                        help="Guncelleme araligi (saniye)")
    parser.add_argument("--output", default=None,
                        help="Cikti dosya yolu (varsayilan: platform'a gore)")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers.split(",")]

    if args.output:
        BRIDGE_OUTPUT = Path(args.output)

    if args.loop:
        bridge_loop(tickers, args.interval)
    else:
        result = generate_bridge(tickers)
        print(json.dumps(result, indent=2, ensure_ascii=False))
