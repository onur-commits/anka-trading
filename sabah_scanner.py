"""
BIST Sabah Scanner v2 - Her gün 09:00'da çalışır
Tüm BIST100 hisselerini tarar, en iyi 5'i seçer
Teknik + ML çift onay sistemi
Sonuçları data/sabah_secim.json'a yazar
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from tahmin_motoru import feature_olustur, hisse_analiz, model_yukle, model_egit

# ─────────────────────────────────────────────
# BIST100 Hisse Evreni
# ─────────────────────────────────────────────
BIST100 = [
    "GARAN", "THYAO", "ASELS", "EREGL", "KRDMD",
    "PETKM", "SASA",  "AKBNK", "ISCTR", "KCHOL",
    "TUPRS", "TCELL", "BIMAS", "FROTO", "TOASO",
    "SAHOL", "KOZAL", "ARCLK", "ENKAI", "SISE",
    "EKGYO", "TTKOM", "DOHOL", "VESTL", "TAVHL",
    "PGSUS", "SOKM",  "ULKER", "AGHOL", "GUBRF",
    "KONTR", "ODAS",  "AKSEN", "ZOREN", "KCAER",
    "MAVI",  "LOGO",  "ALARK", "NETAS", "CIMSA",
    "OYAKC", "MGROS", "BRYAT", "YKBNK", "HALKB",
    "VAKBN", "TSKB",  "ALBRK", "ENJSA", "INDES",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "sabah_secim.json")
LOG_FILE = os.path.join(DATA_DIR, "scanner_log.txt")

# ─────────────────────────────────────────────
# Teknik Analiz Fonksiyonları
# ─────────────────────────────────────────────

def ema(seri, period):
    return seri.ewm(span=period, adjust=False).mean()

def rsi(seri, period=14):
    delta = seri.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def hisse_puanla(sembol):
    """Hisseyi indir ve 0-100 arasında puanla"""
    try:
        ticker = sembol + ".IS"
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)

        if df is None or len(df) < 30:
            return None

        close = df["Close"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()
        volume = df["Volume"].squeeze()

        if close.iloc[-1] < 2:  # Çok ucuz hisseleri atla
            return None

        # ── Göstergeler ──────────────────────────────
        ema8  = ema(close, 8)
        ema21 = ema(close, 21)
        ema50 = ema(close, 50)
        rsi14 = rsi(close, 14)
        atr14 = atr(high, low, close, 14)
        vol_ma20 = volume.rolling(20).mean()

        son_fiyat   = float(close.iloc[-1])
        son_ema8    = float(ema8.iloc[-1])
        son_ema21   = float(ema21.iloc[-1])
        son_ema50   = float(ema50.iloc[-1])
        son_rsi     = float(rsi14.iloc[-1])
        son_atr     = float(atr14.iloc[-1])
        son_hacim   = float(volume.iloc[-1])
        ort_hacim   = float(vol_ma20.iloc[-1])

        # ── Puan Hesaplama ────────────────────────────
        puan = 0
        detay = {}

        # 1. EMA Trendi (0-25 puan)
        if son_ema8 > son_ema21 > son_ema50:
            p = 25  # Güçlü yükselen trend
        elif son_ema8 > son_ema21:
            p = 15  # Kısa vadeli trend yukarı
        elif son_ema8 > son_ema50:
            p = 8
        else:
            p = 0
        puan += p
        detay["ema_trend"] = p

        # 2. Trend Gücü - EMA ayrışması (0-15 puan)
        trend_guc = abs(son_ema8 - son_ema21) / son_ema21 * 100 if son_ema21 > 0 else 0
        p = min(15, trend_guc * 30)
        puan += p
        detay["trend_guc"] = round(p, 1)

        # 3. RSI Momentum (0-20 puan)
        if 55 <= son_rsi <= 75:
            p = 20  # İdeal momentum bölgesi
        elif 50 <= son_rsi < 55:
            p = 12
        elif 45 <= son_rsi < 50:
            p = 6
        elif son_rsi > 75:
            p = 5   # Aşırı alım, dikkat
        else:
            p = 0
        puan += p
        detay["rsi"] = round(son_rsi, 1)
        detay["rsi_puan"] = p

        # 4. Hacim Gücü (0-20 puan)
        if ort_hacim > 0:
            hacim_oran = son_hacim / ort_hacim
            p = min(20, hacim_oran * 10)
        else:
            p = 0
        puan += p
        detay["hacim_oran"] = round(son_hacim / ort_hacim if ort_hacim > 0 else 0, 2)
        detay["hacim_puan"] = round(p, 1)

        # 5. Kısa Vadeli Momentum - 5 günlük getiri (0-10 puan)
        if len(close) >= 6:
            getiri_5g = (son_fiyat - float(close.iloc[-6])) / float(close.iloc[-6]) * 100
            if 1 <= getiri_5g <= 8:
                p = 10  # İyi momentum, aşırı değil
            elif 0 <= getiri_5g < 1:
                p = 6
            elif getiri_5g > 8:
                p = 3   # Çok yükseldi, riskli
            else:
                p = 0
        else:
            p = 0
            getiri_5g = 0
        puan += p
        detay["getiri_5g"] = round(getiri_5g, 2)

        # 6. 52 Hafta Pozisyonu (0-10 puan)
        yillik_max = float(close.rolling(252).max().iloc[-1]) if len(close) >= 30 else float(close.max())
        yillik_min = float(close.rolling(252).min().iloc[-1]) if len(close) >= 30 else float(close.min())
        yillik_aralik = yillik_max - yillik_min
        if yillik_aralik > 0:
            pozisyon = (son_fiyat - yillik_min) / yillik_aralik
            # %40-75 arası en iyi: ne dip ne de zirve
            if 0.40 <= pozisyon <= 0.75:
                p = 10
            elif 0.25 <= pozisyon < 0.40:
                p = 7
            elif 0.75 < pozisyon <= 0.90:
                p = 5
            else:
                p = 2
        else:
            p = 5
            pozisyon = 0.5
        puan += p
        detay["yillik_pozisyon"] = round(pozisyon * 100, 1)

        # ── Sonuç ─────────────────────────────────────
        return {
            "sembol": sembol,
            "fiyat": round(son_fiyat, 2),
            "puan": round(puan, 1),
            "rsi": round(son_rsi, 1),
            "ema8": round(son_ema8, 2),
            "ema21": round(son_ema21, 2),
            "trend_yukari": son_ema8 > son_ema21,
            "hacim_oran": round(son_hacim / ort_hacim if ort_hacim > 0 else 0, 2),
            "getiri_5g": round(getiri_5g, 2),
            "yillik_poz": round(pozisyon * 100, 1),
            "detay": detay,
        }

    except Exception as e:
        return None


def tarama_yap(top_n=5, ml_esik=0.55):
    """Tüm hisseleri tara, en iyi N'i seç — Teknik + ML çift onay"""
    os.makedirs(DATA_DIR, exist_ok=True)

    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔍 BIST Scanner v2 başladı — {zaman}")
    print(f"📊 {len(BIST100)} hisse taranıyor...\n")

    # ML modelini yükle
    ml_model = model_yukle()
    if ml_model:
        print("🤖 ML modeli yüklendi!\n")
    else:
        print("⚠️  ML modeli bulunamadı, sadece teknik analiz kullanılacak\n")

    # Tüm veriyi indirip analiz et
    tum_df = {}
    sonuclar = []

    for i, sembol in enumerate(BIST100):
        print(f"  [{i+1:02d}/{len(BIST100)}] {sembol}...", end=" ", flush=True)
        try:
            ticker = sembol + ".IS"
            df = yf.download(ticker, period="1y", interval="1d",
                             progress=False, auto_adjust=True)

            if df is None or len(df) < 60:
                print("⚪ atlandı (veri yetersiz)")
                continue

            # Temizle
            df = df.dropna()
            if float(df["Close"].squeeze().iloc[-1]) < 2:
                print("⚪ atlandı (fiyat çok düşük)")
                continue

            tum_df[sembol] = df

            # Teknik + ML analiz
            analiz = hisse_analiz(sembol, df, ml_model)
            if analiz is None:
                print("⚪ atlandı (analiz başarısız)")
                continue

            # Trend kontrolü
            close = df["Close"].squeeze()
            ema8  = close.ewm(span=8, adjust=False).mean()
            ema21 = close.ewm(span=21, adjust=False).mean()
            trend_yukari = float(ema8.iloc[-1]) > float(ema21.iloc[-1])

            getiri_5g = float(close.pct_change(5).iloc[-1] * 100) if len(close) >= 6 else 0

            sonuc = {
                "sembol": sembol,
                "fiyat": analiz["fiyat"],
                "teknik_puan": analiz["teknik_skor"],
                "ml_olasilik": analiz["ml_olasilik"],
                "birlesik_puan": analiz["birlesik_skor"],
                "rsi": analiz["features"].get("rsi", 50),
                "adx": analiz["adx"],
                "obv_trend": analiz["obv_trend"],
                "trend_yukari": trend_yukari,
                "getiri_5g": round(getiri_5g, 2),
                "hacim_oran": analiz["features"].get("hacim_oran", 1.0),
                "yillik_poz": analiz["yillik_poz"],
                "sinyaller": analiz["sinyaller"],
            }
            sonuclar.append(sonuc)

            ml_str = f"ML:{analiz['ml_olasilik']:.2f}" if analiz["ml_olasilik"] else "ML:?"
            emoji = "🟢" if trend_yukari else "🔴"
            print(f"{emoji} Teknik:{analiz['teknik_skor']:.0f} | {ml_str} | "
                  f"Birleşik:{analiz['birlesik_skor']:.0f} | 5g:{getiri_5g:+.1f}%")

        except Exception as e:
            print(f"⚪ hata: {str(e)[:40]}")

    # ── Seçim Mantığı ──────────────────────────────────────────
    # Öncelik 1: Trend yukarı + ML yüksek
    ml_onaylilar = [s for s in sonuclar
                    if s["trend_yukari"]
                    and s["ml_olasilik"] is not None
                    and s["ml_olasilik"] >= ml_esik]

    # Öncelik 2: Sadece teknik (ML yoksa)
    sadece_teknik = [s for s in sonuclar
                     if s["trend_yukari"]
                     and (s["ml_olasilik"] is None or s["ml_olasilik"] < ml_esik)]

    # Birleşik puana göre sırala
    ml_onaylilar.sort(key=lambda x: x["birlesik_puan"], reverse=True)
    sadece_teknik.sort(key=lambda x: x["teknik_puan"], reverse=True)

    # ML onaylıları önce al, eksik kalan yerleri teknik ile doldur
    secilen = ml_onaylilar[:top_n]
    if len(secilen) < top_n:
        kalan = top_n - len(secilen)
        secilen += sadece_teknik[:kalan]

    # Yine de boşsa tüm listeden al
    if not secilen:
        tum_sirali = sorted(sonuclar, key=lambda x: x["birlesik_puan"], reverse=True)
        secilen = tum_sirali[:top_n]

    # ── Kaydet ────────────────────────────────────────────────
    tum_sirali = sorted(sonuclar, key=lambda x: x["birlesik_puan"], reverse=True)
    cikti = {
        "tarama_zamani": zaman,
        "taranan_hisse": len(sonuclar),
        "ml_aktif": ml_model is not None,
        "ml_esik": ml_esik,
        "secilen_hisseler": secilen,
        "tum_siralama": tum_sirali[:20],
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=2, default=str)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*55}\n")
        f.write(f"Tarama: {zaman} | ML: {'aktif' if ml_model else 'pasif'}\n")
        f.write(f"Taranan: {len(sonuclar)} hisse\n")
        f.write("Seçilenler:\n")
        for s in secilen:
            ml_str = f"ML:{s['ml_olasilik']:.2f}" if s["ml_olasilik"] else "ML:?"
            f.write(f"  {s['sembol']:8s} Birleşik:{s['birlesik_puan']:5.1f} "
                    f"Teknik:{s['teknik_puan']:5.1f} {ml_str} "
                    f"5g:{s['getiri_5g']:+5.1f}%\n")

    # ── Sonuç Ekrana ──────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"✅ Tarama tamamlandı! ML: {'🤖 Aktif' if ml_model else '⚠️  Pasif'}")
    print(f"{'='*55}")
    print(f"\n🏆 EN İYİ {top_n} HİSSE (Çift Onay):\n")
    for i, s in enumerate(secilen, 1):
        ml_str = f"ML:{s['ml_olasilik']:.0%}" if s["ml_olasilik"] else "ML:N/A"
        onay = "🤖✅" if (s["ml_olasilik"] and s["ml_olasilik"] >= ml_esik) else "📊"
        print(f"  {i}. {onay} {s['sembol']:6s} | "
              f"Birleşik:{s['birlesik_puan']:5.1f} | "
              f"Teknik:{s['teknik_puan']:5.1f} | {ml_str} | "
              f"Fiyat:{s['fiyat']:8.2f}TL | 5g:{s['getiri_5g']:+.1f}%")

    print(f"\n📁 Sonuçlar: {OUTPUT_FILE}")
    print(f"⚡ Bu hisseleri Matriks IQ'ya ekle: MaxPositionValue = 10000 TL\n")

    return secilen, tum_df


if __name__ == "__main__":
    import sys

    # Argüman: --egit → modeli yeniden eğit
    if "--egit" in sys.argv:
        print("🎓 Model eğitimi başlıyor...")
        _, tum_veri = tarama_yap(top_n=5)
        if tum_veri:
            sonuc = model_egit(tum_veri)
            if sonuc:
                print(f"\n✅ Model eğitildi!")
                print(f"   Doğruluk  : %{sonuc['dogruluk']*100:.1f}")
                print(f"   F1 Skoru  : {sonuc['f1']:.3f}")
                print(f"   Precision : {sonuc['precision']:.3f}")
                print(f"   Eğitim    : {sonuc['egitim_boyut']:,} satır")
                if sonuc.get("walk_forward"):
                    wf = sonuc["walk_forward"]
                    ort_f1 = np.mean([s["f1"] for s in wf])
                    print(f"   WF Ort F1 : {ort_f1:.3f} ({len(wf)} fold)")
                print(f"\n   🥇 En önemli özellikler:")
                for feat, imp in list(sonuc["top_features"].items())[:5]:
                    print(f"      {feat:25s}: {imp:.4f}")
    else:
        secilen, _ = tarama_yap(top_n=5)
