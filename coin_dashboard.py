"""
🪙 COIN DASHBOARD — Kripto Kontrol Merkezi
============================================
ANKA'dan ayrı, bağımsız kripto dashboard.
Port: 8502

Özellikler:
- Anlık fiyatlar (Binance)
- Roket tarayıcı (hacim patlaması)
- Bomba tarayıcı (teknik + hacim + makro)
- Coin AI skorları
- Portföy takip
- 7/24 çalışır
"""

import streamlit as st
import json
import os
import sys
import time
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="COIN Dashboard", page_icon="🪙", layout="wide")

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── BINANCE VERİ FONKSİYONLARI ─────────────────────────────
@st.cache_data(ttl=30)
def tum_fiyatlar():
    """Binance'den tüm coin fiyatlarını çek."""
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10)
        data = r.json()
        sonuc = {}
        for d in data:
            sym = d["symbol"]
            if sym.endswith("USDT") or sym.endswith("TRY"):
                sonuc[sym] = {
                    "fiyat": float(d["lastPrice"]),
                    "degisim": float(d["priceChangePercent"]),
                    "hacim": float(d["quoteVolume"]),
                    "yuksek": float(d["highPrice"]),
                    "dusuk": float(d["lowPrice"]),
                }
        return sonuc
    except:
        return {}


def mini_grafik(symbol, interval="1h", limit=24):
    """Son 24 saatlik mini grafik verisi."""
    try:
        r = requests.get("https://api.binance.com/api/v3/klines",
                        params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=5)
        data = r.json()
        return [float(k[4]) for k in data]  # Close fiyatları
    except:
        return []


# ── ANA DASHBOARD ───────────────────────────────────────────
st.markdown("# 🪙 COIN Dashboard")
st.caption(f"Anlık veriler — Binance | {datetime.now().strftime('%H:%M:%S')}")

# ── ÜST BANT ───────────────────────────────────────────────
fiyatlar = tum_fiyatlar()

