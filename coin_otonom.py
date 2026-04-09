"""
COIN OTONOM BOT — 7/24 Kripto Trading
======================================
Mevcut ajanları (TECHNO, VOLUME, MACRO) kullanarak
otonom alım-satım yapar. Stop-loss, trailing stop,
komisyon filtresi dahil.

Kullanım:
  python coin_otonom.py                # 7/24 otonom bot
  python coin_otonom.py --dry-run      # Simülasyon (emir göndermez)
  python coin_otonom.py --durum        # Pozisyon durumu
  python coin_otonom.py --tara         # Tek seferlik tarama

Güvenlik:
  - Max pozisyon: bakiyenin %20'si (tek coin)
  - Max toplam: bakiyenin %60'ı
  - Stop-loss: ATR bazlı (%3-5)
  - Trailing stop: %2 (aktivasyon %1.5 kâr sonrası)
  - Komisyon filtresi: net getiri negatifse işlem yapma
"""

import sys
import json
import time
import hmac
import hashlib
import requests
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

STATE_FILE = DATA_DIR / "coin_otonom_state.json"
LOG_FILE = DATA_DIR / "coin_otonom_log.json"

# ============================================================
# KONFIGÜRASYON
# ============================================================

# İzlenen coinler (USDT pair)
COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "ATOMUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT",
    "SUIUSDT", "APTUSDT", "INJUSDT", "RENDERUSDT", "FETUSDT",
]

# Risk parametreleri
MAX_POZISYON_ORAN = 0.20      # Bakiyenin max %20'si tek coine
MAX_TOPLAM_ORAN = 0.60        # Bakiyenin max %60'ı toplam pozisyon
STOP_LOSS_PCT = 3.0           # %3 sabit stop-loss
TRAILING_STOP_PCT = 2.0       # %2 trailing stop
TRAILING_AKTIF_PCT = 1.5      # %1.5 kâr sonrası trailing aktif
BREAKEVEN_PCT = 0.8           # %0.8 kâr sonrası break-even
MIN_SKOR = 55                 # Minimum ajan skoru (AL için) — bear'de 62 çok yüksek
TARAMA_ARALIK_DK = 10         # Her 10 dakikada tarama
KOMISYON_ORAN = 0.001         # %0.1 Binance spot komisyon (BNB ile)
SLIPPAGE_ORAN = 0.001         # %0.1 tahmini slippage
TOPLAM_MALIYET = (KOMISYON_ORAN * 2) + SLIPPAGE_ORAN  # %0.3 gidiş-dönüş

DRY_RUN = "--dry-run" in sys.argv

# Bot bu coinlere DOKUNMAZ (kilitli pozisyonlar)
KILITLI_COINLER = ["SOLUSDT"]  # Yarı SOL serbest piyasada, bot karışmaz


# ============================================================
# BINANCE CLIENT
# ============================================================

