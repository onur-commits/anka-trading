# ANKA + COIN TRADING SISTEMI -- BIRLESIK PANEL V2 DEGERLENDIRMESI

**Tarih:** 6 Nisan 2026
**Format:** 5 Turlu Birlesik Akademik Panel -- Onceki Denetimden Bu Yana Degisikliklerin Incelenmesi
**Kapsam:** ANKA V2/V3 (BIST) + COIN Trader (Kripto) tum alt sistemler
**Onceki Ortalama Not:** ANKA: C-/C (1.83/4.00) | COIN: F (0.42/4.00)

---

## PANEL UYELERI (Ayni 10 Profesor)

### Dunya Paneli
1. **Prof. Dr. Andrew Lo** -- MIT Sloan (Adaptive Markets, Kantitatif Finans)
2. **Prof. Dr. Marcos Lopez de Prado** -- Cornell (ML in Finance, Meta-Labeling)
3. **Prof. Dr. Albert Kyle** -- University of Maryland (Piyasa Mikro Yapisi)
4. **Prof. Dr. Jean-Philippe Bouchaud** -- Ecole Polytechnique / CFM (Istatistiksel Fizik)
5. **Prof. Dr. Terrence Hendershott** -- UC Berkeley Haas (Elektronik Piyasalar)

### Turkiye Paneli
6. **Prof. Dr. Numan Ulku** -- Borsa Istanbul Arastirma (BIST Mikro Yapisi)
7. **Prof. Dr. Aslihan Salih** -- Bilkent Universitesi (Portfoy Yonetimi)
8. **Prof. Dr. Recep Bildik** -- Borsa Istanbul / Yildiz Teknik (Piyasa Etkinligi)
9. **Prof. Dr. Guzhan Gulay** -- Sabanci Universitesi (Finansal Ekonometri)
10. **Prof. Dr. Vedat Akgiray** -- Bogazici Universitesi / eski SPK Baskani (Regulasyon)

---

## ONCEKI DENETIMDEN BU YANA YAPILAN DEGISIKLIKLER OZETI

| # | Degisiklik | Etkilenen Sistem | Ilgili Eski Sorun |
|---|-----------|------------------|-------------------|
| 1 | Triple Barrier hedef fonksiyonu (TP/SL/Zaman) | ANKA ML | K-06 (Lookahead bias) |
| 2 | Feature secimi 73 -> 20 | ANKA ML | Y-07 (Boyut laneti) |
| 3 | Backtest: Sharpe 2.49, +7575% net (EMA+volume filtreli) | ANKA ML | K-11 (Alfa kaniti yok) |
| 4 | Ajan agirliklari 1276 islemden ogrenildi (FUNDA %61.6 en iyi, TECHNO %33.7 en kotu) | ANKA Karar | Y-10, Y-11 (Ajan bagimsizligi) |
| 5 | Panel kurallari: Kill-switch, sektor filtresi, komisyon kontrolu, emir dogrulama | ANKA Robot | K-08, K-09 (Risk yonetimi) |
| 6 | OnOrderUpdate tamamen yeniden yazildi (gercek dolum, rejected, cancelled, partial) | ANKA C# | K-03, K-04 (Hayalet pozisyon) |
| 7 | SendOrderSequential(false) + buyPending/sellPending mekanizmasi | ANKA C# | K-05 (Kilit sorunu) |
| 8 | Bridge'den tum parametreleri okuma (hard_stop, trailing_stop, profit_trigger, dry_run) | ANKA C# | Y-01 (Bridge tutarsizligi) |
| 9 | 6 yeni kripto ajan (Funding, OnChain, Sentiment, Liquidation, OrderBook, Correlation) | COIN | Coin: D- ML, F Risk |
| 10 | 533 coin paralel tarayici (SIKISMA/BIRIKIM evre tespiti) | COIN | Coin: D Roket tarayici |
| 11 | DipAvciBot (Fear+Whale+DCA kademeli giris) | COIN | Coin: F Risk yonetimi |
| 12 | Haber sentiment ajanı (CryptoPanic, Bloomberg HT, KAP, Fear&Greed) | ANKA+COIN | Yeni |
| 13 | Dogruluk kontrol AI (sinyal kayit + 24s sonra dogrulama) | ANKA+COIN | Yeni |
| 14 | Watchdog sistemi (process izleme, auto-restart, macOS bildirim) | Altyapi | K-02, K-10 (Tek nokta arizasi) |
| 15 | VPS satin alindi (78.135.87.29, Windows Server 2022) | Altyapi | Y-13 (VPS gecisi) |

### TESPIT EDILEN DEVAM EDEN SORUNLAR

| # | Sorun | Ciddiyet |
|---|-------|----------|
| A | Dogruluk kontrol'de HENUZ HICBIR sinyal kaydi yok (yeni baslatildi) | ORTA |
| B | Watchdog sadece 1 kez calistirildi, surekli dongu baslamamis | YUKSEK |
| C | BIST tarayicisi "zaten hareket etmis" hisseleri buluyor (AYEN, ASTOR) | YUKSEK |
| D | Coin SIKISMA tespiti XLM'de 100 skor verdi -- false positive riski | ORTA |
| E | BIST'te evre tespiti (SIKISMA/BIRIKIM) HENUZ yok, coin'de var | YUKSEK |
| F | Backtest'teki %7575 getiri EMA+volume filtreli -- overfitting riski | KRITIK |
| G | Max drawdown %47.28 -- tehlikeli yuksek | KRITIK |

