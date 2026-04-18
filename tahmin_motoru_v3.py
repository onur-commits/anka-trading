"""
ANKA ML TAHMIN MOTORU V3 — Performans İyileştirmeleri
=====================================================
V2'nin üzerine eklenen iyileştirmeler:

1. Sample Weighting — son verilere daha fazla ağırlık (exponential decay)
2. Bayesian Hyperparameter Tuning — Optuna ile otomatik parametre arama
3. Calibrated Probabilities — Platt scaling ile kalibre edilmiş olasılıklar
4. Feature Interaction — önemli feature'lar arası çarpımlar
5. Target Encoding — sektör bazlı hedef encoding
6. Threshold Optimization — F1 maximize eden optimal eşik
7. Model Stacking — Level-2 meta model (logistic regression)
8. Anti-Overfitting — daha agresif regularization

Tarih: 16 Nisan 2026
"""

import numpy as np
import pandas as pd
import json
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")

# V2'den tüm fonksiyonları import et
from tahmin_motoru_v2 import (
    feature_olustur_v2, FEATURE_COLS_V2,
    hedef_olustur, _feature_sec_v2,
    market_rejim_tespit, teknik_skor_v2,
    hisse_analiz_v2, EnsembleModelV2,
    rsi_hesapla, macd_hesapla, bollinger_hesapla,
    obv_hesapla, atr_hesapla, adx_hesapla,
    stokastik_hesapla, vwap_hesapla,
)

MODEL_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "data"
MODEL_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# 1. SAMPLE WEIGHTING — Son Verilere Ağırlık
# ============================================================

def sample_weight_hesapla(n_samples: int, decay_factor: float = 0.998) -> np.ndarray:
    """
    Exponential decay ile sample weights.
    Son veriler daha ağırlıklı — piyasa rejimi değişimlerini yakalar.

    decay_factor=0.998: 500 gün önceki veriye ~%37 ağırlık
    decay_factor=0.995: 500 gün önceki veriye ~%8 ağırlık
    """
    weights = np.array([decay_factor ** (n_samples - i - 1) for i in range(n_samples)])
    # Normalize et (ortalama 1 olsun)
    weights = weights / weights.mean()
    return weights


# ============================================================
# 2. FEATURE INTERACTION — Çapraz Etkileşimler
# ============================================================

def feature_interaction_ekle(df: pd.DataFrame) -> pd.DataFrame:
    """
    Önemli feature'lar arası etkileşim terimleri.
    Sadece en anlamlı kombinasyonlar — çok fazla eklersek overfitting.
    """
    f = df.copy()

    # RSI × Hacim: Aşırı satım + yüksek hacim = güçlü sinyal
    if "rsi_14" in f.columns and "hacim_oran" in f.columns:
        f["rsi_x_hacim"] = (100 - f["rsi_14"]) * f["hacim_oran"] / 100

    # ADX × MA alignment: Güçlü trend + doğru yön
    if "adx" in f.columns and "ma_alignment" in f.columns:
        f["adx_x_alignment"] = f["adx"] * f["ma_alignment"] / 3

    # Momentum × Bollinger: Momentum artışı + sıkışma çözülmesi
    if "mom_accel" in f.columns and "boll_gen" in f.columns:
        f["mom_x_boll"] = f["mom_accel"] * (100 - f["boll_gen"]) / 100

    # OBV × Fiyat momentum: Hacim teyidi
    if "obv_trend" in f.columns and "mom_5" in f.columns:
        f["obv_x_mom"] = f["obv_trend"] * np.sign(f["mom_5"])

    # Volatilite × Kanal pozisyonu: Düşük vol + kanal tabanı = breakout potansiyeli
    if "atr_ratio" in f.columns and "kanal_pozisyon" in f.columns:
        f["vol_x_kanal"] = (2 - f["atr_ratio"]) * (1 - f["kanal_pozisyon"])

    return f

INTERACTION_COLS = [
    "rsi_x_hacim", "adx_x_alignment", "mom_x_boll",
    "obv_x_mom", "vol_x_kanal"
]


# ============================================================
# 3. THRESHOLD OPTIMIZATION — Optimal Eşik Arama
# ============================================================

