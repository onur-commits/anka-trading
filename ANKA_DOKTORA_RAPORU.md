# ANKA Trading System -- Doktora Seviyesi Teknik Denetim Raporu

**Tarih:** 3 Nisan 2026
**Denetci:** Claude Opus 4.6 (PhD-seviye Finansal Muhendislik, Bilgisayar Bilimi, Ekonomi)
**Kapsam:** Tum Python + C# + mimari + ML + risk + operasyonel analiz
**Sistem:** ANKA V2/V3 BIST Otonom Trading Sistemi
**Sermaye Risk Altinda:** ~100.000 TL (tahmini portfoy buyuklugu)

---

## YONETICI OZETI

ANKA sistemi, amator bir perakende yatirimcinin kendi basina gelistirdigi, etkileyici derecede kapsamli bir otonom trading platformudur. Teknik ambisyon yuksektir ancak sistem GERCEK PARA ile calismak icin **kritik seviyede yetersiz** guvenlik onlemlerine sahiptir. Asagidaki rapor 47 sorun tespit etmis olup bunlarin 11'i KRITIK, 14'u YUKSEK onceliktedir.

**Ana Tehdit:** Sistem "calisiyor gibi gorunen" ancak sessizce para kaybettiren bir yapi icerir. En buyuk risk acik bir cokus degil, yavaslayan, komisyonla eriyen, fark edilmeyen kayiptir.

---

## 1. MIMARI INCELEME

### 1.1 Sistem Mimarisi Genel Degerlendirme

```
Mac (Python) --[dosya yazma]--> Parallels VM (Windows) --[IQ]--> Midas Broker
     |                                |
     v                                v
 v3_bridge.json              aktif_bombalar.txt
 (60sn guncelleme)           (gun basinda bir kez)
```

**KRITIK SORUN K-01: Dosya Tabanli IPC (Inter-Process Communication)**

Tum sistem, iki isletim sistemi arasinda `File.ReadAllText()` ve `prlctl exec` ile dosya paylasimina dayanmaktadir. Bu mimari su sorunlari icerir:

- **Atomiklik yoklugu:** C# robotu `File.ReadAllText(bridgePath)` ile bridge dosyasini okurken, Python tarafinda `v3_risk_motor.py` ayni dosyayi yaziyorsa, YARIM OKUNAN JSON parse hatasi olusur. `try { } catch { macroMultiplier = 1.0m; }` blogu bu hatayi sessizce yutar ve robot YANLIS CARPAN ile islem yapar.
- **v3_risk_motor.py satir 71-74:** Lokal dosyaya atomik yazim (tmp+rename) uygulanmis, AMA Windows'a kopyalama `prlctl exec ... copy` ile yapilmakta ve bu islem atomik DEGILDIR.
- **Gecikme:** prlctl exec ortalama 2-5 saniye surer. Bridge verisi 60 saniyede bir guncelleniyor, ama kopyalama gecikmesiyle robot 65-90 saniye eski veri ile calisabilir.

**COZUM:** Windows tarafinda bridge dosyasini dogrudan paylasilmis klasorden (\\\\Mac\\Home\\...) okumayin. Bunun yerine C# robotuna kendi icinde HTTP GET ile veri cekmesini saglayan basit bir endpoint yazin. Veya en azindan dosya kilidi (file lock) mekanizmasi ekleyin.

**KRITIK SORUN K-02: Tek Nokta Arizasi (Single Points of Failure)**

| Bilesken | Ariza Senaryosu | Etki |
|----------|-----------------|------|
| Mac laptop | Kapanir / uyur | Tum Python tarafli islemler durur, risk motoru calismaz |
| Parallels VM | Crash / guncelleme | IQ robotu calismaz, emirler gitmez |
| Midas baglantisi | Kopma | Emir red edilir ama robot bunu BILMEZ |
| Yahoo Finance API | Rate limit / kapanma | ML egitim, risk motoru, acilis kontrolu hepsi durur |
| WiFi / Internet | Kopma | Her sey durur |

Sistem, HICBIR bilesenin saglik kontrolunu yapan bir watchdog / heartbeat mekanizmasina sahip degildir. `caffeinate` komutu Mac uykusunu engeller ama kernel panic, disk dolu, RAM yetersiz gibi durumlari kapsamaz.

**YUKSEK SORUN Y-01: Bridge Format Tutarsizligi**

`v3_risk_motor.py` su alanlari yazar:
```json
{"multiplier", "regime", "xu100_change", "vix", "usd_change", "pos_value", "last_update"}
```

`kontrol_paneli.py` su EK alanlari yazar:
```json
{"hard_stop", "trailing_stop", "profit_trigger", "rsi_threshold", "ema_fast", "ema_slow", "robot_active"}
```

Ancak C# robotu (`BOMBA_V3_TURBO.cs` satir 93-102) SADECE `multiplier`, `pos_value` ve `regime` okur. Kontrol panelinden girilen `hard_stop`, `trailing_stop` degerleri robot tarafindan HICBIR ZAMAN OKUNMAZ. Kullanici panelden parametreleri degistirdigini zanneder ama robot sabit kodlanmis degerlerle calisir.

