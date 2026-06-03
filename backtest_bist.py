"""
BIST Backtest Harness — son ~1 yıl
====================================
İki versiyon: (1) ML ile bomba_skor, (2) ML yoksa teknik fallback
(hacim+momentum+RSI). Sebep şeffaf görünür.
"""
import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

MIN_SKOR = 25
MAX_POZ = 3
GUN = 252
KOMISYON = 0.002

debug = {"hisse_yuklendi": 0, "model_ok": False, "gun_isleyen": 0,
         "skor_toplam": 0, "aday_toplam": 0}


def rsi(serisi, n=14):
    delta = serisi.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = -delta.clip(upper=0).rolling(n).mean()
    rs = up / down
    return 100 - 100 / (1 + rs)


def basit_skor(df):
    """ML olmadan: hacim_oran + RSI + momentum + günlük değişim."""
    close = df["Close"]
    vol = df["Volume"]
    son = close.iloc[-1]
    onceki = close.iloc[-2]
    gun5 = close.iloc[-5] if len(close) > 5 else onceki

    deg_gunluk = float((son / onceki - 1) * 100)
    mom5 = float((son / gun5 - 1) * 100)
    rsi_son = float(rsi(close).iloc[-1])
    ort_vol = float(vol.rolling(20).mean().iloc[-1]) if len(vol) > 20 else 1
    son_vol = float(vol.iloc[-1])
    hacim_oran = son_vol / ort_vol if ort_vol > 0 else 1

    skor = 0
    if deg_gunluk > 1: skor += 15
    if deg_gunluk > 3: skor += 10
    if mom5 > 0: skor += 10
    if mom5 > 5: skor += 10
    if 40 < rsi_son < 70: skor += 15
    if hacim_oran > 1.5: skor += 20
    if hacim_oran > 3: skor += 10
    return float(skor)


def yukle_model_opsiyonel():
    try:
        from tahmin_motoru_v2 import EnsembleModelV2  # noqa
        m = EnsembleModelV2.yukle()
        if m:
            debug["model_ok"] = True
            return m
    except Exception as e:
        print(f"Model yüklenemedi (basit skora geçilecek): {e}")
    return None


def gelismis_skor(df, model):
    """Model varsa tahmin_motoru üzerinden, yoksa basit_skor."""
    try:
        from tahmin_motoru_v2 import feature_olustur_v2, hisse_analiz_v2
        from gunluk_bomba import bomba_skor_hesapla
        analiz = hisse_analiz_v2("X", df, model, rejim=None)
        features = feature_olustur_v2(df)
        if analiz is None or features is None:
            return basit_skor(df)
        son = features.iloc[-1].to_dict()
        skor, _ = bomba_skor_hesapla(analiz, son)
        return float(skor)
    except Exception:
        return basit_skor(df)


def tickers():
    try:
        from gunluk_bomba import TICKERS
        return list(TICKERS)
    except Exception:
        # Fallback: BIST 30 + sık çalışan hisseler
        return ["THYAO.IS", "GARAN.IS", "AKBNK.IS", "ISCTR.IS", "TUPRS.IS",
                "EREGL.IS", "ASELS.IS", "BIMAS.IS", "TCELL.IS", "PETKM.IS",
                "SISE.IS", "TOASO.IS", "FROTO.IS", "HEKTS.IS", "KCHOL.IS",
                "SAHOL.IS", "VAKBN.IS", "HALKB.IS", "AEFES.IS", "PGSUS.IS",
                "AKSEN.IS", "ENJSA.IS", "ENKAI.IS", "SOKM.IS", "TKFEN.IS",
                "MGROS.IS", "DOAS.IS", "AYEN.IS", "ALARK.IS", "TSKB.IS"]


def veri_cek_hepsi(tlist):
    veri = {}
    for t in tlist:
        try:
            df = yf.download(t, period="2y", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) >= 200:
                veri[t] = df
        except Exception:
            pass
    debug["hisse_yuklendi"] = len(veri)
    return veri