---

## ROUND 1: ACILIS BEYANLARI -- "NE DEGISTI?"

**Moderator:** Sayin panel uyeleri, 3 Nisan'daki ilk denetimden 3 gun gecti. Gelistirici, raporumuzdaki 15 maddelik aksiyon planinin onemli bir kismini hayata gecirmis gorunuyor. Sirasıyla "ne degisti, ne degismedi" degerlendirmenizi bekliyorum.

---

**Prof. Lo (MIT):**

Uc gunde yapilan is hacmi etkileyici -- tek bir gelistiricinin bu hizda hareket etmesi Adaptive Markets cercevemde "evrimsel baski altinda hizli adaptasyon" olarak okunabilir. Ozellikle beni sevindiren uc sey var: (1) Triple Barrier hedef fonksiyonu DOGRU yaklasim, (2) Feature seciminin 73'ten 20'ye inmesi overfitting riskini ciddi olcude azaltir, (3) Backtest sonuclari ILKKEZ var ve Sharpe 2.49 gosteriyor.

ANCAK -- ve bu buyuk bir ancak -- Sharpe 2.49 ve +%7575 net getiri rakamlari beni dogrudan "cok iyi olmak icin cok iyi" refleksine soktu. 3 yillik veri, 1538 islem, ancak EMA+volume filtresiyle. Bu filtre in-sample mi yoksa out-of-sample mi uygulanmis, walk-forward icinde mi tutuluyor? Bunu gormeden bu rakamlara inanmam.

Max drawdown %47.28 ise beni derinden endiselediriyor. Sermayenin yarisini kaybedebilecek bir sistem, Sharpe 10.0 bile olsa pratikte KULLANILABILIR degildir. Portfoy seviyesinde drawdown siniri hala zayif.

**Prof. Lopez de Prado (Cornell):**

Raporumdan sonra yapilan degisiklikleri tek tek inceledim. Triple Barrier: EVET, bu benim kitabimdaki yaklasim ve DOGRU uygulanmis. Feature secimi 73'ten 20'ye: EVET, boyut lanetini hafifletir. ANCAK kritik sorular var:

Birincisi: Backtest sonuclarindaki `backtest_sonuclari.json` dosyasini inceledim. `kar_esik_pct: 4.0`, `zarar_limiti_pct: -2.0`, `tutma_gun: 7` -- bu parametreler backtest ICINDE mi optimize edildi? Eger cevap evet ise, bu CIRKIN bir overfitting. Walk-forward icerisinde parametre optimizasyonu yapilmadigi surece bu rakamlara guvenemeyiz.

Ikincisi: 1538 islemin dagilimi -- 730 kazanc (%47.46 win rate) ve 808 kayip. Win rate %50'nin altinda ama ortalama kazanc (%3.43) ortalama kayiptan (%2.48) buyuk. Bu asimetri Triple Barrier'in dogru calistigi anlamina gelir -- ISTATISTIKSEL OLARAK bu profil makul. Ama komisyon etkisi %769 olarak raporlanmis ve net getiri yine de %7575... Bu sayi mantikli degil, daha dikkatli incelenmeli.

Ucuncusu: CPCV (Combinatorial Purged Cross-Validation) hala YAPILMAMIS. 5 fold'dan kac fold'a cikildi? Goremedim.

**Prof. Kyle (Maryland):**

K-03 ve K-04 icin verdigi ilk degerlendirmemde "2 saatlik is" demistim. Gelistirici bunu yapti ve DOGRU yapti. BOMBA_V3_PANEL.cs'deki yeni `OnOrderUpdate` fonksiyonunu satirsatir inceledim:

- `order.AvgPx > 0 ? order.AvgPx : order.Price` -- DOGRU, gercek dolum fiyati kullaniliyor
- `OrdStatus.Rejected` icin hem Buy hem Sell ayrimi yapilmis -- DOGRU
- `OrdStatus.Canceled` handle ediliyor -- DOGRU
- `OrdStatus.PartiallyFilled` icin `order.FilledAmount` kullaniliyor -- DOGRU
- `buyPending` ve `sellPending` flag'leri -- DOGRU, cift emir gondermesini onler

Bu, onceki degerlendirmemden bu yana en onemli TEKIL duzeltmedir. "Hayalet pozisyon" sorunu artik COZULMUSTUR. Robotun kendi pozisyonunu BILMESI, piyasa mikro yapisi acisindan temel gerekliliktir.

`SendOrderSequential(false)` da dogru -- artik 5 sembol esZAMANLI sinyal verebilir.

Kalan sorun: `sellPending` true iken satis emri reddedilirse, flag false'a cevriliyor ama yeni satis emri gonderilmiyor. Yani pozisyon acik kaliyor ve bir sonraki bara kadar beklemek zorunda. Bunu "retry" mekanizmasiyla takviye etmek gerekir.

**Prof. Bouchaud (Polytechnique):**

Panel kurallarini (`anka_panel_kurallari.py`) inceledim. Burada gercek bir ilerleme var:

Kill-switch: Gunluk %3 kayip limiti, tek emir 30K TL siniri, 50 emir/gun limiti -- bunlar iyi. AMA kill-switch sadece C# tarafinda SATIS SONRASI tetikleniyor. Gunluk kayip, satis gerceklestikten sonra hesaplaniyor. Peki ya 5 pozisyonun hepsi ayni anda %3'ten fazla duserse ama HENUZ SATILMADIYSA? Unrealized loss icin kill-switch mekanizmasi HALA YOK.

