"""
BIST Walk-Forward Trading Backtest — DURUST edge olcumu
========================================================
backtest_bist.py'nin sorunu: modeli, backtest ettigi donemin USTUNDE egitilmis
(in-sample) -> +%19.6/yil sonucu look-ahead ile sismis. Bu harness onu duzeltir.

Walk-forward (expanding window) + embargo:
  - Her fold: model SADECE gecmis veriyle egitilir (date <= cutoff)
  - Triple-barrier hedefi 5 gun ileri baktigi icin train ile test arasina
    EMBARGO (hedef_gun kadar gun) konur -> etiket sizintisi yok
  - Skorlama OOS: modelin hic gormedigi gunlerde tahmin
  - Trade simulasyonu: gunluk top-k secim (canli bot mantigi), komisyon dahil
  - Benchmark: ayni OOS donemde endeks (XU100) Al&Tut

Kullanim:
  VPS (yfinance acik):  python backtest_walkforward.py
  Smoke-test (CSV):     python backtest_walkforward.py --csv data/price_history_2yil.csv

NOT: cloud sandbox'ta yfinance BLOKE. Gercek BIST sayilari VPS'te uretilir.
Smoke-test CSV ile harness mantigi (look-ahead bug yok) dogrulanir.
"""
import argparse
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from anka_ai_egitim import BIST50, feature_hesapla, hedef_hesapla  # noqa: E402

# ── Parametreler (canli bot ile hizali) ──
HEDEF_GUN = 5          # triple-barrier zaman bariyeri
KAR_ESIK = 2.0         # +%2 TP
ZARAR_LIMIT = -1.5     # -%1.5 SL
MAX_POZ = 3            # gunluk max pozisyon (canli: max 3)
KOMISYON = 0.001       # alim+satim TOPLAM binde 1 (kullanici, 2026-06-04)
SLIPPAGE = 0.0005      # tek yon kayma
PROBA_ESIK = 0.55      # modelin "al" dedigi minimum olasilik
TEST_PENCERE = 60      # her fold OOS test gun sayisi (~3 ay borsa gunu)
MIN_TRAIN_GUN = 252    # ilk fold icin minimum egitim gunu (~1 yil)
MIN_TRAIN = 300        # ek guvenlik: minimum egitim ornegi


CACHE_YOL = ROOT / "data" / "bist_gunluk_cache.pkl"
CACHE_SAAT = 20  # cache bu kadar saatten taze ise yfinance'e gitme


def veri_yukle_yfinance(yil=5):
    """
    VPS: BIST50 + endeks N yillik gunluk veri.
    yfinance RATE-LIMIT'e karsi cache: basarili indirme pickle'lanir, <20h ise
    tekrar indirilmez (ardisik backtest kosulari Yahoo'yu yormaz).
    """
    import time
    if CACHE_YOL.exists():
        yas_saat = (time.time() - CACHE_YOL.stat().st_mtime) / 3600
        if yas_saat < CACHE_SAAT:
            try:
                import pickle
                with open(CACHE_YOL, "rb") as f:
                    d = pickle.load(f)
                print(f"  cache kullanildi ({yas_saat:.1f}h taze): {len(d['veri'])} hisse")
                return d["veri"], d.get("xu")
            except Exception:
                pass

    import yfinance as yf
    veri, basari = {}, 0
    for s in BIST50:
        try:
            df = yf.download(f"{s}.IS", period=f"{yil}y", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) >= 300:
                veri[s] = df
                basari += 1
        except Exception:
            pass
    print(f"  yfinance: {basari}/{len(BIST50)} hisse")
    try:
        xu = yf.download("XU100.IS", period=f"{yil}y", progress=False, auto_adjust=True)
        if isinstance(xu.columns, pd.MultiIndex):
            xu.columns = xu.columns.get_level_values(0)
    except Exception:
        xu = None
    # Basarili indirme cache'lenir (rate-limit'e karsi)
    if basari >= 10:
        try:
            import pickle
            with open(CACHE_YOL, "wb") as f:
                pickle.dump({"veri": veri, "xu": xu}, f)
        except Exception:
            pass
    return veri, xu


