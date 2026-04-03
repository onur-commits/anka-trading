"""
BIST Sürpriz Hisse Tahmin Motoru v2
- Teknik Analiz Skoru (0-100)
- XGBoost ML Modeli — genişletilmiş feature seti
- Walk-Forward Validation
- Birleşik Sürpriz Skoru
"""

import numpy as np
import pandas as pd
from pathlib import Path
import joblib
import warnings

warnings.filterwarnings("ignore")

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


# ============================================================
# TEKNİK İNDİKATÖRLER
# ============================================================

def rsi_hesapla(seri, periyot=14):
    delta = seri.diff()
    kazanc = delta.where(delta > 0, 0).rolling(periyot).mean()
    kayip = (-delta.where(delta < 0, 0)).rolling(periyot).mean()
    rs = kazanc / kayip.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd_hesapla(seri, hizli=12, yavas=26, sinyal=9):
    ema_hizli = seri.ewm(span=hizli, adjust=False).mean()
    ema_yavas = seri.ewm(span=yavas, adjust=False).mean()
    macd = ema_hizli - ema_yavas
    macd_sinyal = macd.ewm(span=sinyal, adjust=False).mean()
    histogram = macd - macd_sinyal
    return macd, macd_sinyal, histogram


def bollinger_hesapla(seri, periyot=20, std_carpan=2):
    sma = seri.rolling(periyot).mean()
    std = seri.rolling(periyot).std()
    ust = sma + std_carpan * std
    alt = sma - std_carpan * std
    genislik = (ust - alt) / sma * 100
    return sma, ust, alt, genislik


def obv_hesapla(close, volume):
    """On-Balance Volume — birikimli alım/satım baskısı."""
    yon = np.sign(close.diff()).fillna(0)
    obv = (yon * volume).cumsum()
    return obv


def adx_hesapla(high, low, close, periyot=14):
    """Average Directional Index — trend gücü 0-100."""
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    dm_plus = high.diff().clip(lower=0)
    dm_minus = (-low.diff()).clip(lower=0)
    dm_plus = dm_plus.where(dm_plus > dm_minus, 0)
    dm_minus = dm_minus.where(dm_minus > dm_plus, 0)

    atr = tr.ewm(span=periyot, adjust=False).mean()
    di_plus = 100 * dm_plus.ewm(span=periyot, adjust=False).mean() / atr.replace(0, np.nan)
    di_minus = 100 * dm_minus.ewm(span=periyot, adjust=False).mean() / atr.replace(0, np.nan)

    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx = dx.ewm(span=periyot, adjust=False).mean()
    return adx, di_plus, di_minus


def stokastik_hesapla(high, low, close, k_periyot=14, d_periyot=3):
    """Stokastik Osilatör."""
    en_dusuk = low.rolling(k_periyot).min()
    en_yuksek = high.rolling(k_periyot).max()
    k = 100 * (close - en_dusuk) / (en_yuksek - en_dusuk).replace(0, np.nan)
    d = k.rolling(d_periyot).mean()
    return k, d


def vwap_hesapla(high, low, close, volume):
    """VWAP yaklaşımı (günlük reset yok, kümülatif)."""
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap


