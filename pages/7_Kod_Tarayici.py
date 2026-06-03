"""
ANKA Kod Tarayıcı — Tüm program koduna tek panelden eriş
=========================================================
Salt-okuma. Repodaki tüm kaynak dosyaları (.py / .md / .yml / .bat / .sh)
listeler, seçince renkli (syntax highlight) gösterir, içerikte arama yapar.
Hiçbir dosyayı değiştirmez.
"""

from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent.parent

st.set_page_config(page_title="ANKA Kod Tarayıcı", page_icon="📂", layout="wide")
st.markdown("# 📂 ANKA Kod Tarayıcı")
st.caption("Programın tüm kaynak kodu — tek panelden, salt-okuma.")

# Hangi uzantılar + dil eşlemesi (syntax highlight için)
UZANTI_DIL = {
    ".py": "python", ".md": "markdown", ".yml": "yaml", ".yaml": "yaml",
    ".bat": "bat", ".sh": "bash", ".json": "json", ".toml": "toml",
    ".txt": "text", ".cs": "csharp",
}
HARIC = {".venv", "__pycache__", ".git", "node_modules", ".ruff_cache",
         ".pytest_cache", ".mypy_cache"}


@st.cache_data(ttl=30)
def dosyalari_tara():
    """Repodaki tüm kaynak dosyaları topla (haric klasörler hariç)."""
    bulunan = []
    for p in sorted(BASE_DIR.rglob("*")):
        if not p.is_file():
            continue
        if any(h in p.parts for h in HARIC):
            continue
        if p.suffix.lower() in UZANTI_DIL:
            try:
                boyut = p.stat().st_size
            except OSError:
                boyut = 0
            bulunan.append((str(p.relative_to(BASE_DIR)), p, boyut))
    return bulunan


dosyalar = dosyalari_tara()

# ── Üst metrikler ──
c1, c2, c3 = st.columns(3)
c1.metric("Toplam dosya", len(dosyalar))
c2.metric("Python", sum(1 for d in dosyalar if d[0].endswith(".py")))
c3.metric("Toplam boyut", f"{sum(d[2] for d in dosyalar) / 1024:.0f} KB")

st.divider()

sol, sag = st.columns([1, 3])

with sol:
    st.subheader("Dosyalar")
    # Uzantı filtresi
    uzantilar = sorted({Path(d[0]).suffix for d in dosyalar})
    sec_uz = st.multiselect("Tür filtrele", uzantilar, default=[".py"])
    # İsim araması
    ara_isim = st.text_input("Dosya adında ara", placeholder="örn. otonom, beyin")

    liste = [d for d in dosyalar
             if (not sec_uz or Path(d[0]).suffix in sec_uz)
             and (not ara_isim or ara_isim.lower() in d[0].lower())]

    st.caption(f"{len(liste)} dosya")
    secenekler = [d[0] for d in liste]
    secili = st.radio("Seç", secenekler, label_visibility="collapsed") if secenekler else None

with sag:
    if secili:
        yol = BASE_DIR / secili
        dil = UZANTI_DIL.get(yol.suffix.lower(), "text")
        try:
            icerik = yol.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            icerik = f"(okunamadı: {e})"
            dil = "text"

        satir = icerik.count("\n") + 1
        st.subheader(f"`{secili}`")
        st.caption(f"{satir} satır · {len(icerik) / 1024:.1f} KB · {dil}")

        # İçerikte arama (vurgulamak yerine eşleşen satırları göster)
        ara_ic = st.text_input("İçerikte ara (satır filtrele)", key="ic_ara",
                               placeholder="örn. alis_emri, MIN_BOMBA")
        if ara_ic:
            eslesen = [f"{i+1:>5}: {ln}" for i, ln in enumerate(icerik.splitlines())
                       if ara_ic.lower() in ln.lower()]
            st.caption(f"{len(eslesen)} eşleşen satır")
            st.code("\n".join(eslesen) if eslesen else "(eşleşme yok)", language=dil)
            with st.expander("Tüm dosyayı göster"):
                st.code(icerik, language=dil)
        else:
            st.code(icerik, language=dil)

        st.download_button("📥 Bu dosyayı indir", data=icerik.encode("utf-8"),
                           file_name=yol.name, use_container_width=True)
    else:
        st.info("Soldan bir dosya seç.")
