"""
BIST ALPHA V2 — Dashboard
Streamlit multi-page: pages/1_🏆_Alpha_V2.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from tahmin_motoru_v2 import (
    EnsembleModelV2, feature_olustur_v2, market_rejim_tespit,
    sektor_momentum_hesapla, hisse_analiz_v2, teknik_skor_v2,
    atr_hesapla, FEATURE_COLS_V2, SEKTOR_HISSELERI,
)
from risk_yonetimi import RiskYoneticisi
from haber_sentiment import haberleri_analiz_et, hisse_sentiment_al

st.set_page_config(page_title="BIST ALPHA V2", page_icon="🏆", layout="wide")

# ── Dark Theme CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a2a4a;
        border-radius: 10px;
        padding: 12px 16px;
    }
    .rejim-bull { color: #00ff88; font-size: 1.5rem; font-weight: 700; }
    .rejim-bear { color: #ff4444; font-size: 1.5rem; font-weight: 700; }
    .rejim-sideways { color: #ffaa00; font-size: 1.5rem; font-weight: 700; }
    .sinyal-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        margin: 1px;
    }
    .badge-al { background: #00ff8822; color: #00ff88; border: 1px solid #00ff8844; }
    .badge-bekle { background: #ffaa0022; color: #ffaa00; border: 1px solid #ffaa0044; }
    .badge-sat { background: #ff444422; color: #ff4444; border: 1px solid #ff444444; }
</style>
""", unsafe_allow_html=True)

# ── State ─────────────────────────────────────────────────────
if "v2_veri" not in st.session_state:
    st.session_state.v2_veri = None
if "v2_model" not in st.session_state:
    st.session_state.v2_model = None
if "v2_sonuclar" not in st.session_state:
    st.session_state.v2_sonuclar = None
if "v2_rejim" not in st.session_state:
    st.session_state.v2_rejim = None
if "v2_sentiment" not in st.session_state:
    st.session_state.v2_sentiment = None
if "v2_sektor" not in st.session_state:
    st.session_state.v2_sektor = None
if "v2_risk" not in st.session_state:
    st.session_state.v2_risk = RiskYoneticisi(sermaye=100_000)


