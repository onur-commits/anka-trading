"""
ANKA SCALPER — Gün İçi Oynaklık Avcısı
========================================
30 dakikada bir çalışır, gün içi fırsatları bulur.
Bomba sistemiyle birlikte çalışır — ayrı liste yazar.

Stratejiler:
  1. Gap Play — sabah açılış gap'i
  2. Volume Spike — anlık hacim patlaması
  3. VWAP Bounce — VWAP'tan dönüş
  4. Range Breakout — ilk saat aralığını kırma
  5. Mean Reversion — aşırı düşenden dönüş
"""

import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
import sys
import subprocess
import platform
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

BIST50 = [
    "GARAN","THYAO","ASELS","TUPRS","EREGL","SISE","TOASO","AKBNK","YKBNK","HALKB",
    "SAHOL","KCHOL","TCELL","BIMAS","PGSUS","TAVHL","FROTO","ARCLK","PETKM","ENKAI",
    "TKFEN","EKGYO","TTKOM","VAKBN","MGROS","DOHOL","GUBRF","ISCTR","AKSEN","AYEN",
    "KONTR","SASA","GESAN","OTKAR","ENJSA","TSKB","SMRTG","CCOLA","CIMSA","KORDS",
    "VESTL","ALARK","HEKTS","ULKER","ASTOR","TTRAK","EGEEN","CEMTS","BRISA"
]


