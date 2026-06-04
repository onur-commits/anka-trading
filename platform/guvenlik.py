"""
Güvenlik katmanı (Gün 4) — OTP/2FA, rate limit, lockout, reset token
=====================================================================
- TOTP (2FA): pyotp varsa gerçek, yoksa basit HMAC-zaman tabanlı fallback.
- Rate limit + lockout: ardışık hatalı girişte hesabı geçici kilitle.
- Reset token: tek kullanımlık, süreli parola sıfırlama jetonu.
- Parola politikası: uzunluk + karmaşıklık.

Durum dosyaları: data/guvenlik_state.json (lockout/token), in-memory hız.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
STATE = DATA / "guvenlik_state.json"

MAX_HATA = 5            # bu kadar hatadan sonra kilit
KILIT_SURE = 15 * 60   # 15 dakika
TOKEN_SURE = 30 * 60   # reset token 30 dakika

try:
    import pyotp
    _HAS_PYOTP = True
except ImportError:
    _HAS_PYOTP = False


def _oku():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"hata": {}, "kilit": {}, "token": {}, "totp": {}}


def _yaz(d):
    DATA.mkdir(exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)


# ── Parola politikası ──
def parola_politika_kontrol(parola):
    """(uygun: bool, sebepler: list)"""
    s = []
    if len(parola) < 10:
        s.append("En az 10 karakter")
    if not re.search(r"[A-Z]", parola):
        s.append("En az 1 büyük harf")
    if not re.search(r"[a-z]", parola):
        s.append("En az 1 küçük harf")
    if not re.search(r"[0-9]", parola):
        s.append("En az 1 rakam")
    if not re.search(r"[^A-Za-z0-9]", parola):
        s.append("En az 1 özel karakter")
    return (len(s) == 0), s


# ── Rate limit / lockout ──
def kilitli_mi(kullanici):
    d = _oku()
    kilit = d["kilit"].get(kullanici, 0)
    if kilit and time.time() < kilit:
        return True, int(kilit - time.time())
    return False, 0


def hata_kaydet(kullanici):
    d = _oku()
    n = d["hata"].get(kullanici, 0) + 1
    d["hata"][kullanici] = n
    if n >= MAX_HATA:
        d["kilit"][kullanici] = time.time() + KILIT_SURE
        d["hata"][kullanici] = 0
    _yaz(d)
    return n


def basari_sifirla(kullanici):
    d = _oku()
    d["hata"].pop(kullanici, None)
    d["kilit"].pop(kullanici, None)
    _yaz(d)


# ── Reset token ──
def reset_token_uret(kullanici):
    token = secrets.token_urlsafe(24)
    d = _oku()
    d["token"][hashlib.sha256(token.encode()).hexdigest()] = {
        "kullanici": kullanici, "bitis": time.time() + TOKEN_SURE}
    _yaz(d)
    return token  # gerçekte e-posta/SMS ile gönderilir


def reset_token_dogrula(token):
    h = hashlib.sha256(token.encode()).hexdigest()
    d = _oku()
    kayit = d["token"].get(h)
    if not kayit or time.time() > kayit["bitis"]:
        return None
    del d["token"][h]  # tek kullanımlık
    _yaz(d)
    return kayit["kullanici"]


# ── TOTP / 2FA ──
def totp_kur(kullanici):
    """Kullanıcı için TOTP secret üret (QR/uygulama için)."""
    if _HAS_PYOTP:
        sec = pyotp.random_base32()
    else:
        sec = secrets.token_hex(10)
    d = _oku()
    d["totp"][kullanici] = sec
    _yaz(d)
    return sec


def totp_uri(kullanici, secret):
    if _HAS_PYOTP:
        return pyotp.totp.TOTP(secret).provisioning_uri(kullanici, issuer_name="ANKA")
    return f"otpauth://totp/ANKA:{kullanici}?secret={secret}"


def _fallback_totp(secret, t=None):
    """pyotp yoksa: 30sn pencereli HMAC-SHA1 6 haneli kod."""
    t = int((t or time.time()) // 30)
    msg = t.to_bytes(8, "big")
    h = hmac.new(secret.encode(), msg, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    kod = (int.from_bytes(h[o:o+4], "big") & 0x7FFFFFFF) % 1_000_000
    return f"{kod:06d}"


def totp_dogrula(kullanici, kod):
    d = _oku()
    sec = d["totp"].get(kullanici)
    if not sec:
        return False
    if _HAS_PYOTP:
        return pyotp.TOTP(sec).verify(kod, valid_window=1)
    # fallback: şu an + bir önceki pencere
    return kod in (_fallback_totp(sec), _fallback_totp(sec, time.time() - 30))


if __name__ == "__main__":
    print("=== GÜVENLİK MODÜLÜ ===")
    print(f"pyotp: {_HAS_PYOTP} (yoksa HMAC fallback)")
    print("Parola 'abc':", parola_politika_kontrol("abc"))
    print("Parola 'Anka2026!ab':", parola_politika_kontrol("Anka2026!ab"))
    s = totp_kur("test")
    kod = _fallback_totp(s) if not _HAS_PYOTP else __import__("pyotp").TOTP(s).now()
    print("TOTP doğrula:", totp_dogrula("test", kod))
    tok = reset_token_uret("test")
    print("Reset token doğrula:", reset_token_dogrula(tok))