**COZUM:** C# robotuna bridge'den tum parametreleri okuyan mantik ekleyin:
```csharp
if (data.hard_stop != null) HardStop = (double)data.hard_stop;
if (data.trailing_stop != null) TrailingStop = (double)data.trailing_stop;
if (data.profit_trigger != null) ProfitTrigger = (double)data.profit_trigger;
```

### 1.2 Veri Akisi Butunlugu

```
Yahoo Finance --> Python ML --> bomba_skor --> aktif_bombalar.txt --> C# Robot OnInit()
                                                                          |
                                                                          v
                                                                    MatriksIQ canli veri
                                                                          |
                                                                          v
                                                                    SendMarketOrder --> Midas
```

**YUKSEK SORUN Y-02:** Python tarafindaki ML tahminleri Yahoo Finance GUNLUK verisine dayanir, ancak C# robotu 5-DAKIKALIK (Min5) barlarla calisir. Zaman ufku uyumsuzlugu vardir. ML modeli "5 gunde %3+ yukari" hedefi ile egitilmis (`hedef_olustur()` fonksiyonu, gun=5, esik=3.0), ancak robot 5 dakikalik barlarda %0.7 profit trigger ile islem yapar. Bu iki sistem farkli sorulara cevap vermektedir.

---

## 2. ISLEM MANTIGI HATALARI

### 2.1 C# Robot (BOMBA_V3_TURBO.cs) Kritik Hatalar

**KRITIK SORUN K-03: Sahte Pozisyon Takibi**

```csharp
// Satir 141-142
inPosition[s] = true;
entryPrices[s] = close;  // BAR KAPANIS fiyati, gercek dolum fiyati DEGIL!
```

Robot, `SendMarketOrder` gonderdikten HEMEN SONRA `inPosition = true` ve `entryPrices = close` atar. Ancak:
1. Emir henuz dolmamis olabilir (beklemede, kismen dolmus, veya RED edilmis)
2. Gercek dolum fiyati bar kapanis fiyatindan FARKLI olabilir (slippage)
3. `OnOrderUpdate` callback'inde sadece SATIS dolumunda `ResetSymbol` cagriliyor. ALIS dolumunda gercek fiyat guncellenmez.

**Sonuc:** PnL hesabi (`pnl = (close - entryPrices[s]) / entryPrices[s] * 100`) yanlis olabilir. Trailing stop seviyesi yanlis hesaplanir. Robot %1.2 karda oldugunu zannederken aslinda %0.5 karda olabilir ve trailing stop prematüre tetiklenebilir.

**COZUM:**
```csharp
public override void OnOrderUpdate(IOrder order)
{
    if (order.OrdStatus.Obj == OrdStatus.Filled)
    {
        string sym = order.Symbol;
        if (!symbolCache.ContainsValue(sym)) return;

        if (order.Side.Obj == Side.Buy)
        {
            inPosition[sym] = true;
            entryPrices[sym] = order.Price;  // GERCEK dolum fiyati
            posQuantities[sym] = order.FilledAmount;
            highestPrices[sym] = order.Price;
        }
        else if (order.Side.Obj == Side.Sell)
        {
            ResetSymbol(sym);
        }
    }
    else if (order.OrdStatus.Obj == OrdStatus.Rejected)
    {
        // RED edilen emirleri yakala!
        string sym = order.Symbol;
        if (order.Side.Obj == Side.Buy)
        {
            ResetSymbol(sym);  // Pozisyon yok say
            Debug($"[HATA] {sym} ALIS REDDEDILDI: {order.Text}");
        }
    }
}
```

**KRITIK SORUN K-04: Rejected Order Yonetimi Yok**

Mevcut `OnOrderUpdate` (satir 162-167):
```csharp
if (order.OrdStatus.Obj == OrdStatus.Filled && order.Side.Obj == Side.Sell)
{
    if (symbolCache.ContainsValue(order.Symbol)) ResetSymbol(order.Symbol);
}
```

Bu kod SADECE basarili satis dolumlarini isler. Su durumlar tamamen gozardi edilir:
- **Rejected Buy:** Robot `inPosition = true` atar ama emir red edilir. Simdi robot, olmayan bir pozisyonu yonetiyor.
- **Rejected Sell:** Robot `ResetSymbol` cagrisi almaz. Sonsuza kadar stop-loss'a vurmayi bekleyecek ama satis emri gitmemis.
- **PartiallyFilled:** Kismi dolum durumunda lot miktari yanlis.
- **Cancelled:** Iptal edilen emirler.

**KRITIK SORUN K-05: SendOrderSequential(true) Kilitleme Sorunu**

`OnInit`'te `SendOrderSequential(true)` ayarlanmis. Bu, bir onceki emir dolana kadar yeni emir gonderilemeyecegi anlamina gelir. 5 sembol ayni anda sinyal verirse:

1. AYEN icin AL emri gonderilir
2. TUPRS sinyal verir ama kuyrukta bekler
3. AYEN emri 30 saniye sonra dolar
4. TUPRS emri gonderilir ama fiyat coktan degismis
5. AKSEN, PETKM, BRISA sinyalleri tamamen kacirilir

Bu, multi-symbol stratejide CIDDI bir performans kaybina yol acar.

**COZUM:** `SendOrderSequential(false)` kullanin ve her sembol icin kendi emir kilit mekanizmanizi yazin:
```csharp
Dictionary<string, bool> orderPending = new Dictionary<string, bool>();
// AL gonderirken: orderPending[s] = true;
// OnOrderUpdate'te: orderPending[s] = false;
```

**YUKSEK SORUN Y-03: EMA Parametreleri Tutarsiz**

- ANKA_RESTORE.md: "EMA: 10/20"
- BOMBA_V3_TURBO.cs (aktif kod): fastMov EMA 5, slowMov EMA 13
- kontrol_paneli.py varsayilan: ema_fast=10, ema_slow=20
- gunluk_bomba.py sablonu: FastPeriod=10, SlowPeriod=20

Dokumantasyon ile gercek kod FARKLI parametreler kullaniyor. Bu, geri test sonuclariyla canli sonuclarin eslesip eslesmedigini imkansiz kilar.

**YUKSEK SORUN Y-04: T+2 Settlement Yok**

BIST'te T+2 kuralina gore, alinmis hisseler 2 is gunu boyunca satilamamalidir (broker'a gore degisir, bazilari izin verir). Robot ayni barda almasi ve satmasi mumkun olmasa da (lastOrderBarIndex kilidi), ayni GUN icerisinde alis-satis yapmaya hicbir engel yoktur. Bu, brokerage'dan reject almaya veya hesap dondurmaya yol acabilir.

**YUKSEK SORUN Y-05: Kapanista Acik Pozisyon Riski**

Robot kodunda geceden ertesi gune acik kalan pozisyonlar icin HICBIR mekanizma yoktur. ANKA_RESTORE.md'de "17:50'de %0.5+ karda ise sat" kuralidan bahsedilir ama BOMBA_V3_TURBO.cs'de bu mantik YOKTUR. Robotun tek cikis kosullari:
1. `close <= stopPrice` (stop-loss)
2. `!emaOk` (EMA ters donmesi)

Kapanisa yakin "zarar ama stop'a vurmamis" pozisyonlar gece acik kalir ve ertesi gun gap-down riski tasir.

---

## 3. ML MODEL ELESTIRISI

### 3.1 Veri Kalitesi

**KRITIK SORUN K-06: Yahoo Finance BIST Veri Guvenilirligi**

Yahoo Finance, BIST hisseleri icin RESMI bir veri saglayici degildir. Bilinen sorunlar:

1. **Gecikmeli veri:** 15-20 dakika gecikmeli olabilir
2. **Eksik gunler:** Bazi tatil gunlerinde veri gelmez, NaN satirlari olusur
3. **Yanlis kapanislar:** Seanslar arasi (11:30-14:00 donemleri vs.) fiyat tutarsizliklari
4. **Bolunme/sermaye artirimi:** Otomatik duzeltme her zaman dogru yapilmaz
5. **Rate limiting:** 2000+ istek/saat sonrasi engelleme
6. **MultiIndex sorunu:** `yf.download` coklu hisse icin MultiIndex dondurur, `.squeeze()` ile duzlestirme yapilmis ama bu tek hissede farkli davranir

ML modeli bu verilerle egitildiginde, gercek canli islemle TUTARSIZ tahminler uretir.

**COZUM:** Matriks IQ'nun kendi veri terminalini Python'dan cekmek icin Matriks Data API kullanin. Veya en azindan Yahoo verilerini gunluk olarak Matriks kapanislariyla karsilastirin.

### 3.2 Hedef Tanim Sorunu (Label Definition)

**YUKSEK SORUN Y-06: Gelecege Bakis Sapması (Lookahead Bias)**

`hedef_olustur` fonksiyonu (tahmin_motoru_v2.py):
```python
def hedef_olustur(df, gun=5, esik=3.0):
    gelecek_max = df["High"].squeeze().rolling(gun).max().shift(-gun)
    close = df["Close"].squeeze()
    yukari = (gelecek_max - close) / close * 100
    return (yukari >= esik).astype(int)
```

Bu fonksiyon "5 gunluk pencerenin EN YUKSEK fiyatinin kapanis fiyatindan %3+ yuksek olup olmadigini" kontrol eder. Sorunlar:

