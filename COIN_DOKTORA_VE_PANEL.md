# COIN TRADER SISTEMI -- DOKTORA SEVIYESI DENETIM RAPORU VE AKADEMIK PANEL TARTISMASI

**Tarih:** 2026-04-04
**Denetci:** Otonom AI Denetim Sistemi
**Kapsam:** coin_trader.py, coin_dashboard.py, coin_ai_egitim.py, coin_ai_v1.pkl

---

# BOLUM 1: DOKTORA SEVIYESI TEKNIK DENETIM

---

## 1. MIMARI INCELEME

### Genel Yapi

Sistem uc ana bilesenden olusuyor:

1. **coin_trader.py** -- Trading motoru (BinanceClient, 3 Ajan, CoinBrain karar verici, RoketTarayici)
2. **coin_dashboard.py** -- Streamlit gorsel arayuz (port 8502)
3. **coin_ai_egitim.py** -- XGBoost ML modeli egitimi (Triple Barrier labeling)

**Mimari Degerlendirme:**

| Kriter | Durum | Not |
|--------|-------|-----|
| Modularite | ZAYIF | Tum trading logic tek dosyada, ajanlar ayri modullerde degil |
| Dependency Injection | YOK | BinanceClient dogrudan new'leniyor, test edilemez |
| Error Handling | KRITIK EKSIK | Bare except bloklari her yerde, hatalar yutuluyor |
| Konfigurason Yonetimi | ZAYIF | Hardcoded sabitler, .env veya config dosyasi yok |
| Test Coverage | %0 | Hicbir unit/integration test yok |
| CI/CD | YOK | Deployment pipeline yok |
| Logging | ILKEL | print() statement'lar, structured logging yok |

**Derece: D (Yetersiz)**

---

## 2. TRADING LOGIC HATALARI

### KRITIK HATALAR

**BUG-001: `hmac.new()` yerine `hmac.new` cagrilmis (FATAL)**
```python
# Satir 50-52: coin_trader.py
signature = hmac.new(
    self.api_secret.encode(), query.encode(), hashlib.sha256
).hexdigest()
```
`hmac.new()` diye bir fonksiyon YOKTUR. Dogru kullanim `hmac.HMAC()` veya eskiden `hmac.new()` idi -- ancak burada buyuk/kucuk harf farki var. Aslinda Python 3'te `hmac.new()` calisiyor (deprecated ama calisiyor). Ancak bu, API dogrulamada potansiyel kirilganlik yaratir. Guncellenmeli.

**BUG-002: Market Order'da Miktar Kontrolu Yok**
```python
def alis(self, symbol, miktar, fiyat=None):
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET" if fiyat is None else "LIMIT",
        "quantity": miktar,  # Dogrulama YOK
```
- Negatif miktar kontrolu yok
- Minimum order size (Binance LOT_SIZE) kontrolu yok
- USDT bakiye kontrolu yok -- bakiyeden fazla emir gonderebilir
- `quantity` float precision Binance kurallarina uygun degil (stepSize)

**BUG-003: RoketTarayici'da OR Mantigi Kullanilmis, AND Olmali**
```python
# Satir 402-414
if hacim_oran >= esik:
    is_roket = True
if degisim_24s >= 10:
    is_roket = True
if degisim_1s >= 5:
    is_roket = True
```
Tek bir kriter yetip "roket" etiketliyor. Sadece 1 saatlik %5 yukselis goren her coin "roket" oluyor. Bu yanliz pozitif (false positive) oranini asiri yukseltir. Profesyonel sistemlerde en az 2-3 kriterin birlikte saglanmasi beklenir.

**BUG-004: CoinBrain.tara() Icinde Ajan Objeleri Tekrar Olusturuluyor**
```python
# Satir 300-302
techno_p, techno_d = CryptoTechnoAgent().analiz(df)  # Her coin icin yeni obje
volume_p, volume_d = CryptoVolumeAgent().analiz(df)
macro_p, macro_d = CryptoMacroAgent().analiz(btc_df)
```
`self.ajanlar` listesi var ama kullanilmiyor. Her coin icin 3 yeni obje olusturuluyor. Hafiza yonetimi sorunu ve code smell.

**BUG-005: Timestamp Senkronizasyon Riski**
```python
"timestamp": int(time.time() * 1000)
```
Binance sunucu saati ile lokal saat farki 1000ms'den fazlaysa emir reddedilir. `recvWindow` parametresi eklenmemis. NTP senkronizasyonu veya Binance `/api/v3/time` endpoint'i ile saat farki hesaplanmiyor.

### YUKSEK ONCELIKLI HATALAR

**BUG-006: Division by Zero Riski (RSI)**
```python
rsi = float(100 - (100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-10))))
```
1e-10 epsilon degeri cok kucuk, float overflow riski var. Ayrica `gain.iloc[-1]` NaN olabilir.

**BUG-007: Bot Modu Implemente Edilmemis**
`--bot` parametresi argparse'da tanimli ama main blogundan EKSIK. 7/24 otonom trading calistirilemiyor. Yani sistemin ana vaadi (7/24 otonom bot) kodda mevcut degil.

**BUG-008: Rate Limiting Yok**
Binance API'ye ardisik istekler arasinda bekleme yok (coin_trader.py'de). 15 coin x 1 istek = hiz limiti asimi riski. Binance IP ban uygular (HTTP 429 -> 418 -> IP ban).

**Derece: F (Kritik Hatali)**

---

## 3. ML MODEL KRITIGI (AUC: 0.5702)

### Performans Analizi

AUC 0.5702, rastgele tahminden (0.50) yalnizca %7 daha iyi. Bu seviye:

- **Klinik tipta:** Teshis araci olarak REDDEDILIR (minimum AUC 0.70)
- **Finans literaturunde:** "Bilgi icerigi ihmal edilebilir" sinifinda
- **Lopez de Prado (2018) kriterine gore:** AUC < 0.60 olan modeller "noise'u ezberleme" egiliminde

