"""
ANKA ROTASYON — Akilli Hisse Degistirme Sistemi
=================================================
Her 30 dakikada:
1. Mevcut pozisyonlarin hacim/momentum kontrolu
2. Kotuleseni SAT
3. Daha iyi bomba varsa AL
4. IQ robotlarini otomatik yonet

Kullanim:
  python anka_rotasyon.py           # 30dk dongude calistir
  python anka_rotasyon.py --kontrol # Tek seferlik kontrol
"""

import sys
import json
import time
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
sys.path.insert(0, str(BASE_DIR))

STATE_FILE = DATA_DIR / "rotasyon_state.json"
LOG_FILE = DATA_DIR / "rotasyon_log.json"

# Parametreler
MAX_POZISYON = 5
POZISYON_TUTAR = 30000  # TL
KONTROL_ARALIK_DK = 30
HACIM_DUSUS_ESIK = 0.5   # Ortalama hacmin 0.5 katina dustuyse cik
MOMENTUM_BOZULMA = -3.0   # Son 2 saatte %-3 dustuyse cik
RSI_ASIRI_ALIM = 80       # RSI 80 ustune ciktiysa kar al
MIN_BOMBA_SKOR = 40       # Yeni hisse icin minimum bomba skoru


def log(mesaj, seviye="INFO"):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{zaman}] [{seviye}] {mesaj}")
    try:
        logs = []
        if LOG_FILE.exists():
            with open(LOG_FILE, encoding="utf-8") as f:
                logs = json.load(f)
        logs.append({"zaman": zaman, "seviye": seviye, "mesaj": mesaj})
        logs = logs[-500:]
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def state_yukle():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"pozisyonlar": {}, "son_kontrol": None, "rotasyon_sayisi": 0}


def state_kaydet(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def veri_cek(ticker, period="5d"):
    t = f"{ticker}.IS" if not ticker.endswith(".IS") else ticker
    try:
        df = yf.download(t, period=period, interval="30m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df if not df.empty else None
    except Exception:
        return None


def hisse_saglik_kontrol(ticker):
    """Mevcut pozisyonun sagligini kontrol et."""
    df = veri_cek(ticker)
    if df is None or len(df) < 10:
        return {"durum": "VERI_YOK", "skor": 0, "sebep": "Veri alinamadi"}

    c = df["Close"].values.flatten()
    v = df["Volume"].values.flatten()

    # Hacim kontrolu
    vol_avg = np.mean(v[-20:]) if len(v) >= 20 else np.mean(v)
    vol_son = v[-1]
    rvol = vol_son / vol_avg if vol_avg > 0 else 0

    # Son 2 saatlik momentum (4 x 30dk mum)
    if len(c) >= 5:
        momentum_2s = (c[-1] / c[-5] - 1) * 100
    else:
        momentum_2s = 0

    # RSI
    delta = pd.Series(c).diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])

    # EMA trend
    ema8 = pd.Series(c).ewm(span=8).mean().iloc[-1]
    ema21 = pd.Series(c).ewm(span=21).mean().iloc[-1]
    trend_ok = ema8 > ema21

    # Karar
    sorunlar = []
    skor = 100

    if rvol < HACIM_DUSUS_ESIK:
        sorunlar.append(f"Hacim cok dusuk (x{rvol:.1f})")
        skor -= 30

    if momentum_2s < MOMENTUM_BOZULMA:
        sorunlar.append(f"Momentum bozuldu ({momentum_2s:+.1f}%)")
        skor -= 30

    if rsi > RSI_ASIRI_ALIM:
        sorunlar.append(f"RSI asiri alim ({rsi:.0f})")
        skor -= 20

    if not trend_ok:
        sorunlar.append("EMA trend kirildi")
        skor -= 20

    if skor >= 70:
        durum = "SAGLIKLI"
    elif skor >= 40:
        durum = "UYARI"
    else:
        durum = "CIK"

    return {
        "durum": durum,
        "skor": skor,
        "rvol": round(rvol, 2),
        "momentum": round(momentum_2s, 2),
        "rsi": round(rsi, 1),
        "trend_ok": trend_ok,
        "sebep": " | ".join(sorunlar) if sorunlar else "Saglikli",
        "fiyat": round(float(c[-1]), 2),
    }