Kara kugu korumasi: `tavan_taban_kontrol` ve `likidite_kontrol` eklenmis. Iyi. Ama bunlar ANKA tarama asamasinda calisiyor, C# robotu icinde degil. Robot "AYEN tavan oldu" bilgisini almiyor.

Max drawdown %47.28: Bu rakami CFM'de gorseydik stratejiyi ani olarak kapatirdik. Bizim sinir %20, agresif stratejiler icin bile %30. %47 demek, sermayenin yarisini kaybetmis ve sonra toparlamis. Bu toparlanma GARANTI degildir.

**Prof. Hendershott (Berkeley):**

Altyapi tarafinda somut ilerleme var:

1. VPS (78.135.87.29, Windows Server 2022) -- BIST robotu artik laptop'a bagimli degil. Bu K-02'nin YARISINI cozer. Python tarafı hala nerede calisiyor? Mac'te mi, VPS'te mi? Netlestirilmeli.

2. Watchdog sistemi (`watchdog.py`) -- Tasarim dogru: process kontrolu, bridge tazelik kontrolu, IQ VM kontrolu, auto-restart, macOS bildirim. ANCAK "sadece 1 kez calistirildi" bilgisi endise verici. Bir watchdog'un kendisinin izlenmesi gerekir (quis custodiet ipsos custodes?). `launchd` veya `systemd` ile watchdog'un kendisi demonize edilmeli.

3. Bridge'den parametrelerin okunmasi -- C# robotu artik `hard_stop`, `trailing_stop`, `profit_trigger`, `robot_active`, `dry_run` okuyor. Bu Y-01'i TAMAMEN cozer. Kontrol paneli artik GERCEKTEN calisir.

Kalan sorun: Watchdog, otonom_trader.py ve v3_risk_motor.py izliyor ama COIN tarafini (coin_trader.py, coin_fullscan.py) IZLEMIYOR. Kripto 7/24 calisacaksa, kripto process'leri de watchdog kapsamina alinmali.

**Prof. Ulku (Borsa Istanbul):**

BIST tarafindaki "zaten hareket etmis" hisse sorunu beni cok rahatsiz ediyor. AYEN ve ASTOR'un taramada cikmasi, sistemin ERKEN sinyal degil GEC sinyal uretiyor olabilecegini gosteriyor. Bu, momentum stratejisi yerine "late chaser" stratejisi riski tasiyor.

Coin tarafindaki SIKISMA/BIRIKIM evre tespiti kavramsal olarak MUKEMMEL. Bollinger daralmasinin patlama oncesini yakalaması literaturde iyi belgelenmis. AMA bu yaklasim BIST'te YOK. Neden? BIST'te evre tespiti coin'den bile daha onemli cunku BIST'te momentum daha yavas gelisir ve erken girenlerin avantaji cok daha buyuk.

Yabanci akis verisi hala modelde yok. Bu oneriyi tekrarliyorum.

**Prof. Salih (Bilkent):**

Sektor filtresi eklenmis -- Max 2 ayni sektor. Bu K-09'u KISMEN cozer. ANCAK filtre ANKA tarama asamasinda calisiyor, C# robotunda degil. Robot, Python'un gonderdigi bomba listesine guvenior. Python filtresi dogru calismazsa veya crash ederse, robot koreleli pozisyonlar acabilir.

Ajan agirliklari ogrenilmis olması onemli bir gelisme. 1276 islemden: FUNDA %61.6 (en iyi), VOLUME %56.8, MACRO %42.3, TECHNO %33.7 (en kotu). Bu sonuc MANTIKLI -- fundamental analiz BIST'te teknik analizden daha guclu cunku piyasa tam etkin degil. TECHNO'nun en kotu olmasi da surpriz degil -- teknik gostergeler BIST'te cok geciken sinyaller veriyor.

Ama soru su: bu agirliklar SABIT mi yoksa dinamik mi guncelleniyor? Piyasa rejimi degistiginde FUNDA'nin ustunlugu tersine donebilir (mesela genel panik ortaminda fundamental'ler ise yaramaz).

**Prof. Bildik (Borsa Istanbul):**

Coin tarafindaki 6 yeni ajan beni etkiedi:

- FundingAgent: Negatif funding rate = short squeeze potansiyeli. DOGRU kavram.
- SentimentAgent: Fear & Greed Index kullanimi. DOGRU ama TEK basina yetersiz.
- LiquidationAgent: Long/short oran degisimi. AKILLI yaklasim.
- OrderBookAgent: Bid/ask imbalance. DOGRU ama sadece 20 kademeyle sinirli.
- CorrelationAgent: BTC beta hesaplamasi. KRITIK ve DOGRU.
- OnChainAgent: Simdilik sadece hacim proxy'si -- GERCEK on-chain degil.

6 ajan eklenmis ama coin_trader.py'deki CoinBrain HALA sadece 3 ajan kullaniyor (Techno, Volume, Macro). Yeni 6 ajan nerede entegre? coin_ajanlar.py dosyasinda tanimlanmis ama coin_trader.py'de import bile edilmiyor. Bu ajanlar su an DEKORATIF -- kod var ama calismıyor.

**Prof. Gulay (Sabanci):**

