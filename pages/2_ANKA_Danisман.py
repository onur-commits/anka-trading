"""
ANKA Danışman — Yerleşik Zeka Sohbet Paneli
=============================================
Sen yokken ajanlarla konuş, hisse hakkında görüş al.
4 ajan (TECHNO, VOLUME, MACRO, FUNDA) analiz yapar,
komisyon dahil net kâr hesabı gösterir, nihai karar verir.
"""

import sys
import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from anka_panel_kurallari import KomisyonKontrol

# ============================================================
# AJAN TANIMLARI
# ============================================================

AJAN_BILGI = {
    "TECHNO": {
        "isim": "TECHNO — Teknik Analist",
        "ikon": "📊",
        "aciklama": "EMA, RSI, MACD, Bollinger, formasyon analizi",
    },
    "VOLUME": {
        "isim": "VOLUME — Hacim Uzmanı",
        "ikon": "📈",
        "aciklama": "OBV, hacim profili, kurumsal akış, arz-talep",
    },
    "MACRO": {
        "isim": "MACRO — Makro Stratejist",
        "ikon": "🌍",
        "aciklama": "XU100 rejim, sektör rotasyonu, döviz, faiz",
    },
    "FUNDA": {
        "isim": "FUNDA — Temel Analist",
        "ikon": "💎",
        "aciklama": "F/K, PD/DD, kârlılık, bilanço, temettü",
    },
}

# ============================================================
# TEKNİK ANALİZ FONKSİYONLARI
# ============================================================

