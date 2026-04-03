"""
ANKA AI — Kendi Kendine Öğrenen Bomba Bulucu
=============================================
5 yıllık BIST verisiyle eğitilir.
Her hisse, her gün, her koşul için optimal parametreleri öğrenir.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import joblib
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

PROJECT_DIR = Path(__file__).parent
MODEL_DIR = PROJECT_DIR / "models"
DATA_DIR = PROJECT_DIR / "data"
MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# BIST50
BIST50 = [
    "GARAN","THYAO","ASELS","TUPRS","EREGL","SISE","TOASO","AKBNK","YKBNK","HALKB",
    "SAHOL","KCHOL","TCELL","BIMAS","PGSUS","TAVHL","FROTO","ARCLK","PETKM","ENKAI",
    "TKFEN","EKGYO","TTKOM","VAKBN","MGROS","DOHOL","GUBRF","ISCTR","AKSEN","AYEN",
    "KONTR","SASA","GESAN","OTKAR","ENJSA","TSKB","SMRTG","CCOLA","CIMSA","KORDS",
    "VESTL","ALARK","HEKTS","ULKER","ASTOR","TTRAK","EGEEN","CEMTS","BRISA"
]


def veri_cek(yil=5):
    """Tüm BIST50 hisselerinin N yıllık verisini çek."""
    print(f"📥 {len(BIST50)} hisse için {yil} yıllık veri çekiliyor...")
    tum_veri = {}
    for i, s in enumerate(BIST50):
        try:
            df = yf.download(f"{s}.IS", period=f"{yil}y", progress=False)
            if len(df) >= 200:
                tum_veri[s] = df
                print(f"  [{i+1}/{len(BIST50)}] {s}: {len(df)} gün ✅")
            else:
                print(f"  [{i+1}/{len(BIST50)}] {s}: yetersiz veri ❌")
        except:
            print(f"  [{i+1}/{len(BIST50)}] {s}: hata ❌")
    print(f"\n✅ {len(tum_veri)} hisse yüklendi")
    return tum_veri


def feature_hesapla(df):
    """Her gün için teknik özellikler hesapla."""
    close = df['Close'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    volume = df['Volume'].squeeze()
    open_ = df['Open'].squeeze()

    f = pd.DataFrame(index=df.index)

    # EMA
    f['ema10'] = close.ewm(span=10).mean()
    f['ema20'] = close.ewm(span=20).mean()
    f['ema_cross'] = (f['ema10'] > f['ema20']).astype(int)

    # RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    f['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    f['macd'] = ema12 - ema26
    f['macd_signal'] = f['macd'].ewm(span=9).mean()
    f['macd_hist'] = f['macd'] - f['macd_signal']

    # Hacim
    f['hacim_ort10'] = volume.rolling(10).mean()
    f['hacim_oran'] = volume / (f['hacim_ort10'] + 1)

    # Bollinger
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    f['boll_ust'] = sma20 + 2 * std20
    f['boll_alt'] = sma20 - 2 * std20
    f['boll_poz'] = (close - f['boll_alt']) / (f['boll_ust'] - f['boll_alt'] + 1e-10)

    # ATR
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    f['atr'] = tr.rolling(14).mean()
    f['atr_pct'] = f['atr'] / close * 100

    # Mum analizi
    f['govde'] = (close - open_).abs() / (high - low + 1e-10)
    f['kapanis_gucu'] = close / (high + 1e-10)
    f['ust_fitil'] = (high - close.clip(lower=open_)) / (high - low + 1e-10)
    f['alt_fitil'] = (close.clip(upper=open_) - low) / (high - low + 1e-10)

    # Momentum
    f['mom_1d'] = close.pct_change(1) * 100
    f['mom_5d'] = close.pct_change(5) * 100
    f['mom_10d'] = close.pct_change(10) * 100

    # OBV
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    f['obv_trend'] = (obv - obv.rolling(20).mean()) / (obv.rolling(20).std() + 1e-10)

    # MA Alignment
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    f['ma_alignment'] = ((close > f['ema10']).astype(int) +
                         (close > f['ema20']).astype(int) +
                         (close > sma50).astype(int))

    # 52 hafta pozisyonu
    f['pos_52w'] = (close - close.rolling(252).min()) / (close.rolling(252).max() - close.rolling(252).min() + 1e-10)

    # Gün bilgisi
    f['gun_haftada'] = df.index.dayofweek  # 0=Pazartesi, 4=Cuma

    # Kapanış
    f['close'] = close

    return f.dropna()


def hedef_hesapla(df, gun=1):
    """N gün sonraki getiriyi hesapla — AI'nın öğreneceği hedef."""
    close = df['Close'].squeeze()
    # N gün sonraki yüzdesel değişim
    getiri = close.shift(-gun) / close - 1
    # Binary: +%1 üstü = 1 (iyi), altı = 0 (kötü)
    hedef = (getiri > 0.01).astype(int)
    return hedef, getiri