def feature_olustur(df):
    """Bir hisse DataFrame'inden tüm feature'ları çıkarır."""
    if len(df) < 60:
        return None

    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    volume = df["Volume"].squeeze()

    f = pd.DataFrame(index=df.index)

    # ── Temel Göstergeler ──────────────────────────────────────
    f["rsi"] = rsi_hesapla(close)
    f["rsi_degisim"] = f["rsi"].diff(3)

    macd, macd_sinyal, histogram = macd_hesapla(close)
    f["macd"] = macd
    f["macd_sinyal"] = macd_sinyal
    f["macd_hist"] = histogram
    f["macd_hist_degisim"] = histogram.diff()

    _, ust, alt, genislik = bollinger_hesapla(close)
    f["boll_pozisyon"] = (close - alt) / (ust - alt).replace(0, np.nan)
    f["boll_genislik"] = genislik
    f["boll_sikisma"] = (genislik == genislik.rolling(10).min()).astype(int)

    # ── Yeni: OBV ─────────────────────────────────────────────
    obv = obv_hesapla(close, volume)
    obv_ort = obv.rolling(20).mean()
    f["obv_trend"] = (obv - obv_ort) / obv_ort.abs().replace(0, np.nan)
    f["obv_momentum"] = obv.pct_change(5)

    # ── Yeni: ADX ─────────────────────────────────────────────
    adx, di_plus, di_minus = adx_hesapla(high, low, close)
    f["adx"] = adx
    f["di_fark"] = di_plus - di_minus   # pozitif = yukarı trend güçlü

    # ── Yeni: Stokastik ───────────────────────────────────────
    stok_k, stok_d = stokastik_hesapla(high, low, close)
    f["stok_k"] = stok_k
    f["stok_d"] = stok_d
    f["stok_kesisim"] = (stok_k - stok_d)   # pozitif = K, D'yi geçiyor

    # ── Yeni: VWAP ────────────────────────────────────────────
    vwap = vwap_hesapla(high, low, close, volume)
    f["vwap_oran"] = (close - vwap) / vwap * 100   # pozitif = fiyat VWAP üstünde

    # ── Hacim ─────────────────────────────────────────────────
    hacim_ort20 = volume.rolling(20).mean()
    hacim_ort5 = volume.rolling(5).mean()
    f["hacim_oran"] = volume / hacim_ort20.replace(0, np.nan)
    f["hacim_trend"] = hacim_ort5 / hacim_ort20.replace(0, np.nan)
    f["hacim_artis"] = volume.pct_change(3)   # son 3 günde hacim artışı

    # ── Momentum ──────────────────────────────────────────────
    f["mom_3"] = close.pct_change(3) * 100
    f["mom_5"] = close.pct_change(5) * 100
    f["mom_10"] = close.pct_change(10) * 100
    f["mom_20"] = close.pct_change(20) * 100

    # ── Volatilite ────────────────────────────────────────────
    gunluk_getiri = close.pct_change()
    f["volatilite"] = gunluk_getiri.rolling(20).std() * 100
    f["volatilite_degisim"] = f["volatilite"].pct_change(5)
    f["volatilite_kisalma"] = (f["volatilite"] < f["volatilite"].rolling(10).mean()).astype(int)

    # ── Hareketli Ortalamalar ─────────────────────────────────
    ema8  = close.ewm(span=8, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    sma5  = close.rolling(5).mean()
    sma10 = close.rolling(10).mean()
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    f["fiyat_ema8_oran"]   = (close - ema8) / ema8 * 100
    f["fiyat_sma20_oran"]  = (close - sma20) / sma20 * 100
    f["ema8_ema21_oran"]   = (ema8 - ema21) / ema21 * 100
    f["sma5_sma20_oran"]   = (sma5 - sma20) / sma20 * 100
    f["sma10_sma50_oran"]  = (sma10 - sma50) / sma50 * 100

    # ── Yeni: 52 Hafta Pozisyonu ──────────────────────────────
    yil_max = close.rolling(252).max()
    yil_min = close.rolling(252).min()
    yil_aralik = (yil_max - yil_min).replace(0, np.nan)
    f["yillik_pozisyon"] = (close - yil_min) / yil_aralik

    # ── Günlük Değişim ────────────────────────────────────────
    gunluk = close.pct_change() * 100
    f["gunluk_degisim"] = gunluk
    f["gunluk_ort_5"]   = gunluk.rolling(5).mean()
    f["gunluk_max_10"]  = gunluk.rolling(10).max()
    f["gunluk_min_10"]  = gunluk.rolling(10).min()

    # ── Yeni: Ardışık Gün Serisi ──────────────────────────────
    yukari = (gunluk > 0).astype(int)
    f["ardi_yukari"] = yukari.groupby((yukari != yukari.shift()).cumsum()).cumcount() + 1
    f["ardi_yukari"] = f["ardi_yukari"] * yukari   # sadece yukarı günler

    # ── Destek / Direnç ───────────────────────────────────────
    yuksek_20 = high.rolling(20).max()
    dusuk_20  = low.rolling(20).min()
    f["direnc_yakinlik"] = (yuksek_20 - close) / close * 100
    f["destek_yakinlik"] = (close - dusuk_20) / close * 100

    # ── Yeni: Mum Analizi ─────────────────────────────────────
    gurur = high - low   # günlük mum boyu
    f["mum_boy_oran"] = gurur / gurur.rolling(20).mean().replace(0, np.nan)
    govde = (close - df["Open"].squeeze()).abs()
    f["govde_oran"] = govde / gurur.replace(0, np.nan)   # govde/mum oranı

    return f


# ============================================================
# TEKNİK ANALİZ SKORU (0-100)
# ============================================================

def teknik_skor_hesapla(features_row):
    """Tek satır feature'dan teknik analiz skoru hesaplar."""
    skor = 50

    rsi = features_row.get("rsi", 50)
    if rsi < 30:
        skor += 15 * (30 - rsi) / 30
    elif rsi > 70:
        skor += 15 * (rsi - 70) / 30

    macd_hist = features_row.get("macd_hist_degisim", 0)
    if abs(macd_hist) > 0:
        skor += min(10, abs(macd_hist) * 5)

    if features_row.get("boll_sikisma", 0):
        skor += 15

    boll_poz = features_row.get("boll_pozisyon", 0.5)
    if boll_poz > 1.0 or boll_poz < 0.0:
        skor += 10

    hacim_oran = features_row.get("hacim_oran", 1.0)
    if hacim_oran > 2.0:
        skor += min(15, (hacim_oran - 1) * 5)

    # ADX trend gücü bonusu
    adx = features_row.get("adx", 20)
    if adx > 25:
        skor += min(10, (adx - 25) * 0.5)

    # OBV pozitif trend bonusu
    obv_trend = features_row.get("obv_trend", 0)
    if obv_trend > 0.1:
        skor += min(8, obv_trend * 20)

    vol_deg = features_row.get("volatilite_degisim", 0)
    if abs(vol_deg) > 0.3:
        skor += min(10, abs(vol_deg) * 10)

    direnc = features_row.get("direnc_yakinlik", 5)
    destek = features_row.get("destek_yakinlik", 5)
    if direnc < 1.0 or destek < 1.0:
        skor += 5

    return max(0, min(100, skor))


def teknik_sinyal_detay(features_row):
    sinyaller = []
    rsi = features_row.get("rsi", 50)

    if rsi < 30:
        sinyaller.append(("RSI Aşırı Satım", f"RSI: {rsi:.1f}", "yukari"))
    elif rsi > 70:
        sinyaller.append(("RSI Aşırı Alım", f"RSI: {rsi:.1f}", "asagi"))

    if features_row.get("boll_sikisma", 0):
        sinyaller.append(("Bollinger Sıkışma", "Band sıkışması — patlama beklentisi", "notr"))

    boll_poz = features_row.get("boll_pozisyon", 0.5)
    if boll_poz > 1.0:
        sinyaller.append(("Üst Band Kırım", f"Pozisyon: {boll_poz:.2f}", "yukari"))
    elif boll_poz < 0.0:
        sinyaller.append(("Alt Band Kırım", f"Pozisyon: {boll_poz:.2f}", "asagi"))

    hacim_oran = features_row.get("hacim_oran", 1.0)
    if hacim_oran > 2.0:
        sinyaller.append(("Hacim Patlaması", f"Ortalamanın {hacim_oran:.1f}x üstü", "notr"))

    adx = features_row.get("adx", 0)
    if adx > 30:
        di_fark = features_row.get("di_fark", 0)
        yon = "yukari" if di_fark > 0 else "asagi"
        sinyaller.append(("Güçlü Trend (ADX)", f"ADX: {adx:.0f}", yon))

    obv_trend = features_row.get("obv_trend", 0)
    if obv_trend > 0.15:
        sinyaller.append(("OBV Birikim", "Kurumsal alım baskısı artıyor", "yukari"))

    macd_hist = features_row.get("macd_hist_degisim", 0)
    if macd_hist > 0.5:
        sinyaller.append(("MACD Yükseliş", "Histogram pozitife dönüyor", "yukari"))
    elif macd_hist < -0.5:
        sinyaller.append(("MACD Düşüş", "Histogram negatife dönüyor", "asagi"))

    mom_5 = features_row.get("mom_5", 0)
    if abs(mom_5) > 5:
        yon = "yukari" if mom_5 > 0 else "asagi"
        sinyaller.append(("Güçlü Momentum", f"5 günlük: %{mom_5:.1f}", yon))

    vwap_oran = features_row.get("vwap_oran", 0)
    if vwap_oran > 2:
        sinyaller.append(("VWAP Üstünde", f"VWAP'ın %{vwap_oran:.1f} üstünde", "yukari"))

    return sinyaller


# ============================================================
# ML MODELİ (XGBoost) — Walk-Forward Validation
# ============================================================

FEATURE_COLS = [
    "rsi", "rsi_degisim",
    "macd", "macd_sinyal", "macd_hist", "macd_hist_degisim",
    "boll_pozisyon", "boll_genislik", "boll_sikisma",
    "obv_trend", "obv_momentum",
    "adx", "di_fark",
    "stok_k", "stok_d", "stok_kesisim",
    "vwap_oran",
    "hacim_oran", "hacim_trend", "hacim_artis",
    "mom_3", "mom_5", "mom_10", "mom_20",
    "volatilite", "volatilite_degisim", "volatilite_kisalma",
    "fiyat_ema8_oran", "fiyat_sma20_oran",
    "ema8_ema21_oran", "sma5_sma20_oran", "sma10_sma50_oran",
    "yillik_pozisyon",
    "gunluk_degisim", "gunluk_ort_5", "gunluk_max_10", "gunluk_min_10",
    "ardi_yukari",
    "direnc_yakinlik", "destek_yakinlik",
    "mum_boy_oran", "govde_oran",
]


def hedef_olustur(df, gun=5, esik=3.0):
    """Sonraki N günde %esik+ hareket olup olmadığı (yukarı sürpriz odaklı)."""
    gelecek_max = df["High"].squeeze().rolling(gun).max().shift(-gun)
    close = df["Close"].squeeze()
    yukari = (gelecek_max - close) / close * 100
    return (yukari >= esik).astype(int)


def walk_forward_validation(X, y, n_splits=5):
    """
    Walk-Forward Validation:
    Geçmiş verilerle eğit → gelecek veriyle test et.
    Gerçekçi performans ölçümü.
    """
    from xgboost import XGBClassifier
    from sklearn.metrics import accuracy_score, f1_score, precision_score

    n = len(X)
    split_size = n // (n_splits + 1)
    sonuclar = []

    for i in range(n_splits):
        train_end = split_size * (i + 1)
        test_end = min(train_end + split_size, n)

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]
        X_test = X.iloc[train_end:test_end]
        y_test = y.iloc[train_end:test_end]

        if len(X_train) < 100 or len(X_test) < 20:
            continue

        model = XGBClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=5,   # overfitting önleme
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        sonuclar.append({
            "fold": i + 1,
            "dogruluk": accuracy_score(y_test, y_pred),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "pozitif_oran": y_test.mean(),
            "train_n": len(X_train),
            "test_n": len(X_test),
        })

    return sonuclar