def veri_yukle_csv(yol):
    """Smoke-test: intraday CSV -> gunluk OHLCV (sembol basina)."""
    raw = pd.read_csv(yol)
    raw["datetime"] = pd.to_datetime(raw["datetime"], utc=True)
    veri = {}
    for sym, g in raw.groupby("symbol"):
        g = g.set_index("datetime").sort_index()
        gunluk = g.resample("1D").agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}
        ).dropna()
        gunluk.columns = ["Open", "High", "Low", "Close", "Volume"]
        if len(gunluk) >= 300:
            veri[sym] = gunluk
    print(f"  CSV: {len(veri)} sembol (gunluge resample edildi)")
    return veri, None


def panel_hazirla(veri):
    """
    Her hisse icin feature + hedef hesapla, (sembol, tarih) indeksli birlesik
    panel uret. feature_hesapla SADECE geriye-donuk (ewm/rolling/shift) ->
    satir t yalniz <=t veriyi kullanir, look-ahead YOK.
    """
    parcalar = []
    skor_cache = {}  # (sembol) -> feature DataFrame (tarih indeksli)
    for s, df in veri.items():
        try:
            feats = feature_hesapla(df)
            hedef, getiri = hedef_hesapla(df, HEDEF_GUN, KAR_ESIK, ZARAR_LIMIT)
            ortak = feats.index.intersection(hedef.dropna().index)
            if len(ortak) < 150:
                continue
            X = feats.loc[ortak].copy()
            X["__sembol"] = s
            X["__tarih"] = ortak
            X["__hedef"] = hedef.loc[ortak].values
            parcalar.append(X)
            skor_cache[s] = feats
        except Exception:
            continue
    if not parcalar:
        return None, None
    panel = pd.concat(parcalar, ignore_index=True)
    panel["__tarih"] = pd.to_datetime(panel["__tarih"])
    return panel, skor_cache


def kesitsel_ekle(panel, xu):
    """
    KESITSEL + ENDEKS-RELATIF + REJIM feature'lari ekle (hepsi causal, look-ahead YOK).
    Mevcut feature'lar tek-hisse; bunlar 'bugun digerlerine GORE' boyutunu katar.

    - ks_mom_rank/ks_vol_rank/ks_rsi_rank: o gun TUM evrende yuzdelik sira (kesitsel)
    - ks_xu_rel5/ks_xu_rel10: hisse getirisi − XU100 getirisi (relative strength)
    - ks_rejim: XU100 50g SMA ustunde mi (1/0) — boga/ayi rejim filtresi
    - ks_xu_vol: XU100 20g volatilite (piyasa stres)
    """
    p = panel.copy()
    # Kesitsel siralama (sadece panel — o gun digerlerine gore)
    for src, dst in [("mom_10d", "ks_mom_rank"),
                     ("hacim_oran", "ks_vol_rank"),
                     ("rsi", "ks_rsi_rank")]:
        if src in p.columns:
            p[dst] = p.groupby("__tarih")[src].rank(pct=True)

    # Endeks-relatif + rejim (XU100 gerekli)
    if xu is not None and "Close" in getattr(xu, "columns", []):
        xc = xu["Close"].astype(float)
        xr5 = xc.pct_change(5) * 100
        xr10 = xc.pct_change(10) * 100
        xtrend = (xc > xc.rolling(50).mean()).astype(float)
        xvol = (xc.pct_change() * 100).rolling(20).std()

        def mp(series):
            s = series.copy()
            s.index = pd.to_datetime(s.index).normalize()
            s = s[~s.index.duplicated(keep="last")]
            return p["__tarih"].dt.normalize().map(s)

        if "mom_5d" in p.columns:
            p["ks_xu_rel5"] = p["mom_5d"] - mp(xr5).fillna(0)
        if "mom_10d" in p.columns:
            p["ks_xu_rel10"] = p["mom_10d"] - mp(xr10).fillna(0)
        p["ks_rejim"] = mp(xtrend).fillna(0)
        p["ks_xu_vol"] = mp(xvol)
    return p


