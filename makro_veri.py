"""
ANKA Makro Veri Katmanı — Faz 1
================================
TCMB EVDS API + yfinance fallback ile makro ekonomik verileri çeker.
Feature olarak ML modeline beslenir.

Veri kaynakları:
  - USD/TRY, EUR/TRY (döviz)
  - TCMB politika faizi
  - TCMB ağırlıklı ortalama fonlama maliyeti (AOFM)
  - XU100 endeks verisi (piyasa rejimi)
  - VIX (küresel korku endeksi)
  - Altın, Petrol (emtia korelasyon)

EVDS API key .env dosyasında EVDS_API_KEY olarak saklanır.
Key yoksa yfinance fallback kullanılır.
"""

import os
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from functools import lru_cache

warnings.filterwarnings("ignore")

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── EVDS API (evds kütüphanesi ile) ─────────────────────────────

# EVDS seri kodları
EVDS_SERILERI = {
    "usdtry": "TP.DK.USD.A.YTL",          # USD/TRY alış (efektif)
    "eurtry": "TP.DK.EUR.A.YTL",          # EUR/TRY alış
    "politika_faiz": "TP.PF.PF",           # Politika faizi
    "aofm": "TP.TRB.AGIR.ORLAM",          # Ağırlıklı ort. fonlama maliyeti
    "gecelik_repo": "TP.PY.P01",           # Gecelik repo faizi
}