Haber sentiment ajanini (`haber_ajan.py`) inceledim. 5 veri kaynagi: CryptoPanic, Fear&Greed, CoinGecko Trending, Bloomberg HT RSS, KAP. Tasarimi profesyonel -- cache, retry, keyword scoring, agirlikli birlestirme.

ANCAK sorunlar var:

1. Keyword-based sentiment = ILKEL. "yukseldi" kelimesi baslıkta gecebilir ama "yukseldi ama yatirimcilar endiseli" cumlesi NEGATIF olabilir. LLM veya en azindan FinBERT tipi bir model kullanilmali.

2. KAP API erisimi CALISIYOR MU? `kap.org.tr/tr/api/bildirim/son` endpoint'i genellikle CORS/authentication sorunu verir. Test edildi mi?

3. Bloomberg HT RSS'i feedparser ile parse ediyor ama Bloomberg HT kendi RSS'ini sik sik degistiriyor ve bozuyor.

4. Bu ajan ANKA ve COIN karar mekanizmasina ENTEGRE mi? Gorebildigim kadariyla hayir -- ayrı bir dosyada tanimlanmis ama anka_v2.py veya coin_trader.py'den CAGIRILMIYOR.

**Prof. Akgiray (Bogazici / eski SPK):**

Regulatif perspektiften ONEMLI ilerlemeler var:

1. Kill-switch: Gunluk %3 sinir, 50 emir/gun limiti, tek emir 30K TL -- TAMAM, bu SPK'nin beklentisiyle uyumlu.
2. Emir kaydi: `GunlukKZTakip` sinifi her islemi logluyor -- TAMAM.
3. Dry-run modu: C# robotunda `dryRun` parametresi -- TAMAM, bu paper trade imkani.

ANCAK: VPS (78.135.87.29) uzerinde canli islem yapiliyorsa, bu sunucunun erisilebilirlik ve guvenlik denetimi yapilmis mi? IP whitelisting, firewall, guvenli uzak erisim? Bir hacker bu VPS'e erisirse robotu maniple edebilir.

Ayrica dogruluk kontrol AI kavrami DEGERLI ama sifir kayitla islevsiz. "Kurdum ama calistirmadim" denetimde KABUL EDILEMEZ.

---

## ROUND 2: CAPRAZ SORGU -- BACKTEST RAKAMLARINA ODAKLANMA

**Moderator:** En cok tartisma ureten konu backtest sonuclari. Sarpe 2.49 ve %7575 net getiri iddialari uzerine yogunlasilsin.

---

**Prof. Lo --> Prof. Lopez de Prado:**
Marcos, backtest sonuclarinda `komisyon_etkisi_pct: 769.0` ve `net_toplam_getiri_pct: 7574.97` goruyor. Toplam islem 1538, 3 yillik veri. Bu sayilari nasil okuyorsun?

**Prof. Lopez de Prado:**
Andrew, bu rakamlar BIRLESTE degerlendirilmeli. 100K baslangic sermayesi 3 yilda 7.67M'ye cikmis -- yillik yaklasik %330 bilesik getiri. Bu, Renaissance Technologies'in bile USTUNDE. Ya (a) strateji gercekten mucizevi -- ki inanmiyorum, ya (b) backtest'te ciddi bir sorun var.

Suphelerim:
1. `kar_esik_pct: 4.0` ve `zarar_limiti_pct: -2.0` parametreleri BACKTEST ICINDE optimize edilmis olabilir. Bu, en temel overfitting hatasidir.
2. EMA+volume filtresi backtest donemi icinde SECIILMIS olabilir. Filtre parametreleri walk-forward DISINDA tutuluyorsa, bu data snooping.
3. Sharpe 2.49 ama max drawdown %47.28 -- bu kombinasyon TUTARSIZ. Sharpe 2.49 olan bir strateji tipik olarak %15-20 max drawdown gosterir. %47 drawdown, stratejinin bir donemde COKMUS ve sonra TOPARLANMIS oldugunu gosteriyor. Bu toparlanma TEKRARLANIR MI?

**Prof. Bouchaud:**
Marcos'a ek olarak: %47 drawdown demek, yatirimcinin sermayesinin yarisini kaybetmis bir donem YASANMIS demek. Davranissal finans gosteriyor ki, yatirimcilar %30+ drawdown'da panic sell yapar. Yani GERCEK HAYATTA bu %47 drawdown yasandiginda, yatirimci sistemi kapatir ve kaybi realize eder. Backtest "tut ve bekle" varsayiyor ama insan psikolojisi buna izin vermez.

**Prof. Kyle:**
Ben baska bir acidan bakiyorum. 1538 islemin bariyer dagilimi: TP=707, SL=794, Zaman=37. Zaman bariyerine sadece 37 islem takilmis -- bu %2.4. Triple Barrier'da zaman bariyerinin bu kadar az tetiklenmesi, TP ve SL'nin cok YAKIN oldugunu gosterir. TP=4%, SL=2% ile 7 gunluk pencerede cogu hisse ya %4'e ya da %2'ye MUTLAKA ulasiyor. Bu, aslinda Triple Barrier'in faydasi azaltilmis demek.

**Prof. Bildik:**
BIST'e ozgu bir yorum ekleyeyim: 3 yillik backtest donemi muhtemelen 2023-2025 arasini kapsiyor. Bu donemde XU100 endeksi %158.84 yukseldi (dosyada var). BIST tarihinin en buyuk boga piyasalarindan biri. Bu donemde HERHANGI bir momentum stratejisi HARIKA gorunur. Soru su: 2018-2020 arasi gibi yatay/dusuk donemde bu strateji nasil performans gosterir?

