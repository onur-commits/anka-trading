Warning: Permanently added '78.135.87.29' (ED25519) to the list of known hosts.
## Ozet (OUT-OF-SAMPLE, look-ahead YOK)
- **Genel OOS AUC:** 0.5670
- **Ort. net trade getirisi:** %+0.446 (komisyon+slippage dahil)
- **Benchmark (endeks Al&Tut):** %+161.4
## Fold detay
| Fold | Donem | Train | Test | AUC | Trade | Kazanc% | OrtNet% |
|---|---|---|---|---|---|---|---|
## Yorum
- backtest_bist.py (in-sample) ile FARK = look-ahead'in sismesi.
- Edge pozitifse: canli MIN_BOMBA_SKOR_ALIS / PROBA_ESIK kalibre edilir.
- Edge negatifse: sinyal zayif -> feature muhendisligi (kesitsel/rejim) sart.
