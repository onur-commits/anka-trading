"""
ANKA Raporlar Merkezi — Sistemin Hafızası
==========================================
Tek bakışta geçmiş: işlemler, performans, sistem logları (audit), durum.
Hepsi CSV olarak dışa aktarılabilir.

Veri kaynakları (salt-okuma — trading koduna dokunmaz):
- data/otonom_trades.json  : GERCEK canli/paper emirler (varsa)
- data/islem_gecmisi.json  : SENTETIK egitim verisi (anka_ogrenme.py,
                              5 yil simulasyon, ajan agirligi ogretmek
                              icin — gercek trade kaydi DEGIL)
- data/otonom_log.json     : sistem aksiyon/audit loglari
- data/otonom_state.json   : guncel rejim + aktif stratejiler
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(page_title="ANKA Raporlar", page_icon="📊", layout="wide")


def yukle(dosya, varsayilan):
    """JSON güvenli oku — dosya yok/bozuksa varsayılan döner."""
    p = DATA_DIR / dosya
    try:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, ValueError, OSError):
        pass
    return varsayilan


def csv_indir(df: pd.DataFrame, dosya_adi: str, etiket: str):
    """DataFrame'i CSV download butonu olarak sun."""
    if df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8-sig")  # Excel Türkçe uyumlu
    st.download_button(
        f"📥 {etiket}",
        data=csv,
        file_name=dosya_adi,
        mime="text/csv",
        use_container_width=True,
    )


st.markdown("# 📊 ANKA Raporlar Merkezi")
st.caption("Sistemin hafızası — işlemler, performans, audit logları. Hepsi salt-okuma + CSV export.")

islem = yukle("islem_gecmisi.json", [])
gercek_trades = yukle("otonom_trades.json", [])
loglar = yukle("otonom_log.json", [])
state = yukle("otonom_state.json", {})

# Sentetik mi gercek mi ayrimi — kullanici dogru veriyi gorsun
SENTETIK_NOT = (
    "⚠️ Bu tablo `data/islem_gecmisi.json` — **sentetik 5 yıl simülasyon eğitim verisi** "
    "(`anka_ogrenme.py` ajan ağırlıklarını öğretmek için). "
    "Gerçek canlı/paper emirler `data/otonom_trades.json` dosyasında "
    "(bot canlıda emir verdikten sonra dolar)."
)
GERCEK_NOT = (
    "✅ Bu tablo `data/otonom_trades.json` — **gerçek canlı/paper emir kayıtları** "
    "(`otonom_trader.py`'nin yazdığı)."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 İşlem Raporu", "🏆 Performans", "🔍 Sistem / Audit Log", "🧭 Güncel Durum"]
)

# ══════════════════════════════════════════════════════════
# TAB 1: İŞLEM RAPORU
# ══════════════════════════════════════════════════════════
with tab1:
    # Hangi kaynak gosterilsin? Gercek varsa onu, yoksa sentetik (uyariyla)
    if gercek_trades:
        kaynak = st.radio(
            "Veri kaynağı",
            ["🟢 Gerçek emirler (otonom_trades.json)", "🟡 Sentetik eğitim verisi (islem_gecmisi.json)"],
            horizontal=True,
        )
        kayitlar = gercek_trades if kaynak.startswith("🟢") else islem
        st.info(GERCEK_NOT if kaynak.startswith("🟢") else SENTETIK_NOT)
    else:
        kayitlar = islem
        st.warning(SENTETIK_NOT + "\n\n_Gerçek emir log'u (otonom_trades.json) henüz yok — bot canlıda emir vermemiş._")

    if not kayitlar:
        st.info("Henüz işlem geçmişi yok.")
    else:
        df = pd.DataFrame(kayitlar)
        # ajan_kararlari dict → okunur sütun
        if "ajan_kararlari" in df.columns:
            df["ajanlar"] = df["ajan_kararlari"].apply(
                lambda d: ", ".join(f"{k}:{v}" for k, v in d.items()) if isinstance(d, dict) else ""
            )
            df = df.drop(columns=["ajan_kararlari"])

        kapanan = df[df.get("durum", "") == "KAPANDI"] if "durum" in df.columns else df

        # ── Outlier filtresi (BIST gunluk ~%10 tavan/taban; >|30%| supheli)
        if "kar_zarar_pct" in kapanan.columns and len(kapanan):
            outlier_say = ((kapanan["kar_zarar_pct"].abs() > 30)).sum()
            if outlier_say > 0:
                temizle = st.checkbox(
                    f"📊 Şüpheli outlier'ları gizle ({outlier_say} kayıt, |K/Z|>%30 — BIST'te tek işlemde gerçekçi değil)",
                    value=True,
                )
                if temizle:
                    kapanan = kapanan[kapanan["kar_zarar_pct"].abs() <= 30]
                    df = df[df.index.isin(kapanan.index) | (df.get("durum", "") != "KAPANDI")]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam İşlem", len(df))
        c2.metric("Kapanan", len(kapanan))
        if "kar_zarar_pct" in kapanan.columns and len(kapanan):
            kazanan = (kapanan["kar_zarar_pct"] > 0).sum()
            c3.metric("Kazanç Oranı", f"%{kazanan / len(kapanan) * 100:.1f}")
            c4.metric("Ortalama K/Z", f"%{kapanan['kar_zarar_pct'].mean():+.2f}")

        # Filtreler
        st.divider()
        fc1, fc2 = st.columns(2)
        with fc1:
            tickerlar = ["(hepsi)"] + sorted(df["ticker"].dropna().unique().tolist()) if "ticker" in df.columns else ["(hepsi)"]
            sec_ticker = st.selectbox("Hisse filtrele", tickerlar)
        with fc2:
            durumlar = ["(hepsi)"] + sorted(df["durum"].dropna().unique().tolist()) if "durum" in df.columns else ["(hepsi)"]
            sec_durum = st.selectbox("Durum filtrele", durumlar)

        gosterilen = df.copy()
        if sec_ticker != "(hepsi)" and "ticker" in gosterilen.columns:
            gosterilen = gosterilen[gosterilen["ticker"] == sec_ticker]
        if sec_durum != "(hepsi)" and "durum" in gosterilen.columns:
            gosterilen = gosterilen[gosterilen["durum"] == sec_durum]

        st.dataframe(gosterilen, use_container_width=True, height=420)
        csv_indir(gosterilen, f"anka_islemler_{datetime.now():%Y%m%d}.csv",
                  f"İşlem geçmişini indir ({len(gosterilen)} kayıt)")

