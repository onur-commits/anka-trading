# ANKA Backtest v2 — Sonuç Raporu

**Tarih:** 2026-04-18 16:01
**Dönem:** Son 365 gün (1h mumlar)
**Semboller:** BNBUSDT, ATOMUSDT, BTCUSDT, MOVRUSDT
**Başlangıç sermaye:** $2500.00
**Komisyon/yön:** %0.1 | **Slippage/yön:** %0.1

## Parametreler
- MIN_SKOR_AL: **65**
- Stop-loss: **%7.0**
- Trailing başlangıç: **+%3.0** üstünden **-%3.0**
- TP1: **+%8.0** (yarısı) | TP2: **+%15.0** (tamamı)
- Max pozisyon: **5**

## Skor formülü
`SKOR = TEK*0.30 + HAC*0.20 + MAK*0.15 + LIK*0.10 + SEN*0.15 + FUN*0.10`

## Özet Tablo

| Strateji | Bitiş $ | Getiri % | Trade | Winrate | Ort Kazanç | Ort Kayıp | MaxDD | Sharpe~ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A) Baseline (teknik+hacim) | $1791.30 | -28.3% | 330 | 61.2% | +3.55% | -6.25% | 42.1% | -1.06 |
| B) v2 Full (SEN+FUN trend) | $1983.80 | -20.6% | 301 | 63.5% | +3.45% | -6.29% | 38.0% | -0.72 |
| C) v2 Kontrarian F&G | $1856.26 | -25.7% | 366 | 61.7% | +3.66% | -6.28% | 38.6% | -0.87 |

## A) Baseline (teknik+hacim)

- Başlangıç → Bitiş: **$2500.00 → $1791.30**
- Toplam getiri: **-28.35%**
- İşlem: 330 (kazanan 202, kaybeden 128)
- Winrate: **61.2%**
- Max drawdown: **42.1%**
- Sharpe-benzeri (yıllık): **-1.06**

### İlk 5 işlem
| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |
|---|---|---|---:|---|---:|
| 2025-04-20T19:00 | MOVRUSDT | AL | 5.71571 | SKOR=76.7 | — |
| 2025-04-20T20:00 | BTCUSDT | AL | 85212.70758 | SKOR=69.4 | — |
| 2025-04-20T21:00 | MOVRUSDT | SAT | 5.855848 | STOP | +2.35 |
| 2025-04-20T21:00 | MOVRUSDT | AL | 5.621616 | SKOR=65.2 | — |
| 2025-04-21T00:00 | BNBUSDT | AL | 598.30771 | SKOR=78.1 | — |

### Son 5 işlem
| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |
|---|---|---|---:|---|---:|
| 2026-04-17T16:00 | MOVRUSDT | SAT | 3.579116 | TP1 | +7.78 |
| 2026-04-17T17:00 | MOVRUSDT | SAT | 3.752084 | STOP | +12.99 |
| 2026-04-18T10:00 | ATOMUSDT | SAT | 1.809179 | STOP | +0.31 |
| 2026-04-18T11:00 | BTCUSDT | SAT | 75907.02699 | STOP | +1.00 |
| 2026-04-18T15:00 | BNBUSDT | SAT | 633.89 | EOT | +4.42 |

## B) v2 Full (SEN+FUN trend)

- Başlangıç → Bitiş: **$2500.00 → $1983.80**
- Toplam getiri: **-20.65%**
- İşlem: 301 (kazanan 191, kaybeden 110)
- Winrate: **63.5%**
- Max drawdown: **38.0%**
- Sharpe-benzeri (yıllık): **-0.72**

### İlk 5 işlem
| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |
|---|---|---|---:|---|---:|
| 2025-04-20T19:00 | MOVRUSDT | AL | 5.71571 | SKOR=74.8 | — |
| 2025-04-20T20:00 | BTCUSDT | AL | 85212.70758 | SKOR=68.9 | — |
| 2025-04-20T21:00 | MOVRUSDT | SAT | 5.855848 | STOP | +2.35 |
| 2025-04-21T00:00 | BNBUSDT | AL | 598.30771 | SKOR=79.5 | — |
| 2025-04-21T00:00 | MOVRUSDT | AL | 5.710705 | SKOR=65.9 | — |

### Son 5 işlem
| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |
|---|---|---|---:|---|---:|
| 2026-04-17T16:00 | MOVRUSDT | SAT | 3.579116 | TP1 | +7.78 |
| 2026-04-17T17:00 | MOVRUSDT | SAT | 3.752084 | STOP | +12.99 |
| 2026-04-18T10:00 | ATOMUSDT | SAT | 1.809179 | STOP | +0.03 |
| 2026-04-18T11:00 | BTCUSDT | SAT | 75907.02699 | STOP | +1.00 |
| 2026-04-18T15:00 | BNBUSDT | SAT | 633.89 | EOT | +4.37 |

## C) v2 Kontrarian F&G

- Başlangıç → Bitiş: **$2500.00 → $1856.26**
- Toplam getiri: **-25.75%**
- İşlem: 366 (kazanan 226, kaybeden 140)
- Winrate: **61.7%**
- Max drawdown: **38.6%**
- Sharpe-benzeri (yıllık): **-0.87**

### İlk 5 işlem
| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |
|---|---|---|---:|---|---:|
| 2025-04-20T18:00 | MOVRUSDT | AL | 5.486481 | SKOR=65.8 | — |
| 2025-04-20T19:00 | MOVRUSDT | SAT | 5.919474 | TP1 | +7.78 |
| 2025-04-20T20:00 | MOVRUSDT | SAT | 5.855848 | STOP | +6.63 |
| 2025-04-20T20:00 | MOVRUSDT | AL | 5.61561 | SKOR=81.5 | — |
| 2025-04-20T20:00 | BTCUSDT | AL | 85212.70758 | SKOR=73.9 | — |

### Son 5 işlem
| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |
|---|---|---|---:|---|---:|
| 2026-04-17T22:00 | MOVRUSDT | AL | 3.011008 | SKOR=66.1 | — |
| 2026-04-18T00:00 | MOVRUSDT | SAT | 3.096051 | STOP | +2.72 |
| 2026-04-18T10:00 | ATOMUSDT | SAT | 1.809179 | STOP | +0.53 |
| 2026-04-18T11:00 | BTCUSDT | SAT | 75907.02699 | STOP | +1.84 |
| 2026-04-18T15:00 | BNBUSDT | SAT | 633.89 | EOT | +3.97 |

## Yorum

- **SEN + FUN dahil etmek getiriyi +7.7 puan değiştirdi** (-28.3% → -20.6%).
- Kontrarian F&G (-25.7%) bu dönemde trend-following'e (-20.6%) göre **daha zayıf**.
- Not: Bu backtest survivorship-bias içerebilir (sadece MOVR/ATOM/BNB/BTC).
- Not: Funding rate sadece futures'a yansır; spot'ta dolaylı etkidir.
- Not: F&G günlük, funding 8h/4h — skor yavaş değişir. İntraday sinyal değil rejim filtresi olarak güçlü.
