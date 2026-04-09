# ANKA COWORK GÖREVİ — 86 Hisse Strateji Yükleme

## DURUM
- 86 adet ANKA_*.cs strateji dosyası VPS'te hazır: `C:\ANKA\matriks_iq\`
- Her biri 15.000 TL pozisyon limiti, 15dk periyot
- MaxPositionValue: 15000, Komisyon: 0
- Stop-loss %2, Trailing %1.5, Break-even %0.8
- Saat filtresi 10:00-18:00, XU100 endeks filtresi aktif

## VPS BİLGİLERİ
- IP: 78.135.87.29
- User: Administrator
- Midas Menkul hesap: 0-2205905
- MatriksIQ çalışıyor

## YAPILACAK İŞ
MatriksIQ'da her hisse için strateji yükleme:

1. IQ Algo → Yeni Strateji Oluştur → Yeni şablon
2. Strateji adını ANKA_TICKER yap (ör: ANKA_GARAN)
3. Kodu C:\ANKA\matriks_iq\ANKA_TICKER.cs dosyasından kopyala-yapıştır
4. Kodu Derle → hata yoksa Çalıştır
5. Parametreler: Period 15dk, Komisyon 0
6. BuyOrderQuantity ve SellOrderQuantity: aşağıdaki tablodan

## 86 HİSSE LİSTESİ VE ADETLER (15.000 TL / Fiyat)

### Bankalar
| Hisse | Fiyat | Adet |
|-------|-------|------|
| GARAN | 136 | 110 |
| AKBNK | 56 | 267 |
| ISCTR | 13 | 1153 |
| YKBNK | 30 | 500 |
| HALKB | 18 | 833 |
| VAKBN | 13 | 1153 |
| TSKB | 11 | 1363 |
| SKBNK | 4 | 3750 |

### Holdingler
| Hisse | Fiyat | Adet |
|-------|-------|------|
| SAHOL | 97 | 154 |
| KCHOL | 200 | 75 |
| TAVHL | 293 | 51 |
| DOHOL | 21 | 714 |

### Sanayi
| Hisse | Fiyat | Adet |
|-------|-------|------|
| EREGL | 30 | 500 |
| TOASO | 280 | 53 |
| TUPRS | 257 | 58 |
| SISE | 47 | 319 |
| FROTO | 1200 | 12 |
| OTKAR | 530 | 28 |
| TTRAK | 600 | 25 |
| KORDS | 58 | 258 |
| BRISA | 85 | 176 |
| CIMSA | 49 | 306 |
| EGEEN | 400 | 37 |
| TKFEN | 108 | 138 |

### Enerji
| Hisse | Fiyat | Adet |
|-------|-------|------|
| AKSEN | 79 | 189 |
| ODAS | 30 | 500 |
| ENJSA | 116 | 129 |
| AYEN | 36 | 416 |
| GESAN | 5 | 3000 |
| EUPWR | 3 | 5000 |
| CWENE | 5 | 3000 |

### Teknoloji/Savunma
| Hisse | Fiyat | Adet |
|-------|-------|------|
| ASELS | 378 | 39 |
| LOGO | 160 | 93 |
| KONTR | 8 | 1875 |
| MTRKS | 22 | 681 |
| ARDYZ | 15 | 1000 |

### Perakende/Gıda
| Hisse | Fiyat | Adet |
|-------|-------|------|
| BIMAS | 738 | 20 |
| MGROS | 603 | 24 |
| SOKM | 50 | 300 |
| ULKER | 150 | 100 |
| AEFES | 200 | 75 |
| MPARK | 8 | 1875 |
| CCOLA | 200 | 75 |
| TABGD | 25 | 600 |
| TATGD | 30 | 500 |

### Havacılık/Turizm
| Hisse | Fiyat | Adet |
|-------|-------|------|
| THYAO | 294 | 51 |
| PGSUS | 500 | 30 |

### Telekom
| Hisse | Fiyat | Adet |
|-------|-------|------|
| TCELL | 80 | 187 |
| TTKOM | 25 | 600 |

### İnşaat/GYO
| Hisse | Fiyat | Adet |
|-------|-------|------|
| ENKAI | 92 | 163 |
| EKGYO | 6 | 2500 |
| ISGYO | 10 | 1500 |
| OZKGY | 8 | 1875 |

### Kimya
| Hisse | Fiyat | Adet |
|-------|-------|------|
| PETKM | 21 | 714 |
| GUBRF | 100 | 150 |
| HEKTS | 80 | 187 |
| SASA | 2.3 | 6521 |

### Otomotiv
| Hisse | Fiyat | Adet |
|-------|-------|------|
| VESTL | 35 | 428 |
| ARCLK | 180 | 83 |
| ASUZU | 50 | 300 |
| DOAS | 200 | 75 |

### Diğer
| Hisse | Fiyat | Adet |
|-------|-------|------|
| ALFAS | 60 | 250 |
| ALTNY | 50 | 300 |
| ASTOR | 50 | 300 |
| BERA | 130 | 115 |
| BIOEN | 15 | 1000 |
| BRYAT | 10 | 1500 |
| BTCIM | 20 | 750 |
| CANTE | 30 | 500 |
| CEMTS | 30 | 500 |
| ECILC | 20 | 750 |
| GWIND | 10 | 1500 |
| KMPUR | 100 | 150 |
| KOPOL | 15 | 1000 |
| KRDMD | 30 | 500 |
| SMRTG | 10 | 1500 |
| SUNTK | 30 | 500 |
| TKNSA | 25 | 600 |
| TURSG | 15 | 1000 |
| VESBE | 20 | 750 |
| YATAS | 30 | 500 |
| AKFGY | 10 | 1500 |
| AKFYE | 15 | 1000 |
| AKSA | 40 | 375 |
| ALARK | 50 | 300 |
| KOZAL | 80 | 187 |

## NOT
- Fiyatlar tahminidir, IQ çalıştırırken güncel fiyattan adet hesapla
- Adet = 15000 / güncel_fiyat (yuvarla)
- MaxPositionValue 15000 olduğu için kod otomatik hesaplar ama BuyOrderQuantity'yi de doğru gir
- İlk 10 hisse ile başla, sorun yoksa kalanını ekle

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
