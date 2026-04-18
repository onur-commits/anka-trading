"""
ANKA COIN OTONOM TRADER — 7/24 Kripto Trading Sistemi
======================================================
Binance Spot API üzerinden tam otonom kripto trading.
BIST motorundan BAĞIMSIZ, kendine özgü dinamiklerle çalışır.

KRİPTO'YA ÖZGÜ DİNAMİKLER:
  - 7/24 piyasa (gün sonu kapanış yok)
  - BTC korelasyonu: BTC düşüyorsa altcoin alma
  - Hacim patlaması tespiti (whale alert)
  - Likidite derinliği analizi (spread kontrolü)
  - Funding rate sentiment (futures kaynaklı)
  - Volatilite bazlı pozisyon boyutu (ATR)
  - Roket tespit: Anormal hareket → hızlı giriş/çıkış

KARAR DÖNGÜSÜ (her 15 dakika):
  1. BTC trend kontrolü (koruma kalkanı)
  2. 15 coin tara → skor hesapla
  3. Skor >= 65 + BTC OK → market alış
  4. Pozisyon takibi: stop-loss, trailing stop, take-profit
  5. Drawdown kontrolü (kill-switch)

KURALLAR:
  - Max 5 pozisyon, pozisyon başına max %20 sermaye
  - Stop-loss: ATR bazlı (2x ATR)
  - Trailing stop: %5+ kârda aktif, %2 trailing
  - Take-profit: %15 kâr → %50 sat, %25 kâr → tümünü sat
  - Kill-switch: %15 drawdown'da tüm pozisyonları kapat
  - BTC koruma: BTC SMA20 altında → yeni alış yapma

Kullanım:
  python coin_otonom_trader.py              # 7/24 otonom
  python coin_otonom_trader.py --dry-run    # Simülasyon
  python coin_otonom_trader.py --tara       # Tek tarama
  python coin_otonom_trader.py --durum      # Durum göster
"""

import json
import time
import os
import sys
import hmac
import hashlib
import logging
import argparse
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# ── Proje yapısı ──
PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

# ── Telegram Bildirim ──
def bildirim(mesaj, oncelik="normal"):
    """Telegram + log bildirim."""
    try:
        from bildirim import gonder
        gonder(f"[COIN] {mesaj}", oncelik)
    except Exception:
        pass

DATA_DIR = PROJECT_DIR / "data"
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

STATE_FILE = DATA_DIR / "coin_otonom_state.json"
TRADE_LOG = DATA_DIR / "coin_otonom_trades.json"
BRIDGE_FILE = DATA_DIR / "coin_otonom_bridge.json"

# ── Logging ──
logger = logging.getLogger("coin_otonom")
logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
logger.addHandler(_sh)
_fh = logging.FileHandler(LOG_DIR / "coin_otonom.log", encoding="utf-8")
_fh.setFormatter(_fmt)
logger.addHandler(_fh)

# ── Argümanlar ──
parser = argparse.ArgumentParser(description="ANKA Coin Otonom Trader")
parser.add_argument("--dry-run", action="store_true", help="Simülasyon modu")
parser.add_argument("--tara", action="store_true", help="Tek tarama")
parser.add_argument("--durum", action="store_true", help="Durum göster")
_args, _ = parser.parse_known_args()
DRY_RUN = _args.dry_run

# ══════════════════════════════════════════════════════════════
# PARAMETRELERİ (kullanıcı ayarlayabilir)
# ══════════════════════════════════════════════════════════════
class Config:
    """Tüm parametreler tek yerde — ileride UI'dan ayarlanabilir."""
    # Coin listesi — Top 25 likit coin
    COINS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
        "ATOMUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT",
        "APTUSDT", "SUIUSDT", "MATICUSDT", "FILUSDT",
        "RENDERUSDT", "INJUSDT", "FETUSDT",
        "TIAUSDT", "SEIUSDT", "WIFUSDT", "JUPUSDT", "ENAUSDT",
    ]
    # BTC koruma muafiyeti — BTC ve ETH her zaman alınabilir
    BTC_KORUMA_MUAF = ["BTCUSDT", "ETHUSDT"]

    # Risk parametreleri
    MAX_POZISYON = 5              # Aynı anda max pozisyon
    POZISYON_YUZDE = 15.0         # Sermayenin max %'si pozisyon başına
    MIN_ISLEM_USDT = 12.0         # Min işlem tutarı
    MAX_ISLEM_USDT = 500.0        # Max işlem tutarı

    # Sinyal parametreleri
    MIN_SKOR_AL = 65              # Min skor (alış) — rally zirvesi filtresi
    MIN_AJAN_ONAY = 2             # En az N ajan >= 60 olmalı
    DONGU_BASINA_MAX_ALIS = 2     # Tek tarama döngüsünde max alış (toplu giriş engeli)
    POZISYON_COOLDOWN_DK = 30     # Yeni pozisyon açmadan önce bekleme (min)

    # Stop / Take-profit — kripto volatilitesi için ayarlanmış
    STOP_LOSS_ATR_CARPAN = 3.5    # ATR x N stop-loss (2.0'dan gevşetildi)
    STOP_LOSS_VARSAYILAN_PCT = 7.0  # ATR yoksa fallback stop %
    TRAILING_BASLA_PCT = 3.0      # %3 kârda trailing aktif
    TRAILING_MESAFE_PCT = 2.0     # %2 trailing mesafe
    TAKE_PROFIT_1_PCT = 8.0       # %8'de yarısını sat (erken kâr koruma)
    TAKE_PROFIT_2_PCT = 15.0      # %15'te tümünü sat
    ACIL_STOP_PCT = -10.0         # %-10 acil çıkış

    # Kill-switch
    MAX_DRAWDOWN_PCT = 15.0       # %15 DD → tüm pozisyonları kapat

    # Tarama aralığı
    TARAMA_ARALIK_DK = 15         # Dakika

    # BTC koruma kalkanı
    BTC_KORUMA_AKTIF = True       # BTC düşüşte altcoin alma

    # Komisyon
    KOMISYON_PCT = 0.1            # %0.1 (Binance spot)

    @classmethod
    def dosyadan_yukle(cls, path=None):
        """JSON config dosyasından parametreleri yükle."""
        if path is None:
            path = DATA_DIR / "coin_config.json"
        if Path(path).exists():
            try:
                with open(path) as f:
                    cfg = json.load(f)
                for k, v in cfg.items():
                    if hasattr(cls, k):
                        setattr(cls, k, v)
                logger.info(f"Config yüklendi: {path}")
            except Exception as e:
                logger.warning(f"Config yükleme hatası: {e}")

    @classmethod
    def dosyaya_kaydet(cls, path=None):
        """Mevcut parametreleri JSON'a kaydet."""
        if path is None:
            path = DATA_DIR / "coin_config.json"
        cfg = {k: v for k, v in vars(cls).items()
               if not k.startswith("_") and not callable(v)}
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)