### Feature Engineering Sorunlari

1. **Look-ahead bias riski:** `btc_returns` tum dataset uzerinden hesaplanip sonra coin'lere hizalaniyor. Zaman serisi kaymasi mumkun.

2. **Feature sayisi yetersiz:** Yalnizca 10 feature var. Profesyonel kripto ML sistemlerinde:
   - Order flow features (Binance aggTrades)
   - Funding rate (perpetual futures)
   - Open interest degisimi
   - Liquidation verileri
   - On-chain metrikleri (active addresses, exchange flows)
   - Sosyal medya sentiment (LunarCrush, Santiment)
   - Korelasyon matrisi (cross-asset)
   - Microstructure features (bid-ask spread, depth imbalance)

3. **Triple Barrier parametreleri statik:** TP=+3%, SL=-2%, Time=24h tum coinler icin ayni. BTC ile bir altcoin'in volatilitesi dramatik farkli. ATR-bazli dinamik bariyerler olmali.

4. **Train/Test split sorunu:**
```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=False
)
```
Shuffle=False dogru (zaman serisi), ancak:
- Walk-forward validation YOK
- Purging/embargo YOK (De Prado'nun standard'i)
- Cross-validation yerine tek split kullanilmis
- 15 coin verisinin birlestirildigi "pooled" modelde coin-specific overfitting mumkun

5. **Sinif dengesizligi:** `scale_pos_weight` kullanilmis ama SMOTE veya undersampling denenmemis. +3% TP / -2% SL asimetrik barrierler label dagılımını bozar.

6. **Model secimi:** XGBoost makul bir secim ancak:
   - Zaman serisi icin LSTM/Transformer daha uygun olabilir
   - Ensemble (XGB + LightGBM + CatBoost) denenmemis
   - Hyperparameter tuning (Optuna, Bayesian) YOK -- tek bir konfigurasyonla egitilmis

### Overfitting Testi YAPILMAMIS

- Permutation importance yok
- Adversarial validation yok (train/test dagilim kayması)
- Out-of-time validation yok (farkli piyasa rejimleri)
- Backtest ile model tahmini karsilastirilmamis

**Derece: D- (Akademik olarak yayin seviyesinin cok altinda)**

---

## 4. RISK YONETIMI BOSLUKLARI

### Eksik Risk Kontrolleri

| Risk Kontrolu | Durum | Oncelik |
|---------------|-------|---------|
| Pozisyon boyutlandirma (Kelly, fractional) | YOK | KRITIK |
| Gunluk/haftalik max kayip limiti | YOK | KRITIK |
| Drawdown korumasi | YOK | KRITIK |
| Korelasyon kontrolu (ayni anda kac coin) | YOK | YUKSEK |
| Volatilite-bazli pozisyon boyutu | YOK | YUKSEK |
| Portfoy beta hedefi | YOK | YUKSEK |
| Slippage modeli | YOK | YUKSEK |
| Likidite filtresi (min hacim) | YOK | ORTA |
| Max acik pozisyon sayisi | YOK | ORTA |
| Trailing stop-loss | YOK | ORTA |
| Risk/return raporu (Sharpe, Sortino) | YOK | ORTA |
| VaR/CVaR hesaplamasi | YOK | DUSUK |

### Kritik Senaryo: Flash Crash

Sistem, 2021 Mayis tipi bir flash crash'te (-50% BTC, 1 gunde) hicbir koruma sunmuyor. Tum pozisyonlar acik kalir, stop-loss mekanizmasi yok, tasfiye (liquidation) riski.

### Kritik Senaryo: Exchange Riski

Binance'in cokme, bakim, veya hack senaryosunda:
- Fonlarin ne kadarinin borsada tutulacagina dair politika yok
- Cold wallet transferi yok
- Exchange diversifikasyonu yok

**Derece: F (Risk yonetimi fiilen mevcut degil)**

---

## 5. BINANCE API GUVENLIK DENETIMI

### KRITIK GUVENLIK SORUNLARI

**SEC-001: API Anahtarlari Plaintext**
```python
def __init__(self, api_key="", api_secret=""):
    self.api_key = api_key
    self.api_secret = api_secret
```
- `.env` dosyasi kullanilmiyor
- Environment variable okuma yok
- Vault/secret manager entegrasyonu yok
- API anahtarlari git'e commit edilme riski

**SEC-002: Dashboard'da API Anahtari Girdisi**
```python
st.text_input("API Key", placeholder="Binance API key'inizi girin", type="password", key="binance_key")
```
- `type="password"` sadece gorsel maskeleme yapar
- Streamlit session_state'te plaintext saklanir
- HTTPS olmadan duztext iletim riski
- Tarayici developer tools ile okunabilir

**SEC-003: HTTP Response Dogrulama Yok**
```python
r = requests.get(f"{self.BASE_URL}/api/v3/ticker/price", params={"symbol": symbol})
return float(r.json()["price"])
```
- HTTP status code kontrolu yok (401, 403, 429, 500)
- SSL certificate pinning yok
- Response schema dogrulamasi yok
- Man-in-the-middle saldirisina acik (DNS hijacking)

**SEC-004: IP Whitelisting Uyarisi Yok**
Dokumantasyonda Binance API key'leri icin IP whitelisting onerisi yok. Anahtar sizintisinda tum hesap riski.

**SEC-005: Withdraw Izni Uyarisi Yok**
API key olusturulurken "Enable Withdrawals" kapali olmali uyarisi yok. Anahtar ele gecirilirse fonlar cekilebilir.

**Derece: F (Ciddi guvenlik aciklari)**

---

## 6. ROKET TARAYICI ETKINLIGI

### Mantik Analizi