class BinanceClient:
    BASE_URL = "https://api.binance.com"

    def __init__(self):
        env_path = BASE_DIR / ".env"
        self.api_key = ""
        self.api_secret = ""
        if env_path.exists():
            for line in env_path.read_text().strip().splitlines():
                if line.startswith("BINANCE_API_KEY="):
                    self.api_key = line.split("=", 1)[1].strip()
                elif line.startswith("BINANCE_API_SECRET="):
                    self.api_secret = line.split("=", 1)[1].strip()

    def _sign(self, params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        sig = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params

    def _headers(self):
        return {"X-MBX-APIKEY": self.api_key}

    def fiyat(self, symbol):
        r = requests.get(f"{self.BASE_URL}/api/v3/ticker/price", params={"symbol": symbol}, timeout=10)
        return float(r.json()["price"])

    def kline(self, symbol, interval="1h", limit=100):
        r = requests.get(f"{self.BASE_URL}/api/v3/klines",
                        params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=10)
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

    def bakiye_usdt(self):
        params = {"timestamp": int(time.time() * 1000)}
        params = self._sign(params)
        r = requests.get(f"{self.BASE_URL}/api/v3/account",
                        headers=self._headers(), params=params, timeout=10)
        data = r.json()
        for b in data.get("balances", []):
            if b["asset"] == "USDT":
                return float(b["free"])
        return 0.0

    def bakiye_coin(self, asset):
        params = {"timestamp": int(time.time() * 1000)}
        params = self._sign(params)
        r = requests.get(f"{self.BASE_URL}/api/v3/account",
                        headers=self._headers(), params=params, timeout=10)
        data = r.json()
        for b in data.get("balances", []):
            if b["asset"] == asset:
                return float(b["free"])
        return 0.0

    def market_buy(self, symbol, quote_qty):
        """USDT miktarı ile market alış."""
        if DRY_RUN:
            log(f"[DRY-RUN] ALIS: {symbol} {quote_qty} USDT")
            return {"status": "DRY_RUN", "symbol": symbol, "quoteQty": quote_qty}
        params = {
            "symbol": symbol,
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": f"{quote_qty:.2f}",
            "timestamp": int(time.time() * 1000),
        }
        params = self._sign(params)
        r = requests.post(f"{self.BASE_URL}/api/v3/order",
                         headers=self._headers(), params=params, timeout=10)
        return r.json()

    def market_sell(self, symbol, qty):
        """Coin miktarı ile market satış."""
        if DRY_RUN:
            log(f"[DRY-RUN] SATIS: {symbol} {qty}")
            return {"status": "DRY_RUN", "symbol": symbol, "qty": qty}
        params = {
            "symbol": symbol,
            "side": "SELL",
            "type": "MARKET",
            "quantity": f"{qty}",
            "timestamp": int(time.time() * 1000),
        }
        params = self._sign(params)
        r = requests.post(f"{self.BASE_URL}/api/v3/order",
                         headers=self._headers(), params=params, timeout=10)
        return r.json()

    def symbol_info(self, symbol):
        """Sembol min lot, step size bilgisi."""
        r = requests.get(f"{self.BASE_URL}/api/v3/exchangeInfo",
                        params={"symbol": symbol}, timeout=10)
        info = r.json()
        for s in info.get("symbols", []):
            if s["symbol"] == symbol:
                for f in s["filters"]:
                    if f["filterType"] == "LOT_SIZE":
                        return {
                            "minQty": float(f["minQty"]),
                            "stepSize": float(f["stepSize"]),
                        }
        return {"minQty": 0.001, "stepSize": 0.001}


# ============================================================
# LOG
# ============================================================

def log(mesaj, seviye="INFO"):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{zaman}] [{seviye}] {mesaj}")
    try:
        logs = []
        if LOG_FILE.exists():
            with open(LOG_FILE, encoding="utf-8") as f:
                logs = json.load(f)
        logs.append({"zaman": zaman, "seviye": seviye, "mesaj": mesaj})
        logs = logs[-500:]
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# ============================================================
# AJANLAR
# ============================================================

def techno_analiz(df):
    if df is None or len(df) < 50:
        return 0, "Veri yok"
    c = df["Close"]
    puan = 0
    detay = []

    # EMA
    ema10 = c.ewm(span=10).mean()
    ema20 = c.ewm(span=20).mean()
    ema50 = c.ewm(span=50).mean()
    if float(ema10.iloc[-1]) > float(ema20.iloc[-1]) > float(ema50.iloc[-1]):
        puan += 25
        detay.append("EMA tam dizilim")
    elif float(ema10.iloc[-1]) > float(ema20.iloc[-1]):
        puan += 15
        detay.append("EMA yukari")

    # RSI
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])
    if 50 < rsi < 70:
        puan += 20
        detay.append(f"RSI:{rsi:.0f}")
    elif rsi < 30:
        puan += 10
        detay.append(f"RSI:{rsi:.0f} asiri satim")
    elif rsi > 75:
        puan -= 10
        detay.append(f"RSI:{rsi:.0f} asiri alim")

    # MACD
    macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
    signal = macd.ewm(span=9).mean()
    if float(macd.iloc[-1]) > float(signal.iloc[-1]):
        puan += 20
        detay.append("MACD yukari")

    # Bollinger sıkışma
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    bw = float(4 * std20.iloc[-1] / sma20.iloc[-1] * 100) if float(sma20.iloc[-1]) > 0 else 0
    if bw < 5:
        puan += 15
        detay.append("Sikisma")

    return min(100, max(0, puan)), " | ".join(detay)


def volume_analiz(df):
    if df is None or len(df) < 20:
        return 0, "Veri yok"
    v = df["Volume"]
    c = df["Close"]
    puan = 0
    detay = []

    vol_avg = float(v.rolling(20).mean().iloc[-1])
    vol_son = float(v.iloc[-1])
    rvol = vol_son / vol_avg if vol_avg > 0 else 0

    if rvol >= 2.0:
        puan += 40
        detay.append(f"Hacim x{rvol:.1f} PATLAMA")
    elif rvol >= 1.5:
        puan += 25
        detay.append(f"Hacim x{rvol:.1f}")
    elif rvol < 0.5:
        puan -= 10
        detay.append(f"Hacim dusuk x{rvol:.1f}")

    # OBV
    obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
    obv_sma = obv.rolling(20).mean()
    if float(obv.iloc[-1]) > float(obv_sma.iloc[-1]):
        puan += 30
        detay.append("OBV birikim")
    else:
        puan -= 10
        detay.append("OBV dagitim")

    # Kapanış gücü
    kap = float(c.iloc[-1] / df["High"].iloc[-1])
    if kap >= 0.985:
        puan += 30
        detay.append("Guclu kapanis")

    return min(100, max(0, puan)), " | ".join(detay)


