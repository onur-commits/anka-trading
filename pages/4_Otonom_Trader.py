"""
ANKA Otonom Trader Dashboard — Devralma & Pozisyon Yönetimi
"""

import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="ANKA Otonom Trader", page_icon="🤖", layout="wide")

# ============================================================
# PATHS
# ============================================================
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVRALMA_PATH = os.path.join(BASE, "data", "devralma_listesi.json")
STATE_PATH = os.path.join(BASE, "data", "otonom_state.json")
LOG_PATH = os.path.join(BASE, "logs", "otonom_stdout.log")
TRADE_LOG = os.path.join(BASE, "logs", "trade_log.json")


def devralma_oku():
    if os.path.exists(DEVRALMA_PATH):
        with open(DEVRALMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def devralma_kaydet(data):
    os.makedirs(os.path.dirname(DEVRALMA_PATH), exist_ok=True)
    with open(DEVRALMA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def state_oku():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def trade_log_oku():
    if os.path.exists(TRADE_LOG):
        with open(TRADE_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def log_tail(n=50):
    if not os.path.exists(LOG_PATH):
        return "Log dosyası bulunamadı"
    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return "".join(lines[-n:])


# ============================================================
# HEADER
# ============================================================
st.title("🤖 ANKA Otonom Trader")

state = state_oku()
col1, col2, col3, col4 = st.columns(4)
with col1:
    sermaye = state.get("sermaye", 100_000)
    st.metric("Sermaye", f"{sermaye:,.0f} ₺")
with col2:
    gun_pl = state.get("gun_sonu_pl", 0)
    st.metric("Günlük PL", f"{gun_pl:+,.0f} ₺")
with col3:
    aktif = len(state.get("aktif_emirler", []))
    st.metric("ANKA Pozisyon", aktif)
with col4:
    devralma_list = devralma_oku()
    st.metric("Devralma Pozisyon", len(devralma_list))

st.divider()

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Devralma Pozisyonları",
    "📊 ANKA Emirleri",
    "➕ Yeni Devralma Ekle",
    "📜 Log & İşlem Geçmişi"
])

# --- TAB 1: Devralma ---
with tab1:
    st.subheader("Devralma Pozisyonları")
    st.caption("Senin aldığın, ANKA'nın yönettiği hisseler")

    devralma = devralma_oku()
    if not devralma:
        st.info("Henüz devralma pozisyonu yok. 'Yeni Devralma Ekle' sekmesinden ekleyebilirsin.")
    else:
        for i, d in enumerate(devralma):
            ticker = d["ticker"]
            giris = d["giris_fiyat"]
            adet = d["adet"]
            stop = d.get("stop_loss", giris * 0.95)
            tp1_done = d.get("tp1_yapildi", False)
            trail_aktif = d.get("trailing_aktif", False)
            trail_high = d.get("trailing_high", giris)

            # Tahmini PL (son fiyat bilinmiyorsa girişe eşit)
            toplam = giris * adet

            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
                with c1:
                    st.markdown(f"### {ticker}")
                    st.caption(f"Giriş: {giris:.2f} ₺ | {adet} lot")
                with c2:
                    st.metric("Toplam Maliyet", f"{toplam:,.0f} ₺")
                with c3:
                    st.metric("Stop-Loss", f"{stop:.2f} ₺",
                              delta=f"-{d.get('stop_pct', 5):.0f}%", delta_color="inverse")
                with c4:
                    durum = []
                    if tp1_done:
                        durum.append("✅ TP1 yapıldı")
                    else:
                        durum.append(f"⏳ TP1: %{d.get('tp1_pct', 7)}")
                    if trail_aktif:
                        durum.append(f"🔄 Trail: {trail_high:.2f}")
                    else:
                        durum.append("⏸️ Trail beklemede")
                    st.markdown("  \n".join(durum))
                with c5:
                    if st.button("🗑️ Çıkar", key=f"del_{ticker}"):
                        devralma = [x for x in devralma if x["ticker"] != ticker]
                        devralma_kaydet(devralma)
                        st.rerun()

                st.divider()

# --- TAB 2: ANKA Emirleri ---
with tab2:
    st.subheader("ANKA'nın Kendi Emirleri")
    st.caption("Bomba skor taramasından otomatik alınan hisseler")

    emirler = state.get("aktif_emirler", [])
    if not emirler:
        st.info("Aktif ANKA emri yok. Otonom trader 09:05'te bomba skora göre alım yapar.")
    else:
        import pandas as pd
        df = pd.DataFrame(emirler)
        cols_rename = {
            "ticker": "Hisse", "lot": "Lot", "giris_fiyat": "Giriş",
            "skor": "Bomba Skor", "zaman": "Alış Saati"
        }
        df = df.rename(columns={k: v for k, v in cols_rename.items() if k in df.columns})
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- TAB 3: Yeni Devralma Ekle ---
with tab3:
    st.subheader("Yeni Devralma Pozisyonu Ekle")
    st.caption("Elindeki bir hisseyi ANKA'nın yönetmesini istiyorsan buradan ekle")

    with st.form("devralma_form"):
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Hisse Kodu", placeholder="ASELS").upper().strip()
            giris_fiyat = st.number_input("Giriş Fiyatı (₺)", min_value=0.01, step=0.01)
            adet = st.number_input("Lot Adedi", min_value=1, step=1)
        with col2:
            stop_pct = st.slider("Stop-Loss %", min_value=2.0, max_value=15.0, value=5.0, step=0.5)
            tp1_pct = st.slider("TP1 (yarısını sat) %", min_value=3.0, max_value=20.0, value=7.0, step=0.5)
            tp2_pct = st.slider("TP2 (tamamını sat) %", min_value=5.0, max_value=30.0, value=15.0, step=0.5)

        submitted = st.form_submit_button("🚀 Devralma Ekle", use_container_width=True)

        if submitted:
            if not ticker or giris_fiyat <= 0 or adet <= 0:
                st.error("Tüm alanları doldur!")
            else:
                devralma = devralma_oku()
                # Aynı ticker varsa güncelle
                devralma = [d for d in devralma if d["ticker"] != ticker]
                entry = {
                    "ticker": ticker,
                    "giris_fiyat": giris_fiyat,
                    "adet": int(adet),
                    "stop_pct": stop_pct,
                    "stop_loss": round(giris_fiyat * (1 - stop_pct / 100), 2),
                    "trailing_high": giris_fiyat,
                    "trailing_aktif": False,
                    "tp1_yapildi": False,
                    "tp1_pct": tp1_pct,
                    "tp2_pct": tp2_pct,
                    "ekleme_zaman": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                devralma.append(entry)
                devralma_kaydet(devralma)
                st.success(f"✅ {ticker} devralma listesine eklendi! "
                           f"Stop: {entry['stop_loss']:.2f} ₺ | "
                           f"TP1: %{tp1_pct} | TP2: %{tp2_pct}")
                st.rerun()

# --- TAB 4: Log ---
with tab4:
    st.subheader("İşlem Geçmişi & Log")

    log_tab1, log_tab2 = st.tabs(["📜 Canlı Log", "💰 İşlem Geçmişi"])

    with log_tab1:
        n_lines = st.slider("Son kaç satır", 10, 200, 50)
        log_text = log_tail(n_lines)
        st.code(log_text, language="text")
        if st.button("🔄 Yenile"):
            st.rerun()

    with log_tab2:
        trades = trade_log_oku()
        if not trades:
            st.info("Henüz işlem kaydı yok")
        else:
            import pandas as pd
            df = pd.DataFrame(trades)
            # En son işlemler üstte
            if "zaman" in df.columns:
                df = df.sort_values("zaman", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("---")
    st.subheader("⚙️ Otonom Trader")

    # Durum
    st.markdown("**Sistem Durumu**")
    son_alis = state.get("son_alis_zaman", "—")
    st.caption(f"Son alış: {son_alis}")
    st.caption(f"Aktif emirler: {len(state.get('aktif_emirler', []))}")
    st.caption(f"Devralma: {len(devralma_oku())}")

    st.markdown("---")
    st.caption("ANKA Otonom Trader v3")
    st.caption("Kademeli satış: TP1 → TP2 → Trailing")
