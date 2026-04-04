"""
Crypto AI Egitim Scripti
========================
- Top 15 coin icin 2 yillik saatlik veri indirir (Binance public API)
- Feature engineering: EMA cross, RSI, MACD, BB width, Volume ratio, OBV, Momentum, BTC correlation
- Triple Barrier labeling: +3% TP / -2% SL / 24h time barrier
- XGBoost modeli egitir
- AUC, feature importance, per-coin accuracy yazdirir
- Modeli kaydeder: borsa_surpriz/models/coin_ai_v1.pkl
"""

import os
import time
import pickle
import warnings
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore")

# ── Sabitler ─────────────────────────────────────────────────────────────────
COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT",
    "ATOMUSDT", "NEARUSDT", "FTMUSDT", "ARBUSDT", "OPUSDT",
]
INTERVAL       = "1h"
YEARS          = 2
TP_PCT         = 0.03    # +3%  üst bariyer
SL_PCT         = 0.02    # -2%  alt bariyer
TIME_BARRIER   = 24      # bar sayisi (1h → 24 saat)
MODEL_PATH     = "/Users/onurbodur/adsız klasör/borsa_surpriz/models/coin_ai_v1.pkl"
BINANCE_URL    = "https://api.binance.com/api/v3/klines"
LIMIT_PER_REQ  = 1000    # Binance max limit

# ── Yardimci: Binance klines indirici ────────────────────────────────────────

