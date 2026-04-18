"""
BIST100 Hisse Listesi (T2/T1 hariç)
Son güncelleme: 2026-04-15
Kaynak: Borsa Istanbul BIST100 endeks bileşenleri
"""

# BIST100 — T2 ve T1 pazar hisseleri hariç
BIST100 = [
    # Bankalar
    "GARAN.IS", "AKBNK.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS",
    "TSKB.IS", "ALBRK.IS", "QNBFB.IS",
    # Holdingler
    "SAHOL.IS", "KCHOL.IS", "TAVHL.IS", "DOHOL.IS", "AGHOL.IS",
    # Sanayi / Otomotiv
    "EREGL.IS", "TOASO.IS", "TUPRS.IS", "SISE.IS", "FROTO.IS", "OTKAR.IS",
    "TTRAK.IS", "KORDS.IS", "BRISA.IS", "CIMSA.IS", "EGEEN.IS", "CEMTS.IS",
    # Enerji
    "AKSEN.IS", "ODAS.IS", "ENJSA.IS", "AYEN.IS", "EUPWR.IS",
    # Teknoloji / Savunma
    "ASELS.IS", "LOGO.IS", "NETAS.IS",
    # Perakende / Ticaret
    "BIMAS.IS", "MGROS.IS", "SOKM.IS", "CCOLA.IS", "TRGYO.IS",
    # Havayolu / Turizm
    "THYAO.IS", "PGSUS.IS",
    # Telekom
    "TCELL.IS", "TTKOM.IS",
    # İnşaat / GYO
    "ENKAI.IS", "EKGYO.IS", "ISGYO.IS", "SMRTG.IS",
    # Kimya / Gübre / Petrokimya
    "PETKM.IS", "GUBRF.IS", "HEKTS.IS", "SASA.IS",
    # Gıda / İçecek
    "ULKER.IS", "AEFES.IS", "BANVT.IS",
    # Madencilik
    "KOZAL.IS", "KOZAA.IS", "IPEKE.IS",
    # Diğer Sanayi
    "TKFEN.IS", "VESTL.IS", "ARCLK.IS", "GESAN.IS", "KONTR.IS",
    "MPARK.IS", "ASTOR.IS", "ALARK.IS",
    # Cam / Seramik
    "TRKCM.IS", "KRDMA.IS", "KRDMB.IS",
    # Gayrimenkul
    "PGSUS.IS", "KLRHO.IS",
    # Sigorta
    "ANHYT.IS", "AGESA.IS",
    # Finansal Kiralama
    "GLYHO.IS",
    # Kağıt / Ambalaj
    "KARTN.IS",
    # Tarım
    "TATGD.IS",
    # Tekstil
    "MAVI.IS",
    # Lojistik
    "CLEBI.IS",
    # İlaç / Sağlık
    "SELEC.IS", "DEVA.IS",
    # Yatırım Ortaklıkları (hariç tutulabilir ama likitler)
    "SKBNK.IS",
    # Ek BIST100 üyeleri
    "PRKME.IS", "BERA.IS", "OYAKC.IS", "BTCIM.IS",
    "VESBE.IS", "AKFGY.IS", "BOYP.IS", "MIATK.IS",
    "ISSEN.IS", "TURSG.IS", "CANTE.IS", "RGYAS.IS",
]

# Tekrarları kaldır
BIST100 = list(dict.fromkeys(BIST100))