# Config'i yükle (varsa)
Config.dosyadan_yukle()


# ══════════════════════════════════════════════════════════════
# BİNANCE API CLIENT
# ══════════════════════════════════════════════════════════════
class BinanceClient:
    BASE_URL = "https://api.binance.com"

    def __init__(self):
        self.api_key = os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = os.environ.get("BINANCE_API_SECRET", "")
        self.timeout = 15

    def _sign(self, params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        sig = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    def _headers(self):
        return {"X-MBX-APIKEY": self.api_key}

    # ── Piyasa verisi ──
    def fiyat(self, symbol):
        try:
            r = requests.get(f"{self.BASE_URL}/api/v3/ticker/price",
                             params={"symbol": symbol}, timeout=self.timeout)
            return float(r.json()["price"])
        except Exception as e:
            logger.error(f"fiyat({symbol}): {e}")
            return 0.0

    def kline(self, symbol, interval="1h", limit=100):
        try:
            r = requests.get(f"{self.BASE_URL}/api/v3/klines",
                             params={"symbol": symbol, "interval": interval, "limit": limit},
                             timeout=self.timeout)
            df = pd.DataFrame(r.json(), columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "quote_vol", "trades", "buy_base", "buy_quote", "ignore"
            ])
            for col in ["Open", "High", "Low", "Close", "Volume", "quote_vol"]:
                df[col] = df[col].astype(float)
            df["time"] = pd.to_datetime(df["open_time"], unit="ms")
            df.set_index("time", inplace=True)
            return df
        except Exception as e:
            logger.error(f"kline({symbol}): {e}")
            return pd.DataFrame()

    def ticker_24h(self, symbol):
        try:
            r = requests.get(f"{self.BASE_URL}/api/v3/ticker/24hr",
                             params={"symbol": symbol}, timeout=self.timeout)
            return r.json()
        except Exception:
            return {}

    def derinlik(self, symbol, limit=20):
        try:
            r = requests.get(f"{self.BASE_URL}/api/v3/depth",
                             params={"symbol": symbol, "limit": limit}, timeout=self.timeout)
            return r.json()
        except Exception:
            return {}

    # ── Hesap ──
    def bakiye(self):
        try:
            params = {"timestamp": int(time.time() * 1000)}
            params = self._sign(params)
            r = requests.get(f"{self.BASE_URL}/api/v3/account",
                             headers=self._headers(), params=params, timeout=self.timeout)
            return r.json()
        except Exception as e:
            logger.error(f"bakiye(): {e}")
            return {}

    def usdt_bakiye(self):
        hesap = self.bakiye()
        for b in hesap.get("balances", []):
            if b["asset"] == "USDT":
                return float(b["free"])
        return 0.0

    def acik_pozisyonlar(self):
        """USDT dışındaki bakiyeleri döndür (LD* Earn tokenları hariç)."""
        hesap = self.bakiye()
        pozlar = []
        # LD prefix: Binance Flexible Earn tokenları (LDBNB, LDUSDT vb.) — trade edilemez
        skip_prefixes = ("LD",)
        skip_assets = ("USDT", "USD", "BUSD", "EUR", "TRY")
        for b in hesap.get("balances", []):
            asset = b["asset"]
            free = float(b["free"])
            locked = float(b["locked"])
            toplam = free + locked
            if toplam <= 0.0001:
                continue
            if asset in skip_assets:
                continue
            if any(asset.startswith(p) for p in skip_prefixes):
                continue
            pozlar.append({
                "asset": asset,
                "miktar": toplam,
                "free": free,
            })
        return pozlar

    def toplam_portfoy_degeri(self):
        """Toplam portföy = serbest USDT + pozisyonlar + Earn varlıkları."""
        toplam = 0.0
        hesap = self.bakiye()
        for b in hesap.get("balances", []):
            asset = b["asset"]
            miktar = float(b["free"]) + float(b["locked"])
            if miktar <= 0.0001:
                continue

            # USDT ve LD-USDT doğrudan ekle
            if asset in ("USDT", "LDUSDT"):
                toplam += miktar
                continue

            # LD prefix → Earn token, gerçek asset adını çıkar
            real_asset = asset[2:] if asset.startswith("LD") and len(asset) > 2 else asset

            # Özel/bilinmeyen tokenları atla
            if not real_asset.isascii() or not real_asset.isalpha():
                continue

            symbol = f"{real_asset}USDT"
            try:
                f = self.fiyat(symbol)
                if f > 0:
                    toplam += miktar * f
            except Exception:
                pass
        return toplam

    # ── Emir ──
    def market_al(self, symbol, quote_qty):
        """Market alış (USDT cinsinden miktar)."""
        if DRY_RUN:
            logger.info(f"[DRY-RUN] AL {symbol} ~${quote_qty:.2f}")
            return {"status": "DRY_RUN", "symbol": symbol, "quoteQty": quote_qty}
        try:
            params = {
                "symbol": symbol, "side": "BUY", "type": "MARKET",
                "quoteOrderQty": f"{quote_qty:.2f}",
                "timestamp": int(time.time() * 1000),
            }
            params = self._sign(params)
            r = requests.post(f"{self.BASE_URL}/api/v3/order",
                              headers=self._headers(), params=params, timeout=self.timeout)
            return r.json()
        except Exception as e:
            logger.error(f"market_al({symbol}): {e}")
            return {"error": str(e)}

    def market_sat(self, symbol, quantity):
        """Market satış (coin cinsinden miktar)."""
        if DRY_RUN:
            logger.info(f"[DRY-RUN] SAT {symbol} {quantity}")
            return {"status": "DRY_RUN", "symbol": symbol, "quantity": quantity}
        try:
            params = {
                "symbol": symbol, "side": "SELL", "type": "MARKET",
                "quantity": f"{quantity}",
                "timestamp": int(time.time() * 1000),
            }
            params = self._sign(params)
            r = requests.post(f"{self.BASE_URL}/api/v3/order",
                              headers=self._headers(), params=params, timeout=self.timeout)
            return r.json()
        except Exception as e:
            logger.error(f"market_sat({symbol}): {e}")
            return {"error": str(e)}


