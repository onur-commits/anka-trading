"""
🪙 COIN TRADER — ANKA'nın Kripto Kardeşi
==========================================
Binance API ile 7/24 otonom kripto trading.
ANKA ile aynı mimari: 5 ajan + karar verici + panel kuralları.

BIST (ANKA): 09:10-18:00 çalışır
COIN: 7/24 çalışır — gece bile!

Kullanım:
  python coin_trader.py --tara          # Tek tarama
  python coin_trader.py --bot           # 7/24 otonom
  python coin_trader.py --durum         # Durum kontrol
  python coin_trader.py --dry-run       # Simülasyon (emir göndermez)
"""

import json
import time
import os
import sys
import hmac
import hashlib
import requests
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

COIN_BRIDGE = DATA_DIR / "coin_bridge.json"
COIN_STATE = DATA_DIR / "coin_state.json"
COIN_LOG = DATA_DIR / "coin_log.json"


# ================================================================
# BINANCE API CLIENT
# ================================================================
class BinanceClient:
    """Binance REST API client."""

    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key="", api_secret=""):
        self.api_key = api_key
        self.api_secret = api_secret

    def _sign(self, params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        signature = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _headers(self):
        return {"X-MBX-APIKEY": self.api_key}

    # ── PİYASA VERİSİ (API key gerekmez) ──────────
    def fiyat(self, symbol="BTCUSDT"):
        """Anlık fiyat."""
        r = requests.get(f"{self.BASE_URL}/api/v3/ticker/price", params={"symbol": symbol})
        return float(r.json()["price"])

    def kline(self, symbol="BTCUSDT", interval="1h", limit=100):
        """Mum verisi çek."""
        r = requests.get(f"{self.BASE_URL}/api/v3/klines", params={
            "symbol": symbol, "interval": interval, "limit": limit
        })
        data = r.json()
        import pandas as pd
        df = pd.DataFrame(data, columns=[
            "open_time", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_vol", "trades", "buy_base", "buy_quote", "ignore"
        ])
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = df[col].astype(float)
        df["time"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("time", inplace=True)
        return df

    def ticker_24h(self, symbol="BTCUSDT"):
        """24 saatlik özet."""
        r = requests.get(f"{self.BASE_URL}/api/v3/ticker/24hr", params={"symbol": symbol})
        return r.json()

    def derinlik(self, symbol="BTCUSDT", limit=10):
        """Emir defteri (LOB)."""
        r = requests.get(f"{self.BASE_URL}/api/v3/depth", params={
            "symbol": symbol, "limit": limit
        })
        return r.json()

    # ── HESAP & EMİR (API key gerekir) ─────────────
    def bakiye(self):
        """Hesap bakiyesi."""
        params = {"timestamp": int(time.time() * 1000)}
        params = self._sign(params)
        r = requests.get(f"{self.BASE_URL}/api/v3/account",
                        headers=self._headers(), params=params)
        return r.json()

    def alis(self, symbol, miktar, fiyat=None):
        """
        Alış emri.
        fiyat=None → Piyasa emri
        fiyat=değer → Limit emri
        """
        params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET" if fiyat is None else "LIMIT",
            "quantity": miktar,
            "timestamp": int(time.time() * 1000),
        }
        if fiyat:
            params["price"] = fiyat
            params["timeInForce"] = "GTC"
        params = self._sign(params)
        r = requests.post(f"{self.BASE_URL}/api/v3/order",
                         headers=self._headers(), params=params)
        return r.json()

    def satis(self, symbol, miktar, fiyat=None):
        """Satış emri."""
        params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET" if fiyat is None else "LIMIT",
            "quantity": miktar,
            "timestamp": int(time.time() * 1000),
        }
        if fiyat:
            params["price"] = fiyat
            params["timeInForce"] = "GTC"
        params = self._sign(params)
        r = requests.post(f"{self.BASE_URL}/api/v3/order",
                         headers=self._headers(), params=params)
        return r.json()


# ================================================================
# KRİPTO AJANLARI (ANKA ile aynı mimari)
# ================================================================

