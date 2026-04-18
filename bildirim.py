"""
ANKA Bildirim Sistemi — Telegram + Fallback Log
Kullanım:
    from bildirim import gonder
    gonder("ASELS stop-loss tetiklendi! -%5.2")

Telegram kurulumu:
    1. @BotFather'dan bot oluştur → token al
    2. Bot'a mesaj at, sonra https://api.telegram.org/bot<TOKEN>/getUpdates → chat_id al
    3. .env'ye ekle:
        TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
        TELEGRAM_CHAT_ID=987654321
"""

import os
import json
import logging
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("bildirim")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

BASE = os.path.dirname(os.path.abspath(__file__))
BILDIRIM_LOG = os.path.join(BASE, "logs", "bildirimler.json")


def _log_kaydet(mesaj: str, kanal: str):
    """Her bildirimi JSON log'a kaydet."""
    os.makedirs(os.path.dirname(BILDIRIM_LOG), exist_ok=True)
    kayitlar = []
    if os.path.exists(BILDIRIM_LOG):
        try:
            with open(BILDIRIM_LOG, "r", encoding="utf-8") as f:
                kayitlar = json.load(f)
        except Exception:
            kayitlar = []

    kayitlar.append({
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mesaj": mesaj,
        "kanal": kanal
    })

    # Son 500 kaydı tut
    kayitlar = kayitlar[-500:]
    with open(BILDIRIM_LOG, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)


def telegram_gonder(mesaj: str) -> bool:
    """Telegram'a mesaj gönder. Başarılıysa True."""
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        import urllib.request
        import ssl
        # VPS'te self-signed cert sorunu olabiliyor, SSL verify'ı atla
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": CHAT_ID,
            "text": f"🤖 ANKA\n{mesaj}",
            "parse_mode": "HTML"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return resp.status == 200
    except Exception as e:
        logger.warning(f"Telegram gönderim hatası: {e}")
        return False


def gonder(mesaj: str, oncelik: str = "normal"):
    """
    Ana bildirim fonksiyonu.
    oncelik: "normal", "onemli", "acil"
    """
    prefix = ""
    if oncelik == "onemli":
        prefix = "⚠️ "
    elif oncelik == "acil":
        prefix = "🚨 ACİL: "

    tam_mesaj = f"{prefix}{mesaj}"

    # Telegram
    tg_ok = telegram_gonder(tam_mesaj)
    kanal = "telegram" if tg_ok else "sadece_log"

    # Her zaman log'a yaz
    _log_kaydet(tam_mesaj, kanal)
    logger.info(f"[BİLDİRİM][{kanal}] {tam_mesaj}")

    return tg_ok


# Quick test
if __name__ == "__main__":
    if BOT_TOKEN and CHAT_ID:
        ok = gonder("Test bildirimi — ANKA bildirim sistemi aktif!", "normal")
        print(f"Telegram: {'OK' if ok else 'FAIL'}")
    else:
        print("TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID .env'de yok")
        print("Log'a yazılacak, Telegram atlanacak")
        gonder("Test — sadece log", "normal")
        print(f"Log: {BILDIRIM_LOG}")