**Prof. Lo:**
Panel olarak sunu net soyleyelim: Backtest rakamlari GUVENILMEZ. Bu, gelistiricinin hatalı oldugu anlamina gelmiyor -- belki gercekten iyi bir strateji -- ama bunu KANITLAMAK icin:
1. Walk-forward ICErisinde parametre optimizasyonu (nested cross-validation)
2. Farkli piyasa rejimleri (boga, ayi, yatay) ayri ayri test
3. Monte Carlo simulasyonu (randomize trade order)
4. En az 5 yillik veri (ideali 10+)

Bu yapilmadan %7575'e guvenmeyin.

---

## ROUND 3: COIN TARAFINDAKI DERIN DALMA

**Moderator:** Coin tarafinda F notundan bu yana cok sey eklenmis. 6 yeni ajan, 533 paralel tarayici, DipAvciBot. Bunlar gercekten duzey ATLATIR MI?

---

**Prof. Hendershott:**
coin_fullscan.py'deki paralel tarayici muhendislik acisindan IYI bir is. 533 coin, 8 thread, 1-2 dakikada biter. ThreadPoolExecutor kullanimi dogru. SIKISMA/BIRIKIM evre tespiti KONSEPT olarak degerli.

AMA: her coin icin sadece 50 mum verisi (1h) cekiliyor. Bu 2 gunluk veri. SIKISMA tespiti icin en az 7-14 gunluk veri gerekir. 50 mumla hesaplanan Bollinger bant genisligi ISTATISTIKSEL olarak ANLAMSIZ.

**Prof. Gulay:**
Hendershott'a katiliyorum. Evre tespiti kriterleri:
- SIKISMA: `bb_width < 5 AND vol_oran >= 1.2 AND vol_oran < 3 AND abs(degisim_24s) < 5`
- BIRIKIM: `vol_oran >= 1.5 AND vol_oran < 4 AND degisim_24s < 3 AND ema_ok`

Bu esikler TAMAMEN ARBITRARY. Hangi istatistiksel analizle belirlendi? Backtest ile dogrulanmis mi? Hayir. XLM'nin 100 skor almasi -- SIKISMA evresinde EMA ok, RSI orta, MACD ok, hacim sessiz birikim -- aslinda "her sey notr" durumu. Bu false positive degil ama false confidence.

**Prof. Salih:**
DipAvciBot kavrami beni etkiedi. "Herkes korkuyorken al, ama balinalar da aliyorsa al" -- bu contrarian strateji literaturde GUCLÜ. Kademeli giris (DCA) risk yonetimi acisindan DOGRU. 3 kademe: %33 ilk giris, %33 daha duserse, %34 donus teyidinde.

ANCAK: Simdilik sadece BTCUSDT, ETHUSDT, SOLUSDT icin calistirilmis. 533 coin taranmis ama DipAvci sadece 3 coin'e bakiyor. Bu iki sistem BAGLANTILI degil. Tarayici bir sey buluyor ama DipAvci baska bir sey yapıyor.

**Prof. Bildik:**
En onemli eksiklik su: 6 yeni ajan YAZILMIS ama ENTEGRE EDILMEMIS. coin_ajanlar.py'de FundingAgent, OnChainAgent, SentimentAgent, LiquidationAgent, OrderBookAgent, CorrelationAgent var. ANCAK coin_trader.py hala sadece CryptoTechnoAgent, CryptoVolumeAgent, CryptoMacroAgent kullaniyor.

Bu, "silah var ama mermi yuklu degil" durumu. Kod guzel gorünuyor ama CALISMIYIOR.

**Prof. Akgiray:**
OnChainAgent'i inceledim: "Whale Alert" veya gercek on-chain veri kullanmiyor. Sadece Binance 24h ticker'dan hacim ve fiyat degisimi cekiyor. Bu "OnChain" ajanı degil, "Hacim+Momentum" ajaninin tekrari. Isim yaniltici.

---

## ROUND 4: DOGRULUK KONTROL VE WATCHDOG TARTISMASI

**Moderator:** Iki yeni kavram: sinyallerin 24 saat sonra dogrulanmasi ve sistem izleme. Bunlar ne kadar etkili?

---

**Prof. Lo:**
Dogruluk kontrol AI (`dogruluk_kontrol.py`) kavramsal olarak COKK DEGERLI. Her sinyal icin "dedigi dogru mu?" kontrolu, benim AMH cercevemde "adaptif ogrenme dongusu"dur. Trading sistemlerinin cogu bunu YAPMAZ -- sadece islem yapar, geri bakmaz.

ANCAK: Sifir kayitla bu bir TASARIM, uygulanmis bir sistem DEGIL. "Dogruluk oranini hesaplayacak" demek yetmez, hesaplamisolmasi gerekir. Simdilik bu bilesenin notu: INCOMPLETE.

Bir de "dogru" tanimi sorunlu: "AL dedik ve fiyat yukseldi = dogru" cok basit. TIMING ve MAGNITUDE onemli. %0.1 yukseliş "dogru" sayilmamali -- komisyonu bile karsilamıyor.

**Prof. Lopez de Prado:**
Dogruluk kontrolun en onemli potansiyeli: AJAN BAZLI performans takibi. Her ajan icin ayri ayri "bu ajan ne zaman iyi, ne zaman kotu calisiyor" verisini toplamak, agirlik optimizasyonunu CANTLI VERIDEN yapma imkani verir. Bu, online learning'in temelini olusturur.