if fiyatlar:
    btc = fiyatlar.get("BTCUSDT", {})
    eth = fiyatlar.get("ETHUSDT", {})
    sol = fiyatlar.get("SOLUSDT", {})
    bnb = fiyatlar.get("BNBUSDT", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("BTC", f"${btc.get('fiyat',0):,.0f}", f"{btc.get('degisim',0):+.1f}%")
    with col2:
        st.metric("ETH", f"${eth.get('fiyat',0):,.0f}", f"{eth.get('degisim',0):+.1f}%")
    with col3:
        st.metric("SOL", f"${sol.get('fiyat',0):,.2f}", f"{sol.get('degisim',0):+.1f}%")
    with col4:
        st.metric("BNB", f"${bnb.get('fiyat',0):,.0f}", f"{bnb.get('degisim',0):+.1f}%")

st.divider()

# ── TABLAR ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Piyasa", "🚀 Roket Tarayıcı", "🪙 Bomba Tarayıcı", "⚙️ Ayarlar"])

# ══════════════════════════════════════════════════════════
# TAB 1: PİYASA
# ══════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 Kripto Piyasası")

    # Filtre
    filtre = st.radio("Göster:", ["🔥 Top 20 USDT", "🇹🇷 TL Pairleri", "📈 En çok yükselen", "📉 En çok düşen"], horizontal=True)

    if fiyatlar:
        rows = []
        for sym, v in fiyatlar.items():
            if filtre == "🇹🇷 TL Pairleri" and not sym.endswith("TRY"):
                continue
            if filtre == "🔥 Top 20 USDT" and not sym.endswith("USDT"):
                continue

            coin_name = sym.replace("USDT", "").replace("TRY", "")
            birim = "₺" if "TRY" in sym else "$"

            rows.append({
                "Coin": coin_name,
                "Pair": sym,
                "Fiyat": v["fiyat"],
                "24s %": v["degisim"],
                "Hacim": v["hacim"],
                "Yüksek": v["yuksek"],
                "Düşük": v["dusuk"],
                "Birim": birim,
            })

        df = pd.DataFrame(rows)

        if filtre == "📈 En çok yükselen":
            df = df.sort_values("24s %", ascending=False).head(20)
        elif filtre == "📉 En çok düşen":
            df = df.sort_values("24s %", ascending=True).head(20)
        else:
            df = df.sort_values("Hacim", ascending=False).head(20)

        # Fiyat formatla
        for i, row in df.iterrows():
            b = row["Birim"]
            f = row["Fiyat"]
            df.at[i, "Fiyat Str"] = f"{b}{f:,.2f}" if f >= 1 else f"{b}{f:,.6f}"
            df.at[i, "Hacim Str"] = f"{b}{row['Hacim']/1e6:,.0f}M"

        st.dataframe(
            df[["Coin", "Pair", "Fiyat Str", "24s %", "Hacim Str"]].rename(
                columns={"Fiyat Str": "Fiyat", "Hacim Str": "Hacim"}
            ),
            use_container_width=True, hide_index=True,
            height=700
        )

# ══════════════════════════════════════════════════════════
# TAB 2: ROKET TARAYICI
# ══════════════════════════════════════════════════════════
with tab2:
    st.subheader("🚀 Roket Tarayıcı — Hacim Patlaması Yakalayıcı")

    col1, col2 = st.columns([3, 1])
    with col1:
        esik = st.slider("Hacim eşiği (x)", 1.5, 10.0, 2.0, 0.5)
    with col2:
        if st.button("🚀 TARA", use_container_width=True, type="primary"):
            st.session_state["roket_tara"] = True

    if st.session_state.get("roket_tara"):
        with st.spinner("46 coin taranıyor..."):
            try:
                from coin_trader import RoketTarayici
                tarayici = RoketTarayici()
                roketler = tarayici.hacim_patlama_tara(esik=esik)

                if roketler:
                    for r in roketler:
                        col1, col2, col3 = st.columns([2, 2, 3])
                        with col1:
                            st.markdown(f"### 🚀 {r['symbol']}")
                            birim = "₺" if "TRY" in r['symbol'] else "$"
                            st.markdown(f"**{birim}{r['fiyat']:,.4f}**" if r['fiyat'] < 1 else f"**{birim}{r['fiyat']:,.2f}**")
                        with col2:
                            st.metric("24s", f"{r['degisim_24s']:+.1f}%")
                            st.metric("1s", f"{r['degisim_1s']:+.1f}%")
                        with col3:
                            st.markdown(f"**Hacim:** x{r['hacim_x']}")
                            st.markdown(f"**Skor:** {r['skor']}")
                            st.markdown(f"**Sebep:** {r['sebep']}")

                        # Mini grafik
                        grafik = mini_grafik(r['symbol'])
                        if grafik:
                            st.line_chart(pd.DataFrame({"fiyat": grafik}), height=80)
                        st.divider()
                else:
                    st.info("🌊 Piyasa sakin — şu an roket yok")

                st.session_state["roket_tara"] = False
            except Exception as e:
                st.error(str(e))

# ══════════════════════════════════════════════════════════
# TAB 3: BOMBA TARAYICI
# ══════════════════════════════════════════════════════════
with tab3:
    st.subheader("🪙 Bomba Tarayıcı — Teknik + Hacim + Makro")

    if st.button("🪙 BOMBA TARA", use_container_width=True, type="primary"):
        with st.spinner("15 coin ajanlarla taranıyor..."):
            try:
                from coin_trader import CoinBrain
                brain = CoinBrain()
                bombalar = brain.tara()

                if bombalar:
                    for b in bombalar:
                        birim = "₺" if "TRY" in b['symbol'] else "$"
                        renk = "green" if b['skor'] >= 80 else "orange" if b['skor'] >= 60 else "gray"
                        st.markdown(f"""
                        <div style="background:#1a1a2e;padding:15px;border-radius:10px;margin:5px 0;border-left:4px solid {renk}">
                            <b style="font-size:18px">🪙 {b['symbol']}</b> — {birim}{b['fiyat']:,.2f}<br>
                            <span style="color:{renk};font-size:24px;font-weight:bold">Skor: {b['skor']:.0f}</span>
                        </div>
                        """, unsafe_allow_html=True)

                        grafik = mini_grafik(b['symbol'])
                        if grafik:
                            st.line_chart(pd.DataFrame({"fiyat": grafik}), height=80)
                else:
                    st.info("Şu an bomba coin yok")
            except Exception as e:
                st.error(str(e))

# ══════════════════════════════════════════════════════════
# TAB 4: AYARLAR
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("⚙️ Coin Ayarları")

    st.markdown("**Binance API (emir göndermek için)**")
    st.text_input("API Key", placeholder="Binance API key'inizi girin", type="password", key="binance_key")
    st.text_input("API Secret", placeholder="Binance API secret'ınızı girin", type="password", key="binance_secret")

    if st.button("💾 Kaydet", use_container_width=True):
        st.success("API bilgileri kaydedildi (oturumda)")

    st.divider()
    st.markdown("**İzlenen Coinler**")
    st.text_area("USDT Pairleri (virgülle ayır)",
                 value="BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,XRPUSDT,ADAUSDT,AVAXUSDT,DOTUSDT,LINKUSDT,NEARUSDT,ARBUSDT",
                 key="coin_list")

    st.divider()
    st.markdown("**Roket Kriterleri**")
    st.number_input("Min hacim oranı (x)", 1.5, 20.0, 5.0, 0.5, key="min_hacim")
    st.number_input("Min 24s değişim (%)", 1.0, 50.0, 10.0, 1.0, key="min_degisim")

# ── SIDEBAR ─────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("**🪙 COIN Dashboard**")
st.sidebar.markdown(f"⏰ {datetime.now().strftime('%H:%M:%S')}")

if fiyatlar:
    btc_f = fiyatlar.get("BTCUSDT", {})
    st.sidebar.markdown(f"₿ BTC: ${btc_f.get('fiyat',0):,.0f} ({btc_f.get('degisim',0):+.1f}%)")

if st.sidebar.button("🔄 Yenile"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("[🦅 ANKA Borsa](http://localhost:8501)")
st.sidebar.markdown("[🪙 COIN Kripto](http://localhost:8502)")
