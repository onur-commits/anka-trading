"""
BIST ALPHA V2 — Günlük Bomba Hisse Bulucu + IQ Robot Üretici
==============================================================
Her sabah 09:00'da:
1. Tüm BIST hisselerini tarar
2. ML + Teknik + Sentiment ile bomba adaylarını bulur
3. Bulunan hisseler için otomatik IQ C# kodu üretir
4. Kodları Windows'a kopyalar, panoya hazırlar

Kullanım:
  python gunluk_bomba.py              # Tam tarama + IQ kodu üret
  python gunluk_bomba.py --sadece-tara # Sadece tarama, kod üretme
  python gunluk_bomba.py --deploy      # Üretilen kodları Windows'a kopyala
"""

import sys
import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))

from tahmin_motoru_v2 import (
    EnsembleModelV2, feature_olustur_v2, market_rejim_tespit,
    sektor_momentum_hesapla, hisse_analiz_v2, atr_hesapla,
)
from haber_sentiment import haberleri_analiz_et

DATA_DIR = Path(__file__).parent / "data"
IQ_DIR = Path(__file__).parent / "matriks_iq"
DATA_DIR.mkdir(exist_ok=True)

# ============================================================
# GENIŞ BIST EVRENİ — 80+ hisse
# ============================================================

TICKERS = [
    # Bankalar
    "GARAN.IS", "AKBNK.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS",
    "TSKB.IS", "ALBRK.IS",
    # Holdingler
    "SAHOL.IS", "KCHOL.IS", "TAVHL.IS", "DOHOL.IS",
    # Sanayi
    "EREGL.IS", "TOASO.IS", "TUPRS.IS", "SISE.IS", "FROTO.IS", "OTKAR.IS",
    "TTRAK.IS", "KORDS.IS", "BRISA.IS", "CIMSA.IS", "EGEEN.IS",
    # Enerji
    "AKSEN.IS", "ODAS.IS", "ENJSA.IS", "AYEN.IS",
    # Teknoloji
    "ASELS.IS", "LOGO.IS", "NETAS.IS",
    # Perakende
    "BIMAS.IS", "MGROS.IS", "SOKM.IS",
    # Havayolu / Turizm
    "THYAO.IS", "PGSUS.IS",
    # Telekom
    "TCELL.IS", "TTKOM.IS",
    # İnşaat / GYO
    "ENKAI.IS", "EKGYO.IS", "ISGYO.IS",
    # Kimya / Gübre
    "PETKM.IS", "GUBRF.IS", "HEKTS.IS", "SASA.IS",
    # Gıda
    "ULKER.IS", "AEFES.IS",
    # Savunma
    "ASELS.IS",
    # Diğer
    "TKFEN.IS", "VESTL.IS", "ARCLK.IS", "GESAN.IS", "KONTR.IS",
    "MPARK.IS", "KOZAL.IS", "KOZAA.IS",
]
# Tekrarları kaldır
TICKERS = list(dict.fromkeys(TICKERS))


# ============================================================
# BOMBA SKOR HESAPLAMA
# ============================================================

