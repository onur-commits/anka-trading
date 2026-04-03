"""
BIST ALPHA V2 — Türkçe Haber Sentiment Analizi
=================================================
- Borsa haberleri scraping (RSS + web)
- Türkçe finansal kelime bazlı sentiment
- Hisse bazlı haber skoru
- Piyasa genel duygu analizi
"""

import re
import json
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# TÜRKÇE FİNANSAL SENTIMENT SÖZLÜĞÜ
# ============================================================

POZITIF = {
    # Fiyat/Performans
    "yükseldi", "yükseliş", "artış", "arttı", "artıyor", "yükseliyor",
    "tavan", "rekor", "zirve", "rallye", "ralli", "boğa", "bull",
    "toparlanma", "toparlandı", "güçlendi", "güçleniyor", "ivme",
    "sıçrama", "sıçradı", "fırladı", "fırlama", "aştı", "geçti",
    "kırdı", "kırılım", "breakout", "tepki",

    # Finansal
    "kâr", "kar", "kazanç", "gelir", "büyüme", "büyüdü", "temettü",
    "beklenti aştı", "beklentinin üzerinde", "güçlü bilanço",
    "pozitif", "iyimser", "olumlu", "umut verici",

    # Piyasa
    "alım", "talep", "yabancı alımı", "net alım", "giriş",
    "yatırım", "destek", "hedef yükseltti", "tavsiye",
    "outperform", "overweight", "al", "tut",

    # Makro
    "faiz indirimi", "enflasyon düştü", "dolar düştü",
    "kredi notu yükseldi", "upgrade", "reform",
}

NEGATIF = {
    # Fiyat/Performans
    "düştü", "düşüş", "geriledi", "gerileme", "azaldı", "azalış",
    "taban", "dip", "çakıldı", "çöktü", "eridi", "eriyor",
    "ayı", "bear", "satış baskısı", "kan kaybı", "sert düşüş",
    "kayıp", "kaybetti", "kırıldı", "bozuldu", "zayıfladı",

    # Finansal
    "zarar", "ziyan", "borç", "iflas", "konkordato", "haciz",
    "beklentinin altında", "hayal kırıklığı", "negatif",
    "kötümser", "olumsuz", "endişe", "risk", "tehlike",

    # Piyasa
    "satım", "çıkış", "yabancı satışı", "net satış",
    "hedef düşürdü", "downgrade", "underperform", "sat",

    # Makro
    "faiz artışı", "enflasyon yükseldi", "dolar yükseldi",
    "kredi notu düşürüldü", "kriz", "resesyon", "durgunluk",
    "belirsizlik", "jeopolitik", "savaş", "yaptırım",
}

# Ağırlıklı kelimeler (çok güçlü sinyal)
COKPOZITIF = {"rekor", "tavan", "fırladı", "beklenti aştı", "breakout", "temettü"}
COKNEGATIF = {"çöktü", "iflas", "konkordato", "kriz", "çakıldı", "taban"}


# ============================================================
# HISSE İSİM EŞLEŞTİRME
# ============================================================

HISSE_ISIMLERI = {
    "THYAO": ["thy", "türk hava yolları", "türk hava", "thyao"],
    "GARAN": ["garanti", "garanti bankası", "garanti bbva", "garan"],
    "AKBNK": ["akbank", "akbnk"],
    "ISCTR": ["iş bankası", "işbank", "iş bank", "isctr"],
    "YKBNK": ["yapı kredi", "yapıkredi", "ykbnk"],
    "HALKB": ["halkbank", "halk bankası", "halkb"],
    "VAKBN": ["vakıfbank", "vakıf bankası", "vakbn"],
    "EREGL": ["erdemir", "ereğli", "eregl"],
    "SAHOL": ["sabancı", "sahol"],
    "KCHOL": ["koç", "koç holding", "kchol"],
    "TUPRS": ["tüpraş", "tuprs"],
    "BIMAS": ["bim", "bimas"],
    "MGROS": ["migros", "mgros"],
    "SOKM": ["şok", "şok market", "sokm"],
    "ASELS": ["aselsan", "asels"],
    "TOASO": ["tofaş", "toaso"],
    "SISE": ["şişecam", "şişe cam", "sise"],
    "PGSUS": ["pegasus", "pgsus"],
    "TCELL": ["turkcell", "tcell"],
    "FROTO": ["ford otosan", "ford", "froto"],
    "PETKM": ["petkim", "petkm"],
    "ENKAI": ["enka", "enkai"],
    "VESTL": ["vestel", "vestl"],
    "ARCLK": ["arçelik", "arclk"],
    "SASA": ["sasa", "sasa polyester"],
    "EKGYO": ["emlak konut", "ekgyo"],
}


