"""
DCA (Dollar-Cost Averaging) Backtest — 2 Yıl, BTC + ETH
Haftalık sabit USDT ile alım. Satış yok (buy & hold).

Varyantlar:
- DCA_BTC_only: Her hafta $25 BTC
- DCA_ETH_only: Her hafta $25 ETH
- DCA_50_50:    Her hafta $12.5 BTC + $12.5 ETH
- DCA_RSI_dip:  Normal $25, RSI<30 ise $50 (2x)

Çıktı: data/dca_backtest_rapor.md
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

VERI = Path(__file__).parent / "data" / "price_history_2yil.csv"
RAPOR = Path(__file__).parent / "data" / "dca_backtest_rapor.md"

HAFTALIK_USDT = 25.0    # haftada $25 → 104 hafta × $25 = $2600 toplam
KOMISYON = 0.001        # %0.1
SLIPPAGE = 0.0005       # %0.05
RSI_PERIYOT = 14
RSI_DIP = 30


def veri_yukle():
    """symbol → [(datetime, open, high, low, close), ...]"""
    data = defaultdict(list)
    with open(VERI, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            data[row["symbol"]].append((
                datetime.fromisoformat(row["datetime"]),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
            ))
    return data


def rsi_hesapla(kapanis_list, periyot=14):
    """Basit RSI, son değer."""
    if len(kapanis_list) < periyot + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, periyot + 1):
        delta = kapanis_list[-i] - kapanis_list[-i - 1]
        if delta > 0:
            gains.append(delta); losses.append(0)
        else:
            gains.append(0); losses.append(-delta)
    avg_g = sum(gains) / periyot
    avg_l = sum(losses) / periyot
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - (100 / (1 + rs))


def dca_calistir(bars_btc, bars_eth, varyant: str):
    """
    Haftalık DCA simülasyonu. Haftanın ilk barında (Pazartesi 00:00 UTC veya ilk bar) alım.
    Dönem başı T0, son fiyatla değerlendirme.
    Dönüş: (toplam_yatirilan, son_deger, islem_sayisi)
    """
    # Haftaları belirle: her haftanın ilk barının indexi
    # bars_btc ve bars_eth aynı zamanı kapsıyor varsayımı (2024-04-19 → 2026-04-19)
    # Zaman eşitle
    zaman_btc = [b[0] for b in bars_btc]
    zaman_eth = [b[0] for b in bars_eth]
    # BTC ve ETH aynı timestamp'lerde olmalı; değilse intersect
    zaman_set = set(zaman_btc) & set(zaman_eth)

    # Hızlı erişim için dict
    btc_dict = {b[0]: b[4] for b in bars_btc}  # close
    eth_dict = {b[0]: b[4] for b in bars_eth}

    # Hafta başlangıçlarını bul (haftanın ilk bar'ı - monday 00:00)
    hafta_barlari = []
    son_hafta_no = -1
    for t in sorted(zaman_set):
        hafta_no = t.isocalendar()[1] + t.year * 100  # unique hafta ID
        if hafta_no != son_hafta_no:
            hafta_barlari.append(t)
            son_hafta_no = hafta_no

    # RSI için kapanış listesi
    btc_kapanis = []
    eth_kapanis = []
    btc_idx = 0
    eth_idx = 0

    btc_coin = 0.0
    eth_coin = 0.0
    toplam_yatirilan = 0.0
    islem_sayisi = 0

    for t in hafta_barlari:
        # RSI için son 20 kapanışı topla (yavaş ama basit)
        btc_k = [b[4] for b in bars_btc if b[0] <= t][-20:]
        eth_k = [b[4] for b in bars_eth if b[0] <= t][-20:]
        if len(btc_k) < 2 or len(eth_k) < 2:
            continue

        btc_p = btc_dict[t] * (1 + SLIPPAGE)  # alırken slip+
        eth_p = eth_dict[t] * (1 + SLIPPAGE)

        if varyant == "DCA_BTC_only":
            usdt = HAFTALIK_USDT
            btc_coin += (usdt * (1 - KOMISYON)) / btc_p
            toplam_yatirilan += usdt
            islem_sayisi += 1
        elif varyant == "DCA_ETH_only":
            usdt = HAFTALIK_USDT
            eth_coin += (usdt * (1 - KOMISYON)) / eth_p
            toplam_yatirilan += usdt
            islem_sayisi += 1
        elif varyant == "DCA_50_50":
            usdt = HAFTALIK_USDT / 2
            btc_coin += (usdt * (1 - KOMISYON)) / btc_p
            eth_coin += (usdt * (1 - KOMISYON)) / eth_p
            toplam_yatirilan += HAFTALIK_USDT
            islem_sayisi += 2
        elif varyant == "DCA_RSI_dip":
            btc_rsi = rsi_hesapla(btc_k, RSI_PERIYOT)
            eth_rsi = rsi_hesapla(eth_k, RSI_PERIYOT)
            btc_usdt = HAFTALIK_USDT / 2 * (2 if btc_rsi < RSI_DIP else 1)
            eth_usdt = HAFTALIK_USDT / 2 * (2 if eth_rsi < RSI_DIP else 1)
            btc_coin += (btc_usdt * (1 - KOMISYON)) / btc_p
            eth_coin += (eth_usdt * (1 - KOMISYON)) / eth_p
            toplam_yatirilan += btc_usdt + eth_usdt
            islem_sayisi += 2

    # Son fiyat ile değerlendir
    son_t = max(zaman_set)
    son_btc_p = btc_dict[son_t]
    son_eth_p = eth_dict[son_t]
    son_deger = btc_coin * son_btc_p + eth_coin * son_eth_p

    return toplam_yatirilan, son_deger, islem_sayisi, btc_coin, eth_coin


def main():
    print("Veri yükleniyor...")
    data = veri_yukle()
    bars_btc = sorted(data["BTCUSDT"], key=lambda x: x[0])
    bars_eth = sorted(data["ETHUSDT"], key=lambda x: x[0])
    print(f"BTC: {len(bars_btc)} bar, ETH: {len(bars_eth)} bar")
    print(f"Dönem: {bars_btc[0][0].date()} → {bars_btc[-1][0].date()}")
    print()

    # B&H referansı (baştan tek seferde al, sonda değerle)
    bh_btc_p0 = bars_btc[0][4] * (1 + SLIPPAGE)
    bh_btc_pN = bars_btc[-1][4]
    bh_btc_pct = (bh_btc_pN / bh_btc_p0 * (1 - KOMISYON) - 1) * 100

    bh_eth_p0 = bars_eth[0][4] * (1 + SLIPPAGE)
    bh_eth_pN = bars_eth[-1][4]
    bh_eth_pct = (bh_eth_pN / bh_eth_p0 * (1 - KOMISYON) - 1) * 100

    print(f"B&H BTC (tek seferde): {bh_btc_pct:+.2f}%")
    print(f"B&H ETH (tek seferde): {bh_eth_pct:+.2f}%")
    print()

    sonuclar = []
    for v in ["DCA_BTC_only", "DCA_ETH_only", "DCA_50_50", "DCA_RSI_dip"]:
        yat, deger, ks, btc_c, eth_c = dca_calistir(bars_btc, bars_eth, v)
        getiri = (deger / yat - 1) * 100 if yat > 0 else 0
        kar = deger - yat
        print(f"[{v:14s}] Yatırılan: ${yat:.0f} | Değer: ${deger:.2f} | "
              f"Getiri: {getiri:+.2f}% | Kâr: ${kar:+.2f} | İşlem: {ks}")
        sonuclar.append({
            "varyant": v,
            "yatirilan": yat,
            "deger": deger,
            "getiri": getiri,
            "kar": kar,
            "islem": ks,
            "btc_coin": btc_c,
            "eth_coin": eth_c,
        })

    # Rapor
    lines = []
    lines.append("# DCA Backtest Raporu — 2 Yıl (2024-04 → 2026-04)")
    lines.append("")
    lines.append(f"**Haftalık alım:** ${HAFTALIK_USDT}")
    lines.append(f"**Komisyon:** %0.1  |  **Slippage:** %0.05")
    lines.append(f"**Dönem:** {bars_btc[0][0].date()} → {bars_btc[-1][0].date()} ({len(bars_btc)} saatlik bar)")
    lines.append("")
    lines.append("## Referans: Buy & Hold (tek seferde al, sonda sat)")
    lines.append("")
    lines.append(f"- BTC B&H: **{bh_btc_pct:+.2f}%**")
    lines.append(f"- ETH B&H: **{bh_eth_pct:+.2f}%**")
    lines.append("")
    lines.append("## DCA Sonuçları")
    lines.append("")
    lines.append("| Varyant | Yatırılan | Son Değer | Getiri | Kâr | İşlem | BTC | ETH |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for s in sonuclar:
        lines.append(
            f"| {s['varyant']} | ${s['yatirilan']:.0f} | ${s['deger']:.2f} | "
            f"{s['getiri']:+.2f}% | ${s['kar']:+.2f} | {s['islem']} | "
            f"{s['btc_coin']:.5f} | {s['eth_coin']:.4f} |"
        )
    lines.append("")
    lines.append("## Yorum")
    lines.append("")
    lines.append("- **DCA getirisi**, zamanla yayılmış alım nedeniyle B&H'dan farklıdır.")
    lines.append("- Volatil dönemde (düşüş varsa) DCA, B&H'ı geçebilir (ucuzken çok alım).")
    lines.append("- Trendde (yükseliş) B&H genelde DCA'dan iyidir (erken alım kazanır).")
    lines.append("- RSI_dip varyantı: RSI<30 haftalarda 2x alım yapar.")

    RAPOR.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapor yazıldı: {RAPOR}")


if __name__ == "__main__":
    main()