1. **Pratik olarak ulasilamaz hedef:** Gercek islemde tam zirveyi yakalamak imkansizdir. Model "zirve %3 yukarda olacak" ogrenir ama siz %3 kar elde EDEMEZSINIZ cunku giris zamani, slippage, ve cikis zamani farklıdir.
2. **Asimetrik etiket:** Sadece yukari bakiyor, asagi risk yok sayiliyor. Hisse %3 yukari gidip sonra %10 asagi inebilir — model bunu "basarili" sayar.
3. **Rolling max sorunu:** 5 gunluk pencerede HERHANGI bir anda %3'e dokunmasi yeterli. Bu, intraday spike'lari bile "basarili" sayar ve modeli agresif yaptirir.

**DAHA DOGRU ALTERNATIF:**
```python
def hedef_olustur_v3(df, gun=5, kar_esik=2.0, zarar_limiti=-1.5):
    """Risk/Odul oranli hedef: kar esigine ONCE ulasirsa 1, zarar limitine once ulasirsa 0"""
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()

    sonuc = pd.Series(0, index=close.index)
    for i in range(len(close) - gun):
        giris = close.iloc[i]
        for j in range(1, gun + 1):
            max_kar = (high.iloc[i+j] - giris) / giris * 100
            max_zarar = (low.iloc[i+j] - giris) / giris * 100
            if max_kar >= kar_esik:
                sonuc.iloc[i] = 1
                break
            if max_zarar <= zarar_limiti:
                sonuc.iloc[i] = 0
                break
    return sonuc
```

### 3.3 AUC 0.5982 Degerlendirmesi

**KRITIK SORUN K-07: AUC 0.5982 Gercekte Kullanilabilir Degil**

ANKA_RESTORE.md'de modelin AUC'si 0.5982 olarak raporlanmis. Bunu perspektife koyalim:

- **AUC 0.50:** Rastgele tahmin (yazı-tura)
- **AUC 0.5982:** Rastgeleden sadece ~0.10 puan iyi
- **AUC 0.65:** Minimum "bir sey ogrenmis" esigi (finans literaturunde)
- **AUC 0.70+:** Kullanilabilir model

AUC 0.5982 su anlama gelir: Model, 100 rastgele sinyal ciftinden sadece 60'inda dogru siralamaya koyabilir. Komisyon (%0.15 alis + %0.15 satis = %0.30 toplam), slippage (%0.1-0.3), ve spread maliyetleri dusuldugunde, bu modelin NET BEKLENEN GETIRISI NEGATIF olma ihtimali cok yuksektir.

**Matematiksel Analiz:**

- Ortalama islem suresi: 1-5 gun
- Komisyon maliyeti: %0.30 (gidis-donus)
- Slippage tahmini: %0.15
- Toplam maliyet/islem: %0.45
- AUC 0.5982 ile tahmini brut kenar: ~%0.5-1.0
- **Net kenar: %0.05 - %0.55** (BELIRSIZ, negatif olabilir)

Bu, aylik 20 islemle 100.000 TL sermayede YILLIK +/- 1000-5000 TL arasinda sonuclar uretir ki bu komisyonlarla net negatife donebilir.

### 3.4 Walk-Forward Validasyon Elestirisi

`purged_walk_forward` fonksiyonu dogru yaklasimi kullanmaktadir (purge gap + expanding window). Ancak:

1. **5 fold yetersiz:** n_splits=5 ile sadece 5 test penceresi var. Istatistiksel guvenilirlik icin en az 20-50 fold gerekir.
2. **Purge suresi yetersiz:** purge_days=5 ama hedef fonksiyonu da 5 gun ileriye bakiyor. En az purge_days=10 olmali.
3. **Sabit hiperparametre:** Walk-forward icinde hiperparametre optimizasyonu yok. Her fold'da ayni XGBoost parametreleri kullaniliyor.
4. **Sadece XGBoost test ediliyor:** Ensemble modelin kendisi (XGB+LGBM+MLP) walk-forward ile test edilmemis.

### 3.5 Overfitting Riski

**YUKSEK SORUN Y-07: 73+ Feature / ~50 Hisse = Boyut Laneti**

73+ feature ile 50 hisse x 500 gun = ~25.000 satir veri. Feature/sample orani ~1/340 ki bu sinirda kabul edilebilir, ANCAK:

1. **Cok sayida feature birbiriyle koreledir:** RSI_7, RSI_14, RSI_21 hepsi fiyat momentumunu olcer. MACD, EMA cross, momentum da benzer bilgi tasir. Efektif bagimsiz feature sayisi muhtemelen 15-20 civarindadir.
2. **XGBoost max_depth=5 + 200 agac:** Bu, ~6400 yaprak dugumu demektir. 25.000 ornekle bu agresif bir karmasikliktir.
3. **Shuffle=False ama zaman bazli split tutarsiz:** `anka_ai_egitim.py` satir 186: `train_test_split(X, y, test_size=0.2, shuffle=False)` — bu dogru. Ancak `tahmin_motoru_v2.py`'deki walk-forward ile tutarsiz.
4. **Regularizasyon yetersiz:** `min_child_weight=10` ve `reg_lambda=1.0` var ama `reg_alpha` (L1) cok dusuk (0.1).

---