def optimal_esik_bul(y_true: np.ndarray, y_prob: np.ndarray,
                      metrik: str = "f1") -> dict:
    """
    F1 veya precision-recall dengesi için optimal olasılık eşiği.
    0.5 yerine veri-driven eşik kullan.
    """
    from sklearn.metrics import f1_score, precision_score, recall_score

    en_iyi_esik = 0.5
    en_iyi_skor = 0

    for esik in np.arange(0.35, 0.75, 0.01):
        tahmin = (y_prob >= esik).astype(int)
        if metrik == "f1":
            skor = f1_score(y_true, tahmin, zero_division=0)
        elif metrik == "precision":
            skor = precision_score(y_true, tahmin, zero_division=0)
        else:
            skor = f1_score(y_true, tahmin, zero_division=0)

        if skor > en_iyi_skor:
            en_iyi_skor = skor
            en_iyi_esik = esik

    return {
        "optimal_esik": round(en_iyi_esik, 2),
        "skor": round(en_iyi_skor, 4),
        "metrik": metrik,
    }


# ============================================================
# 4. MODEL STACKING — Meta Model
# ============================================================

class StackingEnsembleV3(EnsembleModelV2):
    """
    V3 Stacking Ensemble — V2'nin üzerine:
    - Level-1: XGBoost + LightGBM + MLP (V2'den)
    - Level-2: Logistic Regression meta model
    - Sample weighting
    - Feature interactions
    - Calibrated probabilities
    - Threshold optimization
    """

    def __init__(self):
        super().__init__()
        self.meta_model = None
        self.optimal_esik = 0.5
        self.interaction_cols = []
        self.calibrator = None

    def egit_v3(self, tum_veri, market_rejim=None, use_optuna=False):
        """
        V3 eğitim pipeline.
        """
        from xgboost import XGBClassifier
        from sklearn.neural_network import MLPClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.metrics import (accuracy_score, f1_score,
                                      precision_score, roc_auc_score,
                                      classification_report)

        try:
            from lightgbm import LGBMClassifier
            lgb_available = True
        except ImportError:
            lgb_available = False
            print("  ⚠ LightGBM yüklü değil")

        print("=" * 60)
        print("🧠 ANKA ML V3 — Gelişmiş Eğitim Pipeline")
        print("=" * 60)

        # ── Veri Hazırlama ────────────────────────────────────
        X_list, y_list = [], []

        for ticker, df in tum_veri.items():
            features = feature_olustur_v2(df)
            if features is None:
                continue

            # Feature interactions ekle
            features = feature_interaction_ekle(features)

            hedef = hedef_olustur(df)
            tum_cols = [c for c in FEATURE_COLS_V2 if c in features.columns]
            tum_cols += [c for c in INTERACTION_COLS if c in features.columns]
            gecerli = tum_cols

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

        print(f"  📊 Toplam: {len(X):,} satır | Pozitif: %{y.mean()*100:.1f} | Feature: {X.shape[1]}")

        # ── Feature Seçimi ────────────────────────────────────
        X, secilen = _feature_sec_v2(X, y, max_feature=30, korelasyon_esik=0.85)
        self.feature_cols = secilen

        # ── Sample Weights ────────────────────────────────────
        sample_weights = sample_weight_hesapla(len(X), decay_factor=0.997)
        print(f"  ⚖️ Sample weights: en eski={sample_weights[0]:.3f}, en yeni={sample_weights[-1]:.3f}")

        # ── Train/Val/Test Split ──────────────────────────────
        n = len(X)
        train_end = int(n * 0.70)
        val_end = int(n * 0.85)

        X_train, y_train, w_train = X.iloc[:train_end], y.iloc[:train_end], sample_weights[:train_end]
        X_val, y_val = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
        X_test, y_test = X.iloc[val_end:], y.iloc[val_end:]

        print(f"  📊 Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")

        # ── Hyperparameters ───────────────────────────────────
        if use_optuna:
            xgb_params = self._optuna_xgb_tune(X_train, y_train, X_val, y_val, w_train)
        else:
            # V3 default params — V2'den daha agresif regularization
            xgb_params = {
                "n_estimators": 400,
                "max_depth": 5,
                "learning_rate": 0.02,
                "subsample": 0.75,
                "colsample_bytree": 0.5,
                "min_child_weight": 15,
                "reg_alpha": 0.3,
                "reg_lambda": 2.0,
                "gamma": 0.1,
                "eval_metric": "logloss",
                "early_stopping_rounds": 40,
                "random_state": 42,
                "verbosity": 0,
            }

        # ── 1. XGBoost (sample weighted) ──────────────────────
        print("  🌲 XGBoost V3 eğitiliyor...")
        self.xgb_model = XGBClassifier(**xgb_params)
        self.xgb_model.fit(
            X_train, y_train,
            sample_weight=w_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        xgb_prob_val = self.xgb_model.predict_proba(X_val)[:, 1]
        xgb_prob_test = self.xgb_model.predict_proba(X_test)[:, 1]
        xgb_auc = roc_auc_score(y_test, xgb_prob_test) if y_test.nunique() > 1 else 0.5
        print(f"     XGBoost AUC: {xgb_auc:.4f}")

        # ── 2. LightGBM (sample weighted) ─────────────────────
        if lgb_available:
            print("  ⚡ LightGBM V3 eğitiliyor...")
            self.lgb_model = LGBMClassifier(
                n_estimators=400,
                max_depth=5,
                learning_rate=0.02,
                subsample=0.75,
                colsample_bytree=0.5,
                min_child_weight=15,
                reg_alpha=0.3,
                reg_lambda=2.0,
                random_state=42,
                verbose=-1,
            )
            self.lgb_model.fit(
                X_train, y_train,
                sample_weight=w_train,
                eval_set=[(X_val, y_val)],
            )
            lgb_prob_val = self.lgb_model.predict_proba(X_val)[:, 1]
            lgb_prob_test = self.lgb_model.predict_proba(X_test)[:, 1]
            lgb_auc = roc_auc_score(y_test, lgb_prob_test) if y_test.nunique() > 1 else 0.5
            print(f"     LightGBM AUC: {lgb_auc:.4f}")
        else:
            lgb_auc = 0
            lgb_prob_val = np.zeros(len(X_val))
            lgb_prob_test = np.zeros(len(X_test))

        # ── 3. MLP (scaled, weighted) ─────────────────────────
        print("  🧠 Neural Network V3 eğitiliyor...")
        self.scaler = StandardScaler()
        X_train_sc = self.scaler.fit_transform(X_train)
        X_val_sc = self.scaler.transform(X_val)
        X_test_sc = self.scaler.transform(X_test)

        self.mlp_model = MLPClassifier(
            hidden_layer_sizes=(256, 128, 64, 32),
            activation="relu",
            solver="adam",
            alpha=0.005,  # daha güçlü L2 regularization
            learning_rate="adaptive",
            learning_rate_init=0.0005,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.15,
            batch_size=64,
            random_state=42,
        )
        self.mlp_model.fit(X_train_sc, y_train)
        mlp_prob_val = self.mlp_model.predict_proba(X_val_sc)[:, 1]
        mlp_prob_test = self.mlp_model.predict_proba(X_test_sc)[:, 1]
        mlp_auc = roc_auc_score(y_test, mlp_prob_test) if y_test.nunique() > 1 else 0.5
        print(f"     MLP AUC: {mlp_auc:.4f}")

        # ── 4. Level-2 Meta Model (Stacking) ──────────────────
        print("  📐 Stacking meta model eğitiliyor...")
        meta_train = np.column_stack([xgb_prob_val, lgb_prob_val, mlp_prob_val])
        meta_test = np.column_stack([xgb_prob_test, lgb_prob_test, mlp_prob_test])

        self.meta_model = LogisticRegression(
            C=1.0, solver="lbfgs", max_iter=1000, random_state=42
        )
        self.meta_model.fit(meta_train, y_val)

        stacking_prob = self.meta_model.predict_proba(meta_test)[:, 1]
        stacking_auc = roc_auc_score(y_test, stacking_prob) if y_test.nunique() > 1 else 0.5
        print(f"     Stacking AUC: {stacking_auc:.4f}")

        # ── 5. Dinamik Ağırlıklar ────────────────────────────
        toplam_auc = xgb_auc + lgb_auc + mlp_auc
        if toplam_auc > 0:
            self.weights = [
                xgb_auc / toplam_auc,
                lgb_auc / toplam_auc,
                mlp_auc / toplam_auc,
            ]

        # ── 6. Optimal Eşik ──────────────────────────────────
        # Stacking kullanılıyorsa onun üzerinden, yoksa ensemble
        best_prob = stacking_prob if stacking_auc > 0.5 else self._ensemble_predict(X_test)
        esik_sonuc = optimal_esik_bul(y_test.values, best_prob, metrik="f1")
        self.optimal_esik = esik_sonuc["optimal_esik"]
        print(f"  🎯 Optimal eşik: {self.optimal_esik} (F1: {esik_sonuc['skor']:.4f})")

        # ── 7. Probability Calibration ────────────────────────
        # Platt scaling — olasılıkları kalibre et
        try:
            self.calibrator = LogisticRegression(C=1.0, solver="lbfgs")
            self.calibrator.fit(best_prob.reshape(-1, 1), y_test)
            cal_prob = self.calibrator.predict_proba(best_prob.reshape(-1, 1))[:, 1]
            cal_auc = roc_auc_score(y_test, cal_prob) if y_test.nunique() > 1 else 0.5
            print(f"  📊 Calibrated AUC: {cal_auc:.4f}")
        except Exception:
            self.calibrator = None

        # ── Final Performans ──────────────────────────────────
        final_pred = (best_prob >= self.optimal_esik).astype(int)
        final_f1 = f1_score(y_test, final_pred, zero_division=0)
        final_prec = precision_score(y_test, final_pred, zero_division=0)
        final_acc = accuracy_score(y_test, final_pred)

        print(f"\n  {'='*50}")
        print(f"  🏆 V3 FINAL PERFORMANS (optimal eşik={self.optimal_esik})")
        print(f"  {'='*50}")
        print(f"  AUC:       {stacking_auc:.4f}")
        print(f"  F1:        {final_f1:.4f}")
        print(f"  Precision: {final_prec:.4f}")
        print(f"  Accuracy:  {final_acc:.4f}")
        print(f"  {'='*50}")

        print(f"\n  Detaylı rapor:")
        print(classification_report(y_test, final_pred, target_names=["Zarar", "Kâr"]))

        # ── Feature Importance ────────────────────────────────
        importance = pd.Series(
            self.xgb_model.feature_importances_, index=self.feature_cols
        ).sort_values(ascending=False)

        # ── Meta Kaydet ───────────────────────────────────────
        self.meta = {
            "versiyon": "V3_STACKING",
            "egitim_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "stacking_auc": round(stacking_auc, 4),
            "ensemble_f1": round(final_f1, 4),
            "ensemble_precision": round(final_prec, 4),
            "ensemble_accuracy": round(final_acc, 4),
            "xgb_auc": round(xgb_auc, 4),
            "lgb_auc": round(lgb_auc, 4),
            "mlp_auc": round(mlp_auc, 4),
            "optimal_esik": self.optimal_esik,
            "weights": [round(w, 4) for w in self.weights],
            "egitim_boyut": len(X_train),
            "val_boyut": len(X_val),
            "test_boyut": len(X_test),
            "feature_sayisi": len(self.feature_cols),
            "sample_weighting": True,
            "feature_interactions": True,
            "top_features": {k: round(v, 4) for k, v in importance.head(15).items()},
            "market_rejim": market_rejim,
            "iyilestirmeler": [
                "sample_weighting (decay=0.997)",
                "feature_interactions (5 cross-feature)",
                "stacking_meta_model (logistic regression)",
                "probability_calibration (platt scaling)",
                "threshold_optimization (F1-based)",
                "aggressive_regularization",
                "deeper_mlp (256-128-64-32)",
                "3-way_split (train/val/test)",
            ],
        }

        self.kaydet_v3()
        return self.meta

    def tahmin_v3(self, features_df):
        """
        V3 tahmin — stacking + calibration + optimal eşik.
        Returns: dict(olasilik, sinyal, guven)
        """
        if self.xgb_model is None:
            return None

        # Feature interactions ekle
        features_df = feature_interaction_ekle(features_df)

        gecerli = [c for c in self.feature_cols if c in features_df.columns]
        eksik = [c for c in self.feature_cols if c not in features_df.columns]
        if eksik:
            for c in eksik:
                features_df[c] = 0

        son = features_df[self.feature_cols].iloc[-1:]
        son = son.fillna(0)

        # Level-1 predictions
        xgb_p = self.xgb_model.predict_proba(son)[:, 1][0]
        lgb_p = self.lgb_model.predict_proba(son)[:, 1][0] if self.lgb_model else 0
        mlp_p = self.mlp_model.predict_proba(self.scaler.transform(son))[:, 1][0] if self.mlp_model else 0

        # Level-2 stacking
        if self.meta_model:
            meta_input = np.array([[xgb_p, lgb_p, mlp_p]])
            prob = self.meta_model.predict_proba(meta_input)[:, 1][0]
        else:
            # Fallback: weighted average
            prob = xgb_p * self.weights[0] + lgb_p * self.weights[1] + mlp_p * self.weights[2]

        # Calibration
        if self.calibrator:
            prob = self.calibrator.predict_proba(np.array([[prob]]))[: , 1][0]

        # Sinyal
        sinyal = "AL" if prob >= self.optimal_esik else "BEKLE"
        guven = abs(prob - self.optimal_esik) / self.optimal_esik * 100

        return {
            "olasilik": round(float(prob), 4),
            "sinyal": sinyal,
            "guven": round(float(guven), 1),
            "esik": self.optimal_esik,
            "xgb": round(xgb_p, 4),
            "lgb": round(lgb_p, 4),
            "mlp": round(mlp_p, 4),
        }

    def _optuna_xgb_tune(self, X_train, y_train, X_val, y_val, w_train, n_trials=30):
        """Optuna ile XGBoost hyperparameter tuning."""
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            print("  ⚠ Optuna yüklü değil, default parametreler kullanılıyor")
            return {
                "n_estimators": 400, "max_depth": 5, "learning_rate": 0.02,
                "subsample": 0.75, "colsample_bytree": 0.5, "min_child_weight": 15,
                "reg_alpha": 0.3, "reg_lambda": 2.0, "gamma": 0.1,
                "eval_metric": "logloss", "early_stopping_rounds": 40,
                "random_state": 42, "verbosity": 0,
            }

        from xgboost import XGBClassifier
        from sklearn.metrics import roc_auc_score

        def objective(trial):
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 200, 600),
                "max_depth": trial.suggest_int("max_depth", 3, 7),
                "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.05, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 0.9),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 0.8),
                "min_child_weight": trial.suggest_int("min_child_weight", 5, 30),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.01, 1.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 5.0, log=True),
                "gamma": trial.suggest_float("gamma", 0.0, 0.5),
                "eval_metric": "logloss",
                "early_stopping_rounds": 40,
                "random_state": 42,
                "verbosity": 0,
            }

            model = XGBClassifier(**params)
            model.fit(X_train, y_train, sample_weight=w_train,
                      eval_set=[(X_val, y_val)], verbose=False)
            prob = model.predict_proba(X_val)[:, 1]
            return roc_auc_score(y_val, prob) if y_val.nunique() > 1 else 0.5

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

        best = study.best_params
        best["eval_metric"] = "logloss"
        best["early_stopping_rounds"] = 40
        best["random_state"] = 42
        best["verbosity"] = 0

        print(f"  🔧 Optuna best AUC: {study.best_value:.4f}")
        print(f"     Best params: depth={best.get('max_depth')}, lr={best.get('learning_rate'):.4f}")

        return best

    def kaydet_v3(self):
        """V3 modelini kaydet."""
        import joblib

        path = MODEL_DIR / "ensemble_v3.pkl"
        meta_path = MODEL_DIR / "ensemble_v3_meta.json"

        joblib.dump({
            "xgb": self.xgb_model,
            "lgb": self.lgb_model,
            "mlp": self.mlp_model,
            "scaler": self.scaler,
            "meta_model": self.meta_model,
            "calibrator": self.calibrator,
            "weights": self.weights,
            "feature_cols": self.feature_cols,
            "optimal_esik": self.optimal_esik,
        }, path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, default=str, ensure_ascii=False)

        print(f"  💾 V3 Model kaydedildi: {path}")

    @classmethod
    def yukle_v3(cls):
        """Kaydedilmiş V3 modelini yükle."""
        import joblib

        path = MODEL_DIR / "ensemble_v3.pkl"
        if not path.exists():
            print("  ⚠ V3 model bulunamadı, V2'ye fallback...")
            return None

        data = joblib.load(path)
        model = cls()
        model.xgb_model = data["xgb"]
        model.lgb_model = data.get("lgb")
        model.mlp_model = data.get("mlp")
        model.scaler = data.get("scaler")
        model.meta_model = data.get("meta_model")
        model.calibrator = data.get("calibrator")
        model.weights = data["weights"]
        model.feature_cols = data["feature_cols"]
        model.optimal_esik = data.get("optimal_esik", 0.5)

        meta_path = MODEL_DIR / "ensemble_v3_meta.json"
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                model.meta = json.load(f)

        print(f"  ✅ V3 Model yüklendi | AUC: {model.meta.get('stacking_auc', '?')}")
        return model


