"""Tek seferlik detayli coin tarama testi."""
import sys
sys.path.insert(0, "C:\\ANKA")
from coin_otonom import *

client = BinanceClient()
btc_df = client.kline("BTCUSDT", "1h", 100)

print(f"BTC: ${float(btc_df['Close'].iloc[-1]):.0f}")
m_puan, m_detay = macro_analiz(btc_df)
print(f"Macro: {m_puan} ({m_detay})")
print()
print(f"{'Symbol':12} {'Fiyat':>10} {'T':>4} {'V':>4} {'M':>4} {'Skor':>6} {'RSI':>5} {'KomOK':>6} {'Karar'}")
print("-" * 75)

for sym in COINS:
    try:
        df = client.kline(sym, "1h", 100)
        if len(df) < 50:
            continue
        t_p, td = techno_analiz(df)
        v_p, vd = volume_analiz(df)
        toplam = t_p * 0.4 + v_p * 0.3 + m_puan * 0.3

        fiyat = float(df["Close"].iloc[-1])
        atr = atr_hesapla(df)
        atr_pct = (atr / fiyat) * 100
        bek = atr_pct * 0.4
        ok, net = komisyon_karli_mi(bek)

        # RSI
        c = df["Close"]
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = float((100 - (100 / (1 + gain / (loss + 1e-10)))).iloc[-1])

        karar = "AL" if toplam >= MIN_SKOR and ok else ("KOM" if toplam >= MIN_SKOR else "BEKLE")
        marker = " <<<" if karar == "AL" else ""
        print(f"{sym:12} ${fiyat:>9.2f} {t_p:4} {v_p:4} {m_puan:4} {toplam:6.1f} {rsi:5.0f} {'OK' if ok else 'NO':>6} {karar}{marker}")
    except Exception as e:
        print(f"{sym:12} HATA: {e}")

print()
# Mevcut SOL pozisyonu
sol_fiyat = client.fiyat("SOLUSDT")
sol_miktar = client.bakiye_coin("SOL")
print(f"Mevcut SOL: {sol_miktar:.4f} x ${sol_fiyat:.2f} = ${sol_miktar*sol_fiyat:.2f}")
print(f"USDT: ${client.bakiye_usdt():.2f}")