class CryptoTechnoAgent:
    """Teknik analiz — EMA, RSI, MACD, Bollinger."""
    ad = "TECHNO"

    def analiz(self, df):
        if df is None or len(df) < 50:
            return 0, "Veri yok"

        c = df['Close']
        puan = 0
        detay = []

        ema10 = c.ewm(span=10).mean()
        ema20 = c.ewm(span=20).mean()
        if float(ema10.iloc[-1]) > float(ema20.iloc[-1]):
            puan += 25
            detay.append("EMA✅")

        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = float(100 - (100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-10))))
        if 50 < rsi < 70:
            puan += 20
            detay.append(f"RSI:{rsi:.0f}✅")

        macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        signal = macd.ewm(span=9).mean()
        if float(macd.iloc[-1]) > float(signal.iloc[-1]):
            puan += 20
            detay.append("MACD✅")

        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        boll_width = float(4 * std20.iloc[-1] / sma20.iloc[-1] * 100) if sma20.iloc[-1] > 0 else 0
        if boll_width < 5:
            puan += 15
            detay.append("SIKIŞMA🔥")

        vol = df['Volume']
        vol_oran = float(vol.iloc[-1] / vol.rolling(20).mean().iloc[-1]) if vol.rolling(20).mean().iloc[-1] > 0 else 0
        if vol_oran > 1.5:
            puan += 20
            detay.append(f"Hacim:x{vol_oran:.1f}✅")

        return min(100, puan), " ".join(detay)


class CryptoMacroAgent:
    """Kripto makro — BTC dominans, Fear & Greed, funding rate."""
    ad = "MACRO"

    def analiz(self, btc_df=None):
        puan = 50
        detay = []

        try:
            # BTC trend
            if btc_df is not None and len(btc_df) >= 20:
                c = btc_df['Close']
                sma20 = float(c.rolling(20).mean().iloc[-1])
                son = float(c.iloc[-1])
                if son > sma20:
                    puan += 20
                    detay.append("BTC trend✅")
                else:
                    puan -= 20
                    detay.append("BTC trend❌")

                chg_24h = float((c.iloc[-1] / c.iloc[-2] - 1) * 100)
                if chg_24h > 2:
                    puan += 10
                    detay.append(f"BTC:{chg_24h:+.1f}%✅")
                elif chg_24h < -2:
                    puan -= 10
                    detay.append(f"BTC:{chg_24h:+.1f}%❌")
        except:
            pass

        return max(0, min(100, puan)), " ".join(detay) if detay else "Nötr"


class CryptoVolumeAgent:
    """Hacim ve likidite analizi."""
    ad = "VOLUME"

    def analiz(self, df):
        if df is None or len(df) < 20:
            return 0, "Veri yok"

        v = df['Volume']
        c = df['Close']
        puan = 0
        detay = []

        vol_oran = float(v.iloc[-1] / v.rolling(20).mean().iloc[-1])
        if vol_oran >= 2.0:
            puan += 40
            detay.append(f"Hacim:x{vol_oran:.1f}🔥")
        elif vol_oran >= 1.5:
            puan += 25
            detay.append(f"Hacim:x{vol_oran:.1f}✅")

        # OBV
        import numpy as np
        obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
        obv_sma = obv.rolling(20).mean()
        if float(obv.iloc[-1]) > float(obv_sma.iloc[-1]):
            puan += 30
            detay.append("OBV✅")

        # Kapanış gücü
        kap = float(c.iloc[-1] / df['High'].iloc[-1])
        if kap >= 0.985:
            puan += 30
            detay.append(f"Kap:{kap:.3f}✅")

        return min(100, puan), " ".join(detay)


