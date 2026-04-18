"""
ANKA Sistem Sağlık Dashboard — Mühendis Raporu
================================================
Sen yokken buraya bak:
- Tüm servislerin durumu (yeşil/kırmızı)
- Mühendis son kontrol zamanı
- ML model doğruluk oranları
- Bugünkü bomba isabet analizi
- Otonom trader PL
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
sys.path.insert(0, str(BASE_DIR))

st.set_page_config(page_title="Sistem Sağlık", page_icon="🏥", layout="wide")


def yukle(dosya, varsayilan=None):
    if varsayilan is None:
        varsayilan = {}
    yol = DATA_DIR / dosya
    if yol.exists():
        try:
            with open(yol, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return varsayilan


def log_tail(dosya, n=20):
    yol = LOG_DIR / dosya
    if yol.exists():
        try:
            with open(yol, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return lines[-n:]
        except Exception:
            pass
    return []


def dosya_yasi_dk(dosya_path):
    """Dosyanın kaç dakika önce güncellendiğini döndür."""
    try:
        if isinstance(dosya_path, str):
            dosya_path = Path(dosya_path)
        if dosya_path.exists():
            mod_time = datetime.fromtimestamp(dosya_path.stat().st_mtime)
            return int((datetime.now() - mod_time).total_seconds() / 60)
    except Exception:
        pass
    return -1


# ============================================================
# HEADER
# ============================================================

st.title("🏥 ANKA Sistem Sağlık Paneli")
st.caption(f"Son güncelleme: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================
# SERVİS DURUMLARI
# ============================================================

st.subheader("🚦 Servis Durumları")

servisler = []

# Mühendis
muhendis_yas = dosya_yasi_dk(LOG_DIR / "muhendis_output.log")
servisler.append({
    "Servis": "🔧 ANKA Mühendis",
    "Durum": "🟢 ÇALIŞIYOR" if 0 <= muhendis_yas <= 35 else "🔴 DURMUŞ",
    "Son Aktivite": f"{muhendis_yas} dk önce" if muhendis_yas >= 0 else "Bilinmiyor",
    "Kontrol": "30 dk döngü"
})

# Otonom Trader
otonom_yas = dosya_yasi_dk(LOG_DIR / "otonom_stdout.log")
servisler.append({
    "Servis": "🤖 Otonom Trader (BIST)",
    "Durum": "🟢 ÇALIŞIYOR" if 0 <= otonom_yas <= 120 else "🔴 DURMUŞ",
    "Son Aktivite": f"{otonom_yas} dk önce" if otonom_yas >= 0 else "Bilinmiyor",
    "Kontrol": "Schedule bazlı"
})

# Coin Trader
coin_yas = dosya_yasi_dk(LOG_DIR / "coin_otonom_stdout.log")
servisler.append({
    "Servis": "🪙 Coin Otonom Trader",
    "Durum": "🟢 ÇALIŞIYOR" if 0 <= coin_yas <= 35 else "🔴 DURMUŞ",
    "Son Aktivite": f"{coin_yas} dk önce" if coin_yas >= 0 else "Bilinmiyor",
    "Kontrol": "20 dk döngü"
})

# BIST Dashboard
bist_dash = dosya_yasi_dk(DATA_DIR / "otonom_state.json")
servisler.append({
    "Servis": "📊 BIST Dashboard (8501)",
    "Durum": "🟢 AKTİF" if 0 <= bist_dash <= 1440 else "🟡 ESKİ VERİ",
    "Son Aktivite": f"{bist_dash} dk önce" if bist_dash >= 0 else "Bilinmiyor",
    "Kontrol": "Streamlit"
})

# Coin Dashboard
coin_dash = dosya_yasi_dk(DATA_DIR / "coin_otonom_state.json")
servisler.append({
    "Servis": "🪙 Coin Dashboard (8502)",
    "Durum": "🟢 AKTİF" if 0 <= coin_dash <= 60 else "🟡 ESKİ VERİ",
    "Son Aktivite": f"{coin_dash} dk önce" if coin_dash >= 0 else "Bilinmiyor",
    "Kontrol": "Streamlit"
})

# Summary metrics
calisan = sum(1 for s in servisler if "🟢" in s["Durum"])
col1, col2, col3 = st.columns(3)
col1.metric("Çalışan", f"{calisan}/{len(servisler)}", delta="OK" if calisan == len(servisler) else "SORUN")
col2.metric("Mühendis", "UYANIK" if 0 <= muhendis_yas <= 35 else "UYUYOR")
col3.metric("Son Kontrol", f"{muhendis_yas} dk önce" if muhendis_yas >= 0 else "?")

st.dataframe(pd.DataFrame(servisler), use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# OTONOM TRADER DURUM
# ============================================================

st.subheader("📈 Otonom Trader Durumu")

state = yukle("otonom_state.json")
coin_state = yukle("coin_otonom_state.json")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**BIST Otonom Trader**")
    bombalar = state.get("bombalar", [])
    emirler = state.get("aktif_emirler", [])
    rejim = state.get("rejim", {})
    st.write(f"Rejim: **{rejim.get('rejim', '?')}** (güven: {rejim.get('guven', '?')})")
    st.write(f"Bomba bulunan: **{len(bombalar)}** hisse")
    st.write(f"Aktif emir: **{len(emirler)}**")
    if bombalar:
        bomba_df = pd.DataFrame(bombalar)
        st.dataframe(bomba_df, use_container_width=True, hide_index=True)

with col2:
    st.markdown("**Coin Otonom Trader**")
    coin_poz = yukle("coin_pozisyonlar_aktif.json", [])
    if isinstance(coin_poz, list):
        st.write(f"Aktif pozisyon: **{len(coin_poz)}**")
        if coin_poz:
            coin_df = pd.DataFrame(coin_poz)
            st.dataframe(coin_df, use_container_width=True, hide_index=True)
    else:
        st.write("Coin pozisyon verisi okunamadı")
    risk = coin_state.get("risk", {})
    if risk:
        st.write(f"Drawdown: **{risk.get('drawdown', 0):.1f}%** | Peak: **${risk.get('peak', 0):,.0f}**")

st.divider()

# ============================================================
# DEVRALMA LİSTESİ
# ============================================================

st.subheader("📥 Devralma Listesi")
devralma = yukle("devralma_listesi.json", [])
if devralma:
    dev_df = pd.DataFrame(devralma)
    st.dataframe(dev_df, use_container_width=True, hide_index=True)
else:
    st.info("Devralma listesi boş")

st.divider()

# ============================================================
# ML MODEL DOĞRULUK
# ============================================================

st.subheader("🧠 ML Model Doğruluk Raporu")

dogruluk = yukle("dogruluk_raporu.json")
sinyal_log = yukle("sinyal_dogruluk.json", [])

if isinstance(sinyal_log, list) and sinyal_log:
    toplam = len(sinyal_log)
    kontrol_edilen = [s for s in sinyal_log if s.get("sonuc")]
    dogru = [s for s in kontrol_edilen if s.get("dogru")]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Sinyal", toplam)
    col2.metric("Kontrol Edilen", len(kontrol_edilen))
    col3.metric("Doğru", len(dogru))
    isabet = (len(dogru) / max(len(kontrol_edilen), 1)) * 100
    col4.metric("İsabet Oranı", f"%{isabet:.1f}")

    # Son 10 sinyal
    st.markdown("**Son 10 Sinyal:**")
    son_df = pd.DataFrame(sinyal_log[-10:])
    st.dataframe(son_df, use_container_width=True, hide_index=True)
elif dogruluk:
    st.json(dogruluk)
else:
    st.warning("Henüz doğruluk verisi yok. `dogruluk_kontrol.py` çalıştırılması gerekiyor.")

st.divider()

# ============================================================
# BUGÜNÜN BOMBA İSABET ANALİZİ
# ============================================================

st.subheader("🎯 Bugünün Bomba İsabet Analizi")
st.caption("ANKA'nın sabah tespit ettikleri vs günün gerçek bombaları")

# Trade log
trade_log = yukle("otonom_trades.json", [])
bugun = datetime.now().strftime("%Y-%m-%d")
bugun_trades = [t for t in trade_log if bugun in t.get("tarih", "")]

if bugun_trades:
    st.markdown("**Bugünkü İşlemler:**")
    trade_df = pd.DataFrame(bugun_trades)
    st.dataframe(trade_df, use_container_width=True, hide_index=True)
else:
    st.info("Bugün henüz işlem yok")

st.divider()

# ============================================================
# MÜHENDIS LOGLARI
# ============================================================

st.subheader("🔧 Mühendis Son Loglar")

muhendis_log = yukle("muhendis_log.json" if (DATA_DIR / "muhendis_log.json").exists() else "", [])
if muhendis_log:
    son_loglar = muhendis_log[-15:]
    for l in reversed(son_loglar):
        seviye = l.get("seviye", "INFO")
        renk = {"ERROR": "🔴", "WARNING": "🟡", "INFO": "🟢"}.get(seviye, "⚪")
        st.text(f"{renk} [{l.get('zaman', '')}] [{l.get('kategori', '')}] {l.get('mesaj', '')}")
else:
    st.info("Mühendis log verisi yok")

# Otonom trader son loglar
with st.expander("📋 Otonom Trader Son Log (stdout)"):
    lines = log_tail("otonom_stdout.log", 30)
    if lines:
        st.code("".join(lines))
    else:
        st.info("Log dosyası bulunamadı")

with st.expander("📋 Coin Trader Son Log"):
    lines = log_tail("coin_otonom_stdout.log", 30)
    if lines:
        st.code("".join(lines))
    else:
        st.info("Log dosyası bulunamadı")

# ============================================================
# AUTO REFRESH
# ============================================================
st.divider()
st.caption("Bu sayfa her açıldığında güncel veriyi gösterir. Otomatik yenileme için tarayıcıyı yenileyin.")