def macro_analiz(btc_df):
    puan = 50
    detay = []
    if btc_df is None or len(btc_df) < 20:
        return 50, "BTC veri yok"

    c = btc_df["Close"]
    sma20 = float(c.rolling(20).mean().iloc[-1])
    son = float(c.iloc[-1])

    if son > sma20:
        puan += 20
        detay.append("BTC trend yukari")
    else:
        puan -= 20
        detay.append("BTC trend asagi")

    chg_24h = float((c.iloc[-1] / c.iloc[-24] - 1) * 100) if len(c) >= 24 else 0
    if chg_24h > 3:
        puan += 10
        detay.append(f"BTC 24s: +{chg_24h:.1f}%")
    elif chg_24h < -3:
        puan -= 10
        detay.append(f"BTC 24s: {chg_24h:.1f}%")

    return max(0, min(100, puan)), " | ".join(detay)


def atr_hesapla(df, period=14):
    h = df["High"]
    l = df["Low"]
    c = df["Close"]
    tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


# ============================================================
# POZİSYON YÖNETİMİ
# ============================================================

def state_yukle():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"pozisyonlar": {}, "son_tarama": None, "toplam_trade": 0, "toplam_kar": 0}


def state_kaydet(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def komisyon_karli_mi(beklenen_getiri_pct):
    net = beklenen_getiri_pct - (TOPLAM_MALIYET * 100)
    return net > 0, round(net, 3)


def qty_yuvarla(qty, step_size):
    if step_size <= 0:
        return qty
    precision = max(0, -int(np.log10(step_size)))
    return round(np.floor(qty / step_size) * step_size, precision)


# ============================================================
# ANA BOT
# ============================================================

def tara_ve_islem(client, state):
    """Tüm coinleri tara, sinyal varsa işlem yap."""
    log("=" * 50)
    log(f"COIN OTONOM TARAMA - {len(COINS)} coin")

    usdt_bakiye = client.bakiye_usdt()
    log(f"USDT Bakiye: ${usdt_bakiye:.2f}")

    # Mevcut pozisyon değeri hesapla
    toplam_poz_deger = 0
    for sym, poz in list(state["pozisyonlar"].items()):
        try:
            fiyat = client.fiyat(sym)
            poz_deger = poz["miktar"] * fiyat
            toplam_poz_deger += poz_deger
        except Exception:
            pass

    toplam_varlik = usdt_bakiye + toplam_poz_deger
    log(f"Toplam varlik: ${toplam_varlik:.2f} (USDT: ${usdt_bakiye:.2f} + Poz: ${toplam_poz_deger:.2f})")

    # BTC verisi (makro)
    btc_df = None
    try:
        btc_df = client.kline("BTCUSDT", "1h", 100)
    except Exception:
        pass

    # === 1. MEVCUT POZİSYONLARI KONTROL ET ===
    for sym, poz in list(state["pozisyonlar"].items()):
        if sym in KILITLI_COINLER:
            log(f"  {sym}: KILITLI — bot dokunmuyor")
            continue
        try:
            fiyat = client.fiyat(sym)
            giris = poz["giris_fiyat"]
            miktar = poz["miktar"]
            en_yuksek = poz.get("en_yuksek", giris)

            # En yüksek güncelle
            if fiyat > en_yuksek:
                en_yuksek = fiyat
                poz["en_yuksek"] = en_yuksek

            kar_pct = (fiyat / giris - 1) * 100
            poz_deger = miktar * fiyat

            # Stop seviyeleri
            sabit_stop = giris * (1 - STOP_LOSS_PCT / 100)
            etkin_stop = sabit_stop

            # Break-even
            if fiyat >= giris * (1 + BREAKEVEN_PCT / 100):
                etkin_stop = max(etkin_stop, giris)

            # Trailing stop
            if en_yuksek >= giris * (1 + TRAILING_AKTIF_PCT / 100):
                trail = en_yuksek * (1 - TRAILING_STOP_PCT / 100)
                etkin_stop = max(etkin_stop, trail)

            # SATIŞ KONTROLÜ
            sat = False
            sebep = ""

            if fiyat <= etkin_stop:
                sat = True
                if etkin_stop == sabit_stop:
                    sebep = "SABIT STOP"
                elif etkin_stop == giris:
                    sebep = "BREAK-EVEN"
                else:
                    sebep = "TRAILING STOP"

            # Teknik bozulma kontrolü (EMA kırılması)
            try:
                df = client.kline(sym, "1h", 30)
                ema10 = df["Close"].ewm(span=10).mean()
                ema20 = df["Close"].ewm(span=20).mean()
                if float(ema10.iloc[-1]) < float(ema20.iloc[-1]) and kar_pct > 0:
                    sat = True
                    sebep = "EMA KIRILMA (karl)"
            except Exception:
                pass

            status = f"{'SATIS' if sat else 'TUTUYOR'}"
            log(f"  {sym}: ${fiyat:.4f} | Kar: %{kar_pct:.2f} | Stop: ${etkin_stop:.4f} | {status}")

            if sat:
                asset = sym.replace("USDT", "")
                gercek_miktar = client.bakiye_coin(asset)
                if gercek_miktar > 0:
                    info = client.symbol_info(sym)
                    sell_qty = qty_yuvarla(gercek_miktar, info["stepSize"])
                    if sell_qty >= info["minQty"]:
                        sonuc = client.market_sell(sym, sell_qty)
                        log(f"  SATIS: {sym} {sell_qty} | Sebep: {sebep} | Kar: %{kar_pct:.2f}", "TRADE")
                        state["toplam_trade"] += 1
                        state["toplam_kar"] += kar_pct
                        del state["pozisyonlar"][sym]
                    else:
                        log(f"  {sym} miktar cok kucuk, siliyor", "WARNING")
                        del state["pozisyonlar"][sym]
                else:
                    log(f"  {sym} bakiye 0, pozisyon siliniyor", "WARNING")
                    del state["pozisyonlar"][sym]

        except Exception as e:
            log(f"  {sym} kontrol hatasi: {e}", "ERROR")

    # === 2. YENİ FIRSATLARI TARA ===
    if toplam_poz_deger >= toplam_varlik * MAX_TOPLAM_ORAN:
        log(f"Max toplam pozisyon oranina ulasildi (%{MAX_TOPLAM_ORAN*100:.0f}), yeni alis yok")
    else:
        sinyaller = []
        for sym in COINS:
            if sym in state["pozisyonlar"] or sym in KILITLI_COINLER:
                continue
            try:
                df = client.kline(sym, "1h", 100)
                if len(df) < 50:
                    continue

                t_puan, t_detay = techno_analiz(df)
                v_puan, v_detay = volume_analiz(df)
                m_puan, m_detay = macro_analiz(btc_df)

                toplam = t_puan * 0.40 + v_puan * 0.30 + m_puan * 0.30

                # Komisyon kontrolü
                atr = atr_hesapla(df)
                fiyat = float(df["Close"].iloc[-1])
                atr_pct = (atr / fiyat) * 100
                beklenen = atr_pct * 0.4
                kom_ok, net_getiri = komisyon_karli_mi(beklenen)

                if toplam >= MIN_SKOR and kom_ok:
                    sinyaller.append({
                        "symbol": sym,
                        "skor": round(toplam, 1),
                        "fiyat": fiyat,
                        "atr_pct": round(atr_pct, 2),
                        "net_getiri": net_getiri,
                        "techno": t_puan,
                        "volume": v_puan,
                        "macro": m_puan,
                        "detay": f"T:{t_detay} | V:{v_detay} | M:{m_detay}",
                    })
                elif toplam >= MIN_SKOR and not kom_ok:
                    log(f"  {sym}: Skor {toplam:.0f} ama komisyon karsilamaz (net %{net_getiri})")

            except Exception:
                continue

        sinyaller.sort(key=lambda x: x["skor"], reverse=True)

        # En iyi sinyallere al
        for sinyal in sinyaller[:2]:  # Max 2 yeni pozisyon aynı anda
            sym = sinyal["symbol"]
            fiyat = sinyal["fiyat"]

            # Pozisyon boyutu
            max_usdt = min(usdt_bakiye * MAX_POZISYON_ORAN, usdt_bakiye - 10)  # 10 USDT reserve
            if max_usdt < 15:
                log(f"  Yetersiz bakiye ({usdt_bakiye:.2f} USDT), alis yapilmiyor")
                break

            alis_usdt = min(max_usdt, 100)  # Max 100 USDT per trade

            log(f"  AL SINYAL: {sym} | Skor: {sinyal['skor']} | ${fiyat:.4f} | {alis_usdt:.0f} USDT")
            log(f"    {sinyal['detay']}")

            sonuc = client.market_buy(sym, alis_usdt)

            if sonuc.get("status") == "FILLED" or sonuc.get("status") == "DRY_RUN":
                # Gerçek dolum fiyatını hesapla
                if sonuc.get("fills"):
                    dolan_fiyat = sum(float(f["price"]) * float(f["qty"]) for f in sonuc["fills"]) / \
                                  sum(float(f["qty"]) for f in sonuc["fills"])
                    dolan_miktar = sum(float(f["qty"]) for f in sonuc["fills"])
                else:
                    dolan_fiyat = fiyat
                    dolan_miktar = alis_usdt / fiyat

                state["pozisyonlar"][sym] = {
                    "giris_fiyat": round(dolan_fiyat, 8),
                    "miktar": round(dolan_miktar, 8),
                    "giris_usdt": round(alis_usdt, 2),
                    "en_yuksek": round(dolan_fiyat, 8),
                    "zaman": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "skor": sinyal["skor"],
                }
                state["toplam_trade"] += 1
                usdt_bakiye -= alis_usdt
                log(f"  ALIS TAMAM: {sym} {dolan_miktar:.6f} @ ${dolan_fiyat:.4f}", "TRADE")
            else:
                hata = sonuc.get("msg", str(sonuc))
                log(f"  ALIS HATA: {sym} — {hata}", "ERROR")

    state["son_tarama"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state_kaydet(state)
    log(f"Aktif pozisyon: {len(state['pozisyonlar'])} | Toplam trade: {state['toplam_trade']}")


# ============================================================
# ANA DÖNGÜ
# ============================================================

def bot_dongusu():
    log("=" * 60)
    log("COIN OTONOM BOT BASLATILDI")
    log(f"  Mod: {'DRY-RUN (simulasyon)' if DRY_RUN else 'CANLI TRADE'}")
    log(f"  Coin: {len(COINS)} adet")
    log(f"  Tarama: her {TARAMA_ARALIK_DK} dakika")
    log(f"  Stop-loss: %{STOP_LOSS_PCT} | Trailing: %{TRAILING_STOP_PCT}")
    log(f"  Komisyon: %{TOPLAM_MALIYET*100:.1f}")
    log("=" * 60)

    client = BinanceClient()
    state = state_yukle()

    # İlk tarama hemen
    try:
        tara_ve_islem(client, state)
    except Exception as e:
        log(f"Ilk tarama hatasi: {e}", "ERROR")
        traceback.print_exc()

    # Döngü
    while True:
        try:
            time.sleep(TARAMA_ARALIK_DK * 60)
            tara_ve_islem(client, state)
        except KeyboardInterrupt:
            log("Bot durduruldu (Ctrl+C)")
            break
        except Exception as e:
            log(f"Dongu hatasi: {e}", "ERROR")
            traceback.print_exc()
            time.sleep(60)  # 1dk bekle, tekrar dene


def durum_goster():
    state = state_yukle()
    client = BinanceClient()

    print("\n=== COIN OTONOM BOT DURUMU ===")
    print(f"Son tarama: {state.get('son_tarama', 'Hic')}")
    print(f"Toplam trade: {state.get('toplam_trade', 0)}")
    print(f"Toplam kar: %{state.get('toplam_kar', 0):.2f}")
    print(f"\nUSDT Bakiye: ${client.bakiye_usdt():.2f}")

    pozlar = state.get("pozisyonlar", {})
    if pozlar:
        print(f"\nAktif Pozisyonlar ({len(pozlar)}):")
        print(f"{'Symbol':12} {'Giris':>10} {'Simdi':>10} {'Kar%':>8} {'Miktar':>10} {'USDT':>8}")
        print("-" * 65)
        for sym, poz in pozlar.items():
            try:
                fiyat = client.fiyat(sym)
                kar = (fiyat / poz["giris_fiyat"] - 1) * 100
                deger = poz["miktar"] * fiyat
                emoji = "+" if kar > 0 else ""
                print(f"{sym:12} ${poz['giris_fiyat']:>9.4f} ${fiyat:>9.4f} {emoji}{kar:>7.2f}% {poz['miktar']:>9.6f} ${deger:>7.2f}")
            except Exception:
                print(f"{sym:12} {poz['giris_fiyat']:>10} ??? ")
    else:
        print("\nAktif pozisyon yok.")


def tek_tarama():
    client = BinanceClient()
    state = state_yukle()
    tara_ve_islem(client, state)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if "--durum" in sys.argv:
        durum_goster()
    elif "--tara" in sys.argv:
        tek_tarama()
    else:
        bot_dongusu()
