# BIST_ALPHA_CORE_V1 — Final Parametre Seti

## Backtest Sonucu
- Getiri: +12% (1 yil)
- Max DD: -1.19%
- Trade: ~930

## Kilitli Parametreler (DEGISTIRME)
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
StopLossPercent    = 2.0
TrailingStopPercent       = 1.5
TrailingActivationPercent = 1.0
BreakEvenActivationPercent = 0.8
TrendStrengthPercent      = 0.3
UseIndexFilter     = true
StartHour          = 10
StartMinute        = 0
EndHour            = 18
EndMinute          = 0
```

## Komisyon
- Strateji Secenekleri > Komisyon Orani = 0.0004

## Onemli Notlar
- DateTime.Now KULLANMA — barData.BarData.Dtime kullan
- CrossAbove/CrossBelow YOK — fastMov > slowMov mantigi
- Midas islem yetkisi acik olmali (API/algo yetkisi)

## Canli Gecis Plani
1. 1 lot ile basla
2. Sadece GARAN
3. 1 hafta gozlem
4. Sonra THYAO, ASELS ekle
5. Lot arttir
