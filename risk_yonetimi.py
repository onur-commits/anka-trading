"""
BIST ALPHA V2 — Dinamik Risk Yönetimi
=======================================
- ATR bazlı dinamik stop-loss
- Kelly Criterion pozisyon boyutlama
- Maximum Drawdown limiti
- Korelasyon filtresi (aynı sektörden fazla almama)
- Rejime göre risk ayarı
"""

import numpy as np
import pandas as pd
from datetime import datetime


class RiskYoneticisi:
    """Kurumsal seviye risk yönetimi."""

    def __init__(self, sermaye=100_000, max_risk_pct=2.0, max_pozisyon=5):
        self.sermaye = sermaye
        self.max_risk_pct = max_risk_pct          # işlem başına max risk %
        self.max_pozisyon = max_pozisyon            # aynı anda max pozisyon
        self.max_sektor_agirlik = 0.40              # bir sektöre max %40
        self.max_drawdown_limit = 10.0              # %10 DD'de dur
        self.aktif_pozisyonlar = []
        self.trade_gecmisi = []
        self.baslangic_sermaye = sermaye
        self.peak_sermaye = sermaye

    # ──────────────────────────────────────────────────────────
    # ATR BAZLI DİNAMİK STOP-LOSS
    # ──────────────────────────────────────────────────────────

    def dinamik_stop_hesapla(self, fiyat, atr, rejim="normal"):
        """
        ATR bazlı stop-loss — piyasa volatilitesine göre ayarlanır.
        Bull: 2x ATR (geniş), Bear: 1.2x ATR (sıkı), Normal: 1.5x ATR
        """
        carpanlar = {
            "bull": 2.5,
            "sideways": 1.8,
            "bear": 1.2,
            "normal": 1.5,
        }
        carpan = carpanlar.get(rejim, 1.5)
        stop_mesafe = atr * carpan
        stop_fiyat = fiyat - stop_mesafe

        # Trailing stop başlangıç seviyesi (1.5x ATR kâr'da aktif)
        trailing_baslangic = fiyat + atr * 1.5

        # Take-profit (3x ATR — 1:2 risk/ödül minimum)
        take_profit = fiyat + stop_mesafe * 2.5

        return {
            "stop_loss": round(stop_fiyat, 4),
            "stop_pct": round(stop_mesafe / fiyat * 100, 2),
            "trailing_baslangic": round(trailing_baslangic, 4),
            "take_profit": round(take_profit, 4),
            "risk_odul": round(2.5, 1),
            "atr_carpan": carpan,
            "rejim": rejim,
        }

    # ──────────────────────────────────────────────────────────
    # KELLY CRITERION POZİSYON BOYUTLAMA
    # ──────────────────────────────────────────────────────────

    def kelly_pozisyon_hesapla(self, ml_olasilik, risk_odul=2.5):
        """
        Kelly Criterion — optimal pozisyon boyutu.
        Yarım Kelly kullanılır (daha güvenli).

        f = (bp - q) / b
        b = risk/ödül oranı
        p = kazanma olasılığı (ML tahmini)
        q = kaybetme olasılığı (1 - p)
        """
        p = min(0.75, max(0.3, ml_olasilik))  # %30-75 arasında sınırla
        q = 1 - p
        b = risk_odul

        kelly_full = (b * p - q) / b
        kelly_half = kelly_full / 2  # yarım Kelly — daha güvenli

        # Sınırla: max %15 sermaye, min %2
        kelly_capped = max(0.02, min(0.15, kelly_half))

        lot_degeri = self.sermaye * kelly_capped
        max_risk_tl = self.sermaye * (self.max_risk_pct / 100)

        return {
            "kelly_full": round(kelly_full * 100, 2),
            "kelly_half": round(kelly_half * 100, 2),
            "pozisyon_pct": round(kelly_capped * 100, 2),
            "pozisyon_tl": round(lot_degeri, 0),
            "max_risk_tl": round(max_risk_tl, 0),
            "ml_olasilik": round(p, 3),
        }

    # ──────────────────────────────────────────────────────────
    # DRAWDOWN TAKİP
    # ──────────────────────────────────────────────────────────

    def drawdown_kontrol(self):
        """Mevcut drawdown'u kontrol eder, limit aşılırsa uyar."""
        self.peak_sermaye = max(self.peak_sermaye, self.sermaye)
        drawdown = (self.peak_sermaye - self.sermaye) / self.peak_sermaye * 100

        durum = "normal"
        if drawdown >= self.max_drawdown_limit:
            durum = "DURDUR"
        elif drawdown >= self.max_drawdown_limit * 0.7:
            durum = "DİKKAT"
        elif drawdown >= self.max_drawdown_limit * 0.5:
            durum = "UYARI"

        return {
            "drawdown_pct": round(drawdown, 2),
            "peak": round(self.peak_sermaye, 0),
            "mevcut": round(self.sermaye, 0),
            "limit": self.max_drawdown_limit,
            "durum": durum,
            "kalan_risk": round(self.max_drawdown_limit - drawdown, 2),
        }

    # ──────────────────────────────────────────────────────────
    # KORELASYON FİLTRESİ
    # ──────────────────────────────────────────────────────────

    SEKTOR_MAP = {
        "GARAN": "banka", "AKBNK": "banka", "ISCTR": "banka",
        "YKBNK": "banka", "HALKB": "banka", "VAKBN": "banka",
        "SAHOL": "holding", "KCHOL": "holding", "KOZAL": "holding",
        "EREGL": "sanayi", "TOASO": "sanayi", "TUPRS": "sanayi",
        "SISE": "sanayi", "ASELS": "teknoloji", "THYAO": "havayolu",
        "PGSUS": "havayolu", "BIMAS": "perakende", "MGROS": "perakende",
        "SOKM": "perakende", "AKSEN": "enerji", "ODAS": "enerji",
        "LOGO": "teknoloji", "NETAS": "teknoloji",
    }

    def korelasyon_kontrol(self, yeni_ticker):
        """Aynı sektörden fazla pozisyon almayı önler."""
        ticker_temiz = yeni_ticker.replace(".IS", "")
        yeni_sektor = self.SEKTOR_MAP.get(ticker_temiz, "diger")

        sektor_sayac = {}
        for poz in self.aktif_pozisyonlar:
            t = poz["ticker"].replace(".IS", "")
            s = self.SEKTOR_MAP.get(t, "diger")
            sektor_sayac[s] = sektor_sayac.get(s, 0) + 1

        mevcut_sayi = sektor_sayac.get(yeni_sektor, 0)
        max_ayni_sektor = max(1, int(self.max_pozisyon * self.max_sektor_agirlik))

        izin = mevcut_sayi < max_ayni_sektor

        return {
            "izin": izin,
            "sektor": yeni_sektor,
            "mevcut_sektor_sayisi": mevcut_sayi,
            "max_ayni_sektor": max_ayni_sektor,
            "toplam_pozisyon": len(self.aktif_pozisyonlar),
            "max_pozisyon": self.max_pozisyon,
        }

    # ──────────────────────────────────────────────────────────
    # REJİME GÖRE RİSK AYARI
    # ──────────────────────────────────────────────────────────

    def rejim_risk_ayari(self, rejim_info):
        """Piyasa rejimine göre risk parametrelerini ayarlar."""
        rejim = rejim_info.get("rejim", "sideways") if rejim_info else "sideways"

        ayarlar = {
            "bull": {
                "max_risk_pct": 2.5,
                "max_pozisyon": 6,
                "min_ml_esik": 0.50,
                "min_teknik_esik": 55,
                "aciklama": "Agresif — trend arkadaşın",
            },
            "sideways": {
                "max_risk_pct": 1.5,
                "max_pozisyon": 4,
                "min_ml_esik": 0.60,
                "min_teknik_esik": 65,
                "aciklama": "Temkinli — kaliteli fırsatları bekle",
            },
            "bear": {
                "max_risk_pct": 1.0,
                "max_pozisyon": 2,
                "min_ml_esik": 0.70,
                "min_teknik_esik": 75,
                "aciklama": "Defansif — sadece çok güçlü sinyaller",
            },
        }

        ayar = ayarlar.get(rejim, ayarlar["sideways"])
        self.max_risk_pct = ayar["max_risk_pct"]
        self.max_pozisyon = ayar["max_pozisyon"]

        return {
            "rejim": rejim,
            **ayar,
        }

    # ──────────────────────────────────────────────────────────
    # TAM SİNYAL DEĞERLENDİRME
    # ──────────────────────────────────────────────────────────

    def sinyal_degerlendir(self, ticker, fiyat, atr, ml_olasilik,
                           teknik_skor, rejim_info=None):
        """
        Bir sinyal geldiğinde tam risk değerlendirmesi yapar.
        Returns: {"islem": True/False, ...detaylar}
        """
        # 1. Drawdown kontrolü
        dd = self.drawdown_kontrol()
        if dd["durum"] == "DURDUR":
            return {"islem": False, "sebep": f"Drawdown limiti aşıldı: %{dd['drawdown_pct']}", **dd}

        # 2. Max pozisyon kontrolü
        if len(self.aktif_pozisyonlar) >= self.max_pozisyon:
            return {"islem": False, "sebep": f"Max pozisyon ({self.max_pozisyon}) dolu"}

        # 3. Rejim ayarla
        rejim_ayar = self.rejim_risk_ayari(rejim_info)

        # 4. ML eşik kontrolü
        if ml_olasilik and ml_olasilik < rejim_ayar["min_ml_esik"]:
            return {
                "islem": False,
                "sebep": f"ML olasılığı düşük: {ml_olasilik:.2f} < {rejim_ayar['min_ml_esik']}",
            }

        # 5. Teknik skor kontrolü
        if teknik_skor < rejim_ayar["min_teknik_esik"]:
            return {
                "islem": False,
                "sebep": f"Teknik skor düşük: {teknik_skor} < {rejim_ayar['min_teknik_esik']}",
            }

        # 6. Korelasyon kontrolü
        kor = self.korelasyon_kontrol(ticker)
        if not kor["izin"]:
            return {
                "islem": False,
                "sebep": f"Sektör limiti ({kor['sektor']}): {kor['mevcut_sektor_sayisi']}/{kor['max_ayni_sektor']}",
            }

        # 7. Stop-loss hesapla
        rejim = rejim_info.get("rejim", "normal") if rejim_info else "normal"
        stop = self.dinamik_stop_hesapla(fiyat, atr, rejim)

        # 8. Pozisyon boyutu (Kelly)
        kelly = self.kelly_pozisyon_hesapla(
            ml_olasilik or 0.5,
            stop.get("risk_odul", 2.5)
        )

        # 9. Lot hesapla
        lot = int(kelly["pozisyon_tl"] / fiyat)

        return {
            "islem": True,
            "ticker": ticker,
            "fiyat": fiyat,
            "lot": lot,
            "pozisyon_tl": round(lot * fiyat, 0),
            "stop_loss": stop["stop_loss"],
            "stop_pct": stop["stop_pct"],
            "take_profit": stop["take_profit"],
            "risk_odul": stop["risk_odul"],
            "kelly": kelly,
            "rejim": rejim_ayar,
            "korelasyon": kor,
            "drawdown": dd,
            "zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    # ──────────────────────────────────────────────────────────
    # POZİSYON YÖNETİMİ
    # ──────────────────────────────────────────────────────────

    def pozisyon_ac(self, sinyal):
        """Onaylanan sinyali aktif pozisyona ekler."""
        if not sinyal.get("islem"):
            return False

        self.aktif_pozisyonlar.append({
            "ticker": sinyal["ticker"],
            "giris_fiyat": sinyal["fiyat"],
            "lot": sinyal["lot"],
            "stop_loss": sinyal["stop_loss"],
            "take_profit": sinyal["take_profit"],
            "giris_zaman": sinyal["zaman"],
            "trailing_aktif": False,
            "trailing_stop": None,
        })
        return True

    def pozisyon_guncelle(self, ticker, mevcut_fiyat, mevcut_atr):
        """Trailing stop güncelle, çıkış kontrolü yap."""
        for poz in self.aktif_pozisyonlar:
            if poz["ticker"] != ticker:
                continue

            # Stop-loss tetiklendi mi?
            if mevcut_fiyat <= poz["stop_loss"]:
                return self._pozisyon_kapat(poz, mevcut_fiyat, "STOP_LOSS")

            # Take-profit tetiklendi mi?
            if mevcut_fiyat >= poz["take_profit"]:
                return self._pozisyon_kapat(poz, mevcut_fiyat, "TAKE_PROFIT")

            # Trailing stop güncelle
            kar_pct = (mevcut_fiyat - poz["giris_fiyat"]) / poz["giris_fiyat"]
            if kar_pct >= 0.015:  # %1.5 kârda trailing aktif
                poz["trailing_aktif"] = True
                yeni_trailing = mevcut_fiyat - mevcut_atr * 1.5
                if poz["trailing_stop"] is None or yeni_trailing > poz["trailing_stop"]:
                    poz["trailing_stop"] = round(yeni_trailing, 4)

            # Trailing stop tetiklendi mi?
            if poz["trailing_aktif"] and poz["trailing_stop"]:
                if mevcut_fiyat <= poz["trailing_stop"]:
                    return self._pozisyon_kapat(poz, mevcut_fiyat, "TRAILING_STOP")

        return None

    def _pozisyon_kapat(self, poz, cikis_fiyat, sebep):
        """Pozisyonu kapatır ve sonucu kaydeder."""
        kar_zarar_pct = (cikis_fiyat - poz["giris_fiyat"]) / poz["giris_fiyat"] * 100
        kar_zarar_tl = (cikis_fiyat - poz["giris_fiyat"]) * poz["lot"]

        sonuc = {
            "ticker": poz["ticker"],
            "giris": poz["giris_fiyat"],
            "cikis": cikis_fiyat,
            "lot": poz["lot"],
            "kar_zarar_pct": round(kar_zarar_pct, 2),
            "kar_zarar_tl": round(kar_zarar_tl, 2),
            "sebep": sebep,
            "giris_zaman": poz["giris_zaman"],
            "cikis_zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        self.trade_gecmisi.append(sonuc)
        self.sermaye += kar_zarar_tl
        self.aktif_pozisyonlar.remove(poz)

        return sonuc

    # ──────────────────────────────────────────────────────────
    # PERFORMANS RAPORU
    # ──────────────────────────────────────────────────────────

    def performans_raporu(self):
        """Trade geçmişinden performans raporu."""
        if not self.trade_gecmisi:
            return {"mesaj": "Henüz trade yok"}

        kazanc = [t for t in self.trade_gecmisi if t["kar_zarar_tl"] > 0]
        kayip = [t for t in self.trade_gecmisi if t["kar_zarar_tl"] <= 0]

        toplam_kar = sum(t["kar_zarar_tl"] for t in self.trade_gecmisi)
        ort_kazanc = np.mean([t["kar_zarar_pct"] for t in kazanc]) if kazanc else 0
        ort_kayip = np.mean([t["kar_zarar_pct"] for t in kayip]) if kayip else 0

        return {
            "toplam_trade": len(self.trade_gecmisi),
            "kazanan": len(kazanc),
            "kaybeden": len(kayip),
            "win_rate": round(len(kazanc) / len(self.trade_gecmisi) * 100, 1),
            "toplam_kar_tl": round(toplam_kar, 2),
            "toplam_kar_pct": round(toplam_kar / self.baslangic_sermaye * 100, 2),
            "ort_kazanc_pct": round(ort_kazanc, 2),
            "ort_kayip_pct": round(ort_kayip, 2),
            "profit_factor": round(
                abs(sum(t["kar_zarar_tl"] for t in kazanc)) /
                abs(sum(t["kar_zarar_tl"] for t in kayip))
                if kayip and sum(t["kar_zarar_tl"] for t in kayip) != 0 else 0, 2
            ),
            "mevcut_sermaye": round(self.sermaye, 0),
            "peak_sermaye": round(self.peak_sermaye, 0),
            "mevcut_dd": self.drawdown_kontrol(),
        }
