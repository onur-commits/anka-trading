"""
BIST ALPHA V2 — TAM OTONOM TRADİNG SİSTEMİ
=============================================
  05:30 → ML model eğit
  08:30 → Günün bombalarını tara + IQ kodları üret + Windows'a kopyala
  08:50 → IQ'ya bildirim gönder (kodlar hazır)
  09:35 → Açılış kontrolü (gap, ilk hareketler)
  10:00 → İlk yarım saat raporu
  12:00 → Öğlen hacim kontrolü
  12:15 → Strateji güncelleme (daha iyi varsa değiştir)
  15:00 → İkindi risk kontrolü
  17:35 → Gün sonu rapor

Kullanım:
  python otonom_trader.py          # Tam otonom başlat (7/24 çalışır)
  python otonom_trader.py --simdi  # Hemen tek döngü çalıştır
  python otonom_trader.py --durum  # Durum kontrol
"""

import sys
import json
import time
import subprocess
import warnings
import schedule
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from tahmin_motoru_v2 import (
    EnsembleModelV2, feature_olustur_v2, market_rejim_tespit,
    sektor_momentum_hesapla, hisse_analiz_v2, atr_hesapla,
)
from risk_yonetimi import RiskYoneticisi
from haber_sentiment import haberleri_analiz_et
from gunluk_bomba import (
    TICKERS, bomba_skor_hesapla, iq_kodu_uret, stop_hesapla,
)
from piyasa_takvim import sadece_bist_acikken, bist_acik_mi

DATA_DIR = BASE_DIR / "data"
IQ_DIR = BASE_DIR / "matriks_iq"
LOG_FILE = DATA_DIR / "otonom_log.json"
STATE_FILE = DATA_DIR / "otonom_state.json"
DATA_DIR.mkdir(exist_ok=True)

VM_NAME = "Windows 11"
WIN_DEPLOY = r"C:\Robot"


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def log(mesaj, seviye="INFO"):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{zaman}] [{seviye}] {mesaj}")
    try:
        logs = []
        if LOG_FILE.exists():
            with open(LOG_FILE) as f:
                logs = json.load(f)
        logs.append({"zaman": zaman, "seviye": seviye, "mesaj": mesaj})
        logs = logs[-500:]
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


IS_WINDOWS = sys.platform.startswith("win")


def win_cmd(cmd, timeout=30):
    """Windows cmd komutu — VPS'te native, Mac'te Parallels VM uzerinden."""
    try:
        if IS_WINDOWS:
            r = subprocess.run(["cmd", "/c", cmd],
                               capture_output=True, text=True, timeout=timeout, shell=False)
        else:
            r = subprocess.run(["prlctl", "exec", VM_NAME, "cmd", "/c", cmd],
                               capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def win_ps(script, timeout=30):
    """PowerShell komutu — VPS'te native, Mac'te Parallels VM uzerinden."""
    try:
        if IS_WINDOWS:
            r = subprocess.run(["powershell", "-Command", script],
                               capture_output=True, text=True, timeout=timeout, shell=False)
        else:
            r = subprocess.run(["prlctl", "exec", VM_NAME, "powershell", "-Command", script],
                               capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def iq_calisiyor_mu():
    """MatriksIQ.exe calisiyor mu? VPS'te direkt, Mac'te Parallels uzerinden."""
    if IS_WINDOWS:
        # PowerShell Get-Process — CMD tasklist argparse sorunundan bagimsiz
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "if (Get-Process -Name MatriksIQ -ErrorAction SilentlyContinue) { 'YES' } else { 'NO' }"],
                capture_output=True, text=True, timeout=15
            )
            return "YES" in (r.stdout or "")
        except Exception:
            return False
    # Mac / Parallels fallback
    return "MatriksIQ.exe" in win_cmd("tasklist /FI \"IMAGENAME eq MatriksIQ.exe\" /NH")


def bildirim(mesaj):
    log(mesaj, "BILDIRIM")
    try:
        subprocess.run(["osascript", "-e",
                         f'display notification "{mesaj}" with title "BIST ALPHA V2" sound name "Glass"'],
                       timeout=5, capture_output=True)
    except Exception:
        pass


def veri_cek(period="6mo"):
    veri = {}
    for t in TICKERS:
        try:
            df = yf.download(t, period=period, progress=False)
            if len(df) >= 120:
                veri[t] = df
        except Exception:
            pass
    xu = yf.download("XU100.IS", period=period, progress=False)
    if len(xu) > 50:
        veri["XU100.IS"] = xu
    return veri


