# ANKA COWORK GÖREVİ — 86 Hisse Strateji Yükleme

## DURUM
- 86 adet ANKA_*.cs strateji dosyası VPS'te hazır: `C:\ANKA\matriks_iq\`
- Her biri 15.000 TL pozisyon limiti, 15dk periyot
- MaxPositionValue: 15000 → KOD GÜNCEL FİYATTAN ADETİ OTOMATİK HESAPLAR
- Stop-loss %2, Trailing %1.5, Break-even %0.8
- Saat filtresi 10:00-18:00, XU100 endeks filtresi aktif

## ÖNEMLİ: ADET HESAPLAMA
Kodda `buyQty = Math.Floor(15000 / guncelFiyat)` var.
Fiyat değişse bile her sinyalde güncel fiyattan adet hesaplanır.
BuyOrderQuantity parametresine dokunma veya 999999 yaz — kod kendi hesaplayacak.

## VPS BİLGİLERİ
- IP: 78.135.87.29 (İstanbul Bakırköy, Markahost)
- User: Administrator
- Midas Menkul hesap: 0-2205905
- MatriksIQ çalışıyor
- Saat: İstanbul (otomatik düzeltme kuruldu)

## YAPILACAK İŞ
MatriksIQ'da her hisse için strateji yükleme:

### ADIM ADIM (her hisse için ~30 saniye):
1. IQ Algo → Kullanıcı Stratejileri → "Strateji Al" veya "Yeni Strateji Oluştur"
2. Strateji adını **ANKA_TICKER** yap (ör: ANKA_GARAN) — CLASS ADI İLE BİREBİR AYNI OLMALI
3. Kodu `C:\ANKA\matriks_iq\ANKA_TICKER.cs` dosyasından kopyala-yapıştır
4. **Kodu Derle** → hata yoksa devam
5. **Çalıştır** → Parametreler:
   - Symbol: otomatik gelir (kodda tanımlı)
   - SymbolPeriod: **15Dakika**
   - BuyOrderQuantity: **999999** (kod kendi hesaplar)
   - SellOrderQuantity: **999999** (kod kendi hesaplar)
   - MaxPositionValue: **15000** (otomatik gelir)
   - Komisyon: **0**
6. **İleri → Çalıştır**

### 86 HİSSENİN TAMAMINI YAP — seçme yok, hepsi yüklenir

Sıra farketmez. Tek tek 86'sını yükle. Her biri ~30 saniye.
Adet yazmana gerek yok — kod güncel fiyattan otomatik hesaplar.

## TAM HİSSE LİSTESİ (86 adet)

```
GARAN  AKBNK  ISCTR  YKBNK  HALKB  VAKBN  TSKB   SAHOL
KCHOL  TAVHL  DOHOL  EREGL  TOASO  TUPRS  SISE   FROTO
OTKAR  TTRAK  KORDS  BRISA  CIMSA  EGEEN  AKSEN  ODAS
ENJSA  AYEN   ASELS  LOGO   BIMAS  MGROS  SOKM   THYAO
PGSUS  TCELL  TTKOM  ENKAI  EKGYO  ISGYO  PETKM  GUBRF
HEKTS  SASA   ULKER  AEFES  TKFEN  VESTL  ARCLK  GESAN
KONTR  MPARK  KOZAL  ALFAS  ALTNY  ARDYZ  ASTOR  ASUZU
BERA   BIOEN  BRYAT  BTCIM  CANTE  CCOLA  CEMTS  CWENE
DOAS   ECILC  EUPWR  GWIND  KMPUR  KOPOL  KRDMD  MTRKS
OZKGY  SKBNK  SMRTG  SUNTK  TABGD  TATGD  TKNSA  TURSG
VESBE  YATAS  AKFGY  AKFYE  AKSA   ALARK
```

Her hisse için dosya: `C:\ANKA\matriks_iq\ANKA_[TICKER].cs`
Strateji adı: `ANKA_[TICKER]` (class adı ile birebir aynı)

## ADET HESAPLAMA — OTOMATİK
Kod içinde: `buyQty = Math.Floor(15000 / closePrice)`
- Fiyat 100 TL → 150 lot alır
- Fiyat 50 TL → 300 lot alır
- Fiyat değişirse → sonraki sinyalde yeni fiyattan hesaplar
- **Elle adet yazmana GEREK YOK**
- BuyOrderQuantity: **999999** yaz (kod kendi sınırlar)
- SellOrderQuantity: **999999** yaz

## BUGÜN KONUŞTUKLARIMIZ (9 Nisan 2026)

### Yapılanlar
1. VPS saat düzeltildi (Pasifik → İstanbul)
2. Midas Menkul canlı hesap bağlandı (İşlem Limiti: 335K TL)
3. BIST_ALPHA_CORE_V1 stratejisi IQ'ya yüklendi, GARAN ile ilk canlı trade
4. 5 bomba hissesi eklendi (KORDS, ASELS, BIMAS, PETKM, TKFEN)
5. Güncel bomba taraması: Piyasa BULL'a döndü
6. ANKA Beyin: 4 katmanlı rejim motoru (Trend/Vol/Likidite/Duygu)
7. Merkezi config: anka_config.json (tüm parametreler tek dosyada)
8. ANKA Orkestra: tüm modülleri yöneten ana motor
9. Mühendis: IQ strateji izleme + bildirim sistemi
10. 86 hisse için strateji dosyaları üretildi

### Sorunlar
- IQ stratejileri Midas kopunca durdu → çözüm: Mühendis bildirim gönderiyor
- RDP bağlantısı stabil değil → çözüm: AnyDesk kurulacak
- Bot 1 lot aldı → çözüm: BuyOrderQuantity manuel girilmeli

### Kararlar
- 5 hisse → 10 hisse (15K/hisse)
- Sonra 86 hisseye genişle (her biri kendi AI ajanı)
- Rejim motoruna göre strateji seçimi
- Her hissenin karakter profili var
- Kraliçe bot (orkestra) hepsini yönetiyor

### Profesör Paneli Gereksinimleri (%90-95 geçiş)
- Walk-forward validation + CPCV
- HAR-RV volatilite modeli
- CVaR risk yönetimi
- On-chain veri (coin tarafı)
- Mevsimsellik matrisi
- Haber sentiment (KAP + genel)
- Öğrenme/hafıza sistemi (feedback loop)
- Kill switch (3 üst üste kayıp → dur)