def model_egit(tum_veri, walk_forward=True):
    """
    Tüm hisse verilerinden model eğitir.
    tum_veri: dict {ticker: DataFrame}
    """
    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("XGBoost yüklü değil!")
        return None

    X_list, y_list = [], []

    for ticker, df in tum_veri.items():
        features = feature_olustur(df)
        if features is None:
            continue

        hedef = hedef_olustur(df)
        gecerli_cols = [c for c in FEATURE_COLS if c in features.columns]
        birlesik = features[gecerli_cols].copy()
        birlesik["hedef"] = hedef
        birlesik = birlesik.dropna()

        if len(birlesik) < 50:
            continue

        X_list.append(birlesik[gecerli_cols])
        y_list.append(birlesik["hedef"])

    if not X_list:
        print("Yeterli veri yok!")
        return None

    X = pd.concat(X_list, ignore_index=True)
    y = pd.concat(y_list, ignore_index=True)

    gecerli_cols = X.columns.tolist()

    print(f"  Toplam veri: {len(X):,} satır | Pozitif oran: %{y.mean()*100:.1f}")

    # Walk-Forward Validation
    wf_sonuclar = []
    if walk_forward and len(X) > 500:
        print("  Walk-Forward Validation çalışıyor...")
        wf_sonuclar = walk_forward_validation(X, y)
        if wf_sonuclar:
            ort_f1 = np.mean([s["f1"] for s in wf_sonuclar])
            ort_precision = np.mean([s["precision"] for s in wf_sonuclar])
            print(f"  WF Sonuçları → Ortalama F1: {ort_f1:.3f} | Precision: {ort_precision:.3f}")

    # Son model — tüm veriyle eğit
    split = int(len(X) * 0.85)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=5,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    from sklearn.metrics import accuracy_score, f1_score, precision_score
    y_pred = model.predict(X_test)
    dogruluk = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    precision = precision_score(y_test, y_pred, zero_division=0)

    # Feature importance
    importance = pd.Series(model.feature_importances_, index=gecerli_cols)
    importance = importance.sort_values(ascending=False)

    # Kaydet
    model_path = MODEL_DIR / "surpriz_model.pkl"
    meta_path = MODEL_DIR / "model_meta.json"
    joblib.dump(model, model_path)

    import json
    meta = {
        "egitim_tarihi": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "dogruluk": round(dogruluk, 4),
        "f1": round(f1, 4),
        "precision": round(precision, 4),
        "egitim_boyut": len(X_train),
        "test_boyut": len(X_test),
        "feature_sayisi": len(gecerli_cols),
        "top_features": importance.head(10).to_dict(),
        "walk_forward": wf_sonuclar,
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)

    return {
        "model": model,
        "dogruluk": dogruluk,
        "f1": f1,
        "precision": precision,
        "egitim_boyut": len(X_train),
        "test_boyut": len(X_test),
        "top_features": importance.head(10).to_dict(),
        "walk_forward": wf_sonuclar,
        "feature_cols": gecerli_cols,
    }


