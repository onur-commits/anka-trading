"""
ANKA KARAR VERİCİ — Multi-AI Orchestrator
==========================================
5 uzman AI'nın kararlarını birleştirir, son kararı verir.

Uzman AI'lar:
  1. Teknik AI   → EMA, RSI, MACD, hacim, mum analizi
  2. Makro AI    → VIX, USD/TRY, XU100, petrol, altın
  3. Haber AI    → Twitter/X, KAP, Bloomberg, sentiment
  4. Kurumsal AI → Yabancı akış, bilanço, PD/DD
  5. Momentum AI → Sektör rotasyonu, para akışı

Karar Verici: Hepsini dinler, ağırlıklandırır, son kararı verir.
"""

import json
import os
import sys
import time
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))


# ================================================================
# UZMAN AI #1: TEKNİK
# ================================================================
class TeknikAI:
    """EMA, RSI, MACD, Bollinger, hacim, mum analizi."""

    def __init__(self):
        self.ad = "TEKNİK"
        self.agirlik = 0.30  # Karar vericide %30 ağırlık

    def analiz(self, df):
        if df is None or len(df) < 50:
            return {"sinyal": "BEKLE", "guven": 0, "detay": "Yetersiz veri"}

        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        open_ = df['Open'].squeeze()

        # EMA
        ema10 = close.ewm(span=10).mean()
        ema20 = close.ewm(span=20).mean()
        ema_cross = float(ema10.iloc[-1]) > float(ema20.iloc[-1])

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        rsi = float(100 - (100 / (1 + rs.iloc[-1])))

        # MACD
        macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
        macd_signal = macd.ewm(span=9).mean()
        macd_pozitif = float(macd.iloc[-1]) > float(macd_signal.iloc[-1])

        # Hacim
        avg_vol = float(volume.rolling(10).mean().iloc[-1])
        curr_vol = float(volume.iloc[-1])
        hacim_oran = curr_vol / avg_vol if avg_vol > 0 else 0

        # Mum gücü
        c = float(close.iloc[-1])
        h = float(high.iloc[-1])
        l = float(low.iloc[-1])
        o = float(open_.iloc[-1])
        govde = abs(c - o) / (h - l + 1e-10)
        kapanis_gucu = c / h if h > 0 else 0

        # Bollinger
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        boll_poz = float((close.iloc[-1] - (sma20.iloc[-1] - 2*std20.iloc[-1])) /
                         (4*std20.iloc[-1] + 1e-10))

        # Puanlama
        puan = 0
        if ema_cross: puan += 25
        if rsi > 50: puan += 20
        if macd_pozitif: puan += 15
        if hacim_oran > 1.5: puan += 20
        if kapanis_gucu > 0.985: puan += 10
        if govde > 0.6: puan += 10

        guven = min(100, puan)
        sinyal = "AL" if guven >= 60 else "BEKLE" if guven >= 30 else "SAT"

        return {
            "sinyal": sinyal, "guven": guven,
            "detay": f"EMA:{'✅' if ema_cross else '❌'} RSI:{rsi:.0f} Hacim:x{hacim_oran:.1f} Kap:{kapanis_gucu:.3f}"
        }


# ================================================================
# UZMAN AI #2: MAKRO
# ================================================================
class MakroAI:
    """VIX, USD/TRY, XU100, küresel risk."""

    def __init__(self):
        self.ad = "MAKRO"
        self.agirlik = 0.25

    def analiz(self, _df=None):
        try:
            # XU100
            xu = yf.download("XU100.IS", period="5d", progress=False)
            xu100_chg = 0
            if len(xu) >= 2:
                xu100_chg = float((xu['Close'].iloc[-1] / xu['Close'].iloc[-2] - 1) * 100)

            # VIX
            vix_val = 20.0
            try:
                vix = yf.download("^VIX", period="5d", progress=False)
                if len(vix) > 0:
                    vix_val = float(vix['Close'].iloc[-1])
            except:
                pass

            # USD/TRY
            usd_chg = 0
            try:
                usd = yf.download("USDTRY=X", period="5d", progress=False)
                if len(usd) >= 2:
                    usd_chg = float((usd['Close'].iloc[-1] / usd['Close'].iloc[-2] - 1) * 100)
            except:
                pass

            # Karar
            puan = 50  # Nötr başla
            if xu100_chg > 0.5: puan += 20
            elif xu100_chg < -0.5: puan -= 20
            if xu100_chg < -1.0: puan -= 30

            if vix_val < 20: puan += 15
            elif vix_val > 25: puan -= 15
            elif vix_val > 30: puan -= 30

            if usd_chg > 0.8: puan -= 20  # Kur şoku
            elif usd_chg < -0.3: puan += 10  # TL güçleniyor

            guven = max(0, min(100, puan))
            sinyal = "AL" if guven >= 60 else "BEKLE" if guven >= 30 else "SAT"

            return {
                "sinyal": sinyal, "guven": guven,
                "detay": f"XU100:{xu100_chg:+.1f}% VIX:{vix_val:.1f} USD:{usd_chg:+.2f}%"
            }
        except:
            return {"sinyal": "BEKLE", "guven": 50, "detay": "Veri hatası"}