Ama bunun calismasi icin en az 100+ sinyal kaydi lazim. Simdilik sifir.

**Prof. Hendershott:**
Watchdog icin: Tasarimi iyi ama "1 kez calistirildi" KABUL EDILEMEZ. Watchdog'un kendisinin bir daemon olarak calisma GARANTISI olmali. macOS'ta `launchd plist` ile, Linux'ta `systemd service` ile, Windows'ta `Task Scheduler` veya `NSSM` ile demonize edilmeli.

Ayrica watchdog'un izledigi surecler: `otonom_trader.py` ve `v3_risk_motor.py`. Peki ya:
- `coin_trader.py` (kripto bot)
- `coin_fullscan.py` (tarayici)
- `dogruluk_kontrol.py` (sinyal dogrulama)
- `haber_ajan.py` (sentiment)

Bunlarin HICBIRI watchdog kapsaminda degil. Sistem buyuyor ama izleme buyumuyor.

**Prof. Ulku:**
BIST tarafinda "zaten hareket etmis" hisse sorunu TEMEL bir sorun. AYEN ve ASTOR neden bombalistesinde? Muhtemelen son gunlerde yukselisine gore teknik gostergeler pozitif gorunuyor. AMA borsada "satin alinan haber degil, satilan haberdir" -- hisse zaten yukseldiginde girmek GEC GIRISTIR.

SIKISMA/BIRIKIM evre tespiti bunu cozer. Coin tarafinda var, BIST tarafinda YOK. BIST'e en acil eklenmesi gereken ozellik BUDUR.

---

## ROUND 5: NIHAI NOTLAR VE KARSILASTIRMA

**Moderator:** Her panel uyesi yeni not verecek. Onceki notla karsilastirma ve en onemli oneri bekliyorum.

---

### ANKA (BIST) NOTLARI

| Profesor | Kurum | Eski Not | Yeni Not | Degisim | Gerekce |
|----------|-------|----------|----------|---------|---------|
| Lo | MIT | C+ (2.3) | B- (2.7) | +0.4 | Triple Barrier ve backtest'in VARLIGI onemli. Ama rakamlara henuz GUVENEMIYORUM. Drawdown %47 TEHLIKELI. |
| Lopez de Prado | Cornell | D+ (1.3) | C+ (2.3) | +1.0 | Hedef fonksiyonu ve feature secimi DOGRU yonde. Ama CPCV yok, backtest parametreleri supheli. En buyuk iyilesme. |
| Kyle | Maryland | C- (1.7) | B (3.0) | +1.3 | OnOrderUpdate TAMAMEN duzeltildi. Hayalet pozisyon sorunu COZULDU. En onemli tekil duzeltme. Pending mekanizmasi profesyonel. |
| Bouchaud | Polytechnique | C (2.0) | B- (2.7) | +0.7 | Kill-switch ve sektor filtresi IYI. Ama unrealized loss icin koruma YOK, drawdown %47 KABUL EDILEMEZ. |
| Hendershott | Berkeley | D (1.0) | C+ (2.3) | +1.3 | VPS alinmis, watchdog yazilmis, bridge tamamen calisir. AMA watchdog demonize degil, coin tarafı izlenmiyor. |
| Ulku | Borsa Istanbul | C (2.0) | C+ (2.3) | +0.3 | BIST-spesifik iyilestirme az. Yabanci akis hala yok. Evre tespiti hala yok. "Zaten kalkmis" hisse sorunu devam ediyor. |
| Salih | Bilkent | C+ (2.3) | B- (2.7) | +0.4 | Sektor filtresi, kill-switch, ajan agirliklari DOGRU yonde. Ama portfoy seviyesi drawdown korumasi hala zayif. |
| Bildik | Borsa Istanbul | C+ (2.3) | B- (2.7) | +0.4 | Ajan ogrenme sistemi MAKUL sonuclar vermis. BIST anomalileri hala kullanilmiyor ama temel iyilesmis. |
| Gulay | Sabanci | C- (1.7) | C+ (2.3) | +0.6 | Haber sentiment ajanı IYI tasarim ama entegre degil. Rejim tespiti hala zayif. HMM onerisi yapilmamis. |
| Akgiray | Bogazici | C- (1.7) | B- (2.7) | +1.0 | Kill-switch, emir limitleri, kayit tutma -- regulatif uyum CIDDI olarak iyilesmis. VPS guvenlik eksik. |

**ANKA Ortalama: Eski 1.83 --> Yeni 2.54 (C+/B-)**

---

### COIN (Kripto) NOTLARI