def model_yukle():
    model_path = MODEL_DIR / "surpriz_model.pkl"
    if model_path.exists():
        return joblib.load(model_path)
    return None


def model_meta_oku():
    import json
    meta_path = MODEL_DIR / "model_meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            return json.load(f)
    return None


def ml_tahmin(model, features_df):
    if model is None:
        return None

    gecerli_cols = [c for c in FEATURE_COLS if c in features_df.columns]
    son_satir = features_df[gecerli_cols].iloc[-1:]

    if son_satir.isna().any(axis=1).iloc[0]:
        return None

    olasilik = model.predict_proba(son_satir)[0]
    return float(olasilik[1]) if len(olasilik) > 1 else 0.0


# ============================================================
# BİRLEŞİK SKOR
# ============================================================

def birlesik_skor_hesapla(teknik, ml_olasilik):
    """Teknik skor (%35) + ML olasılığı (%65) = Nihai skor."""
    if ml_olasilik is None:
        return teknik
    ml_skor = ml_olasilik * 100
    return teknik * 0.35 + ml_skor * 0.65


def hisse_analiz(ticker, df, ml_model=None):
    features = feature_olustur(df)
    if features is None:
        return None

    son = features.iloc[-1].to_dict()
    teknik = teknik_skor_hesapla(son)
    sinyaller = teknik_sinyal_detay(son)

    ml_olasilik = ml_tahmin(ml_model, features) if ml_model else None
    birlesik = birlesik_skor_hesapla(teknik, ml_olasilik)

    close = df["Close"].squeeze()

    return {
        "ticker": ticker,
        "teknik_skor": round(teknik, 1),
        "ml_olasilik": round(ml_olasilik, 3) if ml_olasilik else None,
        "birlesik_skor": round(birlesik, 1),
        "sinyaller": sinyaller,
        "features": son,
        "fiyat": float(close.iloc[-1]),
        "gunluk_degisim": float(((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]) * 100) if len(close) > 1 else 0,
        "hacim": float(df["Volume"].squeeze().iloc[-1]),
        "adx": round(son.get("adx", 0), 1),
        "obv_trend": round(son.get("obv_trend", 0), 3),
        "yillik_poz": round(son.get("yillik_pozisyon", 0.5) * 100, 1),
    }
