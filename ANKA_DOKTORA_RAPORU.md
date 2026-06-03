# ANKA Trading System — Teknik Denetim Raporu

**Tarih:** 3 Nisan 2026  
**Kapsam:** Python + C# + mimari + ML + risk + operasyonel analiz  
**Sistem:** ANKA V2/V3 BIST Otonom Trading Sistemi  
**Sermaye Risk Altinda:** ~100.000 TL

---

## YONETICI OZETI

47 sorun tespit edildi: 11 KRITIK, 14 YUKSEK. En buyuk tehlike sistemin "calisiyor gibi gorunmesi"dir — sessizce para kaybettiren, fark edilmeyen kayip. AUC 0.5982 + komisyon maliyetleri ile net pozitif getiri ihtimali dusuktur.

---

## 1. MIMARI INCELEME

### 1.1 Sistem Mimarisi

```
Mac (Python) --[dosya yazma]--> Parallels VM (Windows) --[IQ]--> Midas Broker
     |                                |
     v                                v
 v3_bridge.json              aktif_bombalar.txt
 (60sn guncelleme)           (gun basinda bir kez)
```

**K-01 [KRITIK]: Dosya Tabanli IPC — Atomiklik Yok**

C# robotu `File.ReadAllText(bridgePath)` ile bridge dosyasini okurken Python tarafinda `v3_risk_motor.py` ayni dosyayi yaziyorsa YARIM OKUNAN JSON parse hatasi olusur. `catch { macroMultiplier = 1.0m; }` blogu bu hatayi sessizce yutar ve robot yanlis carpanla islem yapar.

`v3_risk_motor.py` satir 71-74: Lokal dosyaya atomik yazim (tmp+rename) uygulanmis, ancak Windows'a kopyalama `prlctl exec ... copy` ile yapiliyor — bu islem atomik DEGILDIR. Ek olarak prlctl exec 2-5 saniye surer; bridge verisi 60 saniyede guncelleniyor ama robot 65-90 saniye eski veriyle calisabilir.

**Cozum:** C# robotuna bridge'i HTTP GET ile cekmesini saglayan endpoint ekleyin; ya da en azindan dosya kilidi + retry mantigi ekleyin.

**K-02 [KRITIK]: Tek Nokta Arizasi**

| Bilesken | Ariza Senaryosu | Etki |
|----------|-----------------|------|
| Mac laptop | Kapanir / uyur | Tum Python surecler durur |
| Parallels VM | Crash / guncelleme | IQ robotu calismaz |
| Midas baglantisi | Kopma | Emir red edilir, robot bunu BILMEZ |
| Yahoo Finance API | Rate limit | ML egitim, risk motoru durur |

Hicbir bilesenin saglik kontrolunu yapan watchdog/heartbeat mekanizmasi yoktur.

**Y-01 [YUKSEK]: Bridge Format Tutarsizligi**

`v3_risk_motor.py` yazdigi: `{multiplier, regime, xu100_change, vix, usd_change, pos_value, last_update}`  
`kontrol_paneli.py` ek olarak yazdigi: `{hard_stop, trailing_stop, profit_trigger, rsi_threshold, ema_fast, ema_slow, robot_active}`

`BOMBA_V3_TURBO.cs` satir 93-102 SADECE `multiplier`, `pos_value`, `regime` okur. Panelden girilen stop/TP degerleri robot tarafindan hicbir zaman okunmaz.

**Cozum:**
```csharp
if (data.hard_stop != null) HardStop = (double)data.hard_stop;
if (data.trailing_stop != null) TrailingStop = (double)data.trailing_stop;
if (data.profit_trigger != null) ProfitTrigger = (double)data.profit_trigger;
```

### 1.2 Veri Akisi Uyumsuzlugu

**Y-02 [YUKSEK]: Zaman Ufku Uyumsuzlugu**

Python ML tahminleri Yahoo Finance GUNLUK verisine dayanir; C# robotu 5-DAKIKALIK (Min5) barlarda calisir. ML modeli "5 gunde %3+ yukari" hedefiyle egitilmis ama robot 5dk barlarda %0.7 profit trigger ile islem yapar. Iki sistem farkli sorulara cevap veriyor.

---

## 2. ISLEM MANTIGI HATALARI

### 2.1 C# Robot (BOMBA_V3_TURBO.cs)

**K-03 [KRITIK]: Sahte Pozisyon Takibi**

