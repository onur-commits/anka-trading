"""
BIST ALPHA V3 — OTONOM TRADİNG MOTORU
======================================
VPS-ready, Telegram entegreli, tam otonom.

Önceki V2'den farklar:
  - Telegram bildirim (macOS notification yerine)
  - Strateji yöneticisi (otomatik robot ekleme/çıkarma)
  - Daha akıllı bomba listesi yönetimi (her bar kontrol)
  - VPS'te çalışmaya hazır (prlctl bağımlılığı yok)
  - Portföy takibi ve P/L izleme
  - Gün içi sinyal güncelleme

Kullanım:
  python motor_v3.py                # Tam otonom başlat
  python motor_v3.py --simdi        # Hemen tek döngü
  python motor_v3.py --durum        # Durum kontrol
  python motor_v3.py --telegram-test  # Telegram bağlantı test
  python motor_v3.py --vps          # VPS modunda çalış (prlctl yok, direkt dosya yolu)
"""

import sys
import json
import time
import os
import subprocess
import warnings
import schedule
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

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

# ============================================================
# YAPILANDIRMA
# ============================================================

class Config:
    """Tüm yapılandırma tek yerde."""

    # Çalışma modu
    VPS_MODE = "--vps" in sys.argv  # True ise prlctl kullanmaz

    # Dizinler
    DATA_DIR = BASE_DIR / "data"
    IQ_DIR = BASE_DIR / "matriks_iq"
    LOG_FILE = DATA_DIR / "motor_v3_log.json"
    STATE_FILE = DATA_DIR / "motor_v3_state.json"
    PORTFOLIO_FILE = DATA_DIR / "portfolio.json"

    # Windows bağlantısı
    VM_NAME = "Windows 11"
    if VPS_MODE:
        # VPS'te direkt Windows dosya yolu
        WIN_DEPLOY = Path(r"C:\Users\onurbodur\Desktop\IQ_Deploy")
        BOMBA_FILE = WIN_DEPLOY / "aktif_bombalar.txt"
    else:
        # Mac → Parallels
        WIN_DEPLOY_CMD = r"C:\Robot"
        BOMBA_FILE_CMD = WIN_DEPLOY_CMD + r"\aktif_bombalar.txt"

    # Telegram (kullanıcı kendi bot token'ını ekler)
    TELEGRAM_BOT_TOKEN = ""  # @BotFather'dan al
    TELEGRAM_CHAT_ID = ""    # @userinfobot'dan al

    # Trading parametreleri
    MAX_BOMBA = 7          # Aynı anda max bomba hisse
    MIN_BOMBA_SKOR = 25    # Minimum bomba skoru
    MAX_POSITION_TL = 7000  # Max pozisyon değeri (TL)
    STOP_LOSS_PCT = 6.0    # Stop-loss yüzdesi
    TRAILING_STOP_PCT = 2.5 # Trailing stop yüzdesi

    # Zamanlama
    SCHEDULE = {
        "egitim": "05:30",
        "tarama": "08:30",
        "iq_kontrol": "08:50",
        "acilis": "09:35",
        "ilk_yarim_saat": "10:00",
        "ogle_kontrol": "12:00",
        "strateji_guncelle": "12:15",
        "ikindi_risk": "15:00",
        "gun_sonu": "17:35",
    }


Config.DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# LOG & BİLDİRİM SİSTEMİ
# ============================================================