def hisse_bul(metin):
    """Metinde geçen BIST hisselerini bulur."""
    metin_lower = metin.lower()
    bulunan = set()

    for ticker, isimler in HISSE_ISIMLERI.items():
        for isim in isimler:
            if isim in metin_lower:
                bulunan.add(ticker)
                break

    # Direkt ticker kodu arama (THYAO, GARAN gibi)
    ticker_pattern = re.findall(r'\b([A-Z]{3,5})\b', metin)
    for t in ticker_pattern:
        if t in HISSE_ISIMLERI:
            bulunan.add(t)

    return list(bulunan)


# ============================================================
# SENTIMENT HESAPLAMA
# ============================================================

def metin_sentiment(metin):
    """
    Türkçe finansal metin sentiment skoru.
    Returns: -1.0 (çok negatif) ... +1.0 (çok pozitif)
    """
    if not metin:
        return 0.0

    metin_lower = metin.lower()
    kelimeler = re.findall(r'\w+', metin_lower)

    poz_skor = 0
    neg_skor = 0

    # Tek kelime eşleştirme
    for k in kelimeler:
        if k in POZITIF:
            poz_skor += 1
        if k in NEGATIF:
            neg_skor += 1

    # Çoklu kelime (bigram/trigram) eşleştirme
    for ifade in POZITIF:
        if " " in ifade and ifade in metin_lower:
            poz_skor += 2  # çoklu kelime = daha güçlü sinyal
    for ifade in NEGATIF:
        if " " in ifade and ifade in metin_lower:
            neg_skor += 2

    # Çok güçlü sinyaller
    for ifade in COKPOZITIF:
        if ifade in metin_lower:
            poz_skor += 3
    for ifade in COKNEGATIF:
        if ifade in metin_lower:
            neg_skor += 3

    toplam = poz_skor + neg_skor
    if toplam == 0:
        return 0.0

    return round((poz_skor - neg_skor) / toplam, 3)


# ============================================================
# HABER KAYNAKLARI
# ============================================================

def haberleri_cek_rss():
    """RSS kaynaklarından borsa haberleri çeker."""
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
    except ImportError:
        return []

    RSS_FEEDS = [
        "https://www.bloomberght.com/rss",
        "https://www.dunya.com/rss",
    ]

    haberler = []
    for url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml = resp.read()
            root = ET.fromstring(xml)

            for item in root.findall(".//item")[:20]:
                baslik = item.findtext("title", "")
                aciklama = item.findtext("description", "")
                tarih = item.findtext("pubDate", "")
                link = item.findtext("link", "")

                haberler.append({
                    "baslik": baslik,
                    "aciklama": aciklama[:500],
                    "tarih": tarih,
                    "kaynak": url.split("/")[2],
                    "link": link,
                })
        except Exception:
            continue

    return haberler


