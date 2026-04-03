"""
ANKA — 7/24 Bomba Tarayıcı
============================
Her saat çalışır. Gün içi veriyle hacim karşılaştırması yapar.
Sabah, öğlen, akşam — her zaman bomba bulabilir.
"""

import pandas as pd
import yfinance as yf
import os
import sys
import subprocess
import platform
import time
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

try:
    from tahmin_motoru_v2 import EnsembleModelV2, hisse_analiz_v2, feature_olustur_v2
    ML_READY = True
except ImportError:
    ML_READY = False

# BIST50
BIST50 = [
    "GARAN","THYAO","ASELS","TUPRS","EREGL","SISE","TOASO","AKBNK","YKBNK","HALKB",
    "SAHOL","KCHOL","TCELL","BIMAS","PGSUS","TAVHL","FROTO","ARCLK","PETKM","ENKAI",
    "TKFEN","EKGYO","TTKOM","VAKBN","MGROS","DOHOL","GUBRF","ISCTR","AKSEN","AYEN",
    "KONTR","SASA","GESAN","OTKAR","ENJSA","TSKB","SMRTG","CCOLA","CIMSA","KORDS",
    "VESTL","ALARK","HEKTS","ULKER","ASTOR","TTRAK","EGEEN","CEMTS","BRISA"
]


def ml_model_yukle():
    """Önce ANKA AI (5 yıl eğitimli), yoksa eski model."""
    # 1. ANKA AI v1 (yeni, 5 yıl veriyle eğitilmiş)
    anka_path = PROJECT_DIR / "models" / "anka_ai_v1.pkl"
    if anka_path.exists():
        try:
            import joblib
            data = joblib.load(anka_path)
            print(f"🧠 ANKA AI yüklendi (AUC: {data.get('auc', '?')})")
            return {"type": "anka", "data": data}
        except:
            pass
    # 2. Eski ensemble model
    if ML_READY:
        try:
            m = EnsembleModelV2.yukle()
            if m:
                print("🧠 Ensemble V2 yüklendi")
                return {"type": "ensemble", "data": m}
        except:
            pass
    return None


def ml_skor(ticker, df_daily, model_wrapper):
    """ML skoru hesapla — ANKA AI veya eski model."""
    if model_wrapper is None:
        return 0.5

    try:
        if model_wrapper["type"] == "anka":
            # ANKA AI — kendi feature'larıyla tahmin
            from anka_ai_egitim import feature_hesapla
            features = feature_hesapla(df_daily)
            if len(features) == 0:
                return 0.5
            last = features.iloc[-1:]
            models = model_wrapper["data"]["models"]
            import numpy as np
            probas = np.mean([m.predict_proba(last)[:, 1] for m in models.values()], axis=0)
            return float(probas[0])

        elif model_wrapper["type"] == "ensemble":
            # Eski yöntem
            analiz = hisse_analiz_v2(ticker, df_daily, model_wrapper["data"], None)
            if analiz and analiz.get("ml_olasilik"):
                return float(analiz["ml_olasilik"])
    except:
        pass
    return 0.5


def gun_ici_hacim_analizi(df_intraday):
    """
    Gün içi hacim analizi — aynı saatteki ortalama hacimle karşılaştır.
    Örnek: Saat 12'deki hacmi, son 5 günün saat 12 hacim ortalamasıyla karşılaştır.
    """
    if df_intraday is None or len(df_intraday) < 20:
        return 0, 0

    # Şu anki bar hacmi
    son_hacim = float(df_intraday['Volume'].iloc[-1])

    # Son 5 günün aynı saatindeki hacim ortalaması
    saat = df_intraday.index[-1].hour
    ayni_saat = df_intraday[df_intraday.index.hour == saat]

    if len(ayni_saat) < 2:
        # Aynı saat verisi yoksa son 20 barın ortalamasını al
        ort = float(df_intraday['Volume'].iloc[-20:].mean())
    else:
        # Bugünkü hariç, önceki günlerin aynı saati
        onceki = ayni_saat.iloc[:-1]
        ort = float(onceki['Volume'].mean()) if len(onceki) > 0 else float(df_intraday['Volume'].mean())

    oran = son_hacim / ort if ort > 0 else 0
    return oran, son_hacim


def mum_guclu_mu(df_intraday):
    """Son mumun gövde doluluğu ve kapanış gücü."""
    if df_intraday is None or len(df_intraday) < 1:
        return 0, 0

    close = float(df_intraday['Close'].iloc[-1])
    open_ = float(df_intraday['Open'].iloc[-1])
    high = float(df_intraday['High'].iloc[-1])
    low = float(df_intraday['Low'].iloc[-1])

    # Gövde doluluğu (0-1)
    total_range = high - low
    if total_range > 0:
        govde = abs(close - open_) / total_range
    else:
        govde = 0

    # Kapanış gücü (close / high oranı)
    kapanis_gucu = close / high if high > 0 else 0

    return govde, kapanis_gucu


