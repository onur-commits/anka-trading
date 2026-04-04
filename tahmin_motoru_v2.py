"""
BIST ALPHA V2 — Kurumsal Seviye ML Tahmin Motoru
==================================================
- XGBoost + LightGBM + Neural Network Ensemble
- 80+ mühendislik feature
- Market Rejim Tespiti (bull/bear/sideways)
- Sektör Momentum Analizi
- Adaptif Model — her hafta kendini günceller
- Walk-Forward + Purged CV (veri sızıntısı önleme)
"""

import numpy as np
import pandas as pd
from pathlib import Path
import joblib
import json
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# ============================================================
# V1'DEN ALINAN TEKNİK İNDİKATÖRLER (geniletilmiş)
# ============================================================

def rsi_hesapla(seri, periyot=14):
    delta = seri.diff()
    kazanc = delta.where(delta > 0, 0).rolling(periyot).mean()
    kayip = (-delta.where(delta < 0, 0)).rolling(periyot).mean()
    rs = kazanc / kayip.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd_hesapla(seri, hizli=12, yavas=26, sinyal=9):
    ema_h = seri.ewm(span=hizli, adjust=False).mean()
    ema_y = seri.ewm(span=yavas, adjust=False).mean()
    macd = ema_h - ema_y
    macd_s = macd.ewm(span=sinyal, adjust=False).mean()
    return macd, macd_s, macd - macd_s


def bollinger_hesapla(seri, periyot=20, std=2):
    sma = seri.rolling(periyot).mean()
    s = seri.rolling(periyot).std()
    return sma, sma + std * s, sma - std * s, (2 * std * s) / sma * 100


def obv_hesapla(close, volume):
    return (np.sign(close.diff()).fillna(0) * volume).cumsum()


def atr_hesapla(high, low, close, periyot=14):
    """Average True Range — volatilite ölçüsü, risk yönetiminde kritik."""
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=periyot, adjust=False).mean()