def haberleri_analiz_et(haberler=None):
    """
    Haberleri çeker ve sentiment analizi yapar.
    Returns: {
        "genel_sentiment": float,
        "hisse_sentiments": {ticker: {"skor": float, "haber_sayisi": int}},
        "son_haberler": [...],
        "analiz_zamani": str,
    }
    """
    if haberler is None:
        haberler = haberleri_cek_rss()

    if not haberler:
        return {
            "genel_sentiment": 0,
            "hisse_sentiments": {},
            "son_haberler": [],
            "analiz_zamani": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "haber_sayisi": 0,
        }

    # Her haber için sentiment
    hisse_skorlar = {}  # {ticker: [skor1, skor2, ...]}
    tum_skorlar = []
    analiz_edilmis = []

    for haber in haberler:
        tam_metin = f"{haber['baslik']} {haber.get('aciklama', '')}"
        skor = metin_sentiment(tam_metin)
        tum_skorlar.append(skor)

        # Hangi hisselerden bahsediyor?
        hisseler = hisse_bul(tam_metin)

        haber_analiz = {
            **haber,
            "sentiment": skor,
            "ilgili_hisseler": hisseler,
            "sinyal": "🟢" if skor > 0.2 else "🔴" if skor < -0.2 else "⚪",
        }
        analiz_edilmis.append(haber_analiz)

        for h in hisseler:
            if h not in hisse_skorlar:
                hisse_skorlar[h] = []
            hisse_skorlar[h].append(skor)

    # Hisse bazlı ortalama sentiment
    hisse_sentiments = {}
    for ticker, skorlar in hisse_skorlar.items():
        hisse_sentiments[ticker] = {
            "skor": round(np.mean(skorlar), 3),
            "haber_sayisi": len(skorlar),
            "max_skor": round(max(skorlar), 3),
            "min_skor": round(min(skorlar), 3),
        }

    # Genel piyasa sentiment
    genel = round(np.mean(tum_skorlar), 3) if tum_skorlar else 0

    sonuc = {
        "genel_sentiment": genel,
        "genel_sinyal": "POZITIF" if genel > 0.1 else "NEGATIF" if genel < -0.1 else "NÖTR",
        "hisse_sentiments": hisse_sentiments,
        "son_haberler": analiz_edilmis[:10],
        "analiz_zamani": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "haber_sayisi": len(haberler),
    }

    # Kaydet
    cache_path = DATA_DIR / "sentiment_cache.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2, default=str)

    return sonuc


def hisse_sentiment_al(ticker):
    """Tek hisse için sentiment skoru döndürür (cache'den)."""
    cache_path = DATA_DIR / "sentiment_cache.json"
    if not cache_path.exists():
        return None

    with open(cache_path, encoding="utf-8") as f:
        data = json.load(f)

    ticker_temiz = ticker.replace(".IS", "")
    return data.get("hisse_sentiments", {}).get(ticker_temiz)


# ============================================================
# SENTIMENT'I ML'E ENTEGRE ETME
# ============================================================

def sentiment_feature_ekle(ticker, features_df):
    """
    Haber sentiment'ini ML feature'ına çevirir.
    Features_df'e 'haber_sentiment' kolonu ekler.
    """
    sentiment = hisse_sentiment_al(ticker)
    if sentiment:
        features_df["haber_sentiment"] = sentiment["skor"]
        features_df["haber_sayisi"] = sentiment["haber_sayisi"]
    else:
        features_df["haber_sentiment"] = 0.0
        features_df["haber_sayisi"] = 0

    # Genel piyasa sentiment
    cache_path = DATA_DIR / "sentiment_cache.json"
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        features_df["piyasa_sentiment"] = data.get("genel_sentiment", 0)
    else:
        features_df["piyasa_sentiment"] = 0.0

    return features_df


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":
    print("📰 Haber Sentiment Analizi başlıyor...")
    print()

    sonuc = haberleri_analiz_et()

    print(f"📊 Genel Piyasa: {sonuc['genel_sinyal']} ({sonuc['genel_sentiment']:+.3f})")
    print(f"📰 {sonuc['haber_sayisi']} haber analiz edildi")
    print()

    if sonuc["hisse_sentiments"]:
        print("📈 Hisse Bazlı Sentiment:")
        sirali = sorted(
            sonuc["hisse_sentiments"].items(),
            key=lambda x: x[1]["skor"],
            reverse=True,
        )
        for ticker, info in sirali[:10]:
            sinyal = "🟢" if info["skor"] > 0.1 else "🔴" if info["skor"] < -0.1 else "⚪"
            print(f"  {sinyal} {ticker:6s} → {info['skor']:+.3f} ({info['haber_sayisi']} haber)")

    print()
    if sonuc["son_haberler"]:
        print("📝 Son Haberler:")
        for h in sonuc["son_haberler"][:5]:
            print(f"  {h['sinyal']} [{h['sentiment']:+.3f}] {h['baslik'][:80]}")
