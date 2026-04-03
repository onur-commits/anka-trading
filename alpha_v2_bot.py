"""
BIST ALPHA V2 — Ana Bot Orkestratörü
======================================
Tüm modülleri birleştirir:
- ML Ensemble (XGBoost + LightGBM + MLP)
- Haber Sentiment (Türkçe NLP)
- Risk Yönetimi (ATR + Kelly + Drawdown)
- Market Rejim Tespiti
- Sektör Momentum
- Bildirim Sistemi

Kullanım:
  python alpha_v2_bot.py --tek        # Tek tarama
  python alpha_v2_bot.py --bot        # Sürekli bot modu
  python alpha_v2_bot.py --egit       # Model yeniden eğit
"""

import sys
import json
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))

from tahmin_motoru_v2 import (
    EnsembleModelV2, feature_olustur_v2, market_rejim_tespit,
    sektor_momentum_hesapla, hisse_analiz_v2, teknik_skor_v2,
    atr_hesapla, FEATURE_COLS_V2,
)
from risk_yonetimi import RiskYoneticisi
from haber_sentiment import haberleri_analiz_et, hisse_sentiment_al

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ============================================================
# BIST HISSE EVRENİ
# ============================================================

TICKERS = [
    "THYAO.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS", "SAHOL.IS",
    "BIMAS.IS", "TUPRS.IS", "KCHOL.IS", "ISCTR.IS", "YKBNK.IS",
    "SISE.IS", "TOASO.IS", "ASELS.IS", "HALKB.IS", "VAKBN.IS",
    "PGSUS.IS", "MGROS.IS", "SOKM.IS", "TAVHL.IS", "AKSEN.IS",
    "ODAS.IS", "LOGO.IS", "NETAS.IS", "TCELL.IS", "ENKAI.IS",
    "PETKM.IS", "DOHOL.IS", "TTKOM.IS", "EKGYO.IS", "FROTO.IS",
    "GUBRF.IS", "HEKTS.IS", "ISGYO.IS", "KORDS.IS", "OTKAR.IS",
    "TKFEN.IS", "TTRAK.IS", "VESTL.IS", "AEFES.IS", "ARCLK.IS",
    "CIMSA.IS", "EGEEN.IS", "ENJSA.IS", "GESAN.IS", "KONTR.IS",
    "MPARK.IS", "SASA.IS", "ULKER.IS",
]


# ============================================================
# VERİ ÇEKME
# ============================================================

def veri_cek(period="1y"):
    """BIST verilerini çeker."""
    print(f"📥 {len(TICKERS)} hisse verisi çekiliyor ({period})...")
    veri = {}
    for t in TICKERS:
        try:
            df = yf.download(t, period=period, progress=False)
            if len(df) >= 120:
                veri[t] = df
        except Exception:
            pass

    # XU100
    xu = yf.download("XU100.IS", period=period, progress=False)
    if len(xu) > 50:
        veri["XU100.IS"] = xu

    print(f"   ✅ {len(veri)} hisse yüklendi")
    return veri


# ============================================================
# TAM TARAMA
# ============================================================

def tam_tarama(veri, model, risk, rejim_info, sentiment_data):
    """Tüm hisseleri tarar, sinyalleri döndürür."""
    sonuclar = []

    for ticker, df in veri.items():
        if ticker == "XU100.IS":
            continue

        try:
            analiz = hisse_analiz_v2(ticker, df, model, rejim_info)
            if analiz is None:
                continue

            # Sentiment ekle
            ticker_temiz = ticker.replace(".IS", "")
            hisse_sent = sentiment_data.get("hisse_sentiments", {}).get(ticker_temiz)
            if hisse_sent:
                analiz["sentiment"] = hisse_sent["skor"]
                # Sentiment'i birleşik skora ekle (%10 ağırlık)
                analiz["birlesik_skor"] = analiz["birlesik_skor"] * 0.9 + (hisse_sent["skor"] + 1) / 2 * 100 * 0.1
            else:
                analiz["sentiment"] = 0

            # ATR hesapla
            close = df["Close"].squeeze()
            high = df["High"].squeeze()
            low = df["Low"].squeeze()
            atr = atr_hesapla(high, low, close)
            analiz["atr"] = float(atr.iloc[-1])

            # Risk değerlendirmesi
            risk_degerlendirme = risk.sinyal_degerlendir(
                ticker=ticker,
                fiyat=analiz["fiyat"],
                atr=analiz["atr"],
                ml_olasilik=analiz.get("ml_olasilik"),
                teknik_skor=analiz["teknik_skor"],
                rejim_info=rejim_info,
            )
            analiz["risk"] = risk_degerlendirme

            sonuclar.append(analiz)

        except Exception as e:
            continue

    # Sırala
    sonuclar.sort(key=lambda x: x["birlesik_skor"], reverse=True)
    return sonuclar


