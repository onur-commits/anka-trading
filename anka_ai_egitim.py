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


def hedef_hesapla(df, gun=5, kar_esik=2.0, zarar_limiti=-1.5):
    """
    Triple Barrier Method (Lopez de Prado, Advances in Financial ML).

    Uc bariyer:
      1. Ust bariyer: Take-profit (kar_esik, ornek +%2)
      2. Alt bariyer: Stop-loss (zarar_limiti, ornek -%1.5)
      3. Zaman bariyeri: Maksimum tutma suresi (gun, ornek 5 gun)

    Etiket = hangi bariyer ONCE vurulursa o:
      - Ust bariyer -> 1 (basarili)
      - Alt bariyer -> 0 (basarisiz)
      - Zaman bariyeri -> kapanistaki getiriye gore

    Returns: (hedef_serisi, getiri_serisi)
    """
    close = df['Close'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()

    n = len(close)
    hedef = pd.Series(np.nan, index=close.index)
    getiri = pd.Series(np.nan, index=close.index)

    for i in range(n - 1):
        giris = close.iloc[i]
        if giris == 0 or np.isnan(giris):
            continue

        bariyer_vuruldu = False
        pencere_sonu = min(i + gun, n - 1)

        for j in range(i + 1, pencere_sonu + 1):
            gun_yuksek = high.iloc[j]
            gun_dusuk = low.iloc[j]

            yukari_pct = (gun_yuksek - giris) / giris * 100
            asagi_pct = (gun_dusuk - giris) / giris * 100

            # Ust bariyer (take profit)
            if yukari_pct >= kar_esik:
                hedef.iloc[i] = 1
                getiri.iloc[i] = kar_esik / 100
                bariyer_vuruldu = True
                break

            # Alt bariyer (stop loss)
            if asagi_pct <= zarar_limiti:
                hedef.iloc[i] = 0
                getiri.iloc[i] = zarar_limiti / 100
                bariyer_vuruldu = True
                break

        # Zaman bariyeri
        if not bariyer_vuruldu and pencere_sonu > i:
            son_getiri_pct = (close.iloc[pencere_sonu] - giris) / giris * 100
            hedef.iloc[i] = 1 if son_getiri_pct > 0 else 0
            getiri.iloc[i] = son_getiri_pct / 100

    hedef = hedef.fillna(0).astype(int)
    getiri = getiri.fillna(0)
    return hedef, getiri


def dataset_olustur(tum_veri, hedef_gun=5):
    """Tüm hisselerden birleşik eğitim seti oluştur (Triple Barrier Method)."""
    print(f"\n📊 Dataset oluşturuluyor (Triple Barrier: {hedef_gun} gün pencere)...")
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


def feature_sec(X, y, max_feature=25, korelasyon_esik=0.90):
    """
    Doktora Raporu Y-07: 73+ feature cok fazla, cogu koreleli.

    Iki asamali feature secimi:
    1. Yuksek korelasyonlu featurelari ele (>0.90 korelasyon)
    2. XGBoost importance ile en iyi N feature sec

    Returns: (X_secilmis, secilen_feature_isimleri)
    """
    from xgboost import XGBClassifier

    print(f"\n🔍 Feature secimi basliyor ({X.shape[1]} feature)...")

    # Adim 1: Korelasyon filtresi
    corr_matrix = X.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    cikarilacak = set()
    for col in upper.columns:
        yuksek_korele = upper.index[upper[col] > korelasyon_esik].tolist()
        if yuksek_korele:
            cikarilacak.add(col)  # koreleli olani cikar

    X_filtreli = X.drop(columns=list(cikarilacak), errors='ignore')
    print(f"  Korelasyon filtresi: {X.shape[1]} -> {X_filtreli.shape[1]} "
          f"({len(cikarilacak)} koreleli feature cikarildi)")

    # Korelasyon sonrasi zaten hedef sayinin altindaysa direkt don
    if X_filtreli.shape[1] <= max_feature:
        print(f"  Secilen {X_filtreli.shape[1]} feature (korelasyon filtresi yeterli)")
        return X_filtreli, X_filtreli.columns.tolist()

    # Adim 2: XGBoost feature importance ile sec
    print(f"  XGBoost importance ile {max_feature} feature seciliyor...")
    from sklearn.model_selection import train_test_split
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_filtreli, y, test_size=0.2, shuffle=False
    )
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
    X_secilmis = X_filtreli[secilen]

    print(f"  En onemli {max_feature} feature secildi:")
    for i, (feat, score) in enumerate(importance.head(max_feature).items()):
        print(f"    {i+1:2d}. {feat}: {score:.4f}")

    return X_secilmis, secilen


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

    # 2. Dataset oluştur (Triple Barrier: 5 gün, +%2 TP, -%1.5 SL)
    X, y, info = dataset_olustur(tum_veri, hedef_gun=5)

    # 3. Feature secimi (73+ -> 20-25)
    X, secilen_features = feature_sec(X, y, max_feature=25, korelasyon_esik=0.90)

    # 4. Model eğit
    models, auc = model_egit(X, y)

    if models:
        print(f"\n✅ ANKA AI hazır! AUC: {auc:.4f}")
        print("Kullanım: anka_predict(df, models_dict)")

        # 5. Komisyon dahil backtest (Doktora Raporu Y-09)
        print("\n" + "=" * 50)
        print("KOMISYON DAHIL BACKTEST (Y-09)")
        print("=" * 50)
        try:
            from tahmin_motoru_v2 import komisyonlu_backtest
            import yfinance as yf
            xu100 = yf.download("XU100.IS", period="5y", progress=False)
            backtest_sonuc = komisyonlu_backtest(
                tum_veri,
                xu100_df=xu100,
                komisyon_tek_yon=0.0015,
                slippage=0.001,
                baslangic_sermaye=100000,
                yil=3,
            )
        except Exception as e:
            print(f"Backtest hatasi: {e}")
    else:
        print("\n❌ Eğitim başarısız")