# ── Header ────────────────────────────────────────────────────
st.title("🏆 BIST ALPHA V2")
st.caption("XGBoost + LightGBM + Neural Network Ensemble | Türkçe NLP Sentiment | Dinamik Risk Yönetimi")


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ V2 Kontrol")

    sermaye = st.number_input("Sermaye (TL)", value=100_000, step=10_000)
    st.session_state.v2_risk.sermaye = sermaye
    st.session_state.v2_risk.baslangic_sermaye = sermaye

    if st.button("🚀 Tam Tarama Başlat", type="primary", use_container_width=True):
        import yfinance as yf

        TICKERS = [
            "THYAO.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS", "SAHOL.IS",
            "BIMAS.IS", "TUPRS.IS", "KCHOL.IS", "ISCTR.IS", "YKBNK.IS",
            "SISE.IS", "TOASO.IS", "ASELS.IS", "HALKB.IS", "VAKBN.IS",
            "PGSUS.IS", "MGROS.IS", "SOKM.IS", "TAVHL.IS", "AKSEN.IS",
            "ODAS.IS", "LOGO.IS", "NETAS.IS", "TCELL.IS", "ENKAI.IS",
            "PETKM.IS", "DOHOL.IS", "TTKOM.IS", "EKGYO.IS", "FROTO.IS",
            "GUBRF.IS", "HEKTS.IS", "ISGYO.IS", "KORDS.IS", "OTKAR.IS",
            "TKFEN.IS", "TTRAK.IS", "VESTL.IS", "AEFES.IS", "ARCLK.IS",
            "CIMSA.IS", "EGEEN.IS", "ENJSA.IS", "GESAN.IS", "KONTR.IS",
            "MPARK.IS", "SASA.IS", "ULKER.IS",
        ]

        # 1. Veri
        progress = st.progress(0, text="Veriler çekiliyor...")
        veri = {}
        for i, t in enumerate(TICKERS):
            try:
                df = yf.download(t, period="1y", progress=False)
                if len(df) >= 120:
                    veri[t] = df
            except Exception:
                pass
            progress.progress((i + 1) / len(TICKERS), text=f"{t.replace('.IS','')}...")

        xu = yf.download("XU100.IS", period="1y", progress=False)
        if len(xu) > 50:
            veri["XU100.IS"] = xu
        st.session_state.v2_veri = veri

        # 2. Model
        progress.progress(0.7, text="Model yükleniyor...")
        model = EnsembleModelV2.yukle()
        if model is None:
            progress.progress(0.7, text="Model eğitiliyor (ilk kez)...")
            model = EnsembleModelV2()
            veri_2y = {}
            for t in TICKERS:
                try:
                    df2 = yf.download(t, period="2y", progress=False)
                    if len(df2) >= 120:
                        veri_2y[t] = df2
                except Exception:
                    pass
            model.egit(veri_2y)
        st.session_state.v2_model = model

        # 3. Rejim
        progress.progress(0.8, text="Piyasa analizi...")
        if "XU100.IS" in veri:
            st.session_state.v2_rejim = market_rejim_tespit(veri["XU100.IS"])

        # 4. Sektör
        st.session_state.v2_sektor = sektor_momentum_hesapla(veri)

        # 5. Sentiment
        progress.progress(0.85, text="Haber analizi...")
        st.session_state.v2_sentiment = haberleri_analiz_et()

        # 6. Risk ayarla
        risk = st.session_state.v2_risk
        if st.session_state.v2_rejim:
            risk.rejim_risk_ayari(st.session_state.v2_rejim)

        # 7. Tarama
        progress.progress(0.9, text="Hisseler analiz ediliyor...")
        sonuclar = []
        for ticker, df in veri.items():
            if ticker == "XU100.IS":
                continue
            try:
                analiz = hisse_analiz_v2(ticker, df, model, st.session_state.v2_rejim)
                if analiz is None:
                    continue

                # Sentiment
                t_temiz = ticker.replace(".IS", "")
                s_data = st.session_state.v2_sentiment or {}
                h_sent = s_data.get("hisse_sentiments", {}).get(t_temiz)
                analiz["sentiment"] = h_sent["skor"] if h_sent else 0

                # ATR
                close = df["Close"].squeeze()
                high = df["High"].squeeze()
                low = df["Low"].squeeze()
                atr = atr_hesapla(high, low, close)
                analiz["atr_val"] = float(atr.iloc[-1])

                # Risk
                analiz["risk"] = risk.sinyal_degerlendir(
                    ticker=ticker, fiyat=analiz["fiyat"],
                    atr=analiz["atr_val"],
                    ml_olasilik=analiz.get("ml_olasilik"),
                    teknik_skor=analiz["teknik_skor"],
                    rejim_info=st.session_state.v2_rejim,
                )
                sonuclar.append(analiz)
            except Exception:
                continue

        sonuclar.sort(key=lambda x: x["birlesik_skor"], reverse=True)
        st.session_state.v2_sonuclar = sonuclar
        progress.empty()
        st.success(f"✅ {len(sonuclar)} hisse analiz edildi!")

    st.divider()

    # Son sonuç varsa bilgi göster
    if st.session_state.v2_sonuclar:
        islem = [s for s in st.session_state.v2_sonuclar if s.get("risk", {}).get("islem")]
        st.metric("İşlem Sinyali", len(islem))
        st.metric("Toplam Hisse", len(st.session_state.v2_sonuclar))

    # Model bilgisi
    if st.session_state.v2_model and st.session_state.v2_model.meta:
        m = st.session_state.v2_model.meta
        st.divider()
        st.caption("📊 Model Bilgisi")
        st.text(f"AUC: {m.get('ensemble_auc', '-')}")
        st.text(f"F1:  {m.get('ensemble_f1', '-')}")
        st.text(f"Eğitim: {m.get('egitim_tarihi', '-')}")


# ── ANA İÇERİK ───────────────────────────────────────────────

if st.session_state.v2_sonuclar is None:
    st.info("👈 Sol panelden **Tam Tarama Başlat** butonuna basın")
    st.stop()

sonuclar = st.session_state.v2_sonuclar
rejim = st.session_state.v2_rejim
sentiment = st.session_state.v2_sentiment
sektor = st.session_state.v2_sektor
risk = st.session_state.v2_risk

# ── ÜST PANEL: Piyasa Durumu ─────────────────────────────────
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)

if rejim:
    emoji = {"bull": "🐂", "bear": "🐻", "sideways": "↔️"}.get(rejim["rejim"], "❓")
    css = f"rejim-{rejim['rejim']}"
    c1.markdown(f'<div class="{css}">{emoji} {rejim["rejim"].upper()}</div>', unsafe_allow_html=True)
    c1.caption(f"ADX: {rejim['adx']} | Vol: {rejim['volatilite']}%")

if sentiment:
    s_val = sentiment.get("genel_sentiment", 0)
    s_emoji = "🟢" if s_val > 0.1 else "🔴" if s_val < -0.1 else "⚪"
    c2.metric("Haber Sentiment", f"{s_emoji} {s_val:+.3f}")
    c2.caption(f"{sentiment.get('haber_sayisi', 0)} haber analiz edildi")

islem_sinyalleri = [s for s in sonuclar if s.get("risk", {}).get("islem")]
c3.metric("🎯 İşlem Sinyali", len(islem_sinyalleri))