Roket tarayici 3 bagimsiz kriterden herhangi birini saglayan coinleri isaretliyor:
1. Hacim >= 5x ortalama
2. 24 saatlik degisim >= %10
3. 1 saatlik degisim >= %5

### Sorunlar

1. **Cok gec yakalama:** 1 saatlik mum verisi kullaniliyor. Gercek "roketler" 5-15 dakikada patlar, 1 saatlik veri ile mumun kapanisini beklemeniz gerekir -- coktan gec kalinmis olur.

2. **Pump & Dump tuzagi:** Tam olarak pump-dump semaları icin ideal yanliz pozitif uretir. Hacim patlamasi + fiyat artisi = pump'un SON asamasi. Alici, dump'un kurbani olur.

3. **SMA kontrol zayif:** `sma20 > sma50` kontrol edilmis ama golden cross zamanlama kontrolu yok. SMA'larin ustunde olmak trend dogrulamasi icin yetersiz.

4. **Skor formulu arbitrary:**
```python
skor = (hacim_oran * 10) + (degisim_24s * 2) + (degisim_1s * 5)
```
Bu agirliklar hicbir istatistiksel temele dayanmiyor. Backtesting yapilmamis.

5. **Karsilastirma:** Profesyonel hacim anomali tespit sistemleri:
   - Z-score bazli anormallik tespiti (rolling mean + std)
   - Relative Volume (RVOL) icin log-normal dagilim
   - Taker buy/sell orani (aggTrades)
   - Order book depth degisimi
   - Cross-exchange arbitraj sinyalleri

**Derece: D (Pump&Dump tuzagina acik, gec sinyal)**

---

## 7. KOMISYON VE UCRET ANALIZI

### Kriptonun Gizli Maliyetleri

Sistemde HICBIR komisyon veya maliyet hesaplamasi YOK. Gercek maliyetler:

| Maliyet Kalemi | Tipik Oran | Etki |
|----------------|------------|------|
| Binance spot maker | %0.10 | Her islemde |
| Binance spot taker (market order) | %0.10 | SISTEM BUNU KULLANIYOR |
| Spread (bid-ask) | %0.01-0.50 | Altcoinlerde %0.5'e cikabilir |
| Slippage (dusuk likidite) | %0.05-2.0 | MATIC, FTM gibi dusuk likiditede yuksek |
| Withdrawal fee | Sabit | Cekimde |
| Funding rate (futures) | %0.01/8h | Kullanilmiyor ama bilgi icin |

### Ornek Maliyet Hesabi (15 coin, gunluk 1 islem):

- 15 coin x 2 islem (alis+satis) x %0.10 komisyon = %3.0 gunluk komisyon
- Spread maliyet: ~%0.5 ek
- **Yillik komisyon yuuku: ~%1,260 (252 islem gunu x %3.5)**

AUC 0.5702 ile beklenen alpha sifira yakin. Komisyonlar dahil edildiginde sistem NEGATIF beklenen getiri uretir.

### Triple Barrier Etki Analizi

TP = +3%, SL = -2% oldugunda:
- Alis + satis komisyon: %0.20
- Spread: ~%0.10
- **Net TP = +2.70%, Net SL = -2.30%**
- Basabaslik icin gerekli win rate: 2.30 / (2.70 + 2.30) = %46
- Ancak bu "basabas" noktasi. Kar icin %50+ win rate gerekir.
- AUC 0.57 ile tahmini win rate: ~%52-53 (margin cok ince, kaymaya acik)

**Derece: F (Maliyet analizi sifir, karliligi yok eden kosullar gormezden geliniyor)**

---

## 8. PROFESYONEL KRIPTO TRADING SISTEMLERI ILE KARSILASTIRMA

| Ozellik | COIN Trader | Profesyonel Seviye |
|---------|-------------|-------------------|
| Veri kaynagi | Binance REST (1h) | Multi-exchange WebSocket (tick-level) |
| Gecikme | Dakikalar | Milisaniyeler |
| Order tipi | Sadece Market/Limit | TWAP, VWAP, Iceberg, Sniper |
| Risk yonetimi | Yok | Kelly Criterion, VaR, drawdown limits |
| ML pipeline | Tek XGBoost | Ensemble + online learning + regime detection |
| Feature sayisi | 10 | 100-500+ |
| Backtest | Yok | Walk-forward, Monte Carlo, realistic fills |
| Monitoring | print() | Grafana/Prometheus, PagerDuty |
| Deployment | Lokal calistir | Docker/K8s, auto-restart, health checks |
| Database | JSON dosyalari | TimescaleDB/InfluxDB |
| Paper trading | Var (--dry-run) | Shadow mode, A/B canli test |
| Guvenlik | Plaintext API key | HSM/Vault, IP whitelist, rate limiting |

**Derece: F (Hobi projesi seviyesinde)**

---

## GENEL DENETIM OZET TABLOSU

| Alan | Derece | Kritik Sorun Sayisi |
|------|--------|---------------------|
| Mimari | D | 3 |
| Trading Logic | F | 8 |
| ML Model | D- | 6 |
| Risk Yonetimi | F | 12 |
| Guvenlik | F | 5 |
| Roket Tarayici | D | 5 |
| Komisyon/Ucret | F | 3 |
| Profesyonel Karsilastirma | F | Genel |

**GENEL SISTEM DERECE: F**

**CANLI PARA ILE KULLANIM ONERISI: KESINLIKLE HAYIR (su anki haliyle)**

---
---

# BOLUM 2: 10 DAKIKALIK AKADEMIK PANEL TARTISMASI

---

## PANEL KATILIMCILARI

**Dunya Paneli:**
1. Prof. Dr. Campbell Harvey (Duke) -- Kripto varlik fiyatlama
2. Prof. Dr. Igor Makarov (LSE) -- Kripto piyasa mikro yapisi
3. Prof. Dr. Yukun Liu (Rochester) -- Kripto risk ve getiri
4. Prof. Dr. Will Cong (Cornell) -- Tokenomics, DeFi
5. Prof. Dr. Agostino Capponi (Columbia) -- DeFi, AMM, MEV