def dataset_olustur(tum_veri, hedef_gun=1):
    """Tüm hisselerden birleşik eğitim seti oluştur."""
    print(f"\n📊 Dataset oluşturuluyor (hedef: {hedef_gun} gün sonra)...")
    X_all = []
    y_all = []
    info_all = []

    for s, df in tum_veri.items():
        try:
            features = feature_hesapla(df)
            hedef, getiri = hedef_hesapla(df, hedef_gun)

            # Hizala
            ortak = features.index.intersection(hedef.dropna().index)
            if len(ortak) < 100:
                continue

            X = features.loc[ortak]
            y = hedef.loc[ortak]

            X_all.append(X)
            y_all.append(y)
            info_all.extend([(s, str(d.date())) for d in ortak])

        except:
            continue

    X_full = pd.concat(X_all, ignore_index=True)
    y_full = pd.concat(y_all, ignore_index=True)

    print(f"  ✅ {len(X_full)} satır, {X_full.shape[1]} özellik")
    print(f"  Pozitif: {y_full.sum()} ({y_full.mean()*100:.1f}%)")
    return X_full, y_full, info_all


def model_egit(X, y):
    """XGBoost + LightGBM ensemble eğit."""
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, roc_auc_score

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False  # Zaman sırası korunmalı
    )

    print(f"\n🧠 Model eğitimi: {len(X_train)} train, {len(X_test)} test")

    models = {}

    # XGBoost
    try:
        from xgboost import XGBClassifier
        xgb = XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric='auc', verbosity=0
        )
        xgb.fit(X_train, y_train)
        models['xgb'] = xgb
        xgb_auc = roc_auc_score(y_test, xgb.predict_proba(X_test)[:, 1])
        print(f"  XGBoost AUC: {xgb_auc:.4f}")
    except Exception as e:
        print(f"  XGBoost hatası: {e}")

    # LightGBM
    try:
        from lightgbm import LGBMClassifier
        lgbm = LGBMClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, verbose=-1
        )
        lgbm.fit(X_train, y_train)
        models['lgbm'] = lgbm
        lgbm_auc = roc_auc_score(y_test, lgbm.predict_proba(X_test)[:, 1])
        print(f"  LightGBM AUC: {lgbm_auc:.4f}")
    except Exception as e:
        print(f"  LightGBM hatası: {e}")

    # Ensemble (ortalama)
    if models:
        probas = np.mean([m.predict_proba(X_test)[:, 1] for m in models.values()], axis=0)
        ens_auc = roc_auc_score(y_test, probas)
        print(f"  Ensemble AUC: {ens_auc:.4f}")

        # Feature importance
        if 'xgb' in models:
            imp = pd.Series(models['xgb'].feature_importances_, index=X.columns)
            print(f"\n📊 En önemli özellikler:")
            for feat, score in imp.nlargest(10).items():
                print(f"  {feat}: {score:.4f}")

        # Kaydet
        model_path = MODEL_DIR / "anka_ai_v1.pkl"
        joblib.dump({
            'models': models,
            'features': list(X.columns),
            'auc': ens_auc,
            'tarih': datetime.now().isoformat(),
        }, model_path)
        print(f"\n💾 Model kaydedildi: {model_path}")

        return models, ens_auc

    return None, 0


def anka_predict(df, models_dict):
    """Tek hisse için tahmin yap."""
    models = models_dict['models']
    feature_cols = models_dict['features']

    features = feature_hesapla(df)
    if len(features) == 0:
        return 0.5

    last = features.iloc[-1:][feature_cols]
    probas = np.mean([m.predict_proba(last)[:, 1] for m in models.values()], axis=0)
    return float(probas[0])


if __name__ == "__main__":
    print("🔥 ANKA AI EĞİTİM SİSTEMİ")
    print("=" * 50)

    # 1. Veri çek
    tum_veri = veri_cek(yil=5)

    # 2. Dataset oluştur
    X, y, info = dataset_olustur(tum_veri, hedef_gun=1)

    # 3. Model eğit
    models, auc = model_egit(X, y)

    if models:
        print(f"\n✅ ANKA AI hazır! AUC: {auc:.4f}")
        print("Kullanım: anka_predict(df, models_dict)")
    else:
        print("\n❌ Eğitim başarısız")
