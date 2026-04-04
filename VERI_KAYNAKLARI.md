# 📊 ANKA & COIN — Veri Kaynakları Haritası

## KRİPTO VERİ KAYNAKLARI

### Anlık (Canlı)
| Kaynak | Veri | API | Bedava | Entegre |
|--------|------|-----|--------|---------|
| Binance | Fiyat, hacim, emir defteri | api.binance.com/api/v3/ | ✅ Limitsiz | ✅ |
| Binance Futures | Funding rate, OI, L/S oranı | fapi.binance.com/fapi/v1/ | ✅ | ✅ |
| Alternative.me | Fear & Greed Index | api.alternative.me/fng/ | ✅ Limitsiz | ✅ |

### Geçmiş
| Kaynak | Veri | API | Bedava | Entegre |
|--------|------|-----|--------|---------|
| Binance Klines | 1dk-1ay bar verisi | api.binance.com/api/v3/klines | ✅ 1000 bar/istek | ✅ |
| CoinGecko | Tarihsel fiyat, market cap | api.coingecko.com/api/v3/ | ✅ 30 istek/dk | ❌ |
| Glassnode | On-chain metrikler | api.glassnode.com/ | 💰 Ücretli | ❌ |

### Eklenecek (Bedava)
| Kaynak | Veri | API | Öncelik |
|--------|------|-----|---------|
| CoinGecko | Market cap, dolaşımdaki arz | api.coingecko.com | YÜKSEK |
| CryptoCompare | Sosyal medya verisi | min-api.cryptocompare.com | ORTA |
| Whale Alert | Büyük transferler | api.whale-alert.io | YÜKSEK |
| Messari | Proje bilgileri, metrikler | data.messari.io/api/ | ORTA |
| DeFi Llama | TVL, DeFi verileri | api.llama.fi/ | DÜŞÜK |

---

## BIST VERİ KAYNAKLARI

### Anlık
| Kaynak | Veri | API | Bedava | Entegre |
|--------|------|-----|--------|---------|
| MatriksIQ API | Fiyat, emir defteri, emir gönder | TCP localhost:18890 | Lisanslı | ✅ (VPS'te) |
| Yahoo Finance | Fiyat (15dk gecikmeli) | yfinance Python | ✅ | ✅ |

### Geçmiş
| Kaynak | Veri | API | Bedava | Entegre |
|--------|------|-----|--------|---------|
| Yahoo Finance | 5 yıl günlük veri | yfinance | ✅ | ✅ |
| TCMB EVDS | Faiz, enflasyon, döviz, yabancı akış | evds2.tcmb.gov.tr/service/evds/ | ✅ (kayıt lazım) | ❌ |
| KAP | Bilanço, temettü, bedelsiz | kap.org.tr | ✅ (scraping) | ❌ |
| Investing.com | Swap, vadeli, emtia | Web scraping | ✅ | ❌ |
| FRED (ABD) | Fed faiz, M2, enflasyon | api.stlouisfed.org | ✅ (kayıt) | ❌ |

### Eklenecek (Bedava)
| Kaynak | Veri | API | Öncelik |
|--------|------|-----|---------|
| TCMB EVDS | Haftalık yabancı akış | evds2.tcmb.gov.tr | YÜKSEK |
| KAP Scraper | Bilanço, özel durum açıklamaları | kap.org.tr | YÜKSEK |
| FRED | Fed faiz kararları, M2 | api.stlouisfed.org | ORTA |
| Google Trends | "borsa" arama hacmi | pytrends | DÜŞÜK |
| Twitter/X | Piyasa sentiment | API (ücretli) | DÜŞÜK |

---

## HANGİ VERİ HANGİ AJANA GİDER?

### COIN
| Ajan | Mevcut Veri | Eklenecek |
|------|-------------|-----------|
| TechnoAgent | Binance klines | - |
| VolumeAgent | Binance klines | CoinGecko market cap |
| MacroAgent | BTC trend | Fear & Greed (✅ eklendi) |
| FundingAgent | Binance Futures | - |
| OnChainAgent | Binance hacim proxy | Whale Alert, Glassnode |
| SentimentAgent | Fear & Greed | CryptoCompare sosyal |
| LiquidationAgent | Binance Futures L/S | - |
| OrderBookAgent | Binance depth | - |
| CorrelationAgent | Binance klines | - |

### ANKA (BIST)
| Ajan | Mevcut Veri | Eklenecek |
|------|-------------|-----------|
| TechnoAgent | Yahoo Finance | MatriksIQ (VPS) |
| VolumeAgent | Yahoo Finance | MatriksIQ Level 2 |
| MacroAgent | Yahoo (XU100,VIX,USD,S&P,Petrol,Altın) | TCMB EVDS (faiz, yabancı akış) |
| FundaAgent | Yahoo (F/K, PD/DD) | KAP (bilanço, temettü) |
| MomentumAgent | Yahoo Finance | - |

---

## GEÇMİŞ VERİ İLE EĞİTİM

### Mevcut Eğitim Verileri
| Veri | Süre | Kaynak | Model |
|------|------|--------|-------|
| BIST50 günlük fiyat | 5 yıl | Yahoo Finance | ANKA AI v1 (AUC 0.6222) |
| 15 coin saatlik fiyat | 2 yıl | Binance | COIN AI v1 (AUC 0.5702) |

### Eklenecek Eğitim Verileri
| Veri | Kaynak | Etkisi |
|------|--------|--------|
| TCMB faiz kararı tarihleri + BIST tepkisi | TCMB + Yahoo | Makro AI güçlenir |
| KAP bilanço açıklama tarihleri + fiyat tepkisi | KAP + Yahoo | Funda AI güçlenir |
| Fed faiz kararı + kripto tepkisi | FRED + Binance | Coin Makro AI güçlenir |
| Fear & Greed geçmişi + BTC fiyat | Alternative.me | Sentiment AI güçlenir |
| Yabancı yatırımcı akışı + BIST | TCMB EVDS | En güçlü BIST sinyali |