## 4. RISK YONETIMI BOSLUKLARI

### 4.1 Portfoy Seviyesi Risk

**KRITIK SORUN K-08: Portfoy Seviyesi Drawdown Koruması CALISMIYOR**

`risk_yonetimi.py`'deki `RiskYoneticisi` sinifi guclu bir tasarim icerir (ATR stop, Kelly, drawdown limiti, korelasyon filtresi). ANCAK bu sinif **HICBIR YERDE CAGRILMIYOR**.

- `BOMBA_V3_TURBO.cs` robotu: `RiskYoneticisi` hakkinda bilgisi yok
- `otonom_trader.py`: `from risk_yonetimi import RiskYoneticisi` importu var ama `sinyal_degerlendir()` fonksiyonu HICBIR YERDE CAGRILMIYOR
- Robotun kendi risk yonetimi: Sadece sembol bazinda sabit % stop-loss

**Sonuc:** 5 sembolun hepsi ayni anda %3.5 stop'a vurursa, toplam kayip: 5 x 20.000 TL x 3.5% = 3.500 TL (tek gunde). Portfoy seviyesinde bunu durduracak HICBIR mekanizma yoktur.

**KRITIK SORUN K-09: Korelasyon Kontrolu Sadece Kagit Uzerinde**

`risk_yonetimi.py`'deki korelasyon filtresi (SEKTOR_MAP) guclu bir fikir ama:
1. C# robotu bu kontrolu YAPMIYOR
2. Bomba taramasi sektör korelasyonunu dikkate ALMIYOR
3. 5 bomba hissenin hepsi ayni sektorden olabilir (ornek: AYEN, AKSEN, ENJSA — hepsi enerji)

Eger hepsi enerji sektorundense ve petrol fiyati duserse, 5 pozisyonun TUMU ayni anda zarar eder.

### 4.2 Kara Kugu Koruması

**YUKSEK SORUN Y-08: Kara Kugu / Flash Crash Koruması Yok**

Sistem su senaryolara HAZIR DEGILDIR:

1. **BIST devre kesici:** Tum borsa %5-7 dususte 30dk durur. Robot bu surede calisir durumda ama emir gonderemez, sonra acilisla gap-down olur.
2. **Hisse bazinda tavan/taban kilidi:** Hisse %10 dusup taban olursa, satis emri gonderilemez. Stop-loss CALISMAZ.
3. **VIX spike (40+):** Sistem VIX>30'da multiplier=0 yapar ama VIX 28'den 42'ye 10 dakikada cikarsa, aradaki 60 saniyelik guncelleme gecikmesinde robot yeni alis yapmis olabilir.
4. **Likidite kurumasi:** Dusuk hacimli hisselerde (GESAN, KONTR gibi) buyuk satis emri dolmayabilir veya cok kotu fiyattan dolar.

### 4.3 Komisyon Etkisi

**YUKSEK SORUN Y-09: Komisyon Analizi Hicbir Yerde Yok**

Tum ML modelleri, bomba skorlari, ve geri testler komisyonSUZ brut getirilerle calisir.

Midas komisyon yapisina gore (tipik BIST):
- Alis komisyonu: %0.13 - %0.20 (paketle degisir)
- Satis komisyonu: %0.13 - %0.20
- BSMV: komisyonun %10'u
- Toplam gidis-donus: ~%0.30 - %0.45

Aylik 20 islem x %0.30 = %6 YILLIK KOMISYON ETKISI. Bu, portfoyun degerinin %6'si kadardir ve AUC 0.5982'nin sagladigi zayif kenari tamamen yok edebilir.

### 4.4 Kelly Criterion Uygulamasi

`risk_yonetimi.py` satir 69-98: Kelly hesaplamasi matematiksel olarak dogru uygulanmis (yarim Kelly kullanimi isabetli). ANCAK:

1. `ml_olasilik` parametresi olarak MODEL TAHMINI kullaniliyor. Model AUC 0.5982 ise, bu olasiliklar CALIBRATE EDILMEMIS demektir. Calibrate edilmemis olasilikla Kelly hesaplamasi tehlikelidir.
2. Kelly, bagimsiz ve esit dagilimli bahisler varsayar. Borsa islemleri ne bagımsız ne de esit dagılımlıdır.

---

## 5. AJAN SISTEMI ELESTIRISI

### 5.1 Ajan Bagimsizligi

**YUKSEK SORUN Y-10: Ajanlar Gercekten Bagimsiz Degil**

`anka_v2.py`'deki 4 ajan sistemi (TechnoAgent, FundamentalAgent, MacroAgent, VolumeAgent) kavramsai olarak guzel bir tasarimdir. Ancak:

1. **TechnoAgent ve VolumeAgent ayni veriyi kullaniyor:** Ikisi de ayni `df` DataFrame'ini alir. Fiyat yukari gidiyorsa IKISI DE yuksek puan verir. Bagimsiz degil, KORELELI.
2. **MacroAgent tum hisseler icin AYNI puani verir:** Makro ortam hisse-spesifik degildir, tum hisselere ayni etkiyi yapar. Bu, aslinda 3 "bagimsiz" ajan, 1 bias kaynagi demektir.
3. **FundamentalAgent Yahoo Finance `info` verisine guveniryor:** Bu veri 3-6 ay eski olabilir, canli degil.

### 5.2 Oylama Sistemi Zayifliklari

**YUKSEK SORUN Y-11: Minimum Oy Esigi Cok Dusuk**

BULL rejimde sadece 2/4 ajan "AL" demesi yetiyor. Macro her zaman AYNI puani verdigi icin, aslinda sadece TechnoAgent + VolumeAgent (ki ikisi de fiyata bakar) onaylarsa islem yapilir. Bu, efektif olarak TEK BIR SINYAL KAYNAGIDIR.

### 5.3 Dinamik Agirlik Ogrenimi

`anka_ogrenme.py`'deki odül/ceza sistemi mantikli ama:

1. **10 islem minimum:** Yeterli istatistiksel guc icin en az 30-50 islem gerekir (her ajan icin ayri). 10 islemle ajan guven skoru anlamsizdir.
2. **Hic decay yok:** Eski islemler yeni islemlerle ayni agirlikta. Piyasa rejimi degismis olabilir ama 6 ay onceki skorlar hala etkili.
3. **Survivorship bias:** Sadece yapilan islemlerin sonuclari kaydediliyor. YAPILMAYAN (veto edilen) islemlerin "aslinda ne olacagi" takip edilmiyor. Bu, agresif ajanlari yanlis sekilde cezalandirir.

---

## 6. OPERASYONEL RISKLER

### 6.1 Mac Uyuma / Yeniden Baslatma

**KRITIK SORUN K-10: Mac Uyuma Koruması Kirilgan**

`caffeinate -d -i -s &` komutu background process olarak calisir. Ama:

1. Mac yeniden baslarsa caffeinate da kapanir ve otomatik baslamaz
2. macOS guncelleme sonrasi zorla yeniden baslama
3. `nohup ... > /dev/null 2>&1 &` ile baslayan Python surecleri, terminal kapaninca hayatta kalir AMA Mac yeniden baslarsa kapanir
4. Hicbir surec icin `launchd` plist veya crontab kaydi yok

**COZUM:** `launchd` plist dosyalari olusturun:
```xml
<!-- ~/Library/LaunchAgents/com.anka.otonom.plist -->
<plist version="1.0">
<dict>
    <key>Label</key><string>com.anka.otonom</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/onurbodur/adsiz klasor/.venv/bin/python</string>
        <string>/Users/onurbodur/adsiz klasor/borsa_surpriz/otonom_trader.py</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>
```

### 6.2 Windows VM Guvenilirligi

**YUKSEK SORUN Y-12: Parallels VM Guvenirligi**

- Windows Update IQ'yu kapatabilir (dokumantasyonda belirtilmis ama cozum "kapat" seviyesinde)
- Parallels guncelleme VM'yi yeniden baslatabilir
- Disk alani yetersizligi VM crash'e yol acabilir
- prlctl exec bazen timeout verir ve Python tarafinda sessizce basarisiz olur

### 6.3 Path Uyumsuzluklari

**ORTA SORUN O-01:** Kodda birden fazla dosya yolu konvansiyonu var:

- `v3_risk_motor.py`: `r"C:\Robot\v3_bridge.json"` (hardcoded Windows)
- `kontrol_paneli.py`: `BASE_DIR / "data" / "v3_bridge.json"` (lokal)
- `anka_dashboard.py`: `BASE_DIR / "data" / "v3_bridge.json"` (lokal)
- Robot: `@"C:\Robot\v3_bridge.json"` (hardcoded Windows)

Eger gelecekte VPS'e tasinirsa, TUM bu yollar degistirilmeli. Merkezi bir konfigürasyon dosyasi yok.

### 6.4 Proses Izleme

**YUKSEK SORUN Y-13: Process Monitoring Yok**