# ══════════════════════════════════════════════════════════════
# KRİPTO ANALİZ AJANLARI
# ══════════════════════════════════════════════════════════════

class TeknikAjan:
    """EMA, RSI, MACD, Bollinger — klasik teknik analiz."""

    def analiz(self, df):
        if df is None or len(df) < 50:
            return 0, "Veri yetersiz"

        c = df["Close"]
        puan, detay = 0, []

        # EMA cross
        ema9 = c.ewm(span=9).mean()
        ema21 = c.ewm(span=21).mean()
        if float(ema9.iloc[-1]) > float(ema21.iloc[-1]):
            puan += 20
            detay.append("EMA9>21")
            # Golden cross (yeni kesişme)
            if float(ema9.iloc[-2]) <= float(ema21.iloc[-2]):
                puan += 10
                detay.append("CROSS!")

        # RSI — erken momentum ödüllendirme, geç girişi cezalandırma
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        rsi = float(100 - (100 / (1 + rs.iloc[-1])))
        if 30 <= rsi < 45:
            # Dip bölgesi — toparlanma başlangıcı, yüksek ödül
            puan += 25
            detay.append(f"RSI:{rsi:.0f} DİP_FIRSAT")
        elif 45 <= rsi < 60:
            # Erken momentum — ideal giriş noktası
            puan += 20
            detay.append(f"RSI:{rsi:.0f}")
        elif 60 <= rsi < 65:
            # Momentum devam ediyor — nötr, ödül yok
            detay.append(f"RSI:{rsi:.0f} NÖTR")
        elif 65 <= rsi < 70:
            # Tepe alanı — ceza
            puan -= 10
            detay.append(f"RSI:{rsi:.0f} TEPE")
        elif rsi >= 70:
            # Aşırı alım — muhtemelen patlamış, sert ceza
            puan -= 25
            detay.append(f"RSI:{rsi:.0f} AŞIRI_ALIM")

        # MACD
        macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        signal = macd.ewm(span=9).mean()
        hist = macd - signal
        if float(hist.iloc[-1]) > 0 and float(hist.iloc[-1]) > float(hist.iloc[-2]):
            puan += 20
            detay.append("MACD+")

        # Bollinger sıkışma
        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        bb_width = float(4 * std20.iloc[-1] / (sma20.iloc[-1] + 1e-10) * 100)
        if bb_width < 4:
            puan += 15
            detay.append(f"BB_SIKISMA:{bb_width:.1f}%")

        # Trend gücü: fiyat SMA50 üstünde
        sma50 = c.rolling(min(50, len(c))).mean()
        if float(c.iloc[-1]) > float(sma50.iloc[-1]):
            puan += 15
            detay.append("SMA50+")

        return min(100, max(0, puan)), " ".join(detay)