def model_egit(X, y):
    """xgb + lgbm ensemble (tek fold)."""
    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    xgb = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                        subsample=0.8, colsample_bytree=0.8,
                        eval_metric="logloss", verbosity=0, random_state=42)
    lgbm = LGBMClassifier(n_estimators=200, max_depth=5, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8, verbose=-1,
                          random_state=42)
    xgb.fit(X, y)
    lgbm.fit(X, y)
    return [xgb, lgbm]


def proba(models, X):
    return np.mean([m.predict_proba(X)[:, 1] for m in models], axis=0)


def triple_barrier_sonuc(df, giris_tarih, giris_fiyat):
    """Bir pozisyonun triple-barrier ile net getirisi (% , komisyon HARIC)."""
    idx = df.index
    try:
        i0 = idx.get_loc(giris_tarih)
    except KeyError:
        return None
    son = min(i0 + HEDEF_GUN, len(idx) - 1)
    for j in range(i0 + 1, son + 1):
        yuk = (df["High"].iloc[j] - giris_fiyat) / giris_fiyat * 100
        asg = (df["Low"].iloc[j] - giris_fiyat) / giris_fiyat * 100
        if yuk >= KAR_ESIK:
            return KAR_ESIK
        if asg <= ZARAR_LIMIT:
            return ZARAR_LIMIT
    if son > i0:
        return (df["Close"].iloc[son] - giris_fiyat) / giris_fiyat * 100
    return None


def walk_forward(veri, panel, skor_cache, benchmark=None, feat_cols=None):
    if feat_cols is None:
        feat_cols = [c for c in panel.columns if not c.startswith("__")]
    tarihler = np.sort(panel["__tarih"].unique())
    embargo = HEDEF_GUN

    # Fold sinirlari: ilk MIN_TRAIN orneklikten sonra TEST_PENCERE'lik dilimler
    fold_sonuc = []
    tum_trade = []      # her OOS trade getirisi (komisyon dahil)
    oos_proba, oos_y = [], []
    equity = [1.0]
    oos_ilk, oos_son = None, None

    # test pencerelerini tarih ekseninde kaydir
    benzersiz = list(tarihler)
    # train baslangici: en az MIN_TRAIN_GUN farkli gun gormus olalim
    i = min(MIN_TRAIN_GUN, len(benzersiz) - 1)
    fold = 0
    while i + embargo + TEST_PENCERE < len(benzersiz):
        train_kesim = benzersiz[i]
        test_basla = benzersiz[i + embargo]
        test_bit = benzersiz[min(i + embargo + TEST_PENCERE, len(benzersiz) - 1)]

        tr = panel[panel["__tarih"] <= train_kesim]
        te = panel[(panel["__tarih"] >= test_basla) & (panel["__tarih"] <= test_bit)]
        if len(tr) < MIN_TRAIN or len(te) < 20 or tr["__hedef"].nunique() < 2:
            i += TEST_PENCERE
            continue
        fold += 1
        models = model_egit(tr[feat_cols], tr["__hedef"])
        p = proba(models, te[feat_cols])
        te = te.assign(__p=p)
        oos_proba.extend(p.tolist())
        oos_y.extend(te["__hedef"].tolist())

        from sklearn.metrics import roc_auc_score
        try:
            f_auc = roc_auc_score(te["__hedef"], p) if te["__hedef"].nunique() > 1 else float("nan")
        except Exception:
            f_auc = float("nan")

        # ── Gunluk top-k trade simulasyonu (OOS) ──
        f_trades = []
        for gun, grup in te.groupby("__tarih"):
            adaylar = grup[grup["__p"] >= PROBA_ESIK].sort_values("__p", ascending=False)
            for _, row in adaylar.head(MAX_POZ).iterrows():
                s = row["__sembol"]
                df_s = veri[s]
                try:
                    giris = float(df_s.loc[gun]["Close"])
                except Exception:
                    continue
                ham = triple_barrier_sonuc(df_s, gun, giris)
                if ham is None:
                    continue
                net = ham - (KOMISYON + 2 * SLIPPAGE) * 100  # round-trip maliyet
                f_trades.append(net)
                tum_trade.append(net)
        if oos_ilk is None:
            oos_ilk = test_basla
        oos_son = test_bit

        # fold getiri (esit agirlik gunluk degil; basitlik icin trade-ort)
        if f_trades:
            arr = np.array(f_trades)
            for t in f_trades:
                equity.append(equity[-1] * (1 + (t / 100) / MAX_POZ))
            kazanc = float((arr > 0).mean() * 100)
            ort = float(arr.mean())
        else:
            kazanc, ort = 0.0, 0.0
        fold_sonuc.append({
            "fold": fold, "train_n": len(tr), "test_n": len(te),
            "auc": round(f_auc, 4), "trade": len(f_trades),
            "kazanc": round(kazanc, 1), "ort_net": round(ort, 3),
            "donem": f"{pd.Timestamp(test_basla).date()}→{pd.Timestamp(test_bit).date()}",
        })
        i += TEST_PENCERE

    return fold_sonuc, tum_trade, oos_proba, oos_y, equity, (oos_ilk, oos_son)