def bomba_skor_hesapla(analiz, features):
    """
    Çok yönlü bomba skoru — 0-100 arası.
    ML + Teknik + Momentum + Hacim + Rejim uyumu.
    """
    # --- Guard: pandas Series/ndarray değerleri scalar'a indir ---
    # yfinance MultiIndex / squeeze edilmemiş DataFrame'den gelen Series'leri safelık
    try:
        import pandas as _pd
        import numpy as _np
        def _scalar(v, default=0):
            if v is None:
                return default
            if isinstance(v, (_pd.Series, _np.ndarray)):
                try:
                    return float(v.iloc[-1]) if hasattr(v, "iloc") else float(v[-1])
                except Exception:
                    try:
                        return float(v.item()) if hasattr(v, "item") else default
                    except Exception:
                        return default
            try:
                return float(v)
            except Exception:
                return default
        if isinstance(features, dict):
            features = {k: _scalar(v) for k, v in features.items()}
        if isinstance(analiz, dict):
            for k, v in list(analiz.items()):
                if isinstance(v, (_pd.Series, _np.ndarray)):
                    analiz[k] = _scalar(v)
    except Exception:
        pass
    # ---

    skor = 0
    sebepler = []

    # 1. ML Olasılığı (0-25 puan)
    ml = analiz.get("ml_olasilik") or 0
    if ml >= 0.70:
        skor += 25
        sebepler.append(f"🧠 ML:{ml*100:.0f}% GÜÇLÜ")
    elif ml >= 0.60:
        skor += 18
        sebepler.append(f"🧠 ML:{ml*100:.0f}%")
    elif ml >= 0.50:
        skor += 10
        sebepler.append(f"🧠 ML:{ml*100:.0f}%")

    # 2. RSI Aşırı Satım Bounce (0-15 puan)
    rsi7 = features.get("rsi_7", 50)
    if rsi7 < 20:
        skor += 15
        sebepler.append(f"⬇️ RSI7:{rsi7:.0f} AŞIRI SATIM")
    elif rsi7 < 35:
        skor += 8
        sebepler.append(f"⬇️ RSI7:{rsi7:.0f}")

    # 3. Bollinger Sıkışma / Alt Band (0-10 puan)
    boll = features.get("boll_poz", 0.5)
    sikisma = features.get("boll_sikisma", 0)
    if sikisma:
        skor += 10
        sebepler.append("🔥 SIKIŞMA")
    elif boll < 0.1:
        skor += 8
        sebepler.append("📉 Boll ALT BAND")

    # 4. Hacim Anomali (0-10 puan)
    rvol = features.get("rvol", 1)
    hacim_spike = features.get("hacim_spike", 0)
    if hacim_spike:
        skor += 10
        sebepler.append("📊 HACİM PATLAMA")
    elif rvol > 1.5:
        skor += 5
        sebepler.append(f"📊 Hacim x{rvol:.1f}")

    # 5. OBV Birikim / Kurumsal Alım (0-10 puan)
    obv = features.get("obv_trend", 0)
    if obv > 0.15:
        skor += 10
        sebepler.append("🏦 KURUMSAL ALIM")
    elif obv > 0.05:
        skor += 5

    # 6. Momentum İvme Dönüşü (0-10 puan)
    accel = features.get("mom_accel", 0)
    if accel > 2:
        skor += 10
        sebepler.append("🚀 İVME DÖNÜŞÜ")
    elif accel > 0.5:
        skor += 5

    # 7. MA Alignment — Trend Kalitesi (0-10 puan)
    ma = features.get("ma_alignment", 0)
    if ma == 3:
        skor += 10
        sebepler.append("✨ TAM TREND")
    elif ma == 2:
        skor += 5

    # 8. Volatilite Sıkışma (0-5 puan)
    vol_ratio = features.get("vol_ratio", 1)
    if vol_ratio < 0.7:
        skor += 5
        sebepler.append("💎 VOL SIKIŞMA")

    # 9. Hammer / Doji Mum (0-5 puan)
    if features.get("hammer", 0):
        skor += 5
        sebepler.append("🔨 HAMMER")
    elif features.get("doji", 0):
        skor += 3

    return min(100, skor), sebepler


def hibrit_bomba_kontrol(df, ml_score):
    """
    VETO SİSTEMİ — ML 'evet' dese bile teknik onaylamazsa listeye almaz.
    3 katman hepsi 'evet' demeli:
      1. ML skoru >= 0.75 (model güveniyor)
      2. Hacim >= ortalamanın 1.8 katı (kurumsal ilgi)
      3. Kapanış >= günün en yükseğinin %98.5'i (alıcılar baskın)
    """
    # ml_score Series ise scalar'a indir
    try:
        import pandas as _pd
        if isinstance(ml_score, _pd.Series):
            ml_score = float(ml_score.iloc[-1])
        else:
            ml_score = float(ml_score)
    except Exception:
        ml_score = 0.0

    # 1. ML Katmanı
    ml_onay = ml_score >= 0.75

    # yfinance MultiIndex guard — tek ticker olduğunda squeeze Series'e düşürür
    try:
        vol = df['Volume'].squeeze()
        close = df['Close'].squeeze()
        high = df['High'].squeeze()
    except Exception:
        vol = df['Volume']
        close = df['Close']
        high = df['High']

    # 2. Hacim Katmanı
    avg_vol = vol.rolling(20).mean().iloc[-1]
    curr_vol = vol.iloc[-1]
    hacim_onay = float(curr_vol) > (float(avg_vol) * 1.8)

    # 3. Kapanış Gücü Katmanı
    kapanis_onay = float(close.iloc[-1]) > (float(high.iloc[-1]) * 0.985)

    # BİRLEŞİK KARAR — hepsi onaylamalı
    return ml_onay and hacim_onay and kapanis_onay