class HacimAjan:
    """Hacim patlaması, OBV, alış-satış baskısı."""

    def analiz(self, df):
        if df is None or len(df) < 20:
            return 0, "Veri yetersiz"

        v = df["Volume"]
        c = df["Close"]
        puan, detay = 0, []

        # Hacim oranı
        vol_sma = v.rolling(20).mean()
        vol_oran = float(v.iloc[-1] / (vol_sma.iloc[-1] + 1e-10))
        if vol_oran >= 3.0:
            puan += 35
            detay.append(f"HAC:x{vol_oran:.1f}!!")
        elif vol_oran >= 1.8:
            puan += 25
            detay.append(f"HAC:x{vol_oran:.1f}")
        elif vol_oran >= 1.3:
            puan += 10
            detay.append(f"HAC:x{vol_oran:.1f}")

        # OBV trendi
        obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
        obv_sma = obv.rolling(20).mean()
        if float(obv.iloc[-1]) > float(obv_sma.iloc[-1]):
            puan += 25
            detay.append("OBV+")

        # Quote volume (USDT hacim) — büyük oyuncu tespiti
        if "quote_vol" in df.columns:
            qv = df["quote_vol"]
            qv_oran = float(qv.iloc[-1] / (qv.rolling(20).mean().iloc[-1] + 1e-10))
            if qv_oran >= 2.5:
                puan += 20
                detay.append(f"WHALE:x{qv_oran:.1f}")

        # Kapanış gücü (close/high)
        kap_gucu = float(c.iloc[-1] / (df["High"].iloc[-1] + 1e-10))
        if kap_gucu >= 0.98:
            puan += 20
            detay.append(f"KAP:{kap_gucu:.3f}")

        return min(100, max(0, puan)), " ".join(detay)