# ================================================================
# UZMAN AI #3: HABER/SENTIMENT
# ================================================================
class HaberAI:
    """Haber sentiment analizi — ileride Twitter/X, KAP entegrasyonu."""

    def __init__(self):
        self.ad = "HABER"
        self.agirlik = 0.15

    def analiz(self, ticker=None):
        try:
            from haber_sentiment import haberleri_analiz_et
            sentiment = haberleri_analiz_et()
            if sentiment and ticker:
                ticker_clean = ticker.replace(".IS", "")
                for item in sentiment:
                    if ticker_clean.lower() in str(item).lower():
                        return {"sinyal": "AL", "guven": 60, "detay": f"Pozitif haber: {ticker_clean}"}
            return {"sinyal": "BEKLE", "guven": 50, "detay": "Nötr sentiment"}
        except:
            return {"sinyal": "BEKLE", "guven": 50, "detay": "Sentiment verisi yok"}


# ================================================================
# UZMAN AI #4: KURUMSAL
# ================================================================
class KurumsalAI:
    """Yabancı akış, kurumsal alım tespiti."""

    def __init__(self):
        self.ad = "KURUMSAL"
        self.agirlik = 0.15

    def analiz(self, df=None):
        try:
            # XU030 vs XU100 spread (yabancı proxy)
            xu030 = yf.download("XU030.IS", period="5d", progress=False)
            xu100 = yf.download("XU100.IS", period="5d", progress=False)
            if len(xu030) >= 2 and len(xu100) >= 2:
                xu030_ret = float((xu030['Close'].iloc[-1] / xu030['Close'].iloc[-2] - 1) * 100)
                xu100_ret = float((xu100['Close'].iloc[-1] / xu100['Close'].iloc[-2] - 1) * 100)
                spread = xu030_ret - xu100_ret

                if spread > 0.3:
                    return {"sinyal": "AL", "guven": 65, "detay": f"Yabancı girişi (+{spread:.2f}%)"}
                elif spread < -0.3:
                    return {"sinyal": "SAT", "guven": 35, "detay": f"Yabancı çıkışı ({spread:.2f}%)"}

            return {"sinyal": "BEKLE", "guven": 50, "detay": "Nötr akış"}
        except:
            return {"sinyal": "BEKLE", "guven": 50, "detay": "Akış verisi yok"}


# ================================================================
# UZMAN AI #5: MOMENTUM
# ================================================================
class MomentumAI:
    """Sektör rotasyonu, momentum analizi."""

    def __init__(self):
        self.ad = "MOMENTUM"
        self.agirlik = 0.15

    def analiz(self, df=None):
        if df is None or len(df) < 20:
            return {"sinyal": "BEKLE", "guven": 50, "detay": "Yetersiz veri"}

        close = df['Close'].squeeze()

        # Momentum
        mom_1d = float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) >= 2 else 0
        mom_5d = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) >= 6 else 0
        mom_10d = float((close.iloc[-1] / close.iloc[-11] - 1) * 100) if len(close) >= 11 else 0

        # İvme (momentum'un momentum'u)
        ivme = mom_1d - mom_5d / 5

        puan = 50
        if mom_1d > 1: puan += 15
        if mom_5d > 3: puan += 15
        if ivme > 0.5: puan += 10
        if mom_1d < -1: puan -= 15
        if mom_5d < -3: puan -= 15

        guven = max(0, min(100, puan))
        sinyal = "AL" if guven >= 60 else "BEKLE" if guven >= 30 else "SAT"

        return {
            "sinyal": sinyal, "guven": guven,
            "detay": f"1G:{mom_1d:+.1f}% 5G:{mom_5d:+.1f}% İvme:{ivme:+.1f}"
        }


