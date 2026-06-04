"""
Walk-Forward Doğrulama (Gün/Adım 6) — overfit kontrolü
=======================================================
In-sample backtest (+%19.6) overfit olabilir. Walk-forward: veriyi
ardışık pencerelere böl, HER pencerede "geçmişe bakıp" parametre seç,
SONRAKİ (görülmemiş) pencerede test et. Out-of-sample getiri gerçeği verir.

Yöntem (basit, lookahead'siz):
- 252 günü 4 çeyreğe böl (her ~63 gün).
- Çeyrek N'de en iyi eşiği bul (in-sample), Çeyrek N+1'de uygula (OOS).
- OOS getirilerini birleştir = gerçek beklenen performans.

Komisyon %0.1 (gerçek), kara liste + stop-loss aynı.
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
KOMISYON = 0.001
STOP_LOSS = -3.0
KARA_LISTE = {"SASA.IS", "VESTL.IS", "GUBRF.IS", "EGEEN.IS", "ENKAI.IS"}
ESIK_GRID = [15, 20, 25, 30, 35, 40]
CEYREK = 4  # walk-forward pencere sayısı


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


def yukle_model():
    try:
        from tahmin_motoru_v2 import EnsembleModelV2
        return EnsembleModelV2.yukle()
    except Exception:
        return None


def tickers():
    try:
        from gunluk_bomba import TICKERS
        return [t for t in TICKERS if t not in KARA_LISTE]
    except Exception:
        return ["THYAO.IS", "GARAN.IS", "AKBNK.IS", "ISCTR.IS", "TUPRS.IS",
                "EREGL.IS", "ASELS.IS", "TOASO.IS", "HEKTS.IS", "HALKB.IS",
                "AKSEN.IS", "KONTR.IS", "TKFEN.IS", "AYEN.IS", "OTKAR.IS"]


def veri_cek(tlist):
    veri = {}
    for t in tlist:
        try:
            df = yf.download(t, period="2y", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) >= 300:
                veri[t] = df
        except Exception:
            pass
    return veri


def pencere_kz(veri, cache, tarihler, esik):
    """Belirli tarih aralığında, verilen eşikle işlemleri çalıştır → kz listesi."""
    kz = []
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
        adaylar.sort(key=lambda x: x[1], reverse=True)
        for t, sk, alis in adaylar[:MAX_POZ]:
            try:
                yar = veri[t].loc[yarin]
                dusuk, kapanis = float(yar["Low"]), float(yar["Close"])
                stop = alis * (1 + STOP_LOSS / 100)
                k = (STOP_LOSS if dusuk <= stop else (kapanis - alis) / alis * 100) - KOMISYON * 100
                if not pd.isna(k):
                    kz.append(k)
            except Exception:
                pass
    return kz


def main():
    print("Model + veri...")
    model = yukle_model()
    veri = veri_cek(tickers())
    print(f"Hisse: {len(veri)}")
    if len(veri) < 5:
        (ROOT / "data" / "walkforward_rapor.md").write_text(
            "# Walk-Forward\n\n❌ Yetersiz veri.", encoding="utf-8")
        return

    ortak = sorted(set.intersection(*[set(df.index) for df in veri.values()]))
    tarihler = ortak[-253:]
    print("Skor cache...")
    cache = {}
    for t, df in veri.items():
        for tar in tarihler[:-1]:
            try:
                dft = df.loc[:tar]
                if len(dft) >= 60:
                    cache[(t, tar)] = skorla(dft, model)
            except Exception:
                pass

    # 4 çeyreğe böl
    n = len(tarihler)
    ceyrek_boy = n // CEYREK
    oos_kz = []
    detay = []
    for q in range(CEYREK - 1):
        train = tarihler[q*ceyrek_boy:(q+1)*ceyrek_boy+1]
        test = tarihler[(q+1)*ceyrek_boy:(q+2)*ceyrek_boy+1]
        # In-sample: en iyi eşik (ortalama kz'ye göre)
        en_iyi_esik, en_iyi_ort = ESIK_GRID[0], -999
        for e in ESIK_GRID:
            kz = pencere_kz(veri, cache, train, e)
            if kz and np.mean(kz) > en_iyi_ort:
                en_iyi_ort, en_iyi_esik = np.mean(kz), e
        # OOS: seçilen eşiği test penceresinde uygula
        test_kz = pencere_kz(veri, cache, test, en_iyi_esik)
        oos_kz += test_kz
        oos_ort = np.mean(test_kz) if test_kz else 0
        detay.append((q+1, en_iyi_esik, en_iyi_ort, len(test_kz), oos_ort))
        print(f"  Çeyrek {q+1}: train en iyi eşik={en_iyi_esik} (ort {en_iyi_ort:+.2f}) "
              f"→ OOS {len(test_kz)} işlem, ort {oos_ort:+.2f}")

    arr = np.array(oos_kz) if oos_kz else np.array([0])
    # OOS bileşik getiri (eşit ağırlık, MAX_POZ böl)
    portfoy = 100000.0
    # günlük yerine işlem-bazlı kabaca: her işlem 1/MAX_POZ ağırlık
    for k in oos_kz:
        portfoy *= (1 + (k / MAX_POZ) / 100)
    getiri = (portfoy / 100000 - 1) * 100

    md = ["# 🦅 Walk-Forward Doğrulama (out-of-sample)", "",
          f"_{datetime.now():%Y-%m-%d %H:%M} · komisyon %0.1 · kara liste · stop %{STOP_LOSS}_", "",
          "## Çeyrek çeyrek (train→OOS)", "",
          "| Çeyrek | Train en iyi eşik | Train ort | OOS işlem | OOS ort K/Z |",
          "|---|---|---|---|---|"]
    for q, e, tr, no, oo in detay:
        md.append(f"| {q} | {e} | %{tr:+.2f} | {no} | %{oo:+.2f} |")
    md += ["",
           "## 🎯 OOS (gerçek beklenen) sonuç", "",
           f"- OOS işlem: {len(oos_kz)}",
           f"- OOS kazanç oranı: %{(arr>0).mean()*100:.1f}",
           f"- OOS ortalama K/Z: %{arr.mean():+.3f}",
           f"- OOS bileşik getiri: **%{getiri:+.1f}**", "",
           "## Yorum",
           ("✅ OOS POZİTİF — edge overfit değil, dayanıklı." if getiri > 0
            else "⚠️ OOS NEGATİF — in-sample +%19.6 OVERFIT'ti. Canlıda dikkat."),
           "",
           "_OOS = görülmemiş veride. In-sample'dan düşük olması NORMAL ve dürüst."]
    (ROOT / "data" / "walkforward_rapor.md").write_text("\n".join(md), encoding="utf-8")
    print("\n" + "\n".join(md))


if __name__ == "__main__":
    main()
