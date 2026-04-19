"""
Grid Trading Backtest — 2 yıllık BTC + ETH saatlik veri.

Grid mantığı:
  - Aralık: [min, max]
  - N kademe, her kademeye eşit USDT yerleştir
  - Fiyat bir kademeyi aşağı geçerse (AL), bir kademeyi yukarı geçerse (SAT)
  - Her tamamlanan al-sat çifti kâr (% aralık/kademe - komisyon)

Parametreler grid sweep:
  - Aralık genişliği: fiyatın ±%X'i
  - Kademe sayısı: 10, 20, 40
  - Her kademe pozisyonu: eşit dağılım

Çıktı: data/grid_backtest_rapor.md
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "data" / "price_history_2yil.csv"
RAPOR = PROJECT_DIR / "data" / "grid_backtest_rapor.md"

BASLANGIC_SERMAYE = 2000.0  # USDT (her sembol için ayrı)
KOMISYON = 0.001  # %0.1 Binance spot (taker)
SLIPPAGE = 0.0005  # %0.05 (grid limit emir olduğu için düşük)


@dataclass
class GridLevel:
    fiyat: float
    coin_miktar: float = 0.0  # Bu seviyede ne kadar coin var
    usdt_ayrilmis: float = 0.0  # Bu seviyeye ayrılmış USDT (al için bekleyen)
    is_filled: bool = False  # Coin mi tutuyor yoksa USDT mi

    def __repr__(self):
        return f"Level(${self.fiyat:.2f}, filled={self.is_filled})"


@dataclass
class GridState:
    semboller: list
    sembol: str
    alt: float
    ust: float
    kademe: int
    sermaye: float  # başlangıç USDT
    levels: list = field(default_factory=list)
    free_usdt: float = 0.0
    trade_sayisi: int = 0
    kar: float = 0.0  # gerçekleşen kâr (USDT cinsinden)
    son_fiyat: float = 0.0
    # Metrikler
    al_sayisi: int = 0
    sat_sayisi: int = 0

    def kurulum(self, ilk_fiyat: float):
        """Grid seviyelerini oluştur. İlk fiyatın altındaki seviyelere AL emri (USDT ayır),
        üstüne ise coin al (SAT emri için)."""
        step = (self.ust - self.alt) / self.kademe
        self.levels = []
        # Her seviyeye eşit USDT değerinde pozisyon
        seviye_basi_usdt = self.sermaye / self.kademe

        for i in range(self.kademe + 1):
            fiyat = self.alt + i * step
            lvl = GridLevel(fiyat=fiyat)
            if fiyat < ilk_fiyat:
                # Bu seviyenin altında = bu fiyatta AL beklentisi → USDT ayır
                lvl.is_filled = False
                lvl.usdt_ayrilmis = seviye_basi_usdt
                self.free_usdt -= seviye_basi_usdt  # ayrılmış
            else:
                # Bu seviyenin üstünde = bu fiyatta SAT edilecek coin tut
                miktar = seviye_basi_usdt / fiyat
                # İlk fiyattan alım yapılmış varsayıyoruz (slippage+komisyon)
                maliyet = seviye_basi_usdt * (1 + KOMISYON + SLIPPAGE)
                self.free_usdt -= maliyet
                lvl.coin_miktar = miktar
                lvl.is_filled = True
            self.levels.append(lvl)

        # Başlangıçta kullanılmayan USDT = sermaye - toplam ayrılmış/harcanmış
        # free_usdt şu anda negatif (ödediğimiz harcamalar)
        # Başlangıç sermayesini ekle
        self.free_usdt += self.sermaye
        self.son_fiyat = ilk_fiyat

    def tik(self, yuksek: float, dusuk: float, kapanis: float):
        """Bir bar için: dusuk'e kadar inildi mi (AL tetiklenir) ve yuksek'e kadar çıkıldı mı (SAT tetiklenir).
        Sıralama önemli değil; her grid emri bağımsız."""
        # Aralığın dışındaysa işlem yapma (grid koptu — coin tutulmaya devam ediyor ama al-sat yok)
        for lvl in self.levels:
            if not lvl.is_filled and lvl.usdt_ayrilmis > 0:
                # AL emri bekliyor. Düşük, seviyenin altına indiyse tetiklenir.
                if dusuk <= lvl.fiyat:
                    # AL
                    gerekli = lvl.usdt_ayrilmis
                    miktar = gerekli / lvl.fiyat * (1 - KOMISYON - SLIPPAGE)
                    lvl.coin_miktar = miktar
                    lvl.is_filled = True
                    lvl.usdt_ayrilmis = 0
                    self.al_sayisi += 1
                    self.trade_sayisi += 1
            elif lvl.is_filled and lvl.coin_miktar > 0:
                # SAT emri bekliyor. Yüksek, seviyenin üstüne çıktıysa tetiklenir.
                # NOT: Grid'de her seviye kendi fiyatında SAT olur. Bu seviyenin üzerindeki bir seviyeye emir.
                # Basit yaklaşım: coin tuttuğumuz seviyenin bir üstüne SAT emri.
                # Ama bu dairesel — gerçek grid: her seviye "al burada, bir üst seviyede sat" şeklinde.
                # Tekrar tasarlıyorum: her seviye bir emir çifti.
                pass
        # Basit tasarım yetersiz — yeniden ele alıyorum aşağıda

    def mark_to_market(self, fiyat: float) -> float:
        """Mevcut fiyatla toplam portföy değeri."""
        coin_toplam = sum(l.coin_miktar for l in self.levels)
        return self.free_usdt + coin_toplam * fiyat


# === Daha temiz grid motoru ===
@dataclass
class GridOrder:
    """Bir grid seviyesindeki iki yönlü emir: alt_fiyat'ta AL, ust_fiyat'ta SAT."""
    alt_fiyat: float
    ust_fiyat: float
    coin_miktar: float = 0.0  # 0 = al bekliyor; >0 = coin var, sat bekliyor
    usdt_ayrilmis: float = 0.0  # al için ayrılmış para

    @property
    def durum(self) -> str:
        return "AL_BEKLER" if self.coin_miktar == 0 else "SAT_BEKLER"


class GridBot:
    def __init__(self, sembol, alt, ust, kademe, sermaye, ilk_fiyat):
        self.sembol = sembol
        self.alt = alt
        self.ust = ust
        self.kademe = kademe
        self.sermaye = sermaye
        self.step = (ust - alt) / kademe
        self.free_usdt = sermaye
        self.al_sayisi = 0
        self.sat_sayisi = 0
        self.tamamlanan_cift = 0  # full roundtrip count
        self.toplam_kar = 0.0

        # kademe adet grid çift-emir. Her emir: [fiyat_alt, fiyat_ust] ve alt'ta AL, ust'ta SAT.
        self.orders: list[GridOrder] = []
        seviye_basi_usdt = sermaye / kademe
        for i in range(kademe):
            alt_f = alt + i * self.step
            ust_f = alt + (i + 1) * self.step
            order = GridOrder(alt_fiyat=alt_f, ust_fiyat=ust_f)
            # İlk fiyata göre başlangıç pozisyonu:
            # Eğer alt_f < ilk_fiyat: bu emir zaten "al" tetiklenmiş varsayılır → coin tutuyor, sat bekliyor
            # Eğer alt_f >= ilk_fiyat: al bekliyor, USDT ayrılmış
            if alt_f < ilk_fiyat:
                # Satın al şimdi (ilk_fiyat'tan), ust_f'ye sat için dur
                maliyet = seviye_basi_usdt * (1 + KOMISYON + SLIPPAGE)
                if self.free_usdt >= maliyet:
                    order.coin_miktar = seviye_basi_usdt / ilk_fiyat * (1 - KOMISYON - SLIPPAGE)
                    self.free_usdt -= maliyet
            else:
                # AL bekliyor
                order.usdt_ayrilmis = seviye_basi_usdt
                self.free_usdt -= seviye_basi_usdt
            self.orders.append(order)

    def tik(self, yuksek, dusuk, kapanis):
        """Bir bar: hem düşük (al tetikler) hem yüksek (sat tetikler) olayları işle."""
        for o in self.orders:
            if o.coin_miktar == 0 and o.usdt_ayrilmis > 0:
                # AL bekliyor: dusuk seviyenin altına indi mi
                if dusuk <= o.alt_fiyat:
                    # AL gerçekleşti (alt_fiyat'ta)
                    miktar = o.usdt_ayrilmis / o.alt_fiyat * (1 - KOMISYON - SLIPPAGE)
                    o.coin_miktar = miktar
                    o.usdt_ayrilmis = 0
                    self.al_sayisi += 1
            if o.coin_miktar > 0:
                # SAT bekliyor: yuksek ust_fiyat'ı geçti mi
                if yuksek >= o.ust_fiyat:
                    # SAT gerçekleşti (ust_fiyat'ta)
                    gelir = o.coin_miktar * o.ust_fiyat * (1 - KOMISYON - SLIPPAGE)
                    # USDT'yi aynı seviyeye geri al için ayır (dönüşüm)
                    # Grid işlem: kâr = gelir - (önceki al maliyeti). Biz seviye_basi_usdt başlangıçta ayırmıştık.
                    seviye_basi_usdt = self.sermaye / self.kademe
                    # Kâr: alt_fiyat'ta alıp ust_fiyat'ta sattık — her çift şu kadar kazandırır:
                    self.toplam_kar += gelir - seviye_basi_usdt
                    # Yeni AL için ayrılır
                    o.usdt_ayrilmis = seviye_basi_usdt
                    o.coin_miktar = 0
                    self.sat_sayisi += 1
                    self.tamamlanan_cift += 1
        # Aralık dışına çıkarsa emirler yerinde durur ama tetiklenmez (grid kopar)

    def portfoy_degeri(self, fiyat):
        coin_toplam = sum(o.coin_miktar for o in self.orders)
        ayrilmis = sum(o.usdt_ayrilmis for o in self.orders)
        return self.free_usdt + ayrilmis + coin_toplam * fiyat

    def unrealized(self, fiyat):
        """Kapatılmamış pozisyonların fiyata göre değeri."""
        return self.portfoy_degeri(fiyat) - self.sermaye


def veri_yukle(sembol):
    """Belirli sembolün saatlik barlarını yükle."""
    bars = []
    with open(DATA_FILE, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["symbol"] == sembol:
                bars.append({
                    "dt": row["datetime"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })
    return bars


def backtest_grid(sembol, alt, ust, kademe, sermaye=BASLANGIC_SERMAYE):
    bars = veri_yukle(sembol)
    if not bars:
        return None
    ilk = bars[0]["close"]
    son = bars[-1]["close"]
    bot = GridBot(sembol, alt, ust, kademe, sermaye, ilk)
    for b in bars:
        bot.tik(b["high"], b["low"], b["close"])
    final_deger = bot.portfoy_degeri(son)
    return {
        "sembol": sembol,
        "alt": alt, "ust": ust, "kademe": kademe,
        "sermaye": sermaye,
        "ilk_fiyat": ilk, "son_fiyat": son,
        "buy_hold_getiri_pct": (son / ilk - 1) * 100,
        "final_deger": final_deger,
        "grid_getiri_pct": (final_deger / sermaye - 1) * 100,
        "al_sayisi": bot.al_sayisi,
        "sat_sayisi": bot.sat_sayisi,
        "tamamlanan_cift": bot.tamamlanan_cift,
        "tamamlanan_kar": bot.toplam_kar,
        "tamamlanan_kar_pct": bot.toplam_kar / sermaye * 100,
    }


def sembol_aralik(sembol, bars, pad_pct):
    """Verinin min-max'ına ±pad_pct ekleyerek grid aralığı önerir."""
    lows = [b["low"] for b in bars]
    highs = [b["high"] for b in bars]
    mn, mx = min(lows), max(highs)
    # Aralığı biraz daralt (extreme değerlere emir koymak boşa yer)
    alt = mn * (1 - pad_pct / 100)
    ust = mx * (1 + pad_pct / 100)
    return alt, ust


