"""
ANKA PAPER TRADER — Gerçekçi Simülasyon Motoru
================================================
Gerçek piyasa koşullarını simüle eder:
- Slippage (kayma): hacme ve volatiliteye göre dinamik
- Likidite filtresi: günlük hacmin %1'inden fazla pozisyon açmaz
- Gecikme simülasyonu: sinyal-emir arası 5-15 sn, fiyat hareket eder
- Kısmi dolum: her emir %100 dolmayabilir
- Komisyon: %0.40 round-trip (Midas/Tacirler/Gedik seviyesi)
- Market impact: emirlerimiz fiyatı hareket ettirebilir

"Pessimist" modda gerçek piyasadan bile kötü koşullar yaratır.
Bu modda kâr ediyorsa, gerçekte daha iyi performans bekleriz.

Arayüz: Tek modül, iki mod — PAPER (simülasyon) ve LIVE (canlı).
Live mod geldiğinde aynı arayüz aracı kurum API'sine bağlanır.

Tarih: 16 Nisan 2026
"""

import json
import os
import random
import time
import logging
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple
from enum import Enum

# Proje dizinleri
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = PROJECT_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Logger
logger = logging.getLogger("PaperTrader")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOGS_DIR / "paper_trader.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(sh)


# ================================================================
# ENUMS & CONFIG
# ================================================================
class TradeMode(Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderSide(Enum):
    BUY = "AL"
    SELL = "SAT"


class OrderStatus(Enum):
    PENDING = "bekliyor"
    PARTIAL = "kismi_doldu"
    FILLED = "doldu"
    REJECTED = "reddedildi"
    CANCELLED = "iptal"


class ExitReason(Enum):
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TAKE_PROFIT = "take_profit"
    MANUAL = "manuel"
    KILL_SWITCH = "kill_switch"
    END_OF_DAY = "gun_sonu"


# ================================================================
# PIYASA SÜRTÜNME MODELİ
# ================================================================
class MarketFriction:
    """
    Gerçek piyasa sürtünmelerini modeller.
    Pessimist mod: gerçekten daha kötü koşullar yaratır.
    """

    def __init__(self, pessimist=True):
        self.pessimist = pessimist
        # Komisyon oranları
        self.komisyon_oran = 0.0015       # %0.15 tek yön
        self.toplam_komisyon = 0.0040     # %0.40 round-trip (alış+satış+slippage)

    def slippage_hesapla(self, fiyat: float, lot: int, gunluk_hacim: int,
                          atr: float, yon: OrderSide) -> float:
        """
        Dinamik slippage modeli.

        Faktörler:
        1. Hacim etkisi: düşük hacimde daha çok kayma
        2. Volatilite etkisi: yüksek ATR = daha çok kayma
        3. Emir büyüklüğü: büyük emirlerde daha çok kayma
        4. Rastgelelik: gerçek piyasadaki belirsizlik

        Returns: slippage TL (her zaman pozitif = maliyet)
        """
        if gunluk_hacim <= 0:
            gunluk_hacim = 1_000_000  # varsayılan

        # 1. Hacim etkisi: emirimiz hacmin yüzde kaçı
        hacim_orani = (lot * fiyat) / (gunluk_hacim * fiyat / 100)  # kabaca
        hacim_etkisi = min(0.005, hacim_orani * 0.01)  # max %0.5

        # 2. Volatilite etkisi: ATR'nin fiyata oranı
        if atr > 0:
            vol_orani = atr / fiyat
            vol_etkisi = vol_orani * 0.05  # ATR'nin %5'i kadar kayma
        else:
            vol_etkisi = 0.001

        # 3. Baz slippage
        baz_slip = 0.0005  # %0.05 minimum

        # 4. Rastgelelik (normal dağılım, pozitif bias)
        rastgele = abs(random.gauss(0, 0.0003))

        # Toplam slippage oranı
        toplam_slip_oran = baz_slip + hacim_etkisi + vol_etkisi + rastgele

        if self.pessimist:
            toplam_slip_oran *= 1.5  # %50 daha kötü

        # TL karşılığı
        slip_tl = fiyat * toplam_slip_oran

        # Yön: alışta daha yüksek fiyat, satışta daha düşük
        if yon == OrderSide.BUY:
            return abs(slip_tl)
        else:
            return -abs(slip_tl)

    def gecikme_simule(self) -> Tuple[float, float]:
        """
        Sinyal-emir arası gecikme simülasyonu.

        Returns: (gecikme_sn, fiyat_degisim_orani)
        Gecikme süresinde fiyat rastgele hareket eder.
        """
        # 5-15 saniye arası gecikme (ağ, işleme, kuyruk)
        gecikme_sn = random.uniform(3, 12)
        if self.pessimist:
            gecikme_sn = random.uniform(5, 20)

        # Gecikme süresince fiyat hareketi (rastgele yürüyüş)
        # Saniyede ~%0.01 hareket varsayımı (volatil piyasa)
        adim_sayisi = int(gecikme_sn)
        hareket = sum(random.gauss(0, 0.0001) for _ in range(adim_sayisi))

        return gecikme_sn, hareket

    def kismi_dolum_hesapla(self, lot: int, gunluk_hacim: int) -> int:
        """
        Kısmi dolum simülasyonu.
        Büyük emirler %100 dolmayabilir.

        Returns: gerçekleşen lot sayısı
        """
        if gunluk_hacim <= 0:
            gunluk_hacim = 1_000_000

        # Emir hacim oranı
        oran = lot / max(1, gunluk_hacim * 0.001)  # dakika hacmine oranla

        if oran < 0.1:
            # Küçük emir: %100 dolum
            dolum_orani = 1.0
        elif oran < 0.5:
            # Orta emir: %85-100 dolum
            dolum_orani = random.uniform(0.85, 1.0)
        else:
            # Büyük emir: %60-90 dolum
            dolum_orani = random.uniform(0.60, 0.90)

        if self.pessimist:
            dolum_orani *= 0.90  # %10 daha kötü

        gerceklesen = max(1, int(lot * dolum_orani))
        return min(gerceklesen, lot)

    def market_impact_hesapla(self, fiyat: float, lot: int,
                               gunluk_hacim: int) -> float:
        """
        Market impact: emirlerimizin piyasayı hareket ettirmesi.
        Kyle'ın lambda modeli basitleştirilmiş hali.

        Returns: fiyat değişimi (TL)
        """
        if gunluk_hacim <= 0:
            return 0

        # Kyle lambda: impact ∝ sqrt(emir/hacim)
        oran = (lot * fiyat) / (gunluk_hacim * fiyat)
        impact = np.sqrt(oran) * fiyat * 0.001  # çok küçük etki

        if self.pessimist:
            impact *= 2.0

        return impact

    def komisyon_hesapla(self, tutar: float) -> float:
        """Komisyon hesapla (tek yön)."""
        return tutar * self.komisyon_oran


# ================================================================
# PAPER TRADE KAYITLARI
# ================================================================
@dataclass
class Order:
    """Emir kaydı."""
    id: str = ""
    ticker: str = ""
    side: str = "AL"
    talep_lot: int = 0
    gerceklesen_lot: int = 0
    talep_fiyat: float = 0.0
    gerceklesen_fiyat: float = 0.0
    slippage_tl: float = 0.0
    komisyon_tl: float = 0.0
    gecikme_sn: float = 0.0
    market_impact_tl: float = 0.0
    status: str = "bekliyor"
    zaman: str = ""
    notlar: str = ""


@dataclass
class Position:
    """Açık pozisyon."""
    ticker: str = ""
    lot: int = 0
    giris_fiyat: float = 0.0
    giris_zaman: str = ""
    stop_loss: float = 0.0
    trailing_stop: Optional[float] = None
    trailing_aktif: bool = False
    take_profit: float = 0.0
    toplam_komisyon: float = 0.0
    toplam_slippage: float = 0.0
    peak_fiyat: float = 0.0
    sektor: str = "diger"


@dataclass
class ClosedTrade:
    """Kapanmış trade."""
    ticker: str = ""
    lot: int = 0
    giris_fiyat: float = 0.0
    cikis_fiyat: float = 0.0
    giris_zaman: str = ""
    cikis_zaman: str = ""
    brut_kar_tl: float = 0.0
    komisyon_tl: float = 0.0
    slippage_tl: float = 0.0
    net_kar_tl: float = 0.0
    net_kar_pct: float = 0.0
    cikis_sebep: str = ""
    sure_dk: int = 0


# ================================================================
# ANA PAPER TRADER
# ================================================================
class PaperTrader:
    """
    Gerçekçi Paper Trading motoru.

    Kullanım:
        trader = PaperTrader(sermaye=100_000, pessimist=True)

        # Alış
        sonuc = trader.emir_gonder("GARAN", OrderSide.BUY, lot=200,
                                    fiyat=120.5, atr=3.2, hacim=5_000_000)

        # Pozisyon güncelle (her dakika)
        trader.pozisyonlari_guncelle(fiyat_dict={"GARAN": 122.0}, atr_dict={"GARAN": 3.1})

        # Satış
        sonuc = trader.emir_gonder("GARAN", OrderSide.SELL, lot=200, fiyat=125.0)

        # Rapor
        rapor = trader.performans_raporu()
    """

    def __init__(self, sermaye: float = 100_000, mode: TradeMode = TradeMode.PAPER,
                 pessimist: bool = True, kayit_dosya: str = "paper_trades.json"):
        self.sermaye = sermaye
        self.baslangic_sermaye = sermaye
        self.peak_sermaye = sermaye
        self.mode = mode
        self.pessimist = pessimist

        # Sürtünme modeli
        self.friction = MarketFriction(pessimist=pessimist)

        # Portföy
        self.pozisyonlar: Dict[str, Position] = {}
        self.kapanis_gecmisi: List[ClosedTrade] = []
        self.emir_gecmisi: List[Order] = []
        self.gunluk_emir_sayisi = 0
        self.gunluk_kz = 0.0
        self.son_trade_gunu = str(date.today())

        # Panel kuralları entegrasyonu
        self.max_gunluk_kayip_pct = 3.0
        self.max_tek_emir_tl = 30_000
        self.max_gunluk_emir = 50
        self.max_pozisyon = 5
        self.max_ayni_sektor = 2

        # Dosya kayıt
        self.kayit_dosya = DATA_DIR / kayit_dosya
        self._kayit_yukle()

        logger.info(f"PaperTrader başlatıldı | Mod: {mode.value} | Sermaye: {sermaye:,.0f} TL | Pessimist: {pessimist}")

    # ──────────────────────────────────────────────────────────
    # EMİR GÖNDERME
    # ──────────────────────────────────────────────────────────

    def emir_gonder(self, ticker: str, side: OrderSide, lot: int, fiyat: float,
                     atr: float = 0, hacim: int = 0, stop_loss: float = 0,
                     take_profit: float = 0) -> Order:
        """
        Emir gönder — tüm sürtünmeler dahil.

        Paper modda: simüle eder
        Live modda: aracı kurum API'sine gönderir (henüz yok)
        """
        # Gün kontrolü
        self._gun_kontrolu()

        # Emir ID
        emir = Order(
            id=f"PT-{datetime.now().strftime('%H%M%S')}-{random.randint(100,999)}",
            ticker=ticker,
            side=side.value,
            talep_lot=lot,
            talep_fiyat=fiyat,
            zaman=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # ── PRE-TRADE KONTROLLER ──

        # 1. Kill-switch
        if self._kill_switch_kontrol() is False:
            emir.status = OrderStatus.REJECTED.value
            emir.notlar = "KILL-SWITCH aktif"
            self.emir_gecmisi.append(emir)
            logger.warning(f"EMİR REDDEDİLDİ: {ticker} {side.value} — Kill-switch aktif")
            return emir

        # 2. Günlük emir sayısı
        if self.gunluk_emir_sayisi >= self.max_gunluk_emir:
            emir.status = OrderStatus.REJECTED.value
            emir.notlar = f"Günlük emir limiti aşıldı ({self.max_gunluk_emir})"
            self.emir_gecmisi.append(emir)
            logger.warning(f"EMİR REDDEDİLDİ: {ticker} — günlük emir limiti")
            return emir

        # 3. Fat-finger kontrolü
        tutar = lot * fiyat
        if tutar > self.max_tek_emir_tl:
            emir.status = OrderStatus.REJECTED.value
            emir.notlar = f"Fat-finger: {tutar:,.0f} TL > {self.max_tek_emir_tl:,.0f} TL"
            self.emir_gecmisi.append(emir)
            logger.warning(f"EMİR REDDEDİLDİ: {ticker} — fat-finger {tutar:,.0f} TL")
            return emir

        # 4. Yeterli bakiye (alışta)
        if side == OrderSide.BUY and tutar > self.sermaye * 0.95:
            emir.status = OrderStatus.REJECTED.value
            emir.notlar = f"Yetersiz bakiye: {tutar:,.0f} > {self.sermaye:,.0f}"
            self.emir_gecmisi.append(emir)
            logger.warning(f"EMİR REDDEDİLDİ: {ticker} — yetersiz bakiye")
            return emir

        # 5. Max pozisyon kontrolü (alışta)
        if side == OrderSide.BUY and len(self.pozisyonlar) >= self.max_pozisyon:
            emir.status = OrderStatus.REJECTED.value
            emir.notlar = f"Max pozisyon limiti ({self.max_pozisyon})"
            self.emir_gecmisi.append(emir)
            logger.warning(f"EMİR REDDEDİLDİ: {ticker} — max pozisyon dolu")
            return emir

        # 6. Sektör kontrolü (alışta)
        if side == OrderSide.BUY:
            sektor_ok = self._sektor_kontrol(ticker)
            if not sektor_ok:
                emir.status = OrderStatus.REJECTED.value
                emir.notlar = "Sektör limiti aşıldı"
                self.emir_gecmisi.append(emir)
                logger.warning(f"EMİR REDDEDİLDİ: {ticker} — sektör limiti")
                return emir

        # ── SÜRTÜNME HESAPLAMALARI ──

        # 1. Gecikme simülasyonu
        gecikme_sn, fiyat_kayma = self.friction.gecikme_simule()
        emir.gecikme_sn = round(gecikme_sn, 1)

        # 2. Gecikme sonrası fiyat
        fiyat_gecikme_sonrasi = fiyat * (1 + fiyat_kayma)

        # 3. Slippage
        slip = self.friction.slippage_hesapla(fiyat_gecikme_sonrasi, lot, hacim, atr, side)
        emir.slippage_tl = round(abs(slip) * lot, 2)

        # 4. Market impact
        impact = self.friction.market_impact_hesapla(fiyat, lot, hacim)
        emir.market_impact_tl = round(impact * lot, 2)

        # 5. Kısmi dolum
        gerceklesen_lot = self.friction.kismi_dolum_hesapla(lot, hacim)
        emir.gerceklesen_lot = gerceklesen_lot

        # 6. Gerçekleşen fiyat
        if side == OrderSide.BUY:
            gercek_fiyat = fiyat_gecikme_sonrasi + abs(slip) + impact
        else:
            gercek_fiyat = fiyat_gecikme_sonrasi - abs(slip) - impact

        gercek_fiyat = round(max(0.01, gercek_fiyat), 4)
        emir.gerceklesen_fiyat = gercek_fiyat

        # 7. Komisyon
        gercek_tutar = gerceklesen_lot * gercek_fiyat
        komisyon = self.friction.komisyon_hesapla(gercek_tutar)
        emir.komisyon_tl = round(komisyon, 2)

        # ── POZİSYON GÜNCELLE ──

        if side == OrderSide.BUY:
            self._pozisyon_ac(ticker, gerceklesen_lot, gercek_fiyat,
                              komisyon, abs(slip) * gerceklesen_lot,
                              stop_loss, take_profit)
            self.sermaye -= (gercek_tutar + komisyon)
            emir.status = OrderStatus.FILLED.value if gerceklesen_lot == lot else OrderStatus.PARTIAL.value

        elif side == OrderSide.SELL:
            kz = self._pozisyon_kapat(ticker, gerceklesen_lot, gercek_fiyat,
                                       komisyon, abs(slip) * gerceklesen_lot)
            self.sermaye += (gercek_tutar - komisyon)
            self.gunluk_kz += kz
            emir.status = OrderStatus.FILLED.value

        # Kayıt
        self.gunluk_emir_sayisi += 1
        self.emir_gecmisi.append(emir)
        self._kayit_yaz()

        logger.info(
            f"{'📈' if side == OrderSide.BUY else '📉'} {side.value} {ticker} | "
            f"Talep: {lot}@{fiyat:.2f} → Gerçekleşen: {gerceklesen_lot}@{gercek_fiyat:.2f} | "
            f"Slip: {emir.slippage_tl:.2f} | Kom: {emir.komisyon_tl:.2f} | "
            f"Gecikme: {gecikme_sn:.1f}sn | Durum: {emir.status}"
        )

        return emir

    # ──────────────────────────────────────────────────────────
    # POZİSYON YÖNETİMİ
    # ──────────────────────────────────────────────────────────

    def _pozisyon_ac(self, ticker, lot, fiyat, komisyon, slippage,
                      stop_loss=0, take_profit=0):
        """Yeni pozisyon aç veya mevcut pozisyona ekle."""
        sektor = self._ticker_sektor(ticker)

        if ticker in self.pozisyonlar:
            poz = self.pozisyonlar[ticker]
            toplam_lot = poz.lot + lot
            poz.giris_fiyat = (poz.giris_fiyat * poz.lot + fiyat * lot) / toplam_lot
            poz.lot = toplam_lot
            poz.toplam_komisyon += komisyon
            poz.toplam_slippage += slippage
        else:
            self.pozisyonlar[ticker] = Position(
                ticker=ticker,
                lot=lot,
                giris_fiyat=fiyat,
                giris_zaman=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                stop_loss=stop_loss,
                take_profit=take_profit,
                toplam_komisyon=komisyon,
                toplam_slippage=slippage,
                peak_fiyat=fiyat,
                sektor=sektor,
            )

    def _pozisyon_kapat(self, ticker, lot, cikis_fiyat, komisyon, slippage,
                         sebep: str = "MANUAL") -> float:
        """Pozisyonu kapat ve trade kaydı oluştur."""
        if ticker not in self.pozisyonlar:
            logger.warning(f"Pozisyon bulunamadı: {ticker}")
            return 0

        poz = self.pozisyonlar[ticker]
        giris_tutar = poz.giris_fiyat * lot
        cikis_tutar = cikis_fiyat * lot
        brut_kar = cikis_tutar - giris_tutar
        toplam_maliyet = poz.toplam_komisyon + komisyon + poz.toplam_slippage + slippage
        net_kar = brut_kar - toplam_maliyet

        giris_zaman = datetime.strptime(poz.giris_zaman, "%Y-%m-%d %H:%M:%S")
        sure_dk = int((datetime.now() - giris_zaman).total_seconds() / 60)

        trade = ClosedTrade(
            ticker=ticker,
            lot=lot,
            giris_fiyat=poz.giris_fiyat,
            cikis_fiyat=cikis_fiyat,
            giris_zaman=poz.giris_zaman,
            cikis_zaman=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            brut_kar_tl=round(brut_kar, 2),
            komisyon_tl=round(poz.toplam_komisyon + komisyon, 2),
            slippage_tl=round(poz.toplam_slippage + slippage, 2),
            net_kar_tl=round(net_kar, 2),
            net_kar_pct=round(net_kar / giris_tutar * 100, 2) if giris_tutar > 0 else 0,
            cikis_sebep=sebep,
            sure_dk=sure_dk,
        )

        self.kapanis_gecmisi.append(trade)

        # Pozisyon kaldır veya lot azalt
        if lot >= poz.lot:
            del self.pozisyonlar[ticker]
        else:
            poz.lot -= lot

        self.peak_sermaye = max(self.peak_sermaye, self.sermaye)

        logger.info(
            f"{'✅' if net_kar > 0 else '❌'} KAPANIŞ {ticker} | "
            f"Giriş: {poz.giris_fiyat:.2f} → Çıkış: {cikis_fiyat:.2f} | "
            f"Net: {net_kar:+,.2f} TL ({trade.net_kar_pct:+.2f}%) | "
            f"Sebep: {sebep} | Süre: {sure_dk}dk"
        )

        return net_kar

    def pozisyonlari_guncelle(self, fiyat_dict: Dict[str, float],
                                atr_dict: Optional[Dict[str, float]] = None):
        """
        Tüm açık pozisyonları güncelle.
        Stop-loss, trailing stop, take-profit kontrolleri.
        Her dakika çağrılmalı.
        """
        kapatilacak = []

        for ticker, poz in self.pozisyonlar.items():
            fiyat = fiyat_dict.get(ticker)
            if fiyat is None:
                continue

            atr = atr_dict.get(ticker, 0) if atr_dict else 0

            # Peak fiyat güncelle
            poz.peak_fiyat = max(poz.peak_fiyat, fiyat)

            # Stop-loss kontrolü
            if poz.stop_loss > 0 and fiyat <= poz.stop_loss:
                kapatilacak.append((ticker, fiyat, ExitReason.STOP_LOSS.value))
                continue

            # Take-profit kontrolü
            if poz.take_profit > 0 and fiyat >= poz.take_profit:
                kapatilacak.append((ticker, fiyat, ExitReason.TAKE_PROFIT.value))
                continue

            # Trailing stop güncelleme
            kar_pct = (fiyat - poz.giris_fiyat) / poz.giris_fiyat
            if kar_pct >= 0.015:  # %1.5 kârda trailing aktif
                poz.trailing_aktif = True
                if atr > 0:
                    yeni_trail = fiyat - atr * 1.5
                else:
                    yeni_trail = fiyat * 0.985  # %1.5 altına düşerse

                if poz.trailing_stop is None or yeni_trail > poz.trailing_stop:
                    poz.trailing_stop = round(yeni_trail, 4)

            # Trailing stop tetikleme
            if poz.trailing_aktif and poz.trailing_stop:
                if fiyat <= poz.trailing_stop:
                    kapatilacak.append((ticker, fiyat, ExitReason.TRAILING_STOP.value))

        # Kapatmaları uygula
        for ticker, fiyat, sebep in kapatilacak:
            poz = self.pozisyonlar.get(ticker)
            if poz:
                # Satış sürtünmeleri de ekliyoruz
                slip = self.friction.slippage_hesapla(fiyat, poz.lot, 0, 0, OrderSide.SELL)
                komisyon = self.friction.komisyon_hesapla(poz.lot * fiyat)
                cikis_fiyat = fiyat - abs(slip)
                kz = self._pozisyon_kapat(ticker, poz.lot, cikis_fiyat, komisyon, abs(slip) * poz.lot, sebep)
                self.sermaye += poz.lot * cikis_fiyat - komisyon
                self.gunluk_kz += kz

    # ──────────────────────────────────────────────────────────
    # KONTROLLER
    # ──────────────────────────────────────────────────────────

    def _kill_switch_kontrol(self) -> bool:
        """Günlük kayıp limitini kontrol et."""
        if self.baslangic_sermaye > 0:
            kayip_pct = abs(self.gunluk_kz) / self.baslangic_sermaye * 100
            if self.gunluk_kz < 0 and kayip_pct > self.max_gunluk_kayip_pct:
                logger.critical(f"🚨 KILL-SWITCH: Günlük kayıp %{kayip_pct:.1f}")
                return False
        return True

    def _sektor_kontrol(self, ticker: str) -> bool:
        """Sektör dağılımı kontrolü."""
        sektor = self._ticker_sektor(ticker)
        sayac = sum(1 for p in self.pozisyonlar.values() if p.sektor == sektor)
        return sayac < self.max_ayni_sektor

    def _ticker_sektor(self, ticker: str) -> str:
        """Hisse sektörü."""
        # Panel kurallarından sektör haritası
        from anka_panel_kurallari import SektorFiltresi
        temiz = ticker.replace(".IS", "")
        return SektorFiltresi.SEKTOR_MAP.get(temiz, "diger")

    def _gun_kontrolu(self):
        """Yeni gün mü kontrol et, sıfırla."""
        bugun = str(date.today())
        if bugun != self.son_trade_gunu:
            self.gunluk_emir_sayisi = 0
            self.gunluk_kz = 0.0
            self.son_trade_gunu = bugun
            logger.info(f"📅 Yeni gün: {bugun}")

    # ──────────────────────────────────────────────────────────
    # PERFORMANS RAPORU
    # ──────────────────────────────────────────────────────────

    def performans_raporu(self) -> Dict:
        """Detaylı performans raporu."""
        if not self.kapanis_gecmisi:
            return {
                "mesaj": "Henüz kapanan trade yok",
                "sermaye": round(self.sermaye, 0),
                "aktif_pozisyon": len(self.pozisyonlar),
            }

        kazananlar = [t for t in self.kapanis_gecmisi if t.net_kar_tl > 0]
        kaybedenler = [t for t in self.kapanis_gecmisi if t.net_kar_tl <= 0]

        toplam_net = sum(t.net_kar_tl for t in self.kapanis_gecmisi)
        toplam_komisyon = sum(t.komisyon_tl for t in self.kapanis_gecmisi)
        toplam_slippage = sum(t.slippage_tl for t in self.kapanis_gecmisi)
        toplam_brut = sum(t.brut_kar_tl for t in self.kapanis_gecmisi)

        ort_kazanc = np.mean([t.net_kar_pct for t in kazananlar]) if kazananlar else 0
        ort_kayip = np.mean([t.net_kar_pct for t in kaybedenler]) if kaybedenler else 0
        ort_sure = np.mean([t.sure_dk for t in self.kapanis_gecmisi])

        # Drawdown
        equity_curve = [self.baslangic_sermaye]
        for t in self.kapanis_gecmisi:
            equity_curve.append(equity_curve[-1] + t.net_kar_tl)
        peak = np.maximum.accumulate(equity_curve)
        drawdowns = (np.array(equity_curve) - peak) / peak * 100
        max_dd = abs(min(drawdowns))

        # Profit factor
        brut_kar = sum(t.net_kar_tl for t in kazananlar) if kazananlar else 0
        brut_zarar = abs(sum(t.net_kar_tl for t in kaybedenler)) if kaybedenler else 1

        # Sharpe (basit)
        getiriler = [t.net_kar_pct for t in self.kapanis_gecmisi]
        sharpe = np.mean(getiriler) / np.std(getiriler) if len(getiriler) > 1 and np.std(getiriler) > 0 else 0

        # Çıkış sebepleri dağılımı
        cikis_dagilim = {}
        for t in self.kapanis_gecmisi:
            cikis_dagilim[t.cikis_sebep] = cikis_dagilim.get(t.cikis_sebep, 0) + 1

        rapor = {
            "mod": self.mode.value,
            "pessimist": self.pessimist,
            "sermaye_baslangic": round(self.baslangic_sermaye, 0),
            "sermaye_mevcut": round(self.sermaye, 0),
            "toplam_getiri_pct": round(toplam_net / self.baslangic_sermaye * 100, 2),
            "toplam_trade": len(self.kapanis_gecmisi),
            "kazanan": len(kazananlar),
            "kaybeden": len(kaybedenler),
            "win_rate": round(len(kazananlar) / len(self.kapanis_gecmisi) * 100, 1),
            "brut_kar_tl": round(toplam_brut, 2),
            "net_kar_tl": round(toplam_net, 2),
            "toplam_komisyon_tl": round(toplam_komisyon, 2),
            "toplam_slippage_tl": round(toplam_slippage, 2),
            "surtuname_maliyeti_tl": round(toplam_komisyon + toplam_slippage, 2),
            "surtuname_pct": round((toplam_komisyon + toplam_slippage) / max(1, abs(toplam_brut)) * 100, 1),
            "ort_kazanc_pct": round(ort_kazanc, 2),
            "ort_kayip_pct": round(ort_kayip, 2),
            "ort_sure_dk": round(ort_sure, 0),
            "profit_factor": round(brut_kar / max(0.01, brut_zarar), 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "aktif_pozisyon": len(self.pozisyonlar),
            "cikis_dagilim": cikis_dagilim,
            "rapor_zamani": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return rapor

    def portfoy_durumu(self) -> Dict:
        """Anlık portföy durumu."""
        pozlar = {}
        for ticker, poz in self.pozisyonlar.items():
            pozlar[ticker] = {
                "lot": poz.lot,
                "giris_fiyat": poz.giris_fiyat,
                "stop_loss": poz.stop_loss,
                "trailing_stop": poz.trailing_stop,
                "take_profit": poz.take_profit,
                "sektor": poz.sektor,
                "komisyon": poz.toplam_komisyon,
            }

        return {
            "sermaye": round(self.sermaye, 0),
            "pozisyon_sayisi": len(self.pozisyonlar),
            "pozisyonlar": pozlar,
            "gunluk_kz": round(self.gunluk_kz, 2),
            "gunluk_emir": self.gunluk_emir_sayisi,
            "kill_switch": not self._kill_switch_kontrol(),
        }

    # ──────────────────────────────────────────────────────────
    # KAYIT / YÜKLEME
    # ──────────────────────────────────────────────────────────

    def _kayit_yaz(self):
        """Durumu dosyaya yaz."""
        try:
            veri = {
                "sermaye": self.sermaye,
                "baslangic_sermaye": self.baslangic_sermaye,
                "peak_sermaye": self.peak_sermaye,
                "mode": self.mode.value,
                "son_trade_gunu": self.son_trade_gunu,
                "gunluk_emir_sayisi": self.gunluk_emir_sayisi,
                "gunluk_kz": self.gunluk_kz,
                "pozisyonlar": {k: asdict(v) for k, v in self.pozisyonlar.items()},
                "kapanis_gecmisi": [asdict(t) for t in self.kapanis_gecmisi[-500:]],
                "emir_gecmisi": [asdict(e) for e in self.emir_gecmisi[-500:]],
                "guncelleme": datetime.now().isoformat(),
            }
            tmp = self.kayit_dosya.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(veri, f, indent=2, ensure_ascii=False)
            tmp.replace(self.kayit_dosya)
        except Exception as e:
            logger.error(f"Kayıt yazma hatası: {e}")

    def _kayit_yukle(self):
        """Önceki durumu yükle."""
        if not self.kayit_dosya.exists():
            return
        try:
            with open(self.kayit_dosya, "r", encoding="utf-8") as f:
                veri = json.load(f)
            self.sermaye = veri.get("sermaye", self.sermaye)
            self.baslangic_sermaye = veri.get("baslangic_sermaye", self.baslangic_sermaye)
            self.peak_sermaye = veri.get("peak_sermaye", self.peak_sermaye)
            self.son_trade_gunu = veri.get("son_trade_gunu", str(date.today()))
            self.gunluk_emir_sayisi = veri.get("gunluk_emir_sayisi", 0)
            self.gunluk_kz = veri.get("gunluk_kz", 0)

            for k, v in veri.get("pozisyonlar", {}).items():
                self.pozisyonlar[k] = Position(**v)

            for t in veri.get("kapanis_gecmisi", []):
                self.kapanis_gecmisi.append(ClosedTrade(**t))

            for e in veri.get("emir_gecmisi", []):
                self.emir_gecmisi.append(Order(**e))

            logger.info(f"Kayıt yüklendi: {len(self.pozisyonlar)} pozisyon, {len(self.kapanis_gecmisi)} kapalı trade")
        except Exception as e:
            logger.error(f"Kayıt yükleme hatası: {e}")


# ================================================================
# TEST
# ================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("ANKA PAPER TRADER — Gerçekçi Simülasyon Testi")
    print("=" * 60)

    trader = PaperTrader(sermaye=100_000, pessimist=True)

    # Test 1: Alış emri
    print("\n--- TEST 1: GARAN Alış ---")
    emir = trader.emir_gonder(
        "GARAN", OrderSide.BUY, lot=200, fiyat=120.50,
        atr=3.2, hacim=5_000_000, stop_loss=115.0, take_profit=130.0
    )
    print(f"  Talep: 200@120.50 → Gerçekleşen: {emir.gerceklesen_lot}@{emir.gerceklesen_fiyat:.2f}")
    print(f"  Slippage: {emir.slippage_tl:.2f} TL | Komisyon: {emir.komisyon_tl:.2f} TL")
    print(f"  Gecikme: {emir.gecikme_sn:.1f} sn | Durum: {emir.status}")

    # Test 2: İkinci hisse
    print("\n--- TEST 2: THYAO Alış ---")
    emir2 = trader.emir_gonder(
        "THYAO", OrderSide.BUY, lot=300, fiyat=310.0,
        atr=8.5, hacim=3_000_000, stop_loss=295.0, take_profit=340.0
    )
    print(f"  Gerçekleşen: {emir2.gerceklesen_lot}@{emir2.gerceklesen_fiyat:.2f}")

    # Test 3: Pozisyon güncelleme (fiyat yükseldi)
    print("\n--- TEST 3: Fiyat güncelleme ---")
    trader.pozisyonlari_guncelle(
        fiyat_dict={"GARAN": 123.0, "THYAO": 315.0},
        atr_dict={"GARAN": 3.1, "THYAO": 8.2}
    )

    # Test 4: Portföy durumu
    print("\n--- TEST 4: Portföy durumu ---")
    durum = trader.portfoy_durumu()
    print(f"  Sermaye: {durum['sermaye']:,.0f} TL")
    print(f"  Pozisyon: {durum['pozisyon_sayisi']}")

    # Test 5: Satış
    print("\n--- TEST 5: GARAN Satış ---")
    emir3 = trader.emir_gonder(
        "GARAN", OrderSide.SELL, lot=200, fiyat=125.0, hacim=5_000_000
    )
    print(f"  Gerçekleşen: {emir3.gerceklesen_lot}@{emir3.gerceklesen_fiyat:.2f}")

    # Test 6: Rapor
    print("\n--- TEST 6: Performans Raporu ---")
    rapor = trader.performans_raporu()
    for k, v in rapor.items():
        print(f"  {k}: {v}")

    print("\n✅ Paper Trader testi tamamlandı!")
