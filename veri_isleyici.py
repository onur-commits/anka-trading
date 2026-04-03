"""
Veri İşleyici
- yfinance ile geçmiş veri çekme
- Matrix IQ screenshot OCR
- CSV/Excel dosya parse
- Manuel veri girişi birleştirme
"""

import pandas as pd
import numpy as np
import re
from io import BytesIO
from pathlib import Path

# BIST 100 hisselerinin Yahoo Finance tickerları
BIST_TICKERS = [
    "THYAO.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS", "BIMAS.IS",
    "KCHOL.IS", "SAHOL.IS", "TUPRS.IS", "SISE.IS", "ASELS.IS",
    "PGSUS.IS", "TAVHL.IS", "TCELL.IS", "TOASO.IS", "FROTO.IS",
    "VESTL.IS", "MGROS.IS", "SOKM.IS", "YKBNK.IS", "ISCTR.IS",
    "HALKB.IS", "VAKBN.IS", "PETKM.IS", "DOHOL.IS", "EKGYO.IS",
    "ENKAI.IS", "ARCLK.IS", "TTKOM.IS", "SASA.IS", "GUBRF.IS",
    "KONTR.IS", "CIMSA.IS", "ULKER.IS", "AEFES.IS", "AKSA.IS",
    "ALARK.IS", "AGHOL.IS", "BRYAT.IS", "CCOLA.IS", "DOAS.IS",
    "GESAN.IS", "HEKTS.IS", "ISGYO.IS", "KORDS.IS", "OTKAR.IS",
    "SELEC.IS", "TRGYO.IS", "AKSEN.IS", "ODAS.IS", "ISMEN.IS",
]

TICKER_ISIMLERI = {
    "THYAO": "Türk Hava Yolları", "GARAN": "Garanti Bankası",
    "AKBNK": "Akbank", "EREGL": "Ereğli Demir Çelik",
    "BIMAS": "BİM Mağazaları", "KCHOL": "Koç Holding",
    "SAHOL": "Sabancı Holding", "TUPRS": "Tüpraş",
    "SISE": "Şişecam", "ASELS": "Aselsan",
    "PGSUS": "Pegasus", "TAVHL": "TAV Havalimanları",
    "TCELL": "Turkcell", "TOASO": "Tofaş",
    "FROTO": "Ford Otosan", "VESTL": "Vestel",
    "MGROS": "Migros", "SOKM": "Şok Marketler",
    "YKBNK": "Yapı Kredi", "ISCTR": "İş Bankası C",
    "HALKB": "Halkbank", "VAKBN": "Vakıfbank",
    "PETKM": "Petkim", "DOHOL": "Doğan Holding",
    "EKGYO": "Emlak Konut GYO", "ENKAI": "Enka İnşaat",
    "ARCLK": "Arçelik", "TTKOM": "Türk Telekom",
    "SASA": "Sasa Polyester", "GUBRF": "Gübre Fabrikaları",
    "KONTR": "Kontrolmatik", "CIMSA": "Çimsa",
    "ULKER": "Ülker", "AEFES": "Anadolu Efes",
    "AKSA": "Aksa Akrilik", "ALARK": "Alarko Holding",
    "AGHOL": "Anadolu Grubu", "BRYAT": "Borusan Yatırım",
    "CCOLA": "Coca-Cola İçecek", "DOAS": "Doğuş Otomotiv",
    "GESAN": "Giresun San.", "HEKTS": "Hektaş",
    "ISGYO": "İş GYO", "KORDS": "Kordsa",
    "OTKAR": "Otokar", "SELEC": "Selçuk Ecza",
    "TRGYO": "Torunlar GYO", "AKSEN": "Aksa Enerji",
    "ODAS": "Odaş Elektrik", "ISMEN": "İş Yatırım",
}


def ticker_isim(ticker):
    """Ticker kodundan şirket adını döner."""
    kod = ticker.replace(".IS", "")
    return TICKER_ISIMLERI.get(kod, kod)


# ============================================================
# YFİNANCE VERİ ÇEKİMİ
# ============================================================

def gecmis_veri_cek(ticker, gun=120):
    """Tek hisse için geçmiş veri çeker."""
    import yfinance as yf
    from datetime import datetime, timedelta

    try:
        bitis = datetime.now()
        baslangic = bitis - timedelta(days=gun)
        df = yf.download(ticker, start=baslangic, end=bitis, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return None


def tum_verileri_cek(tickers=None, gun=120, progress_callback=None):
    """Birden fazla hisse verisini çeker."""
    if tickers is None:
        tickers = BIST_TICKERS

    veriler = {}
    toplam = len(tickers)

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i / toplam, f"{ticker.replace('.IS', '')} çekiliyor...")

        df = gecmis_veri_cek(ticker, gun)
        if df is not None and len(df) > 20:
            veriler[ticker] = df

    if progress_callback:
        progress_callback(1.0, "Tamamlandı!")

    return veriler


# ============================================================
# SCREENSHOT OCR (Matrix IQ)
# ============================================================

