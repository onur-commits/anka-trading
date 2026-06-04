# 🦅 BIST Walk-Forward Backtest — DURUST OOS edge

_2026-06-04 21:01 · kaynak: CSV smoke-test (price_history_2yil.csv)_

## Ozet (OUT-OF-SAMPLE, look-ahead YOK)

- **Genel OOS AUC:** 0.5526
- **Fold sayisi:** 3  ·  OOS donem: 2025-09-09 00:00:00+00:00 → 2026-03-08 00:00:00+00:00
- **Toplam OOS trade:** 239  ·  Kazanc orani: %54.0
- **Ort. net trade getirisi:** %+0.174 (komisyon+slippage dahil)
- **Bilesik OOS getiri:** %+14.4  ·  Max drawdown: %-10.4  ·  Sharpe(trade): 0.100

## Fold detay

| Fold | Donem | Train | Test | AUC | Trade | Kazanc% | OrtNet% |
|---|---|---|---|---|---|---|---|
| 1 | 2025-09-09→2025-11-08 | 506 | 122 | 0.6026 | 76 | %57.9 | %+0.28 |
| 2 | 2025-11-08→2026-01-07 | 626 | 122 | 0.4951 | 78 | %64.1 | %+0.544 |
| 3 | 2026-01-07→2026-03-08 | 746 | 122 | 0.5887 | 85 | %41.2 | %-0.259 |

## Yorum
- Bu sayilar **gercek OOS** — model her fold'da sadece gecmisi gordu, etiket sizintisi embargo ile engellendi.
- backtest_bist.py (in-sample) ile FARK = look-ahead'in sismesi.
- Edge pozitifse: canli MIN_BOMBA_SKOR_ALIS / PROBA_ESIK kalibre edilir.
- Edge negatifse: sinyal zayif -> feature muhendisligi (kesitsel/rejim) sart.