"""
Yönetim Paneli (Gün 7) — Admin + Güvenlik + Auth UI
====================================================
Rol bazlı: sadece admin görür. Kullanıcı CRUD, rol değiştir, aktif/pasif,
parola reset, audit/güvenlik log görüntüleme.

NOT: paket branch — canlı bota dokunmaz. 'birleştir' ile main'e gelir.
"""
import sys
from pathlib import Path

import streamlit as st

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

st.set_page_config(page_title="ANKA Yönetim", page_icon="🔐", layout="wide")

try:
    from platform import auth, audit, guvenlik
except Exception as e:
    st.error(f"Platform modülleri yüklenemedi: {e}")
    st.stop()

st.markdown("# 🔐 Yönetim Paneli")

# ── Basit oturum (gerçekte ana app auth'u taşır) ──
if "rol" not in st.session_state:
    st.session_state.rol = None
    st.session_state.kullanici = None

if not st.session_state.rol:
    st.subheader("Giriş")
    # İlk kurulumda admin oluştur
    parola_ilk = auth.ilk_admin_olustur()
    if parola_ilk:
        st.warning(f"İlk admin oluşturuldu. Kullanıcı: **admin** · Parola: `{parola_ilk}` (kaydet!)")
    k = st.text_input("Kullanıcı")
    p = st.text_input("Parola", type="password")
    if st.button("Giriş"):
        kilit, kalan = guvenlik.kilitli_mi(k)
        if kilit:
            st.error(f"Hesap kilitli — {kalan//60} dk kaldı")
            audit.kaydet(audit.LOCKOUT, k)
        else:
            ok, mesaj, rol = auth.giris(k, p)
            if ok:
                st.session_state.rol = rol
                st.session_state.kullanici = k
                guvenlik.basari_sifirla(k)
                audit.kaydet(audit.LOGIN_OK, k)
                st.rerun()
            else:
                n = guvenlik.hata_kaydet(k)
                audit.kaydet(audit.LOGIN_FAIL, k, mesaj)
                st.error(f"{mesaj} (deneme {n}/{guvenlik.MAX_HATA})")
    st.stop()

# ── Giriş yapıldı ──
st.caption(f"Giriş: **{st.session_state.kullanici}** ({st.session_state.rol})")
if st.button("Çıkış"):
    st.session_state.rol = None
    st.rerun()

if not auth.yetkili_mi(st.session_state.rol, "admin"):
    st.error("Bu panel sadece admin rolüne açık.")
    st.stop()

sekme = st.tabs(["👥 Kullanıcılar", "🛡️ Güvenlik Log", "📋 Audit"])

with sekme[0]:
    st.subheader("Kullanıcı ekle")
    c = st.columns(4)
    yk = c[0].text_input("Kullanıcı adı")
    yp = c[1].text_input("Parola", type="password", key="yeni_p")
    yr = c[2].selectbox("Rol", auth.ROLLER)
    if c[3].button("Ekle"):
        uygun, sebep = guvenlik.parola_politika_kontrol(yp)
        if not uygun:
            st.error("Parola zayıf: " + ", ".join(sebep))
        else:
            try:
                auth.kullanici_ekle(yk, yp, yr)
                audit.kaydet(audit.ADMIN_AKSIYON, st.session_state.kullanici, f"kullanıcı ekle: {yk}")
                st.success(f"{yk} eklendi")
            except Exception as e:
                st.error(str(e))

    st.divider()
    st.subheader("Mevcut kullanıcılar")
    import json as _j
    uf = BASE / "data" / "users.json"
    kullanicilar = _j.loads(uf.read_text(encoding="utf-8")) if uf.exists() else {}
    for ad, bilgi in kullanicilar.items():
        cc = st.columns([2, 1, 1, 1, 1])
        cc[0].write(f"**{ad}**")
        cc[1].write(bilgi["rol"])
        cc[2].write("🟢" if bilgi.get("aktif") else "🔴")
        if cc[3].button("Pasif/Aktif", key=f"akt_{ad}"):
            auth.aktif_yap(ad, not bilgi.get("aktif"))
            st.rerun()
        if cc[4].button("Sil", key=f"sil_{ad}"):
            auth.kullanici_sil(ad)
            audit.kaydet(audit.ADMIN_AKSIYON, st.session_state.kullanici, f"sil: {ad}")
            st.rerun()

with sekme[1]:
    st.subheader("Güvenlik olayları")
    st.dataframe(guvenlik_log := audit.guvenlik_olaylari(), use_container_width=True)

with sekme[2]:
    st.subheader("Tüm audit kaydı")
    st.json(audit.ozet())
    st.dataframe(audit.listele(son=300), use_container_width=True)