# ============================================================
# IQ C# KODU ÜRETİCİ
# ============================================================

IQ_TEMPLATE = '''using System;
using Matriks.Data.Symbol;
using Matriks.Engines;
using Matriks.Indicators;
using Matriks.Symbols;
using Matriks.Trader.Core;
using Matriks.Trader.Core.Fields;
using Matriks.Trader.Core.TraderModels;
using Matriks.Lean.Algotrader.AlgoBase;
using Matriks.Lean.Algotrader.Models;
using Matriks.Lean.Algotrader.Trading;
using Matriks.Data.Tick;
using Matriks.Enumeration;
using Newtonsoft.Json;

namespace Matriks.Lean.Algotrader
{{
    // {tarih} - Bomba Skor: {bomba_skor}/100
    // Sebepler: {sebepler_str}
    public class BOMBA_{ticker} : MatriksAlgo
    {{
        [SymbolParameter("{ticker}")]
        public string Symbol;

        [Parameter(SymbolPeriod.Min60)]
        public SymbolPeriod SymbolPeriod;

        [Parameter({pozisyon})]
        public decimal MaxPositionValue;

        [Parameter(1)]
        public decimal ManualQuantity;

        [Parameter(10)]
        public int FastPeriod;

        [Parameter(20)]
        public int SlowPeriod;

        [Parameter(14)]
        public int RsiPeriod;

        [Parameter(50)]
        public decimal RsiThreshold;

        [Parameter({stop})]
        public decimal StopLossPercent;

        [Parameter(2.5)]
        public decimal TrailingStopPercent;

        MOV fastMov, slowMov;
        RSI rsi;
        bool inPosition = false;
        decimal entryPrice = 0m;
        decimal highestPrice = 0m;
        decimal posQty = 0m;

        [Output] public decimal RSIValue;
        [Output] public decimal PnL;

        public override void OnInit()
        {{
            AddSymbol(Symbol, SymbolPeriod);
            fastMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            slowMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);
            rsi = RSIIndicator(Symbol, SymbolPeriod, OHLCType.Close, RsiPeriod);
            SendOrderSequential(true);
            WorkWithPermanentSignal(true);
        }}

        public override void OnInitCompleted()
        {{
            Debug("BOMBA_{ticker} AKTIF - Skor:{bomba_skor}");
        }}

        public override void OnDataUpdate(BarDataEventArgs barData)
        {{
            if (barData == null || barData.BarData == null) return;
            decimal close = barData.BarData.Close;
            if (close <= 0) return;

            bool emaOk = fastMov.CurrentValue > slowMov.CurrentValue;
            bool rsiOk = rsi.CurrentValue > RsiThreshold;
            RSIValue = Math.Round(rsi.CurrentValue, 2);

            if (inPosition && entryPrice > 0)
            {{
                if (close > highestPrice) highestPrice = close;
                decimal stop = entryPrice * (1 - StopLossPercent / 100m);
                if (highestPrice >= entryPrice * 1.015m)
                {{
                    decimal trail = highestPrice * (1 - TrailingStopPercent / 100m);
                    stop = Math.Max(stop, trail);
                }}
                PnL = Math.Round((close - entryPrice) / entryPrice * 100m, 2);
                if (close <= stop || !emaOk)
                {{
                    SendMarketOrder(Symbol, posQty, OrderSide.Sell);
                    Debug("SATIS: " + posQty + " lot | PnL: %" + PnL);
                }}
            }}
            else
            {{
                if (emaOk && rsiOk)
                {{
                    decimal qty = Math.Floor(MaxPositionValue / close);
                    if (qty < 1) qty = 1;
                    posQty = qty;
                    SendMarketOrder(Symbol, qty, OrderSide.Buy);
                    entryPrice = close;
                    highestPrice = close;
                    Debug("ALIS: " + qty + " lot x " + Math.Round(close, 2) + " TL");
                }}
            }}
        }}

        public override void OnOrderUpdate(IOrder order)
        {{
            if (order == null || order.Symbol != Symbol) return;
            if (order.OrdStatus.Obj == OrdStatus.Filled)
            {{
                if (order.Side.Obj == Side.Buy) inPosition = true;
                if (order.Side.Obj == Side.Sell)
                {{ inPosition = false; entryPrice = 0m; highestPrice = 0m; posQty = 0m; PnL = 0m; }}
            }}
        }}

        public override void OnStopped() {{ }}
    }}
}}'''


