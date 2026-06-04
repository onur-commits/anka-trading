"""
Auth katmanı (Gün 3) — login, bcrypt, rol tabanlı erişim
=========================================================
Kullanıcı deposu: data/users.json (parolalar HASH'li, asla düz metin).
Roller: admin > trader > viewer > readonly.
bcrypt varsa kullanır, yoksa pbkdf2 (hashlib) fallback — her ikisi güvenli.

Streamlit ile: auth.login_formu() çağır; başarılıysa st.session_state'e yazar.
"""
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
USERS_FILE = DATA / "users.json"

ROLLER = ["admin", "trader", "viewer", "readonly"]
ROL_YETKI = {  # her rol hangi işlemleri yapabilir
    "admin": {"trade", "view", "report", "admin", "settings"},
    "trader": {"trade", "view", "report"},
    "viewer": {"view", "report"},
    "readonly": {"view"},
}

# ── Parola hash (bcrypt varsa o, yoksa pbkdf2) ──
try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


def hash_parola(parola: str) -> str:
    if _HAS_BCRYPT:
        return "bcrypt$" + bcrypt.hashpw(parola.encode(), bcrypt.gensalt()).decode()
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", parola.encode(), salt.encode(), 200_000)
    return f"pbkdf2${salt}${dk.hex()}"


def dogrula_parola(parola: str, kayit: str) -> bool:
    try:
        if kayit.startswith("bcrypt$") and _HAS_BCRYPT:
            return bcrypt.checkpw(parola.encode(), kayit[7:].encode())
        if kayit.startswith("pbkdf2$"):
            _, salt, hexdk = kayit.split("$")
            dk = hashlib.pbkdf2_hmac("sha256", parola.encode(), salt.encode(), 200_000)
            return hmac.compare_digest(dk.hex(), hexdk)
    except Exception:
        return False
    return False


# ── Kullanıcı deposu ──
def _oku():
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _yaz(d):
    DATA.mkdir(exist_ok=True)
    tmp = USERS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, USERS_FILE)


def kullanici_ekle(kullanici, parola, rol="viewer", aktif=True):
    if rol not in ROLLER:
        raise ValueError(f"Geçersiz rol: {rol}")
    d = _oku()
    if kullanici in d:
        raise ValueError("Kullanıcı zaten var")
    d[kullanici] = {
        "parola_hash": hash_parola(parola),
        "rol": rol,
        "aktif": aktif,
        "olusturma": datetime.now().isoformat(timespec="seconds"),
        "son_giris": None,
    }
    _yaz(d)
    return True


def parola_degistir(kullanici, yeni_parola):
    d = _oku()
    if kullanici not in d:
        return False
    d[kullanici]["parola_hash"] = hash_parola(yeni_parola)
    _yaz(d)
    return True


def kullanici_sil(kullanici):
    d = _oku()
    if kullanici in d:
        del d[kullanici]
        _yaz(d)
        return True
    return False


def rol_degistir(kullanici, yeni_rol):
    if yeni_rol not in ROLLER:
        return False
    d = _oku()
    if kullanici not in d:
        return False
    d[kullanici]["rol"] = yeni_rol
    _yaz(d)
    return True


def aktif_yap(kullanici, aktif=True):
    d = _oku()
    if kullanici in d:
        d[kullanici]["aktif"] = aktif
        _yaz(d)
        return True
    return False


def giris(kullanici, parola):
    """(başarı: bool, mesaj: str, rol: str|None)"""
    d = _oku()
    u = d.get(kullanici)
    if not u:
        return False, "Kullanıcı bulunamadı", None
    if not u.get("aktif", True):
        return False, "Hesap pasif", None
    if not dogrula_parola(parola, u["parola_hash"]):
        return False, "Parola yanlış", None
    u["son_giris"] = datetime.now().isoformat(timespec="seconds")
    _yaz(d)
    return True, "Giriş başarılı", u["rol"]


def yetkili_mi(rol, islem):
    return islem in ROL_YETKI.get(rol, set())


def ilk_admin_olustur():
    """Hiç kullanıcı yoksa varsayılan admin (parola env'den veya rastgele)."""
    if _oku():
        return None
    parola = os.environ.get("ANKA_ADMIN_PASS") or secrets.token_urlsafe(12)
    kullanici_ekle("admin", parola, rol="admin")
    return parola


if __name__ == "__main__":
    print("=== AUTH MODÜLÜ ===")
    print(f"bcrypt: {_HAS_BCRYPT} (yoksa pbkdf2 fallback)")
    p = ilk_admin_olustur()
    if p:
        print(f"İlk admin oluşturuldu — parola: {p}")
    print("Test giriş:", giris("admin", p or "yanlis"))
    print("Yetki (admin, trade):", yetkili_mi("admin", "trade"))
    print("Yetki (readonly, trade):", yetkili_mi("readonly", "trade"))