def screenshot_ocr(image_bytes):
    """Screenshot'tan hisse verilerini çıkarır.
    Matrix IQ tablo formatını parse eder.
    """
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return None, "pytesseract veya Pillow yüklü değil"

    try:
        image = Image.open(BytesIO(image_bytes))

        # Görüntüyü büyüt (OCR doğruluğu için)
        width, height = image.size
        if width < 1000:
            ratio = 1500 / width
            image = image.resize((int(width * ratio), int(height * ratio)))

        # Gri tonlama
        image = image.convert("L")

        # OCR
        text = pytesseract.image_to_string(image, lang="tur+eng")

        return _parse_borsa_text(text)
    except Exception as e:
        return None, f"OCR hatası: {str(e)}"


def _parse_borsa_text(text):
    """OCR çıktısından hisse verilerini parse eder."""
    satirlar = text.strip().split("\n")
    veriler = []

    # Bilinen BIST ticker kodları
    bilinen_kodlar = set(TICKER_ISIMLERI.keys())

    for satir in satirlar:
        satir = satir.strip()
        if not satir:
            continue

        # Hisse kodu bul (3-5 büyük harf)
        kod_match = re.findall(r'\b([A-ZÇĞİÖŞÜ]{3,5})\b', satir)

        # Sayıları bul (fiyat ve hacim)
        sayilar = re.findall(r'[\d.,]+', satir)

        for kod in kod_match:
            if kod in bilinen_kodlar or len(kod) >= 4:
                fiyatlar = []
                for s in sayilar:
                    try:
                        deger = float(s.replace(",", ".").replace(".", "", s.count(".") - 1) if s.count(".") > 1 else s.replace(",", "."))
                        fiyatlar.append(deger)
                    except ValueError:
                        continue

                if fiyatlar:
                    veri = {"kod": kod, "fiyat": fiyatlar[0]}
                    if len(fiyatlar) > 1:
                        veri["degisim"] = fiyatlar[1]
                    if len(fiyatlar) > 2:
                        veri["hacim"] = fiyatlar[2]
                    veriler.append(veri)
                    break

    if not veriler:
        return None, "Görüntüden hisse verisi çıkarılamadı. Lütfen tablo içeren net bir screenshot yükleyin."

    return pd.DataFrame(veriler), None


# ============================================================
# CSV / EXCEL PARSE
# ============================================================

def dosya_parse(uploaded_file):
    """CSV veya Excel dosyasını parse eder."""
    try:
        dosya_adi = uploaded_file.name.lower()

        if dosya_adi.endswith(".csv") or dosya_adi.endswith(".tsv"):
            # Separator otomatik algılama
            sep = "\t" if dosya_adi.endswith(".tsv") else None
            df = pd.read_csv(uploaded_file, sep=sep, engine="python")
        elif dosya_adi.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            return None, "Desteklenmeyen dosya formatı. CSV, TSV veya Excel yükleyin."

        if df.empty:
            return None, "Dosya boş."

        # Sütun eşleştirme (esnek)
        df = _sutun_eslestir(df)
        return df, None

    except Exception as e:
        return None, f"Dosya okuma hatası: {str(e)}"


def _sutun_eslestir(df):
    """Sütun isimlerini standart formata eşleştirir."""
    sutun_map = {}
    for col in df.columns:
        col_lower = str(col).lower().strip()

        if col_lower in ("kod", "hisse", "ticker", "sembol", "symbol", "name", "hisse kodu"):
            sutun_map[col] = "kod"
        elif col_lower in ("fiyat", "son", "close", "kapanış", "kapanis", "last", "son fiyat"):
            sutun_map[col] = "fiyat"
        elif col_lower in ("değişim", "degisim", "change", "%", "yüzde", "değişim %", "degisim %"):
            sutun_map[col] = "degisim"
        elif col_lower in ("hacim", "volume", "lot", "miktar"):
            sutun_map[col] = "hacim"
        elif col_lower in ("yüksek", "yuksek", "high", "en yüksek"):
            sutun_map[col] = "yuksek"
        elif col_lower in ("düşük", "dusuk", "low", "en düşük"):
            sutun_map[col] = "dusuk"

    if sutun_map:
        df = df.rename(columns=sutun_map)

    return df


# ============================================================
# VERİ BİRLEŞTİRME
# ============================================================

def canli_veri_birlestir(gecmis_df, canli_veriler):
    """Canlı verilerle geçmiş verileri birleştirir.
    canli_veriler: DataFrame with 'kod', 'fiyat', optionally 'hacim', 'degisim'
    """
    if canli_veriler is None or gecmis_df is None:
        return gecmis_df

    guncellenen = {}

    for _, satir in canli_veriler.iterrows():
        kod = satir.get("kod", "")
        if not kod:
            continue

        ticker = f"{kod}.IS"
        if ticker in gecmis_df:
            df = gecmis_df[ticker].copy()
            # Son satırı güncelle
            if "fiyat" in satir and pd.notna(satir["fiyat"]):
                df.iloc[-1, df.columns.get_loc("Close")] = satir["fiyat"]
            if "hacim" in satir and pd.notna(satir.get("hacim")):
                df.iloc[-1, df.columns.get_loc("Volume")] = satir["hacim"]
            guncellenen[ticker] = df

    # Birleştir
    sonuc = dict(gecmis_df)
    sonuc.update(guncellenen)
    return sonuc