def stop_hesapla(atr_pct):
    """ATR bazlı stop yüzdesi."""
    if atr_pct > 5:
        return 8.0
    elif atr_pct > 3:
        return 6.0
    else:
        return 5.0


def iq_kodu_uret(ticker, bomba_skor, sebepler, atr_pct, fiyat):
    """Bir hisse için IQ C# kodu üretir."""
    ticker_temiz = ticker.replace(".IS", "")
    stop = stop_hesapla(atr_pct)

    # Fiyata göre pozisyon: ucuz hisse = 15k, pahalı = 10k
    pozisyon = 15000 if fiyat < 200 else 12000 if fiyat < 500 else 10000

    kod = IQ_TEMPLATE.format(
        ticker=ticker_temiz,
        tarih=datetime.now().strftime("%Y-%m-%d"),
        bomba_skor=bomba_skor,
        sebepler_str=" + ".join(sebepler[:4]),
        pozisyon=pozisyon,
        stop=stop,
    )
    return kod


# ============================================================
# ANA TARAMA
# ============================================================

def gunluk_tarama(top_n=5, min_skor=30):
    """
    Günlük tam tarama:
    1. Veri çek
    2. ML model yükle
    3. Rejim + sentiment analiz
    4. Tüm hisseleri tara
    5. Bomba skoruna göre sırala
    6. Top N için IQ kodu üret
    """
    print("🔥 BIST ALPHA V2 — GÜNLÜK BOMBA TARAMASI")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. Model
    print("\n🧠 ML modeli yükleniyor...")
    model = EnsembleModelV2.yukle()
    if not model:
        print("⚠ Model yok — sadece teknik analiz kullanılacak")

    # 2. Veri
    print(f"\n📥 {len(TICKERS)} hisse verisi çekiliyor...")
    veri = {}
    for t in TICKERS:
        try:
            df = yf.download(t, period="6mo", progress=False)
            if len(df) >= 120:
                veri[t] = df
        except Exception:
            pass

    xu = yf.download("XU100.IS", period="6mo", progress=False)
    print(f"   ✅ {len(veri)} hisse yüklendi")

    # 3. Rejim
    rejim = market_rejim_tespit(xu) if len(xu) > 50 else None
    if rejim:
        emoji = {"bull": "🐂", "bear": "🐻", "sideways": "↔️"}.get(rejim["rejim"], "❓")
        print(f"\n{emoji} Piyasa: {rejim['rejim'].upper()} (ADX:{rejim['adx']}, Vol:{rejim['volatilite']}%)")

    # 4. Sektör
    sektor = sektor_momentum_hesapla(veri)
    print("\n📊 Sektör Momentum:")
    for s, m in sorted(sektor.items(), key=lambda x: x[1]["mom_5"], reverse=True):
        e = "🟢" if m["mom_5"] > 1 else "🔴" if m["mom_5"] < -1 else "⚪"
        print(f"   {e} {s:12s} {m['mom_5']:+.1f}%")

    # 5. Sentiment
    print("\n📰 Haber analizi...")
    sentiment = haberleri_analiz_et()
    s_val = sentiment.get("genel_sentiment", 0) if sentiment else 0
    print(f"   Genel: {s_val:+.3f} ({sentiment.get('haber_sayisi', 0)} haber)")

    # 6. Tarama
    print("\n🔍 Bomba taraması...")
    sonuclar = []

    for ticker, df in veri.items():
        if ticker == "XU100.IS":
            continue
        try:
            analiz = hisse_analiz_v2(ticker, df, model, rejim)
            if analiz is None:
                continue

            features = feature_olustur_v2(df)
            if features is None:
                continue

            son = features.iloc[-1].to_dict()

            # ATR
            close = df["Close"].squeeze()
            high = df["High"].squeeze()
            low = df["Low"].squeeze()
            atr = atr_hesapla(high, low, close)
            atr_pct = float(atr.iloc[-1] / close.iloc[-1] * 100)

            # Bomba skor
            b_skor, b_sebepler = bomba_skor_hesapla(analiz, son)

            # Son performans
            son5g = float((close.iloc[-1] / close.iloc[-5] - 1) * 100) if len(close) > 5 else 0
            son20g = float((close.iloc[-1] / close.iloc[-20] - 1) * 100) if len(close) > 20 else 0

            sonuclar.append({
                "ticker": ticker,
                "bomba_skor": b_skor,
                "sebepler": b_sebepler,
                "ml": analiz.get("ml_olasilik") or 0,
                "teknik": analiz["teknik_skor"],
                "birlesik": analiz["birlesik_skor"],
                "fiyat": analiz["fiyat"],
                "atr_pct": atr_pct,
                "rsi": son.get("rsi_14", 50),
                "ma": son.get("ma_alignment", 0),
                "son5g": son5g,
                "son20g": son20g,
            })
        except Exception:
            continue

    sonuclar.sort(key=lambda x: x["bomba_skor"], reverse=True)

    # 7. Rapor
    print(f"\n{'=' * 60}")
    print(f"💣 GÜNÜN BOMBA HİSSELERİ — Top {top_n}")
    print(f"{'=' * 60}")

    top = [s for s in sonuclar if s["bomba_skor"] >= min_skor][:top_n]

    if not top:
        print("❌ Bugün bomba kriterlerine uyan hisse yok.")
        print("   Piyasa çok durgun veya tüm hisseler düşüşte.")
        return []

    for i, s in enumerate(top):
        t = s["ticker"].replace(".IS", "")
        stop = stop_hesapla(s["atr_pct"])
        hedef1 = s["fiyat"] * (1 + s["atr_pct"] / 100 * 2)
        hedef2 = s["fiyat"] * (1 + s["atr_pct"] / 100 * 3.5)

        print(f"\n  {i+1}. {t:6s} | 💣 Bomba: {s['bomba_skor']}/100 | Fiyat: {s['fiyat']:.2f} TL")
        print(f"     ML: {s['ml']*100:.0f}% | Teknik: {s['teknik']:.0f} | RSI: {s['rsi']:.0f} | MA: {s['ma']}/3")
        print(f"     5g: {s['son5g']:+.1f}% | 20g: {s['son20g']:+.1f}% | ATR: {s['atr_pct']:.1f}%")
        print(f"     🎯 Stop: {s['fiyat']*(1-stop/100):.2f} (-{stop}%) | H1: {hedef1:.2f} | H2: {hedef2:.2f}")
        print(f"     Sebepler: {' + '.join(s['sebepler'])}")

    # 8. IQ kodları üret
    print(f"\n{'=' * 60}")
    print("🤖 IQ Robot Kodları Üretiliyor...")
    print(f"{'=' * 60}")

    uretilen = []
    for s in top:
        ticker = s["ticker"]
        t = ticker.replace(".IS", "")

        kod = iq_kodu_uret(ticker, s["bomba_skor"], s["sebepler"], s["atr_pct"], s["fiyat"])

        # Dosyaya kaydet
        dosya = IQ_DIR / f"BOMBA_{t}.cs"
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(kod)

        uretilen.append({
            "ticker": t,
            "dosya": str(dosya),
            "bomba_skor": s["bomba_skor"],
        })
        print(f"  ✅ BOMBA_{t}.cs üretildi (Skor: {s['bomba_skor']})")

    # 9. Sonuçları kaydet
    rapor = {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rejim": rejim,
        "sentiment": s_val,
        "bombalar": [
            {
                "ticker": s["ticker"].replace(".IS", ""),
                "bomba_skor": s["bomba_skor"],
                "sebepler": s["sebepler"],
                "ml": round(s["ml"], 3),
                "fiyat": s["fiyat"],
                "stop": stop_hesapla(s["atr_pct"]),
            }
            for s in top
        ],
        "tum_skor": [
            {"ticker": s["ticker"].replace(".IS", ""), "skor": s["bomba_skor"]}
            for s in sonuclar[:20]
        ],
    }
    rapor_path = DATA_DIR / "gunluk_bomba.json"
    with open(rapor_path, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n💾 Rapor: {rapor_path}")
    print(f"📁 Kodlar: {IQ_DIR}/BOMBA_*.cs")

    # 10. Telegram bildirimi — kullanıcı telefondan görsün, Midas'tan manuel al
    try:
        from bildirim import gonder

        if rapor["bombalar"]:
            tarih = datetime.now().strftime("%d %b %Y")
            rejim_ad = (rapor.get("rejim") or {}).get("rejim", "?").upper() if isinstance(rapor.get("rejim"), dict) else "?"
            satirlar = [f"🔔 ANKA BIST Bomba — {tarih}", f"Rejim: {rejim_ad}", ""]
            for i, b in enumerate(rapor["bombalar"][:5], 1):
                sym = b["ticker"]
                fiyat = float(b["fiyat"])
                stop_pct = float(b.get("stop", 5))
                stop_fiyat = fiyat * (1 - stop_pct / 100)
                ml = float(b.get("ml", 0)) * 100
                skor = b.get("bomba_skor", 0)
                sebepler = b.get("sebepler", [])
                kisa_sebep = ", ".join(sebepler[:2]) if sebepler else ""
                satirlar.append(f"{i}. {sym} — {fiyat:.2f} TL")
                satirlar.append(f"   Skor:{skor} | ML:%{ml:.0f} | Stop:{stop_fiyat:.2f}")
                if kisa_sebep:
                    satirlar.append(f"   {kisa_sebep}")
                satirlar.append("")
            satirlar.append("Manuel alım için Midas app kullan.")
            mesaj = "\n".join(satirlar)
            gonder(mesaj)
            print(f"📱 Telegram bildirimi gönderildi ({len(rapor['bombalar'][:5])} öneri)")
        else:
            from bildirim import gonder as _g
            _g(f"🔕 ANKA BIST — {datetime.now().strftime('%d %b')}: Bugün bomba sinyali yok.")
    except Exception as _e:
        print(f"⚠️  Telegram bildirimi gönderilemedi: {_e}")

    return uretilen


def windows_deploy(uretilen):
    """Üretilen kodları Windows'a kopyala."""
    import subprocess

    print("\n📦 Windows'a kopyalanıyor...")
    for item in uretilen:
        t = item["ticker"]
        src = f'\\\\Mac\\Home\\adsız klasör\\borsa_surpriz\\matriks_iq\\BOMBA_{t}.cs'
        dst = f'C:\\Users\\onurbodur\\Desktop\\IQ_Deploy\\BOMBA_{t}.cs'
        try:
            subprocess.run(
                ["prlctl", "exec", "Windows 11", "cmd", "/c", f'copy "{src}" "{dst}" /Y'],
                capture_output=True, timeout=10
            )
            print(f"  ✅ BOMBA_{t}.cs → Windows")
        except Exception:
            print(f"  ❌ BOMBA_{t}.cs kopyalanamadı")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    from piyasa_takvim import bist_acik_mi

    acik, sebep = bist_acik_mi()
    if not acik and "--zorla" not in sys.argv:
        print(f"⏸️  BIST kapalı: {sebep}")
        print("   Tarama atlandı. Zorla çalıştırmak için: --zorla")
        sys.exit(0)

    uretilen = gunluk_tarama(
        top_n=5,
        min_skor=25,
    )

    if uretilen and "--sadece-tara" not in sys.argv:
        windows_deploy(uretilen)
        print("\n✅ Tamamlandı! IQ'da yapıştır → derle → çalıştır.")
