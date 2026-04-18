"""
COIN TRADER -- ANKA'nin Kripto Kardesi
==========================================
Binance API ile 7/24 otonom kripto trading.
ANKA ile ayni mimari: 5 ajan + karar verici + panel kurallari.

BIST (ANKA): 09:10-18:00 calisir
COIN: 7/24 calisir -- gece bile!

Kullanim:
  python coin_trader.py --tara          # Tek tarama
  python coin_trader.py --bot           # 7/24 otonom
  python coin_trader.py --durum         # Durum kontrol
  python coin_trader.py --dry-run       # Simulasyon (emir gondermez)
  python coin_trader.py --roket         # Roket tarama
  python coin_trader.py --roket-loop    # Surekli roket tarama
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
from datetime import datetime
from pathlib import Path

# ── .env yukleme ──────────────────────────────────────────────
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).parent
load_dotenv(PROJECT_DIR / ".env")

DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

COIN_BRIDGE = DATA_DIR / "coin_bridge.json"
COIN_STATE = DATA_DIR / "coin_state.json"
COIN_LOG = DATA_DIR / "coin_log.json"

# ── Logging ───────────────────────────────────────────────────
logger = logging.getLogger("coin_trader")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

_sh = logging.StreamHandler()
_sh.setFormatter(_fmt)
logger.addHandler(_sh)

_fh = logging.FileHandler(LOG_DIR / "coin_trader.log", encoding="utf-8")
_fh.setFormatter(_fmt)
logger.addHandler(_fh)

REQUEST_TIMEOUT = 15  # saniye


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

    # ── PIYASA VERISI (API key gerekmez) ──────────
    def fiyat(self, symbol="BTCUSDT"):
        """Anlik fiyat. Hata durumunda 0.0 doner."""
        try:
            r = requests.get(
                f"{self.BASE_URL}/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=REQUEST_TIMEOUT,
            )
            return float(r.json()["price"])
        except Exception as e:
            logger.error(f"fiyat({symbol}) hatasi: {e}")
            return 0.0

    def kline(self, symbol="BTCUSDT", interval="1h", limit=100):
        """Mum verisi cek. Hata durumunda bos DataFrame doner."""
        import pandas as pd
        try:
            r = requests.get(
                f"{self.BASE_URL}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": limit},
                timeout=REQUEST_TIMEOUT,
            )
            data = r.json()
            df = pd.DataFrame(data, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume",
                "close_time", "quote_vol", "trades", "buy_base", "buy_quote", "ignore"
            ])
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                df[col] = df[col].astype(float)
            df["time"] = pd.to_datetime(df["open_time"], unit="ms")
            df.set_index("time", inplace=True)
            return df
        except Exception as e:
            logger.error(f"kline({symbol}) hatasi: {e}")
            return pd.DataFrame()

    def ticker_24h(self, symbol="BTCUSDT"):
        """24 saatlik ozet. Hata durumunda bos dict doner."""
        try:
            r = requests.get(
                f"{self.BASE_URL}/api/v3/ticker/24hr",
                params={"symbol": symbol},
                timeout=REQUEST_TIMEOUT,
            )
            return r.json()
        except Exception as e:
            logger.error(f"ticker_24h({symbol}) hatasi: {e}")
            return {}

    def derinlik(self, symbol="BTCUSDT", limit=10):
        """Emir defteri (LOB). Hata durumunda bos dict doner."""
        try:
            r = requests.get(
                f"{self.BASE_URL}/api/v3/depth",
                params={"symbol": symbol, "limit": limit},
                timeout=REQUEST_TIMEOUT,
            )
            return r.json()
        except Exception as e:
            logger.error(f"derinlik({symbol}) hatasi: {e}")
            return {}

    # ── HESAP & EMIR (API key gerekir) ─────────────
    def bakiye(self):
        """Hesap bakiyesi. Hata durumunda bos dict doner."""
        try:
            params = {"timestamp": int(time.time() * 1000)}
            params = self._sign(params)
            r = requests.get(
                f"{self.BASE_URL}/api/v3/account",
                headers=self._headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            return r.json()
        except Exception as e:
            logger.error(f"bakiye() hatasi: {e}")
            return {}

    def alis(self, symbol, miktar, fiyat=None):
        """
        Alis emri.
        fiyat=None -> Piyasa emri
        fiyat=deger -> Limit emri
        Hata durumunda error dict doner.
        """
        try:
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
            r = requests.post(
                f"{self.BASE_URL}/api/v3/order",
                headers=self._headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            return r.json()
        except Exception as e:
            logger.error(f"alis({symbol}, {miktar}) hatasi: {e}")
            return {"error": str(e)}

    def satis(self, symbol, miktar, fiyat=None):
        """Satis emri. Hata durumunda error dict doner."""
        try:
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
            r = requests.post(
                f"{self.BASE_URL}/api/v3/order",
                headers=self._headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            return r.json()
        except Exception as e:
            logger.error(f"satis({symbol}, {miktar}) hatasi: {e}")
            return {"error": str(e)}


# ================================================================
# KRIPTO AJANLARI (ANKA ile ayni mimari)
# ================================================================

class CryptoTechnoAgent:
    """Teknik analiz -- EMA, RSI, MACD, Bollinger."""
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
            detay.append("EMA+")

        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = float(100 - (100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-10))))
        if 50 < rsi < 70:
            puan += 20
            detay.append(f"RSI:{rsi:.0f}+")

        macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        signal = macd.ewm(span=9).mean()
        if float(macd.iloc[-1]) > float(signal.iloc[-1]):
            puan += 20
            detay.append("MACD+")

        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        boll_width = float(4 * std20.iloc[-1] / sma20.iloc[-1] * 100) if sma20.iloc[-1] > 0 else 0
        if boll_width < 5:
            puan += 15
            detay.append("SIKISMA")

        vol = df['Volume']
        vol_oran = float(vol.iloc[-1] / vol.rolling(20).mean().iloc[-1]) if vol.rolling(20).mean().iloc[-1] > 0 else 0
        if vol_oran > 1.5:
            puan += 20
            detay.append(f"Hacim:x{vol_oran:.1f}+")

        return min(100, puan), " ".join(detay)


class CryptoMacroAgent:
    """Kripto makro -- BTC dominans, Fear & Greed, funding rate."""
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
                    detay.append("BTC trend+")
                else:
                    puan -= 20
                    detay.append("BTC trend-")

                chg_24h = float((c.iloc[-1] / c.iloc[-2] - 1) * 100)
                if chg_24h > 2:
                    puan += 10
                    detay.append(f"BTC:{chg_24h:+.1f}%+")
                elif chg_24h < -2:
                    puan -= 10
                    detay.append(f"BTC:{chg_24h:+.1f}%-")
        except Exception as e:
            logger.warning(f"CryptoMacroAgent analiz hatasi: {e}")

        return max(0, min(100, puan)), " ".join(detay) if detay else "Notr"


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
            detay.append(f"Hacim:x{vol_oran:.1f}!!")
        elif vol_oran >= 1.5:
            puan += 25
            detay.append(f"Hacim:x{vol_oran:.1f}+")

        # OBV
        import numpy as np
        obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
        obv_sma = obv.rolling(20).mean()
        if float(obv.iloc[-1]) > float(obv_sma.iloc[-1]):
            puan += 30
            detay.append("OBV+")

        # Kapanis gucu
        kap = float(c.iloc[-1] / df['High'].iloc[-1])
        if kap >= 0.985:
            puan += 30
            detay.append(f"Kap:{kap:.3f}+")

        return min(100, puan), " ".join(detay)


# ================================================================
# COIN KARAR VERICI
# ================================================================
class CoinBrain:
    """Kripto karar verici -- ANKA ile ayni mimari."""

    COINS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT",
        "ATOMUSDT", "NEARUSDT", "FTMUSDT", "ARBUSDT", "OPUSDT",
    ]

    # Risk limitleri
    MAX_ISLEM_USDT = 100.0      # Tek islemde max USDT
    MAX_ACIK_POZISYON = 5       # Max ayni anda acik pozisyon
    MIN_SKOR_AL = 60            # Min skor AL karari icin
    TARAMA_ARALIK_DK = 15       # Tarama araligi (dakika)

    def __init__(self, api_key="", api_secret="", dry_run=False):
        # .env'den yukle (parametre verilmediyse)
        if not api_key:
            api_key = os.environ.get("BINANCE_API_KEY", "")
        if not api_secret:
            api_secret = os.environ.get("BINANCE_API_SECRET", "")

        self.client = BinanceClient(api_key, api_secret)
        self.ajanlar = [CryptoTechnoAgent(), CryptoVolumeAgent(), CryptoMacroAgent()]
        self.dry_run = dry_run

        if self.dry_run:
            logger.info("DRY-RUN modu aktif -- emirler gonderilmeyecek")

    def pozisyon_guncelle(self):
        """Bakiye ve pozisyon durumunu guncelle."""
        try:
            hesap = self.client.bakiye()
            if "balances" in hesap:
                aktif = [b for b in hesap["balances"]
                         if float(b["free"]) > 0 or float(b["locked"]) > 0]
                state = {
                    "zaman": datetime.now().isoformat(),
                    "bakiye": aktif,
                    "toplam_usdt": sum(
                        float(b["free"]) + float(b["locked"])
                        for b in hesap["balances"] if b["asset"] == "USDT"
                    ),
                }
                with open(COIN_STATE, "w") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                logger.info(f"Pozisyon guncellendi: {len(aktif)} aktif varlik, "
                            f"USDT: {state['toplam_usdt']:.2f}")
                return state
            else:
                logger.warning(f"bakiye() beklenmeyen yanit: {hesap}")
        except Exception as e:
            logger.error(f"Pozisyon guncelleme hatasi: {e}")
        return None

    def emir_gonder(self, symbol, yon, miktar, fiyat=None):
        """
        Emir gonder (dry_run destekli).
        yon: 'AL' veya 'SAT'
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] {yon} {symbol} miktar={miktar} fiyat={fiyat}")
            return {"dry_run": True, "symbol": symbol, "side": yon, "quantity": miktar}

        if yon == "AL":
            sonuc = self.client.alis(symbol, miktar, fiyat)
        elif yon == "SAT":
            sonuc = self.client.satis(symbol, miktar, fiyat)
        else:
            logger.error(f"Gecersiz yon: {yon}")
            return {"error": f"Gecersiz yon: {yon}"}

        # Log kaydet
        self._islem_logla(symbol, yon, miktar, fiyat, sonuc)
        return sonuc

    def _islem_logla(self, symbol, yon, miktar, fiyat, sonuc):
        """Islem sonucunu loglama."""
        kayit = {
            "zaman": datetime.now().isoformat(),
            "symbol": symbol,
            "yon": yon,
            "miktar": miktar,
            "fiyat": fiyat,
            "sonuc": sonuc,
        }

        # Dosyaya ekle
        try:
            loglar = []
            if COIN_LOG.exists():
                with open(COIN_LOG) as f:
                    loglar = json.load(f)
            loglar.append(kayit)
            # Son 500 kayit tut
            loglar = loglar[-500:]
            with open(COIN_LOG, "w") as f:
                json.dump(loglar, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Islem log hatasi: {e}")

        if "error" in sonuc:
            logger.error(f"EMIR HATASI {yon} {symbol}: {sonuc}")
        else:
            logger.info(f"EMIR OK {yon} {symbol} miktar={miktar} sonuc={sonuc.get('status', '?')}")

    def tara(self, coins=None):
        if coins is None:
            coins = self.COINS

        logger.info(f"COIN TRADER -- {len(coins)} coin taraniyor")
        print(f"\n COIN TRADER -- {len(coins)} coin taraniyor")
        print("=" * 60)

        # BTC verisi (makro icin)
        btc_df = self.client.kline("BTCUSDT", "1h", 100)
        if btc_df is None or len(btc_df) == 0:
            logger.warning("BTC verisi alinamadi, makro analiz atlanacak")
            btc_df = None

        bombalar = []

        for symbol in coins:
            try:
                df = self.client.kline(symbol, "1h", 100)
                if df is None or len(df) < 50:
                    continue

                techno_p, techno_d = CryptoTechnoAgent().analiz(df)
                volume_p, volume_d = CryptoVolumeAgent().analiz(df)
                macro_p, macro_d = CryptoMacroAgent().analiz(btc_df)

                puanlar = {"TECHNO": techno_p, "VOLUME": volume_p, "MACRO": macro_p}
                toplam = techno_p * 0.4 + volume_p * 0.3 + macro_p * 0.3

                al_sayisi = sum(1 for p in puanlar.values() if p >= 60)
                karar = "AL" if toplam >= self.MIN_SKOR_AL and al_sayisi >= 2 else "BEKLE"

                isaret = "[AL]" if karar == "AL" else "[ ]"
                fiyat_val = float(df['Close'].iloc[-1])

                puan_txt = " ".join(f"{k[:3]}:{v}" for k, v in puanlar.items())
                print(f"  {isaret} {symbol:12} ${fiyat_val:>10,.2f} | {puan_txt} | Toplam:{toplam:.0f}")

                bombalar.append({
                    "symbol": symbol, "fiyat": fiyat_val, "skor": toplam,
                    "karar": karar, "puanlar": puanlar,
                    "techno_d": techno_d, "volume_d": volume_d,
                })

            except Exception as e:
                logger.warning(f"{symbol} tarama hatasi: {e}")
                continue

        # SKORA GORE SIRALA
        bombalar.sort(key=lambda x: x["skor"], reverse=True)

        print(f"\n{'='*60}")
        print(f"  SKOR SIRALAMASINA GORE TUM COINLER:")
        print(f"{'='*60}")
        for i, b in enumerate(bombalar):
            isaret = "[1.]" if i == 0 else "[2.]" if i == 1 else "[3.]" if i == 2 else "[AL]" if b["karar"] == "AL" else "[ ]"
            birim = "TL" if "TRY" in b["symbol"] else "$"
            print(f"  {i+1:2}. {isaret} {b['symbol']:12} {birim}{b['fiyat']:>10,.2f} | Skor:{b['skor']:5.1f} | {b['karar']}")

        al_listesi = [b for b in bombalar if b["karar"] == "AL"]
        print(f"\n  BOMBA ({len(al_listesi)}/{len(bombalar)}): "
              f"{', '.join(b['symbol'] for b in al_listesi) if al_listesi else 'YOK'}")

        # Bridge dosyasina yaz
        try:
            with open(COIN_BRIDGE, "w") as f:
                json.dump({
                    "zaman": datetime.now().isoformat(),
                    "bombalar": bombalar,
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Bridge yazma hatasi: {e}")

        return bombalar

    def bot_dongusu(self):
        """
        7/24 otonom bot dongusu.
        Her TARAMA_ARALIK_DK dakikada:
          1. Pozisyon guncelle
          2. Tara
          3. AL sinyali varsa emir gonder (risk limitleri dahilinde)
        """
        logger.info("BOT DONGUSU BASLADI" + (" [DRY-RUN]" if self.dry_run else ""))
        print(f"\n  COIN BOT 7/24 -- Her {self.TARAMA_ARALIK_DK} dakika tarama")
        if self.dry_run:
            print("  [DRY-RUN] Emirler gonderilmeyecek")
        print("=" * 60)

        while True:
            try:
                # 1. Pozisyon guncelle
                state = self.pozisyon_guncelle()
                usdt_bakiye = state["toplam_usdt"] if state else 0

                # 2. Tara
                bombalar = self.tara()

                # 3. AL sinyali isle
                al_listesi = [b for b in bombalar if b["karar"] == "AL"]

                if al_listesi and usdt_bakiye > 10:
                    # Kac pozisyon acik?
                    acik_pozisyon = 0
                    if state and state.get("bakiye"):
                        acik_pozisyon = len([
                            b for b in state["bakiye"]
                            if b["asset"] != "USDT" and (float(b["free"]) + float(b["locked"])) > 0
                        ])

                    bos_slot = self.MAX_ACIK_POZISYON - acik_pozisyon
                    if bos_slot <= 0:
                        logger.info(f"Max pozisyon limitine ulasildi ({self.MAX_ACIK_POZISYON})")
                    else:
                        # En yuksek skorlu coinlerden al
                        for bomba in al_listesi[:bos_slot]:
                            islem_usdt = min(self.MAX_ISLEM_USDT, usdt_bakiye * 0.2)
                            if islem_usdt < 10:
                                break

                            miktar = round(islem_usdt / bomba["fiyat"], 6)
                            logger.info(f"AL sinyali: {bomba['symbol']} skor={bomba['skor']:.0f} "
                                        f"miktar={miktar} (~${islem_usdt:.0f})")

                            sonuc = self.emir_gonder(bomba["symbol"], "AL", miktar)
                            if "error" not in sonuc:
                                usdt_bakiye -= islem_usdt
                else:
                    if not al_listesi:
                        logger.info("AL sinyali yok, bekleniyor")
                    elif usdt_bakiye <= 10:
                        logger.info(f"USDT bakiye yetersiz: {usdt_bakiye:.2f}")

            except Exception as e:
                logger.error(f"Bot dongusu hatasi: {e}")

            # Bekle
            logger.info(f"Sonraki tarama: {self.TARAMA_ARALIK_DK} dakika sonra")
            time.sleep(self.TARAMA_ARALIK_DK * 60)


# ================================================================
# ROKET TARAYICI -- Anormal Hacim + Parabolik Yukselis Yakalayici
# ================================================================
class RoketTarayici:
    """
    Roketi yakalar:
    - Hacim x5+ patlama
    - Fiyat %10+ yukselis (24s)
    - Tum SMA'larin ustunde
    - 5 dakikada bir tarar
    """

    # Binance'deki tum populer TL ve USDT pairleri
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
        """Hacim ortalamanin N kati olan coinleri bul."""
        if coins is None:
            coins = self.USDT_COINS + self.TL_COINS

        logger.info(f"ROKET TARAYICI -- {len(coins)} coin, esik=x{esik}")
        print(f"\n  ROKET TARAYICI -- {len(coins)} coin")
        print(f"   Hacim esigi: x{esik}+")
        print("=" * 60)

        roketler = []

        for symbol in coins:
            try:
                # 1 saatlik veri cek
                df = self.client.kline(symbol, "1h", 100)
                if df is None or len(df) < 24:
                    continue

                c = df['Close']
                v = df['Volume']

                son_fiyat = float(c.iloc[-1])
                son_hacim = float(v.iloc[-1])
                ort_hacim = float(v.iloc[-25:-1].mean())  # Son 24 saatlik ortalama

                if ort_hacim <= 0:
                    continue

                hacim_oran = son_hacim / ort_hacim

                # 24 saatlik degisim
                fiyat_24s = float(c.iloc[-24]) if len(c) >= 24 else float(c.iloc[0])
                degisim_24s = (son_fiyat / fiyat_24s - 1) * 100

                # 1 saatlik degisim
                degisim_1s = (float(c.iloc[-1]) / float(c.iloc[-2]) - 1) * 100

                # SMA kontrol
                sma20 = float(c.rolling(20).mean().iloc[-1])
                sma50 = float(c.rolling(min(50, len(c))).mean().iloc[-1])
                sma_ustunde = son_fiyat > sma20 > sma50

                # ROKET KRITERLERI
                is_roket = False
                sebep = []

                if hacim_oran >= esik:
                    sebep.append(f"HACIM x{hacim_oran:.1f}")
                    is_roket = True

                if degisim_24s >= 10:
                    sebep.append(f"24s +%{degisim_24s:.1f}")
                    is_roket = True

                if degisim_1s >= 5:
                    sebep.append(f"1s +%{degisim_1s:.1f}")
                    is_roket = True

                if sma_ustunde and degisim_24s > 5:
                    sebep.append("SMA+")

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

                    fiyat_str = f"TL{son_fiyat:,.2f}" if "TRY" in symbol else f"${son_fiyat:,.4f}" if son_fiyat < 1 else f"${son_fiyat:,.2f}"
                    print(f"  >> {symbol:15} {fiyat_str:>12} | {' | '.join(sebep)} | Skor:{skor:.0f}")

            except Exception as e:
                logger.warning(f"Roket tarama {symbol} hatasi: {e}")
                continue

        roketler.sort(key=lambda x: x["skor"], reverse=True)

        if not roketler:
            print("  Su an roket yok -- piyasa sakin")

        print(f"\n  {len(roketler)} ROKET bulundu")
        logger.info(f"Roket tarama tamamlandi: {len(roketler)} roket")
        return roketler

    def surekli_tara(self, aralik_dk=5):
        """Her N dakikada roket tara -- 7/24."""
        logger.info(f"ROKET TARAYICI 7/24 -- Her {aralik_dk} dakika")
        print(f"  ROKET TARAYICI 7/24 -- Her {aralik_dk} dakika")
        while True:
            try:
                roketler = self.hacim_patlama_tara()
                if roketler:
                    # Bridge'e yaz
                    with open(PROJECT_DIR / "data" / "roket_sinyaller.json", "w") as f:
                        json.dump({
                            "zaman": datetime.now().isoformat(),
                            "roketler": roketler
                        }, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Surekli tarama hatasi: {e}")
            time.sleep(aralik_dk * 60)


# ================================================================
# ANA
# ================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="COIN TRADER -- ANKA Kripto")
    parser.add_argument("--tara", action="store_true", help="Tek tarama yap")
    parser.add_argument("--bot", action="store_true", help="7/24 otonom bot")
    parser.add_argument("--durum", action="store_true", help="Durum kontrol")
    parser.add_argument("--roket", action="store_true", help="Roket tarama")
    parser.add_argument("--roket-loop", action="store_true", help="Surekli roket tarama")
    parser.add_argument("--dry-run", action="store_true", help="Simulasyon modu (emir gondermez)")

    args = parser.parse_args()

    # Hicbir flag verilmediyse --tara varsayilan
    if not any([args.tara, args.bot, args.durum, args.roket, args.roket_loop]):
        args.tara = True

    if args.tara:
        brain = CoinBrain(dry_run=args.dry_run)
        bombalar = brain.tara()

    elif args.bot:
        brain = CoinBrain(dry_run=args.dry_run)
        brain.bot_dongusu()

    elif args.roket:
        tarayici = RoketTarayici()
        tarayici.hacim_patlama_tara()

    elif args.roket_loop:
        tarayici = RoketTarayici()
        tarayici.surekli_tara(aralik_dk=5)

    elif args.durum:
        print("  COIN TRADER durumu")
        # Pozisyon guncelle
        brain = CoinBrain(dry_run=True)
        state = brain.pozisyon_guncelle()
        if state:
            print(json.dumps(state, indent=2, ensure_ascii=False))
        elif COIN_STATE.exists():
            with open(COIN_STATE) as f:
                print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
        else:
            print("Henuz state yok")