# ══════════════════════════════════════════════════════════
# TAB 2: PERFORMANS
# ══════════════════════════════════════════════════════════
with tab2:
    kaynak_perf = gercek_trades if gercek_trades else islem
    if gercek_trades:
        st.info(GERCEK_NOT)
    else:
        st.warning(SENTETIK_NOT)
    if not kaynak_perf:
        st.info("Performans için işlem verisi gerekli.")
    else:
        df = pd.DataFrame(kaynak_perf)
        if "kar_zarar_pct" not in df.columns or "ticker" not in df.columns:
            st.warning("İşlem verisinde kar_zarar_pct / ticker alanı yok.")
        else:
            kapanan = df[df.get("durum", "") == "KAPANDI"] if "durum" in df.columns else df
            kapanan = kapanan.dropna(subset=["kar_zarar_pct"])

            if len(kapanan):
                outlier_say = (kapanan["kar_zarar_pct"].abs() > 30).sum()
                if outlier_say > 0:
                    temizle_p = st.checkbox(
                        f"📊 Şüpheli outlier'ları gizle ({outlier_say} kayıt, |K/Z|>%30)",
                        value=True, key="perf_outlier",
                    )
                    if temizle_p:
                        kapanan = kapanan[kapanan["kar_zarar_pct"].abs() <= 30]

                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Birikmiş K/Z", f"%{kapanan['kar_zarar_pct'].sum():+.1f}")
                if len(kapanan):
                    eniyi = kapanan.loc[kapanan["kar_zarar_pct"].idxmax()]
                    enkotu = kapanan.loc[kapanan["kar_zarar_pct"].idxmin()]
                    c2.metric("En İyi", f"{eniyi['ticker']} %{eniyi['kar_zarar_pct']:+.2f}")
                    c3.metric("En Kötü", f"{enkotu['ticker']} %{enkotu['kar_zarar_pct']:+.2f}")

                st.divider()
                st.subheader("Hisse Bazlı Performans")
                grup = kapanan.groupby("ticker")["kar_zarar_pct"].agg(
                    islem_sayisi="count",
                    ortalama_kz="mean",
                    toplam_kz="sum",
                ).reset_index()
                grup["kazanc_orani"] = kapanan.groupby("ticker")["kar_zarar_pct"].apply(
                    lambda s: (s > 0).mean() * 100
                ).values
                grup = grup.round(2).sort_values("toplam_kz", ascending=False)
                grup.columns = ["Hisse", "İşlem", "Ort. K/Z %", "Toplam K/Z %", "Kazanç %"]
                st.dataframe(grup, use_container_width=True, height=380)
                csv_indir(grup, f"anka_performans_{datetime.now():%Y%m%d}.csv",
                          "Performans tablosunu indir")
            else:
                st.info("Kapanan işlem yok.")

# ══════════════════════════════════════════════════════════
# TAB 3: SİSTEM / AUDIT LOG
# ══════════════════════════════════════════════════════════
with tab3:
    if not loglar:
        st.info("Sistem logu yok (data/otonom_log.json boş).")
    else:
        dfl = pd.DataFrame(loglar)
        st.caption(f"Toplam {len(dfl)} log kaydı — sistemin yaptığı her aksiyonun izi.")

        if "seviye" in dfl.columns:
            seviyeler = ["(hepsi)"] + sorted(dfl["seviye"].dropna().unique().tolist())
            sec = st.selectbox("Seviye filtrele", seviyeler)
            if sec != "(hepsi)":
                dfl = dfl[dfl["seviye"] == sec]

        ara = st.text_input("Mesajda ara", placeholder="örn. AUC, stop, emir, hata")
        if ara and "mesaj" in dfl.columns:
            dfl = dfl[dfl["mesaj"].str.contains(ara, case=False, na=False)]

        # En yeni üstte
        dfl = dfl.iloc[::-1].reset_index(drop=True)
        st.dataframe(dfl, use_container_width=True, height=440)
        csv_indir(dfl, f"anka_loglar_{datetime.now():%Y%m%d}.csv",
                  f"Logları indir ({len(dfl)} kayıt)")

# ══════════════════════════════════════════════════════════
# TAB 4: GÜNCEL DURUM
# ══════════════════════════════════════════════════════════
with tab4:
    if not state:
        st.info("Güncel durum yok (data/otonom_state.json boş).")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Piyasa Rejimi", str(state.get("rejim", "?")))
        c2.metric("Son Güncelleme", str(state.get("son_guncelleme", state.get("tarih", "?"))))

        bombalar = state.get("bombalar") or state.get("aktif_stratejiler") or []
        if bombalar:
            st.subheader("Aktif Bombalar / Stratejiler")
            if isinstance(bombalar, list):
                st.write(", ".join(str(b) for b in bombalar))
            else:
                st.json(bombalar)

        with st.expander("Ham state (JSON)"):
            st.json(state)
