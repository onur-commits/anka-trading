# Matriks IQ Strateji Rehberi - ANKA Trading

## Built-In Stratejiler (66 Adet)

### AI Stratejileri
| Strateji | Aciklama |
|----------|----------|
| AI_BISTBanka_60dk_Yukselis_Strateji | BIST banka hisseleri 60dk yukselis AI |
| AI_EndeksVadeli_5dk_CiftYonluIslem_Strateji | Endeks vadeli 5dk cift yonlu islem |
| AI_PayVadeli_5dk_CiftYonluIslem_Strateji | Pay vadeli 5dk cift yonlu islem |
| LogisticReg | Lojistik regresyon ML strateji |
| SVMPriceRSI | SVM fiyat + RSI ML strateji |

### Trend Takip Stratejileri
| Strateji | Indikatör | Aciklama |
|----------|-----------|----------|
| SMAStrategy | SMA | Basit hareketli ortalama |
| EMAStrategy | EMA | Ustel hareketli ortalama |
| WMAStrategy | WMA | Agirlikli hareketli ortalama |
| HullMAStrategy | Hull MA | Hull hareketli ortalama (gecikme az) |
| KAMAStrategy | KAMA | Uyarlanabilir hareketli ortalama |
| TMAStrategy | TMA | Ucgensel hareketli ortalama |
| VMAStrategy | VMA | Degisken hareketli ortalama |
| CrossMov | MOV Cross | Hareketli ortalama kesisimi |
| FAMOVStrategy | FAMOV | FAMOV indikatoru |
| WildersStrategy | Wilders | Wilders hareketli ortalama |
| ZeroLagStrategy | Zero Lag | Gecikmeiz hareketli ortalama |
| FTStrategy | FT | Fisher Transform |
| TSFStrategy | TSF | Time Series Forecast |
| LRLStrategy | LRL | Lineer Regresyon |
| LRSStrategy | LRS | Lineer Regresyon Slope |

### Momentum Stratejileri
| Strateji | Indikatör | Aciklama |
|----------|-----------|----------|
| SimpleRSI_SMA | RSI + SMA | RSI ile SMA kombinasyonu |
| BolRsiStrategy | Bollinger + RSI | Bollinger bantlari + RSI |
| StochasticFastStrategy | Stochastic Fast | Hizli stokastik |
| StochasticSlow_ADX | Stochastic Slow + ADX | Yavas stokastik + trend gucu |
| StochSMA_Strategy | Stochastic + SMA | Stokastik + SMA birlesimi |
| DIStrategy | DI+/DI- | Yonsel hareket indeksi |

### MOST / PMAX Stratejileri
| Strateji | Aciklama |
|----------|----------|
| MostStrategy | MOST indikatoru |
| Most3 | MOST 3 cizgili versiyon |
| MostDICross | MOST + DI kesisim |
| MostStrategy_Future | MOST vadeli islemler icin |
| PMAX_Strategy | PMAX (Profit Maximizer) |
| TOTTStrategy | TOTT (Tilt Optimized Trend Tracker) |
| TillsonStrategy | Tillson T3 |
| TillsonNoCrossViop | Tillson kesisimsiz VİOP |
| SimpleTMAHullMA | TMA + Hull MA kombinasyonu |

### Parabolic / ATR Stratejileri
| Strateji | Aciklama |
|----------|----------|
| ParabolicSAR_Strategy | Parabolic SAR |
| ParabolicSAR_Future | Parabolic SAR vadeli |
| ATRPrevTrail | ATR bazli trailing stop |

### Bant / Kanal Stratejileri
| Strateji | Aciklama |
|----------|----------|
| ACCBandsIndicator | Acceleration Bands |
| EnvelopeStrategy | Envelope (zarf) bantlari |
| PmR3_Strategy | PmR3 bant stratejisi |

### Ozel Sinyal Stratejileri
| Strateji | Aciklama |
|----------|----------|
| TomDeMarkStandard | Tom DeMark standart |
| TomDemarkStrategy | Tom DeMark gelismis |
| SerialUp | Ardisik yukselis sayaci |
| PriceAbove7Day | Fiyat 7 gunun uzerinde |
| TrendStrategy | Genel trend takibi |
| Yesilyol | Matriks ozel "Yesilyol" stratejisi |
| SteppedStrategy | Kademeli al/sat |
| HeikenAshi_Futures | Heiken Ashi vadeli |

