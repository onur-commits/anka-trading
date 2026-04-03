# ANKA API REHBERİ — Tüm Deneyim ve Bilgiler
## Bu dosyayı yeni Claude oturumuna ver, aynen devam eder.

---

## MatriksIQ Dışarıdan Emir Kabulü API

### Bağlantı Bilgileri
- **Protokol:** TCP Soket
- **Port:** 18890
- **Format:** JSON + char(11) sonlandırıcı
- **Döküman:** /Users/onurbodur/Downloads/0_matriksiq-disaridanemirkabuluapi.pdf
- **GitHub:** https://github.com/MatriksIQ/ApiClient (C# client)
- **Python client:** /Users/onurbodur/adsız klasör/borsa_surpriz/anka_api.py

### Çalışması İçin Gerekenler
1. MatriksIQ açık olmalı
2. "Dışarıdan Emir Kabulü" lisansı aktif (30.04.2026'ya kadar aktif)
3. Midas hesabına giriş yapılmış olmalı
4. Port 18890 otomatik dinlemeye başlar

### KRİTİK: Mac → Windows Bağlantı Sorunu
- Mac'ten `prlctl exec` ile Windows'a komut gönderilebilir
- AMA Mac'ten Windows'taki port 18890'a TCP bağlantısı KURULAMAZ
- Parallels firewall engelliyor
- Windows içinden localhost:18890 ÇALIŞIYOR (test ettik, TcpTestSucceeded: True)
- **ÇÖZÜM:** VPS'te Python + IQ aynı Windows'ta → localhost sorun olmaz

### API Komutları (ApiCommands parametresi)
| Kod | Komut | Açıklama |
|-----|-------|---------|
| 0 | ListAccounts | Hesap listesi |
| 1 | ListPositions | Pozisyon sorgula |
| 2 | ListOrders | Emir sorgula |
| 3 | NewOrder | YENİ EMİR GÖNDER |
| 4 | CancelOrder | Emir iptal |
| 5 | EditOrder | Emir düzelt |
| 6 | SendKeepAlive | Bağlantı canlı tut |
| 7 | SendAccountInformationRequest | Hesap bilgileri |
| 8 | RequestFilledOrders | Gerçekleşen emirler |
| 9 | RequestCanceledOrders | İptal emirler |
| 10 | ChangeLoggingMode | Log modu |
| 11 | ChangeBroadcastMode | Otomatik yanıt al/alma |

### JSON Paket Formatı
Her JSON paketinin sonuna char(11) eklenmeli:
```python
paket = json.dumps(data) + chr(11)
sock.sendall(paket.encode('utf-8'))
```

### Mesaj Tipi Seçimi (İlk bağlantıda)
```json
{"SetMessageType0": "MessageType"}  // JSON modu
```

### Hesap Listesi Alma
```json
{"ApiCommands": 0}
```
Yanıt:
```json
{
  "Accounts": [{
    "BrokageId": "7",
    "BrokageName": "[Midas] ",
    "AccountIdList": [{"AccountId": "HESAP_ID_BURAYA", "ExchangeId": 4}]
  }]
}
```
Not: Kullanıcının Midas hesap bilgileri:
- BrokageId: Midas'ın broker kodu
- AccountId: "HESAP_ID_BURAYA" formatında
- ExchangeId: 4 = BIST, 9 = VIOP

### Pozisyon Okuma
```json
{
  "BrokageId": "7",
  "AccountId": "HESAP_ID_BURAYA",
  "ExchangeId": 4,
  "ApiCommands": 1
}
```
Dönen veriler: Symbol, QtyNet, AvgCost, LastPx, PL, PLPercent, QtyAvailable, Amount

### Yeni Emir Gönderme (ALIŞ)
```json
{
  "OrderSide": 0,          // 0=Alış, 1=Satış
  "OrderID": null,
  "OrderID2": null,
  "OrderQty": 100.0,
  "OrdStatus": "0",
  "LeavesQty": 100.0,
  "FilledQty": 0.0,
  "AvgPx": 0.0,
  "TradeDate": "0001-01-01T00:00:00",
  "TransactTime": "00:00:00",
  "StopPx": 0.0,
  "Explanation": null,
  "ExpireDate": "0001-01-01T00:00:00",
  "Symbol": "GARAN",
  "Price": 130.50,
  "Quantity": 100.0,
  "IncludeAfterSession": false,
  "OrderType": "2",        // "2"=Limit, "1"=Piyasa
  "TransactionType": "1",  // "1"=Normal
  "AccountId": "HESAP_ID_BURAYA",
  "BrokageId": "7",
  "ApiCommands": 3
}
```

### Yeni Emir Gönderme (SATIŞ)
Aynı format, sadece:
```json
"OrderSide": 1   // 1=Satış
```

### Emir İptal
```json
{
  "OrderID": "1258195",     // İptal edilecek emrin ID'si
  "OrderID2": "1258195*8,0300",
  "Symbol": "GARAN",
  "ApiCommands": 4
}
```

### Emir Düzeltme
```json
{
  "OrderID": "1260254",
  "OrderID2": "1260254*10,0000",
  "Price": 9.47,
  "Quantity": 9.0,
  "ApiCommands": 5
}
```

### Gerçekleşen Emirler
```json
{
  "BrokageId": "7",
  "AccountId": "HESAP_ID_BURAYA",
  "ExchangeId": 4,
  "ApiCommands": 8
}
```

### Durum Değişiklikleri (Otomatik Bildirim)
ChangeBroadcastMode (ApiCommands: 11) aktif edilirse, IQ şu durumları otomatik bildirir:
- Emir durumu değişiklikleri (dolum, red, iptal)
- Pozisyon değişiklikleri
- Hesap değişiklikleri
- Bağlantı durumu

### Parametre Tabloları

**ExchangeId:**
- 4 = BIST
- 9 = VIOP

**OrdStatus:**
- "0" = Yeni
- "1" = Kısmi dolum
- "2" = Doldu
- "4" = İptal
- "8" = Reddedildi

**OrderSide:**
- 0 = Alış
- 1 = Satış

**OrderType:**
- "1" = Piyasa
- "2" = Limit

**TimeInForce:**
- "0" = Günlük
- "3" = Anlık (IOC)
- "4" = Fill or Kill (FOK)

---

## VPS Kurulum Planı

### MarkaHost Profesyonel (674 TL/ay)
- 10 Core, 16 GB RAM, 200 GB NVMe SSD
- İstanbul lokasyonu — BIST'e düşük gecikme
- Windows kurulu

### VPS'te Yapılacaklar
1. MatriksIQ kur + Midas'a giriş yap
2. Python 3.13 kur
3. Tüm ANKA dosyalarını kopyala
4. anka_api.py ile localhost:18890'a bağlan → TEST
5. Otonom trader + risk motoru + dashboard başlat
6. IQ robotunu başlat VEYA tamamen API ile çalış

### VPS'te API Akışı
```
Python (aynı makine) → TCP localhost:18890 → IQ → Midas → Borsa
        ↓
  5 Ajan analiz
  Kill-switch
  Panel kuralları
  Dry-run modu
```

---

## Bilinen Sorunlar ve Çözümler

### 1. Mac'ten Windows API'ye bağlanamama
- Sorun: Parallels firewall TCP bağlantısını engelliyor
- Test: `prlctl exec "Windows 11" powershell -Command "Test-NetConnection -ComputerName 127.0.0.1 -Port 18890"` → TcpTestSucceeded: True
- Çözüm: VPS (aynı makine)

### 2. Robot pozisyon takip hatası
- Sorun: SendMarketOrder sonrası hemen inPosition=true atıyor, gerçek dolum beklenmiyor
- Çözüm: buyPending mekanizması + OnOrderUpdate'te gerçek dolum fiyatı (order.AvgPx)
- Dosya: BOMBA_V3_PANEL.cs

### 3. Dosya bridge atomiklik
- Sorun: Python yazarken C# okursa yarım JSON
- Çözüm: temp dosya + rename (os.replace)

### 4. Yahoo Finance gecikme
- Sorun: 15dk gecikmeli veri
- Çözüm: VPS'te IQ API'den anlık fiyat çek

### 5. SendOrderSequential
- Sorun: true iken 5 sembolde 4'ünün sinyali kaçırılıyor
- Çözüm: false yap + kendi kilit mekanizmasını yaz (buyPending, sellPending)

### 6. Kill-switch
- Günlük max kayıp %3 geçerse tüm işlemler durur
- C# robotunda: gunlukKZ takibi + killSwitchAktif flag
- Python'da: anka_panel_kurallari.py

### 7. Sektör filtresi
- Max 2 hisse aynı sektörden
- anka_panel_kurallari.py → SektorFiltresi class

---

## Kullanıcı Bilgileri
- Ad: Onur Bodur
- Broker: Midas Menkul
- Hesap: HESAP_ID_BURAYA
- Matriks paketleri: IQ Veri Terminali + IQ Algo + Dışarıdan Emir Kabulü + BIST Otomatik Emir
- Portföy büyüklüğü: ~200K TL
- Risk toleransı: Orta-yüksek
- Tercih: Tam otonom, izin sormadan devam et, her zaman tam kod ver