```csharp
// Satir 141-142
inPosition[s] = true;
entryPrices[s] = close;  // BAR KAPANIS fiyati, gercek dolum fiyati DEGIL!
```

`SendMarketOrder` gonderilir gonderilmez `inPosition = true` ve `entryPrices = close` ataniyor. Emir henuz dolmamis, kismen dolmus veya red edilmis olabilir. `OnOrderUpdate` callback'inde sadece SATIS dolumunda `ResetSymbol` cagriliyor; alis dolumunda gercek fiyat guncellenmez. Sonuc: PnL yanlis, trailing stop yanlis seviyeden tetiklenebilir.

**Cozum:** `OnOrderUpdate`'te:
```csharp
if (order.OrdStatus.Obj == OrdStatus.Filled && order.Side.Obj == Side.Buy)
{
    inPosition[sym] = true;
    entryPrices[sym] = order.Price;   // gercek dolum
    posQuantities[sym] = order.FilledAmount;
    highestPrices[sym] = order.Price;
}
```

**K-04 [KRITIK]: Rejected Order Yonetimi Yok**

Mevcut `OnOrderUpdate` (satir 162-167) SADECE basarili satis dolumlarini isler:
- **Rejected Buy:** Robot `inPosition = true` atar, olmayan pozisyonu yonetiyor.
- **Rejected Sell:** `ResetSymbol` cagrisi gelmez, robot sonsuza kadar bekler.
- **PartiallyFilled / Cancelled:** Tamamen gozardi.

`OnOrderUpdate`'e `OrdStatus.Rejected` ve `OrdStatus.Cancelled` dallari eklenmelidir.

**K-05 [KRITIK]: SendOrderSequential(true) Kilitleme**

`OnInit`'te `SendOrderSequential(true)` ayarli. 5 sembol ayni anda sinyal verirse, 2.–5. semboller ilk emir dolana kadar kuyrukta bekler; fiyat degisir, firsatlar kacrilir.

**Cozum:** `SendOrderSequential(false)` + her sembol icin `Dictionary<string, bool> orderPending` mekanizmasi.

**Y-03 [YUKSEK]: EMA Parametreleri Tutarsiz**

| Kaynak | Degerler |
|--------|---------|
| ANKA_RESTORE.md | EMA 10/20 |
| BOMBA_V3_TURBO.cs (canli kod) | EMA 5/13 |
| kontrol_paneli.py varsayilan | EMA 10/20 |
| gunluk_bomba.py sablonu | EMA 10/20 |

Canli kod ile dokumantasyon farkli parametreler kullaniyor; geri test sonuclari eslesemez.

**Y-04 [YUKSEK]: T+2 Settlement Yok**

Robot ayni gun alis-satis yapabilir; BIST T+2 kuralinda bu broker reject / hesap dondurma riski tasir.

**Y-05 [YUKSEK]: Kapanista Acik Pozisyon Riski**

ANKA_RESTORE.md'deki "17:50'de %0.5+ karda ise sat" kurali BOMBA_V3_TURBO.cs'de YOKTUR. Robotun tek cikis kosullari stop-loss ve EMA ters donmesidir. "Zarar ama stop'a vurmamis" pozisyonlar gece acik kalir, ertesi gun gap-down riski tasir.

---

## 3. ML MODEL ELESTIRISI

**K-06 [KRITIK]: Yahoo Finance BIST Veri Guvenilirligi**

Yahoo Finance, BIST icin resmi veri saglayici degildir. Bilinen sorunlar: 15-20dk gecikme, tatil gunu NaN satirlari, seanslar arasi fiyat tutarsizliklari, yanlis bolunme duzeltmesi, 2000+ istek/saat sonrasi rate limiting, coklu hisse MultiIndex sorunu.

**K-07 [KRITIK]: AUC 0.5982 Yetersiz**

- AUC 0.50 = rastgele tahmin
- AUC 0.5982 = rastgeleden ~0.10 puan iyi
- AUC 0.65 = minimum "bir sey ogrenmis" esigi (finans literaturunde)

Komisyon (%0.30 gidis-donus) + slippage (%0.15) = islem basina %0.45 maliyet. AUC 0.5982'nin saglayabilecegi brut kenar ile net getiri belirsiz, negatife donebilir.