# ================================================================
# ANKA KARAR VERİCİ
# ================================================================
class AnkaKararVerici:
    """5 uzman AI'nın kararlarını rejime göre birleştirir."""

    # Rejime göre ajan ağırlıkları
    REJIM_AGIRLIKLARI = {
        "BULL": {"TEKNİK": 0.35, "MAKRO": 0.10, "HABER": 0.15, "KURUMSAL": 0.15, "MOMENTUM": 0.25},
        "SIDEWAYS": {"TEKNİK": 0.25, "MAKRO": 0.25, "HABER": 0.15, "KURUMSAL": 0.15, "MOMENTUM": 0.20},
        "BEAR": {"TEKNİK": 0.15, "MAKRO": 0.40, "HABER": 0.10, "KURUMSAL": 0.25, "MOMENTUM": 0.10},
    }

    # Rejime göre minimum AL oyu
    MIN_AL_OYU = {
        "BULL": 2,      # 2/5 ajan AL derse yeter
        "SIDEWAYS": 3,  # 3/5 ajan AL demeli
        "BEAR": 4,      # 4/5 ajan AL demeli (çok zor, ama geçerse güçlü)
    }

    # Rejime göre pozisyon çarpanı
    REJIM_CARPANI = {
        "BULL": 1.0,
        "SIDEWAYS": 0.7,
        "BEAR": 0.4,
    }

    def __init__(self):
        self.uzmanlar = [
            TeknikAI(),
            MakroAI(),
            HaberAI(),
            KurumsalAI(),
            MomentumAI(),
        ]
        self.rejim = "SIDEWAYS"
        self.rejim_guven = 0

    def rejim_tespit(self):
        """ADIM 1: Piyasa rejimini belirle — her şeyden ÖNCE."""
        try:
            xu = yf.download("XU100.IS", period="3mo", progress=False)
            if len(xu) < 50:
                return "SIDEWAYS", 50

            close = xu['Close'].squeeze()
            sma20 = close.rolling(20).mean()
            sma50 = close.rolling(50).mean()

            # ADX hesapla
            high = xu['High'].squeeze()
            low = xu['Low'].squeeze()
            tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
            atr14 = tr.rolling(14).mean()

            son = float(close.iloc[-1])
            s20 = float(sma20.iloc[-1])
            s50 = float(sma50.iloc[-1])

            # Son 20 günlük değişim
            chg_20d = float((close.iloc[-1] / close.iloc[-20] - 1) * 100)

            # Volatilite
            vol = float(close.pct_change().rolling(20).std().iloc[-1] * 100)

            # Rejim tespiti
            if son > s20 > s50 and chg_20d > 2:
                rejim = "BULL"
                guven = min(90, 50 + chg_20d * 5)
            elif son < s20 < s50 and chg_20d < -2:
                rejim = "BEAR"
                guven = min(90, 50 + abs(chg_20d) * 5)
            else:
                rejim = "SIDEWAYS"
                guven = 50 + (20 - abs(chg_20d) * 3)

            self.rejim = rejim
            self.rejim_guven = max(0, min(100, guven))
            return rejim, self.rejim_guven

        except:
            return "SIDEWAYS", 50

    def karar_ver(self, ticker, df_daily):
        """Tek hisse için tüm uzmanların kararını al ve rejime göre birleştir."""

        # Rejime göre ağırlıkları ayarla
        agirliklar = self.REJIM_AGIRLIKLARI.get(self.rejim, self.REJIM_AGIRLIKLARI["SIDEWAYS"])

        sonuclar = {}
        toplam_puan = 0
        toplam_agirlik = 0
        al_sayisi = 0

        for uzman in self.uzmanlar:
            if uzman.ad == "TEKNİK":
                r = uzman.analiz(df_daily)
            elif uzman.ad == "MAKRO":
                r = uzman.analiz()
            elif uzman.ad == "HABER":
                r = uzman.analiz(ticker)
            elif uzman.ad == "KURUMSAL":
                r = uzman.analiz()
            elif uzman.ad == "MOMENTUM":
                r = uzman.analiz(df_daily)
            else:
                r = {"sinyal": "BEKLE", "guven": 50, "detay": ""}

            sonuclar[uzman.ad] = r

            # Rejime göre ağırlık
            w = agirliklar.get(uzman.ad, 0.20)

            if r["sinyal"] == "AL":
                toplam_puan += r["guven"] * w
                al_sayisi += 1
            elif r["sinyal"] == "SAT":
                toplam_puan -= r["guven"] * w

            toplam_agirlik += w

        # Final skor (0-100)
        final_skor = max(0, min(100, 50 + toplam_puan / toplam_agirlik))

        # VETO #1: Makro BEAR'de SAT diyorsa → kesin veto
        veto = False
        veto_sebep = ""
        makro = sonuclar.get("MAKRO", {})
        if makro.get("sinyal") == "SAT" and makro.get("guven", 0) >= 60:
            veto = True
            veto_sebep = f"MAKRO VETO ({makro['detay']})"

        # VETO #2: Minimum AL oyu sağlanmadıysa
        min_al = self.MIN_AL_OYU.get(self.rejim, 3)
        if al_sayisi < min_al and not veto:
            veto = True
            veto_sebep = f"Yetersiz oy ({al_sayisi}/{min_al} — {self.rejim} rejimi)"

        # Pozisyon çarpanı (rejime göre)
        pos_carpan = self.REJIM_CARPANI.get(self.rejim, 0.7)

        # Final karar
        if veto:
            final_karar = "BEKLE"
        elif final_skor >= 65:
            final_karar = "AL"
        elif final_skor <= 35:
            final_karar = "SAT"
        else:
            final_karar = "BEKLE"

        return {
            "ticker": ticker,
            "karar": final_karar,
            "skor": round(final_skor, 1),
            "al_oyu": al_sayisi,
            "min_oy": min_al,
            "rejim_carpan": pos_carpan,
            "veto": veto,
            "veto_sebep": veto_sebep,
            "uzmanlar": sonuclar,
        }

    def toplu_tara(self, symbol_list):
        """Tüm hisseleri tara, bombaları bul."""
        # ADIM 1: REJİM TESPİT
        rejim, guven = self.rejim_tespit()
        agirliklar = self.REJIM_AGIRLIKLARI[rejim]

        print(f"\n🦅 ANKA KARAR VERİCİ V2")
        print("=" * 70)
        print(f"📊 REJİM: {rejim} (güven: %{guven:.0f})")
        print(f"   Ağırlıklar: {' | '.join([f'{k[:3]}:{v:.0%}' for k,v in agirliklar.items()])}")
        print(f"   Min AL oyu: {self.MIN_AL_OYU[rejim]}/5 | Pozisyon çarpanı: x{self.REJIM_CARPANI[rejim]}")
        print(f"   {len(symbol_list)} hisse taranıyor...")
        print("=" * 70)

        # Makro ve kurumsal bir kere çek (herkese aynı)
        bombalar = []
        tum_sonuclar = []

        for s in symbol_list:
            try:
                df = yf.download(f"{s}.IS", period="2y", progress=False)
                if df.empty or len(df) < 60:
                    continue

                karar = self.karar_ver(s, df)
                tum_sonuclar.append(karar)

                emoji = "💣" if karar["karar"] == "AL" else "⚪" if karar["karar"] == "BEKLE" else "🔴"
                veto_txt = f" | VETO: {karar['veto_sebep']}" if karar["veto"] else ""

                detay_parts = []
                for ad, r in karar["uzmanlar"].items():
                    detay_parts.append(f"{ad[:3]}:{r['sinyal'][0]}({r['guven']})")

                print(f"  {emoji} {s:6} Skor:{karar['skor']:5.1f} | {' '.join(detay_parts)}{veto_txt}")

                if karar["karar"] == "AL":
                    bombalar.append(s)

            except:
                continue

        # Sonuçları sırala
        tum_sonuclar.sort(key=lambda x: x["skor"], reverse=True)

        print(f"\n🎯 BOMBALAR: {','.join(bombalar) if bombalar else 'YOK'}")

        # Dosyaya yaz
        if bombalar:
            liste = ",".join(bombalar)
            if platform.system() == "Windows":
                with open("C:/Robot/aktif_bombalar.txt", "w") as f:
                    f.write(liste)
            else:
                try:
                    subprocess.run(
                        ["prlctl", "exec", "Windows 11", "cmd", "/c",
                         f"echo {liste} > C:\\Robot\\aktif_bombalar.txt"],
                        timeout=10, capture_output=True)
                except:
                    pass

        return bombalar, tum_sonuclar


# BIST50
BIST50 = [
    "GARAN","THYAO","ASELS","TUPRS","EREGL","SISE","TOASO","AKBNK","YKBNK","HALKB",
    "SAHOL","KCHOL","TCELL","BIMAS","PGSUS","TAVHL","FROTO","ARCLK","PETKM","ENKAI",
    "TKFEN","EKGYO","TTKOM","VAKBN","MGROS","DOHOL","GUBRF","ISCTR","AKSEN","AYEN",
    "KONTR","SASA","GESAN","OTKAR","ENJSA","TSKB","SMRTG","CCOLA","CIMSA","KORDS",
    "VESTL","ALARK","HEKTS","ULKER","ASTOR","TTRAK","EGEEN","CEMTS","BRISA"
]

if __name__ == "__main__":
    anka = AnkaKararVerici()
    bombalar, sonuclar = anka.toplu_tara(BIST50)