class Logger:
    """Merkezi log sistemi — dosya + konsol + telegram."""

    @staticmethod
    def log(mesaj: str, seviye: str = "INFO"):
        zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{zaman}] [{seviye}] {mesaj}")
        try:
            logs = []
            if Config.LOG_FILE.exists():
                with open(Config.LOG_FILE) as f:
                    logs = json.load(f)
            logs.append({"zaman": zaman, "seviye": seviye, "mesaj": mesaj})
            logs = logs[-1000:]  # Son 1000 kayıt
            with open(Config.LOG_FILE, "w") as f:
                json.dump(logs, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    @staticmethod
    def bildirim(mesaj: str):
        """Telegram + macOS bildirim."""
        Logger.log(mesaj, "BILDIRIM")

        # Telegram
        if Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID:
            try:
                import urllib.request
                url = (f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"
                       f"/sendMessage?chat_id={Config.TELEGRAM_CHAT_ID}"
                       f"&text={urllib.parse.quote(mesaj)}&parse_mode=HTML")
                urllib.request.urlopen(url, timeout=10)
            except Exception:
                pass

        # macOS (VPS'te çalışmaz, sorun değil)
        if not Config.VPS_MODE:
            try:
                subprocess.run(
                    ["osascript", "-e",
                     f'display notification "{mesaj}" with title "BIST ALPHA V3" sound name "Glass"'],
                    timeout=5, capture_output=True)
            except Exception:
                pass


log = Logger.log
bildirim = Logger.bildirim


# ============================================================
# WINDOWS BAĞLANTI KATMANI
# ============================================================

class WindowsBridge:
    """Mac/VPS → Windows iletişimi."""

    @staticmethod
    def cmd(command: str, timeout: int = 30) -> str:
        if Config.VPS_MODE:
            # VPS'te direkt Windows komutu
            try:
                r = subprocess.run(command, shell=True,
                                   capture_output=True, text=True, timeout=timeout)
                return r.stdout.strip()
            except Exception:
                return ""
        else:
            # Mac → Parallels
            try:
                r = subprocess.run(
                    ["prlctl", "exec", Config.VM_NAME, "cmd", "/c", command],
                    capture_output=True, text=True, timeout=timeout)
                return r.stdout.strip()
            except Exception:
                return ""

    @staticmethod
    def iq_calisiyor_mu() -> bool:
        out = WindowsBridge.cmd('tasklist /FI "IMAGENAME eq MatriksIQ.exe" /NH')
        return "MatriksIQ.exe" in out

    @staticmethod
    def bomba_listesi_yaz(ticker_list: List[str]):
        """aktif_bombalar.txt dosyasını atomik olarak güncelle.
        os.replace() kullanarak yarım yazılmış dosya riskini önler —
        MatriksIQ her zaman tutarlı bir liste okur."""
        liste = ",".join(ticker_list)
        if Config.VPS_MODE:
            temp = Config.BOMBA_FILE.with_suffix(".tmp")
            temp.write_text(liste, encoding="utf-8")
            os.replace(str(temp), str(Config.BOMBA_FILE))  # Atomik!
        else:
            # Mac → Parallels: önce temp yaz, sonra rename
            WindowsBridge.cmd(f'echo {liste} > "{Config.BOMBA_FILE_CMD}.tmp"')
            WindowsBridge.cmd(f'move /Y "{Config.BOMBA_FILE_CMD}.tmp" "{Config.BOMBA_FILE_CMD}"')
        log(f"  aktif_bombalar.txt -> {liste}")

    @staticmethod
    def bomba_listesi_oku() -> List[str]:
        """aktif_bombalar.txt dosyasını oku."""
        if Config.VPS_MODE:
            if Config.BOMBA_FILE.exists():
                return Config.BOMBA_FILE.read_text().strip().split(",")
            return []
        else:
            out = WindowsBridge.cmd(f'type "{Config.BOMBA_FILE_CMD}"')
            return [t.strip() for t in out.split(",") if t.strip()] if out else []

    @staticmethod
    def cs_dosyalari_kopyala(ticker_list: List[str]):
        """IQ .cs dosyalarını Windows'a kopyala."""
        if Config.VPS_MODE:
            Config.WIN_DEPLOY.mkdir(parents=True, exist_ok=True)
            for t in ticker_list:
                src = Config.IQ_DIR / f"BOMBA_{t}.cs"
                dst = Config.WIN_DEPLOY / f"BOMBA_{t}.cs"
                if src.exists():
                    shutil.copy2(src, dst)
        else:
            WindowsBridge.cmd(f'mkdir "{Config.WIN_DEPLOY_CMD}" 2>nul')
            for t in ticker_list:
                src = f'\\\\Mac\\Home\\adsız klasör\\borsa_surpriz\\matriks_iq\\BOMBA_{t}.cs'
                dst = f'{Config.WIN_DEPLOY_CMD}\\BOMBA_{t}.cs'
                WindowsBridge.cmd(f'copy "{src}" "{dst}" /Y')


# ============================================================
# PORTFÖY İZLEME
# ============================================================

class PortfolioTracker:
    """Portföy durumunu izle ve raporla."""

    @staticmethod
    def guncelle(aktif_hisseler: List[str]) -> Dict:
        """Aktif hisselerin güncel durumunu çek."""
        portfolio = {"tarih": datetime.now().isoformat(), "pozisyonlar": {}}
        for t in aktif_hisseler:
            try:
                df = yf.download(f"{t}.IS", period="5d", progress=False)
                if len(df) < 2:
                    continue
                close = df["Close"].squeeze()
                volume = df["Volume"].squeeze()
                gunluk = float((close.iloc[-1] / close.iloc[-2] - 1) * 100)
                rvol = float(volume.iloc[-1] / volume.iloc[:-1].mean()) if volume.iloc[:-1].mean() > 0 else 0

                portfolio["pozisyonlar"][t] = {
                    "fiyat": round(float(close.iloc[-1]), 2),
                    "gunluk_pct": round(gunluk, 2),
                    "rvol": round(rvol, 1),
                    "guncelleme": datetime.now().strftime("%H:%M"),
                }
            except Exception:
                continue

        try:
            with open(Config.PORTFOLIO_FILE, "w") as f:
                json.dump(portfolio, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return portfolio

    @staticmethod
    def ozet_mesaj(portfolio: Dict) -> str:
        """Telegram için kısa portföy özeti."""
        satirlar = ["📊 <b>Portföy Durumu</b>"]
        for t, v in portfolio.get("pozisyonlar", {}).items():
            emoji = "🟢" if v["gunluk_pct"] > 0 else "🔴" if v["gunluk_pct"] < 0 else "⚪"
            satirlar.append(
                f"  {emoji} {t}: {v['fiyat']} TL ({v['gunluk_pct']:+.1f}%) Vol:x{v['rvol']}")
        return "\n".join(satirlar)


# ============================================================
# STRATEJİ YÖNETİCİSİ
# ============================================================

class StrategyManager:
    """IQ robot stratejilerini yönetir."""

    @staticmethod
    def cs_uret(ticker: str, bomba_skor: int, atr_pct: float, fiyat: float) -> str:
        """Tek sembol robot kodu üret."""
        sablonu = (Config.IQ_DIR / "AKILLI_ROBOT_SABLONU.cs").read_text(encoding="utf-8")
        # MaxPositionValue'yu bomba skoruna göre ayarla
        if bomba_skor >= 60:
            max_pos = 10000
        elif bomba_skor >= 45:
            max_pos = 7000
        else:
            max_pos = 5000

        # Stop-loss'u ATR'ye göre ayarla
        stop = max(3.0, min(8.0, atr_pct * 1.5))

        kod = sablonu.replace("TICKER", ticker)
        kod = kod.replace("[Parameter(5000)]", f"[Parameter({max_pos})]")
        kod = kod.replace("[Parameter(6.0)]", f"[Parameter({stop:.1f})]")
        return kod

    @staticmethod
    def tumunu_uret(sonuclar: List[Dict]) -> List[str]:
        """Top sonuçlar için robot kodları üret + Windows'a kopyala."""
        uretilen = []
        for s in sonuclar:
            t = s["ticker"].replace(".IS", "")
            kod = StrategyManager.cs_uret(t, s["bomba_skor"], s["atr_pct"], s["fiyat"])
            dosya = Config.IQ_DIR / f"BOMBA_{t}.cs"
            dosya.write_text(kod, encoding="utf-8")
            uretilen.append(t)
        WindowsBridge.cs_dosyalari_kopyala(uretilen)
        return uretilen

    @staticmethod
    def tum_robotlari_uret():
        """Tüm BIST hisseleri için robot kodları üret (tek seferlik setup)."""
        log("🔧 Tüm robotlar üretiliyor...")
        sablonu = (Config.IQ_DIR / "AKILLI_ROBOT_SABLONU.cs").read_text(encoding="utf-8")
        sayac = 0
        for ticker_is in TICKERS:
            t = ticker_is.replace(".IS", "")
            kod = sablonu.replace("TICKER", t)
            dosya = Config.IQ_DIR / f"BOMBA_{t}.cs"
            dosya.write_text(kod, encoding="utf-8")
            sayac += 1
        log(f"  ✅ {sayac} robot kodu üretildi")

        # Hepsini Windows'a kopyala
        tum_tickerlar = [t.replace(".IS", "") for t in TICKERS]
        WindowsBridge.cs_dosyalari_kopyala(tum_tickerlar)
        log(f"  ✅ {sayac} dosya Windows'a kopyalandı")
        return sayac


# ============================================================
# TARAMA & ANALİZ MOTORU
# ============================================================

class ScanEngine:
    """ML + Teknik analiz tarama motoru."""

    @staticmethod
    def veri_cek(period: str = "6mo") -> Dict:
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

    @staticmethod
    def hisse_tara(veri: Dict, model, rejim) -> List[Dict]:
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

                sonuclar.append({
                    "ticker": ticker, "bomba_skor": b_skor,
                    "sebepler": b_sebepler,
                    "ml": analiz.get("ml_olasilik") or 0,
                    "teknik": analiz["teknik_skor"],
                    "fiyat": analiz["fiyat"],
                    "atr_pct": atr_pct,
                })
            except Exception:
                continue
        sonuclar.sort(key=lambda x: x["bomba_skor"], reverse=True)
        return sonuclar

    @staticmethod
    def rejim_analiz(xu_df) -> Optional[Dict]:
        if xu_df is not None and len(xu_df) > 50:
            return market_rejim_tespit(xu_df)
        return None


# ============================================================
# STATE YÖNETİMİ
# ============================================================

class State:
    @staticmethod
    def oku() -> Dict:
        if Config.STATE_FILE.exists():
            with open(Config.STATE_FILE) as f:
                return json.load(f)
        return {}

    @staticmethod
    def kaydet(data: Dict):
        with open(Config.STATE_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ============================================================
# ZAMANLI GÖREVLER
# ============================================================

def gorev_egitim():
    """05:30 — ML model eğit."""
    log("=" * 50)
    log("🧠 ML MODEL EĞİTİMİ")
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
        rejim = ScanEngine.rejim_analiz(xu)
        log(f"  {len(veri)} hisse (2 yil)")

        model = EnsembleModelV2()
        meta = model.egit(veri, market_rejim=rejim)
        if meta:
            log(f"  ✅ AUC:{meta['ensemble_auc']} F1:{meta['ensemble_f1']}")
            bildirim(f"🧠 ML guncellendi — AUC:{meta['ensemble_auc']}")
        else:
            log("  ❌ Egitim basarisiz", "ERROR")
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_tarama():
    """08:30 — Günün bombalarını bul."""
    log("=" * 50)
    log("🔥 SABAH BOMBA TARAMASI")
    try:
        model = EnsembleModelV2.yukle()
        if not model:
            log("  Model yok, egitim yapiliyor...")
            gorev_egitim()
            model = EnsembleModelV2.yukle()

        veri = ScanEngine.veri_cek("6mo")
        log(f"  {len(veri)} hisse")

        xu = veri.get("XU100.IS")
        rejim = ScanEngine.rejim_analiz(xu)
        if rejim:
            log(f"  Piyasa: {rejim['rejim'].upper()} ADX:{rejim['adx']}")

        sonuclar = ScanEngine.hisse_tara(veri, model, rejim)
        top = [s for s in sonuclar if s["bomba_skor"] >= Config.MIN_BOMBA_SKOR][:Config.MAX_BOMBA]

        if top:
            uretilen = StrategyManager.tumunu_uret(top)

            mesaj_satirlari = ["🔥 <b>Sabah Bomba Taramasi</b>"]
            for s in top:
                t = s["ticker"].replace(".IS", "")
                log(f"  💣 {t} Skor:{s['bomba_skor']} ML:{s['ml']*100:.0f}% Fiyat:{s['fiyat']:.2f}")
                mesaj_satirlari.append(
                    f"  💣 {t}: Skor {s['bomba_skor']} | ML %{s['ml']*100:.0f}")

            state = {
                "tarih": datetime.now().strftime("%Y-%m-%d"),
                "rejim": rejim,
                "bombalar": [
                    {"ticker": s["ticker"].replace(".IS", ""), "skor": s["bomba_skor"],
                     "ml": round(s["ml"], 3), "fiyat": s["fiyat"],
                     "atr_pct": round(s["atr_pct"], 2)}
                    for s in top
                ],
                "aktif_stratejiler": uretilen,
                "son_guncelleme": datetime.now().strftime("%H:%M"),
            }
            State.kaydet(state)
            WindowsBridge.bomba_listesi_yaz(uretilen)
            bildirim("\n".join(mesaj_satirlari))
        else:
            log("  ❌ Bugün bomba yok")
            WindowsBridge.bomba_listesi_yaz([])
            bildirim("📊 Bugün bomba hisse bulunamadı — piyasa zayıf.")

    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_iq_kontrol():
    """08:50 — IQ çalışıyor mu kontrol et."""
    log("🤖 IQ KONTROL")
    if not WindowsBridge.iq_calisiyor_mu():
        log("  ⚠ IQ kapali!", "WARN")
        bildirim("⚠️ MatriksIQ kapali! Kontrol et.")
    else:
        log("  ✅ IQ calisiyor")


def gorev_acilis():
    """09:35 — Açılış kontrolü."""
    log("📊 AÇILIŞ KONTROLÜ")
    try:
        state = State.oku()
        aktif = state.get("aktif_stratejiler", [])
        mesaj = ["📊 <b>Acilis Raporu</b>"]

        for t in aktif:
            try:
                df = yf.download(f"{t}.IS", period="5d", interval="5m", progress=False)
                if len(df) < 2:
                    continue
                close = df["Close"].squeeze()
                bugun = df[df.index.date == df.index.date[-1]]
                if len(bugun) > 0:
                    acilis = float(bugun["Open"].squeeze().iloc[0])
                    son = float(bugun["Close"].squeeze().iloc[-1])
                    dun_kapanis = float(close.iloc[-len(bugun)-1]) if len(close) > len(bugun) else acilis
                    gap = (acilis / dun_kapanis - 1) * 100

                    emoji = "🟢" if gap > 0.5 else "🔴" if gap < -0.5 else "⚪"
                    log(f"  {emoji} {t}: Gap {gap:+.1f}% | Son:{son:.2f}")
                    mesaj.append(f"  {emoji} {t}: Gap {gap:+.1f}%")

                    if abs(gap) > 3:
                        bildirim(f"🚨 {t} gap {gap:+.1f}%!")
            except Exception:
                continue

        xu = yf.download("XU100.IS", period="2d", interval="5m", progress=False)
        if len(xu) > 1:
            bugun_xu = xu[xu.index.date == xu.index.date[-1]]
            if len(bugun_xu) > 0:
                xu_son = float(bugun_xu["Close"].squeeze().iloc[-1])
                xu_acilis = float(bugun_xu["Open"].squeeze().iloc[0])
                xu_h = (xu_son / xu_acilis - 1) * 100
                mesaj.append(f"\n  XU100: {xu_son:.0f} ({xu_h:+.1f}%)")

        bildirim("\n".join(mesaj))
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_ogle():
    """12:00 — Öğlen hacim kontrolü + portföy durumu."""
    log("📊 ÖĞLEN KONTROLÜ")
    try:
        state = State.oku()
        aktif = state.get("aktif_stratejiler", [])
        portfolio = PortfolioTracker.guncelle(aktif)
        bildirim(PortfolioTracker.ozet_mesaj(portfolio))
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_strateji_guncelle():
    """12:15 — Daha iyi adaylar varsa güncelle."""
    log("🔄 STRATEJİ GÜNCELLEME")
    try:
        model = EnsembleModelV2.yukle()
        veri = ScanEngine.veri_cek("3mo")
        xu = veri.get("XU100.IS")
        rejim = ScanEngine.rejim_analiz(xu)

        state = State.oku()
        mevcut = state.get("aktif_stratejiler", [])

        sonuclar = ScanEngine.hisse_tara(veri, model, rejim)
        yeni_top = [s["ticker"].replace(".IS", "") for s in sonuclar
                    if s["bomba_skor"] >= Config.MIN_BOMBA_SKOR][:Config.MAX_BOMBA]

        eklenen = [t for t in yeni_top if t not in mevcut]
        cikan = [t for t in mevcut if t not in yeni_top]

        if eklenen:
            yeni_sonuc = [s for s in sonuclar if s["ticker"].replace(".IS", "") in eklenen]
            StrategyManager.tumunu_uret(yeni_sonuc)
            state["aktif_stratejiler"] = yeni_top
            state["son_guncelleme"] = datetime.now().strftime("%H:%M")
            State.kaydet(state)
            WindowsBridge.bomba_listesi_yaz(yeni_top)

            bildirim(f"🔄 Strateji guncellendi!\n  📈 Eklenen: {eklenen}\n  📉 Cikan: {cikan}")
        else:
            log("  ✅ Degisiklik yok")
    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_risk():
    """15:00 — İkindi risk kontrolü."""
    log("⚖️ İKİNDİ RİSK")
    try:
        xu = yf.download("XU100.IS", period="5d", progress=False)
        if len(xu) >= 2:
            close = xu["Close"].squeeze()
            gunluk = (close.iloc[-1] / close.iloc[-2] - 1) * 100
            log(f"  XU100: {close.iloc[-1]:.0f} ({gunluk:+.1f}%)")

            if gunluk < -3:
                bildirim(f"🚨 XU100 -%{abs(gunluk):.1f} — PANIK! Stratejileri kontrol et!")
            elif gunluk > 2:
                bildirim(f"🐂 XU100 +%{gunluk:.1f} — guzel gun!")

        # Portföy güncellemesi
        state = State.oku()
        aktif = state.get("aktif_stratejiler", [])
        portfolio = PortfolioTracker.guncelle(aktif)

        # IQ kontrol
        if WindowsBridge.iq_calisiyor_mu():
            log("  IQ: ✅ Calisiyor")
        else:
            log("  IQ: ❌ KAPALI!", "WARN")
            bildirim("⚠️ MatriksIQ kapanmis! Kontrol et.")

    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


def gorev_gun_sonu():
    """17:35 — Gün sonu rapor."""
    log("=" * 50)
    log("📝 GÜN SONU RAPORU")
    try:
        state = State.oku()
        aktif = state.get("aktif_stratejiler", [])
        portfolio = PortfolioTracker.guncelle(aktif)

        mesaj = [f"📝 <b>{datetime.now().strftime('%d.%m.%Y')} Gun Sonu</b>"]

        if state.get("rejim"):
            mesaj.append(f"Piyasa: {state['rejim'].get('rejim', '?').upper()}")

        for b in state.get("bombalar", []):
            t = b["ticker"]
            poz = portfolio.get("pozisyonlar", {}).get(t, {})
            fiyat = poz.get("fiyat", "?")
            pct = poz.get("gunluk_pct", 0)
            emoji = "🟢" if pct > 0 else "🔴" if pct < 0 else "⚪"
            mesaj.append(f"  {emoji} {t}: {fiyat} TL ({pct:+.1f}%) Skor:{b['skor']}")

        # Mevcut bomba listesi
        mevcut_liste = WindowsBridge.bomba_listesi_oku()
        mesaj.append(f"\nAktif liste: {', '.join(mevcut_liste)}")

        rapor = "\n".join(mesaj)
        log(rapor)
        bildirim(rapor)

        # Rapor dosyası
        rapor_path = Config.DATA_DIR / f"rapor_{datetime.now().strftime('%Y%m%d')}.txt"
        rapor_path.write_text(rapor, encoding="utf-8")

    except Exception as e:
        log(f"  HATA: {e}", "ERROR")


# ============================================================
# ANA SİSTEM
# ============================================================

def otonom_baslat():
    """Tam otonom sistemi başlat."""
    log("=" * 50)
    log("🤖 BIST ALPHA V3 — OTONOM MOTOR")
    log(f"  Mod: {'VPS' if Config.VPS_MODE else 'Mac + Parallels'}")
    log("=" * 50)

    s = Config.SCHEDULE
    schedule.every().day.at(s["egitim"]).do(gorev_egitim)
    schedule.every().day.at(s["tarama"]).do(gorev_tarama)
    schedule.every().day.at(s["iq_kontrol"]).do(gorev_iq_kontrol)
    schedule.every().day.at(s["acilis"]).do(gorev_acilis)
    schedule.every().day.at(s["ilk_yarim_saat"]).do(gorev_ogle)  # 10:00 de öğlen kontrolü yap
    schedule.every().day.at(s["ogle_kontrol"]).do(gorev_ogle)
    schedule.every().day.at(s["strateji_guncelle"]).do(gorev_strateji_guncelle)
    schedule.every().day.at(s["ikindi_risk"]).do(gorev_risk)
    schedule.every().day.at(s["gun_sonu"]).do(gorev_gun_sonu)

    log("\n📅 PROGRAM:")
    for isim, saat in s.items():
        log(f"  {saat} → {isim}")
    log("")

    bildirim("🤖 BIST Alpha V3 Motor baslatildi!")

    while True:
        schedule.run_pending()
        time.sleep(30)


def durum():
    """Mevcut durumu göster."""
    print("\n🔍 MOTOR V3 DURUMU")
    print("=" * 40)
    print(f"Mod: {'VPS' if Config.VPS_MODE else 'Mac + Parallels'}")
    print(f"IQ: {'✅ Calisiyor' if WindowsBridge.iq_calisiyor_mu() else '❌ Kapali'}")
    print(f"Bomba listesi: {WindowsBridge.bomba_listesi_oku()}")

    state = State.oku()
    if state:
        print(f"Tarih: {state.get('tarih', '?')}")
        r = state.get("rejim")
        if r:
            print(f"Rejim: {r.get('rejim', '?').upper()}")
        print(f"Stratejiler: {state.get('aktif_stratejiler', [])}")
        for b in state.get("bombalar", []):
            print(f"  💣 {b['ticker']}: Skor {b['skor']}, ML {b['ml']*100:.0f}%")


def telegram_test():
    """Telegram bağlantısını test et."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN ayarlanmamis!")
        print("  1. @BotFather'da yeni bot olustur")
        print("  2. Token'i Config.TELEGRAM_BOT_TOKEN'a yaz")
        print("  3. @userinfobot'a mesaj at, chat_id'ni al")
        print("  4. Config.TELEGRAM_CHAT_ID'ye yaz")
        return
    bildirim("🧪 Test mesaji — BIST Alpha V3 Motor calisiyor!")
    print("✅ Telegram mesaji gonderildi!")


if __name__ == "__main__":
    if "--simdi" in sys.argv:
        gorev_tarama()
    elif "--durum" in sys.argv:
        durum()
    elif "--telegram-test" in sys.argv:
        telegram_test()
    elif "--setup" in sys.argv:
        # Tüm robotları üret
        StrategyManager.tum_robotlari_uret()
    else:
        otonom_baslat()