def main():
    sonuclar = []

    for sembol in ["BTCUSDT", "ETHUSDT"]:
        bars = veri_yukle(sembol)
        print(f"\n=== {sembol} ({len(bars)} bar) ===")
        print(f"  Fiyat: {bars[0]['close']:.2f} → {bars[-1]['close']:.2f}")
        lows = [b["low"] for b in bars]
        highs = [b["high"] for b in bars]
        print(f"  Range: {min(lows):.2f} ~ {max(highs):.2f}")

        # Farklı aralık/kademe kombinasyonları
        # Aralık: verinin min-max'ı (full range) — kademe sayısı farklı
        alt_full, ust_full = min(lows), max(highs)

        for kademe in [20, 40, 80]:
            r = backtest_grid(sembol, alt_full, ust_full, kademe)
            if r:
                r["etiket"] = f"FullRange_{kademe}k"
                sonuclar.append(r)
                print(f"  [{r['etiket']}] Grid: {r['grid_getiri_pct']:+.2f}% | "
                      f"B&H: {r['buy_hold_getiri_pct']:+.2f}% | "
                      f"Çift: {r['tamamlanan_cift']}")

        # Dar aralık — mevcut fiyatın ±%30'u
        son = bars[-1]["close"]
        ilk = bars[0]["close"]
        # Ortalama fiyata göre ±%40
        ort = (ilk + son) / 2
        alt_dar = ort * 0.6
        ust_dar = ort * 1.4
        for kademe in [20, 40]:
            r = backtest_grid(sembol, alt_dar, ust_dar, kademe)
            if r:
                r["etiket"] = f"DarAralik40_{kademe}k"
                sonuclar.append(r)
                print(f"  [{r['etiket']}] Grid: {r['grid_getiri_pct']:+.2f}% | "
                      f"Çift: {r['tamamlanan_cift']}")

    # Rapor yaz
    lines = ["# Grid Backtest Raporu — 2 Yıl (2024-04 → 2026-04)", ""]
    lines.append(f"**Sermaye:** ${BASLANGIC_SERMAYE} (her sembol için)")
    lines.append(f"**Komisyon:** %{KOMISYON*100} (taker)")
    lines.append(f"**Slippage:** %{SLIPPAGE*100}")
    lines.append("")
    lines.append("## Sonuçlar")
    lines.append("")
    lines.append("| Sembol | Strateji | Aralık | Kademe | Grid % | B&H % | Fark | Tam. Çift | Kar $ |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for r in sonuclar:
        fark = r["grid_getiri_pct"] - r["buy_hold_getiri_pct"]
        lines.append(
            f"| {r['sembol']} | {r['etiket']} | ${r['alt']:.0f}-${r['ust']:.0f} | "
            f"{r['kademe']} | {r['grid_getiri_pct']:+.2f}% | {r['buy_hold_getiri_pct']:+.2f}% | "
            f"{fark:+.2f}% | {r['tamamlanan_cift']} | ${r['tamamlanan_kar']:.2f} |"
        )

    lines.append("")
    lines.append("## Yorum")
    lines.append("")
    lines.append("- **Grid %** = grid bot'un net getirisi (başlangıç vs. son portföy, kapatılmamış dahil)")
    lines.append("- **B&H %** = buy-and-hold (başta al, sonda sat) getirisi")
    lines.append("- **Fark** = Grid B&H'dan ne kadar iyi (pozitif = grid kazandı)")
    lines.append("- **Tamamlanan Çift** = kaç kez al-sat döngüsü kapandı (gerçekleşmiş kâr üretir)")

    RAPOR.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapor yazıldı: {RAPOR}")


if __name__ == "__main__":
    main()
