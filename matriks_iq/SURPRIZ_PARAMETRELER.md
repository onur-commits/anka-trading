# BIST_SURPRIZ_V1 — Surpriz Bulucu Algo

## Ne yapar?
Normal trend algonun ustune "surpriz potansiyeli" filtresi ekler.
Sadece surpriz skoru >= 60 olan anlarda islem acar.

## Surpriz Skoru nasil hesaplanir? (0-100)
- Baslangic: 50 (notr)
- RSI asiri bolge (< 30 veya > 70): +15
- Bollinger sikisma (band < %3): +15
- Fiyat band disinda: +10
- Hacim anomalisi (ortalama x1.5+): +15
- Trend gucu (> %0.5): +10

## Parametreler
```
Symbol             = GARAN
IndexSymbol        = XU100
SymbolPeriod       = Min15
BuyOrderQuantity   = 1
SellOrderQuantity  = 1
FastPeriod         = 8
SlowPeriod         = 21
RsiPeriod          = 14
RsiThreshold       = 52
BollingerPeriod    = 20
BollingerStdDev    = 2.0
UseBollingerSqueeze = true
VolumeMaPeriod     = 20
VolumeMultiplier   = 1.5
UseVolumeFilter    = true
StopLossPercent    = 2.0
TrailingStopPercent       = 1.5
TrailingActivationPercent = 1.0
BreakEvenActivationPercent = 0.8
TrendStrengthPercent      = 0.2
UseIndexFilter     = true
StartHour          = 10
StartMinute        = 0
EndHour            = 18
EndMinute          = 0
```

## V1 (ALPHA) ile farki
- V1: sadece trend + RSI + EMA
- SURPRIZ: trend + RSI + EMA + Bollinger + Hacim + Surpriz Skoru
- Daha az trade, daha kaliteli giris
