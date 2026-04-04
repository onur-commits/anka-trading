"""
🦅 ANKA AI DASHBOARD V2 — Tam Kontrol Merkezi
===============================================
- Portföy anlık takip (pozisyondakiler + potansiyeller)
- Alış/Satış durumu görsel (yüzde + mini grafik)
- 5 Ajan canlı puanları
- Scalper fırsatları
- Robot kontrol (dur/başlat/parametre)
- Rejim göstergesi
- Ajan performans raporu
"""

import streamlit as st
import json
import os
import time
import subprocess
import platform
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="ANKA Dashboard", page_icon="🦅", layout="wide")

BASE_DIR = Path(__file__).parent
IS_WIN = platform.system() == "Windows"
BRIDGE = BASE_DIR / "data" / "v3_bridge.json"
ISLEM_LOG = BASE_DIR / "data" / "islem_gecmisi.json"
AJAN_SKOR = BASE_DIR / "data" / "ajan_skorlari.json"

# Bilinen portföy pozisyonları (robot veya elle alınmış)
PORTFOY_DOSYA = BASE_DIR / "data" / "portfoy_takip.json"


def bridge_oku():
    try:
        if BRIDGE.exists():
            return json.load(open(BRIDGE))
    except:
        pass
    return {}

def bridge_yaz(data):
    with open(BRIDGE, "w") as f:
        json.dump(data, f, indent=4)
    if not IS_WIN:
        try:
            mac_path = str(BRIDGE).replace("/Users/onurbodur/", "\\\\Mac\\Home\\").replace("/", "\\")
            subprocess.run(["prlctl", "exec", "Windows 11", "cmd", "/c",
                           f'copy "{mac_path}" "C:\\Robot\\v3_bridge.json" /Y'],
                          timeout=10, capture_output=True)
        except:
            pass

def bomba_oku():
    # Önce Windows'tan dene
    try:
        if not IS_WIN:
            out = subprocess.run(["prlctl", "exec", "Windows 11", "cmd", "/c",
                                 "type C:\\Robot\\aktif_bombalar.txt"],
                                capture_output=True, text=True, timeout=10).stdout.strip()
            if out:
                return [t.strip() for t in out.split(",") if t.strip()]
    except:
        pass
    # Fallback: lokal dosyadan oku
    try:
        lokal = BASE_DIR / "data" / "aktif_bombalar.txt"
        if lokal.exists():
            return [t.strip() for t in lokal.read_text().strip().split(",") if t.strip()]
    except:
        pass
    # Son çare: otonom state'den oku
    try:
        state_file = BASE_DIR / "data" / "otonom_state.json"
        if state_file.exists():
            state = json.load(open(state_file))
            return state.get("aktif_stratejiler", [])
    except:
        pass
    return []

def bomba_yaz(liste):
    txt = ",".join(liste)
    if not IS_WIN:
        try:
            subprocess.run(["prlctl", "exec", "Windows 11", "cmd", "/c",
                           f'echo {txt} > C:\\Robot\\aktif_bombalar.txt'],
                          timeout=10, capture_output=True)
        except:
            pass

def portfoy_oku():
    """Takip edilen portföy pozisyonlarını oku."""
    if PORTFOY_DOSYA.exists():
        try:
            return json.load(open(PORTFOY_DOSYA))
        except:
            pass
    return {}