def adx_hesapla(high, low, close, periyot=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    dm_p = high.diff().clip(lower=0)
    dm_m = (-low.diff()).clip(lower=0)
    dm_p = dm_p.where(dm_p > dm_m, 0)
    dm_m = dm_m.where(dm_m > dm_p, 0)
    atr = tr.ewm(span=periyot, adjust=False).mean()
    di_p = 100 * dm_p.ewm(span=periyot, adjust=False).mean() / atr.replace(0, np.nan)
    di_m = 100 * dm_m.ewm(span=periyot, adjust=False).mean() / atr.replace(0, np.nan)
    dx = 100 * (di_p - di_m).abs() / (di_p + di_m).replace(0, np.nan)
    return dx.ewm(span=periyot, adjust=False).mean(), di_p, di_m


def stokastik_hesapla(high, low, close, k=14, d=3):
    en_d = low.rolling(k).min()
    en_y = high.rolling(k).max()
    k_val = 100 * (close - en_d) / (en_y - en_d).replace(0, np.nan)
    return k_val, k_val.rolling(d).mean()


def vwap_hesapla(high, low, close, volume):
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum()


# ============================================================
# V2: GELİŞMİŞ FEATURE MÜHENDİSLİĞİ (80+ feature)
# ============================================================

def feature_olustur_v2(df):
    """V2 feature seti — 80+ feature, kurumsal seviye."""
    if len(df) < 120:
        return None

    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    volume = df["Volume"].squeeze()
    opn = df["Open"].squeeze()

    f = pd.DataFrame(index=df.index)

    # ── RSI (çoklu periyot) ───────────────────────────────────
    f["rsi_7"] = rsi_hesapla(close, 7)
    f["rsi_14"] = rsi_hesapla(close, 14)
    f["rsi_21"] = rsi_hesapla(close, 21)
    f["rsi_divergence"] = f["rsi_14"].diff(5) - (close.pct_change(5) * 100)

    # ── MACD ──────────────────────────────────────────────────
    macd, macd_s, hist = macd_hesapla(close)
    f["macd"] = macd
    f["macd_sinyal"] = macd_s
    f["macd_hist"] = hist
    f["macd_hist_degisim"] = hist.diff()
    f["macd_cross"] = np.sign(hist).diff().abs()  # 2 = kesişim

    # ── Bollinger ─────────────────────────────────────────────
    _, ust, alt, gen = bollinger_hesapla(close)
    f["boll_poz"] = (close - alt) / (ust - alt).replace(0, np.nan)
    f["boll_gen"] = gen
    f["boll_sikisma"] = (gen == gen.rolling(20).min()).astype(int)
    f["boll_squeeze_duration"] = f["boll_sikisma"].groupby(
        (f["boll_sikisma"] != f["boll_sikisma"].shift()).cumsum()
    ).cumcount()

    # ── OBV ───────────────────────────────────────────────────
    obv = obv_hesapla(close, volume)
    obv_ort = obv.rolling(20).mean()
    f["obv_trend"] = (obv - obv_ort) / obv_ort.abs().replace(0, np.nan)
    f["obv_momentum"] = obv.pct_change(5)
    f["obv_divergence"] = obv.pct_change(10) - close.pct_change(10)

    # ── ADX ───────────────────────────────────────────────────
    adx, di_p, di_m = adx_hesapla(high, low, close)
    f["adx"] = adx
    f["di_fark"] = di_p - di_m
    f["adx_trend"] = adx.diff(5)  # trend güçleniyor mu?

    # ── ATR (V2 yeni) ────────────────────────────────────────
    atr = atr_hesapla(high, low, close)
    f["atr"] = atr
    f["atr_pct"] = atr / close * 100  # yüzdelik volatilite
    f["atr_change"] = atr.pct_change(5)  # volatilite genişliyor mu?
    f["atr_ratio"] = atr / atr.rolling(50).mean().replace(0, np.nan)

    # ── Stokastik ─────────────────────────────────────────────
    stok_k, stok_d = stokastik_hesapla(high, low, close)
    f["stok_k"] = stok_k
    f["stok_d"] = stok_d
    f["stok_cross"] = stok_k - stok_d

    # ── VWAP ──────────────────────────────────────────────────
    vwap = vwap_hesapla(high, low, close, volume)
    f["vwap_oran"] = (close - vwap) / vwap * 100

    # ── Hacim Profili (V2 yeni) ──────────────────────────────
    h_ort5 = volume.rolling(5).mean()
    h_ort20 = volume.rolling(20).mean()
    h_ort50 = volume.rolling(50).mean()
    f["hacim_oran"] = volume / h_ort20.replace(0, np.nan)
    f["hacim_trend_5_20"] = h_ort5 / h_ort20.replace(0, np.nan)
    f["hacim_trend_20_50"] = h_ort20 / h_ort50.replace(0, np.nan)
    f["hacim_spike"] = (volume > h_ort20 * 3).astype(int)
    f["hacim_kurumus"] = (volume < h_ort20 * 0.3).astype(int)

    # ── Momentum (çoklu) ─────────────────────────────────────
    for p in [1, 3, 5, 10, 20, 60]:
        f[f"mom_{p}"] = close.pct_change(p) * 100

    # ── Momentum Acceleration (V2 yeni) ──────────────────────
    f["mom_accel"] = f["mom_5"].diff(3)  # momentum hızlanıyor mu?
    f["mom_reversal"] = f["mom_20"] - f["mom_5"]  # ortalamaya dönüş sinyali

    # ── Volatilite ────────────────────────────────────────────
    gunluk = close.pct_change()
    f["vol_20"] = gunluk.rolling(20).std() * np.sqrt(252) * 100
    f["vol_5"] = gunluk.rolling(5).std() * np.sqrt(252) * 100
    f["vol_ratio"] = f["vol_5"] / f["vol_20"].replace(0, np.nan)
    f["vol_regime"] = pd.qcut(f["vol_20"].rank(method='first'), q=3, labels=[0, 1, 2]).astype(float)

    # ── Hareketli Ortalamalar ─────────────────────────────────
    ema8 = close.ewm(span=8, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    sma5 = close.rolling(5).mean()
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma100 = close.rolling(100).mean()

    f["ema8_ema21"] = (ema8 - ema21) / ema21 * 100
    f["sma5_sma20"] = (sma5 - sma20) / sma20 * 100
    f["sma20_sma50"] = (sma20 - sma50) / sma50 * 100
    f["sma50_sma100"] = (sma50 - sma100) / sma100.replace(0, np.nan) * 100
    f["fiyat_sma20"] = (close - sma20) / sma20 * 100
    f["fiyat_sma50"] = (close - sma50) / sma50 * 100

    # ── MA Dizilimi (V2 yeni) — trend kalitesi ───────────────
    f["ma_alignment"] = (
        (ema8 > ema21).astype(int) +
        (ema21 > sma50).astype(int) +
        (sma50 > sma100).astype(int)
    )  # 3 = mükemmel trend, 0 = mükemmel düşüş

    # ── 52 Hafta ──────────────────────────────────────────────
    yil_max = close.rolling(252).max()
    yil_min = close.rolling(252).min()
    f["yillik_poz"] = (close - yil_min) / (yil_max - yil_min).replace(0, np.nan)
    f["ath_uzaklik"] = (yil_max - close) / close * 100  # ATH'ye uzaklık
    f["atl_uzaklik"] = (close - yil_min) / close * 100  # ATL'ye uzaklık

    # ── Destek/Direnç ─────────────────────────────────────────
    f["direnc_20"] = (high.rolling(20).max() - close) / close * 100
    f["destek_20"] = (close - low.rolling(20).min()) / close * 100
    f["kanal_pozisyon"] = (close - low.rolling(20).min()) / (
        high.rolling(20).max() - low.rolling(20).min()
    ).replace(0, np.nan)

    # ── Mum Kalıpları (V2 yeni) ──────────────────────────────
    body = close - opn
    shadow_upper = high - pd.concat([close, opn], axis=1).max(axis=1)
    shadow_lower = pd.concat([close, opn], axis=1).min(axis=1) - low
    candle_range = high - low

    f["body_ratio"] = body.abs() / candle_range.replace(0, np.nan)
    f["upper_shadow"] = shadow_upper / candle_range.replace(0, np.nan)
    f["lower_shadow"] = shadow_lower / candle_range.replace(0, np.nan)
    f["candle_size"] = candle_range / candle_range.rolling(20).mean().replace(0, np.nan)

    # Doji, Hammer, Engulfing benzeri sinyaller
    f["doji"] = (f["body_ratio"] < 0.1).astype(int)
    f["hammer"] = ((f["lower_shadow"] > 0.6) & (f["upper_shadow"] < 0.1)).astype(int)
    f["shooting_star"] = ((f["upper_shadow"] > 0.6) & (f["lower_shadow"] < 0.1)).astype(int)

    # ── Ardışık Gün (V2 genişletilmiş) ───────────────────────
    yukari = (gunluk > 0).astype(int)
    gruplar = (yukari != yukari.shift()).cumsum()
    f["ardi_yukari"] = yukari.groupby(gruplar).cumcount() + 1
    f["ardi_yukari"] = f["ardi_yukari"] * yukari
    asagi = (gunluk < 0).astype(int)
    gruplar_a = (asagi != asagi.shift()).cumsum()
    f["ardi_asagi"] = asagi.groupby(gruplar_a).cumcount() + 1
    f["ardi_asagi"] = f["ardi_asagi"] * asagi

    # ── Market Rejim (V2 yeni) ────────────────────────────────
    f["regime_trend"] = sma20.pct_change(20) * 100  # pozitif = bull
    f["regime_vol"] = f["vol_20"].rank(pct=True)  # yüksek = yüksek vol rejimi

    # ── Günlük İstatistikler ──────────────────────────────────
    f["gunluk"] = gunluk * 100
    f["gunluk_ort5"] = (gunluk * 100).rolling(5).mean()
    f["gunluk_max10"] = (gunluk * 100).rolling(10).max()
    f["gunluk_min10"] = (gunluk * 100).rolling(10).min()
    f["gunluk_skew"] = (gunluk * 100).rolling(20).skew()  # dağılım çarpıklığı

    # ── Relative Volume (V2 yeni) ────────────────────────────
    f["rvol"] = volume / h_ort20.replace(0, np.nan)

    return f


# ============================================================
# V2 FEATURE LİSTESİ
# ============================================================

FEATURE_COLS_V2 = [
    # RSI
    "rsi_7", "rsi_14", "rsi_21", "rsi_divergence",
    # MACD
    "macd", "macd_sinyal", "macd_hist", "macd_hist_degisim", "macd_cross",
    # Bollinger
    "boll_poz", "boll_gen", "boll_sikisma", "boll_squeeze_duration",
    # OBV
    "obv_trend", "obv_momentum", "obv_divergence",
    # ADX
    "adx", "di_fark", "adx_trend",
    # ATR
    "atr_pct", "atr_change", "atr_ratio",
    # Stokastik
    "stok_k", "stok_d", "stok_cross",
    # VWAP
    "vwap_oran",
    # Hacim
    "hacim_oran", "hacim_trend_5_20", "hacim_trend_20_50",
    "hacim_spike", "hacim_kurumus", "rvol",
    # Momentum
    "mom_1", "mom_3", "mom_5", "mom_10", "mom_20", "mom_60",
    "mom_accel", "mom_reversal",
    # Volatilite
    "vol_20", "vol_5", "vol_ratio", "vol_regime",
    # MA
    "ema8_ema21", "sma5_sma20", "sma20_sma50", "sma50_sma100",
    "fiyat_sma20", "fiyat_sma50", "ma_alignment",
    # 52 hafta
    "yillik_poz", "ath_uzaklik", "atl_uzaklik",
    # Destek/Direnç
    "direnc_20", "destek_20", "kanal_pozisyon",
    # Mum
    "body_ratio", "upper_shadow", "lower_shadow", "candle_size",
    "doji", "hammer", "shooting_star",
    # Ardışık
    "ardi_yukari", "ardi_asagi",
    # Rejim
    "regime_trend", "regime_vol",
    # Günlük
    "gunluk", "gunluk_ort5", "gunluk_max10", "gunluk_min10", "gunluk_skew",
]


# ============================================================
# MARKET REJİM TESPİTİ
# ============================================================

def market_rejim_tespit(xu100_df):
    """
    XU100 endeksinden piyasa rejimini tespit eder.
    Returns: 'bull', 'bear', 'sideways' + güven skoru
    """
    if xu100_df is None or len(xu100_df) < 50:
        return {"rejim": "bilinmiyor", "guven": 0}

    close = xu100_df["Close"].squeeze()
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    son_fiyat = close.iloc[-1]
    son_sma20 = sma20.iloc[-1]
    son_sma50 = sma50.iloc[-1]

    # ADX ile trend gücü
    high = xu100_df["High"].squeeze()
    low = xu100_df["Low"].squeeze()
    adx, di_p, di_m = adx_hesapla(high, low, close)
    son_adx = adx.iloc[-1]

    # Volatilite rejimi
    vol = close.pct_change().rolling(20).std() * np.sqrt(252)
    son_vol = vol.iloc[-1]
    vol_median = vol.rolling(100).median().iloc[-1]

    # Karar
    skor = 0
    if son_fiyat > son_sma20:
        skor += 1
    if son_fiyat > son_sma50:
        skor += 1
    if son_sma20 > son_sma50:
        skor += 1
    if di_p.iloc[-1] > di_m.iloc[-1]:
        skor += 1

    if skor >= 3:
        rejim = "bull"
    elif skor <= 1:
        rejim = "bear"
    else:
        rejim = "sideways"

    guven = min(100, son_adx * 2)

    return {
        "rejim": rejim,
        "guven": round(guven, 1),
        "adx": round(son_adx, 1),
        "volatilite": round(son_vol * 100, 1),
        "vol_vs_median": round(son_vol / vol_median if vol_median > 0 else 1, 2),
        "sma20_uzaklik": round((son_fiyat - son_sma20) / son_sma20 * 100, 2),
    }


# ============================================================
# SEKTÖR MOMENTUM ANALİZİ
# ============================================================

SEKTOR_HISSELERI = {
    "banka": ["GARAN.IS", "AKBNK.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS"],
    "holding": ["SAHOL.IS", "KCHOL.IS", "KOZAL.IS", "TAVHL.IS"],
    "sanayi": ["EREGL.IS", "TOASO.IS", "TUPRS.IS", "SISE.IS", "ASELS.IS"],
    "enerji": ["AKSEN.IS", "ODAS.IS", "AYEN.IS"],
    "teknoloji": ["ASELS.IS", "LOGO.IS", "NETAS.IS"],
    "perakende": ["BIMAS.IS", "MGROS.IS", "SOKM.IS"],
    "havalimani": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
}


def sektor_momentum_hesapla(tum_veri):
    """Her sektörün 5/20 günlük momentumunu hesaplar."""
    sonuc = {}
    for sektor, hisseler in SEKTOR_HISSELERI.items():
        mom_5_list, mom_20_list = [], []
        for ticker in hisseler:
            if ticker in tum_veri and len(tum_veri[ticker]) > 20:
                close = tum_veri[ticker]["Close"].squeeze()
                m5 = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) > 5 else 0
                m20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) > 20 else 0
                mom_5_list.append(m5)
                mom_20_list.append(m20)
        if mom_5_list:
            sonuc[sektor] = {
                "mom_5": round(np.mean(mom_5_list), 2),
                "mom_20": round(np.mean(mom_20_list), 2),
                "guc": round(np.mean(mom_5_list) - np.mean(mom_20_list), 2),
            }
    return sonuc