def anka_tara(symbol_list=None, ml_model=None):
    """
    ANKA ana tarama fonksiyonu — her saat çalışabilir.
    Gün içi 30dk veriyle hacim, günlük veriyle ML.
    """
    if symbol_list is None:
        symbol_list = BIST50

    saat = datetime.now().hour
    print(f"\n🔥 ANKA TARAMA — Saat {saat:02d}:{datetime.now().minute:02d} | {len(symbol_list)} hisse")
    print("=" * 60)

    bombalar = []
    detaylar = []

    for s in symbol_list:
        try:
            # Gün içi veri (hacim analizi için)
            df_intra = yf.download(f"{s}.IS", period="5d", interval="30m", progress=False)
            if df_intra.empty or len(df_intra) < 20:
                continue

            # Günlük veri (ML için — 2 yıl lazım, 52 hafta rolling hesaplar var)
            df_daily = yf.download(f"{s}.IS", period="2y", interval="1d", progress=False)
            if df_daily.empty or len(df_daily) < 260:
                continue

            # 1. ML SKORU (günlük veriyle)
            ml = ml_skor(s, df_daily, ml_model)

            # 2. GÜN İÇİ HACİM (aynı saatteki ortalamayla karşılaştır)
            hacim_oran, son_hacim = gun_ici_hacim_analizi(df_intra)

            # 3. MUM GÜCÜ (son 30dk bar)
            govde, kapanis_gucu = mum_guclu_mu(df_intra)

            # 4. GÜNLÜK DEĞİŞİM
            gunluk = 0
            if len(df_daily) >= 2:
                gunluk = float((df_daily['Close'].iloc[-1] / df_daily['Close'].iloc[-2] - 1) * 100)

            # === HİBRİT VETO SİSTEMİ ===
            ml_onay = ml >= 0.65       # ML güveniyor
            hacim_onay = hacim_oran >= 1.5   # Gün içi hacim normalin 1.5x (daha esnek)
            kapanis_onay = kapanis_gucu >= 0.985  # Güçlü kapanış
            govde_onay = govde >= 0.5   # Dolu gövde

            # BOMBA SKOR (dinamik)
            skor = 0
            skor += min(40, ml * 40)                    # ML: max 40 puan
            skor += min(30, hacim_oran * 10)             # Hacim: max 30 puan
            skor += min(20, kapanis_gucu * 20)           # Kapanış: max 20 puan
            skor += min(10, govde * 10)                  # Gövde: max 10 puan

            is_bomba = False
            sebep = ""

            # Kural 1: 4/4 onay → KESİN BOMBA
            if ml_onay and hacim_onay and kapanis_onay and govde_onay:
                is_bomba = True
                sebep = "KESİN (4/4)"

            # Kural 2: ML çok güçlü + hacim var → VETO ESNET
            elif ml >= 0.80 and hacim_oran >= 1.2:
                is_bomba = True
                sebep = "ML GÜÇLÜ"

            # Kural 3: Hacim patlama + kapanış güçlü → ML'siz de al
            elif hacim_oran >= 2.5 and kapanis_onay and govde_onay:
                is_bomba = True
                sebep = "HACİM PATLAMA"

            detaylar.append({
                "ticker": s, "ml": ml, "hacim": hacim_oran,
                "kapanis": kapanis_gucu, "govde": govde,
                "skor": skor, "bomba": is_bomba, "sebep": sebep,
                "gunluk": gunluk
            })

            if is_bomba:
                bombalar.append(s)
                print(f"  💣 {s:6} | ML:{ml:.2f} | Hacim:x{hacim_oran:.1f} | Kap:{kapanis_gucu:.3f} | Skor:{skor:.0f} | {sebep}")

        except Exception as e:
            continue

    # En yüksek skorlular (bomba olmasa bile göster)
    detaylar.sort(key=lambda x: x["skor"], reverse=True)
    print(f"\n📊 Top 10 (bomba olmayanlar dahil):")
    for d in detaylar[:10]:
        emoji = "💣" if d["bomba"] else "  "
        print(f"  {emoji} {d['ticker']:6} | ML:{d['ml']:.2f} | Hacim:x{d['hacim']:.1f} | Skor:{d['skor']:.0f} | Gün:{d['gunluk']:+.1f}%")

    # Dosyaya yaz
    liste = ",".join(bombalar)
    print(f"\n🎯 BOMBALAR: {liste if liste else 'YOK'}")

    # Windows'a kopyala
    if platform.system() == "Windows":
        with open("C:/Robot/aktif_bombalar.txt", "w") as f:
            f.write(liste)
    else:
        try:
            subprocess.run(
                ["prlctl", "exec", "Windows 11", "cmd", "/c",
                 f"echo {liste} > C:\\Robot\\aktif_bombalar.txt"],
                timeout=10, capture_output=True)
        except:
            pass

    return bombalar, detaylar


def anka_loop(interval_dk=30):
    """Sürekli tarama döngüsü — her N dakikada bir."""
    model = ml_model_yukle()
    print(f"🦅 ANKA SÜREKLİ TARAMA — Her {interval_dk} dakika")
    if model:
        print("✅ ML model yüklü")
    else:
        print("⚠️ ML model yok")

    while True:
        saat = datetime.now().hour
        # Piyasa saatleri (09:30-18:00)
        if 9 <= saat < 18:
            bombalar, _ = anka_tara(BIST50, model)
        else:
            print(f"[{datetime.now().strftime('%H:%M')}] Piyasa kapalı — bekliyorum")

        time.sleep(interval_dk * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Sürekli tara")
    parser.add_argument("--interval", type=int, default=30, help="Tarama aralığı (dk)")
    args = parser.parse_args()

    if args.loop:
        anka_loop(args.interval)
    else:
        model = ml_model_yukle()
        anka_tara(BIST50, model)