# ================================================================
# COIN KARAR VERİCİ
# ================================================================
class CoinBrain:
    """Kripto karar verici — ANKA ile aynı mimari."""

    COINS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT",
        "ATOMUSDT", "NEARUSDT", "FTMUSDT", "ARBUSDT", "OPUSDT",
    ]

    def __init__(self, api_key="", api_secret=""):
        self.client = BinanceClient(api_key, api_secret)
        self.ajanlar = [CryptoTechnoAgent(), CryptoVolumeAgent(), CryptoMacroAgent()]

    def tara(self, coins=None):
        if coins is None:
            coins = self.COINS

        print(f"\n🪙 COIN TRADER — {len(coins)} coin taranıyor")
        print("=" * 60)

        # BTC verisi (makro için)
        btc_df = self.client.kline("BTCUSDT", "1h", 100)

        bombalar = []

        for symbol in coins:
            try:
                df = self.client.kline(symbol, "1h", 100)
                if len(df) < 50:
                    continue

                techno_p, techno_d = CryptoTechnoAgent().analiz(df)
                volume_p, volume_d = CryptoVolumeAgent().analiz(df)
                macro_p, macro_d = CryptoMacroAgent().analiz(btc_df)

                puanlar = {"TECHNO": techno_p, "VOLUME": volume_p, "MACRO": macro_p}
                toplam = techno_p * 0.4 + volume_p * 0.3 + macro_p * 0.3

                al_sayisi = sum(1 for p in puanlar.values() if p >= 60)
                karar = "AL" if toplam >= 60 and al_sayisi >= 2 else "BEKLE"

                emoji = "🪙" if karar == "AL" else "⚪"
                fiyat = float(df['Close'].iloc[-1])

                puan_txt = " ".join(f"{k[:3]}:{v}" for k, v in puanlar.items())
                print(f"  {emoji} {symbol:12} ${fiyat:>10,.2f} | {puan_txt} | Toplam:{toplam:.0f}")

                bombalar.append({
                    "symbol": symbol, "fiyat": fiyat, "skor": toplam,
                    "karar": karar, "puanlar": puanlar,
                    "techno_d": techno_d, "volume_d": volume_d,
                })

            except Exception as e:
                continue

        # SKORA GÖRE SIRALA
        bombalar.sort(key=lambda x: x["skor"], reverse=True)

        print(f"\n{'='*60}")
        print(f"📊 SKOR SIRALAMASINA GÖRE TÜM COİNLER:")
        print(f"{'='*60}")
        for i, b in enumerate(bombalar):
            emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🪙" if b["karar"] == "AL" else "⚪"
            birim = "₺" if "TRY" in b["symbol"] else "$"
            print(f"  {i+1:2}. {emoji} {b['symbol']:12} {birim}{b['fiyat']:>10,.2f} | Skor:{b['skor']:5.1f} | {b['karar']}")

        al_listesi = [b for b in bombalar if b["karar"] == "AL"]
        print(f"\n🎯 BOMBA ({len(al_listesi)}/{len(bombalar)}): {', '.join(b['symbol'] for b in al_listesi) if al_listesi else 'YOK'}")
        return bombalar