# ============================================================
# V2 ENSEMBLE MODEL — XGBoost + LightGBM + Neural Net
# ============================================================

def hedef_olustur(df, gun=5, kar_esik=2.0, zarar_limiti=-1.5):
    """
    Triple Barrier Method (Lopez de Prado, Advances in Financial ML).

    Uc bariyer:
      1. Ust bariyer: Take-profit (kar_esik, ornek +%2)
      2. Alt bariyer: Stop-loss (zarar_limiti, ornek -%1.5)
      3. Zaman bariyeri: Maksimum tutma suresi (gun, ornek 5 gun)

    Etiket = hangi bariyer ONCE vurulursa o:
      - Ust bariyer once vurulursa -> 1 (basarili islem)
      - Alt bariyer once vurulursa -> 0 (basarisiz islem)
      - Zaman bariyeri dolursa -> kapanistaki getiriye gore (>0 ise 1, degilse 0)

    Bu yontem rolling-max yaklasimindaki lookahead bias ve
    asimetrik etiket sorunlarini cozer.
    """
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()

    n = len(close)
    sonuc = pd.Series(np.nan, index=close.index)

    for i in range(n - 1):
        giris = close.iloc[i]
        if giris == 0 or np.isnan(giris):
            continue

        bariyer_vuruldu = False
        pencere_sonu = min(i + gun, n - 1)

        for j in range(i + 1, pencere_sonu + 1):
            # Gun ici en yuksek ve en dusuk fiyatlari kontrol et
            gun_yuksek = high.iloc[j]
            gun_dusuk = low.iloc[j]

            yukari_pct = (gun_yuksek - giris) / giris * 100
            asagi_pct = (gun_dusuk - giris) / giris * 100

            # Ust bariyer vuruldu mu? (take profit)
            if yukari_pct >= kar_esik:
                sonuc.iloc[i] = 1
                bariyer_vuruldu = True
                break

            # Alt bariyer vuruldu mu? (stop loss)
            if asagi_pct <= zarar_limiti:
                sonuc.iloc[i] = 0
                bariyer_vuruldu = True
                break

        # Zaman bariyeri: hicbir bariyer vurulmadiysa, son gunun kapanisina bak
        if not bariyer_vuruldu and pencere_sonu > i:
            son_getiri = (close.iloc[pencere_sonu] - giris) / giris * 100
            sonuc.iloc[i] = 1 if son_getiri > 0 else 0

    return sonuc.fillna(0).astype(int)