def vwap_hesapla(df):
    """VWAP hesapla — gün içi veride."""
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (tp * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap


def gap_play(ticker, df_daily):
    """
    GAP PLAY: Sabah %1.5+ gap açanlar.
    Gap up + hacimli = momentum devam eder.
    Gap down + düşük hacim = geri dönüş potansiyeli.
    """
    if len(df_daily) < 3:
        return 0, ""

    c = df_daily['Close'].squeeze()
    o = df_daily['Open'].squeeze()

    dun_kapanis = float(c.iloc[-2])
    bugun_acilis = float(o.iloc[-1])
    bugun_son = float(c.iloc[-1])
    gap_pct = (bugun_acilis / dun_kapanis - 1) * 100

    puan = 0
    detay = ""

    if gap_pct > 1.5:
        # Gap up — momentum takip
        if bugun_son > bugun_acilis:  # Gap sonrası yukarı devam
            puan = 80
            detay = f"GAP UP +%{gap_pct:.1f} devam✅"
        else:
            puan = 30
            detay = f"GAP UP +%{gap_pct:.1f} doldu"
    elif gap_pct < -1.5:
        # Gap down — mean reversion potansiyeli
        if bugun_son > bugun_acilis:  # Dönüyor
            puan = 70
            detay = f"GAP DOWN %{gap_pct:.1f} DÖNÜŞ✅"
        else:
            puan = 10
            detay = f"GAP DOWN %{gap_pct:.1f} devam❌"

    return puan, detay


def volume_spike(ticker, df_intraday):
    """
    VOLUME SPIKE: Son 30dk'lık hacim, aynı saatteki ortalamanın 2x üstü.
    Birisi büyük alım yapıyor demek.
    """
    if len(df_intraday) < 20:
        return 0, ""

    v = df_intraday['Volume'].squeeze()
    c = df_intraday['Close'].squeeze()

    # Son barın saati
    saat = df_intraday.index[-1].hour
    ayni_saat = df_intraday[df_intraday.index.hour == saat]

    if len(ayni_saat) < 2:
        ort = float(v.iloc[-20:].mean())
    else:
        ort = float(ayni_saat['Volume'].iloc[:-1].mean())

    son = float(v.iloc[-1])
    oran = son / ort if ort > 0 else 0

    # Fiyat yönü (hacim + yukarı = pozitif)
    fiyat_degisim = float((c.iloc[-1] / c.iloc[-2] - 1) * 100) if len(c) >= 2 else 0

    puan = 0
    detay = ""

    if oran >= 3.0 and fiyat_degisim > 0:
        puan = 90
        detay = f"HACİM x{oran:.1f} + yukarı🔥"
    elif oran >= 2.0 and fiyat_degisim > 0:
        puan = 70
        detay = f"HACİM x{oran:.1f} + yukarı✅"
    elif oran >= 2.0 and fiyat_degisim < 0:
        puan = 40
        detay = f"HACİM x{oran:.1f} ama aşağı⚠️"
    elif oran >= 1.5:
        puan = 30
        detay = f"HACİM x{oran:.1f}"

    return puan, detay


def vwap_bounce(ticker, df_intraday):
    """
    VWAP BOUNCE: Fiyat VWAP'a düşüp dönüyor mu?
    VWAP üstünde ve yükselen = güçlü.
    VWAP'a dokunup geri sıçrama = alım fırsatı.
    """
    if len(df_intraday) < 10:
        return 0, ""

    c = df_intraday['Close'].squeeze()
    vwap = vwap_hesapla(df_intraday)

    son = float(c.iloc[-1])
    son_vwap = float(vwap.iloc[-1])
    onceki = float(c.iloc[-2])
    onceki_vwap = float(vwap.iloc[-2])

    puan = 0
    detay = ""

    # VWAP'a dokunup geri sıçrama
    if onceki <= onceki_vwap and son > son_vwap:
        puan = 80
        detay = f"VWAP BOUNCE✅ (VWAP:{son_vwap:.2f})"
    # VWAP üstünde ve yükseliyor
    elif son > son_vwap and son > onceki:
        puan = 60
        detay = f"VWAP üstü✅"
    # VWAP altında
    elif son < son_vwap:
        puan = 20
        detay = f"VWAP altı❌"

    return puan, detay


def range_breakout(ticker, df_intraday):
    """
    RANGE BREAKOUT: İlk 1 saatteki high kırıldı mı?
    İlk saat aralığı → support/resistance.
    Kırılma + hacim = güçlü hareket.
    """
    if len(df_intraday) < 10:
        return 0, ""

    # İlk 2 bar (30dk × 2 = 1 saat) — açılış aralığı
    h = df_intraday['High'].squeeze()
    l = df_intraday['Low'].squeeze()
    c = df_intraday['Close'].squeeze()

    # Bugünün verisi
    bugun = df_intraday[df_intraday.index.date == df_intraday.index.date[-1]]
    if len(bugun) < 3:
        return 0, ""

    ilk_saat_high = float(bugun['High'].iloc[:2].max())
    ilk_saat_low = float(bugun['Low'].iloc[:2].min())
    son = float(bugun['Close'].iloc[-1])

    puan = 0
    detay = ""

    if son > ilk_saat_high:
        puan = 75
        detay = f"BREAKOUT UP✅ ({ilk_saat_high:.2f} kırıldı)"
    elif son < ilk_saat_low:
        puan = 20  # Aşağı kırılma — short yapamıyoruz ama dikkat
        detay = f"BREAKDOWN❌ ({ilk_saat_low:.2f} altı)"
    else:
        aralik = ilk_saat_high - ilk_saat_low
        puan = 40
        detay = f"Aralık içi ({aralik:.2f} TL)"

    return puan, detay


def mean_reversion(ticker, df_daily, df_intraday):
    """
    MEAN REVERSION: Çok düşenler geri döner.
    Son 3 günde -%5+ düşüp bugün toparlanma başlayan.
    """
    if len(df_daily) < 5 or len(df_intraday) < 5:
        return 0, ""

    c_daily = df_daily['Close'].squeeze()
    c_intra = df_intraday['Close'].squeeze()

    # Son 3 günlük düşüş
    uc_gun = float((c_daily.iloc[-1] / c_daily.iloc[-4] - 1) * 100)

    # Bugünkü gün içi dönüş
    bugun = df_intraday[df_intraday.index.date == df_intraday.index.date[-1]]
    if len(bugun) < 2:
        return 0, ""

    bugun_dip = float(bugun['Low'].min())
    bugun_son = float(bugun['Close'].iloc[-1])
    donus = (bugun_son / bugun_dip - 1) * 100 if bugun_dip > 0 else 0

    puan = 0
    detay = ""

    if uc_gun < -5 and donus > 1.5:
        puan = 85
        detay = f"3G:{uc_gun:.1f}% DÖNÜŞ +%{donus:.1f}✅"
    elif uc_gun < -3 and donus > 1.0:
        puan = 65
        detay = f"3G:{uc_gun:.1f}% dönüş +%{donus:.1f}"
    elif uc_gun < -5:
        puan = 40
        detay = f"3G:{uc_gun:.1f}% henüz dönmedi"

    return puan, detay


# ================================================================
# SCALPER ANA TARAMA
# ================================================================
def scalp_tara(symbol_list=None):
    """Gün içi fırsatları tara."""
    if symbol_list is None:
        symbol_list = BIST50

    saat = datetime.now().hour
    print(f"\n⚡ ANKA SCALPER — Saat {saat:02d}:{datetime.now().minute:02d}")
    print("=" * 70)

    firsatlar = []

    for s in symbol_list:
        try:
            # Gün içi veri
            df_intra = yf.download(f"{s}.IS", period="5d", interval="30m", progress=False)
            df_daily = yf.download(f"{s}.IS", period="1mo", progress=False)

            if df_intra.empty or df_daily.empty:
                continue

            # 5 strateji puanla
            gap_p, gap_d = gap_play(s, df_daily)
            vol_p, vol_d = volume_spike(s, df_intra)
            vwap_p, vwap_d = vwap_bounce(s, df_intra)
            range_p, range_d = range_breakout(s, df_intra)
            mean_p, mean_d = mean_reversion(s, df_daily, df_intra)

            # En yüksek strateji puanı
            stratejiler = [
                ("GAP", gap_p, gap_d),
                ("VOL", vol_p, vol_d),
                ("VWAP", vwap_p, vwap_d),
                ("RANGE", range_p, range_d),
                ("MEAN", mean_p, mean_d),
            ]

            en_iyi = max(stratejiler, key=lambda x: x[1])
            ort_puan = np.mean([p for _, p, _ in stratejiler])

            # En az 1 strateji 60+ puan vermeli
            yuksek_sayisi = sum(1 for _, p, _ in stratejiler if p >= 60)

            firsatlar.append({
                "ticker": s,
                "en_iyi_strateji": en_iyi[0],
                "en_iyi_puan": en_iyi[1],
                "en_iyi_detay": en_iyi[2],
                "ort_puan": round(ort_puan, 1),
                "yuksek": yuksek_sayisi,
                "tum_puanlar": {ad: p for ad, p, _ in stratejiler},
            })

        except:
            continue

    # Sırala
    firsatlar.sort(key=lambda x: x["en_iyi_puan"], reverse=True)

    # Göster
    scalp_listesi = []
    for f in firsatlar[:15]:
        emoji = "⚡" if f["en_iyi_puan"] >= 70 else "🟡" if f["en_iyi_puan"] >= 50 else "⚪"
        puanlar = " ".join(f"{k}:{v}" for k, v in f["tum_puanlar"].items())
        print(f"  {emoji} {f['ticker']:6} | Best:{f['en_iyi_strateji']}({f['en_iyi_puan']}) | {f['en_iyi_detay']}")

        if f["en_iyi_puan"] >= 70:
            scalp_listesi.append(f["ticker"])

    print(f"\n⚡ SCALP FIRSATLARI: {','.join(scalp_listesi) if scalp_listesi else 'YOK'}")

    # Bridge'e yaz (robot okur)
    if scalp_listesi:
        bridge_data = {
            "scalp_targets": scalp_listesi,
            "scan_time": datetime.now().isoformat(),
        }
        bridge_path = PROJECT_DIR / "data" / "scalp_targets.json"
        with open(bridge_path, "w") as f_out:
            json.dump(bridge_data, f_out, indent=2)

    return firsatlar


if __name__ == "__main__":
    firsatlar = scalp_tara()