def veri_cek(ticker, period="6mo"):
    """Yahoo Finance'den veri çek."""
    t = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
    try:
        df = yf.download(t, period=period, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return None


def teknik_hesapla(df):
    """Tüm teknik indikatörleri hesapla."""
    c = df["Close"].values.flatten()
    h = df["High"].values.flatten()
    l = df["Low"].values.flatten()
    v = df["Volume"].values.flatten()

    sonuc = {}

    # EMA'lar
    def ema(data, n):
        s = pd.Series(data)
        return s.ewm(span=n, adjust=False).mean().values

    ema8 = ema(c, 8)
    ema21 = ema(c, 21)
    ema50 = ema(c, 50)
    sma200 = pd.Series(c).rolling(200).mean().values

    sonuc["fiyat"] = round(float(c[-1]), 2)
    sonuc["ema8"] = round(float(ema8[-1]), 2)
    sonuc["ema21"] = round(float(ema21[-1]), 2)
    sonuc["ema50"] = round(float(ema50[-1]), 2)
    sonuc["sma200"] = round(float(sma200[-1]), 2) if not np.isnan(sma200[-1]) else None
    sonuc["ema_trend"] = "YUKARI" if ema8[-1] > ema21[-1] > ema50[-1] else (
        "ASAGI" if ema8[-1] < ema21[-1] < ema50[-1] else "KARISIK"
    )

    # RSI
    delta = pd.Series(c).diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    sonuc["rsi14"] = round(float(rsi.iloc[-1]), 1)

    rsi7_delta = pd.Series(c).diff()
    gain7 = rsi7_delta.where(rsi7_delta > 0, 0).rolling(7).mean()
    loss7 = (-rsi7_delta.where(rsi7_delta < 0, 0)).rolling(7).mean()
    rs7 = gain7 / loss7
    rsi7 = 100 - (100 / (1 + rs7))
    sonuc["rsi7"] = round(float(rsi7.iloc[-1]), 1)

    # MACD
    ema12 = ema(c, 12)
    ema26 = ema(c, 26)
    macd_line = ema12 - ema26
    signal = ema(macd_line, 9)
    sonuc["macd"] = round(float(macd_line[-1]), 4)
    sonuc["macd_signal"] = round(float(signal[-1]), 4)
    sonuc["macd_hist"] = round(float(macd_line[-1] - signal[-1]), 4)
    sonuc["macd_yonu"] = "YUKARI" if macd_line[-1] > signal[-1] else "ASAGI"

    # Bollinger
    sma20 = pd.Series(c).rolling(20).mean()
    std20 = pd.Series(c).rolling(20).std()
    boll_ust = sma20 + 2 * std20
    boll_alt = sma20 - 2 * std20
    boll_gen = ((boll_ust - boll_alt) / sma20 * 100)
    sonuc["boll_ust"] = round(float(boll_ust.iloc[-1]), 2)
    sonuc["boll_alt"] = round(float(boll_alt.iloc[-1]), 2)
    bw = float(boll_gen.iloc[-1])
    sonuc["boll_genislik"] = round(bw, 2)
    if bw < 5:
        sonuc["boll_durum"] = "SIKISMA"
    elif c[-1] > float(boll_ust.iloc[-1]):
        sonuc["boll_durum"] = "UST BAND USTU"
    elif c[-1] < float(boll_alt.iloc[-1]):
        sonuc["boll_durum"] = "ALT BAND ALTI"
    else:
        sonuc["boll_durum"] = "BANT ICI"

    # ATR
    tr = pd.DataFrame({
        "hl": h - l,
        "hc": abs(h - np.roll(c, 1)),
        "lc": abs(l - np.roll(c, 1)),
    }).max(axis=1)
    atr14 = tr.rolling(14).mean()
    sonuc["atr"] = round(float(atr14.iloc[-1]), 2)
    sonuc["atr_pct"] = round(float(atr14.iloc[-1]) / c[-1] * 100, 2)

    # Hacim
    vol_avg20 = pd.Series(v).rolling(20).mean()
    sonuc["hacim_son"] = int(v[-1])
    sonuc["hacim_ort20"] = int(vol_avg20.iloc[-1]) if not np.isnan(vol_avg20.iloc[-1]) else 0
    sonuc["rvol"] = round(float(v[-1] / vol_avg20.iloc[-1]), 2) if vol_avg20.iloc[-1] > 0 else 0

    # OBV Trend
    obv = pd.Series(np.where(pd.Series(c).diff() > 0, v, np.where(pd.Series(c).diff() < 0, -v, 0))).cumsum()
    obv_ema = obv.ewm(span=20, adjust=False).mean()
    sonuc["obv_trend"] = "BIRIKIM" if obv.iloc[-1] > obv_ema.iloc[-1] else "DAGITIM"

    # Son 5 gün getiri
    if len(c) >= 6:
        sonuc["getiri_5g"] = round(float((c[-1] / c[-6] - 1) * 100), 2)
    else:
        sonuc["getiri_5g"] = 0

    # Son 20 gün getiri
    if len(c) >= 21:
        sonuc["getiri_20g"] = round(float((c[-1] / c[-21] - 1) * 100), 2)
    else:
        sonuc["getiri_20g"] = 0

    return sonuc


# ============================================================
# AJAN ANALİZLERİ
# ============================================================

def techno_analiz(teknik):
    """TECHNO ajanı — teknik analiz görüşü."""
    puan = 50
    gorusler = []

    # EMA Trend
    if teknik["ema_trend"] == "YUKARI":
        puan += 15
        gorusler.append("✅ EMA dizilimi yukarı (8>21>50) — güçlü trend")
    elif teknik["ema_trend"] == "ASAGI":
        puan -= 15
        gorusler.append("❌ EMA dizilimi aşağı — düşüş trendi")
    else:
        gorusler.append("⚠️ EMA'lar karışık — net trend yok")

    # RSI
    rsi = teknik["rsi14"]
    if rsi > 70:
        puan -= 10
        gorusler.append(f"⚠️ RSI {rsi} — aşırı alım bölgesi, geri çekilme riski")
    elif rsi < 30:
        puan += 10
        gorusler.append(f"✅ RSI {rsi} — aşırı satım, dipten dönüş potansiyeli")
    elif rsi > 50:
        puan += 5
        gorusler.append(f"📊 RSI {rsi} — pozitif momentum")
    else:
        puan -= 5
        gorusler.append(f"📊 RSI {rsi} — negatif momentum")

    # MACD
    if teknik["macd_yonu"] == "YUKARI":
        puan += 10
        gorusler.append(f"✅ MACD sinyal üstünde — alım sinyali")
    else:
        puan -= 10
        gorusler.append(f"❌ MACD sinyal altında — satım sinyali")

    # Bollinger
    bd = teknik["boll_durum"]
    if bd == "SIKISMA":
        puan += 5
        gorusler.append("🔥 Bollinger sıkışması — büyük hareket yakın")
    elif bd == "ALT BAND ALTI":
        puan += 8
        gorusler.append("✅ Bollinger alt band altı — potansiyel dip")
    elif bd == "UST BAND USTU":
        puan -= 5
        gorusler.append("⚠️ Bollinger üst band üstü — aşırı genişleme")

    # SMA200
    if teknik.get("sma200") and teknik["fiyat"] > teknik["sma200"]:
        puan += 5
        gorusler.append("✅ 200 günlük ortalama üstünde — uzun vade pozitif")
    elif teknik.get("sma200"):
        puan -= 5
        gorusler.append("❌ 200 günlük ortalama altında — uzun vade negatif")

    puan = max(0, min(100, puan))
    karar = "AL" if puan >= 65 else ("SAT" if puan <= 35 else "BEKLE")
    return {"puan": puan, "karar": karar, "gorusler": gorusler}


def volume_analiz(teknik):
    """VOLUME ajanı — hacim analizi."""
    puan = 50
    gorusler = []

    # RVOL
    rvol = teknik["rvol"]
    if rvol > 2.0:
        puan += 15
        gorusler.append(f"🔥 Hacim patlaması! {rvol}x ortalama — büyük ilgi")
    elif rvol > 1.5:
        puan += 10
        gorusler.append(f"📈 Hacim ortalamanın {rvol}x üstünde — artan ilgi")
    elif rvol < 0.5:
        puan -= 10
        gorusler.append(f"⚠️ Hacim çok düşük ({rvol}x) — ilgisizlik")
    else:
        gorusler.append(f"📊 Hacim normal ({rvol}x)")

    # OBV
    if teknik["obv_trend"] == "BIRIKIM":
        puan += 15
        gorusler.append("✅ OBV birikim — kurumsal alım sinyali")
    else:
        puan -= 10
        gorusler.append("❌ OBV dağıtım — kurumsal satış sinyali")

    # Hacim + Fiyat uyumu
    if teknik["getiri_5g"] > 0 and rvol > 1.2:
        puan += 10
        gorusler.append("✅ Yükseliş + artan hacim — sağlıklı hareket")
    elif teknik["getiri_5g"] < 0 and rvol > 1.5:
        puan -= 10
        gorusler.append("❌ Düşüş + yüksek hacim — panik satış riski")
    elif teknik["getiri_5g"] > 0 and rvol < 0.7:
        puan -= 5
        gorusler.append("⚠️ Yükseliş ama düşük hacim — güvenilmez hareket")

    puan = max(0, min(100, puan))
    karar = "AL" if puan >= 65 else ("SAT" if puan <= 35 else "BEKLE")
    return {"puan": puan, "karar": karar, "gorusler": gorusler}


def macro_analiz(teknik):
    """MACRO ajanı — makro/endeks filtresi."""
    puan = 50
    gorusler = []

    # XU100 kontrolü
    try:
        xu = yf.download("XU100.IS", period="3mo", progress=False)
        if isinstance(xu.columns, pd.MultiIndex):
            xu.columns = xu.columns.get_level_values(0)
        xu_c = xu["Close"].values.flatten()
        xu_ema8 = pd.Series(xu_c).ewm(span=8, adjust=False).mean().values
        xu_ema21 = pd.Series(xu_c).ewm(span=21, adjust=False).mean().values

        if xu_ema8[-1] > xu_ema21[-1]:
            puan += 15
            gorusler.append("✅ XU100 trendi yukarı — piyasa desteği var")
        else:
            puan -= 15
            gorusler.append("❌ XU100 trendi aşağı — piyasa baskısı")

        xu_ret5 = (xu_c[-1] / xu_c[-6] - 1) * 100 if len(xu_c) >= 6 else 0
        if xu_ret5 > 2:
            puan += 5
            gorusler.append(f"📈 XU100 son 5 gün: %{xu_ret5:.1f} — güçlü piyasa")
        elif xu_ret5 < -2:
            puan -= 5
            gorusler.append(f"📉 XU100 son 5 gün: %{xu_ret5:.1f} — zayıf piyasa")
    except Exception:
        gorusler.append("⚠️ XU100 verisi alınamadı")

    # ATR (volatilite)
    atr_pct = teknik["atr_pct"]
    if atr_pct > 5:
        puan -= 5
        gorusler.append(f"⚠️ ATR %{atr_pct} — yüksek volatilite, risk fazla")
    elif atr_pct < 2:
        puan += 5
        gorusler.append(f"✅ ATR %{atr_pct} — düşük volatilite, stabil")
    else:
        gorusler.append(f"📊 ATR %{atr_pct} — normal volatilite")

    # Getiri momentumu
    g20 = teknik.get("getiri_20g", 0)
    if g20 > 10:
        puan += 5
        gorusler.append(f"✅ 20 günlük getiri %{g20} — güçlü momentum")
    elif g20 < -10:
        puan -= 5
        gorusler.append(f"❌ 20 günlük getiri %{g20} — düşüş baskısı")

    puan = max(0, min(100, puan))
    karar = "AL" if puan >= 65 else ("SAT" if puan <= 35 else "BEKLE")
    return {"puan": puan, "karar": karar, "gorusler": gorusler}


def funda_analiz(ticker):
    """FUNDA ajanı — temel analiz."""
    puan = 50
    gorusler = []

    t = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
    try:
        info = yf.Ticker(t).info
    except Exception:
        return {"puan": 50, "karar": "BEKLE", "gorusler": ["⚠️ Temel veri alınamadı"]}

    # F/K
    pe = info.get("trailingPE") or info.get("forwardPE")
    if pe:
        if pe < 8:
            puan += 15
            gorusler.append(f"✅ F/K: {pe:.1f} — çok ucuz")
        elif pe < 15:
            puan += 5
            gorusler.append(f"📊 F/K: {pe:.1f} — makul değerleme")
        elif pe > 30:
            puan -= 10
            gorusler.append(f"❌ F/K: {pe:.1f} — pahalı")
        else:
            gorusler.append(f"📊 F/K: {pe:.1f}")
    else:
        gorusler.append("⚠️ F/K verisi yok")

    # PD/DD
    pb = info.get("priceToBook")
    if pb:
        if pb < 1:
            puan += 10
            gorusler.append(f"✅ PD/DD: {pb:.2f} — defter değeri altında")
        elif pb < 2:
            puan += 5
            gorusler.append(f"📊 PD/DD: {pb:.2f} — makul")
        elif pb > 5:
            puan -= 5
            gorusler.append(f"⚠️ PD/DD: {pb:.2f} — yüksek")

    # Kâr marjı
    margin = info.get("profitMargins")
    if margin:
        m_pct = margin * 100
        if m_pct > 20:
            puan += 10
            gorusler.append(f"✅ Kâr marjı: %{m_pct:.1f} — yüksek kârlılık")
        elif m_pct > 10:
            puan += 5
            gorusler.append(f"📊 Kâr marjı: %{m_pct:.1f}")
        elif m_pct < 0:
            puan -= 10
            gorusler.append(f"❌ Kâr marjı: %{m_pct:.1f} — zarar")

    # Temettü
    div = info.get("dividendYield")
    if div and div > 0.03:
        puan += 5
        gorusler.append(f"✅ Temettü verimi: %{div*100:.1f}")

    # Piyasa değeri
    mcap = info.get("marketCap")
    if mcap:
        if mcap > 50e9:
            gorusler.append(f"📊 Piyasa değeri: {mcap/1e9:.0f} milyar TL — büyük şirket")
        elif mcap > 10e9:
            gorusler.append(f"📊 Piyasa değeri: {mcap/1e9:.0f} milyar TL — orta boy")
        else:
            gorusler.append(f"📊 Piyasa değeri: {mcap/1e9:.1f} milyar TL — küçük şirket")

    puan = max(0, min(100, puan))
    karar = "AL" if puan >= 65 else ("SAT" if puan <= 35 else "BEKLE")
    return {"puan": puan, "karar": karar, "gorusler": gorusler}


# ============================================================
# KOMİSYON DAHİL FİNAL KARAR
# ============================================================

def nihai_karar(techno, volume, macro, funda, teknik):
    """4 ajanın oylarını birleştir, komisyon dahil karar ver."""
    # Ağırlıklı ortalama (FUNDA %30, TECHNO %25, VOLUME %25, MACRO %20)
    agirlikli = (
        funda["puan"] * 0.30 +
        techno["puan"] * 0.25 +
        volume["puan"] * 0.25 +
        macro["puan"] * 0.20
    )

    # Komisyon kontrolü
    beklenen_getiri = teknik["atr_pct"] * 0.4  # ATR'nin %40'ı beklenen hareket
    komisyon_ok, net_getiri = KomisyonKontrol.karli_mi(beklenen_getiri)
    min_hedef = KomisyonKontrol.minimum_kar_hedefi()

    # Karar
    if agirlikli >= 65 and komisyon_ok:
        karar = "AL"
        renk = "green"
    elif agirlikli <= 35:
        karar = "SAT"
        renk = "red"
    elif agirlikli >= 60 and not komisyon_ok:
        karar = "BEKLE — komisyon yüksek"
        renk = "orange"
    else:
        karar = "BEKLE"
        renk = "orange"

    # Veto: 3+ ajan SAT diyorsa AL deme
    sat_sayisi = sum(1 for a in [techno, volume, macro, funda] if a["karar"] == "SAT")
    if sat_sayisi >= 3 and karar == "AL":
        karar = "BEKLE — çoklu veto"
        renk = "orange"

    return {
        "karar": karar,
        "renk": renk,
        "toplam_puan": round(agirlikli, 1),
        "komisyon_ok": komisyon_ok,
        "net_getiri": round(net_getiri, 2),
        "min_hedef": round(min_hedef, 2),
        "beklenen_getiri": round(beklenen_getiri, 2),
    }


# ============================================================
# STREAMLIT ARAYÜZÜ
# ============================================================

st.set_page_config(page_title="ANKA Danışman", page_icon="🦅", layout="wide")
st.title("🦅 ANKA Danışman")
st.caption("Ajanlarla konuş, hisse hakkında görüş al — komisyon dahil net analiz")

# Session state
if "gecmis" not in st.session_state:
    st.session_state.gecmis = []

# Giriş
col1, col2 = st.columns([2, 1])
with col1:
    ticker_input = st.text_input(
        "Hisse kodu gir:",
        placeholder="Örn: GARAN, THYAO, ASELS",
        key="ticker_box",
    ).strip().upper()

with col2:
    analiz_btn = st.button("🔍 Analiz Et", type="primary", use_container_width=True)

if analiz_btn and ticker_input:
    ticker = ticker_input.replace(".IS", "")

    with st.spinner(f"🔄 {ticker} analiz ediliyor..."):
        # Veri çek
        df = veri_cek(ticker)
        if df is None or len(df) < 30:
            st.error(f"❌ {ticker} için yeterli veri bulunamadı. Hisse kodunu kontrol et.")
            st.stop()

        # Teknik hesapla
        teknik = teknik_hesapla(df)

        # 4 ajan analiz
        t_result = techno_analiz(teknik)
        v_result = volume_analiz(teknik)
        m_result = macro_analiz(teknik)
        f_result = funda_analiz(ticker)

        # Nihai karar
        final = nihai_karar(t_result, v_result, m_result, f_result, teknik)

    # ============================================================
    # SONUÇ GÖSTER
    # ============================================================

    st.divider()

    # Ana karar
    st.markdown(f"## {ticker} — Fiyat: {teknik['fiyat']} TL")

    karar_emoji = {"AL": "🟢", "SAT": "🔴"}.get(final["karar"].split(" ")[0], "🟡")
    st.markdown(
        f"### {karar_emoji} Nihai Karar: **{final['karar']}** "
        f"(Toplam Puan: **{final['toplam_puan']}/100**)"
    )

    # Komisyon bilgisi
    with st.expander("💰 Komisyon Analizi", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Beklenen Getiri", f"%{final['beklenen_getiri']}")
        c2.metric("Komisyon Maliyeti", f"%{final['min_hedef']}")
        c3.metric("Net Getiri", f"%{final['net_getiri']}", delta=f"%{final['net_getiri']}")
        if not final["komisyon_ok"]:
            st.warning("⚠️ Komisyon sonrası net getiri negatif — bu işlem komisyonu karşılamaz!")

    # 4 Ajan kartları
    st.markdown("### 🤖 Ajan Görüşleri")
    cols = st.columns(4)

    for i, (ajan_key, result) in enumerate([
        ("TECHNO", t_result), ("VOLUME", v_result),
        ("MACRO", m_result), ("FUNDA", f_result),
    ]):
        info = AJAN_BILGI[ajan_key]
        with cols[i]:
            karar_renk = {"AL": "🟢", "SAT": "🔴", "BEKLE": "🟡"}[result["karar"]]
            st.markdown(f"**{info['ikon']} {ajan_key}**")
            st.markdown(f"Puan: **{result['puan']}/100** {karar_renk} {result['karar']}")
            for g in result["gorusler"]:
                st.markdown(f"- {g}")

    # Teknik özet
    with st.expander("📊 Teknik Detaylar"):
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("RSI-14", teknik["rsi14"])
        t2.metric("RSI-7", teknik["rsi7"])
        t3.metric("MACD", teknik["macd_hist"], delta="Yukarı" if teknik["macd_yonu"] == "YUKARI" else "Aşağı")
        t4.metric("ATR %", f"{teknik['atr_pct']}%")

        t5, t6, t7, t8 = st.columns(4)
        t5.metric("EMA Trend", teknik["ema_trend"])
        t6.metric("Bollinger", teknik["boll_durum"])
        t7.metric("Hacim (RVOL)", f"{teknik['rvol']}x")
        t8.metric("OBV", teknik["obv_trend"])

        t9, t10, t11, t12 = st.columns(4)
        t9.metric("5G Getiri", f"%{teknik['getiri_5g']}")
        t10.metric("20G Getiri", f"%{teknik.get('getiri_20g', 0)}")
        t11.metric("EMA8", teknik["ema8"])
        t12.metric("EMA21", teknik["ema21"])

    # Geçmişe kaydet
    kayit = {
        "zaman": datetime.now().strftime("%H:%M"),
        "ticker": ticker,
        "karar": final["karar"],
        "puan": final["toplam_puan"],
        "fiyat": teknik["fiyat"],
    }
    st.session_state.gecmis.insert(0, kayit)
    st.session_state.gecmis = st.session_state.gecmis[:20]  # Son 20

# Geçmiş sorular
if st.session_state.gecmis:
    st.divider()
    st.markdown("### 📜 Geçmiş Analizler")
    for k in st.session_state.gecmis:
        emoji = {"AL": "🟢", "SAT": "🔴"}.get(k["karar"].split(" ")[0], "🟡")
        st.markdown(f"**{k['zaman']}** | {k['ticker']} — {k['fiyat']} TL | {emoji} {k['karar']} ({k['puan']} puan)")

# Hızlı tarama
st.divider()
st.markdown("### 🚀 Hızlı Tarama")
if st.button("Tüm Bomba Adaylarını Tara"):
    from gunluk_bomba import TICKERS as BOMBA_TICKERS
    sonuclar = []
    progress = st.progress(0)
    status = st.empty()

    temiz_tickers = [t.replace(".IS", "") for t in BOMBA_TICKERS]

    for i, ticker in enumerate(temiz_tickers):
        status.text(f"Taraniyor: {ticker} ({i+1}/{len(temiz_tickers)})")
        progress.progress((i + 1) / len(temiz_tickers))

        df = veri_cek(ticker)
        if df is None or len(df) < 30:
            continue

        teknik = teknik_hesapla(df)
        t_r = techno_analiz(teknik)
        v_r = volume_analiz(teknik)
        m_r = macro_analiz(teknik)
        f_r = funda_analiz(ticker)
        final = nihai_karar(t_r, v_r, m_r, f_r, teknik)

        sonuclar.append({
            "Hisse": ticker,
            "Fiyat": teknik["fiyat"],
            "Puan": final["toplam_puan"],
            "Karar": final["karar"],
            "Komisyon OK": "✅" if final["komisyon_ok"] else "❌",
            "Net Getiri": f"%{final['net_getiri']}",
            "RSI": teknik["rsi14"],
            "Trend": teknik["ema_trend"],
        })

    progress.empty()
    status.empty()

    if sonuclar:
        sdf = pd.DataFrame(sonuclar).sort_values("Puan", ascending=False)
        st.dataframe(sdf, use_container_width=True, hide_index=True)

        al_sayisi = sum(1 for s in sonuclar if s["Karar"] == "AL")
        st.success(f"✅ {al_sayisi} hisse AL sinyali verdi (komisyon dahil)")