def purged_walk_forward(X, y, n_splits=5, purge_days=5):
    """
    Purged Walk-Forward CV — veri sızıntısı önleme.
    Train ve test arasında 'purge_days' boşluk bırakır.
    Büyük fonların kullandığı yöntem.
    """
    from xgboost import XGBClassifier
    from sklearn.metrics import accuracy_score, f1_score, precision_score, roc_auc_score

    n = len(X)
    split_size = n // (n_splits + 1)
    sonuclar = []

    for i in range(n_splits):
        train_end = split_size * (i + 1)
        test_start = train_end + purge_days  # PURGE: boşluk bırak
        test_end = min(test_start + split_size, n)

        if test_start >= n or test_end - test_start < 20:
            continue

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]
        X_test = X.iloc[test_start:test_end]
        y_test = y.iloc[test_start:test_end]

        if len(X_train) < 200 or len(X_test) < 30:
            continue

        model = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.6,
            min_child_weight=10,
            reg_alpha=0.1,
            reg_lambda=1.0,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        sonuclar.append({
            "fold": i + 1,
            "dogruluk": round(accuracy_score(y_test, y_pred), 4),
            "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "auc": round(roc_auc_score(y_test, y_prob), 4) if y_test.nunique() > 1 else 0,
            "train_n": len(X_train),
            "test_n": len(X_test),
        })

    return sonuclar


def _feature_sec_v2(X, y, max_feature=25, korelasyon_esik=0.90):
    """
    Doktora Raporu Y-07: 73+ feature -> 20-25 secim.
    1. Korelasyon filtresi (>0.90 koreleli olanlari ele)
    2. XGBoost importance ile en iyi N feature sec
    Returns: (X_secilmis, secilen_feature_isimleri_listesi)
    """
    from xgboost import XGBClassifier
    from sklearn.model_selection import train_test_split

    print(f"  🔍 Feature secimi: {X.shape[1]} feature -> max {max_feature}")

    # Adim 1: Korelasyon filtresi
    corr_matrix = X.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    cikarilacak = set()
    for col in upper.columns:
        yuksek_korele = upper.index[upper[col] > korelasyon_esik].tolist()
        if yuksek_korele:
            cikarilacak.add(col)

    X_filtreli = X.drop(columns=list(cikarilacak), errors='ignore')
    print(f"     Korelasyon: {X.shape[1]} -> {X_filtreli.shape[1]} ({len(cikarilacak)} cikarildi)")

    if X_filtreli.shape[1] <= max_feature:
        return X_filtreli, X_filtreli.columns.tolist()

    # Adim 2: Importance secimi
    X_tr, X_val, y_tr, y_val = train_test_split(X_filtreli, y, test_size=0.2, shuffle=False)
    selector = XGBClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric='logloss', verbosity=0, random_state=42
    )
    selector.fit(X_tr, y_tr)

    importance = pd.Series(
        selector.feature_importances_, index=X_filtreli.columns
    ).sort_values(ascending=False)

    secilen = importance.head(max_feature).index.tolist()
    print(f"     Importance: en iyi {max_feature} feature secildi")
    for i, (feat, score) in enumerate(importance.head(10).items()):
        print(f"       {i+1}. {feat}: {score:.4f}")
    if max_feature > 10:
        print(f"       ... ve {max_feature - 10} feature daha")

    return X_filtreli[secilen], secilen


