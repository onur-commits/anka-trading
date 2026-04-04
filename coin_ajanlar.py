"""
🪙 COIN AJANLAR — 6 Yeni Uzman Ajan
=====================================
Tüm veriler bedava API'lerden çekilir.
Binance + Whale Alert + Alternative.me + Reddit
"""

import requests
import numpy as np
import pandas as pd
import time
from datetime import datetime


# ================================================================
# AJAN 5: FUNDING AGENT — Long/Short Dengesi
# ================================================================
class FundingAgent:
    """
    Funding rate negatif → shortlar baskın → dip yakın olabilir
    Funding rate çok pozitif → longlar aşırı → tepe yakın olabilir
    """
    ad = "FUNDING"

    def analiz(self, symbol="BTCUSDT"):
        puan = 50
        detay = []

        try:
            # Binance Futures funding rate
            r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                           params={"symbol": symbol, "limit": 10}, timeout=5)
            data = r.json()

            if data:
                son_rate = float(data[-1]["fundingRate"])
                ort_rate = np.mean([float(d["fundingRate"]) for d in data])

                if son_rate < -0.001:
                    puan += 30  # Negatif funding → shortlar ödüyor → dip sinyali
                    detay.append(f"Funding:{son_rate:.4f} NEGATİF🟢")
                elif son_rate > 0.005:
                    puan -= 20  # Çok pozitif → aşırı long → tepe riski
                    detay.append(f"Funding:{son_rate:.4f} AŞIRI LONG⚠️")
                else:
                    detay.append(f"Funding:{son_rate:.4f}")

            # Long/Short oranı
            r2 = requests.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
                            params={"symbol": symbol, "period": "1h", "limit": 5}, timeout=5)
            ls_data = r2.json()

            if ls_data:
                long_ratio = float(ls_data[-1]["longAccount"])
                short_ratio = float(ls_data[-1]["shortAccount"])

                if long_ratio > 0.65:
                    puan -= 15
                    detay.append(f"L/S:{long_ratio:.0%}/{short_ratio:.0%} KALABALIK LONG⚠️")
                elif short_ratio > 0.60:
                    puan += 20
                    detay.append(f"L/S:{long_ratio:.0%}/{short_ratio:.0%} SHORT SQUEEZE🟢")
                else:
                    detay.append(f"L/S:{long_ratio:.0%}/{short_ratio:.0%}")

        except Exception as e:
            detay.append(f"Veri hatası")

        return max(0, min(100, puan)), " ".join(detay)


# ================================================================
# AJAN 6: ON-CHAIN AGENT — Balina Takibi
# ================================================================
class OnChainAgent:
    """
    Büyük transferleri izle — borsaya giriş = satış baskısı
    Borsadan çıkış = hodl sinyali
    """
    ad = "ONCHAIN"

    def analiz(self, symbol="BTC"):
        puan = 50
        detay = []

        try:
            # Whale Alert (bedava tier: 10 istek/dk)
            # API key gerekiyor ama bedava kayıt
            # Şimdilik Binance transfer hacminden proxy
            r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                           params={"symbol": f"{symbol}USDT"}, timeout=5)
            data = r.json()

            hacim = float(data.get("quoteVolume", 0))
            fiyat_degisim = float(data.get("priceChangePercent", 0))

            # Yüksek hacim + düşüş = balina satışı
            if hacim > 1e9 and fiyat_degisim < -3:
                puan -= 20
                detay.append(f"Hacim:${hacim/1e9:.1f}B + düşüş → BALINA SATIŞI⚠️")
            elif hacim > 1e9 and fiyat_degisim > 3:
                puan += 20
                detay.append(f"Hacim:${hacim/1e9:.1f}B + yükseliş → BALINA ALIMI🟢")
            else:
                detay.append(f"Hacim:${hacim/1e9:.1f}B")

        except:
            detay.append("Veri hatası")

        return max(0, min(100, puan)), " ".join(detay)