### Derinlik / Kurum Takip
| Strateji | Aciklama |
|----------|----------|
| Depth3 | 3 kademe derinlik analizi |
| ClearedLevelsDepthTemplate | Temizlenen derinlik seviyeleri |
| MarketDepth3Timer | Zamanlayicili derinlik |
| BrokerageFirmTracking | Araci kurum takibi |
| AlgoDetector | Algoritmik islem tespiti |
| AlgoFormation | Formasyon tespiti |

### Haber / Zaman Stratejileri
| Strateji | Aciklama |
|----------|----------|
| NewsStrategy | Haber bazli islem |
| TimedStrategy | Zamanlayicili strateji |
| DailyWeightedAverage | Gunluk agirlikli ortalama |
| SevenDaysWeightedAverage | 7 gunluk agirlikli ortalama |
| DWA2Instruments | 2 enstruman DWA |

### Emir Yonetimi
| Strateji | Aciklama |
|----------|----------|
| MultiLevelLimitOrders | Cok kademeli limit emirleri |
| SMA_Futures_TPSL | SMA + TP/SL vadeli |
| PermanentTemporarySignal | Kalici/gecici sinyal yonetimi |

### Grafik / Veri
| Strateji | Aciklama |
|----------|----------|
| CustomChart | Ozel grafik olusturma |
| OHLCT_Buffer | OHLC tampon |
| OHLCT_OnTimer | OHLC zamanlayici |

---

## Kullanilabilir API Fonksiyonlari

### Veri Erisim
```csharp
AddSymbol(symbol, period)              // Grafik datasina kayit
AddSymbolMarketData(symbol)            // Yuzeysel dataya kayit
AddSymbolMarketDepth(symbol)           // Derinlik datasina kayit
AddSymbolTickData(symbol)              // Tick datasina kayit
AddNewsSymbol(symbol)                  // Haber filtresi sembolu
AddNewsKeyword(keyword, onlyHeaders, exactMatch)  // Haber anahtar kelime
AddMemberTickData(memberId)            // Kurum tick datasi
AddDetectorMember(memberId)            // Kurum dedektoru
GetBarData(symbol, period)             // BarData erisim
GetMarketData(symbol, field)           // Yuzeysel veri
GetMarketDepth(symbol)                 // Derinlik verisi
```

### Indikatör Olusturma
```csharp
MOVIndicator(symbol, period, ohlcType, length, method)  // Hareketli Ortalama
RSIIndicator(symbol, period, ohlcType, length)           // RSI
// MovMethod: Simple, Exponential, Weighted, Triangular, Variable, Hull, KAMA, ZeroLag, Wilders, FAMA
```

### Sinyal Fonksiyonlari
```csharp
CrossAbove(indicator1, indicator2)     // Yukari kesisin
CrossBelow(indicator1, indicator2)     // Asagi kesisim
CrossAbove(barData, indicator, ohlcType)  // Fiyat indikatoru yukari kirdi
CrossBelow(indicator, value)           // Indikatör degeri asagi kirdi
Ref(indicator, period)                 // N bar onceki deger
Cumulate(indicator)                    // Kumulatif toplam
HighestHigh(indicator, period)         // En yuksek
LowestLow(indicator, period)           // En dusuk
Increasing(indicator, period)          // Artan mi
Decreasing(indicator, period)          // Azalan mi
MyTrend(indicator, period)             // Trend yonu
```

### Emir Gonderme
```csharp
SendMarketOrder(symbol, qty, side)                  // Piyasa emri
SendLimitOrder(symbol, qty, price, side)             // Limit emri

// Aciga Satis
SendShortSaleMarketOrder(symbol, qty)
SendShortSaleLimitOrder(symbol, qty, price)
SendMarketCloseShortOrder(symbol, qty)
SendLimitCloseShortOrder(symbol, qty, price)

// VİOP
SendViopStopLimitOrder(symbol, qty, stopPrice, limitPrice, side)

// Binance
SendBinanceStopLimitOrder(symbol, qty, stopPrice, limitPrice, side)
SendBinanceTakeProfitLimitOrder(symbol, qty, stopPrice, limitPrice, side)
SendBinanceStopMarketOrder(symbol, qty, stopPrice, side)
SendBinanceTakeProfitMarketOrder(symbol, qty, stopPrice, side)
SendBinanceTpSlLimitOrder(symbol, qty, tpPrice, slPrice, limitPrice, side)
SendBinanceTpSlMarketOrder(symbol, qty, tpPrice, slPrice, side)
SendBinanceTrailingStopOrder(symbol, qty, callbackRate, side)

// Stop/TP
StopLoss(symbol, params)
TakeProfit(symbol, params)
TrailingStopLoss(symbol, params)
```

