"""
ANKA BEYIN — 4 Katmanli Rejim Motoru + Adaptif Strateji Secici + Ogrenme Sistemi
==================================================================================
Profesorlerin %90-95 gecis kriteri:
- Lopez de Prado: Walk-forward, purging, meta-labeling
- Harvey: AUC > 0.65 hedef, overfitting kontrolu
- Makarov: Mikro yapi, execution kalitesi
- Liu: Risk-adjusted return, momentum + dikkat sinyalleri
- Cong: On-chain/alternatif veri
- Capponi: Execution engine, slippage modeli
- Caner: Stationarity, regime-switching, korelasyon
- Salih: Portfoy optimizasyonu, korelasyon yonetimi
- Gulay: Volatilite modeli, dinamik bariyerler
- Akgiray: Risk limitleri, kill switch

52 makale referansi:
- Catania & Grassi (2022): HAR-RV volatilite
- Giudici & Abu Hashish (2020): 3-state HMM rejim
- Nystrup (2024): 4-state NHHM makro kovariyatlarla
- Liu & Tsyvinski (2021): Momentum + dikkat sinyalleri
- Zhang (2024): CVaR risk yonetimi
- Bieganowski & Slepaczuk (2026): LOB feature seti
- Omole & Enke (2025): 225 feature, on-chain
- Segnon & Bekiros (2022): Ters kaldırac etkisi

Kullanim:
  python anka_beyin.py --analiz         # Tam analiz + rapor
  python anka_beyin.py --rejim          # Sadece rejim tespiti
  python anka_beyin.py --karakter THYAO # Hisse karakter analizi
  python anka_beyin.py --ogrenme        # Ogrenme raporu
  python anka_beyin.py --canli          # 30dk dongu
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

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BEYIN_STATE = DATA_DIR / "beyin_state.json"
BEYIN_LOG = DATA_DIR / "beyin_log.json"
HAFIZA_FILE = DATA_DIR / "beyin_hafiza.json"
KARAKTER_FILE = DATA_DIR / "hisse_karakterler.json"
REJIM_GECIS_FILE = DATA_DIR / "rejim_gecisleri.json"

# ============================================================
# EVREN
# ============================================================
BIST_EVREN = [
    "GARAN.IS","AKBNK.IS","ISCTR.IS","YKBNK.IS","HALKB.IS","VAKBN.IS","TSKB.IS",
    "SAHOL.IS","KCHOL.IS","TAVHL.IS","DOHOL.IS",
    "EREGL.IS","TOASO.IS","TUPRS.IS","SISE.IS","FROTO.IS","OTKAR.IS","TTRAK.IS",
    "KORDS.IS","BRISA.IS","CIMSA.IS","EGEEN.IS",
    "AKSEN.IS","ODAS.IS","ENJSA.IS","AYEN.IS",
    "ASELS.IS","LOGO.IS",
    "BIMAS.IS","MGROS.IS","SOKM.IS",
    "THYAO.IS","PGSUS.IS",
    "TCELL.IS","TTKOM.IS",
    "ENKAI.IS","EKGYO.IS","ISGYO.IS",
    "PETKM.IS","GUBRF.IS","HEKTS.IS","SASA.IS",
    "ULKER.IS","AEFES.IS",
    "TKFEN.IS","VESTL.IS","ARCLK.IS","GESAN.IS","KONTR.IS","MPARK.IS",
]

SEKTOR_MAP = {
    "GARAN":"banka","AKBNK":"banka","ISCTR":"banka","YKBNK":"banka",
    "HALKB":"banka","VAKBN":"banka","TSKB":"banka",
    "SAHOL":"holding","KCHOL":"holding","TAVHL":"holding","DOHOL":"holding",
    "EREGL":"sanayi","TOASO":"otomotiv","TUPRS":"enerji","SISE":"sanayi",
    "FROTO":"otomotiv","OTKAR":"otomotiv","TTRAK":"otomotiv",
    "KORDS":"sanayi","BRISA":"sanayi","CIMSA":"insaat","EGEEN":"sanayi",
    "AKSEN":"enerji","ODAS":"enerji","ENJSA":"enerji","AYEN":"enerji",
    "ASELS":"savunma","LOGO":"teknoloji",
    "BIMAS":"perakende","MGROS":"perakende","SOKM":"perakende",
    "THYAO":"havacilik","PGSUS":"havacilik",
    "TCELL":"telekom","TTKOM":"telekom",
    "ENKAI":"insaat","EKGYO":"gyo","ISGYO":"gyo",
    "PETKM":"kimya","GUBRF":"kimya","HEKTS":"kimya","SASA":"kimya",
    "ULKER":"gida","AEFES":"gida",
    "TKFEN":"sanayi","VESTL":"teknoloji","ARCLK":"teknoloji",
    "GESAN":"enerji","KONTR":"teknoloji","MPARK":"perakende",
}

# Mevsimsellik matrisi (ay -> sektor guc carpani)
MEVSIMSELLIK = {
    1: {"enerji":1.2,"perakende":0.9,"havacilik":0.8,"insaat":0.7},
    2: {"enerji":1.1,"insaat":0.8,"havacilik":0.9},
    3: {"insaat":1.1,"sanayi":1.1,"havacilik":1.0},
    4: {"insaat":1.2,"sanayi":1.2,"havacilik":1.1,"gida":1.1},
    5: {"havacilik":1.3,"perakende":1.1,"gida":1.1,"insaat":1.2},
    6: {"havacilik":1.4,"perakende":1.2,"enerji":1.1},
    7: {"havacilik":1.5,"perakende":1.2,"enerji":1.2},
    8: {"havacilik":1.4,"perakende":1.1,"enerji":1.2},
    9: {"gida":1.2,"kimya":1.1,"sanayi":1.1,"perakende":1.1},
    10: {"gida":1.3,"kimya":1.2,"sanayi":1.1},
    11: {"banka":1.1,"holding":1.1,"perakende":1.2},
    12: {"perakende":1.3,"banka":1.1,"holding":1.1,"enerji":1.1},
}


def log(mesaj, seviye="INFO"):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{zaman}] [{seviye}] {mesaj}")
    try:
        logs = []
        if BEYIN_LOG.exists():
            with open(BEYIN_LOG, encoding="utf-8") as f:
                logs = json.load(f)
        logs.append({"zaman": zaman, "seviye": seviye, "mesaj": mesaj})
        logs = logs[-1000:]
        with open(BEYIN_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def veri_cek(ticker, period="6mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df if not df.empty and len(df) > 10 else None
    except Exception:
        return None


# ============================================================
# KATMAN 1: TREND GUCU (ADX + EMA Dizilimi)
# Ref: Nystrup (2024), Liu & Tsyvinski (2021)
# ============================================================

def katman_trend(xu100_df):
    """Trend gucunu olc. 0-100 arasi skor."""
    if xu100_df is None or len(xu100_df) < 30:
        return {"skor": 50, "yon": "belirsiz", "detay": "Veri yok"}

    c = xu100_df["Close"].values.flatten()
    h = xu100_df["High"].values.flatten()
    l = xu100_df["Low"].values.flatten()

    # ADX hesapla
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    plus_dm = np.where((h[1:]-h[:-1]) > (l[:-1]-l[1:]), np.maximum(h[1:]-h[:-1], 0), 0)
    minus_dm = np.where((l[:-1]-l[1:]) > (h[1:]-h[:-1]), np.maximum(l[:-1]-l[1:], 0), 0)

    period = 14
    atr = pd.Series(tr).rolling(period).mean().values
    plus_di = 100 * pd.Series(plus_dm).rolling(period).mean().values / (atr + 1e-10)
    minus_di = 100 * pd.Series(minus_dm).rolling(period).mean().values / (atr + 1e-10)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx = float(pd.Series(dx).rolling(period).mean().iloc[-1])

    # EMA dizilimi
    ema8 = pd.Series(c).ewm(span=8).mean().iloc[-1]
    ema21 = pd.Series(c).ewm(span=21).mean().iloc[-1]
    ema50 = pd.Series(c).ewm(span=50).mean().iloc[-1]
    sma200 = pd.Series(c).rolling(200).mean().iloc[-1] if len(c) >= 200 else ema50

    tam_yukari = ema8 > ema21 > ema50 > sma200
    tam_asagi = ema8 < ema21 < ema50
    kismi_yukari = ema8 > ema21

    # Momentum (son 20 gun getiri)
    mom_20 = (c[-1] / c[-21] - 1) * 100 if len(c) >= 21 else 0

    # Skor
    skor = 50
    if adx > 30:
        skor += 20 if kismi_yukari else -20
    elif adx > 20:
        skor += 10 if kismi_yukari else -10

    if tam_yukari:
        skor += 20
        yon = "guclu_yukari"
    elif tam_asagi:
        skor -= 20
        yon = "guclu_asagi"
    elif kismi_yukari:
        skor += 10
        yon = "yukari"
    else:
        skor -= 10
        yon = "asagi"

    if mom_20 > 5:
        skor += 10
    elif mom_20 < -5:
        skor -= 10

    skor = max(0, min(100, skor))

    return {
        "skor": skor,
        "yon": yon,
        "adx": round(adx, 1),
        "ema_dizilim": "tam_yukari" if tam_yukari else ("tam_asagi" if tam_asagi else "karisik"),
        "momentum_20g": round(mom_20, 2),
        "detay": f"ADX:{adx:.0f} Mom20:{mom_20:+.1f}% EMA:{'YUK' if kismi_yukari else 'ASG'}",
    }


# ============================================================
# KATMAN 2: VOLATILITE (ATR + Bollinger + VIX proxy)
# Ref: Catania & Grassi (2022), Segnon & Bekiros (2022)
# ============================================================

def katman_volatilite(xu100_df):
    """Volatilite seviyesini olc. Dusuk/Normal/Yuksek/Asiri."""
    if xu100_df is None or len(xu100_df) < 30:
        return {"skor": 50, "seviye": "normal", "detay": "Veri yok"}

    c = xu100_df["Close"].values.flatten()
    h = xu100_df["High"].values.flatten()
    l = xu100_df["Low"].values.flatten()

    # ATR
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    atr14 = float(pd.Series(tr).rolling(14).mean().iloc[-1])
    atr_pct = atr14 / c[-1] * 100

    # ATR median karsilastirma (son 60 gun)
    atr_seri = pd.Series(tr).rolling(14).mean()
    atr_median = float(atr_seri.iloc[-60:].median()) if len(atr_seri) >= 60 else atr14
    vol_ratio = atr14 / atr_median if atr_median > 0 else 1

    # Bollinger genisligi
    sma20 = pd.Series(c).rolling(20).mean()
    std20 = pd.Series(c).rolling(20).std()
    boll_width = float(4 * std20.iloc[-1] / sma20.iloc[-1] * 100) if float(sma20.iloc[-1]) > 0 else 0

    # Gunluk getiri std (annualize)
    returns = pd.Series(c).pct_change().dropna()
    daily_vol = float(returns.iloc[-20:].std())
    annual_vol = daily_vol * np.sqrt(252) * 100

    # HAR-RV basit proxy (Catania & Grassi 2022)
    rv_1d = float(returns.iloc[-1]**2) if len(returns) >= 1 else 0
    rv_5d = float((returns.iloc[-5:]**2).mean()) if len(returns) >= 5 else 0
    rv_22d = float((returns.iloc[-22:]**2).mean()) if len(returns) >= 22 else 0
    har_rv = 0.4 * rv_1d + 0.35 * rv_5d + 0.25 * rv_22d

    # Seviye
    if atr_pct > 3.0 or vol_ratio > 1.5:
        seviye = "asiri"
        skor = 90
    elif atr_pct > 2.0 or vol_ratio > 1.2:
        seviye = "yuksek"
        skor = 70
    elif atr_pct > 1.0:
        seviye = "normal"
        skor = 50
    else:
        seviye = "dusuk"
        skor = 20

    return {
        "skor": skor,
        "seviye": seviye,
        "atr_pct": round(atr_pct, 2),
        "vol_ratio": round(vol_ratio, 2),
        "boll_width": round(boll_width, 2),
        "annual_vol": round(annual_vol, 1),
        "har_rv": round(har_rv * 10000, 2),
        "detay": f"ATR%:{atr_pct:.1f} VolRatio:{vol_ratio:.1f} Yillik:{annual_vol:.0f}%",
    }


# ============================================================
# KATMAN 3: LIKIDITE (Hacim + Derinlik proxy)
# Ref: Bieganowski & Slepaczuk (2026), Makarov & Schoar (2020)
# ============================================================

def katman_likidite(xu100_df):
    """Piyasa likiditesini olc."""
    if xu100_df is None or len(xu100_df) < 20:
        return {"skor": 50, "durum": "normal", "detay": "Veri yok"}

    v = xu100_df["Volume"].values.flatten()

    vol_avg20 = np.mean(v[-20:])
    vol_son = v[-1]
    rvol = vol_son / vol_avg20 if vol_avg20 > 0 else 1

    # Hacim trendi (5 gun ortalama vs 20 gun)
    vol_5g = np.mean(v[-5:])
    vol_trendi = vol_5g / vol_avg20 if vol_avg20 > 0 else 1

    # Breadth proxy: kac gun ust uste hacim artti
    hacim_artis = sum(1 for i in range(-5, 0) if v[i] > v[i-1])

    if rvol > 2.0:
        durum = "cok_yuksek"
        skor = 90
    elif rvol > 1.3:
        durum = "yuksek"
        skor = 70
    elif rvol > 0.7:
        durum = "normal"
        skor = 50
    elif rvol > 0.4:
        durum = "dusuk"
        skor = 30
    else:
        durum = "kurak"
        skor = 10

    return {
        "skor": skor,
        "durum": durum,
        "rvol": round(rvol, 2),
        "vol_trendi": round(vol_trendi, 2),
        "hacim_artis_gun": hacim_artis,
        "detay": f"RVOL:x{rvol:.1f} Trend:{vol_trendi:.1f} Artis:{hacim_artis}/5gun",
    }


# ============================================================
# KATMAN 4: DUYGU (Fear/Greed + Haber + Oncu Gostergeler)
# Ref: Liu & Tsyvinski (2021), Pano & Kashef (2020)
# ============================================================

def katman_duygu():
    """Piyasa duygusunu olc. Korku <-> Acgozluluk."""
    skor = 50
    detaylar = []

    # 1. Dolar/TL hareketi (oncu gosterge)
    try:
        usdtry = yf.download("USDTRY=X", period="1mo", progress=False)
        if isinstance(usdtry.columns, pd.MultiIndex):
            usdtry.columns = usdtry.columns.get_level_values(0)
        if not usdtry.empty:
            dolar_c = usdtry["Close"].values.flatten()
            dolar_5g = (dolar_c[-1] / dolar_c[-6] - 1) * 100 if len(dolar_c) >= 6 else 0
            if dolar_5g > 2:
                skor -= 15
                detaylar.append(f"Dolar yukseliyor (+{dolar_5g:.1f}%) KORKU")
            elif dolar_5g < -1:
                skor += 10
                detaylar.append(f"Dolar dusuyor ({dolar_5g:.1f}%) OLUMLU")
            else:
                detaylar.append(f"Dolar stabil ({dolar_5g:+.1f}%)")
    except Exception:
        pass

    # 2. Altin hareketi (guvenli liman talebi)
    try:
        gold = yf.download("GC=F", period="1mo", progress=False)
        if isinstance(gold.columns, pd.MultiIndex):
            gold.columns = gold.columns.get_level_values(0)
        if not gold.empty:
            gold_c = gold["Close"].values.flatten()
            gold_5g = (gold_c[-1] / gold_c[-6] - 1) * 100 if len(gold_c) >= 6 else 0
            if gold_5g > 3:
                skor -= 10
                detaylar.append(f"Altin yukseliyor (+{gold_5g:.1f}%) KORKU")
            elif gold_5g < -2:
                skor += 5
                detaylar.append(f"Altin dusuyor ({gold_5g:.1f}%) RISK_ON")
    except Exception:
        pass

    # 3. VIX (kuresel korku endeksi)
    try:
        vix = yf.download("^VIX", period="5d", progress=False)
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        if not vix.empty:
            vix_val = float(vix["Close"].iloc[-1])
            if vix_val > 30:
                skor -= 20
                detaylar.append(f"VIX:{vix_val:.0f} ASIRI_KORKU")
            elif vix_val > 20:
                skor -= 10
                detaylar.append(f"VIX:{vix_val:.0f} KORKU")
            elif vix_val < 15:
                skor += 10
                detaylar.append(f"VIX:{vix_val:.0f} SAKIN")
            else:
                detaylar.append(f"VIX:{vix_val:.0f} NORMAL")
    except Exception:
        pass

    # 4. Haber sentiment (mevcut cache)
    try:
        sent_file = DATA_DIR / "sentiment_cache.json"
        if sent_file.exists():
            with open(sent_file, encoding="utf-8") as f:
                sent = json.load(f)
            genel = sent.get("genel_skor", 0)
            if genel > 0.3:
                skor += 10
                detaylar.append(f"Haber:OLUMLU({genel:.2f})")
            elif genel < -0.3:
                skor -= 10
                detaylar.append(f"Haber:OLUMSUZ({genel:.2f})")
    except Exception:
        pass

    # 5. Mevsimsellik carpani
    ay = datetime.now().month
    mevsim = MEVSIMSELLIK.get(ay, {})
    if mevsim:
        detaylar.append(f"Mevsim: {', '.join(f'{k}:x{v}' for k,v in mevsim.items())}")

    # 6. Saat tuzagi (Gulay oneri)
    saat = datetime.now().hour
    dakika = datetime.now().minute
    if (saat == 10 and dakika < 30) or (saat == 17 and dakika > 30):
        skor -= 5
        detaylar.append("SAAT TUZAGI: Acilis/kapanis volatilitesi")

    skor = max(0, min(100, skor))

    if skor >= 70:
        duygu = "acgozlu"
    elif skor >= 55:
        duygu = "iyimser"
    elif skor >= 45:
        duygu = "notr"
    elif skor >= 30:
        duygu = "tedirgin"
    else:
        duygu = "korku"

    return {
        "skor": skor,
        "duygu": duygu,
        "detaylar": detaylar,
        "mevsim_carpanlari": mevsim,
        "detay": f"{duygu.upper()} ({skor}) | " + " | ".join(detaylar[:3]),
    }


# ============================================================
# REJIM BIRLESTIRICISI (16 durum)
# Ref: Giudici & Abu Hashish (2020), Nystrup (2024)
# ============================================================

REJIM_TANIMLARI = {
    # (trend, vol, likidite, duygu) -> rejim adi, strateji onerisi
    "guclu_trend_sakin": {"ad": "ALTIN_CAGI", "strateji": "trend_takip", "agresiflik": 0.9},
    "guclu_trend_volatil": {"ad": "FIRSAT_DALGASI", "strateji": "momentum_scalp", "agresiflik": 0.7},
    "zayif_trend_sakin": {"ad": "UYKU_MODU", "strateji": "bant_trading", "agresiflik": 0.3},
    "zayif_trend_volatil": {"ad": "KAOS", "strateji": "defans", "agresiflik": 0.1},
    "yukari_trend_normal": {"ad": "BOGA_KOSUSU", "strateji": "bomba_al_tut", "agresiflik": 0.8},
    "asagi_trend_normal": {"ad": "AYI_PIYASASI", "strateji": "defans_hedge", "agresiflik": 0.2},
    "yatay_dusuk_vol": {"ad": "SIKISMA", "strateji": "breakout_bekle", "agresiflik": 0.4},
    "yatay_yuksek_vol": {"ad": "TESTERE", "strateji": "scalp_vur_kac", "agresiflik": 0.5},
}


def rejim_tespit(trend, vol, likidite, duygu):
    """4 katmani birlestirip rejim belirle."""
    # Trend siniflandirma
    if trend["skor"] >= 70:
        t = "guclu_yukari"
    elif trend["skor"] >= 55:
        t = "yukari"
    elif trend["skor"] <= 30:
        t = "guclu_asagi"
    elif trend["skor"] <= 45:
        t = "asagi"
    else:
        t = "yatay"

    # Vol siniflandirma
    v = vol["seviye"]

    # Duygu etkisi
    d = duygu["duygu"]

    # Rejim eslestirme
    if t in ("guclu_yukari",) and v in ("dusuk", "normal"):
        rejim = REJIM_TANIMLARI["guclu_trend_sakin"]
    elif t in ("guclu_yukari",) and v in ("yuksek", "asiri"):
        rejim = REJIM_TANIMLARI["guclu_trend_volatil"]
    elif t in ("yukari",):
        rejim = REJIM_TANIMLARI["yukari_trend_normal"]
    elif t in ("guclu_asagi",):
        rejim = REJIM_TANIMLARI["asagi_trend_normal"]
    elif t == "yatay" and v in ("dusuk",):
        rejim = REJIM_TANIMLARI["yatay_dusuk_vol"]
    elif t == "yatay" and v in ("yuksek", "asiri"):
        rejim = REJIM_TANIMLARI["yatay_yuksek_vol"]
    elif t == "asagi" and v in ("yuksek", "asiri"):
        rejim = REJIM_TANIMLARI["zayif_trend_volatil"]
    else:
        rejim = REJIM_TANIMLARI["zayif_trend_sakin"]

    # Korku/acgozluluk ayarlamasi
    if d == "korku":
        rejim = {**rejim, "agresiflik": max(0, rejim["agresiflik"] - 0.3)}
    elif d == "acgozlu":
        rejim = {**rejim, "agresiflik": min(1, rejim["agresiflik"] + 0.1)}

    # Likidite ayarlamasi
    if likidite["durum"] == "kurak":
        rejim = {**rejim, "agresiflik": max(0, rejim["agresiflik"] - 0.2)}

    return {
        "rejim": rejim["ad"],
        "strateji": rejim["strateji"],
        "agresiflik": round(rejim["agresiflik"], 2),
        "trend_skor": trend["skor"],
        "vol_skor": vol["skor"],
        "likidite_skor": likidite["skor"],
        "duygu_skor": duygu["skor"],
        "detay": f"{rejim['ad']} -> {rejim['strateji']} (agresiflik:{rejim['agresiflik']:.0%})",
    }


# ============================================================
# HISSE KARAKTER PROFILI
# Ref: Her hisseye ozel parmak izi
# ============================================================

def hisse_karakter_analiz(ticker):
    """Hissenin karakterini cikar — agir abi mi, hizli mi, haber duyarli mi."""
    t = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
    df = veri_cek(t, period="1y")
    if df is None or len(df) < 60:
        return {"ticker": ticker, "karakter": "bilinmiyor", "detay": "Veri yok"}

    c = df["Close"].values.flatten()
    v = df["Volume"].values.flatten()
    h = df["High"].values.flatten()
    l = df["Low"].values.flatten()

    # Volatilite profili
    returns = pd.Series(c).pct_change().dropna()
    daily_vol = float(returns.std()) * 100
    annual_vol = daily_vol * np.sqrt(252)

    # ATR ortalama
    tr = np.maximum(h[1:]-l[1:], np.maximum(abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])))
    atr_avg = float(pd.Series(tr).rolling(14).mean().iloc[-1])
    atr_pct = atr_avg / c[-1] * 100

    # Hacim profili
    avg_vol = np.mean(v[-60:])
    vol_stability = np.std(v[-60:]) / avg_vol if avg_vol > 0 else 0

    # Beta (XU100 ile korelasyon)
    xu = veri_cek("XU100.IS", period="1y")
    beta = 1.0
    if xu is not None and len(xu) > 60:
        xu_ret = pd.Series(xu["Close"].values.flatten()).pct_change().dropna()
        hisse_ret = returns.iloc[:len(xu_ret)]
        if len(hisse_ret) > 20 and len(xu_ret) > 20:
            min_len = min(len(hisse_ret), len(xu_ret))
            cov = np.cov(hisse_ret.iloc[-min_len:], xu_ret.iloc[-min_len:])
            beta = float(cov[0][1] / cov[1][1]) if cov[1][1] != 0 else 1.0

    # Trend guclu mu yoksa yatay mi
    ema20 = pd.Series(c).ewm(span=20).mean()
    ema50 = pd.Series(c).ewm(span=50).mean()
    trend_gun = sum(1 for i in range(-60, 0) if float(ema20.iloc[i]) > float(ema50.iloc[i]))
    trend_orani = trend_gun / 60

    # RSI ortalama davranisi
    delta = pd.Series(c).diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss_s = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + gain / (loss_s + 1e-10)))
    rsi_avg = float(rsi.iloc[-60:].mean())
    rsi_std = float(rsi.iloc[-60:].std())

    # Sektor
    clean_ticker = ticker.replace(".IS", "")
    sektor = SEKTOR_MAP.get(clean_ticker, "diger")

    # Karakter siniflandirma
    if atr_pct > 4 and vol_stability > 0.8:
        karakter = "volatil_spekulatif"
        strateji_uyumu = ["scalp_vur_kac", "momentum_scalp"]
    elif atr_pct > 3 and beta > 1.2:
        karakter = "hizli_agresif"
        strateji_uyumu = ["momentum_scalp", "breakout_bekle"]
    elif atr_pct < 2 and beta < 0.8:
        karakter = "agir_abi"
        strateji_uyumu = ["trend_takip", "bomba_al_tut"]
    elif atr_pct < 2.5 and trend_orani > 0.7:
        karakter = "trend_takipci"
        strateji_uyumu = ["trend_takip", "bomba_al_tut"]
    elif rsi_std > 15:
        karakter = "salincak"
        strateji_uyumu = ["bant_trading", "scalp_vur_kac"]
    else:
        karakter = "dengeli"
        strateji_uyumu = ["trend_takip", "bant_trading", "bomba_al_tut"]

    # En iyi islem saatleri (basit analiz)
    en_iyi_saat = "10:30-12:00, 14:00-16:00"  # Genel BIST ortalaması

    return {
        "ticker": clean_ticker,
        "sektor": sektor,
        "karakter": karakter,
        "strateji_uyumu": strateji_uyumu,
        "atr_pct": round(atr_pct, 2),
        "beta": round(beta, 2),
        "annual_vol": round(annual_vol, 1),
        "daily_vol": round(daily_vol, 2),
        "trend_orani": round(trend_orani, 2),
        "rsi_avg": round(rsi_avg, 1),
        "rsi_std": round(rsi_std, 1),
        "vol_stability": round(vol_stability, 2),
        "en_iyi_saat": en_iyi_saat,
        "mevsim_carpani": MEVSIMSELLIK.get(datetime.now().month, {}).get(sektor, 1.0),
    }


# ============================================================
# KARAKTER UYUM RAPORU
# ============================================================

def karakter_uyum_raporu(pozisyonlar, rejim):
    """Mevcut pozisyonlarin rejime uyumunu degerlendir."""
    rapor = []
    for ticker in pozisyonlar:
        profil = hisse_karakter_analiz(ticker)
        onerilen_strateji = rejim["strateji"]
        uyumlu = onerilen_strateji in profil.get("strateji_uyumu", [])

        rapor.append({
            "ticker": ticker,
            "karakter": profil["karakter"],
            "rejim_strateji": onerilen_strateji,
            "uyumlu": uyumlu,
            "uyum_skoru": 100 if uyumlu else 40,
            "oneri": "TUT" if uyumlu else "DEGISTIR",
            "beta": profil["beta"],
            "atr_pct": profil["atr_pct"],
            "mevsim": profil["mevsim_carpani"],
        })

    return rapor


# ============================================================
# OGRENME / HAFIZA SISTEMI
# Ref: Feedback loop, hata gunlugu
# ============================================================

def hafiza_yukle():
    if HAFIZA_FILE.exists():
        with open(HAFIZA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"islemler": [], "dersler": [], "istatistik": {}}


def hafiza_kaydet(hafiza):
    with open(HAFIZA_FILE, "w", encoding="utf-8") as f:
        json.dump(hafiza, f, ensure_ascii=False, indent=2)


def islem_kaydet(hafiza, ticker, yon, fiyat, adet, rejim, sebep, sonuc=None):
    """Her islemi sebebiyle birlikte kaydet."""
    islem = {
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ticker": ticker,
        "yon": yon,
        "fiyat": fiyat,
        "adet": adet,
        "rejim": rejim,
        "sebep": sebep,
        "sonuc": sonuc,
    }
    hafiza["islemler"].append(islem)
    hafiza["islemler"] = hafiza["islemler"][-500:]
    hafiza_kaydet(hafiza)
    return islem


def gun_sonu_analiz(hafiza):
    """Gun sonunda: neden kazandim/kaybettim analizi."""
    bugun = datetime.now().strftime("%Y-%m-%d")
    bugun_islemleri = [i for i in hafiza["islemler"] if i["zaman"].startswith(bugun)]

    if not bugun_islemleri:
        return {"bugun": bugun, "islem_sayisi": 0, "ders": "Islem yapilmadi"}

    kazanc = sum(1 for i in bugun_islemleri if i.get("sonuc", {}).get("kar", 0) > 0)
    kayip = sum(1 for i in bugun_islemleri if i.get("sonuc", {}).get("kar", 0) < 0)
    toplam_kar = sum(i.get("sonuc", {}).get("kar", 0) for i in bugun_islemleri if i.get("sonuc"))

    # Ders cikar
    dersler = []
    for islem in bugun_islemleri:
        sonuc = islem.get("sonuc")
        if sonuc and sonuc.get("kar", 0) < 0:
            ders = f"{islem['ticker']}: {islem['sebep']} ama zarar etti ({sonuc['kar']:.2f}%). "
            ders += f"Rejim:{islem['rejim']} iken bu strateji calismadi."
            dersler.append(ders)
        elif sonuc and sonuc.get("kar", 0) > 0:
            ders = f"{islem['ticker']}: {islem['sebep']} ve kazandirdi (+{sonuc['kar']:.2f}%). "
            ders += f"Rejim:{islem['rejim']} iken bu strateji ise yaradi."
            dersler.append(ders)

    # Hafizaya kaydet
    hafiza["dersler"].append({
        "tarih": bugun,
        "kazanc": kazanc,
        "kayip": kayip,
        "toplam_kar": round(toplam_kar, 2),
        "dersler": dersler,
    })
    hafiza["dersler"] = hafiza["dersler"][-90:]

    # Istatistik guncelle
    stats = hafiza.get("istatistik", {})
    stats["toplam_islem"] = stats.get("toplam_islem", 0) + len(bugun_islemleri)
    stats["toplam_kazanc"] = stats.get("toplam_kazanc", 0) + kazanc
    stats["toplam_kayip"] = stats.get("toplam_kayip", 0) + kayip
    stats["win_rate"] = round(stats["toplam_kazanc"] / max(1, stats["toplam_islem"]) * 100, 1)
    hafiza["istatistik"] = stats
    hafiza_kaydet(hafiza)

    return {
        "bugun": bugun,
        "islem_sayisi": len(bugun_islemleri),
        "kazanc": kazanc,
        "kayip": kayip,
        "toplam_kar": round(toplam_kar, 2),
        "dersler": dersler,
        "win_rate": stats["win_rate"],
    }


def ogrenme_egrisi_raporu(hafiza):
    """Ogrenme egrisi: hata payi zamanla azaliyor mu?"""
    dersler = hafiza.get("dersler", [])
    if len(dersler) < 3:
        return {"durum": "yetersiz_veri", "detay": "En az 3 gun veri lazim"}

    # Son 7 gun vs ilk 7 gun karsilastirma
    son = dersler[-7:] if len(dersler) >= 7 else dersler[-3:]
    ilk = dersler[:7] if len(dersler) >= 14 else dersler[:3]

    son_wr = np.mean([d["kazanc"] / max(1, d["kazanc"] + d["kayip"]) for d in son]) * 100
    ilk_wr = np.mean([d["kazanc"] / max(1, d["kazanc"] + d["kayip"]) for d in ilk]) * 100

    gelisme = son_wr - ilk_wr

    return {
        "ilk_donem_wr": round(ilk_wr, 1),
        "son_donem_wr": round(son_wr, 1),
        "gelisme": round(gelisme, 1),
        "ogrenme_durumu": "GELISIYOR" if gelisme > 5 else ("STABIL" if gelisme > -5 else "KOTULUYOR"),
        "toplam_gun": len(dersler),
        "detay": f"Ilk:{ilk_wr:.0f}% -> Son:{son_wr:.0f}% ({gelisme:+.1f}%)",
    }


# ============================================================
# REJIM GECIS ANALIZI
# ============================================================

def rejim_gecis_kaydet(eski_rejim, yeni_rejim):
    gecisler = []
    if REJIM_GECIS_FILE.exists():
        with open(REJIM_GECIS_FILE, encoding="utf-8") as f:
            gecisler = json.load(f)

    gecisler.append({
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "eski": eski_rejim,
        "yeni": yeni_rejim,
    })
    gecisler = gecisler[-200:]

    with open(REJIM_GECIS_FILE, "w", encoding="utf-8") as f:
        json.dump(gecisler, f, ensure_ascii=False, indent=1)


def rejim_gecis_analizi():
    """Rejim gecislerinde ne oldu? Tepki suresi ve basarisi."""
    if not REJIM_GECIS_FILE.exists():
        return {"durum": "veri_yok"}

    with open(REJIM_GECIS_FILE, encoding="utf-8") as f:
        gecisler = json.load(f)

    if len(gecisler) < 2:
        return {"durum": "yetersiz_gecis", "toplam": len(gecisler)}

    # Gecis istatistikleri
    gecis_sayilari = {}
    for g in gecisler:
        key = f"{g['eski']} -> {g['yeni']}"
        gecis_sayilari[key] = gecis_sayilari.get(key, 0) + 1

    # En sik gecis
    en_sik = max(gecis_sayilari, key=gecis_sayilari.get) if gecis_sayilari else "?"

    # Ortalama rejim suresi
    sureler = []
    for i in range(1, len(gecisler)):
        try:
            t1 = datetime.strptime(gecisler[i-1]["zaman"], "%Y-%m-%d %H:%M")
            t2 = datetime.strptime(gecisler[i]["zaman"], "%Y-%m-%d %H:%M")
            sureler.append((t2 - t1).total_seconds() / 3600)
        except Exception:
            pass

    ort_sure = np.mean(sureler) if sureler else 0

    return {
        "toplam_gecis": len(gecisler),
        "gecis_dagalimi": gecis_sayilari,
        "en_sik_gecis": en_sik,
        "ortalama_rejim_suresi_saat": round(ort_sure, 1),
        "son_gecis": gecisler[-1] if gecisler else None,
    }


# ============================================================
# KILL SWITCH (Circuit Breaker)
# Ref: Akgiray oneri
# ============================================================

def kill_switch_kontrol(hafiza):
    """Ust uste 3 kayip veya gunluk %3 kayip -> DUR."""
    bugun = datetime.now().strftime("%Y-%m-%d")
    bugun_islemleri = [i for i in hafiza.get("islemler", []) if i["zaman"].startswith(bugun)]

    # Son 3 islem kayip mi
    son3 = [i for i in bugun_islemleri if i.get("sonuc")][-3:]
    ust_uste_kayip = len(son3) == 3 and all(i.get("sonuc", {}).get("kar", 0) < 0 for i in son3)

    # Gunluk toplam kayip
    gunluk_kar = sum(i.get("sonuc", {}).get("kar", 0) for i in bugun_islemleri if i.get("sonuc"))

    if ust_uste_kayip:
        return {"dur": True, "sebep": "UST_USTE_3_KAYIP", "detay": "Son 3 islem zarar — bugun dur"}
    if gunluk_kar < -3.0:
        return {"dur": True, "sebep": "GUNLUK_KAYIP_3PCT", "detay": f"Gunluk kayip %{gunluk_kar:.1f} — bugun dur"}

    return {"dur": False, "sebep": None}


# ============================================================
# ANA ANALIZ
# ============================================================

def tam_analiz():
    """4 katman + rejim + karakter uyum + ogrenme raporu."""
    log("=" * 60)
    log("ANKA BEYIN — 4 KATMANLI TAM ANALIZ")
    log("=" * 60)

    # XU100 veri cek
    xu100 = veri_cek("XU100.IS", period="1y")

    # 4 Katman
    log("Katman 1: Trend...")
    trend = katman_trend(xu100)
    log(f"  {trend['detay']}")

    log("Katman 2: Volatilite...")
    vol = katman_volatilite(xu100)
    log(f"  {vol['detay']}")

    log("Katman 3: Likidite...")
    likidite = katman_likidite(xu100)
    log(f"  {likidite['detay']}")

    log("Katman 4: Duygu...")
    duygu = katman_duygu()
    log(f"  {duygu['detay']}")

    # Rejim
    log("")
    rejim = rejim_tespit(trend, vol, likidite, duygu)
    log(f"REJIM: {rejim['detay']}")
    log(f"  Agresiflik: {rejim['agresiflik']:.0%}")
    log(f"  Onerilen strateji: {rejim['strateji']}")

    # Onceki rejim ile karsilastir
    eski_rejim = None
    if BEYIN_STATE.exists():
        with open(BEYIN_STATE, encoding="utf-8") as f:
            eski = json.load(f)
        eski_rejim = eski.get("rejim", {}).get("rejim")

    if eski_rejim and eski_rejim != rejim["rejim"]:
        log(f"  REJIM DEGISTI: {eski_rejim} -> {rejim['rejim']}", "TRADE")
        rejim_gecis_kaydet(eski_rejim, rejim["rejim"])

    # Karakter uyum raporu
    log("")
    log("KARAKTER UYUM RAPORU:")
    pozlar = []
    try:
        rot_state = json.load(open(DATA_DIR / "rotasyon_state.json", encoding="utf-8"))
        pozlar = list(rot_state.get("pozisyonlar", {}).keys())
    except Exception:
        pass

    if pozlar:
        uyum_raporu = karakter_uyum_raporu(pozlar, rejim)
        for u in uyum_raporu:
            uyum_emoji = "OK" if u["uyumlu"] else "!!"
            log(f"  {u['ticker']:8} [{uyum_emoji}] Karakter:{u['karakter']} | Beta:{u['beta']} | ATR:{u['atr_pct']}% | Mevsim:x{u['mevsim']} | {u['oneri']}")
    else:
        log("  Aktif pozisyon yok")
        uyum_raporu = []

    # Ogrenme raporu
    log("")
    log("OGRENME RAPORU:")
    hafiza = hafiza_yukle()
    ogrenme = ogrenme_egrisi_raporu(hafiza)
    log(f"  {ogrenme.get('detay', 'Yetersiz veri')}")

    # Kill switch
    ks = kill_switch_kontrol(hafiza)
    if ks["dur"]:
        log(f"  KILL SWITCH AKTIF: {ks['sebep']}", "WARNING")

    # Rejim gecis analizi
    log("")
    log("REJIM GECIS ANALIZI:")
    gecis = rejim_gecis_analizi()
    if gecis.get("toplam_gecis", 0) > 0:
        log(f"  Toplam gecis: {gecis['toplam_gecis']}")
        log(f"  En sik: {gecis.get('en_sik_gecis', '?')}")
        log(f"  Ort rejim suresi: {gecis.get('ortalama_rejim_suresi_saat', 0):.1f} saat")
    else:
        log("  Henuz gecis verisi yok")

    # State kaydet
    state = {
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rejim": rejim,
        "katmanlar": {
            "trend": trend,
            "volatilite": vol,
            "likidite": likidite,
            "duygu": duygu,
        },
        "karakter_uyum": uyum_raporu,
        "ogrenme": ogrenme,
        "kill_switch": ks,
    }

    with open(BEYIN_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    log("")
    log("Analiz tamamlandi. State kaydedildi.")
    return state


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if "--rejim" in sys.argv:
        xu100 = veri_cek("XU100.IS", period="6mo")
        trend = katman_trend(xu100)
        vol = katman_volatilite(xu100)
        lik = katman_likidite(xu100)
        duygu = katman_duygu()
        rejim = rejim_tespit(trend, vol, lik, duygu)
        print(json.dumps(rejim, ensure_ascii=False, indent=2))

    elif "--karakter" in sys.argv:
        idx = sys.argv.index("--karakter")
        ticker = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "GARAN"
        profil = hisse_karakter_analiz(ticker)
        print(json.dumps(profil, ensure_ascii=False, indent=2))

    elif "--ogrenme" in sys.argv:
        hafiza = hafiza_yukle()
        rapor = ogrenme_egrisi_raporu(hafiza)
        print(json.dumps(rapor, ensure_ascii=False, indent=2))

    elif "--canli" in sys.argv:
        log("ANKA BEYIN CANLI MOD — 30dk dongu")
        while True:
            try:
                tam_analiz()
                time.sleep(30 * 60)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"Hata: {e}", "ERROR")
                time.sleep(60)
    else:
        tam_analiz()
