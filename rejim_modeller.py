"""
ANKA Faz 2A — Rejim-Bazli Model Sistemi
=========================================
Bull, bear, sideways icin ayri uzman modeller egitir.
Her rejimin kendi optimal feature seti ve parametreleri vardir.

Mantik:
  1. Tarihsel veriyi rejimlere bol (her gun icin bull/bear/sideways etiketi)
  2. Her rejim icin ayri XGBoost + LightGBM ensemble egit
  3. Tahmin sirasinda: once rejimi tespit et, sonra o rejimin modelini kullan

Neden tek model yetersiz:
  - Bull'da momentum feature'lari baskın
  - Bear'de volatilite ve korku sinyalleri baskın
  - Sideways'de mean-reversion sinyalleri baskın
  - Tek model hepsini karistirinca ortalama performans dusuyor
"""

import numpy as np
import pandas as pd
import joblib
import json
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


def _rejim_etiketle(xu100_df, pencere=50):
    """
    Her gun icin rejim etiketi uret.
    SMA50 trend + ADX + volatilite bazli.
    Returns: Series ('bull', 'bear', 'sideways')
    """
    close = xu100_df["Close"].squeeze()
    high = xu100_df["High"].squeeze()
    low = xu100_df["Low"].squeeze()

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    mom_20 = close.pct_change(20)

    # ADX
    from tahmin_motoru_v2 import adx_hesapla
    adx, di_p, di_m = adx_hesapla(high, low, close)

    # Volatilite
    vol = close.pct_change().rolling(20).std() * np.sqrt(252)
    vol_med = vol.rolling(100).median()

    rejimler = pd.Series("sideways", index=close.index)

    for i in range(pencere, len(close)):
        skor = 0
        # Trend yonu
        if close.iloc[i] > sma20.iloc[i]:
            skor += 1
        if close.iloc[i] > sma50.iloc[i]:
            skor += 1
        if sma20.iloc[i] > sma50.iloc[i]:
            skor += 1
        if mom_20.iloc[i] > 0.02:  # %2+ yukari momentum
            skor += 1

        # Trend gucu
        if adx.iloc[i] > 25:
            # Guclu trend — bull veya bear
            if skor >= 3:
                rejimler.iloc[i] = "bull"
            elif skor <= 1:
                rejimler.iloc[i] = "bear"
            # else sideways
        else:
            # Zayif trend
            if skor >= 3 and mom_20.iloc[i] > 0.05:
                rejimler.iloc[i] = "bull"  # guclu momentum varsa yine bull
            elif skor <= 1 and mom_20.iloc[i] < -0.05:
                rejimler.iloc[i] = "bear"
            # else sideways

    return rejimler