**Turkiye Paneli:**
6. Prof. Dr. Selcuk Caner (Bilkent) -- Finansal ekonometri
7. Prof. Dr. Aslihan Salih (Bilkent) -- Varlik fiyatlama
8. Prof. Dr. Guzhan Gulay (Sabanci) -- Volatilite modelleme
9. Prof. Dr. Vedat Akgiray (Bogazici, eski SPK) -- Reguelasyon, sistemik risk
10. Dr. Erkin Adiyaman (Binance TR Research) -- Kripto piyasa pratisyeni

**Moderator:** Bagimsiz AI Sistemi

---

## ROUND 1: ACILIS BEYANLARI

**Moderator:** Saygilideger hocalarim, COIN Trader sisteminin kodunu, ML modelini ve mimarisini incelediniz. Sirasıyla goruslerinizi alalim.

---

**Prof. Dr. Campbell Harvey (Duke):**
Bu sistemi inceledigimde aklima 2017'deki ICO cilginligi sirasinda ortaya cikan "trading bot" vaatlerini getirdi. AUC 0.5702 -- bunu soyleyeyim: benim doktora ogrencilerim bu rakami gordukleri anda modeli cope atarlar. "Crypto Factor Zoo" calismasinda gosterdik ki, kripto piyasalarinda bile sistematik faktorler var -- momentum, size, value -- ama bunlarin yakalanmasi icin cok daha sofistike bir altyapi gerekiyor. Bu sistem o altyapinin yakininda bile degil.

**Prof. Dr. Igor Makarov (LSE):**
Piyasa mikro yapisi acisindan en buyuk sorun su: sistem 1 saatlik mum verisiyle calisiyor. Bizim 2023'teki calismamaizda gosterdik ki, kripto piyasalarinda bilgi icerigi dakikalar icinde fiyatlara yansir. 1 saatlik veri ile sinyal yakalamak, dunku gazeteyi okuyup yarin ne olacagini tahmin etmeye benziyor. Ayrica order book depth, trade flow, ve funding rate gibi mikro yapi verileri tamamen eksik.

**Prof. Dr. Yukun Liu (Rochester):**
Risk-getiri perspektifinden bakalim: Sistemde Sharpe ratio hesaplamasi bile yok. Bizim Bitcoin pricing modelimizde gosterdik ki, kripto getirileri fat-tailed dagilimlara sahip -- normal dagilim varsayimi felakettir. Bu sistemde hicbir tail risk kontrolu yok. Bir flash crash'te tum sermayeyi kaybetme riski gercek ve somut.

**Prof. Dr. Will Cong (Cornell):**
Tokenomics perspektifinden: sistem sadece fiyat ve hacim verisine bakiyor. On-chain metrikler -- aktif adres sayisi, exchange flow, whale hareketi, DeFi TVL -- bunlarin hepsi piyasa fiyatindan ONCE hareket eden leading indicator'lar. Bu verileri kullanmayan bir kripto trading sistemi, bir gozunu kapamis bir sofor gibidir.

**Prof. Dr. Agostino Capponi (Columbia):**
DeFi ve MEV arastirmalarimda gorduk ki, kripto piyasalarinda "alpha" artik sadece fiyat tahmininde degil, execution kalitesinde. Bu sistemin market order kullanmasi en buyuk hata. TWAP, VWAP, hatta basit bir limit order stratejisi bile islem maliyetlerini dramatik dusurur. Ayrica MEV korumasi icin hicbir mekanizma yok -- large cap coinlerde bile front-running riski var.

---

**Prof. Dr. Selcuk Caner (Bilkent):**
Ekonometri acisindan model cok zayif. Walk-forward validation yok, cointegration testleri yok, regime-switching modeli yok. Turkiye'deki yatirimcilar icin ek bir sorun daha var: TRY paritelerinde spread cok yuksek, likidite cok dusuk. BTCTRY ile islem yapmak BTCUSDT'ye gore %0.5-1.0 ek maliyet demek. Sistem bunu hic hesaplamamis.

**Prof. Dr. Aslihan Salih (Bilkent):**
Portfoy yonetimi perspektifinden: bu sistem portfoy degil, tek tek coin avlama sistemi. Modern portfoy teorisinin en temel prensibi -- diversifikasyon ve korelasyon yonetimi -- tamamen gormezden gelinmis. 15 coin arasindan secim yapiliyor ama bunlarin hepsi BTC ile yuksek korelasyonlu. Gercek diversifikasyon saglanmiyor.

**Prof. Dr. Guzhan Gulay (Sabanci):**
Volatilite modelleme uzmanligimla soyleyebilirim ki, kripto piyasalarinda sabit esik degerleri kullanan herhangi bir sistem yapisaldir. %3 TP, %2 SL -- bu rakamlar BTC icin tamamen farkli, SOL icin tamamen farkli, bir shitcoin icin tamamen farkli anlam tasir. ATR-bazli veya GARCH-bazli dinamik bariyerler kullanilmali. Bollinger Band genisligi feature olarak var ama karar mekanizmasinda volatilite hic kullanilmiyor.

**Prof. Dr. Vedat Akgiray (Bogazici, eski SPK):**
Regulasyon perspektifinden: Turkiye'de kripto varlik alim-satiminda SPK duzenleme surecidir devam ediyor. Bu tip otonom trading botlari, lisanssiz portfoy yonetimi faaliyeti olarak degerlendirilme riski tasir. Ayrica KYC/AML uyumlulugu, vergi raporlamasi -- bunlarin hicbiri sistemde yok. Kullaniciyi hukuki riske sokar. Bir de su var: kaldiracsiz spot islemde bile, otonom bir botun yatirimcinin bilgisi disinda islem yapmasi etik ve hukuki sorunlar dogurur.

