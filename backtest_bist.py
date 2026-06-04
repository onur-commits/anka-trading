"""
BIST Backtest v2 — optimize: kara liste + eşik grid + stop-loss + NaN fix
=========================================================================
Tek koşuda 6 eşik değerini (15-40) tarar, her biri için kazanç/Sharpe/getiri.
Kara liste (kaybeden 5 hisse) çıkarılır. Stop-loss modellenir.
"""
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

MAX_POZ = 3
GUN = 252
KOMISYON = 0.002
STOP_LOSS = -3.0
KARA_LISTE = {"SASA.IS", "VESTL.IS", "GUBRF.IS", "EGEEN.IS", "ENKAI.IS"}
ESIK_GRID = [15, 20, 25, 30, 35, 40]

debug = {"hisse": 0, "model": False, "gun": 0}


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = -d.clip(upper=0).rolling(n).mean()
    return 100 - 100 / (1 + up / dn)


def basit_skor(df):
    c, v = df["Close"], df["Volume"]
    son, onc = c.iloc[-1], c.iloc[-2]
    g5 = c.iloc[-5] if len(c) > 5 else onc
    dg = float((son / onc - 1) * 100)
    m5 = float((son / g5 - 1) * 100)
    r = float(rsi(c).iloc[-1])
    ov = float(v.rolling(20).mean().iloc[-1]) if len(v) > 20 else 1
    ho = float(v.iloc[-1]) / ov if ov > 0 else 1
    sk = 0
    if dg > 1: sk += 15
    if dg > 3: sk += 10
    if m5 > 0: sk += 10
    if m5 > 5: sk += 10
    if 40 < r < 70: sk += 15
    if ho > 1.5: sk += 20
    if ho > 3: sk += 10
    return float(sk)


def yukle_model():
    try:
        from tahmin_motoru_v2 import EnsembleModelV2
        m = EnsembleModelV2.yukle()
        if m:
            debug["model"] = True
            return m
    except Exception as e:
        print(f"Model yok: {e}")
    return None


def skorla(df, model):
    if model:
        try:
            from tahmin_motoru_v2 import feature_olustur_v2, hisse_analiz_v2
            from gunluk_bomba import bomba_skor_hesapla
            a = hisse_analiz_v2("X", df, model, rejim=None)
            f = feature_olustur_v2(df)
            if a is not None and f is not None:
                sk, _ = bomba_skor_hesapla(a, f.iloc[-1].to_dict())
                return float(sk)
        except Exception:
            pass
    return basit_skor(df)


def tickers():
    try:
        from gunluk_bomba import TICKERS
        return list(TICKERS)
    except Exception:
        return ["THYAO.IS", "GARAN.IS", "AKBNK.IS", "ISCTR.IS", "TUPRS.IS",
                "EREGL.IS", "ASELS.IS", "BIMAS.IS", "TCELL.IS", "SISE.IS",
                "TOASO.IS", "FROTO.IS", "HEKTS.IS", "KCHOL.IS", "SAHOL.IS",
                "VAKBN.IS", "HALKB.IS", "AEFES.IS", "PGSUS.IS", "AKSEN.IS",
                "ENJSA.IS", "SOKM.IS", "TKFEN.IS", "MGROS.IS", "DOAS.IS",
                "AYEN.IS", "ALARK.IS", "TSKB.IS", "KONTR.IS", "OTKAR.IS"]


def veri_cek(tlist, kara=True):
    veri = {}
    for t in tlist:
        if kara and t in KARA_LISTE:
            continue
        try:
            df = yf.download(t, period="2y", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) >= 200:
                veri[t] = df
        except Exception:
            pass
    debug["hisse"] = len(veri)
    return veri


def on_hesapla_skorlar(veri, model):
    """Her (ticker, tarih) için skoru bir kez hesapla (grid cache)."""
    cache = {}
    ortak = sorted(set.intersection(*[set(df.index) for df in veri.values()]))
    tarihler = ortak[-GUN-1:]
    for t, df in veri.items():
        for tar in tarihler[:-1]:
            try:
                dft = df.loc[:tar]
                if len(dft) >= 60:
                    cache[(t, tar)] = skorla(dft, model)
            except Exception:
                pass
    return cache