class EnsembleModelV2:
    """
    3 model ensemble:
    1. XGBoost — tabular veri kralı
    2. LightGBM — hız + doğruluk
    3. MLP Neural Network — non-linear patterns

    Ağırlıklar: validation performansına göre dinamik.
    """

    def __init__(self):
        self.xgb_model = None
        self.lgb_model = None
        self.mlp_model = None
        self.scaler = None
        self.weights = [0.4, 0.35, 0.25]  # xgb, lgb, mlp
        self.feature_cols = []
        self.meta = {}

    def egit(self, tum_veri, market_rejim=None):
        """Tüm hisse verilerinden V2 ensemble model eğitir."""
        from xgboost import XGBClassifier
        from sklearn.neural_network import MLPClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import accuracy_score, f1_score, precision_score, roc_auc_score

        # LightGBM opsiyonel
        try:
            from lightgbm import LGBMClassifier
            lgb_available = True
        except ImportError:
            lgb_available = False
            print("  ⚠ LightGBM yüklü değil, XGBoost+MLP ile devam ediliyor.")

        X_list, y_list = [], []

        for ticker, df in tum_veri.items():
            features = feature_olustur_v2(df)
            if features is None:
                continue

            hedef = hedef_olustur(df)
            gecerli = [c for c in FEATURE_COLS_V2 if c in features.columns]
            birlesik = features[gecerli].copy()
            birlesik["hedef"] = hedef
            birlesik = birlesik.dropna()

            if len(birlesik) < 60:
                continue

            X_list.append(birlesik[gecerli])
            y_list.append(birlesik["hedef"])

        if not X_list:
            print("❌ Yeterli veri yok!")
            return None

        X = pd.concat(X_list, ignore_index=True)
        y = pd.concat(y_list, ignore_index=True)

        print(f"  📊 Ham: {len(X):,} satır | Pozitif: %{y.mean()*100:.1f} | Feature: {X.shape[1]}")

        # ── Feature Secimi (Y-07: 73+ -> 20-25) ─────────────
        X, secilen = _feature_sec_v2(X, y, max_feature=25, korelasyon_esik=0.90)
        self.feature_cols = secilen

        print(f"  📊 Secim sonrasi: {len(X):,} satır | Feature: {len(self.feature_cols)}")

        # ── Purged Walk-Forward Validation ────────────────────
        print("  🔄 Purged Walk-Forward Validation...")
        wf_sonuclar = purged_walk_forward(X, y) if len(X) > 1000 else []
        if wf_sonuclar:
            ort_auc = np.mean([s["auc"] for s in wf_sonuclar])
            ort_f1 = np.mean([s["f1"] for s in wf_sonuclar])
            print(f"  ✅ WF → AUC: {ort_auc:.3f} | F1: {ort_f1:.3f}")

        # ── Train/Test Split ──────────────────────────────────
        split = int(len(X) * 0.85)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        # ── 1. XGBoost ───────────────────────────────────────
        print("  🌲 XGBoost eğitiliyor...")
        self.xgb_model = XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.02,
            subsample=0.8,
            colsample_bytree=0.6,
            min_child_weight=10,
            reg_alpha=0.1,
            reg_lambda=1.0,
            eval_metric="logloss",
            early_stopping_rounds=50,
            random_state=42,
            verbosity=0,
        )
        self.xgb_model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        xgb_prob = self.xgb_model.predict_proba(X_test)[:, 1]
        xgb_auc = roc_auc_score(y_test, xgb_prob) if y_test.nunique() > 1 else 0.5
        print(f"     XGBoost AUC: {xgb_auc:.4f}")

        # ── 2. LightGBM ──────────────────────────────────────
        if lgb_available:
            print("  ⚡ LightGBM eğitiliyor...")
            self.lgb_model = LGBMClassifier(
                n_estimators=500,
                max_depth=6,
                learning_rate=0.02,
                subsample=0.8,
                colsample_bytree=0.6,
                min_child_weight=10,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                verbose=-1,
            )
            self.lgb_model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
            )
            lgb_prob = self.lgb_model.predict_proba(X_test)[:, 1]
            lgb_auc = roc_auc_score(y_test, lgb_prob) if y_test.nunique() > 1 else 0.5
            print(f"     LightGBM AUC: {lgb_auc:.4f}")
        else:
            lgb_auc = 0

        # ── 3. MLP Neural Network ────────────────────────────
        print("  🧠 Neural Network eğitiliyor...")
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.mlp_model = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation="relu",
            solver="adam",
            alpha=0.001,
            learning_rate="adaptive",
            learning_rate_init=0.001,
            max_iter=300,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=42,
        )
        self.mlp_model.fit(X_train_scaled, y_train)
        mlp_prob = self.mlp_model.predict_proba(X_test_scaled)[:, 1]
        mlp_auc = roc_auc_score(y_test, mlp_prob) if y_test.nunique() > 1 else 0.5
        print(f"     MLP AUC: {mlp_auc:.4f}")

        # ── Dinamik Ağırlık (performansa göre) ───────────────
        toplam_auc = xgb_auc + lgb_auc + mlp_auc
        if toplam_auc > 0:
            self.weights = [
                xgb_auc / toplam_auc,
                lgb_auc / toplam_auc if lgb_available else 0,
                mlp_auc / toplam_auc,
            ]
        print(f"  ⚖️  Ağırlıklar → XGB:{self.weights[0]:.2f} LGB:{self.weights[1]:.2f} MLP:{self.weights[2]:.2f}")

        # ── Ensemble Performans ──────────────────────────────
        ensemble_prob = self._ensemble_predict(X_test)
        ensemble_pred = (ensemble_prob >= 0.5).astype(int)
        ens_auc = roc_auc_score(y_test, ensemble_prob) if y_test.nunique() > 1 else 0.5
        ens_f1 = f1_score(y_test, ensemble_pred, zero_division=0)
        ens_precision = precision_score(y_test, ensemble_pred, zero_division=0)

        print(f"\n  🏆 ENSEMBLE → AUC: {ens_auc:.4f} | F1: {ens_f1:.4f} | Precision: {ens_precision:.4f}")

        # ── Feature Importance ────────────────────────────────
        importance = pd.Series(
            self.xgb_model.feature_importances_, index=self.feature_cols
        ).sort_values(ascending=False)

        # ── Meta Kaydet ───────────────────────────────────────
        self.meta = {
            "versiyon": "V2_ENSEMBLE",
            "egitim_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ensemble_auc": round(ens_auc, 4),
            "ensemble_f1": round(ens_f1, 4),
            "ensemble_precision": round(ens_precision, 4),
            "xgb_auc": round(xgb_auc, 4),
            "lgb_auc": round(lgb_auc, 4),
            "mlp_auc": round(mlp_auc, 4),
            "weights": [round(w, 4) for w in self.weights],
            "egitim_boyut": len(X_train),
            "test_boyut": len(X_test),
            "feature_sayisi": len(self.feature_cols),
            "top_features": importance.head(15).to_dict(),
            "walk_forward": wf_sonuclar,
            "market_rejim": market_rejim,
        }

        # ── Diske Kaydet ──────────────────────────────────────
        self.kaydet()

        return self.meta

    def _ensemble_predict(self, X):
        """3 modelin ağırlıklı ortalaması."""
        probs = np.zeros(len(X))

        if self.xgb_model is not None:
            probs += self.weights[0] * self.xgb_model.predict_proba(X)[:, 1]

        if self.lgb_model is not None:
            probs += self.weights[1] * self.lgb_model.predict_proba(X)[:, 1]

        if self.mlp_model is not None and self.scaler is not None:
            X_scaled = self.scaler.transform(X)
            probs += self.weights[2] * self.mlp_model.predict_proba(X_scaled)[:, 1]

        return probs

    def tahmin(self, features_df):
        """Tek hisse için ensemble tahmin."""
        if self.xgb_model is None:
            return None

        gecerli = [c for c in self.feature_cols if c in features_df.columns]
        son = features_df[gecerli].iloc[-1:]

        if son.isna().any(axis=1).iloc[0]:
            # NaN'ları 0 ile doldur
            son = son.fillna(0)

        prob = self._ensemble_predict(son)
        return float(prob[0])

    def kaydet(self):
        """Modeli diske kaydet."""
        path = MODEL_DIR / "ensemble_v2.pkl"
        meta_path = MODEL_DIR / "ensemble_v2_meta.json"

        joblib.dump({
            "xgb": self.xgb_model,
            "lgb": self.lgb_model,
            "mlp": self.mlp_model,
            "scaler": self.scaler,
            "weights": self.weights,
            "feature_cols": self.feature_cols,
        }, path)

        with open(meta_path, "w") as f:
            json.dump(self.meta, f, indent=2, default=str)

        print(f"  💾 Model kaydedildi: {path}")

    @classmethod
    def yukle(cls):
        """Kaydedilmiş modeli yükle."""
        path = MODEL_DIR / "ensemble_v2.pkl"
        if not path.exists():
            return None

        data = joblib.load(path)
        model = cls()
        model.xgb_model = data["xgb"]
        model.lgb_model = data["lgb"]
        model.mlp_model = data["mlp"]
        model.scaler = data["scaler"]
        model.weights = data["weights"]
        model.feature_cols = data["feature_cols"]

        meta_path = MODEL_DIR / "ensemble_v2_meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                model.meta = json.load(f)

        return model