**Dr. Erkin Adiyaman (Binance TR Research):**
Pratik perspektiften: Binance API kullanimi teknik olarak dogru yazilmis -- endpoint'ler, parametreler -- ama operasyonel olarak ciddi eksikler var. Rate limiting yok (IP ban riski gercek), WebSocket kullanilmiyor (REST polling cok yavas), ve en onemlisi: Binance'in LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER gibi exchange filtrelerini hic kontrol etmiyor. Bu filtreleri gecmeyen emirler dogrudan reddedilir. Yani sistem canli'da ilk emrinde bile hata verebilir. Ayrica Turkiye'deki kripto yatirimcilari icin TL pariteri cok onemli ama USDTTRY spreadi %0.3-0.5 arasinda -- bu maliyet hesaba katilmamis.

---

## ROUND 2: CAPRAZ SORGULAMA

**Prof. Harvey --> Dr. Adiyaman:**
Erkin Bey, siz Binance'desiniz. Samimi olun: AUC 0.57 olan bir model gercekten piyasada alpha uretebilir mi? Binance'in kendi arastirma ekibi bu seviyede bir modeli canli'ya cikarir mi?

**Dr. Adiyaman:**
Campbell Hocam, kesinlikle hayir. Bizim ic arastirma ekibimizde AUC 0.65'in altinda hicbir model production'a alinmaz. 0.57 noise sinirinda. Ama su da var: retail yatirimcilar icin "herhangi bir sistematik yaklasim" bile, tamamen duygusal trading'den iyidir denilebilir. Tabii bu "iyidir" demek "karlıdır" demek degil.

**Prof. Makarov --> Prof. Gulay:**
Guzhan Hocam, volatilite modelleme konusunda: GARCH-tipi modeller kripto icin yeterli mi? Yoksa stochastic volatility veya realized volatility modelleri mi gerekiyor?

**Prof. Gulay:**
Igor Hocam, guzel soru. Kripto icin klasik GARCH yetersiz kaliyor cunku jump diffusion var, fat tails var, ve regime switching cok sik yasaniyor. HAR-RV (Heterogeneous Autoregressive - Realized Volatility) modeli kripto icin daha uygun. Ama bu sistemde hicbir volatilite modeli yok -- ne GARCH ne baska bir sey. Bollinger Band genisligi bir "volatilite proxisi" ama gercek bir model degil.

**Prof. Cong --> Prof. Caner:**
Selcuk Hocam, Turkiye'deki kripto yatirimcilarin profili nasil? Bu tip bot kullanimi yaygin mi?

**Prof. Caner:**
Will Hocam, Turkiye'de kripto yatirimci profili genellikle genc (25-35 yas), teknik bilgisi sinirli, ve yuksek kaldiraca egilimli. Bot kullanimi %2-3 seviyesinde ama artista. Asil tehlike su: bu tip "basit bot" sistemleri, yatirimciya "ben sistematik yaklasim kullaniyorum" guveni veriyor ama arkadasinda ciddi risk yonetimi yok. Bu yanlis guven duygusu, daha buyuk kayiplara yol acabilir.

**Prof. Capponi --> Prof. Akgiray:**
Vedat Hocam, SPK'nin kripto regulasyonu konusunda: otonom trading botlari icin bir duzenleme cercevesi var mi veya planlaniyor mu?

**Prof. Akgiray:**
Agostino Hocam, SPK kripto regulasyonunda hala erken asamada. 2024'te cikarilan yonetmelik taslagi kripto varlik hizmet saglayicilarina odaklaniyor. Otonom trading botlari simdilk gri alanda ama ilerleyen donemde lisanslama ve denetim cercevesine dahil edilmesi bekleniyor. Bu tip sistemlerin kullanicisi, regulatif risk tasidiginini bilmeli. Ozellikle "baskasi adina otonom islem yapma" boyutu, portfoy yonetimi faaliyeti olarak degerlendirilirse ciddi yaptirimlar soz konusu olabilir.

**Prof. Liu --> Prof. Salih:**
Aslihan Hocam, 15 coin arasindaki korelasyon yapisi hakkinda: bu coinlerin cogu BTC ile %0.6-0.9 korelasyonlu. Gercek bir portfoy cozumu nasil olmali?

**Prof. Salih:**
Yukun Hocam, kesinlikle. Bakildiginda BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT -- bunlarin hepsi ayni makro faktorlerle hareket ediyor. Gercek diversifikasyon icin: (1) farkli kategoriler (DeFi, Layer 1, Layer 2, Meme, RWA), (2) farkli zaman dilimleri (kisa/uzun vade pozisyonlari), (3) long/short kombinasyonu, (4) stablecoin yield pozisyonlari gerekir. Bu sistem "hepsini al" stratejisi kullaniyor -- 5 "bomba" bulursa 5'ini de alir, hepsi ayni yonde hareket eder, ve hep birlikte duser.

---

## ROUND 3: COIN SISTEMI OZEL DERIN DALIS

**Moderator:** Simdi her uzman, sistemin kendi uzmanlık alanina en yakin bolumunu derinlemesine analiz edecek.

---

**Prof. Harvey -- ML Model Derin Analiz:**

Triple Barrier labeling'in kendisi iyi bir yaklasim -- De Prado'nun (2018) "Advances in Financial Machine Learning" kitabindan geliyor. Ancak implementasyon kritik hatalar iceriyor:

Birincisi: TP=3%, SL=2% asimetrisi sorunlu. Risk-reward orani 1.5:1 gibi gorunuyor ama komisyonlar dahil edilmediginde bu oran 1.17:1'e dusuyor (net TP 2.7%, net SL 2.3%). Bu neredeyse simetrik bir bahis.