def portfoy_yaz(data):
    with open(PORTFOY_DOSYA, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@st.cache_data(ttl=120)  # 2 dakika cache — her seferinde çekmez
def toplu_fiyat_cek(tickers):
    """Tüm hisseleri TEK SEFERDE çek — çok daha hızlı."""
    sonuc = {}
    try:
        # Toplu download — 49 hisseyi tek istekte
        semboller = [f"{t}.IS" for t in tickers]
        df = yf.download(semboller, period="5d", progress=False, group_by="ticker")

        for t in tickers:
            try:
                sym = f"{t}.IS"
                if sym in df.columns.get_level_values(0):
                    hisse = df[sym].dropna()
                elif len(tickers) == 1:
                    hisse = df.dropna()
                else:
                    continue

                if len(hisse) < 2:
                    continue

                son = round(float(hisse['Close'].iloc[-1]), 2)
                onceki = round(float(hisse['Close'].iloc[-2]), 2)
                degisim = round((son / onceki - 1) * 100, 2)
                grafik = [round(float(x), 2) for x in hisse['Close'].tolist()[-10:]]

                hacim = float(hisse['Volume'].iloc[-1])
                ort_hacim = float(hisse['Volume'].mean())
                hacim_oran = round(hacim / ort_hacim, 1) if ort_hacim > 0 else 0

                sonuc[t] = {
                    "fiyat": son,
                    "degisim": degisim,
                    "grafik": grafik,
                    "tavan": degisim > 9.0,
                    "taban": degisim < -9.0,
                    "hacim_oran": hacim_oran,
                }
            except:
                continue
    except:
        pass
    return sonuc

def hisse_detay_cek(ticker):
    """Geriye uyumluluk — tek hisse için."""
    sonuc = toplu_fiyat_cek([ticker])
    return sonuc.get(ticker)


# ── CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
    .stMetric { border: 1px solid #333; border-radius: 8px; padding: 10px; }
    .pozisyon-kart { background: #1a1a2e; border-radius: 10px; padding: 15px; margin: 5px 0; }
    .kar { color: #00ff88; font-weight: bold; }
    .zarar { color: #ff4444; font-weight: bold; }
    .tavan { color: #FFD700; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ── BAŞLIK ──────────────────────────────────────────────────
st.markdown("# 🦅 ANKA AI Dashboard")

bridge = bridge_oku()

# ── ÜST BANT ───────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

with col1:
    rejim = bridge.get("regime", "?")
    rejim_renk = "🟢" if rejim == "BULL" else "🔴" if rejim in ("BEAR", "DANGER_CRASH") else "🟡"
    st.metric("Piyasa Rejimi", f"{rejim_renk} {rejim}",
              f"XU100: {bridge.get('xu100_change', 0):+.1f}% | VIX: {bridge.get('vix', 0)}")

with col2:
    st.metric("Bütçe", f"{bridge.get('pos_value', 0):,.0f} TL", f"Çarpan: {bridge.get('multiplier', 1.0)}x")

with col3:
    aktif = bridge.get("robot_active", True)
    dry = bridge.get("dry_run", False)
    if dry:
        durum_txt = "🔬 SİMÜLASYON"
    elif aktif:
        durum_txt = "🟢 CANLI"
    else:
        durum_txt = "🔴 DURDU"
    st.metric("Robot", durum_txt)

with col4:
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🛑" if aktif else "▶️", use_container_width=True, help="Durdur/Başlat"):
            bridge["robot_active"] = not aktif
            bridge_yaz(bridge)
            st.rerun()
    with col_btn2:
        if st.button("🔬" if not dry else "🔥", use_container_width=True, help="Simülasyon/Canlı"):
            bridge["dry_run"] = not dry
            bridge_yaz(bridge)
            st.rerun()

with col5:
    if st.button("🔄 YENİLE", use_container_width=True):
        st.rerun()

st.divider()

# ── TABLAR ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Portföy & Hisseler", "🦅 Ajan Kararları", "⚡ Scalper", "🪙 Coin", "🎛️ Kontrol", "🧠 Öğrenme"])


# ══════════════════════════════════════════════════════════
# TAB 1: PORTFÖY & TÜM HİSSELER
# ══════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 Portföy Pozisyonları & Bomba Listesi")

    # Portföy yönetimi
    portfoy = portfoy_oku()

    col_ekle, col_sil = st.columns([3, 1])
    with col_ekle:
        yeni_pozisyon = st.text_input("➕ Pozisyon Ekle (örn: GARAN,247,129.10)",
                                       placeholder="HİSSE,ADET,MALİYET")
    with col_sil:
        if st.button("➕ Ekle", use_container_width=True) and yeni_pozisyon:
            parcalar = yeni_pozisyon.split(",")
            if len(parcalar) == 3:
                t, adet, maliyet = parcalar[0].strip().upper(), int(parcalar[1]), float(parcalar[2])
                portfoy[t] = {"adet": adet, "maliyet": maliyet, "kaynak": "manuel"}
                portfoy_yaz(portfoy)
                st.success(f"✅ {t} eklendi")
                st.rerun()

    bombalar = bomba_oku()

    # ROBOTUN İÇİNDEKİ TÜM SEMBOLLER (49 hisse)
    ROBOT_SEMBOLLERI = [
        "GARAN","THYAO","ASELS","TUPRS","EREGL","SISE","TOASO","AKBNK","YKBNK","HALKB",
        "SAHOL","KCHOL","TCELL","BIMAS","PGSUS","TAVHL","FROTO","ARCLK","PETKM","ENKAI",
        "TKFEN","EKGYO","TTKOM","VAKBN","MGROS","DOHOL","GUBRF","ISCTR","AKSEN","AYEN",
        "KONTR","SASA","GESAN","OTKAR","ENJSA","TSKB","SMRTG","CCOLA","CIMSA","KORDS",
        "VESTL","ALARK","HEKTS","ULKER","ASTOR","TTRAK","EGEEN","CEMTS","BRISA"
    ]

    # Filtre
    goster = st.radio("Göster:", [
        "📊 Tümü (49 hisse)",
        "💼 Sadece Portföy",
        "💣 Sadece Bombalar",
        "💼💣 Portföy + Bombalar",
        "🔥 En Yüksek Potansiyel 5",
        "💎 Bomba Olmayan En İyi 5",
    ], horizontal=True)

    # Filtre seçimine göre gösterilecek hisseler
    # "En Yüksek Potansiyel 5" ve "Bomba Olmayan En İyi 5" için hepsini tara sonra filtrele
    tam_tara = goster in ["🔥 En Yüksek Potansiyel 5", "💎 Bomba Olmayan En İyi 5"]

    if goster == "💣 Sadece Bombalar":
        gosterilecek = bombalar
    elif goster == "💼 Sadece Portföy":
        gosterilecek = list(portfoy.keys())
    elif goster == "💼💣 Portföy + Bombalar":
        gosterilecek = list(set(list(portfoy.keys()) + bombalar))
    else:
        gosterilecek = ROBOT_SEMBOLLERI  # Hepsini tara

    if gosterilecek:
        st.markdown("---")

        # Stop/Trailing parametreleri (bridge'den)
        hard_stop_pct = float(bridge.get("hard_stop", 3.5))
        trailing_pct = float(bridge.get("trailing_stop", 1.8))
        profit_trigger_pct = float(bridge.get("profit_trigger", 1.2))

        with st.spinner(f"{len(gosterilecek)} hisse yükleniyor..."):
            # TOPLU ÇEKİM — tek istekte 49 hisse
            tum_fiyatlar = toplu_fiyat_cek(gosterilecek)

            satirlar = []
            for t in gosterilecek:
                detay = tum_fiyatlar.get(t)
                if detay is None:
                    continue

                pozisyonda = t in portfoy
                bombada = t in bombalar
                poz = portfoy.get(t, {})

                fiyat = detay["fiyat"]

                # K/Z hesapla
                kz = 0
                kz_pct = 0
                maliyet = poz.get("maliyet", 0)
                if pozisyonda and maliyet > 0:
                    kz = round((fiyat - maliyet) * poz.get("adet", 0), 2)
                    kz_pct = round((fiyat / maliyet - 1) * 100, 2)

                # AL/SAT sinyal mesafesi hesapla
                sinyal_mesafe = ""
                sinyal_bar = 0  # -100 ile +100 arası (negatif=sata yakın, pozitif=ala yakın)

                if pozisyonda and maliyet > 0:
                    # Stop fiyatı
                    stop_fiyat = maliyet * (1 - hard_stop_pct / 100)
                    # Trailing (kârdaysa)
                    if kz_pct >= profit_trigger_pct:
                        trail_fiyat = fiyat * (1 - trailing_pct / 100)  # zirveden
                        stop_fiyat = max(stop_fiyat, trail_fiyat)

                    stop_mesafe = round((fiyat - stop_fiyat) / fiyat * 100, 1)
                    sinyal_mesafe = f"🛑 Stop'a %{stop_mesafe} | Stop: {stop_fiyat:.2f} TL"
                    sinyal_bar = -int(min(100, (1 - stop_mesafe / hard_stop_pct) * 100))

                    if kz_pct >= profit_trigger_pct:
                        sinyal_mesafe += f" | 🎯 Trailing aktif!"
                else:
                    # Pozisyonda değil — değişime göre basit sinyal
                    if detay["degisim"] > 2:
                        sinyal_mesafe = f"🟢 Güçlü yükseliş +%{detay['degisim']:.1f}"
                        sinyal_bar = 70
                    elif detay["degisim"] > 0:
                        sinyal_mesafe = f"🟡 Hafif yukarı +%{detay['degisim']:.1f}"
                        sinyal_bar = 40
                    elif detay["degisim"] > -2:
                        sinyal_mesafe = f"⚪ Hafif aşağı %{detay['degisim']:.1f}"
                        sinyal_bar = 20
                    else:
                        sinyal_mesafe = f"🔴 Düşüşte %{detay['degisim']:.1f}"
                        sinyal_bar = -20

                # Durum ikonu
                if detay["tavan"]:
                    durum = "🔒 TAVAN"
                elif detay["taban"]:
                    durum = "🔻 TABAN"
                elif pozisyonda and kz > 0:
                    durum = "🟢 KÂRDA"
                elif pozisyonda and kz < 0:
                    durum = "🔴 ZARARDA"
                elif bombada and not pozisyonda:
                    durum = "👁️ BOMBA"
                else:
                    durum = "⚪ İZLENİYOR"

                satirlar.append({
                    "ticker": t,
                    "fiyat": fiyat,
                    "degisim": detay["degisim"],
                    "hacim": detay["hacim_oran"],
                    "pozisyonda": pozisyonda,
                    "bombada": bombada,
                    "adet": poz.get("adet", 0),
                    "maliyet": maliyet,
                    "kz": kz,
                    "kz_pct": kz_pct,
                    "durum": durum,
                    "sinyal_mesafe": sinyal_mesafe,
                    "sinyal_bar": sinyal_bar,
                    "grafik": detay["grafik"],
                    "tavan": detay["tavan"],
                })

            # Sırala: pozisyondakiler üstte, sonra bomba, sonra sinyal yakınlığına göre
            satirlar.sort(key=lambda x: (
                0 if x["pozisyonda"] else 1,
                0 if x["bombada"] else 1,
                -x["sinyal_bar"]
            ))

            # Özel filtreler
            if goster == "🔥 En Yüksek Potansiyel 5":
                satirlar.sort(key=lambda x: -x["sinyal_bar"])
                satirlar = satirlar[:5]
            elif goster == "💎 Bomba Olmayan En İyi 5":
                sadece_bomba_olmayan = [s for s in satirlar if not s["bombada"] and not s["pozisyonda"]]
                sadece_bomba_olmayan.sort(key=lambda x: -x["sinyal_bar"])
                satirlar = sadece_bomba_olmayan[:5]

            # TABLO OLARAK GÖSTER (hızlı, kasmaz)
            tablo_data = []
            for row in satirlar:
                etiket = ""
                if row["bombada"]: etiket += "💣"
                if row["pozisyonda"]: etiket += "💼"
                if row["tavan"]: etiket += "🔒"

                kz_txt = f"{row['kz']:+.0f} TL ({row['kz_pct']:+.1f}%)" if row["pozisyonda"] else ""
                poz_txt = f"{row['adet']} lot @ {row['maliyet']}" if row["pozisyonda"] else ""

                tablo_data.append({
                    "": etiket,
                    "Hisse": row["ticker"],
                    "Fiyat": row["fiyat"],
                    "Gün %": row["degisim"],
                    "Hacim": f"x{row['hacim']}",
                    "Durum": row["durum"],
                    "Pozisyon": poz_txt,
                    "K/Z": kz_txt,
                    "Sinyal": row["sinyal_mesafe"][:50] if row["sinyal_mesafe"] else "",
                })

            df_tablo = pd.DataFrame(tablo_data)

            st.dataframe(
                df_tablo.style.applymap(
                    lambda x: "color: #00ff88" if isinstance(x, (int, float)) and x > 0
                    else "color: #ff4444" if isinstance(x, (int, float)) and x < 0
                    else "", subset=["Gün %"]
                ),
                use_container_width=True,
                hide_index=True,
                height=min(800, len(tablo_data) * 38 + 40)
            )

            # ÖZET
            st.markdown("---")
            pozisyondakiler = [s for s in satirlar if s["pozisyonda"]]
            if pozisyondakiler:
                toplam_kz = sum(s["kz"] for s in pozisyondakiler)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Toplam K/Z", f"{toplam_kz:+,.0f} TL")
                with col2:
                    st.metric("Pozisyon Sayısı", len(pozisyondakiler))
                with col3:
                    al_yakin = sum(1 for s in satirlar if not s["pozisyonda"] and s["sinyal_bar"] > 60)
                    st.metric("AL Sinyaline Yakın", f"{al_yakin} hisse")

    else:
        st.info("Gösterilecek hisse yok")

    # Hızlı pozisyon silme
    with st.expander("🗑️ Pozisyon Sil"):
        for t in list(portfoy.keys()):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"{t}: {portfoy[t].get('adet', '?')} lot @ {portfoy[t].get('maliyet', '?')}")
            with col2:
                if st.button(f"Sil {t}", key=f"sil_{t}"):
                    del portfoy[t]
                    portfoy_yaz(portfoy)
                    st.rerun()


# ══════════════════════════════════════════════════════════
# TAB 2: AJAN KARARLARI
# ══════════════════════════════════════════════════════════
with tab2:
    st.subheader("🦅 5 Ajan Karar Paneli")

    if st.button("🔄 Ajanları Çalıştır", use_container_width=True):
        with st.spinner("5 ajan çalışıyor..."):
            try:
                r = subprocess.run([".venv/bin/python", "borsa_surpriz/anka_v2.py"],
                                  capture_output=True, text=True, timeout=300,
                                  cwd=str(BASE_DIR.parent))
                st.session_state["ajan_sonuc"] = r.stdout
            except Exception as e:
                st.error(str(e))

    if "ajan_sonuc" in st.session_state:
        lines = st.session_state["ajan_sonuc"].split("\n")
        for line in lines:
            if "💣" in line:
                st.success(line.strip())
            elif "VETO" in line:
                st.warning(line.strip())
            elif "REJİM" in line or "===" in line or "BOMBALAR" in line:
                st.info(line.strip())
            elif line.strip():
                st.text(line.strip())


# ══════════════════════════════════════════════════════════
# TAB 3: SCALPER
# ══════════════════════════════════════════════════════════
with tab3:
    st.subheader("⚡ Gün İçi Scalper Fırsatları")

    if st.button("⚡ Scalp Tara", use_container_width=True):
        with st.spinner("Scalper çalışıyor..."):
            try:
                r = subprocess.run([".venv/bin/python", "borsa_surpriz/anka_scalper.py"],
                                  capture_output=True, text=True, timeout=300,
                                  cwd=str(BASE_DIR.parent))
                st.session_state["scalp_sonuc"] = r.stdout
            except Exception as e:
                st.error(str(e))

    if "scalp_sonuc" in st.session_state:
        lines = st.session_state["scalp_sonuc"].split("\n")
        for line in lines:
            if "⚡" in line and "|" in line:
                st.success(line.strip())
            elif "FIRSATLARI" in line:
                st.info(line.strip())
            elif line.strip():
                st.text(line.strip())


# ══════════════════════════════════════════════════════════
# TAB 4: COIN
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("🪙 Kripto Piyasası")

    if st.button("🪙 Coin Tara", use_container_width=True):
        with st.spinner("15 coin taranıyor..."):
            try:
                sys.path.insert(0, str(BASE_DIR))
                from coin_trader import CoinBrain
                brain = CoinBrain()
                bombalar = brain.tara()

                if bombalar:
                    df_coin = pd.DataFrame(bombalar)
                    df_coin["fiyat"] = df_coin["fiyat"].apply(lambda x: f"${x:,.2f}")
                    df_coin["skor"] = df_coin["skor"].apply(lambda x: f"{x:.0f}")
                    st.dataframe(df_coin, use_container_width=True, hide_index=True)
                else:
                    st.info("Şu an bomba coin yok")
            except Exception as e:
                st.error(str(e))

    # Roket Tarayıcı
    if st.button("🚀 ROKET TARA (Hacim Patlaması)", use_container_width=True):
        with st.spinner("46 coin taranıyor..."):
            try:
                sys.path.insert(0, str(BASE_DIR))
                from coin_trader import RoketTarayici
                tarayici = RoketTarayici()
                roketler = tarayici.hacim_patlama_tara(esik=2.0)
                if roketler:
                    df_roket = pd.DataFrame(roketler)
                    st.dataframe(df_roket[["symbol","fiyat","hacim_x","degisim_24s","degisim_1s","skor","sebep"]],
                                use_container_width=True, hide_index=True)
                else:
                    st.info("Şu an roket yok — piyasa sakin")
            except Exception as e:
                st.error(str(e))

    st.divider()

    # Hızlı fiyat tablosu
    st.markdown("**Anlık Fiyatlar:**")
    try:
        import requests as req
        coins_quick = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","AVAXUSDT"]
        rows = []
        for sym in coins_quick:
            try:
                r = req.get(f"https://api.binance.com/api/v3/ticker/24hr", params={"symbol": sym}, timeout=5)
                d = r.json()
                rows.append({
                    "Coin": sym.replace("USDT",""),
                    "Fiyat": f"${float(d['lastPrice']):,.2f}",
                    "24s %": f"{float(d['priceChangePercent']):+.1f}%",
                    "Hacim": f"${float(d['quoteVolume'])/1e6:,.0f}M",
                })
            except:
                continue
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    except:
        st.info("Binance verisi alınamadı")


# ══════════════════════════════════════════════════════════
# TAB 5: KONTROL (eski tab4)
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("🎛️ Robot Kontrol Paneli")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Bütçe & Risk**")
        yeni_butce = st.number_input("💰 Pozisyon Bütçesi (TL)", 1000, 100000, int(bridge.get("pos_value", 16000)), 1000)
        yeni_carpan = st.slider("📊 Çarpan", 0.0, 2.0, float(bridge.get("multiplier", 1.0)), 0.1)
        yeni_rejim = st.selectbox("🎭 Rejim",
                                  ["BULL", "SIDEWAYS", "BEAR", "DANGER_CRASH"],
                                  index=["BULL", "SIDEWAYS", "BEAR", "DANGER_CRASH"].index(
                                      bridge.get("regime", "SIDEWAYS")) if bridge.get("regime") in
                                      ["BULL", "SIDEWAYS", "BEAR", "DANGER_CRASH"] else 1)

    with col2:
        st.markdown("**Stop & Trailing**")
        yeni_stop = st.number_input("🛑 Hard Stop %", 0.5, 10.0, float(bridge.get("hard_stop", 3.5)), 0.5)
        yeni_trail = st.number_input("📉 Trailing Stop %", 0.1, 5.0, float(bridge.get("trailing_stop", 1.8)), 0.1)
        yeni_profit = st.number_input("🎯 Kâr Tetikleyici %", 0.1, 5.0, float(bridge.get("profit_trigger", 1.2)), 0.1)

    st.markdown("**Sembol Listesi**")
    mevcut = ",".join(bomba_oku())
    yeni_bombalar = st.text_input("Bomba Listesi", value=mevcut)

    if st.button("💾 KAYDET & UYGULA", type="primary", use_container_width=True):
        bridge["pos_value"] = yeni_butce
        bridge["multiplier"] = yeni_carpan
        bridge["regime"] = yeni_rejim
        bridge["hard_stop"] = yeni_stop
        bridge["trailing_stop"] = yeni_trail
        bridge["profit_trigger"] = yeni_profit
        bridge["last_update"] = datetime.now().strftime("%H:%M:%S")
        bridge_yaz(bridge)
        bomba_yaz([t.strip() for t in yeni_bombalar.split(",") if t.strip()])
        st.success("✅ Kaydedildi!")
        st.balloons()


# ══════════════════════════════════════════════════════════
# TAB 5: ÖĞRENME
# ══════════════════════════════════════════════════════════
with tab5:
    st.subheader("🧠 Ajan Öğrenme Raporu")

    if AJAN_SKOR.exists():
        try:
            skorlar = json.load(open(AJAN_SKOR))
            if skorlar:
                df_ajan = pd.DataFrame([
                    {"Ajan": ad, "Doğru": s.get("dogru", 0), "Yanlış": s.get("yanlis", 0),
                     "Güven %": s.get("guven", 50), "Toplam": s.get("toplam", 0)}
                    for ad, s in skorlar.items()
                ])
                st.dataframe(df_ajan, use_container_width=True, hide_index=True)
                st.bar_chart(df_ajan.set_index("Ajan")["Güven %"])
        except:
            pass
    else:
        st.info("Henüz öğrenme verisi yok")


# ── SIDEBAR ─────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("**🦅 ANKA V2**")
st.sidebar.markdown(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
st.sidebar.markdown(f"📊 {bridge.get('regime', '?')} | XU100: {bridge.get('xu100_change', 0):+.1f}%")
st.sidebar.markdown(f"💰 {bridge.get('pos_value', '?')} TL × {bridge.get('multiplier', 1.0)}x")

if st.sidebar.button("🔄 Yenile"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("[🦅 ANKA Borsa](http://localhost:8501)")
st.sidebar.markdown("[🪙 COIN Kripto](http://localhost:8502)")
