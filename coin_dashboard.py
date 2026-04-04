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

# ── FEAR & GREED (HER ZAMAN GÖRÜNÜR) ────────────────────
fng_val = 50
fng_class = "Neutral"
try:
    fng_r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
    fng_data = fng_r.json()["data"][0]
    fng_val = int(fng_data["value"])
    fng_class = fng_data["value_classification"]
except:
    pass

if fng_val <= 20:
    fng_renk = "🔴"
    fng_bg = "#ff000033"
    fng_mesaj = "EXTREME FEAR — Tarihsel alım bölgesi!"
elif fng_val <= 35:
    fng_renk = "🟠"
    fng_bg = "#ff660033"
    fng_mesaj = "Fear — Dikkatli ol"
elif fng_val >= 75:
    fng_renk = "🟢"
    fng_bg = "#00ff0033"
    fng_mesaj = "EXTREME GREED — Satış düşün!"
elif fng_val >= 55:
    fng_renk = "🟡"
    fng_bg = "#ffff0033"
    fng_mesaj = "Greed — Temkinli ol"
else:
    fng_renk = "⚪"
    fng_bg = "#ffffff11"
    fng_mesaj = "Neutral"

st.markdown(f"""
<div style="background:{fng_bg};padding:10px 20px;border-radius:10px;text-align:center;margin-bottom:10px">
    <span style="font-size:40px">{fng_renk}</span>
    <span style="font-size:30px;font-weight:bold"> Fear & Greed: {fng_val}</span>
    <span style="font-size:16px;color:#aaa"> — {fng_mesaj}</span>
</div>
""", unsafe_allow_html=True)

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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Piyasa", "🚀 Full Scan (533)", "🪙 Bomba Tarayıcı", "🔔 Alarmlar & Notlar", "⚙️ Ayarlar"])

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
# TAB 2: FULL SCAN (533 coin paralel)
# ══════════════════════════════════════════════════════════
with tab2:
    st.subheader("🚀 Full Scan — 533 Coin Paralel Tarama")
    st.caption("Sıkışma + Birikim = Patlama ÖNCESİ yakalama")

    if st.button("🚀 533 COİN TARA", use_container_width=True, type="primary"):
        with st.spinner("533 coin paralel taranıyor (~25sn)..."):
            try:
                from coin_fullscan import tum_coinleri_cek, paralel_tara
                coins = tum_coinleri_cek()
                sonuclar = paralel_tara(coins, max_workers=8)

                if sonuclar:
                    # Tablo
                    rows = []
                    for i, s in enumerate(sonuclar[:30]):
                        if i == 0: emoji = "🥇"
                        elif i == 1: emoji = "🥈"
                        elif i == 2: emoji = "🥉"
                        elif s.get("roket"): emoji = "🚀"
                        elif s["skor"] >= 70: emoji = "🔥"
                        else: emoji = "⚪"

                        birim = "₺" if "TRY" in s["symbol"] else "$"
                        rows.append({
                            "#": f"{emoji} {i+1}",
                            "Coin": s["symbol"],
                            "Fiyat": f"{birim}{s['fiyat']}",
                            "Skor": s["skor"],
                            "Evre": s.get("evre", "?"),
                            "24s %": f"{s['degisim_24s']:+.1f}",
                            "Hacim": f"x{s['hacim_x']}",
                            "RSI": s["rsi"],
                        })

                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=700)

                    # İstatistik
                    col1, col2, col3, col4 = st.columns(4)
                    roketler = [s for s in sonuclar if s.get("roket")]
                    sikismalar = [s for s in sonuclar if s.get("evre") == "SIKISMA"]
                    birikimler = [s for s in sonuclar if s.get("evre") == "BIRIKIM"]
                    with col1: st.metric("Toplam", len(sonuclar))
                    with col2: st.metric("🔥 Sıkışma", len(sikismalar))
                    with col3: st.metric("📦 Birikim", len(birikimler))
                    with col4: st.metric("🚀 Roket", len(roketler))
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
# TAB 4: ALARMLAR & NOTLAR
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("🔔 Alarmlar & Kişisel Notlar")

    ALARM_DOSYA = DATA_DIR / "coin_alarmlar.json"
    NOT_DOSYA = DATA_DIR / "coin_notlar.json"

    def alarmlar_oku():
        if ALARM_DOSYA.exists():
            try: return json.load(open(ALARM_DOSYA))
            except: pass
        return []

    def alarmlar_yaz(data):
        DATA_DIR.mkdir(exist_ok=True)
        with open(ALARM_DOSYA, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def notlar_oku():
        if NOT_DOSYA.exists():
            try: return json.load(open(NOT_DOSYA))
            except: pass
        return []

    def notlar_yaz(data):
        DATA_DIR.mkdir(exist_ok=True)
        with open(NOT_DOSYA, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── ALARM OLUŞTUR ──
    st.markdown("### 🔔 Alarm Kur")

    col1, col2, col3 = st.columns(3)
    with col1:
        alarm_tip = st.selectbox("Alarm tipi", [
            "Fear & Greed değişimi",
            "Coin fiyat hedefi",
            "Hacim patlaması",
            "Skor eşiği",
        ])
    with col2:
        if alarm_tip == "Fear & Greed değişimi":
            alarm_deger = st.number_input("F&G değeri", 0, 100, 25, help="Bu değere gelince alarm")
            alarm_yon = st.selectbox("Yön", ["Altına düşünce", "Üstüne çıkınca"])
        elif alarm_tip == "Coin fiyat hedefi":
            alarm_coin = st.text_input("Coin (örn: BTCUSDT)", "BTCUSDT")
            alarm_deger = st.number_input("Hedef fiyat ($)", 0.0, 1000000.0, 70000.0)
            alarm_yon = st.selectbox("Yön", ["Üstüne çıkınca", "Altına düşünce"])
        elif alarm_tip == "Hacim patlaması":
            alarm_deger = st.number_input("Hacim oranı (x)", 2.0, 50.0, 5.0)
            alarm_yon = "Üstüne çıkınca"
        else:
            alarm_deger = st.number_input("Skor eşiği", 50, 100, 80)
            alarm_yon = "Üstüne çıkınca"
    with col3:
        alarm_ses = st.toggle("🔊 Sesli alarm", True)
        if st.button("➕ Alarm Ekle", use_container_width=True):
            alarmlar = alarmlar_oku()
            alarmlar.append({
                "tip": alarm_tip,
                "deger": alarm_deger,
                "yon": alarm_yon if 'alarm_yon' in dir() else "Üstüne çıkınca",
                "coin": alarm_coin if 'alarm_coin' in dir() else "",
                "ses": alarm_ses,
                "aktif": True,
                "olusturma": datetime.now().isoformat(),
            })
            alarmlar_yaz(alarmlar)
            st.success("✅ Alarm eklendi!")
            st.rerun()

    # Mevcut alarmlar
    alarmlar = alarmlar_oku()
    if alarmlar:
        st.markdown("**Aktif Alarmlar:**")
        for i, a in enumerate(alarmlar):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"🔔 **{a['tip']}** — {a.get('coin','')} {a['deger']} ({a.get('yon','')})")
            with col2:
                if st.button("🗑️", key=f"del_alarm_{i}"):
                    alarmlar.pop(i)
                    alarmlar_yaz(alarmlar)
                    st.rerun()

    # Alarm kontrolü (Fear & Greed)
    for a in alarmlar:
        if a["tip"] == "Fear & Greed değişimi" and a["aktif"]:
            if a.get("yon") == "Altına düşünce" and fng_val <= a["deger"]:
                st.warning(f"🚨 ALARM: Fear & Greed {fng_val} ≤ {a['deger']}!")
                if a["ses"]:
                    try:
                        import subprocess
                        subprocess.run(["osascript", "-e", f'display notification "Fear & Greed {fng_val}!" with title "COIN ALARM" sound name "Glass"'], timeout=3, capture_output=True)
                    except: pass
            elif a.get("yon") == "Üstüne çıkınca" and fng_val >= a["deger"]:
                st.warning(f"🚨 ALARM: Fear & Greed {fng_val} ≥ {a['deger']}!")

    st.divider()

    # ── KİŞİSEL NOT GİRİŞİ ──
    st.markdown("### 📝 Kişisel Notlar & Önseziler")
    st.caption("Hissettiğin bir şeyi yaz — AI sonra öğrenir")

    not_metin = st.text_area("Not / Önsezi / Gözlem",
                             placeholder="Örn: AVAX'ta balina hareketi gördüm, yakında patlayabilir...",
                             height=80)

    col1, col2 = st.columns(2)
    with col1:
        not_oncelik = st.selectbox("Öncelik", ["🔴 Acil", "🟡 Önemli", "🟢 Normal", "📌 Hatırlatma"])
    with col2:
        not_coin = st.text_input("İlgili coin (opsiyonel)", placeholder="AVAXUSDT")

    if st.button("💾 Notu Kaydet", use_container_width=True):
        if not_metin:
            notlar = notlar_oku()
            notlar.append({
                "metin": not_metin,
                "oncelik": not_oncelik,
                "coin": not_coin,
                "zaman": datetime.now().isoformat(),
            })
            notlar_yaz(notlar)
            st.success("✅ Not kaydedildi!")
            st.rerun()

    # Mevcut notlar
    notlar = notlar_oku()
    if notlar:
        st.markdown("**Son Notlar:**")
        for n in reversed(notlar[-10:]):
            zaman = n["zaman"][:16].replace("T", " ")
            coin_txt = f" [{n['coin']}]" if n.get("coin") else ""
            st.markdown(f"{n['oncelik']} **{zaman}**{coin_txt}: {n['metin']}")


# ══════════════════════════════════════════════════════════
# TAB 5: AYARLAR
# ══════════════════════════════════════════════════════════
with tab5:
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
