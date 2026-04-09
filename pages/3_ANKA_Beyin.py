"""
ANKA Beyin Dashboard — Canlı Kontrol Merkezi
=============================================
- Bot modları (agresif/defans/nakit)
- 4 katmanlı rejim sensörü
- Karar gerekçeleri
- Öğrenme logu
- Karakter uyum raporu
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
sys.path.insert(0, str(BASE_DIR))

st.set_page_config(page_title="ANKA Beyin", page_icon="🧠", layout="wide")

# ============================================================
# VERI YUKLE
# ============================================================

def yukle(dosya, varsayilan={}):
    yol = DATA_DIR / dosya
    if yol.exists():
        try:
            with open(yol, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return varsayilan


beyin = yukle("beyin_state.json")
hafiza = yukle("beyin_hafiza.json", {"islemler": [], "dersler": [], "istatistik": {}})
rotasyon = yukle("rotasyon_state.json", {"pozisyonlar": {}})
bomba = yukle("gunluk_bomba.json", {"bombalar": []})
rejim_gecisler = yukle("rejim_gecisleri.json", [])

# ============================================================
# UST PANEL — SURUNUN RUH HALI
# ============================================================

st.title("🧠 ANKA Beyin — Kontrol Merkezi")

rejim_data = beyin.get("rejim", {})
katmanlar = beyin.get("katmanlar", {})

# Rejim banner
rejim_ad = rejim_data.get("rejim", "BILINMIYOR")
strateji = rejim_data.get("strateji", "?")
agresiflik = rejim_data.get("agresiflik", 0)

rejim_renk = {
    "ALTIN_CAGI": "🟢", "BOGA_KOSUSU": "🟢", "FIRSAT_DALGASI": "🟡",
    "UYKU_MODU": "🔵", "SIKISMA": "🟡", "TESTERE": "🟠",
    "AYI_PIYASASI": "🔴", "KAOS": "🔴",
}.get(rejim_ad, "⚪")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Rejim", f"{rejim_renk} {rejim_ad}")
col2.metric("Strateji", strateji.replace("_", " ").title())
col3.metric("Agresiflik", f"{agresiflik:.0%}")
col4.metric("Son Guncelleme", beyin.get("zaman", "?")[:16])

st.divider()

# ============================================================
# BOT MODLARI
# ============================================================

st.subheader("🤖 Bot Modları")

pozlar = rotasyon.get("pozisyonlar", {})

if pozlar:
    agresif = 0
    defans = 0
    nakit_bot = 0

    bot_data = []
    for ticker, poz in pozlar.items():
        karakter_uyum = beyin.get("karakter_uyum", [])
        uyum = next((u for u in karakter_uyum if u.get("ticker") == ticker), {})

        if agresiflik >= 0.6:
            mod = "AGRESIF"
            agresif += 1
        elif agresiflik >= 0.3:
            mod = "NORMAL"
        else:
            mod = "DEFANS"
            defans += 1

        bot_data.append({
            "Bot": f"🤖 {ticker}",
            "Mod": mod,
            "Karakter": uyum.get("karakter", "?"),
            "Uyum": "✅" if uyum.get("uyumlu") else "❌",
            "Beta": uyum.get("beta", "?"),
            "ATR%": uyum.get("atr_pct", "?"),
            "Mevsim": f"x{uyum.get('mevsim', 1.0)}",
            "Oneri": uyum.get("oneri", "?"),
            "Adet": poz.get("adet", 0),
            "Giris": poz.get("giris_fiyat", 0),
        })

    nakit_bot = 5 - len(pozlar)

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Agresif/Alimda", f"{len(pozlar)} bot", delta="AKTIF")
    mc2.metric("Defansta", f"{defans} bot")
    mc3.metric("Nakit/Beklemede", f"{nakit_bot} slot bos")

    st.dataframe(pd.DataFrame(bot_data), use_container_width=True, hide_index=True)
else:
    st.info("Aktif bot yok")

st.divider()

# ============================================================
# 4 KATMAN SENSOR
# ============================================================

st.subheader("📊 4 Katmanlı Rejim Sensörü")

k1, k2, k3, k4 = st.columns(4)

trend = katmanlar.get("trend", {})
vol = katmanlar.get("volatilite", {})
lik = katmanlar.get("likidite", {})
duygu = katmanlar.get("duygu", {})

with k1:
    st.markdown("**Katman 1: Trend**")
    skor = trend.get("skor", 50)
    bar = "🟢" if skor >= 60 else ("🟡" if skor >= 40 else "🔴")
    st.markdown(f"### {bar} {skor}/100")
    st.caption(f"ADX: {trend.get('adx', '?')} | {trend.get('yon', '?')}")
    st.caption(f"Momentum 20g: {trend.get('momentum_20g', '?')}%")

with k2:
    st.markdown("**Katman 2: Volatilite**")
    seviye = vol.get("seviye", "?")
    bar = {"dusuk": "🟢", "normal": "🟡", "yuksek": "🟠", "asiri": "🔴"}.get(seviye, "⚪")
    st.markdown(f"### {bar} {seviye.upper()}")
    st.caption(f"ATR: %{vol.get('atr_pct', '?')} | Yillik: %{vol.get('annual_vol', '?')}")
    st.caption(f"HAR-RV: {vol.get('har_rv', '?')}")

with k3:
    st.markdown("**Katman 3: Likidite**")
    durum = lik.get("durum", "?")
    bar = {"cok_yuksek": "🟢", "yuksek": "🟢", "normal": "🟡", "dusuk": "🟠", "kurak": "🔴"}.get(durum, "⚪")
    st.markdown(f"### {bar} {durum.upper()}")
    st.caption(f"RVOL: x{lik.get('rvol', '?')}")
    st.caption(f"Hacim artis: {lik.get('hacim_artis_gun', '?')}/5 gun")

with k4:
    st.markdown("**Katman 4: Duygu**")
    duygu_ad = duygu.get("duygu", "?")
    bar = {"acgozlu": "🟢", "iyimser": "🟢", "notr": "🟡", "tedirgin": "🟠", "korku": "🔴"}.get(duygu_ad, "⚪")
    st.markdown(f"### {bar} {duygu_ad.upper()}")
    for d in duygu.get("detaylar", [])[:3]:
        st.caption(f"• {d}")

st.divider()

# ============================================================
# KARAR GEREKCESI (Brain Dump)
# ============================================================

st.subheader("💡 Karar Gerekçesi")

if rejim_ad and strateji:
    st.success(f"""
    **Rejim:** {rejim_ad} → **Strateji:** {strateji}

    **Neden bu strateji?**
    - Trend: {trend.get('detay', '?')}
    - Volatilite: {vol.get('detay', '?')}
    - Likidite: {lik.get('detay', '?')}
    - Duygu: {duygu.get('duygu', '?').upper()} (skor: {duygu.get('skor', '?')})
    - Agresiflik %{agresiflik:.0%} — {'Tam gaz' if agresiflik > 0.7 else 'Temkinli' if agresiflik > 0.4 else 'Savunma modu'}
    """)

# Son islemler ve gerekceler
son_islemler = hafiza.get("islemler", [])[-5:]
if son_islemler:
    st.markdown("**Son İşlemler ve Gerekçeleri:**")
    for islem in reversed(son_islemler):
        yon_emoji = "🟢 ALIŞ" if islem.get("yon") == "AL" else "🔴 SATIŞ"
        sonuc = islem.get("sonuc", {})
        kar = sonuc.get("kar", "?") if sonuc else "beklemede"
        st.markdown(f"""
        > {islem.get('zaman', '?')} | {yon_emoji} **{islem.get('ticker', '?')}** {islem.get('adet', '?')} lot @ {islem.get('fiyat', '?')} TL
        > 📋 **Neden:** {islem.get('sebep', 'Belirtilmedi')}
        > 📊 **Rejim:** {islem.get('rejim', '?')} | **Sonuç:** {kar}
        """)
else:
    st.info("Henuz islem gecmisi yok — bot calismaya basladiginda burada gorunecek")

st.divider()

# ============================================================
# OGRENME LOGU (Akan Serit)
# ============================================================

st.subheader("📚 Öğrenme Logu — Bebeğin Bugün Öğrendikleri")

dersler = hafiza.get("dersler", [])
stats = hafiza.get("istatistik", {})

if stats:
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("Toplam İşlem", stats.get("toplam_islem", 0))
    o2.metric("Kazanç", stats.get("toplam_kazanc", 0))
    o3.metric("Kayıp", stats.get("toplam_kayip", 0))
    o4.metric("Win Rate", f"%{stats.get('win_rate', 0)}")

ogrenme = beyin.get("ogrenme", {})
if ogrenme.get("detay"):
    durum_renk = {"GELISIYOR": "🟢", "STABIL": "🟡", "KOTULUYOR": "🔴"}.get(ogrenme.get("ogrenme_durumu"), "⚪")
    st.markdown(f"**Öğrenme Eğrisi:** {durum_renk} {ogrenme.get('detay', '')}")

if dersler:
    for ders in reversed(dersler[-3:]):
        with st.expander(f"📅 {ders.get('tarih', '?')} — Kazanç:{ders.get('kazanc', 0)} Kayıp:{ders.get('kayip', 0)} Net:%{ders.get('toplam_kar', 0)}"):
            for d in ders.get("dersler", []):
                st.markdown(f"- {d}")
else:
    st.info("🍼 Bebek henüz öğrenmeye başlamadı — ilk işlem günü sonrası dersler burada görünecek")

# Kill switch durumu
ks = beyin.get("kill_switch", {})
if ks.get("dur"):
    st.error(f"🚨 KILL SWITCH AKTİF: {ks.get('sebep')} — {ks.get('detay')}")

st.divider()

# ============================================================
# REJIM GECIS TARIHCESI
# ============================================================

st.subheader("🔄 Rejim Geçiş Tarihi")

if isinstance(rejim_gecisler, list) and rejim_gecisler:
    gecis_df = pd.DataFrame(rejim_gecisler)
    st.dataframe(gecis_df, use_container_width=True, hide_index=True)

    # Gecis istatistikleri
    gecis_sayilari = {}
    for g in rejim_gecisler:
        key = f"{g.get('eski', '?')} → {g.get('yeni', '?')}"
        gecis_sayilari[key] = gecis_sayilari.get(key, 0) + 1

    if gecis_sayilari:
        st.markdown("**En sık geçişler:**")
        for k, v in sorted(gecis_sayilari.items(), key=lambda x: -x[1])[:5]:
            st.markdown(f"- {k}: **{v}** kez")
else:
    st.info("Henüz rejim geçişi yaşanmadı")

st.divider()

# ============================================================
# MEVSIMSELLIK
# ============================================================

st.subheader("🌦️ Mevsimsellik")

ay = datetime.now().month
ay_adi = ["", "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
          "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik"][ay]

mevsim = duygu.get("mevsim_carpanlari", {})
if mevsim:
    st.markdown(f"**{ay_adi} ayında güçlü sektörler:**")
    for sektor, carpan in sorted(mevsim.items(), key=lambda x: -x[1]):
        bar_len = int(carpan * 10)
        st.markdown(f"{'🟩' * bar_len} **{sektor}** x{carpan}")
else:
    st.info(f"{ay_adi} için özel mevsimsellik yok")

# ============================================================
# CANLI GUNCELLEME BUTONU
# ============================================================

st.divider()

if st.button("🔄 Beyni Şimdi Güncelle", type="primary"):
    with st.spinner("4 katman analiz ediliyor..."):
        import subprocess
        result = subprocess.run(
            ["C:\\Program Files\\Python312\\python.exe", "-X", "utf8",
             str(BASE_DIR / "anka_beyin.py"), "--analiz"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            st.success("Beyin güncellendi! Sayfayı yenile.")
            st.code(result.stdout[-500:] if result.stdout else "OK")
        else:
            st.error(f"Hata: {result.stderr[-300:]}")

st.caption("ANKA Beyin — 4 Katmanlı Rejim Motoru | 52 Akademik Makale | 10 Profesör Onaylı")