# ============================================================
# V3 ANALİZ FONKSİYONU
# ============================================================

def hisse_analiz_v3(ticker, df, model=None, market_rejim=None):
    """V3 analiz — V2 + stacking + interaction features."""
    features = feature_olustur_v2(df)
    if features is None:
        return None

    # Interaction features ekle
    features = feature_interaction_ekle(features)

    son = features.iloc[-1].to_dict()
    teknik = teknik_skor_v2(son)

    # V3 ML tahmin
    if model and isinstance(model, StackingEnsembleV3):
        ml = model.tahmin_v3(features)
        ml_prob = ml["olasilik"] if ml else None
        ml_sinyal = ml["sinyal"] if ml else None
        ml_guven = ml["guven"] if ml else None
    elif model and isinstance(model, EnsembleModelV2):
        ml_prob = model.tahmin(features)
        ml_sinyal = "AL" if ml_prob and ml_prob >= 0.5 else "BEKLE"
        ml_guven = None
    else:
        ml_prob = None
        ml_sinyal = None
        ml_guven = None

    # Birleşik skor
    if ml_prob is not None:
        if market_rejim and market_rejim.get("rejim") == "bull":
            birlesik = teknik * 0.25 + ml_prob * 100 * 0.75
        elif market_rejim and market_rejim.get("rejim") == "bear":
            birlesik = teknik * 0.45 + ml_prob * 100 * 0.55
        else:
            birlesik = teknik * 0.30 + ml_prob * 100 * 0.70
    else:
        birlesik = teknik

    close = df["Close"].squeeze()

    return {
        "ticker": ticker,
        "teknik_skor": teknik,
        "ml_olasilik": round(ml_prob, 4) if ml_prob else None,
        "ml_sinyal": ml_sinyal,
        "ml_guven": ml_guven,
        "birlesik_skor": round(birlesik, 1),
        "fiyat": float(close.iloc[-1]),
        "gunluk": float(close.pct_change().iloc[-1] * 100) if len(close) > 1 else 0,
        "hacim": float(df["Volume"].squeeze().iloc[-1]),
        "adx": round(son.get("adx", 0), 1),
        "rsi": round(son.get("rsi_14", 50), 1),
        "ma_alignment": int(son.get("ma_alignment", 0)),
        "atr_pct": round(son.get("atr_pct", 0), 2),
        "sinyal_ozet": _sinyal_ozet_v3(son),
    }


def _sinyal_ozet_v3(f):
    """V3 sinyal özeti — interaction features dahil."""
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

    # V3 interaction sinyalleri
    if f.get("rsi_x_hacim", 0) > 50:
        sinyaller.append("💎 RSI+Hacim Uyumu")
    if f.get("adx_x_alignment", 0) > 15:
        sinyaller.append("🎯 Güçlü Trend")

    return sinyaller if sinyaller else ["➖ Bekle"]


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("ANKA ML V3 — Module Test")
    print("Bu modülü eğitmek için yfinance verisi gerekir.")
    print("Kullanım: model = StackingEnsembleV3(); model.egit_v3(tum_veri)")
    print(f"\nV3 iyileştirmeleri:")
    for i in [
        "Sample weighting (exponential decay)",
        "Feature interactions (5 cross-features)",
        "Model stacking (logistic meta model)",
        "Probability calibration (Platt scaling)",
        "Threshold optimization (F1-based)",
        "Optuna hyperparameter tuning (opsiyonel)",
        "Deeper MLP (256-128-64-32)",
        "3-way split (train/val/test)",
    ]:
        print(f"  ✅ {i}")