# ================================================================
# AJAN 7: SENTIMENT AGENT — Korku & Açgözlülük
# ================================================================
class SentimentAgent:
    """
    Fear & Greed Index:
    0-25 = Extreme Fear → ALIŞ fırsatı (herkes korkuyorken al)
    75-100 = Extreme Greed → SATIŞ sinyali (herkes açgözlüyken sat)
    """
    ad = "SENTIMENT"

    def analiz(self):
        puan = 50
        detay = []

        try:
            # Alternative.me Fear & Greed Index (bedava, limitsiz)
            r = requests.get("https://api.alternative.me/fng/?limit=7", timeout=5)
            data = r.json()

            if "data" in data:
                bugun = data["data"][0]
                fng_value = int(bugun["value"])
                fng_class = bugun["value_classification"]

                # Son 7 günün ortalaması
                ort_7g = np.mean([int(d["value"]) for d in data["data"]])

                if fng_value <= 20:
                    puan += 35  # Extreme Fear → ALIŞ!
                    detay.append(f"F&G:{fng_value} EXTREME FEAR🟢💰")
                elif fng_value <= 35:
                    puan += 20
                    detay.append(f"F&G:{fng_value} Fear🟢")
                elif fng_value >= 80:
                    puan -= 25  # Extreme Greed → DİKKAT!
                    detay.append(f"F&G:{fng_value} EXTREME GREED🔴")
                elif fng_value >= 65:
                    puan -= 10
                    detay.append(f"F&G:{fng_value} Greed⚠️")
                else:
                    detay.append(f"F&G:{fng_value} {fng_class}")

                # Trend: artıyor mu azalıyor mu
                if fng_value > ort_7g + 10:
                    detay.append("↑Trend")
                elif fng_value < ort_7g - 10:
                    detay.append("↓Trend")

        except:
            detay.append("Veri hatası")

        return max(0, min(100, puan)), " ".join(detay)


# ================================================================
# AJAN 8: LIQUIDATION AGENT — Likidasyonlar
# ================================================================
class LiquidationAgent:
    """
    Büyük likidasyonlar = volatilite fırsatı
    Long likidasyonu = dip yakın (panic selling bitti)
    Short likidasyonu = pump devam edebilir
    """
    ad = "LIQUIDATION"

    def analiz(self, symbol="BTCUSDT"):
        puan = 50
        detay = []

        try:
            # Top trader long/short ratio
            r = requests.get("https://fapi.binance.com/futures/data/topLongShortPositionRatio",
                           params={"symbol": symbol, "period": "1h", "limit": 10}, timeout=5)
            data = r.json()

            if data:
                son = data[-1]
                long_ratio = float(son["longAccount"])
                short_ratio = float(son["shortAccount"])

                # 10 saat önceki oran
                onceki = data[0]
                onceki_long = float(onceki["longAccount"])

                # Long oranı düşüyorsa → likidasyonlar olmuş
                degisim = long_ratio - onceki_long

                if degisim < -0.05:
                    puan += 25  # Long likidasyonu → dip fırsatı
                    detay.append(f"Long tasfiye:{degisim:+.2%}→DİP🟢")
                elif degisim > 0.05:
                    puan -= 15  # Herkes long → riskli
                    detay.append(f"Long artış:{degisim:+.2%}→KALABALIK⚠️")
                else:
                    detay.append(f"L/S stabil")

            # Open Interest
            r2 = requests.get("https://fapi.binance.com/fapi/v1/openInterest",
                            params={"symbol": symbol}, timeout=5)
            oi = r2.json()
            if oi:
                oi_val = float(oi.get("openInterest", 0))
                detay.append(f"OI:{oi_val:,.0f}")

        except:
            detay.append("Veri hatası")

        return max(0, min(100, puan)), " ".join(detay)


