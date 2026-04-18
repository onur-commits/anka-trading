"""
ANKA Faz 2B — Feedback Loop (Ogrenme Dongusu)
===============================================
Her tahmin kaydedilir, gercek sonucla karsilastirilir.
Model ne zaman dogru, ne zaman yanlis — otomatik analiz.

Akis:
  1. tahmin_kaydet() — model tahmin yaptiginda cagrilir
  2. sonuc_guncelle() — 5 gun sonra gercek sonuc kontrol edilir
  3. performans_raporu() — model nerede basarili, nerede basarisiz
  4. iyilestirme_onerileri() — otomatik iyilestirme onerileri

Veriler: data/feedback_log.json
"""

import json
import numpy as np
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
FEEDBACK_PATH = DATA_DIR / "feedback_log.json"


def _log_yukle() -> list:
    if FEEDBACK_PATH.exists():
        try:
            return json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
        except:
            return []
    return []


def _log_kaydet(log: list):
    FEEDBACK_PATH.write_text(
        json.dumps(log, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8"
    )


def tahmin_kaydet(ticker: str, tahmin_prob: float, rejim: str,
                  sinyal: str, fiyat: float, tarih: str = None,
                  model_versiyon: str = "V2", ekstra: dict = None):
    """
    Model tahmin yaptiginda cagir.
    sinyal: 'AL', 'SAT', 'BEKLE'
    """
    log = _log_yukle()

    kayit = {
        "id": len(log) + 1,
        "ticker": ticker,
        "tarih": tarih or datetime.now().strftime("%Y-%m-%d"),
        "tahmin_prob": round(tahmin_prob, 4),
        "sinyal": sinyal,
        "rejim": rejim,
        "giris_fiyat": round(fiyat, 4),
        "model_versiyon": model_versiyon,
        "durum": "bekliyor",  # bekliyor -> dogru/yanlis
        "sonuc_fiyat": None,
        "getiri_pct": None,
        "dogru_mu": None,
        "kontrol_tarihi": None,
    }
    if ekstra:
        kayit["ekstra"] = ekstra

    log.append(kayit)
    _log_kaydet(log)
    return kayit["id"]


def sonuc_guncelle(gun=5):
    """
    Bekleyen tahminlerin gercek sonuclarini kontrol et.
    gun: kac gun sonra kontrol (default 5)
    """
    log = _log_yukle()
    guncellenen = 0

    for kayit in log:
        if kayit["durum"] != "bekliyor":
            continue

        tahmin_tarihi = datetime.strptime(kayit["tarih"], "%Y-%m-%d")
        kontrol_tarihi = tahmin_tarihi + timedelta(days=gun + 2)  # hafta sonu payi

        if datetime.now() < kontrol_tarihi:
            continue  # henuz erken

        # Gercek fiyati cek
        ticker = kayit["ticker"]
        if not ticker.endswith(".IS"):
            ticker += ".IS"

        try:
            df = yf.download(ticker, start=kayit["tarih"],
                           end=(kontrol_tarihi + timedelta(days=3)).strftime("%Y-%m-%d"),
                           progress=False)
            if len(df) < gun:
                continue  # yeterli veri yok

            giris = kayit["giris_fiyat"]
            # gun sonraki kapanis
            if len(df) > gun:
                sonuc_fiyat = float(df["Close"].squeeze().iloc[gun])
            else:
                sonuc_fiyat = float(df["Close"].squeeze().iloc[-1])

            getiri = (sonuc_fiyat - giris) / giris * 100

            # Dogru mu?
            if kayit["sinyal"] == "AL":
                dogru = getiri > 0
            elif kayit["sinyal"] == "SAT":
                dogru = getiri < 0
            else:
                dogru = abs(getiri) < 1  # BEKLE ise az hareket = dogru

            kayit["sonuc_fiyat"] = round(sonuc_fiyat, 4)
            kayit["getiri_pct"] = round(getiri, 4)
            kayit["dogru_mu"] = dogru
            kayit["durum"] = "dogru" if dogru else "yanlis"
            kayit["kontrol_tarihi"] = datetime.now().strftime("%Y-%m-%d")
            guncellenen += 1

        except Exception as e:
            kayit["durum"] = "hata"
            kayit["kontrol_tarihi"] = str(e)

    _log_kaydet(log)
    print(f"  {guncellenen} tahmin guncellendi")
    return guncellenen


def performans_raporu() -> dict:
    """
    Model performans raporu uret.
    Returns: dict with metrics
    """
    log = _log_yukle()
    tamamlanan = [k for k in log if k["durum"] in ("dogru", "yanlis")]

    if not tamamlanan:
        return {"durum": "veri_yok", "mesaj": "Henuz sonuclanan tahmin yok"}

    df = pd.DataFrame(tamamlanan)

    toplam = len(df)
    dogru = (df["dogru_mu"] == True).sum()
    yanlis = (df["dogru_mu"] == False).sum()
    basari = dogru / toplam * 100

    rapor = {
        "toplam_tahmin": toplam,
        "dogru": int(dogru),
        "yanlis": int(yanlis),
        "basari_orani": round(basari, 1),
        "ortalama_getiri": round(df["getiri_pct"].mean(), 2),
        "toplam_getiri": round(df["getiri_pct"].sum(), 2),
    }

    # Rejim bazli
    if "rejim" in df.columns:
        rejim_perf = {}
        for rejim in df["rejim"].unique():
            r_df = df[df["rejim"] == rejim]
            if len(r_df) >= 3:
                rejim_perf[rejim] = {
                    "n": len(r_df),
                    "basari": round((r_df["dogru_mu"] == True).mean() * 100, 1),
                    "ort_getiri": round(r_df["getiri_pct"].mean(), 2),
                }
        rapor["rejim_bazli"] = rejim_perf

    # Sinyal bazli
    for sinyal in ["AL", "SAT", "BEKLE"]:
        s_df = df[df["sinyal"] == sinyal]
        if len(s_df) >= 3:
            rapor[f"sinyal_{sinyal}"] = {
                "n": len(s_df),
                "basari": round((s_df["dogru_mu"] == True).mean() * 100, 1),
                "ort_getiri": round(s_df["getiri_pct"].mean(), 2),
            }

    # Son 20 tahminin trendi
    son20 = df.tail(20)
    rapor["son20_basari"] = round((son20["dogru_mu"] == True).mean() * 100, 1)

    # En basarili/basarisiz hisseler
    ticker_perf = df.groupby("ticker").agg(
        n=("dogru_mu", "count"),
        basari=("dogru_mu", "mean"),
        ort_getiri=("getiri_pct", "mean"),
    ).sort_values("basari", ascending=False)

    rapor["en_iyi_hisseler"] = ticker_perf.head(5).to_dict("index")
    rapor["en_kotu_hisseler"] = ticker_perf.tail(5).to_dict("index")

    return rapor


def iyilestirme_onerileri(rapor: dict) -> list:
    """
    Performans raporundan otomatik iyilestirme onerileri uret.
    """
    oneriler = []

    basari = rapor.get("basari_orani", 50)

    if basari < 55:
        oneriler.append("KRITIK: Basari orani %55 alti — model yeniden egitilmeli")

    # Rejim bazli analiz
    rejim_perf = rapor.get("rejim_bazli", {})
    for rejim, data in rejim_perf.items():
        if data["basari"] < 45:
            oneriler.append(f"{rejim.upper()} rejiminde basari %{data['basari']} — "
                          f"bu rejim icin model parametreleri ayarlanmali")
        if data["basari"] > 65:
            oneriler.append(f"{rejim.upper()} rejiminde guclu: %{data['basari']} — "
                          f"bu rejimde daha agresif pozisyon alinabilir")

    # Sinyal bazli
    al_perf = rapor.get("sinyal_AL", {})
    if al_perf and al_perf.get("basari", 50) < 50:
        oneriler.append("AL sinyalleri basarisiz — threshold yukari cekilmeli (0.50 -> 0.60)")

    # Trend
    son20 = rapor.get("son20_basari", 50)
    if son20 < basari - 10:
        oneriler.append(f"Son 20 tahminde dusus: %{son20} (genel: %{basari}) — "
                       f"piyasa kosullari degismis, yeniden egitim gerekli")

    if not oneriler:
        oneriler.append("Model stabil calisiyor, buyuk sorun yok")

    return oneriler


def gunluk_kontrol():
    """
    Her gun calistirilacak rutin:
    1. Bekleyen tahminleri guncelle
    2. Performans raporu uret
    3. Iyilestirme onerilerini yazdir
    """
    print("=" * 50)
    print("FEEDBACK LOOP — Gunluk Kontrol")
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 1. Sonuclari guncelle
    print("\n1. Tahmin sonuclari guncelleniyor...")
    n = sonuc_guncelle()

    # 2. Rapor
    print("\n2. Performans raporu:")
    rapor = performans_raporu()

    if rapor.get("durum") == "veri_yok":
        print("  Henuz yeterli veri yok (en az 5 gun bekleyin)")
        return rapor

    print(f"  Toplam: {rapor['toplam_tahmin']} tahmin")
    print(f"  Basari: %{rapor['basari_orani']} ({rapor['dogru']}/{rapor['toplam_tahmin']})")
    print(f"  Ort getiri: %{rapor['ortalama_getiri']}")
    print(f"  Son 20: %{rapor['son20_basari']}")

    if "rejim_bazli" in rapor:
        print("\n  Rejim bazli:")
        for r, d in rapor["rejim_bazli"].items():
            print(f"    {r:10s} %{d['basari']:5.1f} (n={d['n']})")

    # 3. Oneriler
    print("\n3. Iyilestirme onerileri:")
    oneriler = iyilestirme_onerileri(rapor)
    for i, o in enumerate(oneriler, 1):
        print(f"  {i}. {o}")

    # Raporu kaydet
    rapor_path = DATA_DIR / f"feedback_rapor_{datetime.now().strftime('%Y%m%d')}.json"
    rapor_path.write_text(
        json.dumps({"rapor": rapor, "oneriler": oneriler}, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8"
    )

    return rapor


if __name__ == "__main__":
    gunluk_kontrol()