| Senaryo | 200 islem/yil | Ort Kar/Islem | Brut | Komisyon | Net |
|---------|--------------|---------------|------|----------|-----|
| Iyimser | — | +%0.8 | +%160 | -%90 | +%70 |
| Gercekci | — | +%0.3 | +%60 | -%90 | **-%30** |
| Kotumser | — | -%0.1 | -%20 | -%90 | **-%110** |

**Y-06 [YUKSEK]: Lookahead Bias — Hedef Tanim Sorunu**

`hedef_olustur` (tahmin_motoru_v2.py):
```python
gelecek_max = df["High"].squeeze().rolling(gun).max().shift(-gun)
yukari = (gelecek_max - close) / close * 100
return (yukari >= esik).astype(int)
```

5 gunluk pencerenin EN YUKSEK fiyatini hedefliyor. Sorunlar:
1. Gercek islemde tam zirveyi yakalamak imkansiz.
2. Hisse %3 yukari gidip %10 asagi inse de "basarili" sayilir.
3. Intraday spike'lar bile basarili sayilir, model gereksiz agresif olur.

**Y-07 [YUKSEK]: Overfitting Riski**

73+ feature, ~50 hisse x 500 gun = ~25.000 satir. RSI_7/14/21, MACD, EMA cross gibi koreleli featurelar efektif bagimsiz feature sayisini 15-20'ye indiriyor. XGBoost max_depth=5 + 200 agac = ~6400 yaprak dugumu; 25.000 ornekle agresif. `reg_alpha` (L1) cok dusuk (0.1).

Walk-forward (`purged_walk_forward`) dogru yaklasim kullanmis ancak: n_splits=5 yetersiz (min 20-50 gerekir), purge_days=5 az (hedef 5 gune bakiyor, en az 10 olmali), her fold'da ayni hiperparametre kullaniliyor.

---

## 4. RISK YONETIMI BOSLUKLARI

**K-08 [KRITIK]: Portfoy Drawdown Koruması Calismiyor**

`risk_yonetimi.py`'deki `RiskYoneticisi` sinifi (ATR stop, Kelly, drawdown limiti, korelasyon filtresi) **hicbir yerde cagrilmiyor.**

- `BOMBA_V3_TURBO.cs`: `RiskYoneticisi` hakkinda bilgisi yok.
- `otonom_trader.py`: import var ama `sinyal_degerlendir()` hicbir yerde cagrilmiyor.

Sonuc: 5 sembol ayni anda %3.5 stop'a vurursa tek gunde 3.500 TL kayip; bunu durduracak mekanizma yok.

**K-09 [KRITIK]: Korelasyon Kontrolu Sadece Kagit Uzerinde**

`risk_yonetimi.py`'deki sektor korelasyon filtresi C# robotu tarafindan uygulanmiyor. 5 bomba hissenin hepsi enerji sektorunden olabilir (AYEN, AKSEN, ENJSA); petrol duserse hepsi ayni anda zarar eder.

**Y-08 [YUKSEK]: Kara Kugu Koruması Yok**

- BIST devre kesici (%5-7 dususte 30dk): Robot calisir ama emir gonderemez, acilista gap-down.
- Taban kilidi (%10 dusus): Satis emri gonderilemez, stop-loss calismaz.
- VIX spike (28→42 10 dakikada): 60sn guncelleme gecikmesinde robot yeni alis yapmis olabilir.
- Dusuk hacimli hisseler (GESAN, KONTR): Market emirde %0.3-0.5 slippage.

**Y-09 [YUKSEK]: Komisyon Analizi Hicbir Yerde Yok**

Tum ML modelleri ve geri testler komisyonsuz brut getiriyle calisiyor. Aylik 20 islem x %0.30 = %6 yillik komisyon etkisi; AUC 0.5982'nin saglayabilecegi kenari tamamen yok edebilir.

**Ek Not — Kelly Criterion:**

`risk_yonetimi.py` satir 69-98: Matematiksel olarak dogru (yarim Kelly), ancak girdi olarak calibrate edilmemis model olasiliklarini kullaniyor. Calibrate edilmemis olasilikla Kelly hesabinda lotlama tehlikeli.

---

## 5. AJAN SISTEMI ELESTIRISI

**Y-10 [YUKSEK]: Ajanlar Bagimsiz Degil**