def benchmark_getiri(benchmark, ilk, son):
    if benchmark is None or ilk is None:
        return None
    try:
        b = benchmark.loc[(benchmark.index >= pd.Timestamp(ilk)) &
                          (benchmark.index <= pd.Timestamp(son))]
        if len(b) < 2:
            return None
        return float((b["Close"].iloc[-1] / b["Close"].iloc[0] - 1) * 100)
    except Exception:
        return None


def rapor_yaz(fold_sonuc, tum_trade, oos_proba, oos_y, equity, span, bench_pct, kaynak):
    from sklearn.metrics import roc_auc_score
    out = ROOT / "data" / "backtest_walkforward_rapor.md"
    md = ["# 🦅 BIST Walk-Forward Backtest — DURUST OOS edge", "",
          f"_{datetime.now():%Y-%m-%d %H:%M} · kaynak: {kaynak}_", ""]
    if not fold_sonuc:
        md.append("❌ Yeterli fold uretilemedi (veri kisa).")
        out.write_text("\n".join(md), encoding="utf-8")
        print("\n".join(md))
        return

    try:
        genel_auc = roc_auc_score(oos_y, oos_proba) if len(set(oos_y)) > 1 else float("nan")
    except Exception:
        genel_auc = float("nan")
    arr = np.array(tum_trade) if tum_trade else np.array([0.0])
    toplam_getiri = (equity[-1] - 1) * 100
    pik = np.maximum.accumulate(equity)
    max_dd = float(((np.array(equity) / pik - 1).min()) * 100)
    sharpe = float(arr.mean() / arr.std()) if arr.std() > 0 else 0.0
    kazanc = float((arr > 0).mean() * 100)

    md += [
        "## Ozet (OUT-OF-SAMPLE, look-ahead YOK)", "",
        f"- **Genel OOS AUC:** {genel_auc:.4f}",
        f"- **Fold sayisi:** {len(fold_sonuc)}  ·  OOS donem: {span[0]} → {span[1]}",
        f"- **Toplam OOS trade:** {len(tum_trade)}  ·  Kazanc orani: %{kazanc:.1f}",
        f"- **Ort. net trade getirisi:** %{arr.mean():+.3f} (komisyon+slippage dahil)",
        f"- **Bilesik OOS getiri:** %{toplam_getiri:+.1f}  ·  Max drawdown: %{max_dd:.1f}  ·  Sharpe(trade): {sharpe:.3f}",
    ]
    if bench_pct is not None:
        fark = toplam_getiri - bench_pct
        md += [f"- **Benchmark (endeks Al&Tut):** %{bench_pct:+.1f}",
               f"- **Edge (strateji − benchmark):** %{fark:+.1f} "
               f"{'✅ strateji ONDE' if fark > 0 else '⚠️ benchmark ONDE'}"]
    md += ["", "## Fold detay", "",
           "| Fold | Donem | Train | Test | AUC | Trade | Kazanc% | OrtNet% |",
           "|---|---|---|---|---|---|---|---|"]
    for f in fold_sonuc:
        md.append(f"| {f['fold']} | {f['donem']} | {f['train_n']} | {f['test_n']} | "
                  f"{f['auc']} | {f['trade']} | %{f['kazanc']} | %{f['ort_net']:+} |")
    md += ["", "## Yorum",
           "- Bu sayilar **gercek OOS** — model her fold'da sadece gecmisi gordu, "
           "etiket sizintisi embargo ile engellendi.",
           "- backtest_bist.py (in-sample) ile FARK = look-ahead'in sismesi.",
           "- Edge pozitifse: canli MIN_BOMBA_SKOR_ALIS / PROBA_ESIK kalibre edilir.",
           "- Edge negatifse: sinyal zayif -> feature muhendisligi (kesitsel/rejim) sart."]
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\n💾 {out}")