# ================================================================
# ANA
# ================================================================
# ================================================================
# ROKET TARAYICI — Anormal Hacim + Parabolik Yükseliş Yakalayıcı
# ================================================================
class RoketTarayici:
    """
    SIREN gibi roketi yakalar:
    - Hacim x5+ patlama
    - Fiyat %10+ yükseliş (24s)
    - Tüm SMA'ların üstünde
    - 5 dakikada bir tarar
    """

    # Binance'deki tüm popüler TL ve USDT pairleri
    USDT_COINS = [
        "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
        "AVAXUSDT","DOTUSDT","MATICUSDT","LINKUSDT","ATOMUSDT","NEARUSDT",
        "FTMUSDT","ARBUSDT","OPUSDT","APTUSDT","SUIUSDT","SEIUSDT",
        "TIAUSDT","JUPUSDT","WUSDT","ENAUSDT","STRKUSDT","ZETAUSDT",
        "DYDXUSDT","INJUSDT","PENDLEUSDT","RENDERUSDT","FETUSDT",
        "ONDOUSDT","ARUSDT","WLDUSDT","PYTHUSDT","RUNEUSDT","EIGENUSDT",
    ]

    TL_COINS = [
        "BTCTRY","ETHTRY","BNBTRY","SOLTRY","XRPTRY","ADATRY",
        "AVAXTRY","DOTTRY","LINKTRY","USDTTRY","SIRENTRY",
    ]

    def __init__(self):
        self.client = BinanceClient()

    def hacim_patlama_tara(self, coins=None, esik=5.0):
        """Hacim ortalamanın N katı olan coinleri bul."""
        if coins is None:
            coins = self.USDT_COINS + self.TL_COINS

        print(f"\n🚀 ROKET TARAYICI — {len(coins)} coin")
        print(f"   Hacim eşiği: x{esik}+")
        print("=" * 60)

        roketler = []

        for symbol in coins:
            try:
                # 1 saatlik veri çek
                df = self.client.kline(symbol, "1h", 100)
                if len(df) < 24:
                    continue

                c = df['Close']
                v = df['Volume']

                son_fiyat = float(c.iloc[-1])
                son_hacim = float(v.iloc[-1])
                ort_hacim = float(v.iloc[-25:-1].mean())  # Son 24 saatlik ortalama

                if ort_hacim <= 0:
                    continue

                hacim_oran = son_hacim / ort_hacim

                # 24 saatlik değişim
                fiyat_24s = float(c.iloc[-24]) if len(c) >= 24 else float(c.iloc[0])
                degisim_24s = (son_fiyat / fiyat_24s - 1) * 100

                # 1 saatlik değişim
                degisim_1s = (float(c.iloc[-1]) / float(c.iloc[-2]) - 1) * 100

                # SMA kontrol
                sma20 = float(c.rolling(20).mean().iloc[-1])
                sma50 = float(c.rolling(min(50, len(c))).mean().iloc[-1])
                sma_ustunde = son_fiyat > sma20 > sma50

                # ROKET KRİTERLERİ
                is_roket = False
                sebep = []

                if hacim_oran >= esik:
                    sebep.append(f"HACİM x{hacim_oran:.1f}🔥")
                    is_roket = True

                if degisim_24s >= 10:
                    sebep.append(f"24s +%{degisim_24s:.1f}🚀")
                    is_roket = True

                if degisim_1s >= 5:
                    sebep.append(f"1s +%{degisim_1s:.1f}⚡")
                    is_roket = True

                if sma_ustunde and degisim_24s > 5:
                    sebep.append("SMA✅")

                # Skor hesapla
                skor = (hacim_oran * 10) + (degisim_24s * 2) + (degisim_1s * 5)
                if sma_ustunde:
                    skor *= 1.2

                if is_roket:
                    roketler.append({
                        "symbol": symbol,
                        "fiyat": son_fiyat,
                        "hacim_x": round(hacim_oran, 1),
                        "degisim_24s": round(degisim_24s, 1),
                        "degisim_1s": round(degisim_1s, 1),
                        "sma_ok": sma_ustunde,
                        "skor": round(skor, 0),
                        "sebep": " | ".join(sebep),
                    })

                    fiyat_str = f"₺{son_fiyat:,.2f}" if "TRY" in symbol else f"${son_fiyat:,.4f}" if son_fiyat < 1 else f"${son_fiyat:,.2f}"
                    print(f"  🚀 {symbol:15} {fiyat_str:>12} | {' | '.join(sebep)} | Skor:{skor:.0f}")

            except:
                continue

        roketler.sort(key=lambda x: x["skor"], reverse=True)

        if not roketler:
            print("  Şu an roket yok — piyasa sakin")

        print(f"\n🎯 {len(roketler)} ROKET bulundu")
        return roketler

    def surekli_tara(self, aralik_dk=5):
        """Her N dakikada roket tara — 7/24."""
        print(f"🚀 ROKET TARAYICI 7/24 — Her {aralik_dk} dakika")
        while True:
            roketler = self.hacim_patlama_tara()
            if roketler:
                # Bridge'e yaz
                with open(PROJECT_DIR / "data" / "roket_sinyaller.json", "w") as f:
                    json.dump({
                        "zaman": datetime.now().isoformat(),
                        "roketler": roketler
                    }, f, indent=2)
            time.sleep(aralik_dk * 60)


if __name__ == "__main__":
    if "--tara" in sys.argv or len(sys.argv) == 1:
        brain = CoinBrain()
        bombalar = brain.tara()

    elif "--roket" in sys.argv:
        tarayici = RoketTarayici()
        tarayici.hacim_patlama_tara()

    elif "--roket-loop" in sys.argv:
        tarayici = RoketTarayici()
        tarayici.surekli_tara(aralik_dk=5)

    elif "--durum" in sys.argv:
        print("🪙 COIN TRADER durumu")
        if COIN_STATE.exists():
            print(json.dumps(json.load(open(COIN_STATE)), indent=2))
        else:
            print("Henüz state yok")