`anka_v2.py`'deki 4 ajan (TechnoAgent, FundamentalAgent, MacroAgent, VolumeAgent):
- TechnoAgent ve VolumeAgent ayni `df`'i kullaniyor; fiyat yukari giderse ikisi de yuksek puan verir — koreleli.
- MacroAgent tum hisseler icin AYNI puani uretir; aslinda 3 bagimsiz ajan + 1 global bias kaynagi.
- FundamentalAgent Yahoo Finance `info` verisine guvenior; 3-6 ay eski olabilir.

**Y-11 [YUKSEK]: Minimum Oy Esigi Cok Dusuk**

BULL rejimde 2/4 ajan onay yeterli. Macro herkese ayni puani verdigi icin TechnoAgent + VolumeAgent (ikisi de fiyata bakiyor) onaylarsa islem yapiliyor — efektif olarak tek sinyal kaynagi.

**Ek Not — Dinamik Agirlik Ogrenimi:**

`anka_ogrenme.py`: 10 islem minimum yetersiz (her ajan icin 30-50 gerekir), time decay yok (eski islemler yenilerle ayni agirlikta), survivorship bias var (veto edilen islemlerin "ne olacagi" takip edilmiyor).

---

## 6. OPERASYONEL RISKLER

**K-10 [KRITIK]: Mac Yeniden Baslatma Sonrasi Her Sey Durur**

`caffeinate -d -i -s &` background process; Mac yeniden baslarsa kapanir ve otomatik baslamaz. `nohup` ile baslayan Python surecler de yeniden baslatmada kapanir. Hicbir surecin `launchd` plist veya crontab kaydi yok.

**Cozum:**
```xml
<!-- ~/Library/LaunchAgents/com.anka.otonom.plist -->
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
```

**Y-12 [YUKSEK]: Parallels VM Guvenilirligi**

Windows Update, Parallels guncelleme, disk dolmasi — bunlarin hicbirinde otomatik kurtarma mekanizmasi yok. VPS'e gecis planini hizlandirin.

**O-01 [ORTA]: Path Uyumsuzluklari**

- `v3_risk_motor.py`: `r"C:\Robot\v3_bridge.json"` (hardcoded Windows)
- `kontrol_paneli.py`, `anka_dashboard.py`: `BASE_DIR / "data" / "v3_bridge.json"` (lokal)
- C# robotu: `@"C:\Robot\v3_bridge.json"` (hardcoded)

Merkezi config dosyasi yok; VPS'e geciste tum yollar degistirilmeli.

**Y-13 [YUKSEK]: Process Monitoring Yok**

Sistem su sureclerden hangisinin calistigini BILMEZ: v3_risk_motor.py, otonom_trader.py, MatriksIQ, Midas baglantisi, bridge son yazma zamani.

**Cozum:** Her bilesenden 5dk'da bir `heartbeat.json` yazilsin; watchdog eksik heartbeat'i yakalayinca Telegram/macOS bildirimi gondersin.

---

## 7. GERCEK ALFA ANALIZI

**K-11 [KRITIK]: Alfa Kanitlanmamis**

Sistemin herhangi bir yerinde:
- Komisyon dahil kapsamli geri test yok
- XU100 benchmark karsilastirmasi yok
- Sharpe orani hesabi yok
- Maximum drawdown istatistigi yok
- Canli islem sonuclari sistematik log yok

Minimum kabul kriterleri: 2 yillik geri test (komisyon dahil), XU100 B&H ile karsilastirma, 6 ay out-of-sample, Sharpe > 1.0, max drawdown < %15.

BIST XU100 son 5 yillik ortalama getiri ~%30-50/yil (TL bazinda). Mevcut sistemin bu eforsuz benchmark'i gecmesi icin AUC minimum 0.65+ ve cok daha az islem (kalite odakli) gerekiyor.

---

## 8. ONCELIKLI DUZELTMELER

### KRITIK (Hemen — gercek para riski)

| # | Sorun | Cozum |
|---|-------|-------|
| K-01 | IPC atomiklik yok | C# tarafinda file lock + retry; ya da HTTP endpoint |
| K-03 | Sahte pozisyon takibi | OnOrderUpdate'te gercek dolum fiyatini kullan |
| K-04 | Rejected order yonetimi yok | Reject / Cancel / PartialFill durumlarini isle |
| K-05 | SendOrderSequential kilitleme | false + sembol bazinda kilit mekanizmasi |
| K-06 | Yahoo Finance guvenilirligi | Matriks Data API veya capraz dogrulama |
| K-07 | AUC 0.5982 yetersiz | Model iyilestir veya ML'yi kapat, saf teknik sinyal kullan |
| K-08 | Portfoy drawdown koruması calısmiyor | risk_yonetimi.py'yi C# robotuna entegre et |
| K-09 | Korelasyon kontrolu yok | Sektor bazli max pozisyon siniri |
| K-10 | Mac yeniden baslatma | launchd plist + watchdog + Telegram bildirim |
| K-11 | Alfa kanitlanmamis | Komisyon dahil geri test + paper trade once |