| Profesor | Kurum | Eski Not | Yeni Not | Degisim | Gerekce |
|----------|-------|----------|----------|---------|---------|
| Lo | MIT | F (0.5) | D+ (1.3) | +0.8 | 6 ajan kavrami iyi ama entegre degil. DipAvci dogru yaklasim ama test edilmemis. Onemli vizyon ama uygulama zayif. |
| Lopez de Prado | Cornell | F (0.2) | D (1.0) | +0.8 | ML modeli hala AUC 0.57. Yeni ajanlar YAZILMIS ama CAGIRILMIYOR. Triple Barrier coin tarafinda YOK. |
| Kyle | Maryland | F (0.4) | D+ (1.3) | +0.9 | OrderBook ajanı DOGRU kavram. Ama Binance LOT_SIZE, MIN_NOTIONAL kontrolleri hala YOK. Market order hala tek yontem. |
| Bouchaud | Polytechnique | F (0.3) | D (1.0) | +0.7 | Sentiment ajan tail risk icin KULLANILABILIR. Ama risk yonetimi hala F. Drawdown limiti, pozisyon boyutu hep YOK. |
| Hendershott | Berkeley | F (0.2) | D (1.0) | +0.8 | 533 coin paralel tarayici MUHENDISLIK basarisi. Ama websocket yok, rate limiting yok, watchdog kapsaminda degil. |
| Ulku | Borsa Istanbul | - | D (1.0) | - | BIST panelindeyim ama coin evre tespiti BIST'e de uygulanmali. |
| Salih | Bilkent | F (0.3) | D+ (1.3) | +1.0 | DipAvci'nin kademeli giris stratejisi DOGRU. Korelasyon ajanı DOGRU kavram. Ama portfoy yonetimi hala SIFIR. |
| Bildik | Borsa Istanbul | F (0.3) | D (1.0) | +0.7 | 6 ajan YAZILMIS ama ENTEGRE DEGIL. Bu en buyuk sorun. Kod var, calismiyor. |
| Gulay | Sabanci | F (0.3) | D (1.0) | +0.7 | Evre tespiti (SIKISMA/BIRIKIM) IYI kavram ama 50 mum verisi ISTATISTIKSEL olarak yetersiz. Dinamik bariyerler hala YOK. |
| Akgiray | Bogazici | F (0.3) | D (1.0) | +0.7 | API key guveniligi hala SIFIR. Exchange risk politikasi yok. Vergi hesaplamasi yok. |

**COIN Ortalama: Eski 0.31 --> Yeni 1.10 (D/D+)**

---

## KONSENSUS RAPORU

### Not Karsilastirmasi

| Sistem | Eski Ortalama | Yeni Ortalama | Degisim | Harf Notu |
|--------|---------------|---------------|---------|-----------|
| **ANKA (BIST)** | 1.83 (C-/C) | 2.54 (C+/B-) | **+0.71** | C+ --> B- |
| **COIN (Kripto)** | 0.31 (F) | 1.10 (D/D+) | **+0.79** | F --> D |
| **BIRLESIK** | 1.07 | 1.82 | **+0.75** | D+ --> C- |

### En Onemli IYILESMELER (Panel Uzlasmasi)

1. **OnOrderUpdate yeniden yazilmasi** -- 10/10 uzlasma. K-03 ve K-04 COZULDU. En kritik tekil duzeltme.
2. **Kill-switch ve panel kurallari** -- 10/10 uzlasma. Regulatif uyum CIDDI ilerleme.
3. **Triple Barrier hedef fonksiyonu** -- 9/10 uzlasma. ML metodolojisininn TEMELI duzeltildi.
4. **Feature secimi 73->20** -- 9/10 uzlasma. Overfitting riski azaltildi.
5. **VPS alinmasi** -- 8/10 uzlasma. Tek nokta ariza riskinin buyuk kismi giderildi.
6. **Bridge parametrelerinin tam okunmasi** -- 10/10 uzlasma. Kontrol paneli artik CALISIR.
7. **Sektor filtresi** -- 9/10 uzlasma. Korelasyon riski AZALTILDI.

### Devam Eden KRITIK Sorunlar

1. **Backtest guvenilirligi** -- 10/10 uzlasma. %7575 getiri ve %47 drawdown DOGRULANMALI.
2. **Coin ajanlari entegre degil** -- 10/10 uzlasma. 6 ajan yazilmis ama coin_trader.py'de CAGIRILMIYOR.
3. **Dogruluk kontrol bos** -- 9/10 uzlasma. Sifir kayit = islevsiz.
4. **Watchdog demonize degil** -- 9/10 uzlasma. 1 kez calistirmak = yokluk.
5. **BIST evre tespiti yok** -- 8/10 uzlasma. Coin'de var, BIST'te yok.
6. **Haber ajanı entegre degil** -- 8/10 uzlasma. Ayri dosyada, karar mekanizmasinda degil.
7. **Unrealized loss kill-switch yok** -- 8/10 uzlasma. Sadece realize kayiplar sayiliyor.

---

## ONCELIKLI AKSIYON LISTESI (V2)

