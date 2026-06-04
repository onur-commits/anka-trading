"""
Audit Log (Gün 5) — her hareket izlenebilir kayıt
==================================================
Append-only kayıt: kim, ne zaman, ne yaptı, detay. Güvenlik + işlem +
admin olayları. data/audit_log.json (atomik append, son N kayıt tutulur).
Güvenlik paneli için filtre/özet fonksiyonları.
"""
import json
import os
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
AUDIT = DATA / "audit_log.json"
MAX_KAYIT = 5000

# olay tipleri
LOGIN_OK = "LOGIN_OK"
LOGIN_FAIL = "LOGIN_FAIL"
OTP_FAIL = "OTP_FAIL"
LOCKOUT = "LOCKOUT"
RESET_TOKEN = "RESET_TOKEN"
PAROLA_DEGIS = "PAROLA_DEGIS"
ADMIN_AKSIYON = "ADMIN_AKSIYON"
TRADE = "TRADE"
AYAR_DEGIS = "AYAR_DEGIS"

GUVENLIK_OLAYLARI = {LOGIN_FAIL, OTP_FAIL, LOCKOUT, RESET_TOKEN}


def _oku():
    if AUDIT.exists():
        try:
            return json.loads(AUDIT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def kaydet(olay, kullanici="-", detay="", ip="-"):
    """Audit kaydı ekle (atomik)."""
    kayitlar = _oku()
    kayitlar.append({
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "olay": olay,
        "kullanici": kullanici,
        "ip": ip,
        "detay": str(detay)[:300],
    })
    kayitlar = kayitlar[-MAX_KAYIT:]
    DATA.mkdir(exist_ok=True)
    tmp = AUDIT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, AUDIT)


def listele(olay=None, kullanici=None, son=200):
    kayitlar = _oku()
    if olay:
        kayitlar = [k for k in kayitlar if k["olay"] == olay]
    if kullanici:
        kayitlar = [k for k in kayitlar if k["kullanici"] == kullanici]
    return kayitlar[-son:][::-1]  # en yeni üstte


def guvenlik_olaylari(son=200):
    return [k for k in _oku() if k["olay"] in GUVENLIK_OLAYLARI][-son:][::-1]


def ozet():
    kayitlar = _oku()
    sayac = {}
    for k in kayitlar:
        sayac[k["olay"]] = sayac.get(k["olay"], 0) + 1
    return {"toplam": len(kayitlar), "olay_dagilimi": sayac}


if __name__ == "__main__":
    print("=== AUDIT LOG MODÜLÜ ===")
    kaydet(LOGIN_OK, "admin", "demo giriş")
    kaydet(LOGIN_FAIL, "deneme", "yanlış parola")
    kaydet(TRADE, "trader", "ALIS THYAO x100")
    print("Özet:", ozet())
    print("Güvenlik olayları:", guvenlik_olaylari())