def simule(veri, model):
    ortak = sorted(set.intersection(*[set(df.index) for df in veri.values()]))
    tarihler = ortak[-GUN-1:]
    debug["gun_isleyen"] = len(tarihler) - 1

    islemler = []
    portfoy = 100000.0
    pik = portfoy

    for i in range(len(tarihler) - 1):
        bugun, yarin = tarihler[i], tarihler[i+1]
        adaylar = []
        for t, df in veri.items():
            try:
                dft = df.loc[:bugun]
                if len(dft) < 60:
                    continue
                skor = gelismis_skor(dft, model)
                debug["skor_toplam"] += 1
                if skor >= MIN_SKOR:
                    debug["aday_toplam"] += 1
                    adaylar.append((t, skor, float(dft["Close"].iloc[-1])))
            except Exception:
                continue
        if not adaylar:
            continue
        adaylar.sort(key=lambda x: x[1], reverse=True)
        secilen = adaylar[:MAX_POZ]
        gunluk = 0
        for t, skor, alis in secilen:
            try:
                satis = float(veri[t].loc[yarin]["Close"])
                kz = (satis - alis) / alis * 100 - KOMISYON * 100
                gunluk += kz / MAX_POZ
                islemler.append({"tarih": str(bugun)[:10], "ticker": t,
                                 "skor": round(skor, 1), "alis": round(alis, 2),
                                 "satis": round(satis, 2), "kz_pct": round(kz, 2)})
            except Exception:
                continue
        portfoy *= (1 + gunluk / 100)
        pik = max(pik, portfoy)
    return islemler, portfoy, pik


def rapor(islemler, portfoy, pik):
    md = ["# 🦅 BIST Backtest Raporu", "",
          f"_{datetime.now():%Y-%m-%d %H:%M:%S} · son ~1 yıl · yfinance_", ""]
    md.append("## Debug bilgisi")
    md.append("```")
    md.append(f"Veri yüklenen hisse: {debug['hisse_yuklendi']}")
    md.append(f"Model yüklendi (ML): {debug['model_ok']}")
    md.append(f"İşlenen gün: {debug['gun_isleyen']}")
    md.append(f"Skor hesaplaması: {debug['skor_toplam']}")
    md.append(f"Eşik geçen aday: {debug['aday_toplam']}")
    md.append("```")
    md.append("")
    if not islemler:
        md.append("## ❌ Sonuç: 0 işlem")
        md.append("Olası sebepler: veri yüklenemedi, ya da skor eşiğin altında kaldı.")
        return "\n".join(md)
    df = pd.DataFrame(islemler)
    n = len(df)
    kazanc = (df["kz_pct"] > 0).mean() * 100
    ort = df["kz_pct"].mean()
    medyan = df["kz_pct"].median()
    std = df["kz_pct"].std()
    sharpe = ort / std if std > 0 else 0
    getiri = (portfoy / 100000 - 1) * 100
    dd = (portfoy / pik - 1) * 100
    md += [
        "## Özet", "",
        f"| | |", f"|---|---|",
        f"| Toplam işlem | {n} |",
        f"| Kazanç oranı | %{kazanc:.1f} |",
        f"| Ortalama K/Z | %{ort:+.2f} |",
        f"| Medyan K/Z | %{medyan:+.2f} |",
        f"| Std | {std:.2f} |",
        f"| Sharpe-benzeri | {sharpe:.2f} |",
        f"| **Portföy getirisi** | **%{getiri:+.1f}** |",
        f"| Drawdown (son) | %{dd:+.1f} |", "",
        "## Kural",
        f"- Skor eşiği: {MIN_SKOR}",
        f"- Max pozisyon: {MAX_POZ}",
        f"- Komisyon: %{KOMISYON*100:.1f}",
        f"- ML model: {'KULLANILDI' if debug['model_ok'] else 'YOK — basit teknik skora düşüldü'}",
        "",
    ]
    g = df.groupby("ticker")["kz_pct"].agg(["count", "mean", "sum"]).round(2)
    g.columns = ["İşlem", "Ort %", "Toplam %"]
    g = g.sort_values("Toplam %", ascending=False)
    md.append("## En iyi 10")
    md.append("```")
    md.append(g.head(10).to_string())
    md.append("```\n")
    md.append("## En kötü 5")
    md.append("```")
    md.append(g.tail(5).to_string())
    md.append("```")
    return "\n".join(md)


if __name__ == "__main__":
    print("Model yükleniyor (opsiyonel)...")
    model = yukle_model_opsiyonel()
    print(f"Model: {'OK' if model else 'YOK — basit teknik skora düşüyor'}")

    tlist = tickers()
    print(f"Hisse listesi: {len(tlist)} ticker")
    print("Veri çekiliyor...")
    veri = veri_cek_hepsi(tlist)
    print(f"Yüklenen: {len(veri)} hisse")

    if not veri:
        out_text = "# BIST Backtest\n\n❌ HİÇ HİSSE VERİSİ ÇEKİLEMEDİ (yfinance sorunu olabilir)."
    else:
        print("Simülasyon başlıyor...")
        islemler, portfoy, pik = simule(veri, model)
        print(f"İşlem: {len(islemler)}, portföy: %{(portfoy/100000-1)*100:+.1f}")
        out_text = rapor(islemler, portfoy, pik)

    (ROOT / "data" / "backtest_bist_rapor.md").write_text(out_text, encoding="utf-8")
    print("\n--- RAPOR ---")
    print(out_text[:2000])