def metrik_hesapla(sonuc, bench_pct):
    """walk_forward sonucundan ozet metrik dict."""
    from sklearn.metrics import roc_auc_score
    fold_sonuc, tum_trade, oos_p, oos_y, equity, span = sonuc
    try:
        auc = roc_auc_score(oos_y, oos_p) if len(set(oos_y)) > 1 else float("nan")
    except Exception:
        auc = float("nan")
    arr = np.array(tum_trade) if tum_trade else np.array([0.0])
    toplam = (equity[-1] - 1) * 100
    pik = np.maximum.accumulate(equity)
    dd = float(((np.array(equity) / pik - 1).min()) * 100)
    return {
        "auc": auc, "trade": len(tum_trade),
        "kazanc": float((arr > 0).mean() * 100), "ort_net": float(arr.mean()),
        "getiri": toplam, "dd": dd,
        "sharpe": float(arr.mean() / arr.std()) if arr.std() > 0 else 0.0,
        "edge": (toplam - bench_pct) if bench_pct is not None else None,
        "fold": len(fold_sonuc), "span": span, "fold_sonuc": fold_sonuc,
    }


def karsilastir_rapor(m_base, m_ks, bench_pct, kaynak, n_base, n_ks):
    out = ROOT / "data" / "backtest_walkforward_rapor.md"
    md = ["# 🦅 BIST Walk-Forward — Feature A/B (DURUST OOS)", "",
          f"_{datetime.now():%Y-%m-%d %H:%M} · kaynak: {kaynak} · look-ahead YOK_", "",
          "Ayni panel, ayni fold'lar; tek fark feature seti. **Kesitsel/endeks-relatif/"
          "rejim feature'lari edge'i artiriyor mu?**", "",
          "| Metrik | Baseline (tek-hisse) | +Kesitsel | Fark |",
          "|---|---|---|---|",
          f"| Feature sayisi | {n_base} | {n_ks} | +{n_ks - n_base} |",
          f"| **OOS AUC** | {m_base['auc']:.4f} | {m_ks['auc']:.4f} | "
          f"{m_ks['auc'] - m_base['auc']:+.4f} |",
          f"| Ort net trade % | %{m_base['ort_net']:+.3f} | %{m_ks['ort_net']:+.3f} | "
          f"%{m_ks['ort_net'] - m_base['ort_net']:+.3f} |",
          f"| Kazanc % | %{m_base['kazanc']:.1f} | %{m_ks['kazanc']:.1f} | "
          f"%{m_ks['kazanc'] - m_base['kazanc']:+.1f} |",
          f"| Bilesik getiri % | %{m_base['getiri']:+.1f} | %{m_ks['getiri']:+.1f} | "
          f"%{m_ks['getiri'] - m_base['getiri']:+.1f} |",
          f"| Max DD % | %{m_base['dd']:.1f} | %{m_ks['dd']:.1f} | — |",
          f"| Sharpe(trade) | {m_base['sharpe']:.3f} | {m_ks['sharpe']:.3f} | "
          f"{m_ks['sharpe'] - m_base['sharpe']:+.3f} |",
          f"| Trade sayisi | {m_base['trade']} | {m_ks['trade']} | — |"]
    if bench_pct is not None:
        md.append(f"| Benchmark B&H % | %{bench_pct:+.1f} | %{bench_pct:+.1f} | — |")
    auc_fark = m_ks["auc"] - m_base["auc"]
    md += ["", "## Sonuc",
           f"- OOS dönem: {m_base['span'][0]} → {m_base['span'][1]} · {m_base['fold']} fold",
           f"- Kesitsel feature'lar AUC'yi **{auc_fark:+.4f}** değiştirdi "
           f"({'✅ İYİLEŞME' if auc_fark > 0.003 else '➖ kayda değer fark yok' if abs(auc_fark) <= 0.003 else '⚠️ KÖTÜLEŞME'}).",
           "- Eklenenler: ks_mom_rank/ks_vol_rank/ks_rsi_rank (kesitsel sıra), "
           "ks_xu_rel5/10 (endeks-relatif), ks_rejim (XU100 50g trend), ks_xu_vol.",
           "- Tüm feature'lar causal; embargo + expanding window ile sızıntı yok."]
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    print(f"\n💾 {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="intraday CSV ile smoke-test (yfinance yerine)")
    ap.add_argument("--yil", type=int, default=5)
    ap.add_argument("--karsilastir", action="store_true",
                    help="Baseline vs +Kesitsel feature A/B karsilastirmasi")
    ap.add_argument("--baseline", action="store_true",
                    help="Sadece tek-hisse feature'lar (kesitsel ekleme)")
    args = ap.parse_args()

    print("📥 Veri yukleniyor...")
    if args.csv:
        veri, bench = veri_yukle_csv(args.csv)
        kaynak = f"CSV smoke-test ({Path(args.csv).name})"
    else:
        veri, bench = veri_yukle_yfinance(args.yil)
        kaynak = "yfinance BIST50 (VPS)"
    if not veri:
        print("❌ Veri yok")
        return

    print("🧮 Panel (feature+hedef) hazirlaniyor...")
    panel, skor_cache = panel_hazirla(veri)
    if panel is None:
        print("❌ Panel bos")
        return
    base_cols = [c for c in panel.columns if not c.startswith("__")]
    panel = kesitsel_ekle(panel, bench)
    all_cols = [c for c in panel.columns if not c.startswith("__")]
    print(f"  Panel: {len(panel)} satir, base {len(base_cols)} + kesitsel "
          f"{len(all_cols) - len(base_cols)} = {len(all_cols)} feature, "
          f"{panel['__sembol'].nunique()} sembol")

    if args.karsilastir:
        print("🔁 A/B: baseline walk-forward...")
        s_base = walk_forward(veri, panel, skor_cache, bench, feat_cols=base_cols)
        print("🔁 A/B: +kesitsel walk-forward...")
        s_ks = walk_forward(veri, panel, skor_cache, bench, feat_cols=all_cols)
        bench_pct = benchmark_getiri(bench, s_base[5][0], s_base[5][1])
        karsilastir_rapor(metrik_hesapla(s_base, bench_pct),
                          metrik_hesapla(s_ks, bench_pct),
                          bench_pct, kaynak, len(base_cols), len(all_cols))
        return

    feat = base_cols if args.baseline else all_cols
    print(f"🔁 Walk-forward calisiyor ({len(feat)} feature)...")
    fs, tt, op, oy, eq, span = walk_forward(veri, panel, skor_cache, bench, feat_cols=feat)
    bench_pct = benchmark_getiri(bench, span[0], span[1])
    rapor_yaz(fs, tt, op, oy, eq, span, bench_pct, kaynak)


if __name__ == "__main__":
    main()