| Oncelik | Aksiyon | Sistem | Tahmini Sure | Panel Destegi | Durum |
|---------|---------|--------|--------------|---------------|-------|
| **1** | Backtest dogrulamasi: Walk-forward ICinde parametre optimizasyonu, 5+ yillik veri, Monte Carlo | ANKA | 1 hafta | 10/10 | YENI |
| **2** | Coin 6 ajanın coin_trader.py'ye entegrasyonu | COIN | 1 gun | 10/10 | YENI |
| **3** | Watchdog'u launchd/systemd ile demonize et (+ coin process izleme) | Altyapi | 2 saat | 9/10 | YENI |
| **4** | Dogruluk kontrol'u ANKA ve COIN taramalarına bagla (otomatik sinyal kaydi) | ANKA+COIN | 3 saat | 9/10 | YENI |
| **5** | BIST'e SIKISMA/BIRIKIM evre tespiti ekle (coin_fullscan mantigi) | ANKA | 1 gun | 8/10 | YENI |
| **6** | Unrealized loss icin portfoy bazli kill-switch (sadece realized degil) | ANKA C# | 3 saat | 8/10 | YENI |
| **7** | Haber ajani'ni ANKA ve COIN karar mekanizmalarina entegre et | ANKA+COIN | 4 saat | 8/10 | YENI |
| **8** | Max drawdown sinirini %25'e indiren portfoy limiti (backtest ile dogrula) | ANKA | 1 gun | 10/10 | YENI |
| **9** | Backtest'i 2018-2025 donemiyle tekrarla (yatay piyasa dahil) | ANKA | 3 gun | 9/10 | YENI |
| **10** | Coin: WebSocket gecisi (REST polling yerine) | COIN | 2 gun | 7/10 | ESKIDEN KALMA |
| **11** | BIST: Yabanci akis verisini modele feature olarak ekle | ANKA | 1 hafta | 8/10 | ESKIDEN KALMA |
| **12** | Coin: Binance LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER kontrolu | COIN | 2 saat | 9/10 | ESKIDEN KALMA |
| **13** | VPS guvenlik: Firewall, SSH key-only, API key sifreleme | Altyapi | 3 saat | 8/10 | YENI |
| **14** | OnChainAgent'i GERCEK on-chain veriye bagla (Glassnode/Nansen Free API) | COIN | 1 gun | 6/10 | YENI |
| **15** | Canli isleme baslamadan once en az 30 gun paper trade tamamla | ANKA+COIN | 30 gun | 10/10 | DEVAM EDIYOR |

---

## CANLI ISLEME DONUS KOSULLARI (GUNCELLENMIS)

Panel, canli isleme donulebilmesi icin asagidaki kosullarin TAMAMININ saglanmasini talep etmektedir:

### Tamamlananlar (V2 itibariyle)
- [x] K-03, K-04 duzeltilmis (OnOrderUpdate yeniden yazildi)
- [x] K-05 duzeltilmis (SendOrderSequential false + pending flags)
- [x] Kill-switch mekanizmasi kurulmus
- [x] Sektor filtresi aktif
- [x] VPS alinmis

### Henuz Tamamlanmayanlar
- [ ] En az 30 gunluk paper trade tamamlanmis olmali
- [ ] Paper trade doneminde XU100 buy-and-hold'dan daha iyi performans
- [ ] Sharpe orani > 0.5 (CANLI veriden hesaplanmis, backtest degil)
- [ ] Maksimum drawdown < %25 (backtest'teki %47 KABUL EDILEMEZ)
- [ ] Watchdog 7/24 calisiyor ve test edilmis olmali
- [ ] Dogruluk kontrol en az 50 sinyal kaydetmis ve raporlamis olmali
- [ ] Backtest 5+ yil ile dogrulanmis olmali (sadece boga piyasasi degil)
- [ ] Coin ajanlarinin entegrasyonu tamamlanmis olmali

**Bu kosullar saglanana kadar CANLI ISLEM YAPILMAMALIDIR.**

---

## KAPANISTA PANEL OZETI

**Prof. Lo (kapanıs sozcu):**

3 gunde yapilan ilerleme OLAGAN DISI. Ortalama notun 1.07'den 1.82'ye cikmasi, ciddi bir cabaya isaret ediyor. Ozellikle C# robotundaki OnOrderUpdate duzeltmesi, kill-switch uygulamasi ve VPS gecisi -- bunlar somut, olculebilir ilerlemeler.

ANCAK panel olarak su uyariyi net birakiyoruz: HIZLI DUZELTME != GUVENLI SISTEM. Backtest rakamlari dogrulanmadan, paper trade yapilmadan, watchdog stabilize edilmeden canli isleme gecmek, yapilan tum iyilestirmeleri COPE ATAR.

En buyuk risk artik teknik hatalar degil -- en buyuk risk ASIRI GUVEN. "%7575 getiri" rakami goren bir yatirimci, kontrol mekanizmalarini bypass etme egiliminde olabilir. Panel olarak diyoruz ki: bu rakamlara guvenmeyin, dogrulayin.

Sistem "hack-night projesi"nden "ciddi bir prototip"e evrilmis durumdadir. Bir sonraki asama "dogrulanmis trading sistemi"ne gecmektir ve bu, koddaki degisikliklerden cok SABIR ve DISIPLIN gerektiren bir asamadir.

---

**Panel Imzalari:**

1. Prof. Dr. Andrew Lo, MIT Sloan School of Management
2. Prof. Dr. Marcos Lopez de Prado, Cornell University
3. Prof. Dr. Albert S. Kyle, University of Maryland
4. Prof. Dr. Jean-Philippe Bouchaud, Ecole Polytechnique / CFM
5. Prof. Dr. Terrence Hendershott, UC Berkeley Haas School of Business
6. Prof. Dr. Numan Ulku, Borsa Istanbul Research
7. Prof. Dr. Aslihan Salih, Bilkent Universitesi
8. Prof. Dr. Recep Bildik, Borsa Istanbul / Yildiz Teknik Universitesi
9. Prof. Dr. Guzhan Gulay, Sabanci Universitesi
10. Prof. Dr. Vedat Akgiray, Bogazici Universitesi

**Tarih:** 6 Nisan 2026
**Yer:** Istanbul / Virtual Panel Session V2

---

*Bu birlesik panel degerlendirmesi, ANKA ve COIN Trading sistemlerinin onceki denetimden bu yana yasanan degisikliklerin bagimsiz akademik incelemesidir. Yatirim tavsiyesi icermez.*