def bomba_tara():
    """Guncel bomba skorlarini oku veya taze tara."""
    bomba_file = DATA_DIR / "gunluk_bomba.json"
    if bomba_file.exists():
        with open(bomba_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("bombalar", [])
    return []


def rotasyon_kontrol(state):
    """Ana rotasyon dongusu."""
    log("=" * 50)
    log("ROTASYON KONTROLU")

    pozlar = state.get("pozisyonlar", {})

    # 1. Mevcut pozisyonlari kontrol et
    cikarilacak = []
    for ticker, poz in pozlar.items():
        saglik = hisse_saglik_kontrol(ticker)
        durum_emoji = {"SAGLIKLI": "OK", "UYARI": "!!", "CIK": "XX", "VERI_YOK": "??"}
        log(f"  {ticker:8} [{durum_emoji.get(saglik['durum'],'?')}] Skor:{saglik['skor']} | RVOL:x{saglik['rvol']} | Mom:{saglik['momentum']:+.1f}% | RSI:{saglik['rsi']} | {saglik['sebep']}")

        if saglik["durum"] == "CIK":
            cikarilacak.append(ticker)
            log(f"  >>> {ticker} CIKARILACAK: {saglik['sebep']}", "TRADE")

    # 2. Cikis islemleri
    for ticker in cikarilacak:
        # IQ'ya satis emri gonder
        log(f"  SATIS SINYAL: {ticker}", "TRADE")
        # aktif_bombalar.txt'den cikar
        try:
            bomba_path = DATA_DIR / "aktif_bombalar.txt"
            if bomba_path.exists():
                mevcut = bomba_path.read_text().strip().split(",")
                mevcut = [h.strip() for h in mevcut if h.strip() != ticker]
                bomba_path.write_text(",".join(mevcut))
                log(f"  {ticker} bomba listesinden cikarildi")
        except Exception:
            pass
        del pozlar[ticker]
        state["rotasyon_sayisi"] += 1

    # 3. Bos pozisyon varsa yeni bomba ekle
    bos_slot = MAX_POZISYON - len(pozlar)
    if bos_slot > 0:
        bombalar = bomba_tara()
        mevcut_tickerlar = set(pozlar.keys())

        yeni_adaylar = [
            b for b in bombalar
            if b.get("ticker") not in mevcut_tickerlar
            and b.get("skor", b.get("bomba_skor", 0)) >= MIN_BOMBA_SKOR
        ]

        for aday in yeni_adaylar[:bos_slot]:
            ticker = aday.get("ticker")
            skor = aday.get("skor", aday.get("bomba_skor", 0))
            fiyat = aday.get("fiyat", 0)

            if fiyat > 0:
                adet = int(POZISYON_TUTAR / fiyat)
            else:
                adet = 1

            pozlar[ticker] = {
                "giris_fiyat": fiyat,
                "adet": adet,
                "zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "skor": skor,
            }

            # aktif_bombalar.txt'ye ekle
            try:
                bomba_path = DATA_DIR / "aktif_bombalar.txt"
                if bomba_path.exists():
                    mevcut = bomba_path.read_text().strip()
                    if ticker not in mevcut:
                        bomba_path.write_text(mevcut + "," + ticker if mevcut else ticker)
                else:
                    bomba_path.write_text(ticker)
            except Exception:
                pass

            log(f"  ALIS SINYAL: {ticker} | {adet} lot @ {fiyat} TL | Skor:{skor}", "TRADE")
            state["rotasyon_sayisi"] += 1

    # 4. Ozet
    state["son_kontrol"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["pozisyonlar"] = pozlar
    state_kaydet(state)

    log(f"Pozisyon: {len(pozlar)}/{MAX_POZISYON} | Rotasyon: {state['rotasyon_sayisi']}")
    for t, p in pozlar.items():
        log(f"  {t:8} {p.get('adet',0)} lot @ {p.get('giris_fiyat',0)} TL")


def dongu():
    log("ANKA ROTASYON BASLATILDI")
    log(f"  Kontrol: her {KONTROL_ARALIK_DK} dakika")
    log(f"  Max pozisyon: {MAX_POZISYON}")
    log(f"  Pozisyon tutar: {POZISYON_TUTAR} TL")

    state = state_yukle()

    # Ilk kontrol
    rotasyon_kontrol(state)

    while True:
        try:
            time.sleep(KONTROL_ARALIK_DK * 60)
            state = state_yukle()
            rotasyon_kontrol(state)
        except KeyboardInterrupt:
            log("Rotasyon durduruldu")
            break
        except Exception as e:
            log(f"Hata: {e}", "ERROR")
            time.sleep(60)


if __name__ == "__main__":
    if "--kontrol" in sys.argv:
        state = state_yukle()
        rotasyon_kontrol(state)
    else:
        dongu()