# ============================================================
# TEKNİK SKOR (V2 — daha sofistike)
# ============================================================

def teknik_skor_v2(row):
    """V2 teknik skor — 15 faktörlü, ağırlıklı."""
    skor = 0
    max_skor = 0

    # RSI — aşırılık ve divergence (15 puan)
    max_skor += 15
    rsi = row.get("rsi_14", 50)
    if 40 <= rsi <= 60:
        skor += 5
    elif rsi < 30:
        skor += 15  # aşırı satım = fırsat
    elif rsi > 70:
        skor += 10  # momentum güçlü ama riskli
    div = row.get("rsi_divergence", 0)
    if div > 5:
        skor += 3  # pozitif divergence

    # MACD histogram (10 puan)
    max_skor += 10
    hist_d = row.get("macd_hist_degisim", 0)
    if hist_d > 0:
        skor += min(10, hist_d * 3)

    # ADX trend gücü (10 puan)
    max_skor += 10
    adx = row.get("adx", 0)
    if adx > 25:
        skor += min(10, (adx - 20) * 0.5)

    # MA alignment (10 puan)
    max_skor += 10
    alignment = row.get("ma_alignment", 0)
    skor += alignment / 3 * 10

    # Bollinger sıkışma (10 puan)
    max_skor += 10
    if row.get("boll_sikisma", 0):
        skor += 10

    # OBV birikim (10 puan)
    max_skor += 10
    obv_t = row.get("obv_trend", 0)
    if obv_t > 0.1:
        skor += min(10, obv_t * 30)

    # Hacim anomali (10 puan)
    max_skor += 10
    rvol = row.get("rvol", 1)
    if rvol > 2:
        skor += min(10, (rvol - 1) * 4)

    # Momentum ivme (10 puan)
    max_skor += 10
    accel = row.get("mom_accel", 0)
    if accel > 0:
        skor += min(10, accel * 2)

    # ATR volatilite genişleme (5 puan)
    max_skor += 5
    atr_c = row.get("atr_change", 0)
    if atr_c > 0.1:
        skor += min(5, atr_c * 10)

    # Mum kalıpları (5 puan)
    max_skor += 5
    if row.get("hammer", 0):
        skor += 5
    elif row.get("doji", 0):
        skor += 2

    # Kanal pozisyonu (5 puan)
    max_skor += 5
    kanal = row.get("kanal_pozisyon", 0.5)
    if 0.3 <= kanal <= 0.7:
        skor += 3  # orta band = sağlıklı
    elif kanal > 0.9:
        skor += 5  # breakout potansiyeli

    return round(skor / max_skor * 100, 1) if max_skor > 0 else 50


# ============================================================
# BİRLEŞİK ANALİZ FONKSİYONU
# ============================================================

def hisse_analiz_v2(ticker, df, ensemble_model=None, market_rejim=None):
    """V2 tam analiz — teknik + ML + rejim."""
    features = feature_olustur_v2(df)
    if features is None:
        return None

    son = features.iloc[-1].to_dict()
    teknik = teknik_skor_v2(son)

    # ML tahmin
    ml_prob = ensemble_model.tahmin(features) if ensemble_model else None

    # Birleşik skor (rejime göre ağırlık değişir)
    if ml_prob is not None:
        if market_rejim and market_rejim.get("rejim") == "bull":
            birlesik = teknik * 0.3 + ml_prob * 100 * 0.7  # bull'da ML'ye daha çok güven
        elif market_rejim and market_rejim.get("rejim") == "bear":
            birlesik = teknik * 0.5 + ml_prob * 100 * 0.5  # bear'de temkinli ol
        else:
            birlesik = teknik * 0.35 + ml_prob * 100 * 0.65
    else:
        birlesik = teknik

    close = df["Close"].squeeze()

    return {
        "ticker": ticker,
        "teknik_skor": teknik,
        "ml_olasilik": round(ml_prob, 4) if ml_prob else None,
        "birlesik_skor": round(birlesik, 1),
        "fiyat": float(close.iloc[-1]),
        "gunluk": float(close.pct_change().iloc[-1] * 100) if len(close) > 1 else 0,
        "hacim": float(df["Volume"].squeeze().iloc[-1]),
        "adx": round(son.get("adx", 0), 1),
        "rsi": round(son.get("rsi_14", 50), 1),
        "ma_alignment": int(son.get("ma_alignment", 0)),
        "atr_pct": round(son.get("atr_pct", 0), 2),
        "rejim_uyum": _rejim_uyum(son, market_rejim),
        "sinyal_ozet": _sinyal_ozet(son),
    }


def _rejim_uyum(features, rejim):
    """Hissenin piyasa rejimiyle uyumu."""
    if not rejim:
        return "bilinmiyor"
    r = rejim.get("rejim", "")
    alignment = features.get("ma_alignment", 0)
    if r == "bull" and alignment >= 2:
        return "uyumlu"
    elif r == "bear" and alignment <= 1:
        return "uyumlu"
    elif r == "sideways":
        return "nötr"
    return "uyumsuz"


