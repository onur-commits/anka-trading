"""
Coin ML Skor Helper — coin_ai_v1 modelini yukler ve canli skor uretir
======================================================================
Bu modul coin_otonom_trader.py'ye DEGISIKLIK YAPMAZ.
Bot'u guncellemek isteyince:

    from coin_ml_score import CoinMLSkorlayici
    ml = CoinMLSkorlayici()             # model otomatik yuklenir (yoksa None)
    if ml.hazir:
        ml_olasilik = ml.skor(symbol, df, btc_df)   # 0.0–1.0 TP olasilik
        ml_puan = ml.puana_cevir(ml_olasilik)        # 0–100 skor

Featureler coin_ai_egitim.py ile birebir ayni (ayni siralama, ayni hesap).
Aksi takdirde model "shape mismatch" hatasi verir.

Mod:
  CLI:  python coin_ml_score.py --test BTCUSDT
  Lib:  from coin_ml_score import CoinMLSkorlayici
"""
from __future__ import annotations

import pickle
import time
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

# Feature fonksiyonlarini egitimi yapan modulden al — tek-kaynak (DRY)
# coin_ai_egitim.py'de tanimli: ema, rsi, macd, bollinger_width, obv,
# volume_ratio, momentum, rolling_btc_correlation, build_features.
from coin_ai_egitim import build_features

PROJECT_DIR = Path(__file__).parent
MODEL_PATH = PROJECT_DIR / "models" / "coin_ai_v1.pkl"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"

logger = logging.getLogger("coin_ml_score")


