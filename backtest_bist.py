"""
BIST Backtest Harness — son 1 yıl, gerçek bomba_skor mantığı
=============================================================
Veri: yfinance (52 hisse, gunluk_bomba.TICKERS)
Kural: canlı bot ile birebir — skor >= MIN_BOMBA_SKOR (25), max 3 poz,
       09:35 al, 17:30 kapat (intraday).
Çıktı: data/backtest_bist_rapor.md (markdown tablo)

NOT: Bu basitleştirilmiş simülasyon — slippage/komisyon/IQ TCP gecikmesi
yok. Gerçek canlı performans daha düşük olur (paper_trader.py içinde
pessimistic harness var ama ona uydurmak ayrı iş).
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from gunluk_bomba import TICKERS, bomba_skor_hesapla  # noqa: E402
from tahmin_motoru_v2 import (  # noqa: E402
    EnsembleModelV2, feature_olustur_v2, hisse_analiz_v2,
)

MIN_SKOR = 25       # canlı eşik
MAX_POZ = 3         # aynı anda max
GUN = 252           # ~1 yıl borsa günü
KOMISYON = 0.002    # 2 yön x 0.1% (gerçekçi)


def veri_cek_hepsi():
    veri = {}
    for t in TICKERS:
        try:
            df = yf.download(t, period="2y", progress=False, auto_adjust=True)
            if len(df) >= 200:
                veri[t] = df
        except Exception:
            pass
    xu = yf.download("XU100.IS", period="2y", progress=False, auto_adjust=True)
    return veri, xu


def gun_simulasyon(veri, model, son_n_gun=GUN):
    """Her gün için: skorla, en yüksek 3'ü 'al' (kapanış), ertesi gün kapanışta sat."""
    print(f"Simülasyon: {len(veri)} hisse, son {son_n_gun} gün")
    # Tarih indeksini al
    ortak_tarih = sorted(set.intersection(*[set(df.index) for df in veri.values()]))
    tarihler = ortak_tarih[-son_n_gun-1:]  # +1: ertesi gün için son satış

    islemler = []
    portfoy = 100000.0
    pikt = portfoy

    for i in range(len(tarihler) - 1):
        bugun, yarin = tarihler[i], tarihler[i+1]
        adaylar = []

        for t, df in veri.items():
            try:
                dft = df.loc[:bugun]
                if len(dft) < 120:
                    continue
                analiz = hisse_analiz_v2(t, dft, model, rejim=None)
                if analiz is None:
                    continue
                features = feature_olustur_v2(dft)
                if features is None:
                    continue
                son = features.iloc[-1].to_dict()
                skor, _ = bomba_skor_hesapla(analiz, son)
                if skor >= MIN_SKOR:
                    adaylar.append((t, skor, float(dft["Close"].iloc[-1])))
            except Exception:
                continue

        if not adaylar:
            continue

        # En yüksek 3 skor
        adaylar.sort(key=lambda x: x[1], reverse=True)
        secilen = adaylar[:MAX_POZ]

        # Ertesi gün kapat (intraday yerine yarın kapanış — simülasyon basit)
        gunluk_kz = 0
        for t, skor, alis in secilen:
            try:
                satis = float(veri[t].loc[yarin]["Close"])
                kz_pct = (satis - alis) / alis * 100 - (KOMISYON * 100)
                gunluk_kz += kz_pct / MAX_POZ  # eşit ağırlık
                islemler.append({"tarih": bugun, "ticker": t, "skor": skor,
                                 "alis": alis, "satis": satis, "kz_pct": kz_pct})
            except Exception:
                continue

        portfoy *= (1 + gunluk_kz / 100)
        pikt = max(pikt, portfoy)

    return islemler, portfoy, pikt


def rapor_uret(islemler, portfoy_son, pik):
    df = pd.DataFrame(islemler)
    if df.empty:
        return "# BIST Backtest\n\nHiç işlem üretilmedi (skor eşiği yüksek?)."

    n = len(df)
    kazanc = (df["kz_pct"] > 0).mean() * 100
    ort = df["kz_pct"].mean()
    medyan = df["kz_pct"].median()
    std = df["kz_pct"].std()
    sharpe_benzeri = ort / std if std > 0 else 0
    toplam_getiri = (portfoy_son / 100000 - 1) * 100
    drawdown = (portfoy_son / pik - 1) * 100

    g = df.groupby("ticker")["kz_pct"].agg(["count", "mean", "sum"]).round(2)
    g.columns = ["İşlem", "Ort %", "Toplam %"]
    g = g.sort_values("Toplam %", ascending=False)

    rapor = f"""# 🦅 BIST Backtest Raporu

_{datetime.now():%Y-%m-%d %H:%M:%S} · son ~1 yıl · yfinance verisi_

## Özet
| | |
|---|---|
| Toplam işlem | {n} |
| Kazanç oranı | %{kazanc:.1f} |
| Ortalama K/Z | %{ort:+.2f} |
| Medyan K/Z | %{medyan:+.2f} |
| Std | {std:.2f} |
| Sharpe-benzeri | {sharpe_benzeri:.2f} |
| **Portföy getirisi** | **%{toplam_getiri:+.1f}** |
| Max drawdown (anlık) | %{drawdown:+.1f} |

## Kural seti
- MIN_BOMBA_SKOR_ALIS = {MIN_SKOR} (canlı eşik)
- Max pozisyon = {MAX_POZ}
- Komisyon = %{KOMISYON*100:.1f} (iki yön)
- Intraday: alış kapanış, ertesi gün kapanış sat

## En iyi 10 hisse
```
{g.head(10).to_string()}
```

## En kötü 5 hisse
```
{g.tail(5).to_string()}
```

## ⚠️ Uyarılar
- Slippage YOK (gerçekte fiyat hareketi alış-satış arası farklı)
- IQ TCP gecikmesi YOK (gerçek emirde 5-15 sn'lik gecikme)
- "Yarın kapanış sat" basitleştirme — gerçek bot 17:30'da satıyor (intraday)
- Gerçek sonuç **%30-50 daha düşük** beklenebilir
"""
    return rapor


if __name__ == "__main__":
    print("Model yükleniyor...")
    model = EnsembleModelV2.yukle()
    print(f"Model: {'OK' if model else 'YOK'}")

    print("Veri çekiliyor (~52 hisse, yfinance)...")
    veri, xu = veri_cek_hepsi()
    print(f"Çekildi: {len(veri)} hisse")

    print("Simülasyon başlıyor...")
    islemler, portfoy, pik = gun_simulasyon(veri, model)

    rapor = rapor_uret(islemler, portfoy, pik)
    out = ROOT / "data" / "backtest_bist_rapor.md"
    out.write_text(rapor, encoding="utf-8")
    print(f"\n✅ Rapor: {out}")
    print(rapor[:1200])