class MakroAjan:
    """BTC trend, piyasa korelasyonu, genel sentiment."""

    def __init__(self, client):
        self.client = client
        self._btc_cache = None
        self._btc_cache_time = 0

    def _btc_veri(self):
        """BTC verisini cache'le (5 dk)."""
        now = time.time()
        if self._btc_cache is not None and now - self._btc_cache_time < 300:
            return self._btc_cache
        self._btc_cache = self.client.kline("BTCUSDT", "1h", 100)
        self._btc_cache_time = now
        return self._btc_cache

    def analiz(self, symbol=None):
        btc_df = self._btc_veri()
        if btc_df is None or len(btc_df) < 20:
            return 50, "BTC veri yok"

        c = btc_df["Close"]
        puan, detay = 50, []

        # BTC SMA20 trend
        sma20 = float(c.rolling(20).mean().iloc[-1])
        son = float(c.iloc[-1])
        if son > sma20:
            puan += 20
            detay.append("BTC>SMA20")
        else:
            puan -= 25
            detay.append("BTC<SMA20")

        # BTC momentum (24h)
        if len(c) >= 24:
            chg_24h = (float(c.iloc[-1]) / float(c.iloc[-24]) - 1) * 100
            if chg_24h > 3:
                puan += 15
                detay.append(f"BTC24h:+{chg_24h:.1f}%")
            elif chg_24h < -3:
                puan -= 15
                detay.append(f"BTC24h:{chg_24h:.1f}%")

        # BTC volatilite (düşük vol = sıkışma, potansiyel hareket)
        btc_atr = self._atr(btc_df)
        if btc_atr is not None:
            btc_atr_pct = btc_atr / son * 100
            if btc_atr_pct < 1.5:
                puan += 10
                detay.append(f"BTC_SIKISMA:{btc_atr_pct:.1f}%")

        return max(0, min(100, puan)), " ".join(detay) if detay else "Nötr"

    def btc_koruma_aktif_mi(self):
        """BTC SMA20 altındaysa True → altcoin alma."""
        if not Config.BTC_KORUMA_AKTIF:
            return False
        btc_df = self._btc_veri()
        if btc_df is None or len(btc_df) < 20:
            return False
        c = btc_df["Close"]
        sma20 = float(c.rolling(20).mean().iloc[-1])
        return float(c.iloc[-1]) < sma20

    @staticmethod
    def _atr(df, period=14):
        if len(df) < period + 1:
            return None
        h, l, c = df["High"], df["Low"], df["Close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])


class LikiditeAjan:
    """Spread ve emir defteri derinliği analizi — kripto'ya özgü."""

    def __init__(self, client):
        self.client = client

    def analiz(self, symbol):
        puan, detay = 50, []

        # Emir defteri
        depth = self.client.derinlik(symbol, 20)
        if not depth or "bids" not in depth:
            return 50, "Derinlik yok"

        bids = depth.get("bids", [])
        asks = depth.get("asks", [])

        if bids and asks:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid = (best_bid + best_ask) / 2
            spread_pct = (best_ask - best_bid) / mid * 100

            if spread_pct < 0.05:
                puan += 25
                detay.append(f"Spread:{spread_pct:.3f}% SÜPER")
            elif spread_pct < 0.1:
                puan += 15
                detay.append(f"Spread:{spread_pct:.3f}%")
            elif spread_pct > 0.5:
                puan -= 20
                detay.append(f"Spread:{spread_pct:.2f}% GENİŞ")

            # Alış/satış baskısı (bid volume vs ask volume)
            bid_vol = sum(float(b[1]) for b in bids[:10])
            ask_vol = sum(float(a[1]) for a in asks[:10])
            if bid_vol > 0 and ask_vol > 0:
                pressure = bid_vol / ask_vol
                if pressure > 1.5:
                    puan += 20
                    detay.append(f"ALIŞ_BASINCI:x{pressure:.1f}")
                elif pressure < 0.6:
                    puan -= 15
                    detay.append(f"SATIŞ_BASINCI:x{1/pressure:.1f}")

        return max(0, min(100, puan)), " ".join(detay) if detay else "OK"


# ══════════════════════════════════════════════════════════════
# RİSK YÖNETİMİ
# ══════════════════════════════════════════════════════════════

class CoinRiskYoneticisi:
    """Kripto için özelleştirilmiş risk yönetimi."""

    def __init__(self, baslangic_usdt=0):
        self.baslangic = baslangic_usdt
        self.peak = baslangic_usdt
        self.pozisyonlar = {}  # symbol → {giris_fiyat, miktar, stop, trailing_high, tp1_yapildi}

    def drawdown_kontrol(self, mevcut_usdt):
        self.peak = max(self.peak, mevcut_usdt)
        if self.peak <= 0:
            return 0, "normal"
        dd = (self.peak - mevcut_usdt) / self.peak * 100
        if dd >= Config.MAX_DRAWDOWN_PCT:
            return dd, "KILL"
        elif dd >= Config.MAX_DRAWDOWN_PCT * 0.7:
            return dd, "DİKKAT"
        return dd, "normal"

    def pozisyon_boyutu(self, usdt_bakiye):
        """Pozisyon başına USDT miktarı."""
        poz_usdt = usdt_bakiye * (Config.POZISYON_YUZDE / 100)
        return max(Config.MIN_ISLEM_USDT, min(Config.MAX_ISLEM_USDT, poz_usdt))

    def stop_loss_hesapla(self, fiyat, atr):
        """ATR bazlı stop-loss. ATR çok dar ise varsayılan %'ye düş."""
        varsayilan = fiyat * (1 - Config.STOP_LOSS_VARSAYILAN_PCT / 100)
        if atr is None or atr <= 0:
            return varsayilan
        atr_stop = fiyat - (atr * Config.STOP_LOSS_ATR_CARPAN)
        # ATR çok dar kalırsa (kripto için %1.5'tan az) varsayılanı kullan
        if (fiyat - atr_stop) / fiyat < 0.015:
            return varsayilan
        return atr_stop

    def pozisyon_ekle(self, symbol, giris_fiyat, miktar, atr=None):
        stop = self.stop_loss_hesapla(giris_fiyat, atr)
        self.pozisyonlar[symbol] = {
            "giris_fiyat": giris_fiyat,
            "miktar": miktar,
            "stop_loss": stop,
            "trailing_high": giris_fiyat,
            "tp1_yapildi": False,
            "giris_zaman": datetime.now().isoformat(),
        }

    def pozisyon_sil(self, symbol):
        self.pozisyonlar.pop(symbol, None)

    def trailing_guncelle(self, symbol, son_fiyat):
        """Trailing stop güncelle. Dönen: (aksiyon, detay)"""
        poz = self.pozisyonlar.get(symbol)
        if not poz:
            return None, None

        giris = poz["giris_fiyat"]
        pl_pct = (son_fiyat / giris - 1) * 100

        # Trailing high güncelle
        if son_fiyat > poz["trailing_high"]:
            poz["trailing_high"] = son_fiyat

        # STOP-LOSS
        if son_fiyat <= poz["stop_loss"]:
            return "STOP_LOSS", f"Fiyat:{son_fiyat:.4f} <= Stop:{poz['stop_loss']:.4f}"

        # ACİL ÇIKIŞ
        if pl_pct <= Config.ACIL_STOP_PCT:
            return "ACIL_CIKIS", f"PL:{pl_pct:+.1f}%"

        # TAKE-PROFIT 2 (tam çıkış)
        if pl_pct >= Config.TAKE_PROFIT_2_PCT:
            return "TP_FULL", f"PL:+{pl_pct:.1f}%"

        # TAKE-PROFIT 1 (yarısını sat)
        if pl_pct >= Config.TAKE_PROFIT_1_PCT and not poz["tp1_yapildi"]:
            poz["tp1_yapildi"] = True
            return "TP_HALF", f"PL:+{pl_pct:.1f}%"

        # TRAİLİNG STOP (aktifse)
        if pl_pct >= Config.TRAILING_BASLA_PCT:
            trail_stop = poz["trailing_high"] * (1 - Config.TRAILING_MESAFE_PCT / 100)
            if son_fiyat <= trail_stop:
                return "TRAILING_STOP", f"Trail:{trail_stop:.4f} High:{poz['trailing_high']:.4f}"

        return None, None


# ══════════════════════════════════════════════════════════════
# ANA MOTOR
# ══════════════════════════════════════════════════════════════

class CoinOtonomTrader:
    """7/24 otonom kripto trading motoru."""

    def __init__(self):
        self.client = BinanceClient()
        self.teknik = TeknikAjan()
        self.hacim = HacimAjan()
        self.makro = MakroAjan(self.client)
        self.likidite = LikiditeAjan(self.client)
        self.risk = CoinRiskYoneticisi()
        self.cycle_count = 0

    def _atr(self, df, period=14):
        if df is None or len(df) < period + 1:
            return None
        h, l, c = df["High"], df["Low"], df["Close"]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    def trade_log(self, kayit):
        try:
            trades = []
            if TRADE_LOG.exists():
                with open(TRADE_LOG) as f:
                    trades = json.load(f)
            trades.append(kayit)
            trades = trades[-1000:]
            with open(TRADE_LOG, "w") as f:
                json.dump(trades, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Trade log: {e}")

    POZ_FILE = DATA_DIR / "coin_pozisyonlar_aktif.json"

    def _pozisyon_yukle(self):
        """Restart sonrası kayıtlı pozisyonları yükle."""
        if self.POZ_FILE.exists():
            try:
                with open(self.POZ_FILE) as f:
                    saved = json.load(f)
                if saved:
                    self.risk.pozisyonlar = saved
                    logger.info(f"Kayıtlı pozisyonlar yüklendi: {list(saved.keys())}")
            except Exception as e:
                logger.warning(f"Pozisyon yükleme hatası: {e}")

    def _pozisyon_kaydet(self):
        """Aktif pozisyonları dosyaya kaydet."""
        try:
            with open(self.POZ_FILE, "w") as f:
                json.dump(self.risk.pozisyonlar, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"Pozisyon kaydetme hatası: {e}")

    def state_kaydet(self, ekstra=None):
        state = {
            "zaman": datetime.now().isoformat(),
            "cycle": self.cycle_count,
            "pozisyonlar": self.risk.pozisyonlar,
            "son_tarama": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "toplam_trade": 0,
            "toplam_kar": 0,
            "dry_run": DRY_RUN,
        }
        if ekstra:
            state.update(ekstra)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)
        # Pozisyonları ayrıca kaydet
        self._pozisyon_kaydet()

    # ── TARAMA ──
    def tara(self):
        """Tüm coinleri tara, skorla."""
        logger.info(f"TARAMA BAŞLIYOR — {len(Config.COINS)} coin")

        sonuclar = []
        for symbol in Config.COINS:
            try:
                df = self.client.kline(symbol, "1h", 100)
                if df is None or len(df) < 50:
                    continue

                # 4 ajan analizi
                tek_p, tek_d = self.teknik.analiz(df)
                hac_p, hac_d = self.hacim.analiz(df)
                mak_p, mak_d = self.makro.analiz(symbol)
                lik_p, lik_d = self.likidite.analiz(symbol)

                # Ağırlıklı skor
                skor = tek_p * 0.35 + hac_p * 0.25 + mak_p * 0.25 + lik_p * 0.15
                puanlar = {"TEK": tek_p, "HAC": hac_p, "MAK": mak_p, "LIK": lik_p}
                onay = sum(1 for p in [tek_p, hac_p, mak_p] if p >= 60)

                fiyat = float(df["Close"].iloc[-1])
                atr = self._atr(df)
                atr_pct = (atr / fiyat * 100) if atr and fiyat else 0

                # 24h değişim
                chg_24h = (fiyat / float(df["Close"].iloc[-24]) - 1) * 100 if len(df) >= 24 else 0

                sonuclar.append({
                    "symbol": symbol, "fiyat": fiyat, "skor": round(skor, 1),
                    "puanlar": puanlar, "onay": onay,
                    "atr": atr, "atr_pct": round(atr_pct, 2),
                    "chg_24h": round(chg_24h, 1),
                    "detay": f"{tek_d} | {hac_d}",
                })

                karar = "AL" if skor >= Config.MIN_SKOR_AL and onay >= Config.MIN_AJAN_ONAY else ""
                icon = ">>>" if karar else "   "
                logger.info(f"  {icon} {symbol:10s} ${fiyat:>10,.2f} | "
                            f"Skor:{skor:5.1f} | TEK:{tek_p:2.0f} HAC:{hac_p:2.0f} "
                            f"MAK:{mak_p:2.0f} LIK:{lik_p:2.0f} | {karar}")

                time.sleep(0.2)  # Rate limit

            except Exception as e:
                logger.warning(f"{symbol} tarama hatası: {e}")

        sonuclar.sort(key=lambda x: x["skor"], reverse=True)

        # Bridge'e yaz
        try:
            with open(BRIDGE_FILE, "w") as f:
                json.dump({"zaman": datetime.now().isoformat(), "sonuclar": sonuclar},
                          f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return sonuclar

    # ── OTONOM ALIŞ ──
    def otonom_alis(self, sonuclar):
        """Skor yeterli coinlerden otomatik alış."""
        usdt = self.client.usdt_bakiye()
        toplam = self.client.toplam_portfoy_degeri()
        logger.info(f"USDT bakiye: ${usdt:.2f} | Toplam portföy: ${toplam:.2f}")

        # Kill-switch — TOPLAM portföy değerine göre (serbest USDT değil!)
        dd, dd_durum = self.risk.drawdown_kontrol(toplam)
        if dd_durum == "KILL":
            logger.warning(f"KILL-SWITCH! DD: %{dd:.1f} — İŞLEM DURDURULDU")
            bildirim(f"🚨 COIN KILL-SWITCH! Drawdown: %{dd:.1f} — Tüm işlemler durduruldu!", "acil")
            return

        # BTC koruma (BTC/ETH hariç — onlar her zaman alınabilir)
        btc_koruma = self.makro.btc_koruma_aktif_mi()
        if btc_koruma:
            logger.info("BTC KORUMA AKTİF — BTC SMA20 altında, sadece BTC/ETH alınabilir")

        # Mevcut pozisyon sayısı
        mevcut_poz = len(self.risk.pozisyonlar)
        bos_slot = Config.MAX_POZISYON - mevcut_poz

        if bos_slot <= 0:
            logger.info(f"Max pozisyon ({Config.MAX_POZISYON}) dolu")
            return

        # Cooldown — en son pozisyon açılışından bu yana yeterli süre geçti mi?
        son_acilis = None
        for poz in self.risk.pozisyonlar.values():
            try:
                z = datetime.fromisoformat(poz.get("giris_zaman", ""))
                if son_acilis is None or z > son_acilis:
                    son_acilis = z
            except Exception:
                pass
        if son_acilis is not None:
            dakika = (datetime.now() - son_acilis).total_seconds() / 60
            if dakika < Config.POZISYON_COOLDOWN_DK:
                kalan = Config.POZISYON_COOLDOWN_DK - dakika
                logger.info(f"⏳ Cooldown — son pozisyondan bu yana {dakika:.1f}dk, {kalan:.1f}dk bekleniyor")
                return

        # Bu döngüde kaç alış yapıldı — toplu giriş engeli
        dongu_alis = 0

        for s in sonuclar:
            if bos_slot <= 0:
                break
            if dongu_alis >= Config.DONGU_BASINA_MAX_ALIS:
                logger.info(f"Döngü alış limiti ({Config.DONGU_BASINA_MAX_ALIS}) doldu, kalan fırsatlar sonraki taramaya")
                break

            symbol = s["symbol"]
            skor = s["skor"]
            onay = s["onay"]
            fiyat = s["fiyat"]

            # Filtreler
            if skor < Config.MIN_SKOR_AL:
                continue
            if onay < Config.MIN_AJAN_ONAY:
                continue
            if symbol in self.risk.pozisyonlar:
                continue
            # BTC koruma: altcoinleri engelle, BTC/ETH geçebilir
            if btc_koruma and symbol not in Config.BTC_KORUMA_MUAF:
                logger.info(f"  ⛔ {symbol} BTC koruma — atlandı")
                continue

            # Pozisyon boyutu
            islem_usdt = self.risk.pozisyon_boyutu(usdt)
            if usdt < islem_usdt or islem_usdt < Config.MIN_ISLEM_USDT:
                logger.info(f"Bakiye yetersiz: ${usdt:.2f}")
                break

            # ALIŞ
            logger.info(f"💰 ALIŞ: {symbol} | ~${islem_usdt:.0f} | Skor:{skor} | {s.get('detay','')}")
            sonuc = self.client.market_al(symbol, islem_usdt)

            if "error" not in sonuc:
                # Gerçekleşen fiyat ve miktar
                fills = sonuc.get("fills", [])
                if fills:
                    avg_price = sum(float(f["price"]) * float(f["qty"]) for f in fills) / \
                                sum(float(f["qty"]) for f in fills)
                    total_qty = sum(float(f["qty"]) for f in fills)
                else:
                    avg_price = fiyat
                    total_qty = islem_usdt / fiyat

                self.risk.pozisyon_ekle(symbol, avg_price, total_qty, s.get("atr"))
                usdt -= islem_usdt
                bos_slot -= 1
                dongu_alis += 1

                self.trade_log({
                    "zaman": datetime.now().isoformat(), "tip": "AL", "symbol": symbol,
                    "miktar": total_qty, "fiyat": avg_price, "usdt": islem_usdt,
                    "skor": skor, "mod": "DRY" if DRY_RUN else "CANLI",
                })
                logger.info(f"  ✅ {symbol} ALINDI: {total_qty:.6f} @ ${avg_price:.4f}")
                bildirim(f"💰 ALIŞ: {symbol} ${islem_usdt:.0f} @ ${avg_price:.4f} | Skor:{skor}")
            else:
                logger.error(f"  ❌ {symbol} ALIŞ HATASI: {sonuc}")

            time.sleep(0.5)

    # ── POZİSYON TAKİBİ ──
    def pozisyon_kontrol(self):
        """Tüm açık pozisyonları kontrol et — stop/trailing/TP."""
        if not self.risk.pozisyonlar:
            return

        logger.info(f"POZİSYON KONTROL — {len(self.risk.pozisyonlar)} pozisyon")

        satirlar = list(self.risk.pozisyonlar.keys())
        for symbol in satirlar:
            poz = self.risk.pozisyonlar.get(symbol)
            if not poz:
                continue

            son_fiyat = self.client.fiyat(symbol)
            if son_fiyat <= 0:
                continue

            giris = poz["giris_fiyat"]
            pl_pct = (son_fiyat / giris - 1) * 100

            aksiyon, detay = self.risk.trailing_guncelle(symbol, son_fiyat)

            if aksiyon in ("STOP_LOSS", "ACIL_CIKIS", "TP_FULL", "TRAILING_STOP"):
                # TAM SATIŞ
                miktar = poz["miktar"]
                logger.info(f"  🔴 {aksiyon}: {symbol} | PL:{pl_pct:+.1f}% | {detay}")
                sonuc = self.client.market_sat(symbol, self._format_qty(symbol, miktar))

                oncelik = "acil" if aksiyon in ("STOP_LOSS", "ACIL_CIKIS") else "onemli"
                bildirim(f"🔴 {aksiyon}: {symbol} | PL:{pl_pct:+.1f}% | {detay}", oncelik)

                self.trade_log({
                    "zaman": datetime.now().isoformat(), "tip": "SAT", "symbol": symbol,
                    "miktar": miktar, "fiyat": son_fiyat, "pl_pct": round(pl_pct, 2),
                    "sebep": aksiyon, "mod": "DRY" if DRY_RUN else "CANLI",
                })
                self.risk.pozisyon_sil(symbol)

            elif aksiyon == "TP_HALF":
                # YARISINI SAT
                yarim = poz["miktar"] / 2
                logger.info(f"  🟡 TP_HALF: {symbol} | PL:+{pl_pct:.1f}% | Yarısı satılıyor")
                sonuc = self.client.market_sat(symbol, self._format_qty(symbol, yarim))

                bildirim(f"🟡 TP1: {symbol} | PL:+{pl_pct:.1f}% | Yarısı satıldı, kalan trailing'e", "onemli")

                poz["miktar"] = poz["miktar"] - yarim
                # Stop-loss'u girişe çek (breakeven)
                poz["stop_loss"] = giris * 1.005

                self.trade_log({
                    "zaman": datetime.now().isoformat(), "tip": "SAT_YARIM", "symbol": symbol,
                    "miktar": yarim, "fiyat": son_fiyat, "pl_pct": round(pl_pct, 2),
                    "sebep": "TP_HALF", "mod": "DRY" if DRY_RUN else "CANLI",
                })

            else:
                # Normal durum — logla
                icon = "🟢" if pl_pct > 0 else "🔴"
                logger.info(f"  {icon} {symbol}: ${son_fiyat:.4f} | PL:{pl_pct:+.1f}% | "
                            f"Stop:{poz['stop_loss']:.4f}")

            time.sleep(0.3)

    def _format_qty(self, symbol, qty):
        """Binance lot size kurallarına uygun formatlama."""
        # BTC, ETH gibi büyük coinler için farklı precision
        if "BTC" in symbol:
            return f"{qty:.5f}"
        elif "ETH" in symbol or "BNB" in symbol:
            return f"{qty:.4f}"
        else:
            return f"{qty:.2f}"

    # ── ANA DÖNGÜ ──
    def calistir(self):
        """7/24 otonom döngü."""
        logger.info("=" * 60)
        logger.info("🚀 ANKA COIN OTONOM TRADER")
        logger.info(f"  Mod: {'DRY-RUN' if DRY_RUN else 'CANLI'}")
        logger.info(f"  Coins: {len(Config.COINS)}")
        logger.info(f"  Max Poz: {Config.MAX_POZISYON} | Min Skor: {Config.MIN_SKOR_AL}")
        logger.info(f"  Stop: {Config.STOP_LOSS_ATR_CARPAN}x ATR | Trail: %{Config.TRAILING_BASLA_PCT}")
        logger.info(f"  Kill-switch: %{Config.MAX_DRAWDOWN_PCT} DD")
        logger.info(f"  Tarama: Her {Config.TARAMA_ARALIK_DK} dakika")
        logger.info("=" * 60)

        # Kayıtlı pozisyonları yükle (restart dayanıklılığı)
        self._pozisyon_yukle()

        # Başlangıç bakiye — TOPLAM portföy (USDT + pozisyon değerleri)
        usdt = self.client.usdt_bakiye()
        toplam = self.client.toplam_portfoy_degeri()
        if toplam > 0:
            self.risk.baslangic = toplam
            self.risk.peak = toplam
            logger.info(f"Başlangıç → USDT: ${usdt:.2f} | Toplam Portföy: ${toplam:.2f}")
        elif usdt > 0:
            self.risk.baslangic = usdt
            self.risk.peak = usdt
            logger.info(f"Başlangıç USDT: ${usdt:.2f}")
        else:
            logger.warning("Bakiye alınamadı veya $0 — API key ve Binance bakiyeni kontrol et")

        bildirim(f"Coin Trader başladı! {'DRY-RUN' if DRY_RUN else 'CANLI'} | "
                 f"USDT: ${usdt:.2f} | Pozisyon: {len(self.risk.pozisyonlar)}")

        while True:
            try:
                self.cycle_count += 1
                logger.info(f"\n{'='*40} CYCLE #{self.cycle_count} {'='*40}")

                # 1. Tara
                sonuclar = self.tara()

                # 2. Otonom alış
                self.otonom_alis(sonuclar)

                # 3. Pozisyon kontrol
                self.pozisyon_kontrol()

                # 4. State kaydet
                self.state_kaydet({"sonuclar_ozet": [
                    {"s": s["symbol"], "skor": s["skor"], "f": s["fiyat"]}
                    for s in sonuclar[:5]
                ]})

                logger.info(f"Sonraki tarama: {Config.TARAMA_ARALIK_DK} dk sonra")

            except Exception as e:
                logger.error(f"Döngü hatası: {e}", exc_info=True)

            time.sleep(Config.TARAMA_ARALIK_DK * 60)

    def durum_goster(self):
        """Mevcut durumu göster."""
        print("\n🔍 ANKA COIN OTONOM TRADER DURUMU")
        print("=" * 50)
        print(f"Mod: {'DRY-RUN' if DRY_RUN else 'CANLI'}")

        usdt = self.client.usdt_bakiye()
        toplam = self.client.toplam_portfoy_degeri()
        print(f"USDT: ${usdt:.2f} | Toplam Portföy: ${toplam:.2f}")

        dd, dd_durum = self.risk.drawdown_kontrol(toplam)
        print(f"Drawdown: %{dd:.1f} ({dd_durum})")

        pozlar = self.client.acik_pozisyonlar()
        if pozlar:
            print(f"\nAçık Pozisyonlar ({len(pozlar)}):")
            for p in pozlar:
                asset = p["asset"]
                symbol = f"{asset}USDT"
                fiyat = self.client.fiyat(symbol)
                deger = p["miktar"] * fiyat
                print(f"  {asset}: {p['miktar']:.6f} | ${fiyat:.4f} | ~${deger:.2f}")
        else:
            print("\nAçık pozisyon yok")

        if TRADE_LOG.exists():
            with open(TRADE_LOG) as f:
                trades = json.load(f)
            bugun = datetime.now().strftime("%Y-%m-%d")
            bugun_t = [t for t in trades if t.get("zaman", "").startswith(bugun)]
            if bugun_t:
                print(f"\nBugünkü işlemler ({len(bugun_t)}):")
                for t in bugun_t[-10:]:
                    print(f"  {t.get('tip')} {t.get('symbol')} {t.get('miktar',0):.6f} "
                          f"@ ${t.get('fiyat',0):.4f} | {t.get('mod')}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    trader = CoinOtonomTrader()

    if _args.tara:
        trader.tara()
    elif _args.durum:
        trader.durum_goster()
    else:
        trader.calistir()