class CoinMLSkorlayici:
    """
    coin_ai_v1.pkl modelini yukleyip canli skor uretir.
    Model yoksa hazir=False olur, calistirildiginda 0.5 (notr) doner.
    Bot kor calismasin, ama ML olmayan veriden de etkilenmesin.
    """

    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = Path(model_path) if model_path else MODEL_PATH
        self.model = None
        self.feature_cols: list[str] = []
        self.train_meta: dict = {}
        self.hazir = False
        self._btc_df_cache: Optional[pd.DataFrame] = None
        self._btc_cache_zaman = 0.0
        self._yukle()

    def _yukle(self):
        if not self.model_path.exists():
            logger.warning(f"ML model yok: {self.model_path} — coin_ai_egitim.py calistirilarak uretilmeli")
            return
        try:
            with open(self.model_path, "rb") as f:
                save_obj = pickle.load(f)
            self.model = save_obj["model"]
            self.feature_cols = save_obj["feature_cols"]
            self.train_meta = {
                "train_date": save_obj.get("train_date", "?"),
                "auc": save_obj.get("auc", None),
                "accuracy": save_obj.get("accuracy", None),
                "tp_pct": save_obj.get("tp_pct", None),
                "sl_pct": save_obj.get("sl_pct", None),
            }
            self.hazir = True
            logger.info(
                f"Coin ML modeli yuklendi: {self.model_path.name} "
                f"(egitim {self.train_meta['train_date']}, AUC={self.train_meta['auc']})"
            )
        except Exception as e:
            logger.error(f"Model yuklenirken hata: {e}")
            self.hazir = False

    # ──────────────────────────────────────────────
    # BTC verisi (korelasyon icin lazim) — 5 dk cache
    # ──────────────────────────────────────────────
    def _btc_df(self, limit: int = 100) -> pd.DataFrame:
        simdi = time.time()
        # 5 dk cache — taramada her coin icin tekrar BTC indirilmesin
        if self._btc_df_cache is not None and simdi - self._btc_cache_zaman < 300:
            return self._btc_df_cache
        try:
            r = requests.get(
                BINANCE_KLINES,
                params={"symbol": "BTCUSDT", "interval": "1h", "limit": limit},
                timeout=10,
            )
            data = r.json()
            if not isinstance(data, list):
                logger.warning(f"BTC kline beklenmedik yanit: {data}")
                return pd.DataFrame()
            df = self._kline_df(data)
            self._btc_df_cache = df
            self._btc_cache_zaman = simdi
            return df
        except Exception as e:
            logger.error(f"BTC verisi alinamadi: {e}")
            return pd.DataFrame()

    @staticmethod
    def _kline_df(data: list) -> pd.DataFrame:
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "buy_base", "buy_quote", "ignore"
        ])
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = df[c].astype(float)
        return df[["open_time", "open", "high", "low", "close", "volume"]]

    # ──────────────────────────────────────────────
    # Canli skor
    # ──────────────────────────────────────────────
    def skor(self, symbol: str, df: pd.DataFrame,
             btc_df: Optional[pd.DataFrame] = None) -> float:
        """
        Bir coin icin TP olasiligi (0–1).
        df: coin'in OHLCV df'si (en az 100 bar, ayni format: open_time + ohlcv).
        btc_df: opsiyonel BTCUSDT df. Verilmezse otomatik cekilir (5 dk cache).
        Model yuklenemediyse 0.5 (notr) doner.
        """
        if not self.hazir or self.model is None:
            return 0.5
        if df is None or len(df) < 50:
            logger.debug(f"{symbol}: yetersiz veri ({len(df) if df is not None else 0} bar)")
            return 0.5

        # Coin df'sini egitimle ayni sutun isimlerine getir (open_time + lowercase ohlcv)
        coin_df = self._normalize(df)
        if coin_df is None:
            return 0.5

        # BTC referans
        if btc_df is None:
            btc_df = self._btc_df()
        if btc_df is None or btc_df.empty:
            logger.debug(f"{symbol}: BTC ref yok, model atlandi")
            return 0.5

        # Timestamp-bazli BTC returns (egitimle ayni)
        try:
            btc_idx = btc_df.set_index("open_time")
            btc_returns = btc_idx["close"].pct_change()
            btc_ret_aligned = (
                btc_returns.reindex(coin_df["open_time"]).fillna(0).reset_index(drop=True)
            )
        except Exception as e:
            logger.warning(f"{symbol}: BTC alignment hatasi: {e}")
            return 0.5

        # Feature olustur (egitimle birebir ayni fonksiyon)
        try:
            featured = build_features(coin_df.copy(), btc_ret_aligned)
            # Egitimdeki sutun siralamasini birebir kullan — model shape'i bekliyor
            son = featured.iloc[[-1]][self.feature_cols]
            if son.isna().any().any():
                # NaN feature varsa modele besleme — son barda yetersiz veri
                return 0.5
            olasilik = float(self.model.predict_proba(son)[0, 1])
            return olasilik
        except Exception as e:
            logger.warning(f"{symbol}: ml skor hesabi hata: {e}")
            return 0.5

    @staticmethod
    def _normalize(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        coin_otonom_trader.BinanceClient.kline() format: index=time, Open/High/Low/Close/Volume.
        coin_ai_egitim format: open_time sutunu + lowercase ohlcv.
        Bu fonksiyon ikisini de kabul edip egitimi format'ina cevirir.
        """
        try:
            d = df.copy()
            if "open_time" not in d.columns:
                # trader format'i: time index
                if d.index.name == "time" or isinstance(d.index, pd.DatetimeIndex):
                    d = d.reset_index().rename(columns={"time": "open_time"})
                else:
                    return None
            # Kolon adlarini lowercase'e cevir
            rename_map = {}
            for c in d.columns:
                if c.lower() in ("open", "high", "low", "close", "volume") and c != c.lower():
                    rename_map[c] = c.lower()
            if rename_map:
                d = d.rename(columns=rename_map)
            gerekli = {"open_time", "open", "high", "low", "close", "volume"}
            if not gerekli.issubset(set(d.columns)):
                return None
            return d[list(gerekli)].reset_index(drop=True)
        except Exception:
            return None

    @staticmethod
    def puana_cevir(olasilik: float) -> float:
        """
        0–1 olasilik → 0–100 skor. Egitim sirasinda TP class esitlenmis olabilir,
        bu yuzden 0.5'in altinda ML skoru bot icin "olumsuz" katki olarak yorumlanmali.
        Bot'un mevcut skor toplama mantigi 0–100 bekliyor.
        """
        return round(max(0.0, min(1.0, olasilik)) * 100, 1)


# ══════════════════════════════════════════════════════════════
# CLI test
# ══════════════════════════════════════════════════════════════
def _cli():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--test", default="BTCUSDT", help="Test edilecek sembol")
    p.add_argument("--meta", action="store_true", help="Sadece model metadata'sini goster")
    args = p.parse_args()

    ml = CoinMLSkorlayici()
    print(f"\nModel hazir: {ml.hazir}")
    if not ml.hazir:
        print("Model yok — once 'python coin_ai_egitim.py' calistirilmali.")
        return 1

    print(f"Model yolu: {ml.model_path}")
    print(f"Meta: {ml.train_meta}")
    print(f"Feature sayisi: {len(ml.feature_cols)}")
    print(f"Features: {ml.feature_cols}")

    if args.meta:
        return 0

    print(f"\nTest skoru: {args.test}")
    try:
        r = requests.get(
            BINANCE_KLINES,
            params={"symbol": args.test, "interval": "1h", "limit": 100},
            timeout=10,
        )
        data = r.json()
        if not isinstance(data, list):
            print(f"Veri alinamadi: {data}")
            return 1
        df = CoinMLSkorlayici._kline_df(data)
        olasilik = ml.skor(args.test, df)
        puan = ml.puana_cevir(olasilik)
        print(f"  TP olasilik: {olasilik:.4f}")
        print(f"  Puan (0-100): {puan}")
    except Exception as e:
        print(f"Test hatasi: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
