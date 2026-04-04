"""
ANKA/COIN Haber & Sentiment Ajan — Gercek Veri Kaynaklari
==========================================================
Crypto:
  1. CryptoPanic (free public feed) — rising haberler
  2. Alternative.me Fear & Greed — 30 gunluk trend
  3. CoinGecko Trending — perakende FOMO gostergesi

BIST:
  4. Bloomberg HT RSS — Turkce finans haberleri
  5. KAP Aciklamalari — bedelsiz, temettu, sermaye artirimi vb.

Her kaynak 0-100 skor uretir, agirlikli birlesim yapilir.

Kullanim:
  from haber_ajan import HaberAjan
  ajan = HaberAjan()
  crypto_skor = ajan.crypto_sentiment()
  bist_skor   = ajan.bist_sentiment()
  rapor       = ajan.tam_rapor()
"""

import re
import json
import time
import warnings
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

warnings.filterwarnings("ignore")

# ── Lazy imports (opsiyonel bagimliliklar) ─────────────────────
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CACHE_FILE = DATA_DIR / "haber_ajan_cache.json"
LOG_FILE = DATA_DIR / "haber_ajan_log.json"


# ============================================================
# KEYWORD SOZLUKLERI
# ============================================================

CRYPTO_BULLISH = {
    "bull", "bullish", "buy", "long", "breakout", "surge", "rally",
    "pump", "moon", "ath", "all-time high", "profit", "growth",
    "adoption", "partnership", "institutional", "etf", "approval",
    "upgrade", "launch", "mainnet", "halving", "accumulation",
    "whale buy", "inflow", "green", "recover", "rebound",
}

CRYPTO_BEARISH = {
    "bear", "bearish", "sell", "short", "crash", "dump", "plunge",
    "hack", "exploit", "rug", "scam", "fraud", "regulation", "ban",
    "sec", "lawsuit", "fine", "bankrupt", "insolvency", "liquidation",
    "outflow", "red", "fear", "panic", "capitulation", "delisting",
    "vulnerability", "attack", "theft", "ponzi",
}

BIST_POZITIF = {
    "yukseldi", "yukselis", "artis", "artti", "tavan", "rekor",
    "zirve", "rallye", "ralli", "boga", "toparlanma", "guclendi",
    "sicrama", "firladi", "breakout", "kar", "kazanc", "gelir",
    "buyume", "temettu", "bedelsiz", "sermaye artirimi", "is birligi",
    "ortaklik", "anlasma", "ihale", "pozitif", "iyimser", "olumlu",
    "alim", "talep", "yabanci alimi", "hedef yukseltti",
    "faiz indirimi", "enflasyon dustu", "kredi notu",
    "outperform", "overweight", "upgrade",
}

BIST_NEGATIF = {
    "dustu", "dusus", "gerileme", "geriledi", "taban", "kayip",
    "zarar", "iflas", "konkordato", "haciz", "ceza", "sorusturma",
    "manipulasyon", "dolandiricilik", "satis", "arz", "cikis",
    "yabanci satisi", "hedef dusurdu", "downgrade", "underweight",
    "faiz artisi", "enflasyon yukseldi", "kur soku", "dolar yukseldi",
    "risk", "belirsizlik", "kriz", "durgunluk", "resesyon",
    "negatif", "kotumser", "olumsuz", "uyari",
}

# KAP ozel anahtar kelimeler (pozitif sinyaller)
KAP_POZITIF = {
    "bedelsiz", "temettu", "sermaye artirimi", "is birligi",
    "ortaklik", "ihale kazandi", "siparis aldi", "sozlesme imzalandi",
    "kar dagitimi", "geri alim", "pay alim", "hisse geri alim",
}

KAP_NEGATIF = {
    "zarar", "sermaye kaybetti", "iflas", "konkordato",
    "spk ceza", "sorusturma", "manipulasyon", "borsa kotasyondan cikarma",
    "tasfiye", "haciz", "odeme guclukleri",
}