### YUKSEK (1 hafta icinde)

| # | Sorun | Cozum |
|---|-------|-------|
| Y-01 | Bridge format tutarsizligi | C# robotunu tum bridge parametrelerini okuyacak sekilde guncelle |
| Y-02 | Zaman ufku uyumsuzlugu | ML hedef fonksiyonunu robot periyoduna uyumla |
| Y-03 | EMA parametreleri tutarsiz | Kod ile dokumantasyonu eslestir |
| Y-04 | T+2 settlement yok | Giris zamanini kaydet, ayni gun satis engelle |
| Y-05 | Kapanista acik pozisyon | 17:45'te tum pozisyonlari kapat mantigi ekle |
| Y-06 | Lookahead bias | hedef_olustur'u risk/odul bazli yeniden yaz |
| Y-07 | Overfitting riski | Feature secimi (top 20-30), mutual information filtresi |
| Y-08 | Kara kugu koruması yok | Portfoy bazinda gunluk max kayip limiti |
| Y-09 | Komisyon analizi yok | Tum geri testlere %0.30 komisyon ekle |
| Y-10 | Ajanlar bagimsiz degil | En az 1 bagimsiz veri kaynagi ekle |
| Y-11 | Oy esigi dusuk | BULL'da bile 3/5 ajan onayi iste |
| Y-12 | Parallels VM guvenilirligi | VPS gecisini hizlandir |
| Y-13 | Process monitoring yok | Heartbeat + Telegram bildirim |

### ORTA (2 hafta icinde)

| # | Sorun | Cozum |
|---|-------|-------|
| O-01 | Path uyumsuzluklari | Merkezi config.json |
| O-02 | Loglama tutarsiz | Yapisal JSON log + rotasyon |
| O-03 | Dinamik agirlik 10 islem yetersiz | 30+ islem esigi + time decay |
| O-04 | Scalper modulu entegre degil | anka_scalper.py sonuclarini bridge'e yaz |
| O-05 | Iki dashboard var | Birini sec, digerini kaldir |
| O-06 | otonom_trader.py satir 567: `gorev_08_50_iq_hazirla` fonksiyonu yok | `gorev_08_50_iq_kontrol` olarak duzelt |

---

## 9. ACIL EYLEM PLANI

**Ilk 24 Saat:**
1. C# robotunda `OnOrderUpdate`'i genislet — Reject/Cancel yakalama (K-04)
2. Bridge'e `max_daily_loss` ekle; asildıgında multiplier=0 (K-08)
3. Tum surecler icin watchdog + heartbeat yazisi (K-10, Y-13)

**Ilk Hafta:**
4. Paper trade modu — `DRY_RUN = true`, emir gondermeden logla (K-11)
5. 3 aylik geri test komisyon dahil, XU100 ile karsilastir
6. ML'yi gecici devre disi birak; sadece teknik sinyal (EMA + RSI + MOST) ile dene

**Ilk Ay:**
7. VPS gecisi — laptop bagımlılıgını kaldir (Y-12)
8. Telegram bildirimler — her islemde, her hatada, gun sonu
9. Model iyilestirme — feature secimi, daha iyi hedef tanimi, AUC 0.65+ hedefle

---

## 10. SONUC

ANKA, etkileyici teknik ambisyon gosteren bir projedir. Ancak detaylarda hayati hatalar var ve bunlar GERCEK PARA kaybina yol abilir.

**Onerilen strateji:**
1. Canli islemi durdurun
2. 3 ay paper trade yapin
3. Sonuclari XU100 ile karsilastirin
4. Istatistiksel anlamli avantaj gosterirse canli isleme donun
5. Baslangicta 10.000 TL'lik yari pozisyonla baslayin

Sistemi duzeltmek icin gereken bilgi bu raporda mevcut. Kodlama yetenegi yeterli — eksik olan istatistiksel titizlik ve sabir.

---

*Bu rapor yatirim tavsiyesi icermez. Tum finansal kararlar kullanicinin kendi sorumlulugundadir.*