# ================================================================
# AJAN 9: ORDER BOOK AGENT — Emir Defteri Derinliği
# ================================================================
class OrderBookAgent:
    """
    Emir defterindeki büyük duvarları tespit et.
    Büyük alış duvarı = destek
    Büyük satış duvarı = direnç
    """
    ad = "ORDERBOOK"

    def analiz(self, symbol="BTCUSDT"):
        puan = 50
        detay = []

        try:
            r = requests.get("https://api.binance.com/api/v3/depth",
                           params={"symbol": symbol, "limit": 20}, timeout=5)
            data = r.json()

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            # Toplam alış vs satış hacmi
            bid_vol = sum(float(b[1]) for b in bids)
            ask_vol = sum(float(a[1]) for a in asks)

            oran = bid_vol / (ask_vol + 1e-10)

            if oran > 1.5:
                puan += 25
                detay.append(f"Bid/Ask:{oran:.1f} ALIŞ BASKISI🟢")
            elif oran < 0.7:
                puan -= 20
                detay.append(f"Bid/Ask:{oran:.1f} SATIŞ BASKISI🔴")
            else:
                detay.append(f"Bid/Ask:{oran:.1f} Dengeli")

            # En büyük duvar tespiti
            max_bid = max(bids, key=lambda x: float(x[1]))
            max_ask = min(asks, key=lambda x: float(x[1]))
            detay.append(f"Destek:{float(max_bid[0]):,.0f} Direnç:{float(max_ask[0]):,.0f}")

        except:
            detay.append("Veri hatası")

        return max(0, min(100, puan)), " ".join(detay)


# ================================================================
# AJAN 10: CORRELATION AGENT — BTC Korelasyonu
# ================================================================
class CorrelationAgent:
    """
    BTC yükselirken coin daha çok yükseliyorsa = beta yüksek (agresif)
    BTC düşerken coin az düşüyorsa = savunmacı
    """
    ad = "CORRELATION"

    def analiz(self, symbol="ETHUSDT"):
        puan = 50
        detay = []

        try:
            # BTC ve coin verisini çek
            btc = requests.get("https://api.binance.com/api/v3/klines",
                             params={"symbol": "BTCUSDT", "interval": "1h", "limit": 48}, timeout=5).json()
            coin = requests.get("https://api.binance.com/api/v3/klines",
                              params={"symbol": symbol, "interval": "1h", "limit": 48}, timeout=5).json()

            btc_returns = [float(btc[i][4])/float(btc[i-1][4])-1 for i in range(1, len(btc))]
            coin_returns = [float(coin[i][4])/float(coin[i-1][4])-1 for i in range(1, len(coin))]

            min_len = min(len(btc_returns), len(coin_returns))
            btc_r = np.array(btc_returns[:min_len])
            coin_r = np.array(coin_returns[:min_len])

            # Korelasyon
            corr = np.corrcoef(btc_r, coin_r)[0, 1]

            # Beta
            beta = np.cov(coin_r, btc_r)[0, 1] / (np.var(btc_r) + 1e-10)

            # BTC son 24s trend
            btc_24s = (float(btc[-1][4]) / float(btc[0][4]) - 1) * 100

            if btc_24s > 1 and beta > 1.2:
                puan += 25
                detay.append(f"BTC↑ + Beta:{beta:.1f} = AGRESİF YUKARI🟢")
            elif btc_24s < -1 and beta > 1.2:
                puan -= 25
                detay.append(f"BTC↓ + Beta:{beta:.1f} = SERT DÜŞÜŞ RİSKİ🔴")
            elif beta < 0.5:
                puan += 10
                detay.append(f"Beta:{beta:.1f} = BAĞIMSIZ")
            else:
                detay.append(f"Beta:{beta:.1f} Korr:{corr:.2f}")

            detay.append(f"BTC 24s:{btc_24s:+.1f}%")

        except:
            detay.append("Veri hatası")

        return max(0, min(100, puan)), " ".join(detay)


# ================================================================
# TEST
# ================================================================
if __name__ == "__main__":
    print("🪙 COIN AJANLAR — Test")
    print("=" * 60)

    ajanlar = [
        ("FUNDING", FundingAgent()),
        ("ONCHAIN", OnChainAgent()),
        ("SENTIMENT", SentimentAgent()),
        ("LIQUIDATION", LiquidationAgent()),
        ("ORDERBOOK", OrderBookAgent()),
        ("CORRELATION", CorrelationAgent()),
    ]

    for ad, ajan in ajanlar:
        if ad == "SENTIMENT":
            puan, detay = ajan.analiz()
        elif ad == "ONCHAIN":
            puan, detay = ajan.analiz("BTC")
        elif ad == "CORRELATION":
            puan, detay = ajan.analiz("ETHUSDT")
        else:
            puan, detay = ajan.analiz("BTCUSDT")

        emoji = "🟢" if puan >= 60 else "🔴" if puan <= 40 else "🟡"
        print(f"  {emoji} {ad:15} Puan:{puan:3} | {detay}")