# ============================================================
# YARDIMCI FONKSIYONLAR
# ============================================================

def _safe_get(url: str, timeout: int = 15) -> Optional[requests.Response]:
    """HTTP GET wrapper with retry."""
    if not HAS_REQUESTS:
        return None
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=timeout, headers={
                "User-Agent": "ANKA-COIN-SentimentBot/1.0"
            })
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:  # rate limit
                time.sleep(2 ** attempt)
                continue
        except Exception:
            time.sleep(1)
    return None


def _keyword_score(text: str, positive: set, negative: set) -> float:
    """Metin icindeki anahtar kelimelere gore 0-100 skor."""
    text_lower = text.lower()
    pos_count = sum(1 for kw in positive if kw in text_lower)
    neg_count = sum(1 for kw in negative if kw in text_lower)
    total = pos_count + neg_count
    if total == 0:
        return 50.0  # notr
    return round(100.0 * pos_count / total, 1)


def _trend_direction(values: List[float]) -> str:
    """Bir dizi degerin trend yonunu belirle."""
    if len(values) < 3:
        return "notr"
    recent = np.mean(values[-5:]) if len(values) >= 5 else np.mean(values[-3:])
    older = np.mean(values[:5])
    diff = recent - older
    if diff > 10:
        return "yukselis"
    elif diff < -10:
        return "dusus"
    return "notr"


# ============================================================
# ANA SINIF
# ============================================================

