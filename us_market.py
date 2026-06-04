"""
ABD Piyasası Modülü (us_market) — paket için BIST + US çoklu piyasa
====================================================================
BIST'le aynı tarama/skor mantığı, US hisseleri + US borsa saatleri için.
Veri: yfinance (US ticker'lar, .IS eki YOK). Saat: ABD/Doğu (ET).

NOT: Bu modül bağımsız — canlı BIST botuna dokunmaz. Paket branch'inde
geliştiriliyor. 'birleştir' komutuyla main'e alınır.
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

# ── US likit hisse evreni (S&P / Nasdaq aktif isimler) ──
US_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX",
    "AVGO", "JPM", "BAC", "XOM", "CVX", "PFE", "KO", "PEP", "DIS", "INTC",
    "CSCO", "ORCL", "CRM", "QCOM", "TXN", "BA", "CAT", "GE", "F", "GM",
    "PLTR", "SOFI", "COIN", "MARA", "RIOT", "SNAP", "UBER", "ABNB", "SHOP",
    # Nadir toprak / madencilik (kullanıcının REE ilgisi)
    "MP", "VALE", "FCX", "ALB", "LAC", "REMX",
]

ET = ZoneInfo("America/New_York")
TR = ZoneInfo("Europe/Istanbul")

# US borsa saatleri (ET): 09:30 - 16:00, hafta içi
US_ACILIS = time(9, 30)
US_KAPANIS = time(16, 0)


def us_borsa_acik_mi(simdi=None):
    """ABD borsası şu an açık mı? (ET saatine göre, hafta içi)"""
    now = simdi or datetime.now(ET)
    if now.weekday() >= 5:  # Cmt/Pzr
        return False
    return US_ACILIS <= now.time() <= US_KAPANIS


def tr_karsiligi(et_saat_str="09:30"):
    """ET saatini TR saatine çevir (kullanıcı BIST saatinde düşünüyor)."""
    h, m = map(int, et_saat_str.split(":"))
    bugun = datetime.now(ET).replace(hour=h, minute=m, second=0, microsecond=0)
    return bugun.astimezone(TR).strftime("%H:%M")


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = -d.clip(upper=0).rolling(n).mean()
    return 100 - 100 / (1 + up / dn)


def us_skor(df):
    """BIST basit_skor ile aynı mantık — US hissesi için teknik skor."""
    c, v = df["Close"], df["Volume"]
    son, onc = c.iloc[-1], c.iloc[-2]
    g5 = c.iloc[-5] if len(c) > 5 else onc
    dg = float((son / onc - 1) * 100)
    m5 = float((son / g5 - 1) * 100)
    r = float(rsi(c).iloc[-1])
    ov = float(v.rolling(20).mean().iloc[-1]) if len(v) > 20 else 1
    ho = float(v.iloc[-1]) / ov if ov > 0 else 1
    sk = 0
    if dg > 1: sk += 15
    if dg > 3: sk += 10
    if m5 > 0: sk += 10
    if m5 > 5: sk += 10
    if 40 < r < 70: sk += 15
    if ho > 1.5: sk += 20
    if ho > 3: sk += 10
    return float(sk), {"degisim": round(dg, 2), "mom5": round(m5, 2),
                       "rsi": round(r, 1), "hacim_oran": round(ho, 2)}


def us_tara(min_skor=25, limit=10):
    """US evrenini tara, skor >= min_skor olanları döndür (yfinance)."""
    import yfinance as yf
    sonuc = []
    for t in US_TICKERS:
        try:
            df = yf.download(t, period="3mo", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if len(df) < 30:
                continue
            skor, detay = us_skor(df)
            if skor >= min_skor:
                sonuc.append({"ticker": t, "skor": skor,
                              "fiyat": round(float(df["Close"].iloc[-1]), 2),
                              **detay})
        except Exception:
            continue
    sonuc.sort(key=lambda x: x["skor"], reverse=True)
    return sonuc[:limit]


if __name__ == "__main__":
    print("=== ABD PİYASASI MODÜLÜ ===")
    print(f"US borsa açık mı: {us_borsa_acik_mi()}")
    print(f"US açılış 09:30 ET = TR {tr_karsiligi('09:30')}")
    print(f"US kapanış 16:00 ET = TR {tr_karsiligi('16:00')}")
    print(f"Evren: {len(US_TICKERS)} hisse")
    print("\nTarama (skor>=25)...")
    for x in us_tara():
        print(f"  {x['ticker']:6} skor {x['skor']:.0f}  ${x['fiyat']}  "
              f"deg {x['degisim']:+.1f}%  hacim x{x['hacim_oran']}")