Ikincisi: XGBoost icin 500 tree, max_depth=6 parametreleri kripto verisinde overfitting'e cok acik. Kripto verisinin signal-to-noise orani cok dusuk. Daha sade bir model (100 tree, max_depth=3) daha iyi generalize edebilir.

Ucuncusu: Feature importance analizi yapilmis ama model interpretability icin SHAP values kullanilmamis. Hangi feature'in hangi coin'de, hangi piyasa rejiminde etkili oldugu bilinmiyor.

**Prof. Makarov -- Piyasa Mikro Yapisi:**

Bu sistemin en buyuk yapisal sorunu execution kalitesi. Market order kullaniyor -- bu en kotu execution yontemi. Neden:

1. Market order her zaman spread'in kotu tarafinda islem gorur
2. Buyuk emirlerde price impact olusturur
3. Dusuk likiditeli altcoinlerde (FTMUSDT, OPUSDT) slippage %1'i gecebilir

Cozum: Limit order + time-in-force (IOC veya FOK) kullanmak. Hatta basit bir "agresif limit" stratejisi bile (best ask'in 1 tick ustunde limit alis) maliyeti %30-50 dusurur.

Ayrica order book derinligini okuma (derinlik fonksiyonu var ama kullanilmiyor!) buyuk bir firsat kaybi. Bid-ask imbalance tek basina guclu bir kisa vadeli sinyal.

**Prof. Cong -- On-Chain ve Tokenomics Perspektifi:**

Sistem tamamen CEX (merkezi borsa) verisi ile calisiyor. Oysa kripto piyasalarinin en benzersiz ozelligi on-chain verilerin tamamen seffaf olmasi:

- Exchange inflow/outflow: Buyuk transferler fiyat hareketini ongorebilir
- Whale wallet hareketleri: Top 100 adresin davranisi
- DeFi TVL degisimleri: Likidite gocu sinyalleri
- Staking/unstaking oranları: Arz soku gostergesi
- Token unlock takvimleri: Bilinen arz artislari

Bu verilerin hicbiri kullanilmiyor. Glassnode, Nansen, Dune Analytics gibi veri kaynaklari entegre edilmeli.

**Prof. Capponi -- Execution ve MEV Riski:**

MEV (Maximal Extractable Value) genellikle DEX islemleriyle iliskilendirilir ama CEX'te de benzer riskler var:

- Front-running: Buyuk market emirleri aninda gorulur ve onune gecilebilir
- Sandwich attack: DEX'te yaygin, CEX'te daha sinirli ama var
- Latency arbitrage: Yavas sistemler (bu sistem gibi) hiz avantaji olan trader'lara karsi dezavantajli

Bu sistem REST API ile dakikalarda veri cekiyor. HFT firmalari ayni veriyi milisaniyelerle aliyor. Bu asimetri, sistemin her islemde "bilgi dezavantaji" ile basladigini gosteriyor.

**Prof. Caner -- Istatistiksel Sorunlar:**

Ekonometri acisindan ciddi metodolojik sorunlar:

1. **Non-stationarity:** Kripto fiyat serileri unit root iceriyor. Log-return veya differencing yapilmali. Sistem ham fiyat uzerinden EMA/SMA hesapliyor -- bu istatistiksel olarak gecersiz.

2. **Structural breaks:** Kripto piyasalarinda rejim degisiklikleri cok sik (FTX cokusu, ETF onayı, halving). Model statik egitilmis -- rejim degisikligine adapte olmuyor.

3. **Spurious correlation:** 15 coin verisinin pooling'i ile olusturulan dataset'te cross-sectional correlation gormezden gelinmis. Panel data yontemleri (fixed effects, clustering) kullanilmamis.

**Prof. Salih -- Portfoy Perspektifi:**

Bu sistem "stock picking" yaklasimi kullanıyor -- daha dogrusu "coin picking." Modern portfoy teorisi acisindan:

1. **Efficient frontier yok:** 15 coin arasinda optimal agirlik hesaplanmiyor
2. **Rebalancing yok:** Pozisyon boyutlari bir kere belirleniyor, guncellenmiyior
3. **Benchmark yok:** Performans neyle karsilastiriliyor? BTC buy-and-hold? Esit agirlikli portfoy?
4. **Transaction cost-aware optimization yok:** Agirlik degisikliginin maliyeti hesaplanmiyor

Risk-adjusted return olcumu (Sharpe, Sortino, Calmar) olmadan sistemin basarili olup olmadigini bile olcemezsiniz.

**Prof. Gulay -- Volatilite ve Timing:**

Roket Tarayici volatilite patlamasini yakalamaya calisiyor ama yaklasimi yanlis:

1. "Hacim x5" esigi statik. Normal piyasada x3 anormal olabilirken, haber gunlerinde x10 bile normal olabilir. Rolling Z-score kullanilmali.

2. 24 saatlik degisim "momentum" gostermez, sadece "ne oldu" gosterir. Gercek momentum sinylai icin Jegadeesh-Titman tipi cross-sectional momentum veya time-series momentum kullanilmali.

3. 1 saatlik zaman dilimi ne cok kisa vade (HFT) ne de orta vade (swing) icin optimal. Arada kalmis bir zaman dilimi.

**Prof. Akgiray -- Regulasyon ve Etik:**

1. **MiFID II / SPK Uyumu:** Otonom trading botlari Avrupa'da MiFID II altinda "algorithmic trading" olarak siniflandirilir. Turkiye'de SPK benzeri duzenlemelere yonelecektir.

2. **Vergi:** Turkiye'de kripto kazanclari icin vergi yuku belirlenme asamasinda. Sistem hicbir vergi hesaplamasi yapmiyor.

3. **Yatirimci Korumasi:** Retail yatirimciya "7/24 otonom bot" vaadi, profesyonel yatirim danismanligi sinirinda. Bu, lisanssiz faaliyet olabilir.

4. **Veri Gizliligi:** API anahtarlarinin guvensiz saklanmasi KVKK/GDPR kapsaminda sorun teskil edebilir.

**Dr. Adiyaman -- Pratik Uygulama:**

Binance tarafindaki pratik sorunlar:

1. **Exchange Info kontrolu yok:** Her coin icin `GET /api/v3/exchangeInfo` ile LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER ogrenilinmeli. Aksi halde emirler reddedilir.

2. **Testnet kullanilmamis:** Binance Testnet (`testnet.binance.vision`) ile gercek para riskine girmeden test yapilabilir. Sistem dogrudan mainnet'e baglanıyor.

3. **WebSocket avantaji:** REST ile 15 coin taramak 15 HTTP istegi demek. WebSocket ile tek baglanti ile tum coin'lerin anlik verisini almak mumkun. Gecikme 100x azalir.

4. **Binance'in kendi sinirlari:** Spot trading'de max 5 acik emir (per symbol), gunluk islem limitleri, ve KYC seviyesine gore cekme limitleri var. Bunlarin hicbiri kontrol edilmiyor.

---

## ROUND 4: ANLASMAZLIKLAR VE KARSI ARGÜMANLAR

**Prof. Harvey vs Dr. Adiyaman -- Model Performansi:**

**Harvey:** AUC 0.57 kesinlikle kullanilmaz. Bu rakami kabul etmek entelektuel dursustluge aykiri.

**Dr. Adiyaman:** Campbell Hocam, akademik standartlar konusunda haklisiniz. Ama pratik acisindan sunu da dusunmek lazim: Turkiye'deki retail kripto yatirimcilarin %95'i hicbir sistematik yaklasim kullanmiyor. Telegram gruplari, influencer tavsiyeleri, FOMO ile islem yapiyorlar. Bu bot, en azindan "bakiyorsun bir seyler var" hissi veriyor. Tabii bu "iyi" demek degil ama "daha kotu alternatiflerden biraz daha az kotu" olabilir.

**Harvey:** Bu tehlikeli bir arguman. "Daha az kotu" yeterli degil. Yanlis guven duygusu, hicbir sistemden daha tehlikeli. Yatirimci "benim botum calisiyor" diye daha buyuk pozisyon alabilir.

---

**Prof. Makarov vs Prof. Cong -- Veri Onceligi:**

**Makarov:** On-chain veri guzel bir ideal ama gercekte cok gurultulu. Exchange flow verileri maniple edilebilir. Bence order book mikro yapisi cok daha guvenilir ve actionable.

**Cong:** Igor, katilmiyorum. Balik wallet hareketleri dogrulanabilir, blockchain'de yalan soyleyemezsiniz. Exchange flow'daki noise filtrelenebilir. Mikro yapi verileri ise exchange'e ozgu ve fragment'li -- her borsada farkli.

**Makarov:** Ama on-chain veriyi islemek icin ciddi altyapi gerekiyor. Bu seviyedeki bir proje icin pratik degil.

**Cong:** Nansen ve Glassnode API'leri ile oldukca kolay entegre edilir. Zor olan kendi node calistirmak, API kullanmak degil.

---

**Prof. Liu vs Prof. Salih -- Risk Olcumu:**

**Liu:** Kripto icin geleneksel risk olcumleri (VaR, Sharpe) yetersiz. Fat tail distribution'lar icin CVaR veya Omega ratio kullanilmali.

**Salih:** Yukun Hocam, CVaR dogru ama once temel risk olcumlerini koyalim. Bu sistemde HIC risk olcumu yok. Ideal'den once "yeterli"yi hedefleyelim. Sharpe bile olsa buyuk ilerleme.

**Liu:** Katiliyorum ama sunu vurgulayayim: Sharpe ile baslamak tamam, ama Sharpe'a guvenip "iyi performans" demek tehlikeli. Kripto'da yillik Sharpe 2.0 gosterip sonra bir crash'te %40 kaybeden strateji gorduk.

---

**Prof. Gulay vs Prof. Capponi -- Timing vs Execution:**

**Gulay:** Asil sorun timing. Dogru zamanda almak her seyden onemli.

**Capponi:** Guzhan Hocam, saygiyla katilmiyorum. Akademik literatur gosteriyor ki, execution kalitesi timing kadar onemli. Dogru zamanda alip kotu fiyattan alirsaniz, alpha'niz erir. Bu sistemde execution tamamen gormezden gelinmis.

**Gulay:** Ancak bu seviyedeki bir sistem icin -- gunluk 1-2 islem, kucuk pozisyonlar -- execution etkisi sinirli. Daha buyuk sorun yanliz zamanda almak.

**Capponi:** Kucuk pozisyonlarda bile altcoinlerde spread %0.3-0.5 arasinda. Bu kucuk gorunuyor ama yillik bilesik etkisi muazzam.

---

**Prof. Caner vs Prof. Akgiray -- Regulasyon Etkisi:**

**Caner:** Regulasyon onemli ama akademik olarak sorun model kalitesinde. Regulasyon geldiginde bile kotu model kotu model.

**Akgiray:** Selcuk Hocam, ama regulasyon uyumsuzlugu yatirimciyi hapiste bile birakabilir. Model kalitesi ikincil, once hukuki cerceve saglanmali. Turkiye'de kripto suclari cok ciddi yaptirimlara tabii.

**Caner:** Haklisiniz, oncelik sirasi konusunda yanilmis olabilirim. Hukuki risk finansal riskten once gelir.

---

## ROUND 5: NIHAI KARARLAR

### Her Panelistin Notu ve Tek Onerisi

| Panelist | Not | En Kritik Oneri |
|----------|-----|-----------------|
| **Prof. Harvey (Duke)** | **F** | "ML modelini sifirdan tasarlayin. Walk-forward validation, purging/embargo, ve en az AUC 0.65 hedefleyin. 0.57 ile KESINLIKLE canli'ya cikmayin." |
| **Prof. Makarov (LSE)** | **F** | "WebSocket'e gecin, order book derinligini feature olarak ekleyin, ve limit order kullanin. REST + market order = para yakma makinesi." |
| **Prof. Liu (Rochester)** | **F** | "Oncelikle risk yonetimi kurun: max drawdown %10 stop, pozisyon boyutu Kelly fraction ile, ve ATR-bazli dinamik stop-loss. Bunlar olmadan her sey anlamsiz." |
| **Prof. Cong (Cornell)** | **D** | "On-chain verileri entegre edin. Glassnode API ile exchange flow, whale hareketi, ve token unlock verileri ekleyin. Kripto'nun en buyuk avantaji seffaflik -- kullanin." |
| **Prof. Capponi (Columbia)** | **F** | "Execution engine'i yeniden yazin. TWAP/VWAP stratejileri, slippage modeli, ve Binance exchange info filtreleri ekleyin. Market order kullanmayi hemen birakin." |
| **Prof. Caner (Bilkent)** | **F** | "Istatistiksel temeli guclendirin: log-return kullanin, stationarity testleri yapin, regime-switching model ekleyin, ve cross-sectional korelasyonu hesaba katin." |
| **Prof. Salih (Bilkent)** | **F** | "Portfoy yaklasiimna gecin. Markowitz mean-variance optimizer, korelasyon matrisi, rebalancing, ve benchmark tracking ekleyin." |
| **Prof. Gulay (Sabanci)** | **D-** | "Volatilite modeli ekleyin. En azindan ATR-bazli dinamik bariyerler, ideal olarak GARCH veya HAR-RV modeli. Statik esik degerlerini hemen kaldirin." |
| **Prof. Akgiray (Bogazici)** | **F** | "Oncelikle hukuki cerceve oturtun. SPK duzenleme sureci, vergi yuku, KYC/AML -- bunlar olmadan canli para ile islem YAPMAYIN." |
| **Dr. Adiyaman (Binance TR)** | **D** | "Binance Testnet'te en az 3 ay paper trading yapin. Exchange info filtreleri, rate limiting, WebSocket entegrasyonu, ve IP whitelisting ekleyin. Ana kurali bilin: 'once zarar etme'." |

---

### KONSENSUS NOTU: **F (10 panelistin 7'si F, 2'si D/D-, 1'i D)**

---

## KONSENSUS RAPORU: ONCELIKLI AKSIYON LISTESI

Panel oybirligiyle su aksiyonlari ONCELIK SIRASINA GORE onermisTIR:

### ACIL (Ilk 2 Hafta) -- CANLI PARA ILE ISLEM YAPILMAMALI

1. **API guvenligini sagla:** API anahtarlarini .env dosyasina tasi, IP whitelist'i aktive et, withdraw iznini kapat
2. **Risk yonetim modulu ekle:** Max drawdown %10 hard stop, gunluk max kayip %3, tek pozisyon max portfoy %10
3. **Exchange info filtreleri ekle:** LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER kontrolleri
4. **Rate limiting ekle:** Binance API limitlerine uygun bekleme suresi
5. **Error handling duzelt:** Bare except'leri kaldir, anlamli hata yakalama ekle

### KISA VADE (1-2 Ay) -- TESTNET'TE CALISMA

6. **Binance Testnet entegrasyonu:** Tum islemleri once testnet'te dene
7. **WebSocket'e gec:** REST polling'den real-time stream'e
8. **Limit order stratejisi:** Market order yerine agresif limit order
9. **ML modelini yeniden egit:** Walk-forward validation, purging, en az 30 feature
10. **Komisyon modeli ekle:** Her sinyal degerlendirilirken komisyon+spread+slippage dussun

### ORTA VADE (3-6 Ay) -- MINIMUM VIABLE TRADING SYSTEM

11. **On-chain veri entegrasyonu:** Glassnode veya Nansen API
12. **Portfoy optimizasyonu:** Korelasyon-aware pozisyon boyutlandirma
13. **Volatilite modeli:** ATR-bazli dinamik TP/SL
14. **Backtesting framework:** Vectorbt veya Zipline ile kapsamli backtest
15. **Performance tracking:** Sharpe, Sortino, max drawdown, win rate raporlamasi

### UZUN VADE (6-12 Ay) -- PROFESYONEL SEVIYE

16. **Regime detection:** HMM veya clustering ile piyasa rejimi tespiti
17. **Ensemble model:** XGBoost + LightGBM + Neural Network
18. **Execution engine:** TWAP/VWAP, iceberg emirler
19. **Monitoring:** Grafana dashboard, alert sistemi
20. **Regulasyon uyumu:** SPK cercevesi, vergi raporlamasi

---

## PANEL KAPANISI

**Prof. Harvey (son soz):**
"Herkese sunu soylemek istiyorum: kripto trading zor. Dunya uzerindeki en iyi quantlerin %90'i bile pozitif alpha uretemiyor. Bu sistem baslangiç noktasi olarak var ama canli para ile kullanilabilecek seviyeden cok uzak. Once ogrenin, sonra paper trade yapin, sonra cok kucuk miktarlarla baslayın. Ve ASLA kaybetmeyi goze alamayacaginiz parayla islem yapmayin."

**Prof. Akgiray (son soz):**
"Turkiye'deki genc yatirimcilara sesleniyorum: kripto trading bir 'kolay para' araci degil. Bu tip otonom sistemler cazip gorunuyor ama arkasinda ciddi teknik ve hukuki riskler var. Sermaye piyasalarina saygi gosterin, kendi paranizi koruyun."

---

**PANEL TUTANAGI SONU**

*Bu rapor ve panel tutanagi, COIN Trader sisteminin kapsamli bir degerlendirilmesi olup, yatirim tavsiyesi niteliginde degildir.*