### Emir Kontrol
```csharp
SendOrderSequential(true)              // Bir al bir sat
SendOrderSequential(true, side)        // Baslama yonu belirle
WorkWithPermanentSignal(true)          // Her barda calis (false: her tick)
```

### Bildirim
```csharp
Debug(message)                          // Debug log
Alert(message)                          // Masaustu alarm
PushMobile(group, title, message)       // Mobil bildirim
SendTelegramBot(message)                // Telegram mesaji
SendMail(subject, message)              // Email
WriteCustomLog(data, filename)          // Ozel log dosyasi
```

### Portfoy / Hesap
```csharp
GetPortfolio()                          // Portfoy bilgisi
BistOverall                             // BIST toplam
BistBalance                             // BIST bakiye
BistProfitLoss                          // BIST kar/zarar
BistAvailableMargin                     // Kullanilabilir teminat
ViopOverall / ViopBalance / ViopProfitLoss / ViopAvailableMargin
```

### Diger
```csharp
SetTimerInterval(seconds)               // Timer ayarla
SetTimerIntervalMS(milliseconds)        // Timer (ms)
RestartStrategy(background)             // Stratejiyi yeniden baslat
GetCurrentMatriksIqVersion()            // IQ versiyonu
GetPriceStepForBistViop(symbol, price)  // Fiyat adimi
RoundPriceStepBistViop(symbol, price)   // Fiyat adimina yuvarla
AddChart(chartName)                     // Ozel grafik
Plot(chartName, value)                  // Grafige ciz
GetSelectedValueFromBarData(barData, ohlcType)  // OHLC secimi
TakasIndicator(symbol, params)          // Takas gostergesi
TakasOraniIndicator(symbol, params)     // Takas orani gostergesi
```

### Olay Fonksiyonlari (Override)
```csharp
OnInit()                    // Ilk kurulum
OnInitCompleted()           // Kurulum tamamlandi
OnDataUpdate(barData)       // Yeni bar geldi
OnOrderUpdate(order)        // Emir durumu degisti
OnTickDataReceived(tick)    // Tick geldi
OnTimer()                   // Timer tetiklendi
OnNewsReceived(id, news)    // Haber geldi
OnDetectorReceived(data)    // Dedektör sinyali
OnFormationReceived(data)   // Formasyon tespiti
OnStopped()                 // Strateji durdu
```

---

## Mevcut ANKA Stratejileri

### BIST_ALPHA_CORE_V1
- **Tip:** EMA Cross + RSI + Endeks Filtre
- **Periyot:** 15dk
- **Giris:** FastEMA > SlowEMA + RSI > Esik + Trend Gucu + XU100 filtre
- **Cikis:** EMA ters kesisim veya 3 katmanli stop (sabit / break-even / trailing)

### BOMBA Serisi (Akilli Robot Sablonu)
- **Tip:** EMA Cross + RSI + Bomba Listesi
- **Periyot:** 60dk
- **Giris:** Bomba listesinde + EMA ok + RSI ok
- **Cikis:** Stop loss + trailing stop

---

## ANKA icin Yeni Strateji Onerileri

Built-in stratejilerden esinlenerek su cesitleri ekleyebiliriz:

### 1. MOST/PMAX Stratejisi
MOST veya PMAX indikatoru ile trailing stop otomatik. BIST icin cok populer.

### 2. Bollinger + RSI Stratejisi
BolRsiStrategy benzeri. Alt bant + RSI oversold = alis, ust bant + RSI overbought = satis.

### 3. Stochastic + ADX Stratejisi
Trend gucunu olcup, stokastik ile zamanlama. Guclu trendde momentum sinyali.

### 4. Kurum Takip Stratejisi
BrokerageFirmTracking benzeri. Buyuk kurumlarin islem yonunu takip et.

### 5. Formasyon Stratejisi
AlgoFormation benzeri. Teknik formasyonlari otomatik tespit.

### 6. Haber Stratejisi
NewsStrategy benzeri. Belirli anahtar kelimelerde otomatik pozisyon.

### 7. Derinlik Stratejisi
Depth3 benzeri. Alim/satim dengesizligini takip.

### 8. Parabolic SAR Stratejisi
Trend donusu tespiti. VİOP icin de uygun (cift yonlu).

### 9. Cift Yonlu VİOP Stratejisi
AI_EndeksVadeli_5dk benzeri. Hem long hem short.

### 10. Tom DeMark Stratejisi
Ardisik sayac ile tavan/taban tespiti.
