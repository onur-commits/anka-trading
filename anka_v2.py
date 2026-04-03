"""
ANKA V2 — Multi-Agent Karar Sistemi
====================================
4 Uzman Ajan + 1 Karar Verici Beyin

Her ajan 0-100 puan verir.
Karar Verici rejime göre ağırlıklandırır.
En az N ajan onaylamalı (rejime göre değişir).

Sabah 08:45'te otomatik çalışır.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
import sys
import subprocess
import platform
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

BIST50 = [
    "GARAN","THYAO","ASELS","TUPRS","EREGL","SISE","TOASO","AKBNK","YKBNK","HALKB",
    "SAHOL","KCHOL","TCELL","BIMAS","PGSUS","TAVHL","FROTO","ARCLK","PETKM","ENKAI",
    "TKFEN","EKGYO","TTKOM","VAKBN","MGROS","DOHOL","GUBRF","ISCTR","AKSEN","AYEN",
    "KONTR","SASA","GESAN","OTKAR","ENJSA","TSKB","SMRTG","CCOLA","CIMSA","KORDS",
    "VESTL","ALARK","HEKTS","ULKER","ASTOR","TTRAK","EGEEN","CEMTS","BRISA"
]


# ================================================================
# AJAN 1: TECHNO-AGENT (Teknik Analiz)
# EMA, RSI, MOST, Pivot, Trend Kırılması
# ================================================================
class TechnoAgent:
    ad = "TECHNO"

    def analiz(self, df):
        """0-100 puan döndürür."""
        if df is None or len(df) < 50:
            return 0, "Veri yok"

        c = df['Close'].squeeze()
        h = df['High'].squeeze()
        l = df['Low'].squeeze()
        o = df['Open'].squeeze()
        v = df['Volume'].squeeze()

        puan = 0
        detay = []

        # EMA 10/20 Cross
        ema10 = c.ewm(span=10).mean()
        ema20 = c.ewm(span=20).mean()
        if float(ema10.iloc[-1]) > float(ema20.iloc[-1]):
            puan += 20
            detay.append("EMA✅")
        else:
            detay.append("EMA❌")

        # RSI
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = float(100 - (100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-10))))
        if rsi > 50 and rsi < 70:
            puan += 20
            detay.append(f"RSI:{rsi:.0f}✅")
        elif rsi > 70:
            puan += 10  # Aşırı alım riski
            detay.append(f"RSI:{rsi:.0f}⚠️")
        else:
            detay.append(f"RSI:{rsi:.0f}❌")

        # MACD
        macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        signal = macd.ewm(span=9).mean()
        if float(macd.iloc[-1]) > float(signal.iloc[-1]):
            puan += 15
            detay.append("MACD✅")

        # MOST (basitleştirilmiş — EMA3 üzerinde mi)
        ema3 = c.ewm(span=3).mean()
        if float(c.iloc[-1]) > float(ema3.iloc[-1]):
            puan += 15
            detay.append("MOST✅")

        # Pivot (dünkü H/L/C ortalaması)
        if len(c) >= 2:
            pivot = (float(h.iloc[-2]) + float(l.iloc[-2]) + float(c.iloc[-2])) / 3
            if float(c.iloc[-1]) > pivot:
                puan += 15
                detay.append("Pivot✅")
            else:
                detay.append("Pivot❌")

        # Trend kırılması (20 günlük en yüksek kırıldı mı)
        if len(c) >= 20:
            yirmi_gun_max = float(h.iloc[-20:-1].max())
            if float(c.iloc[-1]) > yirmi_gun_max:
                puan += 15
                detay.append("KIRILMA✅")

        return min(100, puan), " ".join(detay)


# ================================================================
# AJAN 2: FUNDAMENTAL-AGENT (Şirket Röntgeni)
# F/K, PD/DD, Nakit akışı, Büyüme
# ================================================================
class FundamentalAgent:
    ad = "FUNDA"

    # Sektör bazlı F/K ortalamaları (yaklaşık)
    SEKTOR_FK = {
        "banka": 5, "enerji": 8, "sanayi": 12, "teknoloji": 15,
        "perakende": 10, "insaat": 7, "diger": 10
    }

    # Hisse-sektör eşleştirmesi
    HISSE_SEKTOR = {
        "GARAN": "banka", "AKBNK": "banka", "YKBNK": "banka", "HALKB": "banka",
        "VAKBN": "banka", "ISCTR": "banka", "TSKB": "banka",
        "THYAO": "sanayi", "ASELS": "teknoloji", "TOASO": "sanayi", "FROTO": "sanayi",
        "TUPRS": "enerji", "AYEN": "enerji", "AKSEN": "enerji", "ENJSA": "enerji",
        "EREGL": "sanayi", "PETKM": "enerji", "SASA": "sanayi",
        "BIMAS": "perakende", "MGROS": "perakende",
        "EKGYO": "insaat", "SAHOL": "diger", "KCHOL": "diger",
    }

    def analiz(self, ticker, df=None):
        """0-100 puan döndürür."""
        puan = 50  # Nötr başla (veri eksikse orta puan)
        detay = []

        try:
            t = yf.Ticker(f"{ticker}.IS")
            info = t.info

            # F/K oranı
            fk = info.get("trailingPE") or info.get("forwardPE")
            if fk:
                sektor = self.HISSE_SEKTOR.get(ticker, "diger")
                sektor_ort = self.SEKTOR_FK.get(sektor, 10)

                if fk < sektor_ort * 0.7:  # Sektör ortalamasının %30 altı
                    puan += 20
                    detay.append(f"F/K:{fk:.1f} UCUZ✅")
                elif fk < sektor_ort:
                    puan += 10
                    detay.append(f"F/K:{fk:.1f}")
                elif fk > sektor_ort * 1.5:
                    puan -= 15
                    detay.append(f"F/K:{fk:.1f} PAHALI❌")
                else:
                    detay.append(f"F/K:{fk:.1f}")

            # PD/DD
            pddd = info.get("priceToBook")
            if pddd:
                if pddd < 1.0:
                    puan += 15
                    detay.append(f"PD/DD:{pddd:.1f} UCUZ✅")
                elif pddd < 2.0:
                    puan += 5
                    detay.append(f"PD/DD:{pddd:.1f}")
                elif pddd > 5.0:
                    puan -= 10
                    detay.append(f"PD/DD:{pddd:.1f}❌")

            # Kâr marjı
            margin = info.get("profitMargins")
            if margin:
                if margin > 0.15:
                    puan += 10
                    detay.append(f"Marj:%{margin*100:.0f}✅")
                elif margin < 0:
                    puan -= 15
                    detay.append(f"Marj:%{margin*100:.0f}❌")

            # Borç/Özsermaye
            de = info.get("debtToEquity")
            if de:
                if de > 200:
                    puan -= 15
                    detay.append(f"Borç:{de:.0f}%❌")
                elif de < 50:
                    puan += 10
                    detay.append(f"Borç:{de:.0f}%✅")

        except:
            detay.append("Veri alınamadı")

        return max(0, min(100, puan)), " ".join(detay) if detay else "Nötr"


# ================================================================
# AJAN 3: MACRO-AGENT (Dışsal Faktörler)
# USD/TRY, VIX, XU100, Faiz
# ================================================================
class MacroAgent:
    ad = "MACRO"

    def analiz(self, _df=None):
        """0-100 puan döndürür. S&P500 + Petrol + Altın dahil."""
        puan = 50
        detay = []

        try:
            # XU100
            xu = yf.download("XU100.IS", period="5d", progress=False)
            xu_chg = 0
            if len(xu) >= 2:
                xu_chg = float((xu['Close'].iloc[-1] / xu['Close'].iloc[-2] - 1) * 100)
                if xu_chg > 1.0:
                    puan += 25
                    detay.append(f"XU100:{xu_chg:+.1f}%✅")
                elif xu_chg > 0:
                    puan += 10
                    detay.append(f"XU100:{xu_chg:+.1f}%")
                elif xu_chg < -1.0:
                    puan -= 25
                    detay.append(f"XU100:{xu_chg:+.1f}%❌")
                else:
                    puan -= 10
                    detay.append(f"XU100:{xu_chg:+.1f}%")

            # VIX
            vix_val = 20.0
            try:
                vix = yf.download("^VIX", period="5d", progress=False)
                if len(vix) > 0:
                    vix_val = float(vix['Close'].iloc[-1])
            except:
                pass

            if vix_val < 18:
                puan += 15
                detay.append(f"VIX:{vix_val:.0f}✅")
            elif vix_val > 28:
                puan -= 20
                detay.append(f"VIX:{vix_val:.0f}❌")
            else:
                detay.append(f"VIX:{vix_val:.0f}")

            # USD/TRY
            try:
                usd = yf.download("USDTRY=X", period="5d", progress=False)
                if len(usd) >= 2:
                    usd_chg = float((usd['Close'].iloc[-1] / usd['Close'].iloc[-2] - 1) * 100)
                    if usd_chg > 1.0:
                        puan -= 20
                        detay.append(f"USD:{usd_chg:+.1f}%❌")
                    elif usd_chg < -0.3:
                        puan += 10
                        detay.append(f"USD:{usd_chg:+.1f}%✅")
                    else:
                        detay.append(f"USD:{usd_chg:+.1f}%")
            except:
                pass

            # S&P 500 — global yön
            try:
                sp = yf.download("^GSPC", period="5d", progress=False)
                if len(sp) >= 2:
                    sp_chg = float((sp['Close'].iloc[-1] / sp['Close'].iloc[-2] - 1) * 100)
                    sp_sma200 = float(sp['Close'].rolling(min(200, len(sp))).mean().iloc[-1])
                    sp_son = float(sp['Close'].iloc[-1])

                    if sp_son < sp_sma200:
                        puan -= 15
                        detay.append(f"S&P:SMA200 altı❌")
                    if sp_chg < -1.0:
                        puan -= 10
                        detay.append(f"S&P:{sp_chg:+.1f}%❌")
                    elif sp_chg > 1.0:
                        puan += 10
                        detay.append(f"S&P:{sp_chg:+.1f}%✅")
            except:
                pass

            # Petrol (Brent) — enerji hisseleri için kritik
            try:
                oil = yf.download("BZ=F", period="5d", progress=False)
                if len(oil) >= 2:
                    oil_chg = float((oil['Close'].iloc[-1] / oil['Close'].iloc[-2] - 1) * 100)
                    oil_val = float(oil['Close'].iloc[-1])
                    if oil_val > 100:
                        puan += 5  # Yüksek petrol = enerji hisselerine pozitif
                        detay.append(f"Petrol:${oil_val:.0f}🛢️")
                    if oil_chg > 2:
                        detay.append(f"Petrol:{oil_chg:+.1f}%⬆️")
                    elif oil_chg < -2:
                        detay.append(f"Petrol:{oil_chg:+.1f}%⬇️")
            except:
                pass

            # Altın — güvenli liman göstergesi
            try:
                gold = yf.download("GC=F", period="5d", progress=False)
                if len(gold) >= 2:
                    gold_chg = float((gold['Close'].iloc[-1] / gold['Close'].iloc[-2] - 1) * 100)
                    if gold_chg > 1.5:
                        puan -= 5  # Altın yükseliyorsa risk-off
                        detay.append(f"Altın:{gold_chg:+.1f}%⚠️")
            except:
                pass

        except:
            detay.append("Veri hatası")

        return max(0, min(100, puan)), " ".join(detay) if detay else "Nötr"


# ================================================================
# AJAN 4: VOLUME-AGENT (Likidite & Akıllı Para)
# Hacim patlaması, MFI, OBV
# ================================================================
class VolumeAgent:
    ad = "VOLUME"

    def analiz(self, df):
        """0-100 puan döndürür."""
        if df is None or len(df) < 20:
            return 0, "Veri yok"

        c = df['Close'].squeeze()
        h = df['High'].squeeze()
        l = df['Low'].squeeze()
        v = df['Volume'].squeeze()

        puan = 0
        detay = []

        # Hacim oranı (10 günlük ortalamaya göre)
        avg_vol = float(v.rolling(10).mean().iloc[-1])
        curr_vol = float(v.iloc[-1])
        hacim_oran = curr_vol / avg_vol if avg_vol > 0 else 0

        if hacim_oran >= 2.0:
            puan += 35
            detay.append(f"Hacim:x{hacim_oran:.1f}🔥")
        elif hacim_oran >= 1.5:
            puan += 25
            detay.append(f"Hacim:x{hacim_oran:.1f}✅")
        elif hacim_oran >= 1.0:
            puan += 10
            detay.append(f"Hacim:x{hacim_oran:.1f}")
        else:
            detay.append(f"Hacim:x{hacim_oran:.1f}❌")

        # MFI (Money Flow Index)
        tp = (h + l + c) / 3
        mf = tp * v
        pos_mf = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg_mf = mf.where(tp <= tp.shift(1), 0).rolling(14).sum()
        mfi = float(100 - (100 / (1 + pos_mf.iloc[-1] / (neg_mf.iloc[-1] + 1e-10))))

        if mfi > 60:
            puan += 25
            detay.append(f"MFI:{mfi:.0f}✅")
        elif mfi < 30:
            puan += 15  # Aşırı satımdan dönüş potansiyeli
            detay.append(f"MFI:{mfi:.0f}⬇️")
        else:
            detay.append(f"MFI:{mfi:.0f}")

        # OBV trend
        obv = (np.sign(c.diff()) * v).fillna(0).cumsum()
        obv_sma = obv.rolling(20).mean()
        if float(obv.iloc[-1]) > float(obv_sma.iloc[-1]):
            puan += 20
            detay.append("OBV✅")
        else:
            detay.append("OBV❌")

        # Kapanış gücü
        son_c = float(c.iloc[-1])
        son_h = float(h.iloc[-1])
        kapanis = son_c / son_h if son_h > 0 else 0
        if kapanis >= 0.985:
            puan += 20
            detay.append(f"Kap:{kapanis:.3f}✅")
        else:
            detay.append(f"Kap:{kapanis:.3f}")

        return min(100, puan), " ".join(detay)


# ================================================================
# REJİM TESPİT
# ================================================================
def rejim_tespit():
    """Piyasa rejimini belirle — BULL / BEAR / SIDEWAYS."""
    try:
        xu = yf.download("XU100.IS", period="3mo", progress=False)
        if len(xu) < 50:
            return "SIDEWAYS", 50

        c = xu['Close'].squeeze()
        sma20 = c.rolling(20).mean()
        sma50 = c.rolling(50).mean()

        son = float(c.iloc[-1])
        s20 = float(sma20.iloc[-1])
        s50 = float(sma50.iloc[-1])
        chg_20d = float((c.iloc[-1] / c.iloc[-20] - 1) * 100)

        if son > s20 > s50 and chg_20d > 2:
            return "BULL", min(90, 50 + chg_20d * 5)
        elif son < s20 < s50 and chg_20d < -2:
            return "BEAR", min(90, 50 + abs(chg_20d) * 5)
        else:
            return "SIDEWAYS", 50
    except:
        return "SIDEWAYS", 50


# ================================================================
# KARAR VERİCİ BEYİN (The Aggregator)
# ================================================================
class AnkaBrain:
    """
    Tüm ajanlardan gelen 0-100 puanları rejime göre ağırlıklandırır.
    Minimum oy kontrolü yapar. Veto hakkı uygular.
    """

    AGIRLIKLAR = {
        "BULL":     {"TECHNO": 0.35, "VOLUME": 0.25, "MACRO": 0.10, "FUNDA": 0.15, "MOMENTUM": 0.15},
        "SIDEWAYS": {"TECHNO": 0.25, "VOLUME": 0.20, "MACRO": 0.25, "FUNDA": 0.15, "MOMENTUM": 0.15},
        "BEAR":     {"TECHNO": 0.15, "VOLUME": 0.10, "MACRO": 0.35, "FUNDA": 0.25, "MOMENTUM": 0.15},
    }

    MIN_ONAY = {"BULL": 2, "SIDEWAYS": 2, "BEAR": 3}
    POS_CARPAN = {"BULL": 1.0, "SIDEWAYS": 0.7, "BEAR": 0.4}
    AL_ESIK = 60  # Bu puanın üstü "AL" sayılır

    def __init__(self):
        self.ajanlar = [TechnoAgent(), VolumeAgent(), MacroAgent(), FundamentalAgent()]
        self.rejim = "SIDEWAYS"
        self.rejim_guven = 50

    def ajanlar_konussun(self, puanlar, detaylar, rejim):
        """
        AJAN DİYALOG SİSTEMİ
        Ajanlar birbirleriyle konuşur — teyit, uyarı, veto.
        """
        konusma = []
        carpan_ayar = 1.0

        techno = puanlar.get("TECHNO", 0)
        volume = puanlar.get("VOLUME", 0)
        macro = puanlar.get("MACRO", 0)
        funda = puanlar.get("FUNDA", 0)

        # 1. Techno sinyal verdi mi?
        if techno >= 60:
            konusma.append(f"🔧 Techno: AL sinyali ({techno})")

            # Volume teyit ediyor mu?
            if volume >= 60:
                konusma.append(f"📊 Volume: TEYİT! Hacim var ({volume})")
                carpan_ayar *= 1.2  # İkisi uyuşunca güçlü sinyal
            else:
                konusma.append(f"📊 Volume: Hacim yok ({volume}), dikkat!")
                carpan_ayar *= 0.7

            # Macro ne diyor?
            if macro < 40:
                konusma.append(f"🌍 Macro: UYARI! Piyasa kötü ({macro})")
                if rejim == "BEAR":
                    konusma.append(f"🌍 Macro: Bear'de bu sinyal TUZAK olabilir → VETO")
                    carpan_ayar = 0  # Hard veto
                else:
                    carpan_ayar *= 0.5

            # Funda ne diyor?
            if funda >= 70:
                konusma.append(f"🏦 Funda: Şirket sağlam ({funda}), destekliyorum")
                carpan_ayar *= 1.1
            elif funda < 35:
                konusma.append(f"🏦 Funda: Şirket riskli ({funda}), pozisyon küçült")
                carpan_ayar *= 0.6

        # 2. Volume tek başına patlama yapıyorsa
        elif volume >= 80 and techno < 60:
            konusma.append(f"📊 Volume: HACİM PATLAMA! ({volume}) ama teknik sinyal yok")
            konusma.append(f"🔧 Techno: Henüz cross yok ({techno}), erken olabilir")
            carpan_ayar *= 0.3  # İzle ama girme

        # 3. Macro alarm
        if macro < 25:
            konusma.append(f"🌍 Macro: ACİL! Piyasa çöküyor ({macro}) → TÜM ALIMLAR DURDUR")
            carpan_ayar = 0

        # 4. Funda çok ucuz ama teknik kötü
        if funda >= 80 and techno < 40:
            konusma.append(f"🏦 Funda: Çok ucuz ({funda}) ama düşüş trendi var")
            konusma.append(f"🔧 Techno: Trend dönüşü bekliyorum ({techno})")

        # 5. HERKESİN PUANI YÜKSEK — güçlü konsensüs
        if all(p >= 60 for p in puanlar.values()):
            konusma.append(f"🦅 KONSENSÜS: 4/4 ajan AL diyor → AGRESİF GİR!")
            carpan_ayar *= 1.3

        return konusma, max(0, min(2.0, carpan_ayar))

    def tara(self, symbol_list=None):
        if symbol_list is None:
            symbol_list = BIST50

        # ADIM 1: REJİM
        self.rejim, self.rejim_guven = rejim_tespit()
        agirliklar = self.AGIRLIKLAR[self.rejim]
        min_onay = self.MIN_ONAY[self.rejim]
        pos_carpan = self.POS_CARPAN[self.rejim]

        print(f"\n🦅 ANKA V2 — Multi-Agent Karar Sistemi")
        print("=" * 70)
        print(f"📊 REJİM: {self.rejim} (güven: %{self.rejim_guven:.0f})")
        print(f"   Ağırlık: {' | '.join(f'{k}:{v:.0%}' for k,v in agirliklar.items())}")
        print(f"   Min onay: {min_onay}/4 | Pozisyon: x{pos_carpan}")
        print("=" * 70)

        bombalar = []
        tum = []

        # Makro bir kere hesapla (herkese aynı)
        macro = MacroAgent()
        macro_puan, macro_detay = macro.analiz()
        print(f"\n🌍 MAKRO DURUM: {macro_detay} (Puan: {macro_puan})")
        print("=" * 70)

        for s in symbol_list:
            try:
                df = yf.download(f"{s}.IS", period="2y", progress=False)
                if df.empty or len(df) < 60:
                    continue

                # Her ajan puanlasın
                techno_p, techno_d = TechnoAgent().analiz(df)
                volume_p, volume_d = VolumeAgent().analiz(df)
                funda_p, funda_d = FundamentalAgent().analiz(s, df)

                puanlar = {
                    "TECHNO": techno_p,
                    "VOLUME": volume_p,
                    "MACRO": macro_puan,
                    "FUNDA": funda_p,
                }

                detaylar = {
                    "TECHNO": techno_d,
                    "VOLUME": volume_d,
                    "MACRO": macro_detay,
                    "FUNDA": funda_d,
                }

                # AJANLAR KONUŞSUN
                konusma, diyalog_carpan = self.ajanlar_konussun(puanlar, detaylar, self.rejim)

                # Ağırlıklı toplam
                agirlikli_puan = sum(puanlar[a] * agirliklar.get(a, 0.25) for a in puanlar)

                # Diyalog çarpanını uygula
                agirlikli_puan *= diyalog_carpan

                # Kaç ajan "AL" diyor
                al_sayisi = sum(1 for p in puanlar.values() if p >= self.AL_ESIK)

                # VETO kontrolü
                veto = False
                veto_sebep = ""

                if diyalog_carpan == 0:
                    veto = True
                    veto_sebep = "AJAN DİYALOG VETO"
                elif macro_puan < 30:
                    veto = True
                    veto_sebep = f"MACRO VETO ({macro_detay})"
                elif al_sayisi < min_onay:
                    veto = True
                    veto_sebep = f"Oy yetersiz ({al_sayisi}/{min_onay})"

                # Final pozisyon çarpanı
                final_carpan = pos_carpan * diyalog_carpan

                # Karar
                if veto:
                    karar = "BEKLE"
                elif agirlikli_puan >= 60:
                    karar = "AL"
                elif agirlikli_puan <= 35:
                    karar = "SAT"
                else:
                    karar = "BEKLE"

                emoji = "💣" if karar == "AL" else "🔴" if karar == "SAT" else "⚪"
                veto_txt = f" VETO:{veto_sebep}" if veto else ""

                puan_txt = " ".join(f"{a[:3]}:{p}" for a, p in puanlar.items())
                print(f"\n  {emoji} {s:6} Toplam:{agirlikli_puan:5.1f} | {puan_txt} | Oy:{al_sayisi}/{min_onay} | Çarpan:x{final_carpan:.1f}{veto_txt}")

                # Ajan diyaloğunu göster
                if konusma:
                    for k in konusma:
                        print(f"      {k}")

                if karar == "AL":
                    bombalar.append(s)

                tum.append({
                    "ticker": s, "karar": karar, "puan": round(agirlikli_puan, 1),
                    "puanlar": puanlar, "al_oyu": al_sayisi, "veto": veto,
                    "pos_carpan": round(final_carpan, 2),
                    "konusma": konusma,
                })

            except:
                continue

        # ════════════════════════════════════════════════════════
        # PANEL KURALLARI — 10 Profesörün Zorunlu Filtresi
        # ════════════════════════════════════════════════════════
        try:
            from anka_panel_kurallari import SektorFiltresi, KomisyonKontrol

            # SEKTÖR FİLTRESİ: Max 2 aynı sektörden
            if bombalar:
                onaylanan, reddedilen = SektorFiltresi.filtrele(bombalar)
                if reddedilen:
                    print(f"\n🎓 PANEL SEKTÖR VETOsu:")
                    for t, s in reddedilen:
                        print(f"   ❌ {t} ({s}) — aynı sektörden çok fazla")
                bombalar = onaylanan

            # KOMİSYON FİLTRESİ: Minimum kâr hedefi uyarısı
            min_kar = KomisyonKontrol.minimum_kar_hedefi()
            print(f"\n🎓 PANEL: Minimum kâr hedefi %{min_kar:.2f} (komisyon+slippage)")

        except ImportError:
            pass

        print(f"\n{'='*70}")
        print(f"🎯 BOMBALAR: {','.join(bombalar) if bombalar else 'YOK'}")

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

        return bombalar, tum


if __name__ == "__main__":
    brain = AnkaBrain()
    bombalar, sonuclar = brain.tara()
