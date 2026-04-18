"""
BIST Sürpriz Hisse Tahmin Sistemi - Streamlit Arayüzü (V2)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from tahmin_motoru_v2 import (
    feature_olustur_v2, teknik_skor_v2,
    EnsembleModelV2, hisse_analiz_v2, FEATURE_COLS_V2,
    rsi_hesapla, macd_hesapla, bollinger_hesapla
)
from veri_isleyici import (
    BIST_TICKERS, TICKER_ISIMLERI, ticker_isim,
    tum_verileri_cek, screenshot_ocr, dosya_parse,
    canli_veri_birlestir
)
from matriks_scraper import (
    matriks_veri_cek_sync, kayitli_veri_oku, veri_to_dataframe,
    CANLI_VERI_PATH
)
from bot import BistBot, BotConfig, sinyal_gecmisi_oku, sinyal_gecmisi_temizle


# ============================================================
# CACHED MODEL LOADING
# ============================================================

@st.cache_resource
def yukle_kayitli_model():
    """Kaydedilmis modeli diskten yukle (cache ile tekrar yuklemeyi onle)."""
    try:
        model = EnsembleModelV2.yukle()
        return model
    except Exception:
        return None

# Sayfa ayarları
st.set_page_config(
    page_title="BIST Sürpriz Bulucu",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tema
st.markdown("""
<style>
    .stMetric { border: 1px solid #333; border-radius: 8px; padding: 10px; }
    .surpriz-yuksek { color: #ff4444; font-weight: bold; }
    .surpriz-orta { color: #ffaa00; font-weight: bold; }
    .surpriz-dusuk { color: #44aa44; }
    div[data-testid="stSidebar"] { background-color: #0e1117; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

def init_state():
    if "veriler" not in st.session_state:
        st.session_state.veriler = None
    if "sonuclar" not in st.session_state:
        st.session_state.sonuclar = None
    if "ml_model" not in st.session_state:
        st.session_state.ml_model = None
    if "model_bilgi" not in st.session_state:
        st.session_state.model_bilgi = None
    if "canli_veri" not in st.session_state:
        st.session_state.canli_veri = None

init_state()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("⚡ BIST Sürpriz Bulucu")
    st.caption("Teknik Analiz + ML Tahmin")
    st.divider()

    # Veri çekme
    st.subheader("📡 Veri Kaynağı")
    gun_sayisi = st.slider("Geçmiş veri (gün)", 60, 365, 120)

    if st.button("🔄 Verileri Çek & Analiz Et", type="primary", use_container_width=True):
        try:
            with st.spinner("Hisse verileri çekiliyor..."):
                progress = st.progress(0)
                status = st.empty()

                def callback(p, msg):
                    progress.progress(p)
                    status.text(msg)

                veriler = tum_verileri_cek(gun=gun_sayisi, progress_callback=callback)
                st.session_state.veriler = veriler
                progress.empty()
                status.empty()
        except Exception as e:
            st.error(f"Veri cekme hatasi: {e}")
            veriler = None

        if veriler:
            st.success(f"{len(veriler)} hisse yüklendi")

            # ML model eğit (V2 Ensemble)
            try:
                with st.spinner("ML modeli eğitiliyor (V2 Ensemble)..."):
                    ensemble = EnsembleModelV2()
                    bilgi = ensemble.egit(veriler)
                    if bilgi:
                        st.session_state.ml_model = ensemble
                        st.session_state.model_bilgi = bilgi
                        auc = bilgi.get("ensemble_auc", 0)
                        st.success(f"Model eğitildi (AUC: {auc:.4f})")
                    else:
                        # Mevcut modeli yüklemeyi dene
                        model = yukle_kayitli_model()
                        if model:
                            st.session_state.ml_model = model
                            st.session_state.model_bilgi = model.meta
                            st.info("Önceki model yüklendi")
            except Exception as e:
                st.warning(f"Model eğitim hatasi: {e}")
                # Mevcut modeli yüklemeyi dene
                model = yukle_kayitli_model()
                if model:
                    st.session_state.ml_model = model
                    st.session_state.model_bilgi = model.meta
                    st.info("Önceki kayıtlı model yüklendi")

            # Analiz (V2)
            try:
                with st.spinner("Hisseler analiz ediliyor..."):
                    sonuclar = []
                    for ticker, df in veriler.items():
                        try:
                            sonuc = hisse_analiz_v2(ticker, df, st.session_state.ml_model)
                            if sonuc:
                                sonuclar.append(sonuc)
                        except Exception:
                            pass  # tek hisse hatasi atlaniyor

                    sonuclar.sort(key=lambda x: x["birlesik_skor"], reverse=True)
                    st.session_state.sonuclar = sonuclar

                st.success(f"{len(sonuclar)} hisse analiz edildi!")
            except Exception as e:
                st.error(f"Analiz hatasi: {e}")
        else:
            st.error("Veri çekilemedi")

    st.divider()

    # Filtre
    st.subheader("🎯 Filtre")
    min_skor = st.slider("Min. sürpriz skoru", 0, 100, 50)
    sinyal_filtre = st.multiselect(
        "Sinyal tipi",
        ["RSI", "MACD", "Bollinger", "Hacim", "Momentum"],
        default=[]
    )

    st.divider()
    st.caption(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")


# ============================================================
# ANA SAYFA
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 Sürpriz Tahminleri",
    "📈 Hisse Detay",
    "🤖 Model Performansı",
    "📥 Canlı Veri Girişi",
    "🔗 Matriks Otomatik",
    "🤖 Bot Kontrol"
])


# --- TAB 1: Sürpriz Tahminleri ---
with tab1:
  try:
    st.header("Sürpriz Yapması Beklenen Hisseler")

    if st.session_state.sonuclar is None:
        st.info("Sol panelden 'Verileri Cek & Analiz Et' butonuna basin")
    else:
        sonuclar = st.session_state.sonuclar

        # Filtrele
        filtreli = [s for s in sonuclar if s["birlesik_skor"] >= min_skor]

        if sinyal_filtre:
            def sinyal_kontrol(s):
                sinyaller = s.get("sinyal_ozet", [])
                for f_item in sinyal_filtre:
                    if any(f_item.lower() in t.lower() for t in sinyaller):
                        return True
                return False
            filtreli = [s for s in filtreli if sinyal_kontrol(s)]

        if not filtreli:
            st.warning("Filtrelere uyan hisse bulunamadi. Filtreleri gevsetin.")
        else:
            # Ust metrikler
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Toplam Surpriz", len(filtreli))
            col2.metric("En Yuksek Skor", f"{filtreli[0]['birlesik_skor']:.0f}")
            en_yukari = max(filtreli, key=lambda x: x.get("gunluk", 0))
            en_asagi = min(filtreli, key=lambda x: x.get("gunluk", 0))
            col3.metric("En Cok Yukselen", f"{en_yukari['ticker'].replace('.IS', '')} %{en_yukari.get('gunluk', 0):.1f}")
            col4.metric("En Cok Dusen", f"{en_asagi['ticker'].replace('.IS', '')} %{en_asagi.get('gunluk', 0):.1f}")

            st.divider()

            # Surpriz skoru bar chart
            st.subheader("Surpriz Skoru Siralamasi")
            chart_df = pd.DataFrame([{
                "Hisse": s["ticker"].replace(".IS", ""),
                "Birlesik Skor": s["birlesik_skor"],
                "Teknik Skor": s["teknik_skor"],
                "ML Olasilik": (s.get("ml_olasilik") or 0) * 100,
            } for s in filtreli[:20]])

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=chart_df["Hisse"], y=chart_df["Birlesik Skor"],
                name="Birlesik Skor",
                marker_color=["#ff4444" if v > 70 else "#ffaa00" if v > 50 else "#44aa44" for v in chart_df["Birlesik Skor"]],
                text=chart_df["Birlesik Skor"].round(1),
                textposition="outside"
            ))
            fig.update_layout(
                height=400,
                yaxis_range=[0, 110],
                template="plotly_dark",
                margin=dict(t=20, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Detay tablosu
            st.subheader("Detay Tablosu")
            tablo_verileri = []
            for s in filtreli:
                sinyaller = s.get("sinyal_ozet", [])
                sinyal_str = " | ".join(sinyaller) if sinyaller else "---"
                tablo_verileri.append({
                    "Hisse": s["ticker"].replace(".IS", ""),
                    "Sirket": ticker_isim(s["ticker"]),
                    "Fiyat (TL)": f"{s['fiyat']:.2f}",
                    "Degisim %": f"{s.get('gunluk', 0):.2f}",
                    "Teknik": f"{s['teknik_skor']:.0f}",
                    "ML %": f"{(s.get('ml_olasilik') or 0)*100:.0f}",
                    "Surpriz Skoru": f"{s['birlesik_skor']:.0f}",
                    "Sinyaller": sinyal_str,
                })

            tablo_df = pd.DataFrame(tablo_verileri)
            st.dataframe(tablo_df, use_container_width=True, height=500)

            # Sinyal detaylari (expandable)
            st.subheader("Sinyal Detaylari")
            for s in filtreli[:10]:
                sinyaller = s.get("sinyal_ozet", [])
                if sinyaller and sinyaller != ["---"]:
                    kod = s["ticker"].replace(".IS", "")
                    isim = ticker_isim(s["ticker"])
                    with st.expander(f"**{kod}** - {isim} | Skor: {s['birlesik_skor']:.0f}"):
                        for sinyal_text in sinyaller:
                            st.write(f"  {sinyal_text}")
  except Exception as e:
    st.error(f"Tab1 hatasi: {e}")


# --- TAB 2: Hisse Detay ---
with tab2:
  try:
    st.header("Hisse Detay Analizi")

    if st.session_state.veriler is None:
        st.info("Once verileri cekin")
    else:
        mevcut = [t.replace(".IS", "") for t in st.session_state.veriler.keys()]
        secim = st.selectbox("Hisse sec", mevcut)

        if secim:
            ticker = f"{secim}.IS"
            df = st.session_state.veriler[ticker]

            try:
                analiz = hisse_analiz_v2(ticker, df, st.session_state.ml_model)
            except Exception as e:
                analiz = None
                st.error(f"Hisse analiz hatasi: {e}")

            if analiz is None:
                st.warning("Bu hisse icin analiz sonucu uretilemedi. Veri yetersiz olabilir.")
            else:
                # Metrikler
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Fiyat", f"{analiz['fiyat']:.2f} TL")
                c2.metric("Degisim", f"%{analiz.get('gunluk', 0):.2f}")
                c3.metric("Teknik Skor", f"{analiz['teknik_skor']:.0f}/100")
                c4.metric("ML Olasilik", f"%{(analiz.get('ml_olasilik') or 0)*100:.0f}")
                c5.metric("Surpriz Skoru", f"{analiz['birlesik_skor']:.0f}/100")

                st.divider()

                # Fiyat grafigi + indikatorler
                try:
                    features = feature_olustur_v2(df)

                    fig = make_subplots(
                        rows=4, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03,
                        row_heights=[0.45, 0.2, 0.15, 0.2],
                        subplot_titles=["Fiyat & Bollinger Bandlari", "MACD", "RSI", "Hacim"]
                    )

                    # Fiyat + Bollinger
                    sma, ust, alt, _ = bollinger_hesapla(df["Close"])
                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df["Open"], high=df["High"],
                        low=df["Low"], close=df["Close"], name="Fiyat"
                    ), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=ust, name="Ust Band", line=dict(color="rgba(255,100,100,0.5)", dash="dash")), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=alt, name="Alt Band", line=dict(color="rgba(100,255,100,0.5)", dash="dash"), fill="tonexty", fillcolor="rgba(100,100,255,0.05)"), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=sma, name="SMA20", line=dict(color="rgba(255,255,100,0.7)")), row=1, col=1)

                    # MACD
                    macd, macd_s, hist = macd_hesapla(df["Close"])
                    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in hist]
                    fig.add_trace(go.Bar(x=df.index, y=hist, name="MACD Hist", marker_color=colors), row=2, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=macd, name="MACD", line=dict(color="#2196f3")), row=2, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=macd_s, name="Sinyal", line=dict(color="#ff9800")), row=2, col=1)

                    # RSI
                    rsi = rsi_hesapla(df["Close"])
                    fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color="#ab47bc")), row=3, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

                    # Hacim
                    vol_colors = ["#26a69a" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ef5350" for i in range(len(df))]
                    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Hacim", marker_color=vol_colors), row=4, col=1)

                    fig.update_layout(
                        height=800,
                        template="plotly_dark",
                        showlegend=False,
                        xaxis_rangeslider_visible=False,
                        margin=dict(t=30, b=20),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Grafik olusturma hatasi: {e}")

                # Sinyaller (V2 format: sinyal_ozet listesi)
                sinyaller = analiz.get("sinyal_ozet", [])
                if sinyaller and sinyaller != ["---"]:
                    st.subheader("Aktif Sinyaller")
                    for sinyal_text in sinyaller:
                        st.write(f"  {sinyal_text}")
  except Exception as e:
    st.error(f"Tab2 hatasi: {e}")


# --- TAB 3: Model Performansi ---
with tab3:
  try:
    st.header("ML Model Performansi")

    bilgi = st.session_state.model_bilgi
    if bilgi is None:
        st.info("Model henuz egitilmedi. Verileri cektiginizde otomatik egitilecek.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("AUC", f"{bilgi.get('ensemble_auc', 0):.4f}")
        c2.metric("F1 Skor", f"{bilgi.get('ensemble_f1', 0):.3f}")
        c3.metric("Egitim Verisi", f"{bilgi.get('egitim_boyut', 0):,}")
        c4.metric("Test Verisi", f"{bilgi.get('test_boyut', 0):,}")

        st.divider()

        st.subheader("Model Hakkinda")
        st.markdown("""
        **Algoritma:** V2 Ensemble (XGBoost + LightGBM + MLP Neural Network)

        **Hedef:** Sonraki 5 gunde %2+ fiyat hareketi olup olmayacagi

        **Feature'lar (80+):**
        - RSI, MACD, Bollinger Band, ADX, Stokastik, OBV
        - Hacim profili, RVOL ve anomaliler
        - Fiyat momentum (5/10/20 gun), ivme
        - Volatilite, ATR, kanal pozisyonu
        - Hareketli ortalama alignment
        - Mum kaliplari (hammer, doji)
        - Market rejim uyumu

        **Birlesik Skor Formulu:**
        `Surpriz Skoru = Teknik Skor x 0.35 + ML Olasiligi x 0.65` (rejime gore dinamik)
        """)

        # Feature importance (V2 ensemble - top_features from meta)
        if st.session_state.ml_model is not None:
            st.subheader("Feature Onem Siralamasi")
            try:
                model = st.session_state.ml_model
                # V2: top_features stored in meta dict
                top_features = bilgi.get("top_features", {})
                if top_features:
                    fi_df = pd.DataFrame({
                        "Feature": list(top_features.keys()),
                        "Onem": list(top_features.values())
                    }).sort_values("Onem", ascending=True).tail(15)
                elif hasattr(model, 'xgb_model') and model.xgb_model is not None:
                    # Fallback: XGBoost feature importances directly
                    importances = model.xgb_model.feature_importances_
                    cols = model.feature_cols if model.feature_cols else FEATURE_COLS_V2
                    fi_df = pd.DataFrame({
                        "Feature": cols[:len(importances)],
                        "Onem": importances
                    }).sort_values("Onem", ascending=True).tail(15)
                else:
                    fi_df = None

                if fi_df is not None and len(fi_df) > 0:
                    fig = go.Figure(go.Bar(
                        x=fi_df["Onem"],
                        y=fi_df["Feature"],
                        orientation="h",
                        marker_color="#2196f3"
                    ))
                    fig.update_layout(
                        height=400,
                        template="plotly_dark",
                        margin=dict(l=150, t=20),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Feature importance verisi mevcut degil.")
            except Exception as e:
                st.warning(f"Feature importance gosterilemiyor: {e}")
  except Exception as e:
    st.error(f"Tab3 hatasi: {e}")


# --- TAB 4: Canli Veri Girisi ---
with tab4:
  try:
    st.header("Canli Veri Girisi")
    st.caption("Matrix IQ veya başka kaynaklardan güncel veri besleyin")

    giris_yontemi = st.radio(
        "Veri giriş yöntemi",
        ["📸 Screenshot (OCR)", "📝 Manuel Giriş", "📂 CSV/Excel Yükle"],
        horizontal=True
    )

    if giris_yontemi == "📸 Screenshot (OCR)":
        st.subheader("Matrix IQ Screenshot")
        st.info("Matrix IQ ekranından `Cmd+Shift+4` ile screenshot alıp buraya sürükleyin")

        uploaded = st.file_uploader(
            "Screenshot yükle",
            type=["png", "jpg", "jpeg", "bmp"],
            key="screenshot"
        )

        if uploaded:
            st.image(uploaded, caption="Yüklenen görüntü", use_container_width=True)

            with st.spinner("OCR ile veriler çıkarılıyor..."):
                sonuc_df, hata = screenshot_ocr(uploaded.read())

            if hata:
                st.error(hata)
            elif sonuc_df is not None:
                st.success(f"{len(sonuc_df)} hisse tespit edildi!")
                st.dataframe(sonuc_df, use_container_width=True)

                # Düzenleme imkanı
                st.caption("Verileri düzenleyebilirsiniz:")
                edited = st.data_editor(sonuc_df, num_rows="dynamic", use_container_width=True)

                if st.button("✅ Verileri Uygula", key="ocr_uygula"):
                    st.session_state.canli_veri = edited
                    if st.session_state.veriler:
                        st.session_state.veriler = canli_veri_birlestir(
                            st.session_state.veriler, edited
                        )
                        st.success("Canlı veriler mevcut verilerle birleştirildi!")
                    else:
                        st.warning("Önce geçmiş verileri çekin, sonra canlı veri ekleyin")

    elif giris_yontemi == "📝 Manuel Giriş":
        st.subheader("Manuel Veri Girişi")

        with st.form("manuel_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                kod = st.text_input("Hisse Kodu", placeholder="THYAO").upper()
            with col2:
                fiyat = st.number_input("Son Fiyat (TL)", min_value=0.01, step=0.01)
            with col3:
                hacim = st.number_input("Hacim", min_value=0, step=1000)

            submitted = st.form_submit_button("➕ Ekle", use_container_width=True)

            if submitted and kod and fiyat > 0:
                yeni = pd.DataFrame([{"kod": kod, "fiyat": fiyat, "hacim": hacim}])

                if st.session_state.canli_veri is not None:
                    st.session_state.canli_veri = pd.concat([st.session_state.canli_veri, yeni], ignore_index=True)
                else:
                    st.session_state.canli_veri = yeni

                st.success(f"{kod} eklendi!")

        # Mevcut girişler
        if st.session_state.canli_veri is not None and len(st.session_state.canli_veri) > 0:
            st.subheader("Girilen Veriler")
            st.dataframe(st.session_state.canli_veri, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Verileri Uygula", key="manuel_uygula"):
                    if st.session_state.veriler:
                        st.session_state.veriler = canli_veri_birlestir(
                            st.session_state.veriler, st.session_state.canli_veri
                        )
                        st.success("Veriler birleştirildi!")
            with c2:
                if st.button("🗑️ Temizle", key="manuel_temizle"):
                    st.session_state.canli_veri = None
                    st.rerun()

    elif giris_yontemi == "📂 CSV/Excel Yükle":
        st.subheader("Dosya Yükleme")
        st.info("CSV veya Excel dosyanızda en azından 'kod/hisse' ve 'fiyat/close' sütunları olmalı")

        uploaded = st.file_uploader(
            "Dosya yükle",
            type=["csv", "tsv", "xlsx", "xls"],
            key="dosya"
        )

        if uploaded:
            with st.spinner("Dosya okunuyor..."):
                sonuc_df, hata = dosya_parse(uploaded)

            if hata:
                st.error(hata)
            elif sonuc_df is not None:
                st.success(f"{len(sonuc_df)} satır okundu!")

                # Sütun eşleştirme önizleme
                st.caption("Algılanan sütunlar:")
                st.dataframe(sonuc_df.head(10), use_container_width=True)

                # Düzenle
                edited = st.data_editor(sonuc_df, num_rows="dynamic", use_container_width=True)

                if st.button("✅ Verileri Uygula", key="dosya_uygula"):
                    st.session_state.canli_veri = edited
                    if st.session_state.veriler:
                        st.session_state.veriler = canli_veri_birlestir(
                            st.session_state.veriler, edited
                        )
                        st.success("Dosya verileri birleştirildi!")
                    else:
                        st.warning("Önce geçmiş verileri çekin")
  except Exception as e:
    st.error(f"Tab4 hatasi: {e}")


# --- TAB 5: Matriks Otomatik ---
with tab5:
  try:
    st.header("Matriks Web Trader - Otomatik Veri Cekimi")
    st.caption("Playwright ile Matriks Web Trader'dan otomatik veri çeker")

    # Giriş bilgileri
    st.subheader("Matriks Giriş Bilgileri")
    col1, col2 = st.columns(2)
    with col1:
        matriks_user = st.text_input("Kullanıcı Adı", key="matriks_user", placeholder="Matriks kullanıcı adınız")
    with col2:
        matriks_pass = st.text_input("Şifre", key="matriks_pass", type="password", placeholder="Şifreniz")

    col_a, col_b = st.columns(2)
    with col_a:
        headless_mode = st.checkbox("Görünmez tarayıcı (headless)", value=True,
                                     help="İşaretli: tarayıcı arka planda çalışır. İşaretsiz: tarayıcı ekranda açılır (debug için)")
    with col_b:
        pass

    st.divider()

    # Veri çekme butonu
    if st.button("🚀 Matriks'ten Veri Çek", type="primary", use_container_width=True, key="matriks_cek"):
        if not matriks_user or not matriks_pass:
            st.warning("Lütfen kullanıcı adı ve şifre girin")
        else:
            try:
              with st.spinner("Matriks Web Trader'a baglaniliyor... (Bu 15-30 sn surebilir)"):
                sonuc = matriks_veri_cek_sync(matriks_user, matriks_pass, headless=headless_mode)
            except Exception as e:
              st.error(f"Matriks baglanti hatasi: {e}")
              sonuc = {"hata": str(e)}

            if "hata" in sonuc:
                st.error(f"Hata: {sonuc['hata']}")
                # Hata ekran görüntüsü
                from pathlib import Path
                hata_img = Path(__file__).parent / "data" / "matriks_hata_ekran.png"
                if hata_img.exists():
                    st.image(str(hata_img), caption="Hata anındaki ekran görüntüsü")
            else:
                st.success(f"Veri çekildi! ({sonuc['zaman']})")

                # Sayfa bilgisi
                bilgi = sonuc.get("sayfa_bilgi", {})
                with st.expander("Sayfa Bilgisi (Debug)"):
                    st.json(bilgi)

                # Veriler
                veriler = sonuc.get("veriler", [])
                if veriler:
                    df = veri_to_dataframe(veriler)
                    st.subheader(f"{len(veriler)} hisse bulundu")
                    st.dataframe(df, use_container_width=True)

                    # Düzenleme
                    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="matriks_edit")

                    if st.button("✅ Verileri Uygula", key="matriks_uygula"):
                        st.session_state.canli_veri = edited
                        if st.session_state.veriler:
                            st.session_state.veriler = canli_veri_birlestir(
                                st.session_state.veriler, edited
                            )
                            st.success("Matriks verileri mevcut verilerle birleştirildi!")
                            st.rerun()
                        else:
                            st.warning("Önce sol panelden geçmiş verileri çekin, sonra Matriks verilerini uygulayın")
                else:
                    st.warning("Sayfadan hisse verisi çıkarılamadı. Debug bilgisini kontrol edin.")

                # Screenshot
                ss = sonuc.get("screenshot")
                if ss:
                    from pathlib import Path
                    ss_path = Path(ss)
                    if ss_path.exists():
                        with st.expander("Tarayıcı Ekran Görüntüsü"):
                            st.image(str(ss_path), caption="Son ekran görüntüsü")

    st.divider()

    # Önceki veri
    st.subheader("Son Kaydedilen Veri")
    onceki = kayitli_veri_oku()
    if onceki:
        st.caption(f"Kaynak: {onceki.get('kaynak', '?')} | Zaman: {onceki.get('zaman', '?')}")
        ov = onceki.get("veriler", [])
        if ov:
            st.dataframe(veri_to_dataframe(ov), use_container_width=True)

            if st.button("📂 Bu Veriyi Yükle", key="matriks_yukle"):
                df = veri_to_dataframe(ov)
                st.session_state.canli_veri = df
                if st.session_state.veriler:
                    st.session_state.veriler = canli_veri_birlestir(
                        st.session_state.veriler, df
                    )
                    st.success("Önceki Matriks verisi yüklendi!")
                    st.rerun()
        else:
            st.info("Kaydedilmiş veride hisse bulunamadı")
    else:
        st.info("Henuz Matriks'ten veri cekilmemis")
  except Exception as e:
    st.error(f"Tab5 hatasi: {e}")


# --- TAB 6: Bot Kontrol Paneli ---
with tab6:
  try:
    st.header("Otomatik Trading Bot")
    st.caption("Periyodik tarama, sinyal tespiti ve bildirim sistemi")

    # Bot instance (session state)
    if "bot_instance" not in st.session_state:
        st.session_state.bot_instance = None

    # BotConfig yukle (hata durumunda varsayilan config)
    try:
        bot_config = BotConfig.yukle()
    except Exception:
        bot_config = BotConfig()
        st.warning("Bot config yuklenemedi, varsayilan ayarlar kullaniliyor.")

    # Durum gostergesi
    bot_aktif = st.session_state.bot_instance is not None and st.session_state.bot_instance.calisiyor
    if bot_aktif:
        st.success("Bot CALISIYOR")
        st.caption(f"Son tarama: {bot_config.son_tarama or 'Henuz yok'}")
        st.caption(f"Toplam tarama: {bot_config.toplam_tarama} | Toplam sinyal: {bot_config.toplam_sinyal}")
    else:
        st.warning("Bot DURDU")

    st.divider()

    # --- Ayarlar ---
    with st.expander("Tarama Ayarlari", expanded=not bot_aktif):
        col1, col2 = st.columns(2)
        with col1:
            tarama_araligi = st.number_input("Tarama araligi (dakika)", min_value=1, max_value=120,
                                              value=bot_config.tarama_araligi_dk, key="bot_aralik")
            bot_min_skor_val = st.slider("Min. surpriz skoru", 0, 100, int(bot_config.min_surpriz_skor), key="bot_min_skor")
            min_teknik = st.slider("Min. teknik skor", 0, 100, int(bot_config.min_teknik_skor), key="bot_min_teknik")
        with col2:
            min_ml = st.slider("Min. ML olasiligi (%)", 0, 100, int(bot_config.min_ml_olasilik * 100), key="bot_min_ml")
            hacim_esik = st.number_input("Hacim carpani esigi", min_value=1.0, max_value=10.0,
                                          value=bot_config.hacim_carpan_esik, step=0.5, key="bot_hacim")
            gun_sayisi_bot = st.number_input("Gecmis veri (gun)", min_value=30, max_value=365,
                                              value=bot_config.gun_sayisi, key="bot_gun")

    # --- Bildirim Ayarlari ---
    with st.expander("Bildirim Ayarlari", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("iMessage")
            imessage_aktif = st.checkbox("iMessage bildirimi", value=bot_config.bildirim_imessage, key="bot_imsg")
            imessage_numara = st.text_input("Telefon/Email", value=bot_config.imessage_numara,
                                             placeholder="+905551234567", key="bot_imsg_num")

            st.subheader("Ses")
            ses_aktif = st.checkbox("Ses bildirimi", value=bot_config.bildirim_ses, key="bot_ses")

        with col2:
            st.subheader("Telegram")
            telegram_aktif = st.checkbox("Telegram bildirimi", value=bot_config.bildirim_telegram, key="bot_tg")
            telegram_token = st.text_input("Bot Token", value=bot_config.telegram_token,
                                            type="password", key="bot_tg_token")
            telegram_chat = st.text_input("Chat ID", value=bot_config.telegram_chat_id, key="bot_tg_chat")

    # --- Ayarlari Kaydet ---
    if st.button("Ayarlari Kaydet", key="bot_kaydet"):
        bot_config.tarama_araligi_dk = tarama_araligi
        bot_config.min_surpriz_skor = float(bot_min_skor_val)
        bot_config.min_teknik_skor = float(min_teknik)
        bot_config.min_ml_olasilik = min_ml / 100.0
        bot_config.hacim_carpan_esik = hacim_esik
        bot_config.gun_sayisi = gun_sayisi_bot
        bot_config.bildirim_imessage = imessage_aktif
        bot_config.imessage_numara = imessage_numara
        bot_config.bildirim_ses = ses_aktif
        bot_config.bildirim_telegram = telegram_aktif
        bot_config.telegram_token = telegram_token
        bot_config.telegram_chat_id = telegram_chat
        try:
            bot_config.kaydet()
            st.success("Ayarlar kaydedildi!")
        except Exception as e:
            st.error(f"Ayar kaydetme hatasi: {e}")

    st.divider()

    # --- Kontrol Butonlari ---
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Botu Baslat", type="primary", use_container_width=True, key="bot_baslat",
                      disabled=bot_aktif):
            # Config guncelle
            bot_config.tarama_araligi_dk = tarama_araligi
            bot_config.min_surpriz_skor = float(bot_min_skor_val)
            bot_config.min_teknik_skor = float(min_teknik)
            bot_config.min_ml_olasilik = min_ml / 100.0
            bot_config.bildirim_imessage = imessage_aktif
            bot_config.imessage_numara = imessage_numara
            bot_config.bildirim_ses = ses_aktif
            bot_config.bildirim_telegram = telegram_aktif
            bot_config.telegram_token = telegram_token
            bot_config.telegram_chat_id = telegram_chat
            bot_config.kaydet()

            bot = BistBot(bot_config)
            bot.baslat()
            st.session_state.bot_instance = bot
            st.success("Bot baslatildi!")
            st.rerun()

    with col2:
        if st.button("Botu Durdur", use_container_width=True, key="bot_durdur",
                      disabled=not bot_aktif):
            if st.session_state.bot_instance:
                st.session_state.bot_instance.durdur()
                st.session_state.bot_instance = None
            st.warning("Bot durduruldu")
            st.rerun()

    with col3:
        if st.button("Tek Tarama", use_container_width=True, key="bot_tek"):
            try:
                with st.spinner("Tarama yapiliyor... (1-3 dk surebilir)"):
                    bot = BistBot(bot_config)
                    sinyaller = bot.tek_tarama()

                if sinyaller:
                    st.success(f"{len(sinyaller)} sinyal bulundu!")
                    sinyal_df = pd.DataFrame([{
                        "Hisse": s["ticker"].replace(".IS", ""),
                        "Sirket": ticker_isim(s["ticker"]),
                        "Skor": f"{s['birlesik_skor']:.0f}",
                        "Fiyat": f"{s['fiyat']:.2f}",
                        "Degisim %": f"{s.get('gunluk', s.get('gunluk_degisim', 0)):+.2f}",
                        "Teknik": f"{s['teknik_skor']:.0f}",
                        "ML %": f"{(s.get('ml_olasilik') or 0)*100:.0f}",
                    } for s in sinyaller])
                    st.dataframe(sinyal_df, use_container_width=True)
                else:
                    st.info("Esik degerlerini gecen sinyal bulunamadi")
            except Exception as e:
                st.error(f"Tarama hatasi: {e}")

    st.divider()

    # --- Sinyal Gecmisi ---
    st.subheader("Sinyal Gecmisi")
    try:
        gecmis = sinyal_gecmisi_oku()
    except Exception:
        gecmis = []

    if gecmis:
        st.caption(f"Toplam {len(gecmis)} kayit")
        # Son 20 kayit
        for kayit in reversed(gecmis[-20:]):
            zaman = kayit.get("zaman", "?")
            mesaj = kayit.get("mesaj", "")
            try:
                dt = datetime.fromisoformat(zaman)
                zaman_str = dt.strftime("%d/%m %H:%M")
            except Exception:
                zaman_str = str(zaman)[:16]

            st.text(f"[{zaman_str}] {mesaj[:150]}")

        if st.button("Gecmisi Temizle", key="bot_gecmis_temizle"):
            sinyal_gecmisi_temizle()
            st.rerun()
    else:
        st.info("Henuz sinyal kaydi yok")
  except Exception as e:
    st.error(f"Tab6 hatasi: {e}")