class HaberAjan:
    """
    ANKA/COIN sistemleri icin haber ve sentiment toplayici.
    Her kaynak 0-100 skor uretir.
    50 = notr, >50 = bullish, <50 = bearish.
    """

    def __init__(self, cache_ttl_min: int = 15):
        self.cache_ttl = timedelta(minutes=cache_ttl_min)
        self._cache = self._load_cache()

    # ── Cache ──────────────────────────────────────────────────

    def _load_cache(self) -> dict:
        try:
            if CACHE_FILE.exists():
                data = json.loads(CACHE_FILE.read_text())
                ts = datetime.fromisoformat(data.get("ts", "2000-01-01"))
                if datetime.now() - ts < self.cache_ttl:
                    return data
        except Exception:
            pass
        return {}

    def _save_cache(self):
        self._cache["ts"] = datetime.now().isoformat()
        try:
            CACHE_FILE.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2))
        except Exception:
            pass

    # ── LOG ────────────────────────────────────────────────────

    def _log(self, source: str, status: str, detail: str = ""):
        entry = {
            "ts": datetime.now().isoformat(),
            "source": source,
            "status": status,
            "detail": detail[:200],
        }
        try:
            log = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
        except Exception:
            log = []
        log.append(entry)
        log = log[-500:]  # son 500 kayit tut
        LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2))

    # ============================================================
    # CRYPTO KAYNAKLARI
    # ============================================================

    def _cryptopanic(self) -> Dict:
        """CryptoPanic free public feed — rising haberler."""
        if "cryptopanic" in self._cache:
            return self._cache["cryptopanic"]

        url = "https://cryptopanic.com/api/free/v1/posts/?auth_token=free&public=true&filter=rising"
        resp = _safe_get(url)
        if not resp:
            self._log("cryptopanic", "FAIL", "HTTP istegi basarisiz")
            return {"skor": 50.0, "haber_sayisi": 0, "basliklar": [], "kaynak": "cryptopanic"}

        try:
            data = resp.json()
            results = data.get("results", [])
            if not results:
                self._log("cryptopanic", "OK", "Haber yok")
                return {"skor": 50.0, "haber_sayisi": 0, "basliklar": [], "kaynak": "cryptopanic"}

            basliklar = [r.get("title", "") for r in results[:20]]
            birlesik = " ".join(basliklar)
            skor = _keyword_score(birlesik, CRYPTO_BULLISH, CRYPTO_BEARISH)

            # Votes-based adjustment
            pos_votes = sum(r.get("votes", {}).get("positive", 0) for r in results[:20])
            neg_votes = sum(r.get("votes", {}).get("negative", 0) for r in results[:20])
            if pos_votes + neg_votes > 0:
                vote_ratio = pos_votes / (pos_votes + neg_votes)
                skor = round(skor * 0.6 + vote_ratio * 100 * 0.4, 1)

            sonuc = {
                "skor": skor,
                "haber_sayisi": len(results),
                "basliklar": basliklar[:5],
                "kaynak": "cryptopanic",
            }
            self._cache["cryptopanic"] = sonuc
            self._log("cryptopanic", "OK", f"skor={skor}, haber={len(results)}")
            return sonuc

        except Exception as e:
            self._log("cryptopanic", "ERROR", str(e))
            return {"skor": 50.0, "haber_sayisi": 0, "basliklar": [], "kaynak": "cryptopanic"}

    def _fear_greed(self) -> Dict:
        """Alternative.me Fear & Greed Index — 30 gunluk trend."""
        if "fear_greed" in self._cache:
            return self._cache["fear_greed"]

        url = "https://api.alternative.me/fng/?limit=30"
        resp = _safe_get(url)
        if not resp:
            self._log("fear_greed", "FAIL", "HTTP istegi basarisiz")
            return {"skor": 50.0, "guncel": 50, "trend": "notr", "history": [], "kaynak": "fear_greed"}

        try:
            data = resp.json()
            items = data.get("data", [])
            if not items:
                return {"skor": 50.0, "guncel": 50, "trend": "notr", "history": [], "kaynak": "fear_greed"}

            values = [int(item["value"]) for item in reversed(items)]  # eski->yeni
            guncel = values[-1]
            trend = _trend_direction(values)

            # Skor: guncel deger + trend bonusu
            skor = float(guncel)
            if trend == "yukselis" and guncel < 30:
                # Extreme fear'dan yukselis = GUCLU AL sinyali
                skor = min(skor + 20, 95.0)
            elif trend == "dusus" and guncel > 70:
                # Extreme greed'den dusus = GUCLU SAT sinyali
                skor = max(skor - 20, 5.0)

            sonuc = {
                "skor": round(skor, 1),
                "guncel": guncel,
                "trend": trend,
                "sinif": items[0].get("value_classification", ""),
                "history_7d": values[-7:] if len(values) >= 7 else values,
                "kaynak": "fear_greed",
            }
            self._cache["fear_greed"] = sonuc
            self._log("fear_greed", "OK", f"guncel={guncel}, trend={trend}")
            return sonuc

        except Exception as e:
            self._log("fear_greed", "ERROR", str(e))
            return {"skor": 50.0, "guncel": 50, "trend": "notr", "history": [], "kaynak": "fear_greed"}

    def _coingecko_trending(self) -> Dict:
        """CoinGecko trending coins — perakende FOMO gostergesi."""
        if "coingecko_trending" in self._cache:
            return self._cache["coingecko_trending"]

        url = "https://api.coingecko.com/api/v3/search/trending"
        resp = _safe_get(url)
        if not resp:
            self._log("coingecko_trending", "FAIL", "HTTP istegi basarisiz")
            return {"skor": 50.0, "trending": [], "kaynak": "coingecko_trending"}

        try:
            data = resp.json()
            coins = data.get("coins", [])

            trending_list = []
            total_rank_score = 0
            for c in coins[:10]:
                item = c.get("item", {})
                trending_list.append({
                    "name": item.get("name", ""),
                    "symbol": item.get("symbol", ""),
                    "market_cap_rank": item.get("market_cap_rank"),
                    "price_btc": item.get("price_btc", 0),
                })
                # Dusuk market cap rank = daha fazla FOMO
                rank = item.get("market_cap_rank")
                if rank and rank < 50:
                    total_rank_score += 2  # buyuk coin trending = bullish
                elif rank and rank < 200:
                    total_rank_score += 1
                else:
                    total_rank_score += 0.5  # kucuk coin = FOMO ama riskli

            # Cok coin trending = piyasa hype'da
            hype_level = min(len(coins), 10) / 10.0  # 0-1
            skor = round(50 + (hype_level * 25) + (total_rank_score * 2), 1)
            skor = min(max(skor, 10), 90)

            sonuc = {
                "skor": skor,
                "trending": trending_list[:5],
                "trending_count": len(coins),
                "kaynak": "coingecko_trending",
            }
            self._cache["coingecko_trending"] = sonuc
            self._log("coingecko_trending", "OK", f"skor={skor}, count={len(coins)}")
            return sonuc

        except Exception as e:
            self._log("coingecko_trending", "ERROR", str(e))
            return {"skor": 50.0, "trending": [], "kaynak": "coingecko_trending"}

    # ============================================================
    # BIST KAYNAKLARI
    # ============================================================

    def _bloomberg_ht(self) -> Dict:
        """Bloomberg HT RSS — Turkce finans haberleri sentiment."""
        if "bloomberg_ht" in self._cache:
            return self._cache["bloomberg_ht"]

        if not HAS_FEEDPARSER:
            self._log("bloomberg_ht", "SKIP", "feedparser kurulu degil")
            return {"skor": 50.0, "haber_sayisi": 0, "basliklar": [], "kaynak": "bloomberg_ht"}

        url = "https://www.bloomberght.com/rss"
        try:
            feed = feedparser.parse(url)
            entries = feed.get("entries", [])
            if not entries:
                self._log("bloomberg_ht", "OK", "Haber yok")
                return {"skor": 50.0, "haber_sayisi": 0, "basliklar": [], "kaynak": "bloomberg_ht"}

            basliklar = [e.get("title", "") for e in entries[:30]]
            # Baslik + ozet birlesimi
            metinler = []
            for e in entries[:30]:
                metin = e.get("title", "") + " " + e.get("summary", "")
                metinler.append(metin)

            birlesik = " ".join(metinler)
            # Turkce karakterleri ASCII'ye donustur (arama icin)
            birlesik_ascii = birlesik.lower()
            for tr_char, ascii_char in [
                ("ı", "i"), ("ğ", "g"), ("ü", "u"), ("ş", "s"),
                ("ö", "o"), ("ç", "c"), ("İ", "i"), ("Ğ", "g"),
                ("Ü", "u"), ("Ş", "s"), ("Ö", "o"), ("Ç", "c"),
            ]:
                birlesik_ascii = birlesik_ascii.replace(tr_char, ascii_char)

            skor = _keyword_score(birlesik_ascii, BIST_POZITIF, BIST_NEGATIF)

            sonuc = {
                "skor": skor,
                "haber_sayisi": len(entries),
                "basliklar": basliklar[:5],
                "kaynak": "bloomberg_ht",
            }
            self._cache["bloomberg_ht"] = sonuc
            self._log("bloomberg_ht", "OK", f"skor={skor}, haber={len(entries)}")
            return sonuc

        except Exception as e:
            self._log("bloomberg_ht", "ERROR", str(e))
            return {"skor": 50.0, "haber_sayisi": 0, "basliklar": [], "kaynak": "bloomberg_ht"}

    def _kap_aciklamalar(self) -> Dict:
        """KAP (Kamuyu Aydinlatma Platformu) — onemli aciklamalar."""
        if "kap" in self._cache:
            return self._cache["kap"]

        # KAP'in resmi RSS/API'si yok, web scraping yapariz
        if not HAS_BS4 or not HAS_REQUESTS:
            self._log("kap", "SKIP", "bs4 veya requests kurulu degil")
            return {"skor": 50.0, "aciklamalar": [], "kaynak": "kap"}

        url = "https://www.kap.org.tr/tr/bildirim-sorgu"
        try:
            # KAP JSON API endpoint (bildirimler)
            api_url = "https://www.kap.org.tr/tr/api/bildirim/son"
            resp = _safe_get(api_url, timeout=10)

            if not resp:
                # Fallback: RSS varsa dene
                self._log("kap", "FAIL", "KAP API erisim hatasi")
                return {"skor": 50.0, "aciklamalar": [], "kaynak": "kap"}

            try:
                bildirimler = resp.json()
            except Exception:
                bildirimler = []

            if not isinstance(bildirimler, list):
                bildirimler = []

            # Bildirim basliklarindan sentiment cikart
            pozitif_count = 0
            negatif_count = 0
            onemli_aciklamalar = []

            for b in bildirimler[:50]:
                baslik = ""
                if isinstance(b, dict):
                    baslik = b.get("baslik", "") or b.get("disclosureTitle", "") or ""
                elif isinstance(b, str):
                    baslik = b

                baslik_lower = baslik.lower()
                # Turkce karakter normalizasyonu
                for tr_char, ascii_char in [
                    ("ı", "i"), ("ğ", "g"), ("ü", "u"), ("ş", "s"),
                    ("ö", "o"), ("ç", "c"),
                ]:
                    baslik_lower = baslik_lower.replace(tr_char, ascii_char)

                is_pozitif = any(kw in baslik_lower for kw in KAP_POZITIF)
                is_negatif = any(kw in baslik_lower for kw in KAP_NEGATIF)

                if is_pozitif:
                    pozitif_count += 1
                    onemli_aciklamalar.append({"baslik": baslik, "tip": "POZITIF"})
                if is_negatif:
                    negatif_count += 1
                    onemli_aciklamalar.append({"baslik": baslik, "tip": "NEGATIF"})

            total = pozitif_count + negatif_count
            if total == 0:
                skor = 50.0
            else:
                skor = round(100.0 * pozitif_count / total, 1)

            sonuc = {
                "skor": skor,
                "pozitif_count": pozitif_count,
                "negatif_count": negatif_count,
                "aciklamalar": onemli_aciklamalar[:10],
                "kaynak": "kap",
            }
            self._cache["kap"] = sonuc
            self._log("kap", "OK", f"skor={skor}, poz={pozitif_count}, neg={negatif_count}")
            return sonuc

        except Exception as e:
            self._log("kap", "ERROR", str(e))
            return {"skor": 50.0, "aciklamalar": [], "kaynak": "kap"}

    # ============================================================
    # BIRLESIK SENTIMENT
    # ============================================================

    def crypto_sentiment(self) -> Dict:
        """
        Crypto birlesik sentiment skoru.
        Agirliklar: CryptoPanic %40, Fear&Greed %35, Trending %25
        """
        cp = self._cryptopanic()
        fg = self._fear_greed()
        cg = self._coingecko_trending()

        birlesik = round(
            cp["skor"] * 0.40 +
            fg["skor"] * 0.35 +
            cg["skor"] * 0.25,
            1
        )

        # Siniflandirma
        if birlesik >= 75:
            sinif = "GUCLU_BULLISH"
        elif birlesik >= 60:
            sinif = "BULLISH"
        elif birlesik >= 40:
            sinif = "NOTR"
        elif birlesik >= 25:
            sinif = "BEARISH"
        else:
            sinif = "GUCLU_BEARISH"

        # Sinyal uret
        sinyal = "BEKLE"
        if birlesik >= 70:
            sinyal = "AL"
        elif birlesik <= 30:
            sinyal = "SAT"
        elif fg.get("trend") == "yukselis" and fg.get("guncel", 50) < 25:
            sinyal = "GUCLU_AL"  # Extreme fear'dan donus
        elif fg.get("trend") == "dusus" and fg.get("guncel", 50) > 75:
            sinyal = "GUCLU_SAT"  # Extreme greed'den donus

        self._save_cache()

        return {
            "sistem": "COIN",
            "birlesik_skor": birlesik,
            "sinif": sinif,
            "sinyal": sinyal,
            "ts": datetime.now().isoformat(),
            "kaynaklar": {
                "cryptopanic": cp,
                "fear_greed": fg,
                "coingecko_trending": cg,
            },
        }

    def bist_sentiment(self) -> Dict:
        """
        BIST birlesik sentiment skoru.
        Agirliklar: Bloomberg HT %50, KAP %50
        """
        bht = self._bloomberg_ht()
        kap = self._kap_aciklamalar()

        birlesik = round(
            bht["skor"] * 0.50 +
            kap["skor"] * 0.50,
            1
        )

        if birlesik >= 75:
            sinif = "GUCLU_BULLISH"
        elif birlesik >= 60:
            sinif = "BULLISH"
        elif birlesik >= 40:
            sinif = "NOTR"
        elif birlesik >= 25:
            sinif = "BEARISH"
        else:
            sinif = "GUCLU_BEARISH"

        sinyal = "BEKLE"
        if birlesik >= 70:
            sinyal = "AL"
        elif birlesik <= 30:
            sinyal = "SAT"

        self._save_cache()

        return {
            "sistem": "ANKA",
            "birlesik_skor": birlesik,
            "sinif": sinif,
            "sinyal": sinyal,
            "ts": datetime.now().isoformat(),
            "kaynaklar": {
                "bloomberg_ht": bht,
                "kap": kap,
            },
        }

    def tam_rapor(self) -> Dict:
        """Her iki sistem icin tam sentiment raporu."""
        crypto = self.crypto_sentiment()
        bist = self.bist_sentiment()

        return {
            "ts": datetime.now().isoformat(),
            "COIN": crypto,
            "ANKA": bist,
            "ozet": {
                "crypto_skor": crypto["birlesik_skor"],
                "crypto_sinyal": crypto["sinyal"],
                "bist_skor": bist["birlesik_skor"],
                "bist_sinyal": bist["sinyal"],
            },
        }

    def rapor_yazdir(self):
        """Konsola okunabilir rapor yazdir."""
        rapor = self.tam_rapor()

        print("\n" + "=" * 60)
        print("  HABER & SENTIMENT RAPORU")
        print(f"  {rapor['ts']}")
        print("=" * 60)

        for sistem in ["COIN", "ANKA"]:
            d = rapor[sistem]
            print(f"\n  [{sistem}] Birlesik Skor: {d['birlesik_skor']}/100")
            print(f"  Sinif: {d['sinif']} | Sinyal: {d['sinyal']}")
            print("  Kaynaklar:")
            for k, v in d["kaynaklar"].items():
                skor = v.get("skor", "?")
                print(f"    - {k}: {skor}/100")

        print("\n" + "=" * 60)
        ozet = rapor["ozet"]
        print(f"  CRYPTO: {ozet['crypto_skor']}/100 → {ozet['crypto_sinyal']}")
        print(f"  BIST:   {ozet['bist_skor']}/100 → {ozet['bist_sinyal']}")
        print("=" * 60 + "\n")


# ============================================================
# CLI KULLANIM
# ============================================================

if __name__ == "__main__":
    import sys

    ajan = HaberAjan()

    if "--crypto" in sys.argv:
        sonuc = ajan.crypto_sentiment()
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))
    elif "--bist" in sys.argv:
        sonuc = ajan.bist_sentiment()
        print(json.dumps(sonuc, indent=2, ensure_ascii=False))
    elif "--json" in sys.argv:
        rapor = ajan.tam_rapor()
        print(json.dumps(rapor, indent=2, ensure_ascii=False))
        # Dosyaya da kaydet
        out = DATA_DIR / "son_sentiment_rapor.json"
        out.write_text(json.dumps(rapor, indent=2, ensure_ascii=False))
        print(f"\nKaydedildi: {out}")
    else:
        ajan.rapor_yazdir()