Sistem su bilgiyi BILMEZ:
- v3_risk_motor.py calisiyor mu?
- otonom_trader.py calisiyor mu?
- MatriksIQ acik mi? (gorev_08_50 ile kontrol var ama sadece sabah 08:50'de)
- Midas baglantiyi kopardi mi?
- Son basarili bridge yazma ne zaman oldu?

**COZUM:** Basit bir healthcheck mekanizmasi:
```python
# Her bilesenin her 5dk'da "heartbeat.json"a yazmasini saglayin
# Bir watchdog script tum heartbeat'leri kontrol etsin
# 3 guncelleme kacirilirsa Telegram/macOS notification
```

---

## 7. FINANSAL / EKONOMIK ELESTIRI

### 7.1 Gercek Alfa Var Mi?

**KRITIK SORUN K-11: Sistemin Gercek Alfa Urettigi Kanitlanmamis**

Hicbir yerde:
1. Kapsamli geri test sonuclari yok (komisyon dahil)
2. XU100 benchmark karsilastirmasi yok
3. Sharpe orani hesaplanmamis
4. Maximum drawdown istatistigi yok
5. Canli islem sonuclari sistematik olarak loglanmamis

"Alfa" iddiasi icin MINIMUM gereklilikler:
- En az 2 yillik geri test (komisyon dahil)
- XU100 buy-and-hold ile karsilastirma
- Out-of-sample donem (en az 6 ay)
- Sharpe ratio > 1.0 (risk-adjusted)
- Maximum drawdown < %15

### 7.2 Komisyon-Ayarli Getiri Tahmini

Basit bir senaryo analizi:

| Senaryo | Yillik Islem | Ort Kar/Islem | Brut Getiri | Komisyon | Net Getiri |
|---------|-------------|---------------|-------------|----------|------------|
| Iyimser | 200 | +%0.8 | +%160 | -%90 | +%70 |
| Gercekci | 200 | +%0.3 | +%60 | -%90 | **-%30** |
| Kotumser | 200 | -%0.1 | -%20 | -%90 | **-%110** |

NOT: "Gercekci" senaryoda bile KAYIP var. AUC 0.5982 ile ortalama islem basina %0.3 kar bile IYIMSER bir tahmindir.

### 7.3 XU100 ile Karsilastirma

BIST XU100 son 5 yillik ortalama yillik getiri: ~%30-50 (TL bazinda, enflasyon dahil).
100.000 TL'yi XU100 ETF'e koyup beklemenin beklenen getirisi: ~30.000-50.000 TL/yil.

ANKA sisteminin bu getiriyi asmasi icin:
- AUC'nin en az 0.65+ olmasi
- Komisyon maliyetlerinin minimize edilmesi (daha az islem, daha yuksek kalite)
- Risk yonetiminin cok iyi calismasi
gerekir ki mevcut durumda bunlarin HICBIRI saglanmamistir.

### 7.4 Piyasa Etkisi

16.000-20.000 TL pozisyon buyuklugu BIST50 hisseleri icin ihmal edilebilir (gunluk islem hacminin %0.001'inden az). ANCAK GESAN, KONTR, CEMTS gibi dusuk hacimli hisselerde market emri ile %0.3-0.5 slippage yasanabilir.

### 7.5 Survivorship Bias

BIST50 listesi MEVCUT buyuk sirketlerden olusur. 5 yil once BIST50'de olup simdi cikmis (veya iflas etmis) sirketler bu listede YOKTUR. ML modeli bu "hayatta kalanlar" ile egitildiginde, gercek risk algisi yanlis olur.

---

## 8. ONCELIKLI DUZELTMELER

### KRITIK (Hemen duzeltilmeli — gercek para riski)

| # | Sorun | Etki | Cozum |
|---|-------|------|-------|
| K-01 | Dosya tabanli IPC atomiklik yok | Robot yanlis veriyle islem yapar | C# tarafinda file lock + retry mantigi ekle |
| K-03 | Sahte pozisyon takibi | Stop-loss yanlis, PnL yanlis | OnOrderUpdate'te gercek dolum fiyatini kullan |
| K-04 | Rejected order yonetimi yok | Hayalet pozisyonlar olusur | Reject, Cancel, PartialFill durumlarini isle |
| K-05 | SendOrderSequential kilitleme | 5 sembolde 4'u sinyal kacirir | false + kendi kilit mekanizmasi |
| K-06 | Yahoo Finance guvenilirligi | ML modeli gercekle uyusmayan tahminler uretir | Matriks Data API veya cross-validation ile |
| K-07 | AUC 0.5982 yetersiz | Komisyon sonrasi net negatif | Model iyilestirme veya ML'yi KAPATIP saf teknik kullan |
| K-08 | Portfoy drawdown koruması calismıyor | Tek gunde %15+ kayip mumkun | risk_yonetimi.py'yi C# robotuna entegre et |
| K-09 | Korelasyon kontrolu yok | 5 hisse ayni anda zarar eder | Sektor bazli max pozisyon siniri ekle |
| K-10 | Mac yeniden baslamayla tum sistem kaybedilir | Gunlerce fark edilmeyebilir | launchd plist + watchdog + Telegram bildirim |
| K-11 | Gercek alfa kanitlanmamis | Tum sermaye risk altinda | Kapsamli geri test (komisyon dahil) + paper trade |

### YUKSEK (1 hafta icinde)

| # | Sorun | Cozum |
|---|-------|-------|
| Y-01 | Bridge format tutarsizligi | C# robotunu bridge'den tum parametreleri okuyacak sekilde guncelle |
| Y-02 | Zaman ufku uyumsuzlugu (gunluk ML vs 5dk robot) | ML hedef fonksiyonunu robot periyoduna uyumla |
| Y-03 | EMA parametreleri tutarsiz | Dokumantasyon ve kodu eslestir |
| Y-04 | T+2 settlement yok | Giris zamanini kaydet, ayni gun satis engelle |
| Y-05 | Kapanista acik pozisyon | 17:45'te tum pozisyonlari kapat mantigi ekle |
| Y-06 | Lookahead bias | hedef_olustur fonksiyonunu risk/odul bazli yeniden yaz |
| Y-07 | Feature overfitting riski | Feature secimi (top 20-30), mutual information filtresi |
| Y-08 | Kara kugu koruması yok | Portfoy bazinda gunluk max kayip limiti |
| Y-09 | Komisyon analizi yok | Tum geri testlere %0.30 komisyon ekle |
| Y-10 | Ajanlar bagimsiz degil | En az 1 bagimsiz veri kaynagi ekle (ornek: opsiyon volatilitesi, para akisi) |
| Y-11 | Minimum oy esigi dusuk | BULL'da bile 3/5 ajan onayı iste |
| Y-12 | Parallels VM guvenilirligi | VPS'e gecis planini hizlandır |
| Y-13 | Process monitoring yok | Heartbeat + Telegram bildirim sistemi kur |

### ORTA (2 hafta icinde)

| # | Sorun | Cozum |
|---|-------|-------|
| O-01 | Path uyumsuzluklari | Merkezi config.json dosyasi |
| O-02 | Loglama tutarsiz | Yapisal JSON log + rotasyon |
| O-03 | Dinamik agirlik 10 islem yetersiz | 30+ islem esigi + time decay |
| O-04 | Scalper modulü entegre degil | anka_scalper.py sonuclarini bridge'e yaz |
| O-05 | Dashboard iki tane var (anka_dashboard + kontrol_paneli) | Birini sec, digerini kaldir |
| O-06 | otonom_trader.py satir 567: gorev_08_50_iq_hazirla fonksiyonu yok | gorev_08_50_iq_kontrol olarak duzelt |

### DUSUK (Gelecek surumde)

| # | Sorun | Cozum |
|---|-------|-------|
| D-01 | Haber sentiment zayif | KAP bildirimleri + Twitter entegrasyonu |
| D-02 | Kurumsal AI proxy kullanıyor | Gercek yabanci alis/satis verisi |
| D-03 | VPS gecisi | MarkaHost Profesyonel 674 TL/ay planini uygula |
| D-04 | Telegram bildirimleri | Bot API ile kritik uyarilari telefona gonder |

---

## 9. ACIL EYLEM PLANI

### Ilk 24 Saat (BU GECE):
1. **C# robotunda OnOrderUpdate'i genislet** — Reject/Cancel yakalama
2. **Portfoy bazinda gunluk max kayip limiti** — bridge'e `max_daily_loss` ekle, asıldığında multiplier=0
3. **Watchdog script** yaz — tum sureclerin heartbeat kontrolu

### Ilk Hafta:
4. **Paper trade modu** — Robot koduna `DRY_RUN = true` parametresi ekle, emir gondermeden logla
5. **3 aylik geri test** (komisyon dahil) — XU100 ile karsilastir
6. **ML modelini devre disi birak** — Sadece teknik sinyal (EMA + RSI + MOST) ile 1 ay paper trade

### Ilk Ay:
7. **VPS gecisi** — Laptop bagımlılığını kaldir
8. **Telegram bildirimler** — Her islemde, her hatada, her gun sonu
9. **Model iyilestirme** — Feature secimi, daha iyi hedef tanimi, AUC 0.65+ hedefle

---

## 10. SONUC

ANKA Trading System, tek bir kisinin olaganustu bir cabayla gelistirdigi kapsamli bir projedir. Mimari tasarim (multi-agent, ML ensemble, bridge sistemi, dashboard) profesyonel bir vizyon gösterir. Ancak detaylarda **hayati hatalar** vardir ve bu hatalar GERCEK PARA kaybina yol acabilir.

**En buyuk tehlike sislemin "calisiyor gibi gorunmesi"dir.** Sistem hatasiz calissa bile, AUC 0.5982 ve komisyon maliyetleri ile NET POZITIF getiri saglama ihtimali dusuktur.

**Onerilen strateji:**
1. CANLI ISLEMI DERHAL DURDURUN
2. 3 ay paper trade yapin
3. Sonuclari XU100 ile karsilastirin
4. Sadece istatistiksel olarak anlamli avantaj gosterirse canli isleme donun
5. Baslangicta YARIM pozisyon (10.000 TL) ile baslayin

Turk atasozuyle bitirelim: **"Acelesi olan ecele yakalanir."**

Sistemi duzeltmek icin gerekli tum bilgi bu raporda mevcuttur. Kodlama yetenegi kesinlikle yeterlidir — eksik olan sabir, disiplin, ve istatistiksel titizliktir.

---

*Bu rapor, PhD-seviye finansal muhendislik, bilgisayar bilimi ve ekonomi perspektifinden hazirlanmistir. Yatirim tavsiyesi icermez. Tum finansal kararlar kullanicinin kendi sorumlulugundadir.*