def state_oku():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def state_kaydet(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def dosya_windows_kopyala(ticker_list):
    win_cmd(f'mkdir "{WIN_DEPLOY}" 2>nul')
    for t in ticker_list:
        src = f'\\\\Mac\\Home\\adsız klasör\\borsa_surpriz\\matriks_iq\\BOMBA_{t}.cs'
        dst = f'{WIN_DEPLOY}\\BOMBA_{t}.cs'
        win_cmd(f'copy "{src}" "{dst}" /Y')


def bomba_listesi_guncelle(ticker_list):
    """aktif_bombalar.txt dosyasını güncelle — IQ robotları bunu okur."""
    liste = ",".join(ticker_list)
    win_cmd(f'echo {liste} > "{WIN_DEPLOY}\\aktif_bombalar.txt"')
    log(f"  📝 aktif_bombalar.txt → {liste}")


def hisse_tara(veri, model, rejim):
    """Tüm hisseleri tara, bomba skorlarıyla döndür."""
    sonuclar = []
    for ticker, df in veri.items():
        if ticker == "XU100.IS":
            continue
        try:
            analiz = hisse_analiz_v2(ticker, df, model, rejim)
            if analiz is None:
                continue
            features = feature_olustur_v2(df)
            if features is None:
                continue
            son = features.iloc[-1].to_dict()
            close = df["Close"].squeeze()
            high = df["High"].squeeze()
            low = df["Low"].squeeze()
            atr = atr_hesapla(high, low, close)
            atr_pct = float(atr.iloc[-1] / close.iloc[-1] * 100)
            b_skor, b_sebepler = bomba_skor_hesapla(analiz, son)
            son5g = float((close.iloc[-1] / close.iloc[-5] - 1) * 100) if len(close) > 5 else 0

            sonuclar.append({
                "ticker": ticker, "bomba_skor": b_skor,
                "sebepler": b_sebepler,
                "ml": analiz.get("ml_olasilik") or 0,
                "teknik": analiz["teknik_skor"],
                "fiyat": analiz["fiyat"],
                "atr_pct": atr_pct, "son5g": son5g,
            })
        except Exception:
            continue
    sonuclar.sort(key=lambda x: x["bomba_skor"], reverse=True)
    return sonuclar


def kodlari_uret_ve_kopyala(top_sonuclar):
    """Top sonuçlar için IQ kodları üret, diske ve Windows'a kopyala."""
    uretilen = []
    for s in top_sonuclar:
        t = s["ticker"].replace(".IS", "")
        kod = iq_kodu_uret(s["ticker"], s["bomba_skor"], s["sebepler"], s["atr_pct"], s["fiyat"])
        dosya = IQ_DIR / f"BOMBA_{t}.cs"
        with open(dosya, "w", encoding="utf-8") as f:
            f.write(kod)
        uretilen.append(t)
    dosya_windows_kopyala(uretilen)
    return uretilen


# ============================================================
# MatriksIQ TCP API ile GERÇEK EMİR GÖNDERME
# ============================================================

TRADE_LOG_FILE = DATA_DIR / "otonom_trades.json"
POZISYON_FILE = DATA_DIR / "otonom_pozisyonlar.json"

# Midas hesap bilgileri — anka_api.py'deki default'larla aynı
MIDAS_ACCOUNT_ID = "0~2205905"
MIDAS_BROKAGE_ID = "115"

# Risk parametreleri (bot config)
MAX_POZISYON_SAYISI = 3           # Aynı anda max pozisyon
MAX_POZISYON_TL = 20000           # Pozisyon başına max TL
MIN_BOMBA_SKOR_ALIS = 60          # Alış için min skor


def _trade_log_yaz(kayit):
    """otonom_trades.json'a append."""
    try:
        trades = []
        if TRADE_LOG_FILE.exists():
            with open(TRADE_LOG_FILE) as f:
                trades = json.load(f)
        trades.append(kayit)
        trades = trades[-500:]  # son 500 kayıt
        with open(TRADE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        log(f"Trade log yazma hatası: {e}", "ERROR")


def _pozisyonlari_oku():
    """Aktif pozisyonları JSON'dan oku."""
    if POZISYON_FILE.exists():
        try:
            with open(POZISYON_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _pozisyonlari_yaz(pozlar):
    """Aktif pozisyonları JSON'a kaydet."""
    try:
        with open(POZISYON_FILE, "w", encoding="utf-8") as f:
            json.dump(pozlar, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        log(f"Pozisyon yazma hatası: {e}", "ERROR")


def iq_alis_yap(symbol, adet, fiyat=0, skor=None, sebep=""):
    """
    MatriksIQ TCP API üzerinden gerçek ALIŞ emri gönder.
    fiyat=0 ise piyasa emri, >0 ise limit.
    Sonucu trade log'a yazar, pozisyon dosyasını günceller.

    DÖNÜŞ: dict {success, yanit, hata}
    """
    try:
        from anka_api import AnkaAPI
    except ImportError as e:
        log(f"anka_api import hatası: {e}", "ERROR")
        return {"success": False, "hata": f"import: {e}"}

    api = AnkaAPI()
    kayit_temel = {
        "zaman": datetime.now().isoformat(),
        "tip": "ALIS",
        "symbol": symbol,
        "adet": adet,
        "fiyat": fiyat,
        "skor": skor,
        "sebep": sebep,
        "mod": "CANLI",
    }
    try:
        if not api.baglan():
            kayit = {**kayit_temel, "status": "bağlantı_yok", "hata": "IQ TCP bağlanamadı"}
            _trade_log_yaz(kayit)
            log(f"❌ ALIS {symbol}: IQ bağlantı yok", "ERROR")
            return {"success": False, "hata": "bağlantı"}

        log(f"📤 ALIS emri gönderiliyor: {symbol} x {adet} adet (fiyat={fiyat})")
        yanit = api.alis_emri(symbol, adet, fiyat=fiyat,
                               account_id=MIDAS_ACCOUNT_ID,
                               brokage_id=MIDAS_BROKAGE_ID)

        kayit = {**kayit_temel, "status": "gonderildi", "yanit": yanit}
        _trade_log_yaz(kayit)

        # Pozisyon ekle
        pozlar = _pozisyonlari_oku()
        pozlar[symbol] = {
            "giris_zaman": datetime.now().isoformat(),
            "adet": adet,
            "giris_fiyat_plan": fiyat,
            "skor": skor,
            "sebep": sebep,
        }
        _pozisyonlari_yaz(pozlar)

        log(f"✅ ALIS gönderildi: {symbol} (yanıt alındı)")
        bildirim(f"💰 ALIŞ: {symbol} x {adet} @ ~{fiyat} | Skor:{skor}")
        return {"success": True, "yanit": yanit}

    except Exception as e:
        kayit = {**kayit_temel, "status": "hata", "hata": str(e)}
        _trade_log_yaz(kayit)
        log(f"❌ ALIS {symbol} hata: {e}", "ERROR")
        return {"success": False, "hata": str(e)}
    finally:
        api.kapat()


def iq_satis_yap(symbol, adet=None, fiyat=0, sebep=""):
    """
    MatriksIQ TCP API üzerinden gerçek SATIŞ emri gönder.
    adet=None ise pozisyon dosyasından oku.
    fiyat=0 ise piyasa emri.
    """
    try:
        from anka_api import AnkaAPI
    except ImportError as e:
        return {"success": False, "hata": f"import: {e}"}

    pozlar = _pozisyonlari_oku()
    if adet is None:
        poz = pozlar.get(symbol)
        if not poz:
            log(f"SATIS: {symbol} pozisyon dosyasında yok", "WARN")
            return {"success": False, "hata": "pozisyon yok"}
        adet = poz.get("adet")

    if not adet:
        return {"success": False, "hata": "adet 0"}

    api = AnkaAPI()
    kayit_temel = {
        "zaman": datetime.now().isoformat(),
        "tip": "SATIS",
        "symbol": symbol,
        "adet": adet,
        "fiyat": fiyat,
        "sebep": sebep,
        "mod": "CANLI",
    }
    try:
        if not api.baglan():
            kayit = {**kayit_temel, "status": "bağlantı_yok"}
            _trade_log_yaz(kayit)
            log(f"❌ SATIS {symbol}: IQ bağlantı yok", "ERROR")
            return {"success": False, "hata": "bağlantı"}

        log(f"📤 SATIS emri: {symbol} x {adet} adet (fiyat={fiyat}) — {sebep}")
        yanit = api.satis_emri(symbol, adet, fiyat=fiyat,
                                account_id=MIDAS_ACCOUNT_ID,
                                brokage_id=MIDAS_BROKAGE_ID)

        kayit = {**kayit_temel, "status": "gonderildi", "yanit": yanit}
        _trade_log_yaz(kayit)

        # Pozisyonu sil
        if symbol in pozlar:
            del pozlar[symbol]
            _pozisyonlari_yaz(pozlar)

        log(f"✅ SATIS gönderildi: {symbol}")
        bildirim(f"💵 SATIŞ: {symbol} x {adet} | {sebep}")
        return {"success": True, "yanit": yanit}

    except Exception as e:
        kayit = {**kayit_temel, "status": "hata", "hata": str(e)}
        _trade_log_yaz(kayit)
        log(f"❌ SATIS {symbol} hata: {e}", "ERROR")
        return {"success": False, "hata": str(e)}
    finally:
        api.kapat()


def gorev_09_05_otonom_alis():
    """09:05 — Sabah taramasında bulunan bombaları otomatik al (CANLI)."""
    log("=" * 50)
    log("💰 [09:05] OTONOM ALIS — CANLI")

    # En son tarama sonucunu oku
    rapor_path = DATA_DIR / "gunluk_bomba.json"
    if not rapor_path.exists():
        log("Sabah taraması raporu yok, alış atlandı", "WARN")
        return

    try:
        with open(rapor_path, "r", encoding="utf-8") as f:
            rapor = json.load(f)
    except Exception as e:
        log(f"Rapor okunamadı: {e}", "ERROR")
        return

    bombalar = rapor.get("bombalar", [])
    if not bombalar:
        log("Bu sabah bomba yok, alış atlandı")
        return

    # Mevcut pozisyonları al
    mevcut = _pozisyonlari_oku()
    bos_slot = MAX_POZISYON_SAYISI - len(mevcut)
    if bos_slot <= 0:
        log(f"Max pozisyon ({MAX_POZISYON_SAYISI}) dolu, alış atlandı")
        return

    # Skor sırasına göre filtrele
    aday = [b for b in bombalar if b.get("bomba_skor", 0) >= MIN_BOMBA_SKOR_ALIS
            and b["ticker"] not in mevcut]
    aday.sort(key=lambda x: x.get("bomba_skor", 0), reverse=True)

    alinan = 0
    for b in aday[:bos_slot]:
        ticker = b["ticker"]
        fiyat = float(b.get("fiyat", 0))
        skor = b.get("bomba_skor", 0)
        sebepler = b.get("sebepler", [])

        if fiyat <= 0:
            log(f"  {ticker}: fiyat 0, atlandı")
            continue

        # Adet hesapla — MAX_POZISYON_TL'yi aşmayacak şekilde
        adet = int(MAX_POZISYON_TL / fiyat)
        if adet < 1:
            log(f"  {ticker}: {fiyat:.2f} TL × 1 adet > {MAX_POZISYON_TL} limit, atlandı")
            continue

        sebep_str = ", ".join(sebepler[:2]) if sebepler else ""
        sonuc = iq_alis_yap(ticker, adet, fiyat=0,  # piyasa emri
                             skor=skor, sebep=sebep_str)
        if sonuc.get("success"):
            alinan += 1
            log(f"  ✅ {ticker}: {adet} adet @ ~{fiyat:.2f} (toplam ~{adet*fiyat:.0f} TL)")
        else:
            log(f"  ❌ {ticker}: {sonuc.get('hata')}")

    log(f"Toplam {alinan} alış yapıldı")


def gorev_17_30_gun_sonu_satis():
    """17:30 — Açık tüm pozisyonları kapat (gün sonu, intraday)."""
    log("=" * 50)
    log("🏁 [17:30] GÜN SONU SATIS — TÜM POZİSYONLAR KAPATILIYOR")

    pozlar = _pozisyonlari_oku()
    if not pozlar:
        log("Açık pozisyon yok")
        return

    satilan = 0
    for symbol in list(pozlar.keys()):
        sonuc = iq_satis_yap(symbol, fiyat=0, sebep="GUN_SONU")  # piyasa emri
        if sonuc.get("success"):
            satilan += 1

    log(f"Toplam {satilan} pozisyon kapatıldı")


def gorev_durum_raporu():
    """Anlık durum: IQ pozisyonları + bot pozisyonları karşılaştır."""
    try:
        from anka_api import AnkaAPI
        api = AnkaAPI()
        iq_durum = api.robot_durum_sorgula()
    except Exception as e:
        log(f"IQ durum hatası: {e}", "ERROR")
        iq_durum = None

    bot_poz = _pozisyonlari_oku()
    log("=" * 50)
    log("📊 DURUM")
    log(f"  Bot pozisyonları: {list(bot_poz.keys())}")
    if iq_durum and iq_durum.get("pozisyonlar"):
        for p in iq_durum["pozisyonlar"]:
            log(f"  Midas: {p['symbol']} x {p['adet']}  PL:{p['kar_zarar']:+.2f} TL")


# ============================================================
# ZAMANLI GÖREVLER
# ============================================================

def gorev_05_30_egitim():
    """05:30 — ML model eğit."""
    log("=" * 50)
    log("🧠 [05:30] ML MODEL EĞİTİMİ")
    try:
        veri = {}
        for t in TICKERS:
            try:
                df = yf.download(t, period="2y", progress=False)
                if len(df) >= 200:
                    veri[t] = df
            except Exception:
                pass
        xu = yf.download("XU100.IS", period="2y", progress=False)
        rejim = market_rejim_tespit(xu) if len(xu) > 50 else None
        log(f"  {len(veri)} hisse (2 yıl)")

        model = EnsembleModelV2()
        meta = model.egit(veri, market_rejim=rejim)
        if meta:
            log(f"  ✅ AUC:{meta['ensemble_auc']} F1:{meta['ensemble_f1']}")
            bildirim(f"ML güncellendi — AUC:{meta['ensemble_auc']}")
        else:
            log("  ❌ Eğitim başarısız", "ERROR")
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_08_30_tarama():
    """08:30 — Günün bombalarını bul + IQ kodları üret."""
    log("=" * 50)
    log("🔥 [08:30] SABAH BOMBA TARAMASI")
    try:
        model = EnsembleModelV2.yukle()
        if not model:
            log("  Model yok, eğitim yapılıyor...")
            gorev_05_30_egitim()
            model = EnsembleModelV2.yukle()

        veri = veri_cek("6mo")
        log(f"  {len(veri)} hisse")

        xu = veri.get("XU100.IS")
        rejim = market_rejim_tespit(xu) if xu is not None and len(xu) > 50 else None
        if rejim:
            log(f"  Piyasa: {rejim['rejim'].upper()} ADX:{rejim['adx']}")

        sentiment = haberleri_analiz_et()

        sonuclar = hisse_tara(veri, model, rejim)
        # HİBRİT VETO: ML + Hacim + Kapanış gücü hepsi onaylamalı
        from gunluk_bomba import hibrit_bomba_kontrol
        hibrit_sonuclar = []
        for s in sonuclar:
            if s["bomba_skor"] >= 25:
                df = veri.get(s["ticker"])
                if df is not None and hibrit_bomba_kontrol(df, s["ml"]):
                    hibrit_sonuclar.append(s)
                    log(f"  ✅ {s['ticker'].replace('.IS','')} HİBRİT ONAY (ML+Hacim+Kapanış)")
                elif s["bomba_skor"] >= 50:
                    # Skor çok yüksekse veto'yu esnet
                    hibrit_sonuclar.append(s)
                    log(f"  ⚠️ {s['ticker'].replace('.IS','')} SKOR YÜKSEK — veto esnetildi")
                else:
                    log(f"  ❌ {s['ticker'].replace('.IS','')} VETOlandı (hacim/kapanış zayıf)")
        top5 = hibrit_sonuclar[:5]

        if top5:
            uretilen = kodlari_uret_ve_kopyala(top5)

            for s in top5:
                t = s["ticker"].replace(".IS", "")
                log(f"  💣 {t} Skor:{s['bomba_skor']} ML:{s['ml']*100:.0f}% Fiyat:{s['fiyat']:.2f}")

            state = {
                "tarih": datetime.now().strftime("%Y-%m-%d"),
                "rejim": rejim,
                "bombalar": [
                    {"ticker": s["ticker"].replace(".IS", ""), "skor": s["bomba_skor"],
                     "ml": round(s["ml"], 3), "fiyat": s["fiyat"], "atr_pct": round(s["atr_pct"], 2)}
                    for s in top5
                ],
                "aktif_stratejiler": uretilen,
                "son_guncelleme": datetime.now().strftime("%H:%M"),
            }
            state_kaydet(state)
            bomba_listesi_guncelle(uretilen)
            bildirim(f"Bombalar: {', '.join(uretilen)}")
        else:
            log("  ❌ Bugün bomba yok")
            bomba_listesi_guncelle([])
            bildirim("Bugün bomba hisse bulunamadı")

    except Exception as e:
        import traceback
        log(f"  HATA: {e}", "ERROR")
        log(f"  TRACEBACK: {traceback.format_exc()}", "ERROR")


def gorev_08_50_iq_kontrol():
    """08:50 — IQ çalışıyor mu kontrol et."""
    log("🤖 [08:50] IQ KONTROL")

    if not iq_calisiyor_mu():
        log("  ⚠ IQ kapalı!", "WARN")
        bildirim("⚠️ MatriksIQ kapalı! Bilgisayarı kontrol et.")
        # IQ'yu başlatmayı dene
        win_cmd('start C:\\MatriksIQ\\MatriksIQ.exe')
        time.sleep(30)
        if iq_calisiyor_mu():
            log("  ✅ IQ otomatik başlatıldı")
            bildirim("MatriksIQ otomatik başlatıldı ✅")
        else:
            log("  ❌ IQ başlatılamadı", "ERROR")
        return

    # IQ log kontrolü — stratejiler çalışıyor mu?
    state = state_oku()
    calisan = 0
    for t in ["ENJSA", "GARAN", "HALKB", "TSKB", "TKFEN", "AKSEN", "ISCTR", "GUBRF", "THYAO", "SAHOL"]:
        log_dir = f"C:\\MatriksIQ\\Logs\\AlgoTrading\\BOMBA_{t}"
        out = win_cmd(f'dir "{log_dir}" /b 2>nul')
        if out:
            calisan += 1

    log(f"  ✅ IQ çalışıyor, {calisan}/10 strateji log'u var")
    if calisan == 0:
        bildirim("⚠️ IQ açık ama hiçbir strateji çalışmıyor! Kontrol et.")


def gorev_09_35_acilis():
    """09:35 — Açılış gap ve ilk hareketler."""
    log("📊 [09:35] AÇILIŞ KONTROLÜ")
    try:
        state = state_oku()
        aktif = state.get("aktif_stratejiler", [])

        for t in aktif:
            try:
                df = yf.download(f"{t}.IS", period="5d", interval="5m", progress=False)
                if len(df) < 2:
                    continue
                close = df["Close"].squeeze()
                # Bugünkü ilk fiyat vs dünkü kapanış
                bugun = df[df.index.date == df.index.date[-1]]
                if len(bugun) > 0:
                    acilis = float(bugun["Open"].squeeze().iloc[0])
                    son = float(bugun["Close"].squeeze().iloc[-1])
                    dun_kapanis = float(close.iloc[-len(bugun)-1]) if len(close) > len(bugun) else acilis
                    gap = (acilis / dun_kapanis - 1) * 100
                    hareket = (son / acilis - 1) * 100

                    emoji = "🟢" if gap > 0.5 else "🔴" if gap < -0.5 else "⚪"
                    log(f"  {emoji} {t}: Gap {gap:+.1f}% | Hareket {hareket:+.1f}% | Son:{son:.2f}")

                    if abs(gap) > 3:
                        bildirim(f"🚨 {t} gap {gap:+.1f}%!")
            except Exception:
                continue

        # XU100
        xu = yf.download("XU100.IS", period="2d", interval="5m", progress=False)
        if len(xu) > 1:
            bugun_xu = xu[xu.index.date == xu.index.date[-1]]
            if len(bugun_xu) > 0:
                xu_acilis = float(bugun_xu["Open"].squeeze().iloc[0])
                xu_son = float(bugun_xu["Close"].squeeze().iloc[-1])
                xu_hareket = (xu_son / xu_acilis - 1) * 100
                log(f"  XU100: {xu_son:.0f} ({xu_hareket:+.1f}%)")

    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_10_00_ilk_yarim_saat():
    """10:00 — İlk yarım saat raporu."""
    log("📈 [10:00] İLK YARIM SAAT")
    try:
        state = state_oku()
        for t in state.get("aktif_stratejiler", []):
            try:
                df = yf.download(f"{t}.IS", period="2d", progress=False)
                if len(df) >= 2:
                    close = df["Close"].squeeze()
                    gunluk = (close.iloc[-1] / close.iloc[-2] - 1) * 100
                    vol = df["Volume"].squeeze().iloc[-1]
                    log(f"  {t}: {close.iloc[-1]:.2f} ({gunluk:+.1f}%) Hacim:{vol:,.0f}")
            except Exception:
                continue
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_12_00_ogle():
    """12:00 — Öğlen hacim kontrolü."""
    log("📊 [12:00] ÖĞLEN KONTROLÜ")
    try:
        state = state_oku()
        for t in state.get("aktif_stratejiler", []):
            try:
                df = yf.download(f"{t}.IS", period="5d", progress=False)
                if len(df) < 2:
                    continue
                close = df["Close"].squeeze()
                volume = df["Volume"].squeeze()
                gunluk = (close.iloc[-1] / close.iloc[-2] - 1) * 100
                rvol = volume.iloc[-1] / volume.iloc[:-1].mean()

                log(f"  {t}: {close.iloc[-1]:.2f} ({gunluk:+.1f}%) Hacim:x{rvol:.1f}")

                if gunluk < -5:
                    bildirim(f"⚠️ {t} -%{abs(gunluk):.1f} düşüş!")
                if rvol > 3:
                    bildirim(f"📊 {t} hacim patlaması x{rvol:.1f}!")
            except Exception:
                continue
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_12_15_guncelle():
    """12:15 — Daha iyi adaylar varsa güncelle."""
    log("🔄 [12:15] STRATEJİ GÜNCELLEME")
    try:
        model = EnsembleModelV2.yukle()
        veri = veri_cek("3mo")
        xu = veri.get("XU100.IS")
        rejim = market_rejim_tespit(xu) if xu is not None and len(xu) > 50 else None

        state = state_oku()
        mevcut = state.get("aktif_stratejiler", [])

        sonuclar = hisse_tara(veri, model, rejim)
        yeni_top = [s["ticker"].replace(".IS", "") for s in sonuclar[:5] if s["bomba_skor"] >= 25]

        eklenen = [t for t in yeni_top if t not in mevcut]
        cikan = [t for t in mevcut if t not in yeni_top]

        if eklenen:
            # Yeni kodları üret
            yeni_sonuc = [s for s in sonuclar if s["ticker"].replace(".IS", "") in eklenen]
            kodlari_uret_ve_kopyala(yeni_sonuc)

            log(f"  📈 Eklenen: {eklenen}")
            log(f"  📉 Çıkan: {cikan}")
            bildirim(f"Yeni bombalar: {eklenen}! IQ'da güncelle.")

            state["aktif_stratejiler"] = yeni_top
            state["son_guncelleme"] = datetime.now().strftime("%H:%M")
            state_kaydet(state)
            bomba_listesi_guncelle(yeni_top)
        else:
            log("  ✅ Değişiklik yok")
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_15_00_risk():
    """15:00 — İkindi risk kontrolü."""
    log("⚖️ [15:00] İKİNDİ RİSK")
    try:
        xu = yf.download("XU100.IS", period="5d", progress=False)
        if len(xu) >= 2:
            close = xu["Close"].squeeze()
            gunluk = (close.iloc[-1] / close.iloc[-2] - 1) * 100
            log(f"  XU100: {close.iloc[-1]:.0f} ({gunluk:+.1f}%)")

            if gunluk < -3:
                bildirim(f"🚨 XU100 -%{abs(gunluk):.1f} — PANİK! Stratejileri kontrol et!")
            elif gunluk > 2:
                bildirim(f"🐂 XU100 +%{gunluk:.1f} — güzel gün!")

        # IQ log kontrol
        state = state_oku()
        for t in state.get("aktif_stratejiler", []):
            tarih = datetime.now().strftime("%Y.%m.%d")
            out = win_cmd(f'dir "C:\\MatriksIQ\\Logs\\AlgoTrading\\BOMBA_{t}\\{tarih}" /b 2>nul')
            status = "✅ Aktif" if out else "❌ Log yok"
            log(f"  BOMBA_{t}: {status}")

    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_17_35_rapor():
    """17:35 — Gün sonu rapor."""
    log("=" * 50)
    log("📝 [17:35] GÜN SONU RAPORU")
    try:
        state = state_oku()
        satirlar = [f"📊 {datetime.now().strftime('%d.%m.%Y')} Raporu"]

        if state.get("rejim"):
            satirlar.append(f"Piyasa: {state['rejim'].get('rejim', '?').upper()}")

        for b in state.get("bombalar", []):
            t = b["ticker"]
            try:
                df = yf.download(f"{t}.IS", period="2d", progress=False)
                if len(df) >= 2:
                    close = df["Close"].squeeze()
                    gunluk = (close.iloc[-1] / close.iloc[-2] - 1) * 100
                    satirlar.append(f"  {t}: {close.iloc[-1]:.2f} ({gunluk:+.1f}%) Skor:{b['skor']}")
            except Exception:
                pass

        rapor = "\n".join(satirlar)
        log(rapor)
        bildirim("Gün sonu rapor hazır")

        rapor_path = DATA_DIR / f"rapor_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(rapor_path, "w", encoding="utf-8") as f:
            f.write(rapor)

    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


# ============================================================
# ANA SİSTEM
# ============================================================

def otonom_baslat():
    """Tam otonom sistemi başlat — 7/24 çalışır."""
    log("=" * 50)
    log("🤖 BIST ALPHA V2 — OTONOM TRADER")
    acik, sebep = bist_acik_mi()
    log(f"  Piyasa: {'🟢 AÇIK' if acik else '🔴 KAPALI'} — {sebep}")
    log("=" * 50)

    # ML eğitim hafta sonu da çalışabilir (geçmiş veri kullanır)
    schedule.every().day.at("05:30").do(gorev_05_30_egitim)
    # Trading job'ları BIST açık günlerde — hafta sonu ve resmi tatil atlanır
    schedule.every().day.at("08:30").do(sadece_bist_acikken(gorev_08_30_tarama))
    schedule.every().day.at("08:50").do(sadece_bist_acikken(gorev_08_50_iq_kontrol))
    # 09:05 — OTONOM ALIS (gerçek CANLI emir, anka_api üzerinden Midas'a)
    schedule.every().day.at("09:05").do(sadece_bist_acikken(gorev_09_05_otonom_alis))
    schedule.every().day.at("09:35").do(sadece_bist_acikken(gorev_09_35_acilis))
    schedule.every().day.at("10:00").do(sadece_bist_acikken(gorev_10_00_ilk_yarim_saat))
    schedule.every().day.at("12:00").do(sadece_bist_acikken(gorev_12_00_ogle))
    schedule.every().day.at("12:15").do(sadece_bist_acikken(gorev_12_15_guncelle))
    schedule.every().day.at("15:00").do(sadece_bist_acikken(gorev_15_00_risk))
    # 17:30 — GÜN SONU SATIS (intraday, tüm pozisyonları kapat)
    schedule.every().day.at("17:30").do(sadece_bist_acikken(gorev_17_30_gun_sonu_satis))
    schedule.every().day.at("17:35").do(sadece_bist_acikken(gorev_17_35_rapor))

    log("")
    log("📅 PROGRAM:")
    log("  05:30 → ML model eğitimi")
    log("  08:30 → Bomba tarama + IQ kod üretimi")
    log("  08:50 → IQ bildirim (kodlar hazır)")
    log("  09:35 → Açılış gap kontrolü")
    log("  10:00 → İlk yarım saat raporu")
    log("  12:00 → Öğlen hacim kontrolü")
    log("  12:15 → Strateji güncelleme")
    log("  15:00 → İkindi risk kontrolü")
    log("  17:35 → Gün sonu rapor")
    log("")

    bildirim("Otonom Trader başladı!")

    while True:
        schedule.run_pending()
        time.sleep(30)


def tek_dongu():
    """Test — hemen hepsini çalıştır."""
    log("🚀 TEK DÖNGÜ")
    gorev_05_30_egitim()
    gorev_08_30_tarama()
    gorev_08_50_iq_hazirla()
    gorev_09_35_acilis()
    gorev_10_00_ilk_yarim_saat()
    gorev_12_00_ogle()
    gorev_17_35_rapor()
    log("✅ Bitti")


def durum():
    """Mevcut durumu göster."""
    print("\n🔍 OTONOM TRADER DURUMU")
    print("=" * 40)

    print("IQ:", "✅ Çalışıyor" if iq_calisiyor_mu() else "❌ Kapalı")

    state = state_oku()
    if state:
        print(f"Tarih: {state.get('tarih', '?')}")
        r = state.get("rejim")
        if r:
            print(f"Rejim: {r.get('rejim', '?').upper()}")
        print(f"Stratejiler: {state.get('aktif_stratejiler', [])}")
        for b in state.get("bombalar", []):
            print(f"  💣 {b['ticker']}: Skor {b['skor']}, ML {b['ml']*100:.0f}%")
    else:
        print("Henüz tarama yok")

    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            logs = json.load(f)
        if logs:
            print(f"\nSon log: {logs[-1]['mesaj']}")


if __name__ == "__main__":
    if "--simdi" in sys.argv:
        tek_dongu()
    elif "--durum" in sys.argv:
        durum()
    else:
        otonom_baslat()