def _evds_api_key():
    """EVDS API key'i .env veya environment'tan al."""
    key = os.environ.get("EVDS_API_KEY", "")
    if not key:
        env_path = PROJECT_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("EVDS_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    return key


def evds_veri_cek(seri_kodu: str, baslangic: str, bitis: str) -> pd.DataFrame:
    """
    EVDS API'den veri çeker (evds kütüphanesi ile).
    baslangic/bitis format: 'dd-MM-yyyy'
    Returns: DataFrame (tarih indexli, numeric)
    """
    key = _evds_api_key()
    if not key:
        return pd.DataFrame()

    try:
        from evds import evdsAPI
        evds = evdsAPI(key)
        df = evds.get_data([seri_kodu], startdate=baslangic, enddate=bitis)

        if df is None or df.empty:
            return pd.DataFrame()

        # Tarih sütununu index yap
        if "Tarih" in df.columns:
            df["Tarih"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y")
            df = df.set_index("Tarih").sort_index()

        # Numeric dönüştür
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # NaN satırları at
        df = df.dropna(how="all")

        return df

    except ImportError:
        print("  evds kütüphanesi yüklü değil: pip install evds")
        return pd.DataFrame()
    except Exception as e:
        print(f"  EVDS API hatası: {e}")
        return pd.DataFrame()


# ── yfinance Fallback ───────────────────────────────────────────

def yfinance_makro_cek(yil: int = 5) -> dict:
    """
    yfinance ile makro verileri çeker (EVDS key yoksa fallback).
    Returns: dict of DataFrames
    """
    semboller = {
        "usdtry": "USDTRY=X",
        "eurtry": "EURTRY=X",
        "altin_usd": "GC=F",
        "petrol": "CL=F",
        "vix": "^VIX",
        "xu100": "XU100.IS",
        "sp500": "^GSPC",
        "dxy": "DX-Y.NYB",      # Dolar endeksi
    }

    sonuc = {}
    for isim, sembol in semboller.items():
        try:
            df = yf.download(sembol, period=f"{yil}y", progress=False)
            if len(df) >= 50:
                sonuc[isim] = df
                print(f"  ✅ {isim}: {len(df)} gün")
            else:
                print(f"  ⚠️ {isim}: yetersiz veri ({len(df)} gün)")
        except Exception as e:
            print(f"  ❌ {isim}: {e}")
        time.sleep(0.3)

    return sonuc


# ── EVDS + yfinance Birleşik ────────────────────────────────────

def tum_makro_veri_cek(yil: int = 5) -> dict:
    """
    Hem EVDS hem yfinance'ten makro veri çeker.
    EVDS key varsa TCMB verilerini de ekler.
    Returns: dict of DataFrames
    """
    print("\n📊 Makro veriler çekiliyor...")

    # 1) yfinance (her zaman)
    sonuc = yfinance_makro_cek(yil)

    # 2) EVDS (key varsa)
    key = _evds_api_key()
    if key:
        print("  🏦 TCMB EVDS verileri çekiliyor...")
        bitis = datetime.now().strftime("%d-%m-%Y")
        baslangic = (datetime.now() - timedelta(days=yil * 365)).strftime("%d-%m-%Y")

        for isim, kod in EVDS_SERILERI.items():
            df = evds_veri_cek(kod, baslangic, bitis)
            if not df.empty:
                sonuc[f"tcmb_{isim}"] = df
                print(f"  ✅ TCMB {isim}: {len(df)} gün")
            else:
                print(f"  ⚠️ TCMB {isim}: veri yok")
            time.sleep(1)
    else:
        print("  ℹ️ EVDS API key yok — TCMB verileri atlanıyor")
        print("  ℹ️ Key almak için: https://evds2.tcmb.gov.tr → Üye Ol → API Key")

    return sonuc


# ── Makro Feature Mühendisliği ──────────────────────────────────

def makro_feature_hesapla(makro_veri: dict, hisse_index: pd.DatetimeIndex) -> pd.DataFrame:
    """
    Makro verilerden hisse bazlı feature'lar üretir.
    hisse_index: Hedef hissenin tarih indexi (hizalama için)
    Returns: DataFrame (hisse_index ile aynı index)
    """
    f = pd.DataFrame(index=hisse_index)

    # ── USD/TRY Feature'ları ─────────────────────────────────
    # TCMB EVDS varsa onu tercih et, yoksa yfinance fallback
    if "tcmb_usdtry" in makro_veri:
        usd_src = makro_veri["tcmb_usdtry"]
        usd = usd_src.iloc[:, 0] if len(usd_src.columns) > 0 else usd_src.squeeze()
    elif "usdtry" in makro_veri:
        usd = makro_veri["usdtry"]["Close"].squeeze()
    else:
        usd = None

    if usd is not None:
        usd = usd.reindex(hisse_index, method="ffill")

        f["usdtry"] = usd
        f["usdtry_degisim_1g"] = usd.pct_change(1) * 100
        f["usdtry_degisim_5g"] = usd.pct_change(5) * 100
        f["usdtry_degisim_20g"] = usd.pct_change(20) * 100
        f["usdtry_vol_10g"] = usd.pct_change().rolling(10).std() * np.sqrt(252) * 100

        # Dolar trendi — yükselen dolar BIST için negatif sinyal
        usd_sma20 = usd.rolling(20).mean()
        usd_sma50 = usd.rolling(50).mean()
        f["usdtry_trend"] = (usd - usd_sma20) / usd_sma20 * 100
        f["usdtry_sma_cross"] = ((usd_sma20 > usd_sma50).astype(int) * 2 - 1)  # 1=yükseliş, -1=düşüş

    # ── EUR/TRY Feature'ları ─────────────────────────────────
    if "tcmb_eurtry" in makro_veri:
        eur_src = makro_veri["tcmb_eurtry"]
        eur = eur_src.iloc[:, 0] if len(eur_src.columns) > 0 else eur_src.squeeze()
    elif "eurtry" in makro_veri:
        eur = makro_veri["eurtry"]["Close"].squeeze()
    else:
        eur = None

    if eur is not None:
        eur = eur.reindex(hisse_index, method="ffill")
        f["eurtry_degisim_5g"] = eur.pct_change(5) * 100

    # ── USD/TRY - EUR/TRY Spread (carry trade sinyali) ──────
    if usd is not None and eur is not None:
        f["eur_usd_spread_degisim"] = (eur / usd).pct_change(5) * 100

    # ── VIX (Küresel Korku) ──────────────────────────────────
    if "vix" in makro_veri:
        vix = makro_veri["vix"]["Close"].squeeze()
        vix = vix.reindex(hisse_index, method="ffill")

        f["vix"] = vix
        f["vix_degisim_5g"] = vix.pct_change(5) * 100
        f["vix_seviye"] = pd.cut(vix, bins=[0, 15, 20, 25, 35, 100],
                                  labels=[0, 1, 2, 3, 4]).astype(float)
        # VIX > 25 = korku, < 15 = aşırı güven
        f["vix_spike"] = (vix.diff(1) > 3).astype(int)  # Ani VIX sıçraması

    # ── Altın (Güvenli Liman) ────────────────────────────────
    if "altin_usd" in makro_veri:
        altin = makro_veri["altin_usd"]["Close"].squeeze()
        altin = altin.reindex(hisse_index, method="ffill")
        f["altin_degisim_5g"] = altin.pct_change(5) * 100
        f["altin_degisim_20g"] = altin.pct_change(20) * 100

    # ── Petrol ───────────────────────────────────────────────
    if "petrol" in makro_veri:
        petrol = makro_veri["petrol"]["Close"].squeeze()
        petrol = petrol.reindex(hisse_index, method="ffill")
        f["petrol_degisim_5g"] = petrol.pct_change(5) * 100
        f["petrol_degisim_20g"] = petrol.pct_change(20) * 100

    # ── DXY (Dolar Endeksi — EM için kritik) ─────────────────
    if "dxy" in makro_veri:
        dxy = makro_veri["dxy"]["Close"].squeeze()
        dxy = dxy.reindex(hisse_index, method="ffill")
        f["dxy_degisim_5g"] = dxy.pct_change(5) * 100
        f["dxy_trend"] = (dxy - dxy.rolling(20).mean()) / dxy.rolling(20).mean() * 100

    # ── S&P 500 (Global risk iştahı) ─────────────────────────
    if "sp500" in makro_veri:
        sp = makro_veri["sp500"]["Close"].squeeze()
        sp = sp.reindex(hisse_index, method="ffill")
        f["sp500_degisim_5g"] = sp.pct_change(5) * 100
        f["sp500_degisim_20g"] = sp.pct_change(20) * 100

    # ── XU100 Endeks (Piyasa genel) ──────────────────────────
    if "xu100" in makro_veri:
        xu = makro_veri["xu100"]["Close"].squeeze()
        xu = xu.reindex(hisse_index, method="ffill")
        f["xu100_degisim_5g"] = xu.pct_change(5) * 100
        f["xu100_degisim_20g"] = xu.pct_change(20) * 100
        f["xu100_vol_20g"] = xu.pct_change().rolling(20).std() * np.sqrt(252) * 100

        # XU100 rejim sinyali
        xu_sma50 = xu.rolling(50).mean()
        xu_sma200 = xu.rolling(200).mean()
        f["xu100_trend"] = (xu - xu_sma50) / xu_sma50 * 100
        f["xu100_golden_cross"] = ((xu_sma50 > xu_sma200).astype(int))

    # ── TCMB Verileri (EVDS key varsa) ───────────────────────
    if "tcmb_politika_faiz" in makro_veri:
        faiz = makro_veri["tcmb_politika_faiz"].iloc[:, 0]
        faiz = faiz.reindex(hisse_index, method="ffill")
        f["tcmb_faiz"] = faiz
        f["tcmb_faiz_degisim"] = faiz.diff()  # Faiz değişimi (bps)

    if "tcmb_aofm" in makro_veri:
        aofm = makro_veri["tcmb_aofm"].iloc[:, 0]
        aofm = aofm.reindex(hisse_index, method="ffill")
        f["tcmb_aofm"] = aofm
        f["tcmb_aofm_spread"] = aofm - f.get("tcmb_faiz", 0)  # AOFM - politika faiz farkı

    if "tcmb_gecelik_repo" in makro_veri:
        repo = makro_veri["tcmb_gecelik_repo"].iloc[:, 0]
        repo = repo.reindex(hisse_index, method="ffill")
        f["tcmb_repo"] = repo

    # ── Türev Sinyaller ──────────────────────────────────────

    # Risk-on/Risk-off skoru (birleşik)
    risk_on = pd.Series(0.0, index=hisse_index)
    sinyal_sayisi = 0

    if "vix" in f.columns:
        risk_on += (f["vix"] < 20).astype(float)
        sinyal_sayisi += 1
    if "usdtry_degisim_5g" in f.columns:
        risk_on += (f["usdtry_degisim_5g"] < 0).astype(float)  # Dolar düşüyor = risk-on
        sinyal_sayisi += 1
    if "sp500_degisim_5g" in f.columns:
        risk_on += (f["sp500_degisim_5g"] > 0).astype(float)
        sinyal_sayisi += 1
    if "dxy_degisim_5g" in f.columns:
        risk_on += (f["dxy_degisim_5g"] < 0).astype(float)  # DXY düşüyor = EM'e iyi
        sinyal_sayisi += 1

    if sinyal_sayisi > 0:
        f["risk_on_skor"] = risk_on / sinyal_sayisi  # 0-1 arası, 1=tam risk-on

    # Döviz baskısı skoru
    if "usdtry_degisim_5g" in f.columns and "usdtry_vol_10g" in f.columns:
        f["doviz_baskisi"] = f["usdtry_degisim_5g"] * f["usdtry_vol_10g"] / 100
        # Pozitif = TL değer kaybı + yüksek volatilite = kötü

    return f.dropna(how="all")


# ── Makro Feature Listesi ───────────────────────────────────────

MAKRO_FEATURE_COLS = [
    # Döviz
    "usdtry_degisim_1g", "usdtry_degisim_5g", "usdtry_degisim_20g",
    "usdtry_vol_10g", "usdtry_trend", "usdtry_sma_cross",
    "eurtry_degisim_5g", "eur_usd_spread_degisim",
    # VIX
    "vix", "vix_degisim_5g", "vix_seviye", "vix_spike",
    # Emtia
    "altin_degisim_5g", "altin_degisim_20g",
    "petrol_degisim_5g", "petrol_degisim_20g",
    # Global
    "dxy_degisim_5g", "dxy_trend",
    "sp500_degisim_5g", "sp500_degisim_20g",
    # BIST endeks
    "xu100_degisim_5g", "xu100_degisim_20g", "xu100_vol_20g",
    "xu100_trend", "xu100_golden_cross",
    # TCMB (EVDS varsa)
    "tcmb_faiz", "tcmb_faiz_degisim",
    "tcmb_aofm", "tcmb_aofm_spread",
    "tcmb_repo",
    # Türev
    "risk_on_skor", "doviz_baskisi",
]


# ── Cache Mekanizması ───────────────────────────────────────────

_makro_cache = {}
_cache_tarihi = None


def makro_veri_al(yil: int = 5, force: bool = False) -> dict:
    """
    Makro verileri çeker ve cache'ler.
    Aynı gün içinde tekrar çağrılırsa cache'ten döner.
    """
    global _makro_cache, _cache_tarihi

    bugun = datetime.now().date()
    if not force and _cache_tarihi == bugun and _makro_cache:
        print("  📦 Makro veriler cache'ten alındı")
        return _makro_cache

    _makro_cache = tum_makro_veri_cek(yil)
    _cache_tarihi = bugun

    # Disk cache
    cache_path = DATA_DIR / "makro_cache_tarih.txt"
    cache_path.write_text(bugun.isoformat())

    return _makro_cache


# ── Test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔥 ANKA Makro Veri Katmanı Test")
    print("=" * 50)

    makro = makro_veri_al(yil=5)

    print(f"\n📊 {len(makro)} makro veri seti yüklendi")
    for isim, df in makro.items():
        print(f"  {isim}: {len(df)} satır, son tarih: {df.index[-1]}")

    # Test: XU100 indexi ile feature üret
    if "xu100" in makro:
        xu_index = makro["xu100"].index
        features = makro_feature_hesapla(makro, xu_index)
        print(f"\n📈 Makro feature'lar: {features.shape[1]} sütun, {len(features)} satır")
        print(f"  Mevcut feature'lar: {[c for c in features.columns if features[c].notna().sum() > 100]}")
        print(f"\n  Son değerler:")
        son = features.iloc[-1]
        for col in features.columns:
            if pd.notna(son[col]):
                print(f"    {col}: {son[col]:.4f}")
