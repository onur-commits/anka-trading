"""
ANKA — Hibrit V3 Bomba Tarayıcı
================================
ML + Teknik + Veto sistemi ile bomba hisse bulucu.
Sonuçları C:\Robot\aktif_bombalar.txt'ye yazar.
"""

import pandas as pd
import yfinance as yf
import os
import sys
import subprocess
import platform
import joblib
from pathlib import Path

# ML model ve feature fonksiyonlarını yükle
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

try:
    from tahmin_motoru_v2 import feature_olustur_v2, EnsembleModelV2
    ML_READY = True
except ImportError:
    ML_READY = False

def ml_model_yukle():
    """Eğitilmiş ML modelini yükle — otonom trader ile aynı yöntem."""
    try:
        model = EnsembleModelV2.yukle()
        return model
    except:
        pass
    # Fallback: joblib
    model_path = PROJECT_DIR / "models" / "ensemble_v2.pkl"
    if model_path.exists():
        try:
            return joblib.load(model_path)
        except:
            pass
    return None

def ml_skor_hesapla(df, model):
    """Hisse için ML skoru hesapla (0-1 arası yükseliş olasılığı)."""
    if model is None or not ML_READY:
        return 0.5

    try:
        from tahmin_motoru_v2 import hisse_analiz_v2
        # Otonom trader'ın kullandığı birebir aynı yöntem
        analiz = hisse_analiz_v2("TEST", df, model, None)
        if analiz and analiz.get("ml_olasilik"):
            return float(analiz["ml_olasilik"])
        return 0.5
    except:
        return 0.5

def hibrit_v3_scanner(symbol_list, ml_model=None):
    bombalar = []
    print(f"🚀 {len(symbol_list)} Hisse Taranıyor...")

    for s in symbol_list:
        try:
            df = yf.download(s + ".IS", period="20d", interval="1d", progress=False)
            if df.empty or len(df) < 15: continue

            # --- 1. ML SKOR (Gerçek model) ---
            ml_score = ml_skor_hesapla(df, ml_model)

            # --- 2. BOMBA SKOR (Teknik Puanlama 0-100) ---
            avg_vol = float(df['Volume'].rolling(10).mean().iloc[-1])
            curr_vol = float(df['Volume'].iloc[-1])
            hacim_orani = curr_vol / avg_vol if avg_vol > 0 else 0

            close = float(df['Close'].iloc[-1])
            high = float(df['High'].iloc[-1])
            kapanis_gucu = close / high if high > 0 else 0

            bomba_skor = (hacim_orani * 30) + (kapanis_gucu * 70)

            # --- 3. HİBRİT VETO MANTIĞI ---
            ml_onay = ml_score >= 0.75
            hacim_onay = hacim_orani >= 1.8
            kapanis_onay = kapanis_gucu >= 0.985

            # KARAR KATMANI
            is_bomba = False

            # Kural 1: 3'ü de EVET ise kesin BOMBA
            if ml_onay and hacim_onay and kapanis_onay:
                is_bomba = True
                print(f"✅ {s} - KESİN BOMBA (3/3 Onay) | ML:{ml_score:.2f} Hacim:x{hacim_orani:.1f} Kapanış:{kapanis_gucu:.3f}")

            # Kural 2: Veto Esnetme (ML çok güçlü + skor yüksek)
            elif ml_score >= 0.85 and bomba_skor >= 50:
                is_bomba = True
                print(f"⚠️ {s} - VETO ESNETİLDİ (ML:{ml_score:.2f} Skor:{bomba_skor:.0f})")

            if is_bomba:
                bombalar.append(s)

        except Exception as e:
            continue

    # Dosyaya yaz
    liste = ",".join(bombalar)
    print(f"\n🎯 BOMBALAR: {liste if liste else 'YOK'}")

    if platform.system() == "Windows":
        with open("C:/Robot/aktif_bombalar.txt", "w") as f:
            f.write(liste)
    else:
        # Mac → Windows'a kopyala
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "aktif_bombalar.txt")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w") as f:
            f.write(liste)
        try:
            subprocess.run(
                ["prlctl", "exec", "Windows 11", "cmd", "/c",
                 f"echo {liste} > C:\\Robot\\aktif_bombalar.txt"],
                timeout=10, capture_output=True)
        except:
            pass

    return bombalar


# BIST50 sembol listesi
BIST50 = [
    "GARAN","THYAO","ASELS","TUPRS","EREGL","SISE","TOASO","AKBNK","YKBNK","HALKB",
    "SAHOL","KCHOL","TCELL","BIMAS","PGSUS","TAVHL","FROTO","ARCLK","PETKM","ENKAI",
    "TKFEN","EKGYO","TTKOM","VAKBN","MGROS","DOHOL","GUBRF","ISCTR","AKSEN","AYEN",
    "KONTR","SASA","GESAN","OTKAR","ENJSA","TSKB","SMRTG","CCOLA","CIMSA","KORDS",
    "VESTL","ALARK","HEKTS","ULKER","ASTOR","TTRAK","EGEEN","CEMTS","BRISA"
]

if __name__ == "__main__":
    print("🔥 ANKA Hibrit V3 Tarayıcı")
    print("ML model yükleniyor...")
    model = ml_model_yukle()
    if model:
        print(f"✅ ML model yüklendi")
    else:
        print("⚠️ ML model bulunamadı — sadece teknik filtre")
    bombalar = hibrit_v3_scanner(BIST50, ml_model=model)
    print(f"\n✅ {len(bombalar)} bomba bulundu: {bombalar}")