# ============================================================
# RAPOR
# ============================================================

def rapor_yazdir(sonuclar, rejim, sektor_mom, sentiment, risk):
    """Terminale güzel formatlanmış rapor."""
    print()
    print("═" * 70)
    print(f"   🏆 BIST ALPHA V2 — TARAMA RAPORU")
    print(f"   📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 70)

    # Piyasa durumu
    if rejim:
        r = rejim["rejim"].upper()
        emoji = "🐂" if r == "BULL" else "🐻" if r == "BEAR" else "↔️"
        print(f"\n   {emoji} Piyasa: {r} | ADX: {rejim['adx']} | Vol: {rejim['volatilite']}%")

    # Sentiment
    if sentiment:
        s = sentiment.get("genel_sentiment", 0)
        s_emoji = "🟢" if s > 0.1 else "🔴" if s < -0.1 else "⚪"
        print(f"   {s_emoji} Haber Sentiment: {s:+.3f} ({sentiment.get('haber_sayisi', 0)} haber)")

    # Sektör
    if sektor_mom:
        print(f"\n   📊 Sektör Momentum (5g):")
        for s, m in sorted(sektor_mom.items(), key=lambda x: x[1]["mom_5"], reverse=True):
            emoji = "🟢" if m["mom_5"] > 1 else "🔴" if m["mom_5"] < -1 else "⚪"
            print(f"      {emoji} {s:12s} {m['mom_5']:+.1f}%")

    # İşleme uygun sinyaller
    islem_sinyalleri = [s for s in sonuclar if s.get("risk", {}).get("islem")]
    bekle_sinyalleri = [s for s in sonuclar if not s.get("risk", {}).get("islem")]

    if islem_sinyalleri:
        print(f"\n   🎯 İŞLEM SİNYALLERİ ({len(islem_sinyalleri)}):")
        print(f"   {'Hisse':8s} {'Skor':>6s} {'ML':>6s} {'Teknik':>7s} {'Sent':>5s} {'ATR%':>6s} {'Lot':>5s} {'Stop%':>6s} {'Sinyaller'}")
        print("   " + "─" * 65)
        for s in islem_sinyalleri[:10]:
            r = s["risk"]
            sinyaller = " ".join(s.get("sinyal_ozet", [])[:3])
            print(f"   {s['ticker']:8s} {s['birlesik_skor']:6.1f} {(s.get('ml_olasilik') or 0)*100:5.1f}% {s['teknik_skor']:6.1f} {s.get('sentiment', 0):+.2f} {s.get('atr_pct', 0):5.2f}% {r.get('lot', 0):5d} {r.get('stop_pct', 0):5.2f}% {sinyaller}")

    # Bekle sinyalleri (top 5)
    if bekle_sinyalleri:
        print(f"\n   ⏳ BEKLE ({len(bekle_sinyalleri)} hisse — top 5):")
        for s in bekle_sinyalleri[:5]:
            sebep = s.get("risk", {}).get("sebep", "")[:40]
            print(f"      {s['ticker']:8s} Skor: {s['birlesik_skor']:5.1f} → {sebep}")

    # Risk durumu
    dd = risk.drawdown_kontrol()
    print(f"\n   💰 Sermaye: {risk.sermaye:,.0f} TL | DD: %{dd['drawdown_pct']:.1f} | Durum: {dd['durum']}")
    print(f"   📊 Aktif pozisyon: {len(risk.aktif_pozisyonlar)}/{risk.max_pozisyon}")

    print("═" * 70)
    return islem_sinyalleri


def sonuc_kaydet(sonuclar, rejim, sentiment):
    """Tarama sonuçlarını JSON'a kaydet."""
    path = DATA_DIR / "alpha_v2_sonuc.json"
    kayit = {
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rejim": rejim,
        "sentiment_genel": sentiment.get("genel_sentiment", 0) if sentiment else 0,
        "islem_sinyalleri": [
            {
                "ticker": s["ticker"],
                "birlesik_skor": s["birlesik_skor"],
                "ml_olasilik": s.get("ml_olasilik"),
                "teknik_skor": s["teknik_skor"],
                "sentiment": s.get("sentiment", 0),
                "fiyat": s["fiyat"],
                "risk": {
                    "islem": s["risk"]["islem"],
                    "lot": s["risk"].get("lot", 0),
                    "stop_loss": s["risk"].get("stop_loss", 0),
                    "take_profit": s["risk"].get("take_profit", 0),
                } if "risk" in s else {},
                "sinyal_ozet": s.get("sinyal_ozet", []),
            }
            for s in sonuclar[:20]
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=2, default=str)


# ============================================================
# ANA FONKSİYONLAR
# ============================================================

def tek_tarama(sermaye=100_000):
    """Tek seferlik tam tarama."""
    print("🚀 BIST ALPHA V2 — Tek Tarama")
    print()

    # 1. Model yükle
    model = EnsembleModelV2.yukle()
    if model is None:
        print("⚠️  Model bulunamadı, eğitim başlatılıyor...")
        model = EnsembleModelV2()
        veri = veri_cek("2y")
        model.egit(veri)
    else:
        print("✅ Ensemble V2 model yüklendi")

    # 2. Güncel veri çek
    veri = veri_cek("1y")

    # 3. Market rejim
    rejim = None
    if "XU100.IS" in veri:
        rejim = market_rejim_tespit(veri["XU100.IS"])

    # 4. Sektör momentum
    sektor_mom = sektor_momentum_hesapla(veri)

    # 5. Haber sentiment
    print("📰 Haber sentiment analizi...")
    sentiment = haberleri_analiz_et()

    # 6. Risk yöneticisi
    risk = RiskYoneticisi(sermaye=sermaye)
    if rejim:
        risk.rejim_risk_ayari(rejim)

    # 7. Tam tarama
    print("🔍 Tarama başlıyor...")
    sonuclar = tam_tarama(veri, model, risk, rejim, sentiment)

    # 8. Rapor
    sinyaller = rapor_yazdir(sonuclar, rejim, sektor_mom, sentiment, risk)

    # 9. Kaydet
    sonuc_kaydet(sonuclar, rejim, sentiment)
    print(f"\n💾 Sonuçlar kaydedildi: data/alpha_v2_sonuc.json")

    return sonuclar


def model_egit_komut():
    """Modeli yeniden eğitir."""
    print("🧠 BIST ALPHA V2 — Model Eğitimi")
    print()
    veri = veri_cek("2y")

    rejim = None
    if "XU100.IS" in veri:
        rejim = market_rejim_tespit(veri["XU100.IS"])

    model = EnsembleModelV2()
    meta = model.egit(veri, market_rejim=rejim)

    if meta:
        print(f"\n✅ Model eğitildi — AUC: {meta['ensemble_auc']}")
    else:
        print("❌ Eğitim başarısız")


def bot_modu(sermaye=100_000, aralik_dk=15):
    """Sürekli çalışan bot modu."""
    print("🤖 BIST ALPHA V2 — Bot Modu")
    print(f"   Tarama aralığı: {aralik_dk} dakika")
    print(f"   Sermaye: {sermaye:,.0f} TL")
    print()

    while True:
        saat = datetime.now()

        # Sadece piyasa saatleri (09:30 - 18:00)
        if saat.weekday() < 5 and 9 <= saat.hour < 18:
            try:
                tek_tarama(sermaye)
            except Exception as e:
                print(f"❌ Hata: {e}")

            print(f"\n⏳ Sonraki tarama: {aralik_dk} dakika sonra")
        else:
            print(f"💤 Piyasa kapalı — {saat.strftime('%H:%M')}")

        time.sleep(aralik_dk * 60)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if "--egit" in sys.argv:
        model_egit_komut()
    elif "--bot" in sys.argv:
        sermaye = 100_000
        for i, arg in enumerate(sys.argv):
            if arg == "--sermaye" and i + 1 < len(sys.argv):
                sermaye = float(sys.argv[i + 1])
        bot_modu(sermaye=sermaye)
    else:
        tek_tarama()
