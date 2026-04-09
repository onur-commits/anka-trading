# ANKA Cowork Görevi — Sektör Bazlı Stratejiler

## GENEL BİLGİ
- VPS: 78.135.87.29 (İstanbul Bakırköy)
- MatriksIQ çalışıyor, Midas Menkul bağlı
- 86 hisse için ANKA_*.cs dosyaları hazır
- Config: anka_config.json (tüm parametreler buradan okunur)

## STRATEJİ YAPISI
Her strateji C# dosyası, MatriksIQ'da derlenir ve çalıştırılır.
- Class adı = dosya adı (zorunlu)
- MaxPositionValue: config'den okunabilir, varsayılan 15000 TL
- Adet otomatik: Math.Floor(MaxPositionValue / closePrice)
- BuyOrderQuantity: 999999 (kod kendi sınırlar)

## SEKTÖR STRATEJİLERİ
Her sektörün karakterine göre farklı parametre:

### BANKA (GARAN, AKBNK, ISCTR, YKBNK, HALKB, VAKBN, TSKB, SKBNK)
- Karakter: Ağır abi, endeks lokomotifi
- EMA: 8/21 (trend takip)
- RSI eşik: 50
- Stop: %2.5 (daha geniş, yavaş hareket eder)
- Trailing: %2.0
- Özel: CDS düşüşünde ağırlık ver, faiz kararı günleri temkinli

### SANAYİ (EREGL, SISE, KORDS, BRISA, CIMSA, EGEEN, TKFEN)
- Karakter: Dengeli, döviz duyarlı
- EMA: 8/21
- RSI eşik: 52
- Stop: %2.0
- Özel: Dolar yükselince ihracatçılara ağırlık

### ENERJİ (AKSEN, ODAS, ENJSA, AYEN, GESAN, EUPWR, CWENE, TUPRS)
- Karakter: Mevsimsel, emtia duyarlı
- EMA: 8/21
- RSI eşik: 52
- Stop: %2.5
- Özel: Kış aylarında güçlü, petrol fiyatına duyarlı

### TEKNOLOJİ/SAVUNMA (ASELS, LOGO, KONTR, MTRKS, ARDYZ)
- Karakter: Volatil, haber duyarlı
- EMA: 5/13 (daha hızlı)
- RSI eşik: 55
- Stop: %1.5 (sıkı)
- Özel: İhale haberleri çok etkili

### HAVACILIK (THYAO, PGSUS)
- Karakter: Haber duyarlı, mevsimsel
- EMA: 8/21
- RSI eşik: 50
- Stop: %2.0
- Özel: Yaz sezonu güçlü, petrol fiyatı ters etki

### PERAKENDE/GIDA (BIMAS, MGROS, SOKM, ULKER, AEFES, MPARK)
- Karakter: Defansif, düşük volatilite
- EMA: 8/21
- RSI eşik: 48
- Stop: %2.0
- Özel: Enflasyon döneminde güçlü

### HOLDING (SAHOL, KCHOL, TAVHL, DOHOL)
- Karakter: Endeks ağırlıklı, yavaş ama güvenilir
- EMA: 8/21
- RSI eşik: 50
- Stop: %2.5
- Özel: İskonto/prim takibi

### KİMYA (PETKM, GUBRF, HEKTS, SASA)
- Karakter: Volatil, emtia duyarlı
- EMA: 5/13
- RSI eşik: 55
- Stop: %3.0 (geniş, çok sallanır)

### OTOMOTİV (TOASO, FROTO, OTKAR, TTRAK, VESTL, ARCLK, ASUZU, DOAS)
- Karakter: Döviz duyarlı, ihracatçı
- EMA: 8/21
- RSI eşik: 52
- Stop: %2.0
- Özel: Euro/Dolar yükselince güçlenir

### İNŞAAT/GYO (ENKAI, EKGYO, ISGYO, OZKGY, CIMSA)
- Karakter: Faiz duyarlı
- EMA: 8/21
- RSI eşik: 50
- Stop: %2.5
- Özel: Faiz düşünce güçlenir

### TELEKOM (TCELL, TTKOM)
- Karakter: Defansif, temettü hissesi
- EMA: 8/21
- RSI eşik: 48
- Stop: %2.0

## BACKTEST
- Midas deneme ortamında backtest yapılabilir
- IQ'da Backtest butonu → tarih aralığı seç → sonuç raporu
- Walk-forward: 6 aylık pencereler, 1 ay ileri kaydır

## PARAMETRELERİN DEĞİŞTİRİLMESİ
Tüm parametreler C:\ANKA\anka_config.json'dan okunabilir.
Config'i değiştir → stratejiler yeniden başlat → yeni parametreler aktif.

MaxPositionValue değiştirmek için:
1. anka_config.json → genel.max_tek_pozisyon_tl değiştir
2. Veya strateji kodunda [Parameter(15000)] satırını değiştir
3. Stratejiyi yeniden derle ve çalıştır
