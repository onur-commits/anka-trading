"""
BIST Sürpriz Bulucu - Otomatik Trading Bot
- Periyodik tarama (her X dakikada)
- Sinyal tespiti (sürpriz skoru eşik kontrolü)
- Bildirim sistemi (iMessage, Telegram, ses, dosya log)
- Opsiyonel: Matriks Web Trader entegrasyonu
"""

import time
import json
import subprocess
import threading
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict

# Proje modülleri
from veri_isleyici import tum_verileri_cek, BIST_TICKERS, ticker_isim
from tahmin_motoru import (
    feature_olustur, teknik_skor_hesapla, teknik_sinyal_detay,
    model_egit, model_yukle, ml_tahmin, birlesik_skor_hesapla,
    hisse_analiz
)

# ============================================================
# YAPILANDIRMA
# ============================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
CONFIG_PATH = DATA_DIR / "bot_config.json"
SINYAL_LOG_PATH = LOG_DIR / "sinyaller.json"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("BistBot")


@dataclass
class BotConfig:
    """Bot yapılandırması."""
    # Tarama
    tarama_araligi_dk: int = 15          # Kaç dakikada bir tara
    gun_sayisi: int = 120                 # Geçmiş veri gün sayısı
    tickers: list = field(default_factory=lambda: BIST_TICKERS.copy())

    # Sinyal eşikleri
    min_surpriz_skor: float = 65.0        # Bu skorun üstü = sinyal
    min_teknik_skor: float = 60.0         # Teknik skor alt limiti
    min_ml_olasilik: float = 0.6          # ML olasılık alt limiti
    hacim_carpan_esik: float = 2.0        # Hacim ortalamanın kaç katı?

    # Bildirim
    bildirim_imessage: bool = True        # iMessage ile bildirim
    imessage_numara: str = ""             # Telefon numarası veya email
    bildirim_telegram: bool = False       # Telegram ile bildirim
    telegram_token: str = ""              # Telegram bot token
    telegram_chat_id: str = ""            # Telegram chat ID
    bildirim_ses: bool = True             # macOS ses bildirimi
    bildirim_dosya: bool = True           # Dosyaya log

    # Matriks entegrasyonu
    matriks_aktif: bool = False
    matriks_user: str = ""
    matriks_pass: str = ""

    # Bot durumu
    aktif: bool = False
    son_tarama: str = ""
    toplam_tarama: int = 0
    toplam_sinyal: int = 0

    def kaydet(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def yukle(cls):
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()


# ============================================================
# BİLDİRİM SİSTEMİ
# ============================================================

class BildirimYoneticisi:
    """Çoklu kanal bildirim sistemi."""

    def __init__(self, config: BotConfig):
        self.config = config

    def gonder(self, mesaj: str, oncelik: str = "normal"):
        """Tüm aktif kanallara bildirim gönderir."""
        baslik = "🚨 BIST SÜRPRIZ" if oncelik == "yuksek" else "📊 BIST Bot"
        tam_mesaj = f"{baslik}\n{mesaj}"

        sonuclar = {}

        if self.config.bildirim_ses:
            sonuclar["ses"] = self._ses_bildirim(tam_mesaj)

        if self.config.bildirim_imessage and self.config.imessage_numara:
            sonuclar["imessage"] = self._imessage_gonder(tam_mesaj)

        if self.config.bildirim_telegram and self.config.telegram_token:
            sonuclar["telegram"] = self._telegram_gonder(tam_mesaj)

        if self.config.bildirim_dosya:
            sonuclar["dosya"] = self._dosya_log(tam_mesaj)

        # macOS notification center
        sonuclar["macos"] = self._macos_bildirim(baslik, mesaj)

        return sonuclar

    def _ses_bildirim(self, mesaj):
        """macOS ses bildirimi."""
        try:
            # Sistem sesi
            subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
            # TTS ile mesaj okuma (kısa versiyon)
            kisa = mesaj[:100]
            subprocess.run(["say", "-v", "Yelda", kisa], check=False, timeout=10)
            return True
        except Exception as e:
            log.warning(f"Ses hatası: {e}")
            return False

    def _macos_bildirim(self, baslik, mesaj):
        """macOS Notification Center bildirimi."""
        try:
            script = f'''display notification "{mesaj[:200]}" with title "{baslik}" sound name "Glass"'''
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
            return True
        except Exception as e:
            log.warning(f"macOS bildirim hatası: {e}")
            return False

    def _imessage_gonder(self, mesaj):
        """iMessage ile bildirim gönderir."""
        try:
            numara = self.config.imessage_numara
            script = f'''
            tell application "Messages"
                set targetService to 1st account whose service type = iMessage
                set targetBuddy to participant "{numara}" of targetService
                send "{mesaj}" to targetBuddy
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                log.info(f"iMessage gönderildi: {numara}")
                return True
            else:
                log.warning(f"iMessage hatası: {result.stderr}")
                return False
        except Exception as e:
            log.warning(f"iMessage hatası: {e}")
            return False

    def _telegram_gonder(self, mesaj):
        """Telegram bot ile bildirim gönderir."""
        try:
            import urllib.request
            import urllib.parse

            token = self.config.telegram_token
            chat_id = self.config.telegram_chat_id
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": mesaj,
                "parse_mode": "HTML"
            }).encode()

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
                if result.get("ok"):
                    log.info("Telegram gönderildi")
                    return True

            return False
        except Exception as e:
            log.warning(f"Telegram hatası: {e}")
            return False

    def _dosya_log(self, mesaj):
        """Sinyal log dosyasına yazar."""
        try:
            kayit = {
                "zaman": datetime.now().isoformat(),
                "mesaj": mesaj
            }
            # Mevcut logları oku
            loglar = []
            if SINYAL_LOG_PATH.exists():
                with open(SINYAL_LOG_PATH, "r", encoding="utf-8") as f:
                    loglar = json.load(f)

            loglar.append(kayit)
            # Son 500 kaydı tut
            loglar = loglar[-500:]

            with open(SINYAL_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(loglar, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            log.warning(f"Dosya log hatası: {e}")
            return False


# ============================================================
# TARAMA MOTORU
# ============================================================

class TaramaMotoru:
    """Periyodik hisse tarama ve sinyal tespiti."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.bildirim = BildirimYoneticisi(config)
        self.ml_model = model_yukle()
        self.son_sinyaller = {}  # Tekrar bildirim önleme
        self.veriler = None

    def veri_cek(self):
        """Tüm hisse verilerini çeker."""
        log.info(f"Veri çekiliyor... ({len(self.config.tickers)} hisse)")
        self.veriler = tum_verileri_cek(
            tickers=self.config.tickers,
            gun=self.config.gun_sayisi
        )
        log.info(f"{len(self.veriler)} hisse verisi alındı")
        return self.veriler

    def model_guncelle(self):
        """ML modelini günceller veya yükler."""
        if self.veriler and len(self.veriler) > 10:
            log.info("ML modeli eğitiliyor...")
            bilgi = model_egit(self.veriler)
            if bilgi:
                self.ml_model = bilgi["model"]
                log.info(f"Model güncellendi (Doğruluk: %{bilgi['dogruluk']*100:.1f})")
        elif self.ml_model is None:
            self.ml_model = model_yukle()

    def tara(self):
        """Tüm hisseleri tarar ve sinyalleri tespit eder."""
        if not self.veriler:
            self.veri_cek()

        if not self.veriler:
            log.error("Veri çekilemedi, tarama iptal")
            return []

        log.info("Hisseler taranıyor...")
        sonuclar = []

        for ticker, df in self.veriler.items():
            analiz = hisse_analiz(ticker, df, self.ml_model)
            if analiz:
                sonuclar.append(analiz)

        # Skora göre sırala
        sonuclar.sort(key=lambda x: x["birlesik_skor"], reverse=True)

        # Sinyalleri filtrele
        sinyaller = self._sinyal_filtrele(sonuclar)

        self.config.son_tarama = datetime.now().isoformat()
        self.config.toplam_tarama += 1
        self.config.toplam_sinyal += len(sinyaller)
        self.config.kaydet()

        return sinyaller

    def _sinyal_filtrele(self, sonuclar):
        """Eşik değerlerine göre sinyalleri filtreler."""
        sinyaller = []

        for s in sonuclar:
            # Ana eşik: birleşik skor
            if s["birlesik_skor"] < self.config.min_surpriz_skor:
                continue

            # Ek filtreler
            if s["teknik_skor"] < self.config.min_teknik_skor:
                continue

            if s["ml_olasilik"] and s["ml_olasilik"] < self.config.min_ml_olasilik:
                continue

            sinyaller.append(s)

        return sinyaller

    def sinyal_bildirim_gonder(self, sinyaller):
        """Tespit edilen sinyaller için bildirim gönderir."""
        if not sinyaller:
            return

        simdi = datetime.now()

        for s in sinyaller:
            ticker = s["ticker"]
            kod = ticker.replace(".IS", "")

            # Son 1 saat içinde aynı hisse için bildirim gönderilmiş mi?
            son = self.son_sinyaller.get(ticker)
            if son and (simdi - son) < timedelta(hours=1):
                continue

            # Mesaj oluştur
            yon_emoji = ""
            if s["sinyaller"]:
                yukari = sum(1 for _, _, y in s["sinyaller"] if y == "yukari")
                asagi = sum(1 for _, _, y in s["sinyaller"] if y == "asagi")
                if yukari > asagi:
                    yon_emoji = "🟢 YUKARI"
                elif asagi > yukari:
                    yon_emoji = "🔴 ASAGI"
                else:
                    yon_emoji = "🟡 BELIRSIZ"

            sinyal_listesi = "\n".join([
                f"  • {ad}: {detay}" for ad, detay, _ in s["sinyaller"]
            ]) if s["sinyaller"] else "  Genel skor yüksek"

            mesaj = (
                f"\n{'='*30}\n"
                f"💎 {kod} - {ticker_isim(ticker)}\n"
                f"📊 Sürpriz Skoru: {s['birlesik_skor']:.0f}/100\n"
                f"📈 Fiyat: {s['fiyat']:.2f} TL ({s['gunluk_degisim']:+.2f}%)\n"
                f"🔬 Teknik: {s['teknik_skor']:.0f} | ML: %{(s['ml_olasilik'] or 0)*100:.0f}\n"
                f"🎯 Yön: {yon_emoji}\n"
                f"📋 Sinyaller:\n{sinyal_listesi}\n"
                f"⏰ {simdi.strftime('%H:%M:%S')}\n"
                f"{'='*30}"
            )

            oncelik = "yuksek" if s["birlesik_skor"] > 80 else "normal"
            self.bildirim.gonder(mesaj, oncelik)
            self.son_sinyaller[ticker] = simdi
            log.info(f"SİNYAL: {kod} skor={s['birlesik_skor']:.0f}")

    def tam_tarama(self):
        """Tam döngü: veri çek → model güncelle → tara → bildir."""
        log.info(f"{'='*50}")
        log.info(f"TAM TARAMA BAŞLADI - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"{'='*50}")

        try:
            # 1. Veri çek
            self.veri_cek()

            # 2. Model güncelle (her 10 taramada bir)
            if self.config.toplam_tarama % 10 == 0:
                self.model_guncelle()

            # 3. Tara
            sinyaller = self.tara()

            # 4. Bildir
            if sinyaller:
                log.info(f"🎯 {len(sinyaller)} sinyal tespit edildi!")
                self.sinyal_bildirim_gonder(sinyaller)

                # Özet bildirim
                ozet = (
                    f"\n📊 Tarama Özeti\n"
                    f"Taranan: {len(self.veriler)} hisse\n"
                    f"Sinyal: {len(sinyaller)} hisse\n"
                    f"En yüksek: {sinyaller[0]['ticker'].replace('.IS', '')} "
                    f"({sinyaller[0]['birlesik_skor']:.0f})\n"
                    f"Saat: {datetime.now().strftime('%H:%M')}"
                )
                self.bildirim.gonder(ozet)
            else:
                log.info("Sinyal yok — eşik değerlerini geçen hisse bulunamadı")

            return sinyaller

        except Exception as e:
            log.error(f"Tarama hatası: {e}", exc_info=True)
            self.bildirim.gonder(f"⚠️ Bot hatası: {str(e)[:100]}")
            return []


# ============================================================
# BOT ANA DÖNGÜSÜ
# ============================================================

class BistBot:
    """Ana bot sınıfı — periyodik tarama döngüsü."""

    def __init__(self, config: BotConfig = None):
        self.config = config or BotConfig.yukle()
        self.motor = TaramaMotoru(self.config)
        self._thread = None
        self._durdur = threading.Event()

    def baslat(self):
        """Botu başlatır."""
        if self._thread and self._thread.is_alive():
            log.warning("Bot zaten çalışıyor")
            return

        self.config.aktif = True
        self.config.kaydet()
        self._durdur.clear()

        log.info(f"🤖 BIST Sürpriz Bot başlatıldı!")
        log.info(f"   Tarama aralığı: {self.config.tarama_araligi_dk} dk")
        log.info(f"   Min sürpriz skor: {self.config.min_surpriz_skor}")
        log.info(f"   Hisse sayısı: {len(self.config.tickers)}")

        self.motor.bildirim.gonder(
            f"🤖 Bot başlatıldı!\n"
            f"Aralık: {self.config.tarama_araligi_dk} dk\n"
            f"Eşik: {self.config.min_surpriz_skor}\n"
            f"Hisse: {len(self.config.tickers)}"
        )

        self._thread = threading.Thread(target=self._dongu, daemon=True)
        self._thread.start()

    def durdur(self):
        """Botu durdurur."""
        self._durdur.set()
        self.config.aktif = False
        self.config.kaydet()
        log.info("🛑 Bot durduruldu")
        self.motor.bildirim.gonder("🛑 Bot durduruldu")

    def tek_tarama(self):
        """Tek seferlik tarama yapar (bot döngüsü dışında)."""
        return self.motor.tam_tarama()

    def _dongu(self):
        """Bot ana döngüsü."""
        while not self._durdur.is_set():
            try:
                self.motor.tam_tarama()
            except Exception as e:
                log.error(f"Döngü hatası: {e}", exc_info=True)

            # Sonraki taramaya kadar bekle
            bekleme_sn = self.config.tarama_araligi_dk * 60
            log.info(f"Sonraki tarama: {self.config.tarama_araligi_dk} dk sonra")
            self._durdur.wait(bekleme_sn)

    @property
    def calisiyor(self):
        return self._thread is not None and self._thread.is_alive()


# ============================================================
# SINYAL GEÇMİŞİ
# ============================================================

def sinyal_gecmisi_oku():
    """Geçmiş sinyal loglarını okur."""
    if SINYAL_LOG_PATH.exists():
        with open(SINYAL_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def sinyal_gecmisi_temizle():
    """Sinyal geçmişini temizler."""
    if SINYAL_LOG_PATH.exists():
        SINYAL_LOG_PATH.unlink()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("  BIST Sürpriz Bulucu - Trading Bot")
    print("=" * 50)

    config = BotConfig.yukle()

    if "--tek" in sys.argv:
        # Tek tarama
        print("\nTek seferlik tarama...")
        bot = BistBot(config)
        sinyaller = bot.tek_tarama()
        if sinyaller:
            print(f"\n{'='*50}")
            print(f"  {len(sinyaller)} SİNYAL TESPİT EDİLDİ!")
            print(f"{'='*50}")
            for s in sinyaller:
                kod = s["ticker"].replace(".IS", "")
                print(f"  {kod}: Skor={s['birlesik_skor']:.0f} Fiyat={s['fiyat']:.2f}")
        else:
            print("\nSinyal bulunamadı.")

    elif "--bot" in sys.argv:
        # Sürekli bot
        print(f"\nBot başlatılıyor (her {config.tarama_araligi_dk} dk)...")
        print("Durdurmak için Ctrl+C\n")

        bot = BistBot(config)
        bot.baslat()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            bot.durdur()
            print("\nBot durduruldu.")

    else:
        print("\nKullanım:")
        print("  python bot.py --tek     Tek seferlik tarama")
        print("  python bot.py --bot     Sürekli bot modu")
        print(f"\nMevcut ayarlar:")
        print(f"  Aralık: {config.tarama_araligi_dk} dk")
        print(f"  Eşik: {config.min_surpriz_skor}")
        print(f"  iMessage: {'Aktif' if config.bildirim_imessage else 'Kapalı'}")
        print(f"  Telegram: {'Aktif' if config.bildirim_telegram else 'Kapalı'}")