def fetch_klines(symbol: str, interval: str = "1h", years: int = 2) -> pd.DataFrame:
    """Binance public API'den paginated sekilde saatlik veri indirir."""
    end_ts   = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=years * 365)).timestamp() * 1000)

    all_rows = []
    current_start = start_ts

    while current_start < end_ts:
        params = {
            "symbol":    symbol,
            "interval":  interval,
            "startTime": current_start,
            "endTime":   end_ts,
            "limit":     LIMIT_PER_REQ,
        }
        try:
            resp = requests.get(BINANCE_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [HATA] {symbol} veri cekilemedi: {e}")
            time.sleep(2)
            continue

        if not data:
            break

        all_rows.extend(data)
        last_ts = data[-1][0]

        if len(data) < LIMIT_PER_REQ:
            break

        current_start = last_ts + 1
        time.sleep(0.15)   # rate limit korumasi

    if not all_rows:
        return pd.DataFrame()

    cols = ["open_time","open","high","low","close","volume",
            "close_time","quote_vol","trades","taker_buy_base",
            "taker_buy_quote","ignore"]
    df = pd.DataFrame(all_rows, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open","high","low","close","volume"]:
        df[c] = df[c].astype(float)
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    return df[["open_time","open","high","low","close","volume"]]


# ── Feature Engineering ───────────────────────────────────────────────────────

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_g = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_l = loss.ewm(com=period - 1, min_periods=period).mean()
    rs    = avg_g / avg_l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    m_line = ema(series, fast) - ema(series, slow)
    s_line = ema(m_line, signal)
    hist   = m_line - s_line
    return m_line, s_line, hist

def bollinger_width(series: pd.Series, period: int = 20) -> pd.Series:
    mid  = series.rolling(period).mean()
    std  = series.rolling(period).std()
    return (2 * std) / mid.replace(0, np.nan)

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()

def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
    avg = volume.rolling(period).mean()
    return volume / avg.replace(0, np.nan)

def momentum(close: pd.Series, periods: list) -> dict:
    return {f"mom_{p}h": close.pct_change(p) for p in periods}

def rolling_btc_correlation(coin_ret: pd.Series, btc_ret: pd.Series, window: int = 24) -> pd.Series:
    return coin_ret.rolling(window).corr(btc_ret)

def build_features(df: pd.DataFrame, btc_returns: pd.Series) -> pd.DataFrame:
    close = df["close"]
    vol   = df["volume"]

    # EMA cross
    e10 = ema(close, 10)
    e20 = ema(close, 20)
    df["ema_cross"]    = (e10 - e20) / close   # normalize

    # RSI
    df["rsi14"]        = rsi(close, 14)

    # MACD
    _, _, df["macd_hist"] = macd(close)

    # Bollinger Band genisligi
    df["bb_width"]     = bollinger_width(close, 20)

    # Volume ratio
    df["vol_ratio"]    = volume_ratio(vol, 20)

    # OBV trendi (normalize: 24h degisim)
    obv_series         = obv(close, vol)
    df["obv_trend"]    = obv_series.diff(24) / (np.abs(obv_series.shift(24)) + 1e-9)

    # Momentum
    moms = momentum(close, [1, 4, 24])
    for k, v in moms.items():
        df[k] = v

    # BTC korelasyonu
    coin_ret           = close.pct_change()
    df["btc_corr"]     = rolling_btc_correlation(coin_ret, btc_returns, window=24)

    return df


# ── Triple Barrier Labeling ───────────────────────────────────────────────────

def triple_barrier_labels(close: pd.Series,
                           tp: float = TP_PCT,
                           sl: float = SL_PCT,
                           max_bars: int = TIME_BARRIER) -> pd.Series:
    """
    Returns:
        1  → TP tarafi vuruldu (yukari)
        0  → SL tarafi vuruldu (asagi)  VEYA zaman bariyeri doldu
    Simplelestirilmis binary label: TP=1, diger=0
    """
    n      = len(close)
    labels = np.full(n, np.nan)
    prices = close.values

    for i in range(n - max_bars):
        entry = prices[i]
        tp_px = entry * (1 + tp)
        sl_px = entry * (1 - sl)

        label = 0   # varsayilan: TP vurulmadi
        for j in range(1, max_bars + 1):
            if prices[i + j] >= tp_px:
                label = 1
                break
            elif prices[i + j] <= sl_px:
                label = 0
                break
        labels[i] = label

    return pd.Series(labels, index=close.index)


# ── Ana Akis ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Crypto AI Egitim Scripti Basladi")
    print(f"  Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1) Veri indir
    print("\n[1/5] Binance'den veri indiriliyor...")
    raw_data: dict[str, pd.DataFrame] = {}
    for coin in COINS:
        print(f"  Indiriliyor: {coin} ...", end=" ", flush=True)
        df = fetch_klines(coin, INTERVAL, YEARS)
        if df.empty:
            print("BOS - atlanıyor")
            continue
        raw_data[coin] = df
        print(f"{len(df):,} satir OK")

    if "BTCUSDT" not in raw_data:
        print("[KRITIK] BTC verisi alinamadi, cikiliyor.")
        return

    # BTC returns referans
    btc_returns = raw_data["BTCUSDT"]["close"].pct_change()

    # 2) Feature engineering + labeling
    print("\n[2/5] Feature engineering & Triple Barrier labeling...")
    dataset_frames = []

    for coin, df in raw_data.items():
        print(f"  {coin} isleniyor...", end=" ", flush=True)

        # BTC returns ile hizala (index esitle)
        btc_ret_aligned = btc_returns.reindex(df.index).fillna(0)

        df = build_features(df.copy(), btc_ret_aligned)
        df["label"]  = triple_barrier_labels(df["close"], TP_PCT, SL_PCT, TIME_BARRIER)
        df["symbol"] = coin
        dataset_frames.append(df)
        tp_count = (df["label"] == 1).sum()
        total    = df["label"].notna().sum()
        print(f"{total:,} etiket, TP orani={tp_count/max(total,1)*100:.1f}%")

    full_df = pd.concat(dataset_frames, ignore_index=True)

    # 3) Veri temizleme
    print("\n[3/5] Veri temizleniyor...")
    feature_cols = [
        "ema_cross", "rsi14", "macd_hist", "bb_width",
        "vol_ratio", "obv_trend", "mom_1h", "mom_4h", "mom_24h", "btc_corr",
    ]

    full_df = full_df.dropna(subset=feature_cols + ["label"])
    full_df["label"] = full_df["label"].astype(int)

    print(f"  Toplam ornek: {len(full_df):,}")
    print(f"  TP=1 : {(full_df['label']==1).sum():,}  ({(full_df['label']==1).mean()*100:.1f}%)")
    print(f"  TP=0 : {(full_df['label']==0).sum():,}  ({(full_df['label']==0).mean()*100:.1f}%)")

    X = full_df[feature_cols]
    y = full_df["label"]

    # 4) Model egitimi
    print("\n[4/5] XGBoost modeli egitiliyor...")
    try:
        import xgboost as xgb
    except ImportError:
        print("  xgboost bulunamadi, pip install xgboost calistirilıyor...")
        os.system("pip install xgboost -q")
        import xgboost as xgb

    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_auc_score, accuracy_score, classification_report

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False   # zaman sirasi koruyarak bol
    )

    scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    model = xgb.XGBClassifier(
        n_estimators     = 500,
        max_depth        = 6,
        learning_rate    = 0.05,
        subsample        = 0.8,
        colsample_bytree = 0.8,
        scale_pos_weight = scale_pos,
        use_label_encoder= False,
        eval_metric      = "auc",
        random_state     = 42,
        n_jobs           = -1,
        verbosity        = 0,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # 5) Sonuclar
    print("\n[5/5] Sonuclar:")
    print("-" * 60)

    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred       = model.predict(X_test)

    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n  GENEL AUC       : {auc:.4f}")
    print(f"  GENEL Accuracy  : {acc:.4f}")

    print("\n  Classification Report:")
    print(classification_report(y_test, y_pred, target_names=["No-TP (0)", "TP Hit (1)"]))

    # Feature importance
    print("\n  Feature Importance (gain):")
    importance = dict(zip(feature_cols, model.feature_importances_))
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        bar = "█" * int(imp * 100)
        print(f"    {feat:<15} {imp:.4f}  {bar}")

    # Per-coin accuracy
    print("\n  Per-Coin Accuracy (test seti):")
    test_df = full_df.iloc[len(X_train):].copy()
    test_df["pred"]  = y_pred
    test_df["proba"] = y_pred_proba

    for coin in COINS:
        sub = test_df[test_df["symbol"] == coin]
        if len(sub) < 10:
            continue
        coin_acc = accuracy_score(sub["label"], sub["pred"])
        coin_auc = roc_auc_score(sub["label"], sub["proba"]) if sub["label"].nunique() > 1 else float("nan")
        tp_rate  = sub["label"].mean() * 100
        print(f"    {coin:<12} acc={coin_acc:.3f}  auc={coin_auc:.3f}  TP%={tp_rate:.1f}%  n={len(sub):,}")

    # 6) Kaydet
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    save_obj = {
        "model":        model,
        "feature_cols": feature_cols,
        "tp_pct":       TP_PCT,
        "sl_pct":       SL_PCT,
        "time_barrier": TIME_BARRIER,
        "train_date":   datetime.now().isoformat(),
        "auc":          auc,
        "accuracy":     acc,
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(save_obj, f)

    print(f"\n  Model kaydedildi: {MODEL_PATH}")
    print("\n" + "=" * 60)
    print("  EGITIM TAMAMLANDI")
    print("=" * 60)


if __name__ == "__main__":
    main()
