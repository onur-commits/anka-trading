"""
🪙 COIN STRATEJİ — Balina + Korku + Kademe + Makro
=====================================================
3 katmanlı giriş stratejisi:
1. Korku + Balina teyidi → gerçek dip mi?
2. Kademeli giriş (DCA) → riski dağıt
3. Makro haber tetikleyici → siyasi/ekonomik katalizör

"Herkes korkuyorken al, ama balinalar da alıyorsa al"
"""

import requests
import numpy as np
import time
from datetime import datetime


class DipAvciBot:
    """
    Dip avcısı — korku + balina + kademe stratejisi.

    Kurallar:
    1. Fear & Greed < 20 → DİP BÖLGESİ
    2. Hacim artıyor + fiyat düşüyor → BALİNA TOPLUYOR
    3. İkisi birlikte → KADEMELİ GİRİŞ BAŞLAT
    """

    def __init__(self, toplam_butce=1000):
        self.toplam_butce = toplam_butce
        self.kademe_1 = toplam_butce * 0.33  # İlk giriş
        self.kademe_2 = toplam_butce * 0.33  # %10 düşerse
        self.kademe_3 = toplam_butce * 0.34  # Dönüş teyidinde
        self.giris_fiyat = 0
        self.pozisyonlar = []

    def korku_analiz(self):
        """Fear & Greed Index — 0-100."""
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=7", timeout=5)
            data = r.json()["data"]
            bugun = int(data[0]["value"])
            dun = int(data[1]["value"])
            ort_7g = np.mean([int(d["value"]) for d in data])

            return {
                "deger": bugun,
                "dun": dun,
                "ort_7g": round(ort_7g, 1),
                "trend": "yukari" if bugun > dun else "asagi",
                "extreme_fear": bugun <= 20,
                "donus_basladi": bugun > dun and bugun <= 30,  # Dipten dönüyor
            }
        except:
            return {"deger": 50, "extreme_fear": False, "donus_basladi": False}

    def balina_kontrol(self, symbol="BTCUSDT"):
        """
        Balina accumulation tespiti:
        Fiyat düşüyor + hacim artıyor = birileri dipten topluyor
        """
        try:
            # Son 48 saatlik veri
            r = requests.get("https://api.binance.com/api/v3/klines",
                           params={"symbol": symbol, "interval": "1h", "limit": 48}, timeout=5)
            data = r.json()

            fiyatlar = [float(k[4]) for k in data]  # Close
            hacimler = [float(k[5]) for k in data]  # Volume

            # Son 24 saat vs önceki 24 saat
            fiyat_son24 = np.mean(fiyatlar[-24:])
            fiyat_onceki24 = np.mean(fiyatlar[:24])
            fiyat_degisim = (fiyat_son24 / fiyat_onceki24 - 1) * 100

            hacim_son24 = np.mean(hacimler[-24:])
            hacim_onceki24 = np.mean(hacimler[:24])
            hacim_degisim = (hacim_son24 / hacim_onceki24 - 1) * 100

            # Son 6 saatteki hacim trendi
            hacim_son6 = np.mean(hacimler[-6:])
            hacim_ort = np.mean(hacimler)
            hacim_spike = hacim_son6 / hacim_ort

            # BALİNA ACCUMULATION:
            # Fiyat düşerken veya yatayken hacim artıyorsa → birileri topluyor
            accumulation = fiyat_degisim < 2 and hacim_degisim > 20

            # DIVERGENCE:
            # Fiyat düşüyor ama hacim artıyor → güçlü dip sinyali
            divergence = fiyat_degisim < -3 and hacim_degisim > 30

            return {
                "fiyat_degisim": round(fiyat_degisim, 1),
                "hacim_degisim": round(hacim_degisim, 1),
                "hacim_spike": round(hacim_spike, 1),
                "accumulation": accumulation,
                "divergence": divergence,
                "son_fiyat": round(fiyatlar[-1], 2),
            }
        except:
            return {"accumulation": False, "divergence": False}

    def makro_kontrol(self):
        """
        Makro tetikleyiciler:
        - BTC dominans artıyorsa → altcoin'ler daha çok düşer
        - DXY (dolar endeksi) düşüyorsa → kripto için pozitif
        """
        try:
            # BTC 24h değişim
            r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                           params={"symbol": "BTCUSDT"}, timeout=5)
            btc = r.json()
            btc_degisim = float(btc["priceChangePercent"])

            # Toplam kripto piyasa hacmi (BTC + ETH + BNB proxy)
            toplam_hacim = 0
            for sym in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
                r2 = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                                params={"symbol": sym}, timeout=5)
                toplam_hacim += float(r2.json()["quoteVolume"])

            return {
                "btc_degisim": round(btc_degisim, 1),
                "toplam_hacim_b": round(toplam_hacim / 1e9, 1),
                "btc_pozitif": btc_degisim > 0,
            }
        except:
            return {"btc_degisim": 0, "btc_pozitif": False}

    def strateji_degerlendir(self, symbol="BTCUSDT"):
        """
        3 KATMANLI DEĞERLENDİRME:
        Korku + Balina + Makro → Kademe kararı
        """
        korku = self.korku_analiz()
        balina = self.balina_kontrol(symbol)
        makro = self.makro_kontrol()

        print(f"\n🪙 DİP AVCI ANALİZ — {symbol}")
        print("=" * 60)

        # KATMAN 1: KORKU
        print(f"\n😱 KORKU ENDEKSİ: {korku['deger']}")
        if korku["extreme_fear"]:
            print(f"   🟢 EXTREME FEAR — tarihsel alım bölgesi!")
        elif korku["donus_basladi"]:
            print(f"   🟡 Dönüş başladı (dün:{korku['dun']} → bugün:{korku['deger']})")
        else:
            print(f"   ⚪ Normal bölge")

        # KATMAN 2: BALİNA
        print(f"\n🐋 BALİNA ANALİZ:")
        print(f"   Fiyat 24s: {balina.get('fiyat_degisim', 0):+.1f}%")
        print(f"   Hacim 24s: {balina.get('hacim_degisim', 0):+.1f}%")
        if balina.get("divergence"):
            print(f"   🟢 DİVERGENCE — Fiyat düşüyor ama hacim artıyor → BALİNA TOPLUYOR!")
        elif balina.get("accumulation"):
            print(f"   🟡 ACCUMULATION — Hacim artıyor, birikim var")
        else:
            print(f"   ⚪ Normal hareket")

        # KATMAN 3: MAKRO
        print(f"\n🌍 MAKRO:")
        print(f"   BTC 24s: {makro.get('btc_degisim', 0):+.1f}%")
        print(f"   Toplam hacim: ${makro.get('toplam_hacim_b', 0):.1f}B")

        # KARAR
        print(f"\n{'='*60}")
        print("📊 KARAR:")

        skor = 0
        if korku["extreme_fear"]: skor += 3
        if korku["donus_basladi"]: skor += 2
        if balina.get("divergence"): skor += 3
        if balina.get("accumulation"): skor += 2
        if makro.get("btc_pozitif"): skor += 1

        if skor >= 6:
            print(f"   🟢 KADEME 1 BAŞLAT — {self.kademe_1:.0f}$ ile gir!")
            print(f"   Fiyat %10 düşerse → KADEME 2 ({self.kademe_2:.0f}$)")
            print(f"   Dönüş teyidi → KADEME 3 ({self.kademe_3:.0f}$)")
            karar = "KADEME_1"
        elif skor >= 4:
            print(f"   🟡 HAZIRLAN — Sinyaller güçleniyor, dipte birikim var")
            print(f"   Korku endeksi dönüş yaparsa → GİR")
            karar = "HAZIRLAN"
        elif skor >= 2:
            print(f"   ⚪ İZLE — Henüz yeterli sinyal yok")
            karar = "IZLE"
        else:
            print(f"   🔴 BEKLE — Piyasa henüz dip yapmadı")
            karar = "BEKLE"

        print(f"   Skor: {skor}/9")
        print(f"   Korku: {korku['deger']} | Balina: {'TOPLUYOR' if balina.get('accumulation') else 'pasif'}")

        return {
            "karar": karar,
            "skor": skor,
            "korku": korku,
            "balina": balina,
            "makro": makro,
            "symbol": symbol,
            "fiyat": balina.get("son_fiyat", 0),
        }


if __name__ == "__main__":
    bot = DipAvciBot(toplam_butce=1300)

    # BTC analiz
    btc = bot.strateji_degerlendir("BTCUSDT")

    # ETH analiz
    print("\n" + "="*60)
    eth = bot.strateji_degerlendir("ETHUSDT")

    # SOL analiz
    print("\n" + "="*60)
    sol = bot.strateji_degerlendir("SOLUSDT")