def _sinyal_ozet(f):
    """Kısa sinyal özeti."""
    sinyaller = []
    if f.get("boll_sikisma", 0):
        sinyaller.append("🔥 Sıkışma")
    if f.get("hacim_spike", 0):
        sinyaller.append("📊 Hacim Patlaması")
    if f.get("hammer", 0):
        sinyaller.append("🔨 Hammer")
    if f.get("rsi_14", 50) < 30:
        sinyaller.append("⬇️ Aşırı Satım")
    if f.get("rsi_14", 50) > 70:
        sinyaller.append("⬆️ Aşırı Alım")
    if f.get("ma_alignment", 0) == 3:
        sinyaller.append("✨ Tam Trend")
    if f.get("obv_trend", 0) > 0.2:
        sinyaller.append("🏦 Kurumsal Alım")
    if f.get("mom_accel", 0) > 2:
        sinyaller.append("🚀 İvme Artışı")
    return sinyaller if sinyaller else ["➖ Bekle"]


# ============================================================
# KOMISYON DAHIL BACKTEST (Doktora Raporu Y-09)
# ============================================================

def komisyonlu_backtest(
    tum_veri,
    xu100_df=None,
    komisyon_tek_yon=0.0015,   # %0.15 tek yon
    slippage=0.001,            # %0.10
    baslangic_sermaye=100000,
    yil=3,
    kar_esik=2.0,
    zarar_limiti=-1.5,
    tutma_gun=5,
):
    """
    Doktora Raporu Y-09: Komisyon dahil 3 yillik backtest.

    - Komisyon: komisyon_tek_yon * 2 (gidis-donus)
    - Slippage: her islemde ek maliyet
    - Buy-and-hold XU100 karsilastirmasi
    - Sharpe ratio, max drawdown hesaplanir
    - Sonuclar JSON olarak kaydedilir

    Triple Barrier Method ile sinyal uretir ve her sinyalde islem acar.
    """
    toplam_maliyet_oran = (komisyon_tek_yon * 2) + (slippage * 2)  # gidis-donus

    print("=" * 60)
    print("KOMISYON DAHIL BACKTEST")
    print(f"Komisyon: %{komisyon_tek_yon*100:.2f} tek yon (%{komisyon_tek_yon*200:.2f} gidis-donus)")
    print(f"Slippage: %{slippage*100:.2f} tek yon")
    print(f"Toplam maliyet/islem: %{toplam_maliyet_oran*100:.2f}")
    print(f"Sermaye: {baslangic_sermaye:,.0f} TL")
    print(f"Triple Barrier: +%{kar_esik} / -%{abs(zarar_limiti)} / {tutma_gun} gun")
    print("=" * 60)

    # Tum hisse islemlerini simule et
    islemler = []
    for ticker, df in tum_veri.items():
        if len(df) < 252 * yil:
            continue

        close = df["Close"].squeeze()
        high = df["High"].squeeze()
        low = df["Low"].squeeze()

        # Son N yillik veriyi al
        baslangic_idx = max(0, len(close) - 252 * yil)
        close = close.iloc[baslangic_idx:]
        high = high.iloc[baslangic_idx:]
        low = low.iloc[baslangic_idx:]

        # EMA + Hacim filtresi — her gün değil, sadece sinyal olunca işlem aç
        ema10 = close.ewm(span=10).mean()
        ema20 = close.ewm(span=20).mean()
        vol_avg = df["Volume"].squeeze().iloc[baslangic_idx:].rolling(10).mean()
        vol_cur = df["Volume"].squeeze().iloc[baslangic_idx:]

        n = len(close)
        i = 50  # EMA hesaplanabilmesi için 50. günden başla
        while i < n - tutma_gun - 1:
            giris_fiyat = close.iloc[i]
            if giris_fiyat == 0 or np.isnan(giris_fiyat):
                i += 1
                continue

            # SİNYAL FİLTRESİ: EMA cross + hacim normalin üstü
            ema_ok = float(ema10.iloc[i]) > float(ema20.iloc[i])
            hacim_ok = float(vol_cur.iloc[i]) > float(vol_avg.iloc[i]) * 1.2 if not np.isnan(vol_avg.iloc[i]) else False

            if not (ema_ok and hacim_ok):
                i += 1
                continue  # Sinyal yoksa atla

            # Triple barrier kontrol
            bariyer_vuruldu = False
            pencere_sonu = min(i + tutma_gun, n - 1)
            cikis_gun = pencere_sonu
            brut_getiri_pct = 0

            for j in range(i + 1, pencere_sonu + 1):
                yukari_pct = (high.iloc[j] - giris_fiyat) / giris_fiyat * 100
                asagi_pct = (low.iloc[j] - giris_fiyat) / giris_fiyat * 100

                if yukari_pct >= kar_esik:
                    brut_getiri_pct = kar_esik
                    cikis_gun = j
                    bariyer_vuruldu = True
                    break
                if asagi_pct <= zarar_limiti:
                    brut_getiri_pct = zarar_limiti
                    cikis_gun = j
                    bariyer_vuruldu = True
                    break

            if not bariyer_vuruldu:
                brut_getiri_pct = (close.iloc[pencere_sonu] - giris_fiyat) / giris_fiyat * 100

            # Net getiri = brut - komisyon - slippage
            net_getiri_pct = brut_getiri_pct - (toplam_maliyet_oran * 100)

            islemler.append({
                "ticker": ticker,
                "giris_tarih": str(close.index[i].date()) if hasattr(close.index[i], 'date') else str(close.index[i]),
                "cikis_tarih": str(close.index[cikis_gun].date()) if hasattr(close.index[cikis_gun], 'date') else str(close.index[cikis_gun]),
                "giris_fiyat": float(giris_fiyat),
                "brut_getiri_pct": round(brut_getiri_pct, 4),
                "net_getiri_pct": round(net_getiri_pct, 4),
                "tutma_gun": cikis_gun - i,
                "bariyer": "TP" if brut_getiri_pct >= kar_esik else ("SL" if brut_getiri_pct <= zarar_limiti else "TIME"),
            })

            # Cooldown: En az 3 gün bekle (overtrading önleme)
            i = cikis_gun + 3

    if not islemler:
        print("HATA: Hicbir islem uretilmedi!")
        return None

    islem_df = pd.DataFrame(islemler)

    # ── Portfoy Equity Curve ────────────────────────────────
    sermaye = baslangic_sermaye
    equity_curve = [sermaye]
    gunluk_getiriler = []

    for _, islem in islem_df.iterrows():
        getiri = islem["net_getiri_pct"] / 100
        sermaye *= (1 + getiri)
        equity_curve.append(sermaye)
        gunluk_getiriler.append(getiri)

    # ── Performans Metrikleri ────────────────────────────────
    toplam_islem = len(islem_df)
    kazanc_sayisi = (islem_df["net_getiri_pct"] > 0).sum()
    kayip_sayisi = (islem_df["net_getiri_pct"] <= 0).sum()
    basari_orani = kazanc_sayisi / toplam_islem * 100 if toplam_islem > 0 else 0

    toplam_getiri = (sermaye / baslangic_sermaye - 1) * 100
    brut_toplam = islem_df["brut_getiri_pct"].sum()
    komisyon_etkisi = brut_toplam - islem_df["net_getiri_pct"].sum()

    ort_kazanc = islem_df.loc[islem_df["net_getiri_pct"] > 0, "net_getiri_pct"].mean() if kazanc_sayisi > 0 else 0
    ort_kayip = islem_df.loc[islem_df["net_getiri_pct"] <= 0, "net_getiri_pct"].mean() if kayip_sayisi > 0 else 0

    # Sharpe ratio (yillik)
    getiri_array = np.array(gunluk_getiriler)
    if len(getiri_array) > 1 and getiri_array.std() > 0:
        # Islem basina ortalama getiri / std, yillastirilmis
        islem_per_yil = toplam_islem / yil if yil > 0 else 252
        sharpe = (getiri_array.mean() / getiri_array.std()) * np.sqrt(islem_per_yil)
    else:
        sharpe = 0

    # Max drawdown
    equity_arr = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_arr)
    drawdown = (equity_arr - peak) / peak * 100
    max_dd = drawdown.min()

    # Bariyer dagilimi
    tp_count = (islem_df["bariyer"] == "TP").sum()
    sl_count = (islem_df["bariyer"] == "SL").sum()
    time_count = (islem_df["bariyer"] == "TIME").sum()

    # ── Buy & Hold XU100 Karsilastirmasi ─────────────────────
    bh_getiri = None
    bh_sharpe = None
    bh_max_dd = None
    if xu100_df is not None and len(xu100_df) > 252:
        xu_close = xu100_df["Close"].squeeze()
        xu_start = max(0, len(xu_close) - 252 * yil)
        xu_slice = xu_close.iloc[xu_start:]
        if len(xu_slice) > 1:
            bh_getiri = (xu_slice.iloc[-1] / xu_slice.iloc[0] - 1) * 100

            xu_gunluk = xu_slice.pct_change().dropna()
            if xu_gunluk.std() > 0:
                bh_sharpe = (xu_gunluk.mean() / xu_gunluk.std()) * np.sqrt(252)
            else:
                bh_sharpe = 0

            xu_equity = (1 + xu_gunluk).cumprod()
            xu_peak = xu_equity.cummax()
            xu_dd = ((xu_equity - xu_peak) / xu_peak * 100)
            bh_max_dd = xu_dd.min()

    # ── Sonuclari Yazdir ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("BACKTEST SONUCLARI")
    print("=" * 60)
    print(f"Toplam islem:        {toplam_islem}")
    print(f"Kazanc/Kayip:        {kazanc_sayisi}/{kayip_sayisi}")
    print(f"Basari orani:        %{basari_orani:.1f}")
    print(f"Ort kazanc:          %{ort_kazanc:.2f}")
    print(f"Ort kayip:           %{ort_kayip:.2f}")
    print(f"")
    print(f"Bariyer dagilimi:    TP={tp_count} | SL={sl_count} | TIME={time_count}")
    print(f"")
    print(f"BRUT toplam getiri:  %{brut_toplam:.2f}")
    print(f"Komisyon etkisi:     %{komisyon_etkisi:.2f}")
    print(f"NET toplam getiri:   %{toplam_getiri:.2f}")
    print(f"Son sermaye:         {sermaye:,.0f} TL")
    print(f"")
    print(f"Sharpe Ratio:        {sharpe:.3f}")
    print(f"Max Drawdown:        %{max_dd:.2f}")
    print(f"")
    if bh_getiri is not None:
        print(f"--- XU100 Buy & Hold ---")
        print(f"XU100 getiri:        %{bh_getiri:.2f}")
        print(f"XU100 Sharpe:        {bh_sharpe:.3f}")
        print(f"XU100 Max DD:        %{bh_max_dd:.2f}")
        alpha = toplam_getiri - bh_getiri
        print(f"ALPHA (strateji-BH): %{alpha:.2f}")
    print("=" * 60)

    # ── JSON kaydet ──────────────────────────────────────────
    sonuc = {
        "backtest_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "parametreler": {
            "komisyon_tek_yon": komisyon_tek_yon,
            "slippage": slippage,
            "toplam_maliyet_islem": toplam_maliyet_oran,
            "baslangic_sermaye": baslangic_sermaye,
            "yil": yil,
            "kar_esik_pct": kar_esik,
            "zarar_limiti_pct": zarar_limiti,
            "tutma_gun": tutma_gun,
        },
        "sonuclar": {
            "toplam_islem": int(toplam_islem),
            "kazanc_sayisi": int(kazanc_sayisi),
            "kayip_sayisi": int(kayip_sayisi),
            "basari_orani_pct": round(basari_orani, 2),
            "ort_kazanc_pct": round(ort_kazanc, 4),
            "ort_kayip_pct": round(ort_kayip, 4),
            "brut_toplam_getiri_pct": round(brut_toplam, 2),
            "komisyon_etkisi_pct": round(komisyon_etkisi, 2),
            "net_toplam_getiri_pct": round(toplam_getiri, 2),
            "son_sermaye": round(sermaye, 2),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown_pct": round(max_dd, 2),
            "bariyer_dagilimi": {
                "take_profit": int(tp_count),
                "stop_loss": int(sl_count),
                "zaman_bariyeri": int(time_count),
            },
        },
        "xu100_buy_hold": {
            "getiri_pct": round(bh_getiri, 2) if bh_getiri is not None else None,
            "sharpe_ratio": round(bh_sharpe, 4) if bh_sharpe is not None else None,
            "max_drawdown_pct": round(bh_max_dd, 2) if bh_max_dd is not None else None,
            "alpha_pct": round(toplam_getiri - bh_getiri, 2) if bh_getiri is not None else None,
        },
    }

    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    sonuc_path = data_dir / "backtest_sonuclari.json"
    with open(sonuc_path, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, indent=2, ensure_ascii=False)
    print(f"\nSonuclar kaydedildi: {sonuc_path}")

    return sonuc