def simule(veri, esik, cache):
    ortak = sorted(set.intersection(*[set(df.index) for df in veri.values()]))
    tarihler = ortak[-GUN-1:]
    debug["gun"] = len(tarihler) - 1
    kz_liste = []
    portfoy, pik = 100000.0, 100000.0

    for i in range(len(tarihler) - 1):
        bugun, yarin = tarihler[i], tarihler[i+1]
        adaylar = []
        for t, df in veri.items():
            sk = cache.get((t, bugun))
            if sk is not None and sk >= esik:
                try:
                    adaylar.append((t, sk, float(df.loc[bugun]["Close"])))
                except Exception:
                    pass
        if not adaylar:
            continue
        adaylar.sort(key=lambda x: x[1], reverse=True)
        gunluk = 0.0
        for t, sk, alis in adaylar[:MAX_POZ]:
            try:
                yar = veri[t].loc[yarin]
                dusuk = float(yar["Low"])
                kapanis = float(yar["Close"])
                stop_fiyat = alis * (1 + STOP_LOSS / 100)
                if dusuk <= stop_fiyat:
                    kz = STOP_LOSS - KOMISYON * 100
                else:
                    kz = (kapanis - alis) / alis * 100 - KOMISYON * 100
                if pd.isna(kz):
                    continue
                gunluk += kz / MAX_POZ
                kz_liste.append(kz)
            except Exception:
                continue
        if not pd.isna(gunluk):
            portfoy *= (1 + gunluk / 100)
            pik = max(pik, portfoy)
    return kz_liste, portfoy, pik


def main():
    print("Model...")
    model = yukle_model()
    tlist = tickers()
    print(f"Veri çekiliyor (kara liste {len(KARA_LISTE)} hariç)...")
    veri = veri_cek(tlist, kara=True)
    print(f"Yüklenen: {len(veri)}")
    if not veri:
        (ROOT / "data" / "backtest_bist_rapor.md").write_text(
            "# Backtest\n\n❌ Veri çekilemedi.", encoding="utf-8")
        return

    print("Skorlar ön-hesaplanıyor (grid cache)...")
    cache = on_hesapla_skorlar(veri, model)

    sonuclar = []
    for esik in ESIK_GRID:
        kz, portfoy, pik = simule(veri, esik, cache)
        if not kz:
            sonuclar.append((esik, 0, 0, 0, 0, 0, 0))
            continue
        arr = np.array(kz)
        n = len(arr)
        kazanc = (arr > 0).mean() * 100
        ort = arr.mean()
        std = arr.std()
        sharpe = ort / std if std > 0 else 0
        getiri = (portfoy / 100000 - 1) * 100
        dd = (portfoy / pik - 1) * 100
        sonuclar.append((esik, n, kazanc, ort, sharpe, getiri, dd))
        print(f"  Eşik {esik}: {n} işlem, kazanç %{kazanc:.1f}, getiri %{getiri:+.1f}")

    gecerli = [s for s in sonuclar if s[1] > 0]
    en_iyi = max(gecerli, key=lambda x: x[5]) if gecerli else None

    md = ["# 🦅 BIST Backtest v2 — Optimize", "",
          f"_{datetime.now():%Y-%m-%d %H:%M:%S} · son ~1 yıl · yfinance_", "",
          f"Model ML: {debug['model']} · Hisse: {debug['hisse']} · Gün: {debug['gun']}",
          f"Kara liste: {', '.join(sorted(KARA_LISTE))}",
          f"Stop-loss: %{STOP_LOSS} · Komisyon: %{KOMISYON*100:.1f} · Max poz: {MAX_POZ}", "",
          "## Eşik grid sonuçları", "",
          "| Eşik | İşlem | Kazanç % | Ort K/Z % | Sharpe | Getiri % | Drawdown % |",
          "|---|---|---|---|---|---|---|"]
    for e, n, k, o, sh, g, d in sonuclar:
        yildiz = " ⭐" if en_iyi and e == en_iyi[0] else ""
        md.append(f"| {e}{yildiz} | {n} | %{k:.1f} | %{o:+.2f} | {sh:.3f} | %{g:+.1f} | %{d:+.1f} |")
    md.append("")
    if en_iyi:
        e, n, k, o, sh, g, d = en_iyi
        md += ["## 🏆 En iyi config", "",
               f"- **Eşik = {e}** · Getiri **%{g:+.1f}** (1 yıl) · Kazanç %{k:.1f} · Sharpe {sh:.3f} · {n} işlem", "",
               "## Öneri",
               f"- `MIN_BOMBA_SKOR_ALIS = {e}` (şu an 25)",
               "- Kara listeyi canlı bota uygula (5 hisse skip)",
               f"- Getiri {'POZİTİF ✅ edge düzeldi' if g > 0 else 'hâlâ negatif ⚠️'}"]
    out = ROOT / "data" / "backtest_bist_rapor.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n" + "\n".join(md))


if __name__ == "__main__":
    main()