class RejimModelSistemi:
    """
    3 uzman model: bull_model, bear_model, sideways_model
    + rejim tespit modeli
    """

    def __init__(self):
        self.modeller = {}  # {"bull": model, "bear": model, "sideways": model}
        self.feature_cols = {}  # her rejimin kendi feature listesi
        self.scalers = {}
        self.meta = {}

    def egit(self, tum_veri, xu100_df, makro_veri=None):
        """
        Rejim-bazli modelleri egitir.
        tum_veri: {ticker: DataFrame} dict
        xu100_df: XU100 endeks verisi (rejim tespiti icin)
        makro_veri: makro_veri.py'den gelen dict (opsiyonel)
        """
        from xgboost import XGBClassifier
        from sklearn.metrics import roc_auc_score, f1_score, precision_score
        from sklearn.preprocessing import StandardScaler
        from tahmin_motoru_v2 import feature_olustur_v2, hedef_olustur, FEATURE_COLS_V2

        try:
            from lightgbm import LGBMClassifier
            lgb_ok = True
        except ImportError:
            lgb_ok = False

        # Makro feature hazirla
        if makro_veri:
            from makro_veri import makro_feature_hesapla, MAKRO_FEATURE_COLS
        else:
            MAKRO_FEATURE_COLS = []

        # 1) Rejim etiketlerini uret
        print("  Rejim etiketleri uretiliyor...")
        rejim_serileri = _rejim_etiketle(xu100_df)
        rejim_dagilim = rejim_serileri.value_counts()
        print(f"    Bull: {rejim_dagilim.get('bull', 0)} gun")
        print(f"    Bear: {rejim_dagilim.get('bear', 0)} gun")
        print(f"    Sideways: {rejim_dagilim.get('sideways', 0)} gun")

        # 2) Tum hisseler icin feature + hedef + rejim birlestir
        print("  Veri hazirlaniyor...")
        X_rejim = {"bull": [], "bear": [], "sideways": []}
        y_rejim = {"bull": [], "bear": [], "sideways": []}

        for ticker, df in tum_veri.items():
            features = feature_olustur_v2(df)
            if features is None:
                continue

            # Makro ekle
            if makro_veri:
                mf = makro_feature_hesapla(makro_veri, features.index)
                mf_cols = [c for c in MAKRO_FEATURE_COLS if c in mf.columns]
                for col in mf_cols:
                    features[col] = mf[col]

            hedef = hedef_olustur(df)
            tum_cols = [c for c in FEATURE_COLS_V2 if c in features.columns]
            if makro_veri:
                tum_cols += [c for c in mf_cols if c not in tum_cols]

            birlesik = features[tum_cols].copy()
            birlesik["hedef"] = hedef

            # Rejim etiketi hizala
            rejim_hizali = rejim_serileri.reindex(birlesik.index, method="ffill")
            birlesik["rejim"] = rejim_hizali
            birlesik = birlesik.dropna()

            for rejim_adi in ["bull", "bear", "sideways"]:
                mask = birlesik["rejim"] == rejim_adi
                if mask.sum() > 10:
                    X_rejim[rejim_adi].append(birlesik.loc[mask, tum_cols])
                    y_rejim[rejim_adi].append(birlesik.loc[mask, "hedef"])

        # 3) Her rejim icin model egit
        sonuclar = {}
        for rejim_adi in ["bull", "bear", "sideways"]:
            if not X_rejim[rejim_adi]:
                print(f"\n  {rejim_adi.upper()}: Yeterli veri yok, atlaniyor")
                continue

            X = pd.concat(X_rejim[rejim_adi], ignore_index=True)
            y = pd.concat(y_rejim[rejim_adi], ignore_index=True)

            if len(X) < 200:
                print(f"\n  {rejim_adi.upper()}: {len(X)} satir — yetersiz, atlaniyor")
                continue

            print(f"\n  {'='*50}")
            print(f"  {rejim_adi.upper()} MODEL ({len(X):,} satir, pozitif: %{y.mean()*100:.1f})")
            print(f"  {'='*50}")

            # Feature secimi (rejime ozel)
            from tahmin_motoru_v2 import _feature_sec_v2
            X_sec, secilen = _feature_sec_v2(X, y, max_feature=20, korelasyon_esik=0.85)
            self.feature_cols[rejim_adi] = secilen

            # Train/test split
            split = int(len(X_sec) * 0.85)
            X_train, X_test = X_sec.iloc[:split], X_sec.iloc[split:]
            y_train, y_test = y.iloc[:split], y.iloc[split:]

            # XGBoost
            xgb = XGBClassifier(
                n_estimators=300,
                max_depth=5,
                learning_rate=0.03,
                subsample=0.8,
                colsample_bytree=0.7,
                min_child_weight=8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                eval_metric="logloss",
                early_stopping_rounds=30,
                random_state=42,
                verbosity=0,
            )
            xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
            xgb_prob = xgb.predict_proba(X_test)[:, 1]
            xgb_auc = roc_auc_score(y_test, xgb_prob) if y_test.nunique() > 1 else 0.5

            # LightGBM
            lgb_model = None
            lgb_auc = 0
            if lgb_ok:
                lgb_model = LGBMClassifier(
                    n_estimators=300, max_depth=5, learning_rate=0.03,
                    subsample=0.8, colsample_bytree=0.7,
                    min_child_weight=8, reg_alpha=0.1, reg_lambda=1.0,
                    random_state=42, verbose=-1,
                )
                lgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)])
                lgb_prob = lgb_model.predict_proba(X_test)[:, 1]
                lgb_auc = roc_auc_score(y_test, lgb_prob) if y_test.nunique() > 1 else 0.5

            # Ensemble
            if lgb_ok and lgb_model is not None:
                w_xgb = xgb_auc / (xgb_auc + lgb_auc)
                w_lgb = lgb_auc / (xgb_auc + lgb_auc)
                ens_prob = w_xgb * xgb_prob + w_lgb * lgb_prob
            else:
                w_xgb, w_lgb = 1.0, 0.0
                ens_prob = xgb_prob

            ens_auc = roc_auc_score(y_test, ens_prob) if y_test.nunique() > 1 else 0.5
            ens_pred = (ens_prob >= 0.5).astype(int)
            ens_f1 = f1_score(y_test, ens_pred, zero_division=0)
            ens_prec = precision_score(y_test, ens_pred, zero_division=0)

            print(f"    XGB AUC: {xgb_auc:.4f} | LGB AUC: {lgb_auc:.4f}")
            print(f"    ENSEMBLE AUC: {ens_auc:.4f} | F1: {ens_f1:.4f} | Precision: {ens_prec:.4f}")

            self.modeller[rejim_adi] = {
                "xgb": xgb,
                "lgb": lgb_model,
                "weights": (w_xgb, w_lgb),
            }

            sonuclar[rejim_adi] = {
                "auc": round(ens_auc, 4),
                "f1": round(ens_f1, 4),
                "precision": round(ens_prec, 4),
                "veri_boyut": len(X),
                "feature_sayisi": len(secilen),
                "top_features": dict(zip(
                    secilen[:5],
                    xgb.feature_importances_[:5].tolist()
                )),
            }

        # 4) Meta kaydet
        self.meta = {
            "versiyon": "V3_REJIM_BAZLI",
            "egitim_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "rejimler": sonuclar,
            "rejim_dagilim": rejim_dagilim.to_dict(),
        }

        self.kaydet()

        # Ozet
        print(f"\n  {'='*50}")
        print(f"  REJIM BAZLI MODEL OZETI")
        print(f"  {'='*50}")
        for r, s in sonuclar.items():
            print(f"    {r.upper():10s} AUC:{s['auc']:.4f} F1:{s['f1']:.4f} Prec:{s['precision']:.4f} (n={s['veri_boyut']})")

        return self.meta

    def tahmin(self, features_df, rejim="sideways"):
        """Rejime gore tahmin yap."""
        if rejim not in self.modeller:
            # Fallback: en yakin rejim
            rejim = "sideways" if "sideways" in self.modeller else list(self.modeller.keys())[0]

        model_dict = self.modeller[rejim]
        cols = self.feature_cols[rejim]
        gecerli = [c for c in cols if c in features_df.columns]
        son = features_df[gecerli].iloc[-1:].fillna(0)

        xgb_prob = model_dict["xgb"].predict_proba(son)[:, 1]
        w_xgb, w_lgb = model_dict["weights"]

        if model_dict["lgb"] is not None:
            lgb_prob = model_dict["lgb"].predict_proba(son)[:, 1]
            prob = w_xgb * xgb_prob + w_lgb * lgb_prob
        else:
            prob = xgb_prob

        return float(prob[0])

    def kaydet(self):
        path = MODEL_DIR / "rejim_modeller_v3.pkl"
        meta_path = MODEL_DIR / "rejim_modeller_v3_meta.json"

        joblib.dump({
            "modeller": self.modeller,
            "feature_cols": self.feature_cols,
        }, path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, default=str, ensure_ascii=False)

        print(f"  Model kaydedildi: {path}")

    @classmethod
    def yukle(cls):
        path = MODEL_DIR / "rejim_modeller_v3.pkl"
        if not path.exists():
            return None

        data = joblib.load(path)
        model = cls()
        model.modeller = data["modeller"]
        model.feature_cols = data["feature_cols"]

        meta_path = MODEL_DIR / "rejim_modeller_v3_meta.json"
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                model.meta = json.load(f)

        return model
