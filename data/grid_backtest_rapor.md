# Grid Backtest Raporu — 2 Yıl (2024-04 → 2026-04)

**Sermaye:** $2000.0 (her sembol için)
**Komisyon:** %0.1 (taker)
**Slippage:** %0.05

## Sonuçlar

| Sembol | Strateji | Aralık | Kademe | Grid % | B&H % | Fark | Tam. Çift | Kar $ |
|---|---|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | FullRange_20k | $49000-$126200 | 20 | -14.41% | +20.70% | -35.11% | 114 | $450.41 |
| BTCUSDT | FullRange_40k | $49000-$126200 | 40 | -14.91% | +20.70% | -35.61% | 474 | $425.16 |
| BTCUSDT | FullRange_80k | $49000-$126200 | 80 | -15.16% | +20.70% | -35.86% | 2118 | $397.84 |
| BTCUSDT | DarAralik40_20k | $41521-$96883 | 20 | -4.10% | +20.70% | -24.80% | 148 | $370.02 |
| BTCUSDT | DarAralik40_40k | $41521-$96883 | 40 | -4.37% | +20.70% | -25.07% | 616 | $332.25 |
| ETHUSDT | FullRange_20k | $1385-$4957 | 20 | -22.75% | -22.76% | +0.02% | 156 | $616.01 |
| ETHUSDT | FullRange_40k | $1385-$4957 | 40 | -23.39% | -22.76% | -0.62% | 622 | $578.93 |
| ETHUSDT | FullRange_80k | $1385-$4957 | 80 | -23.71% | -22.76% | -0.95% | 2639 | $518.73 |
| ETHUSDT | DarAralik40_20k | $1617-$3773 | 20 | -13.67% | -22.76% | +9.10% | 310 | $794.72 |
| ETHUSDT | DarAralik40_40k | $1617-$3773 | 40 | -14.13% | -22.76% | +8.63% | 1289 | $732.16 |

## Yorum

- **Grid %** = grid bot'un net getirisi (başlangıç vs. son portföy, kapatılmamış dahil)
- **B&H %** = buy-and-hold (başta al, sonda sat) getirisi
- **Fark** = Grid B&H'dan ne kadar iyi (pozitif = grid kazandı)
- **Tamamlanan Çift** = kaç kez al-sat döngüsü kapandı (gerçekleşmiş kâr üretir)