dd = risk.drawdown_kontrol()
c4.metric("💰 Sermaye", f"{risk.sermaye:,.0f} TL")
c5.metric("📉 Drawdown", f"%{dd['drawdown_pct']:.1f}", delta=f"Limit: %{dd['limit']}")

# ── TABLAR ────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Sinyaller", "📊 Sektör", "📰 Haberler", "⚖️ Risk", "🧠 Model"
])

# ── TAB 1: Sinyaller ─────────────────────────────────────────
with tab1:
    if islem_sinyalleri:
        st.subheader(f"🎯 İşlem Sinyalleri ({len(islem_sinyalleri)})")
        for s in islem_sinyalleri:
            r = s["risk"]
            sinyal_str = " ".join(s.get("sinyal_ozet", []))
            col1, col2, col3, col4 = st.columns([2, 1, 1, 3])
            col1.markdown(f"**{s['ticker'].replace('.IS', '')}** — ₺{s['fiyat']:.2f}")
            col2.metric("Skor", f"{s['birlesik_skor']:.0f}")
            col3.metric("ML", f"%{(s.get('ml_olasilik') or 0)*100:.0f}")
            col4.caption(f"Lot: {r.get('lot', 0)} | Stop: ₺{r.get('stop_loss', 0):.2f} ({r.get('stop_pct', 0):.1f}%) | TP: ₺{r.get('take_profit', 0):.2f} | {sinyal_str}")
            st.divider()
    else:
        st.warning("⏳ Şu an işleme uygun sinyal yok — piyasa BEAR rejiminde, defansif mod aktif.")

    # Tüm sonuçlar tablosu
    st.subheader("📋 Tüm Hisseler")
    tablo = []
    for s in sonuclar:
        r = s.get("risk", {})
        tablo.append({
            "Hisse": s["ticker"].replace(".IS", ""),
            "Skor": round(s["birlesik_skor"], 1),
            "ML %": round((s.get("ml_olasilik") or 0) * 100, 1),
            "Teknik": round(s["teknik_skor"], 1),
            "Sent.": round(s.get("sentiment", 0), 2),
            "RSI": round(s.get("rsi", 50), 1),
            "ADX": round(s.get("adx", 0), 1),
            "MA": s.get("ma_alignment", 0),
            "Fiyat": round(s["fiyat"], 2),
            "Değişim %": round(s.get("gunluk", 0), 2),
            "İşlem": "✅" if r.get("islem") else "❌",
            "Sinyaller": " ".join(s.get("sinyal_ozet", [])[:2]),
        })
    df_tablo = pd.DataFrame(tablo)
    st.dataframe(df_tablo, use_container_width=True, height=600)

    # Skor bar chart
    st.subheader("Sürpriz Skoru Sıralaması")
    top20 = sonuclar[:20]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[s["ticker"].replace(".IS", "") for s in top20],
        y=[s["birlesik_skor"] for s in top20],
        marker_color=[
            "#00ff88" if s.get("risk", {}).get("islem") else
            "#ffaa00" if s["birlesik_skor"] > 40 else "#555"
            for s in top20
        ],
        text=[f"{s['birlesik_skor']:.0f}" for s in top20],
        textposition="outside",
    ))
    fig.update_layout(
        height=350, template="plotly_dark",
        yaxis_range=[0, 110], margin=dict(t=10, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── TAB 2: Sektör ────────────────────────────────────────────
with tab2:
    st.subheader("📊 Sektör Momentum Analizi")
    if sektor:
        sektor_df = pd.DataFrame([
            {"Sektör": s.capitalize(), "5 Gün %": m["mom_5"], "20 Gün %": m["mom_20"], "Güç": m["guc"]}
            for s, m in sorted(sektor.items(), key=lambda x: x[1]["mom_5"], reverse=True)
        ])

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=sektor_df["Sektör"], y=sektor_df["5 Gün %"],
            name="5 Günlük", marker_color=[
                "#00ff88" if v > 0 else "#ff4444" for v in sektor_df["5 Gün %"]
            ]
        ))
        fig.add_trace(go.Bar(
            x=sektor_df["Sektör"], y=sektor_df["20 Gün %"],
            name="20 Günlük", marker_color=[
                "#00ff8866" if v > 0 else "#ff444466" for v in sektor_df["20 Gün %"]
            ]
        ))
        fig.update_layout(
            barmode="group", height=400, template="plotly_dark",
            margin=dict(t=10),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(sektor_df, use_container_width=True)
    else:
        st.info("Tarama sonrası sektör verileri görünür")


# ── TAB 3: Haberler ──────────────────────────────────────────
with tab3:
    st.subheader("📰 Haber Sentiment Analizi")
    if sentiment:
        c1, c2, c3 = st.columns(3)
        c1.metric("Genel Sentiment", f"{sentiment.get('genel_sentiment', 0):+.3f}")
        c2.metric("Durum", sentiment.get("genel_sinyal", "NÖTR"))
        c3.metric("Haber Sayısı", sentiment.get("haber_sayisi", 0))

        # Hisse bazlı sentiment
        if sentiment.get("hisse_sentiments"):
            st.subheader("Hisse Bazlı")
            sent_df = pd.DataFrame([
                {"Hisse": t, "Sentiment": i["skor"], "Haber": i["haber_sayisi"]}
                for t, i in sorted(
                    sentiment["hisse_sentiments"].items(),
                    key=lambda x: x[1]["skor"], reverse=True
                )
            ])
            st.dataframe(sent_df, use_container_width=True)

        # Son haberler
        if sentiment.get("son_haberler"):
            st.subheader("Son Haberler")
            for h in sentiment["son_haberler"][:10]:
                st.markdown(f"{h.get('sinyal', '⚪')} **[{h.get('sentiment', 0):+.3f}]** {h.get('baslik', '')[:100]}")
    else:
        st.info("Tarama sonrası haber analizi görünür")


# ── TAB 4: Risk ──────────────────────────────────────────────
with tab4:
    st.subheader("⚖️ Risk Yönetimi")

    c1, c2, c3, c4 = st.columns(4)
    dd = risk.drawdown_kontrol()
    c1.metric("Mevcut Sermaye", f"₺{risk.sermaye:,.0f}")
    c2.metric("Peak", f"₺{risk.peak_sermaye:,.0f}")
    c3.metric("Drawdown", f"%{dd['drawdown_pct']:.1f}")
    c4.metric("Durum", dd["durum"])

    st.divider()

    # Rejim ayarları
    if rejim:
        rejim_ayar = risk.rejim_risk_ayari(rejim)
        st.subheader(f"🎛️ Rejim Ayarları — {rejim['rejim'].upper()}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Max Risk/İşlem", f"%{rejim_ayar['max_risk_pct']}")
        c2.metric("Max Pozisyon", rejim_ayar["max_pozisyon"])
        c3.metric("Min ML Eşik", f"%{rejim_ayar['min_ml_esik']*100:.0f}")
        c4.metric("Min Teknik", rejim_ayar["min_teknik_esik"])
        st.info(f"💡 {rejim_ayar['aciklama']}")

    # Performans
    perf = risk.performans_raporu()
    if perf.get("toplam_trade", 0) > 0:
        st.subheader("📊 Performans")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Trade", perf["toplam_trade"])
        c2.metric("Win Rate", f"%{perf['win_rate']}")
        c3.metric("Toplam P&L", f"₺{perf['toplam_kar_tl']:,.0f}")
        c4.metric("Profit Factor", perf["profit_factor"])


# ── TAB 5: Model ─────────────────────────────────────────────
with tab5:
    st.subheader("🧠 Ensemble Model V2")

    model = st.session_state.v2_model
    if model and model.meta:
        m = model.meta

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ensemble AUC", m.get("ensemble_auc", "-"))
        c2.metric("F1 Score", m.get("ensemble_f1", "-"))
        c3.metric("Precision", m.get("ensemble_precision", "-"))
        c4.metric("Feature Sayısı", m.get("feature_sayisi", "-"))

        st.divider()

        # Ağırlıklar
        st.subheader("⚖️ Model Ağırlıkları")
        w = m.get("weights", [0.33, 0.33, 0.33])
        fig = go.Figure(go.Pie(
            labels=["XGBoost", "LightGBM", "Neural Net"],
            values=w,
            marker_colors=["#00ff88", "#ffaa00", "#ff6688"],
            hole=0.4,
        ))
        fig.update_layout(height=300, template="plotly_dark", margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # Feature importance
        if m.get("top_features"):
            st.subheader("🏆 Top Features")
            feat_df = pd.DataFrame([
                {"Feature": k, "Importance": v}
                for k, v in list(m["top_features"].items())[:15]
            ])
            fig = go.Figure(go.Bar(
                x=feat_df["Importance"],
                y=feat_df["Feature"],
                orientation="h",
                marker_color="#00ff88",
            ))
            fig.update_layout(
                height=400, template="plotly_dark",
                yaxis=dict(autorange="reversed"),
                margin=dict(l=150, t=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Walk-forward
        if m.get("walk_forward"):
            st.subheader("📈 Walk-Forward Validation")
            wf_df = pd.DataFrame(m["walk_forward"])
            st.dataframe(wf_df, use_container_width=True)

        st.caption(f"Model eğitim tarihi: {m.get('egitim_tarihi', '-')}")
    else:
        st.info("Model henüz yüklenmedi — Tam Tarama başlatın")
