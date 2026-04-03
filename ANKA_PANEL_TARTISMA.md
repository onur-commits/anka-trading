# ANKA Trading System -- Uluslararasi Akademik Panel Tartismasi

**Tarih:** 3 Nisan 2026
**Format:** 15 Dakikalik Derin Akademik Panel Tartismasi
**Konu:** ANKA Otonom Trading Sistemi Doktora Seviyesi Denetim Raporu Degerlendirmesi
**Moderator:** Bagimsiz Akademik Sekreterya

---

## PANEL UYELERI

### Dunya Paneli
1. **Prof. Dr. Andrew Lo** -- MIT Sloan (Adaptive Markets, Kantitatif Finans)
2. **Prof. Dr. Marcos Lopez de Prado** -- Cornell / eski AQR (ML in Finance, Meta-Labeling)
3. **Prof. Dr. Albert Kyle** -- University of Maryland (Piyasa Mikro Yapisi, Kyle's Lambda)
4. **Prof. Dr. Jean-Philippe Bouchaud** -- Ecole Polytechnique / CFM (Istatistiksel Fizik, Agir Kuyruk)
5. **Prof. Dr. Terrence Hendershott** -- UC Berkeley Haas (Elektronik Piyasalar, HFT)

### Turkiye Paneli
6. **Prof. Dr. Numan Ulku** -- Borsa Istanbul Arastirma (BIST Mikro Yapisi, Yabanci Akislar)
7. **Prof. Dr. Aslihan Salih** -- Bilkent Universitesi (Varlik Fiyatlama, Portfoy Yonetimi)
8. **Prof. Dr. Recep Bildik** -- Borsa Istanbul / Yildiz Teknik (Piyasa Etkinligi, BIST Anomalileri)
9. **Prof. Dr. Guzhan Gulay** -- Sabanci Universitesi (Finansal Ekonometri, Volatilite Modelleme)
10. **Prof. Dr. Vedat Akgiray** -- Bogazici Universitesi / eski SPK Baskani (Regulasyon, Sistemik Risk)

---

## ROUND 1: ACILIS BEYANLARI

**Moderator:** Sayin panel uyeleri, onunuzde ANKA Trading System'in kapsamli bir doktora seviyesi teknik denetim raporu ve literatur taramasi bulunmaktadir. Sirasiyla acilis beyanlarinizi rica ediyorum.

---

**Prof. Lo (MIT):** ANKA sistemi, Adaptive Markets Hypothesis cercevesinde degerlendirildiginde, perakende bir yatirimcinin kendi basina bu karmasiklikta bir sistem kurmus olmasi evrimsel bir uyum cabasi olarak takdire deger. Ancak raporun ortaya koydugu AUC 0.5982 rakami beni derinden endiselendiriyor. Kendi 2004 calismamdaki "survivor bias" uyarilari burada aynen gecerli -- bu sistemin alfa uretip uretmedigi en temel sorudur ve rapor bu soruya "hayir" cevabina yakin bir tablo cizmektedir.

**Prof. Lopez de Prado (Cornell):** Dogrudan soyleyecegim: bu rapordaki K-07 bulgusunu okuyan herhangi bir ciddi kantitatif arastirmaci, sistemi hemen kapatirdi. AUC 0.5982 demek, benim "Advances in Financial Machine Learning" kitabimda detayli olarak tarif ettigim "yalanci kesif" sorunuyla karsi karsiyayiz demektir. Hedef fonksiyonundaki lookahead bias (K-06) ise metodolojik olarak affedilemez. Walk-forward validasyonun 5 fold ile yapilmasi da yetersizdir -- en az combinatorial purged cross-validation ile 100+ yol test edilmeliydi.

**Prof. Kyle (Maryland):** Benim odak noktam K-03 ve K-04 numarali bulgular. Robot, `SendMarketOrder` gonderdikten hemen sonra pozisyonu "girilmis" sayiyor, dolum fiyatini bar kapanis fiyati olarak aliyor. Bu, piyasa mikro yapisi acisindan ciddi bir hata. Kyle's Lambda ile olculdugunde, bilgi asimetrisi goz ardi edilmis. Daha da onemlisi, rejected order yonetiminin olmamasi "hayalet pozisyon" sorununa yol aciyor ki bu, herhangi bir kurumsal sistemde kabul edilemez.

**Prof. Bouchaud (Polytechnique):** Ben fizikci gozuyle bakiyorum ve gordugum sey sudur: bu sistem normal dagilim varsayimini hicbir yerde sorgulamiyor. BIST gibi gelisen piyasalarda kuyruk riskleri cok daha agir. Kara kugu korumasi eksikligi (Y-08) beni ozellikle rahatsiz etti. CFM'de biz, herhangi bir stratejiyi canli piyasaya almadan once en az 10.000 Monte Carlo senaryosu kosturuyor ve kuyruk risklerini ayrica modelleyoruz. Burada boyle bir analiz sifir.

**Prof. Hendershott (Berkeley):** Kurumsal kalite standartlari acisindan baktigimda, bu sistem bir prototip bile sayilamaz. Dosya tabanli IPC (K-01), tek nokta arizasi (K-02), process monitoring yoklugu (Y-13) -- bunlar 2006'daki elektronik piyasalar calismamdaki en temel gereksinimlerdir. ANKA'nin mimarisi etkileyici bir niyet gosteriyor ama muhendislik olgunlugu alpha-asamasinda bile degil.

**Prof. Ulku (Borsa Istanbul):** Ben BIST'in ic dinamiklerini yakindan taniyan biri olarak soyluyorum: raporun BIST'e ozgu tespit ettigi sorunlar cok onemli. Yabanci yatirimci akislari BIST'te fiyat hareketlerinin %60-70'ini aciklar. ANKA'nin bu degiskeni hicbir sekilde modellememesinasasirtici buldum. Ayrica BIST'teki T+2 kuralinin goz ardi edilmesi (Y-04) pratikte ciddi sorunlara yol acar -- broker hesabi dondurabilir.

**Prof. Salih (Bilkent):** Portfoy yonetimi perspektifinden baktigimda, K-08 ve K-09 bulgulari alarm verici. Portfoy seviyesinde drawdown korumasi "var ama cagrilmiyor" -- bu, emniyet kemeri takilmis ama kilit mekanizmasi calismayan bir araba gibi. 5 hissenin hepsinin ayni sektordan secilme ihtimali ve korelasyon kontrolunun yalnizca kagit uzerinde olmasi, tek bir kotu gunde sermayenin %15'inden fazlasinin kaybedilmesi anlamina gelir.

**Prof. Bildik (Borsa Istanbul):** Ben BIST anomalileriyle ilgili kapsamli calismalari olan biri olarak sunu soyleyebilirim: BIST'te gercekten istismar edilebilir anomaliler vardir -- haftanin gunu etkisi, ay donumu etkisi, yabanci akis momentum etkisi gibi. Ancak ANKA bunlari sistematik olarak kullanmiyor. Bunun yerine genel teknik analiz ve zayif bir ML modeline dayanarak BIST'e ozgu avantajlari kaybediyor. Biraz paradoksal: en cok alfa potansiyeli olan piyasada en az BIST-spesifik optimizasyon yapilmis.

**Prof. Gulay (Sabanci):** Volatilite modelleme acisindan baktigimda, rejim tespiti kavrami dogru kurulmus (VIX proxy, XU100 degisim) ama uygulama zayif. 60 saniyede bir guncellenen bridge verisi uzerinden rejim degisikligini yakalamak, GARCH veya Markov switching modeli yerine son derece kaba bir yaklasim. Ozellikle 2022 ve 2024'teki BIST volatilite patlamalarinda bu sistem rejim degisikligini 5-10 dakika gecikmeyle algilar ki bu sureye birden fazla yanlis islem sigar.

**Prof. Akgiray (Bogazici / eski SPK):** Regulatorun gozunden baktigimda, bu sistem ciddi uyumluluk riskleri tasiyor. SPK'nin algoritmik islem duzenlemeleri cercevesinde, otomatik islem yapan sistemlerin belirli standartlari karsilamasi gerekir. Kill-switch mekanizmasinin yoklugu, emir kayitlarinin sistematik tutulmamalasi, ve manipulasyon tespitinin olmamasi ciddi idari yaptirim riskleri olusturur. Ben SPK baskaniyken bu tur sistemler icin ozel denetim prosedurlerimiz vardi.

---

## ROUND 2: CAPRAZ SORGU

**Moderator:** Simdi panel uyeleri birbirlerinin goruslerini sorgulayacak. Baslatiyorum.

---

**Prof. Lo:** Marcos, sana bir soru -- sen AUC 0.5982'yi dogrudan "kapat" olarak degerlendirdin. Ama benim Adaptive Markets cercevemde, dusuk AUC'ler bile belirli rejim donemlerinde gecici alfa uretebilir. BIST gibi daha az etkin bir piyasada bu esik daha dusuk olabilir mi?

**Prof. Lopez de Prado:** Andrew, saygimla karsi cikiyorum. Senin Adaptive Markets Hypothesis'ini takdir ediyorum ama burada temel bir istatistik sorunu var. AUC 0.5982'yi urettigi iddia edilen walk-forward validasyon sadece 5 fold kullaniyor. Benim CPCV (Combinatorial Purged Cross-Validation) yontemimle test edilseydi, muhtemelen AUC 0.55'in altina duser ve tamamen anlamsiz hale gelirdi. Rejim-spesifik alfa olabilir, evet -- ama bunu test etmek icin en az 20 yillik veri lazim, BIST'te bu veri kalitesi sorgulanir.

**Prof. Kyle:** Jean-Philippe, senin agir kuyruk riskleri vurgunu anliyorum ama sormak istiyorum: BIST'te 16.000-20.000 TL pozisyon buyuklugu icin piyasa etkisi gercekten onemli mi? Gunluk islem hacminin binde birinden az.

**Prof. Bouchaud:** Albert, haklisn -- bireysel pozisyon buyuklugu icin piyasa etkisi ihmal edilebilir. Ama benim kaygim baska: agir kuyruk riski piyasa etkisinden bagimsiz. Flash crash senaryosunda, hissenin %10 taban kilidi olmasi durumunda stop-loss calismiyor. Bu, pozisyon buyuklugu ne olursa olsun gecerli. CFM'de bizim Bouchaud-Farmer-Lillo modelimiz gosterir ki piyasa etkisi lineer degil, konkav fonksiyondur -- ama taban/tavan kilidi gibi durumlarda model tamamen kirilir.

**Prof. Hendershott:** Numan, sana sormak istiyorum -- BIST'te perakende yatirimcilarin algoritmik islem yapmasina iliskin pratikte nasil bir durum var? Regulasyon bunu engelliyor mu?

**Prof. Ulku:** Terrence, pratikte BIST'te perakende algoritmik islem grisi bir alan. SPK duzenlemeleri esas olarak kurumsal aktörleri hedefliyor. Matriks IQ gibi platformlar perakende yatirimcilara robot yazma imkani veriyor ve broker'lar bunu memnuniyetle kabul ediyor cunku komisyon uretiyorlar. Ama burada ciddi bir bilgi asimetrisi var: yabanci kurumsal yatirimcilar BIST'te dark pool erisimi, co-location avantaji ve Level-3 veri erisimi ile donatilmisken, ANKA gibi bir sistem Yahoo Finance'ten gecen gunku veriyle islem yapiyor. Bu adil bir oyun alani degil.

**Prof. Salih:** Recep Hocam, sen BIST anomalilerinden bahsettin. Sormak istiyorum: bu anomaliler ML ile yakalanabilir mi yoksa klasik faktor modelleriyle mi daha iyi istismar edilir?

**Prof. Bildik:** Aslihan Hoca, cok onemli bir nokta. Benim 2010 ve 2018 calismalari gosterdi ki BIST anomalileri buyuk olcude yapisal -- takas donemi etkileri, endeks yeniden dengeleme etkisi, temettü donem anomalileri. Bunlar ML'ye ihtiyac duymaz, basit kural tabanli stratejilerle yakalanabilir. ML modeli ise bu basit kurallarin ustune ek katman olarak kullanilabilir ama ANKA'da bu hiyerarsi yok -- her sey ML'ye bagli ve ML zayif.

**Prof. Gulay:** Vedat Hocam, regulasyon acisindan, ANKA gibi bir sistemin SPK'ya bildirim yukumlulugu var mi?

**Prof. Akgiray:** Guzhan Hoca, mevcut mevzuatta perakende yatirimcinin kendi hesabi icin yazilim kullanarak islem yapmasini dogrudan engelleyen bir madde yok. Ancak 6362 sayili Kanun'un 101. maddesi piyasa bozucu islemleri yasaklar. Eger ANKA'nin hatalari nedeniyle -- mesela rejected order'in fark edilmemesi ve ayni emrin tekrar tekrar gonderilmesi -- piyasada anormal islem kaliplari olusursa, SPK bunu sorusturabilir. Kill-switch yoklugu tam da boyle bir senaryoyu mumkun kiliyor.

**Prof. Lo:** Vedat Hocam'in soyledigi cok onemli bir noktaya dikkat cekmek istiyorum. ABD'de SEC'in Market Access Rule'u (Rule 15c3-5) tam olarak bunu duzenliyor. Her algoritmanin pre-trade risk kontrollerine sahip olmasi ZORUNLU. BIST'te boyle bir zorunluluk olmasa bile, best practice olarak olmali.

**Prof. Lopez de Prado:** Ben de Kyle'in K-03 bulgusuna donmek istiyorum. Albert, senin 1985 makalen bilgili islemcinin piyasaya etkisini modeller. ANKA burada "bilgili islemci" bile degil -- gercek dolum fiyatini bilMEyen bir islemci. Bu, senin modelindeki en temel varsayimin bile ihlali degil mi?

**Prof. Kyle:** Kesinlikle, Marcos. Benim 1985 modelimde market maker, bilgili islemcinin varligini bilir ve buna gore fiyati ayarlar. Ama ANKA'da islemcinin kendisi kendi pozisyonunu bilmiyor! Bu, bilgi asimetrisinin en absurt formudur -- kendinize karsi bilgi asimetrisi. `entryPrices[s] = close` satiri, robotun kendi giris fiyatini yanlis kaydetmesi demek. Bu durumda trailing stop, profit target -- her sey yanlis hesaplaniyor.

---

## ROUND 3: ANKA-SPESIFIK DERIN DALMA (11 KRITIK SORUN)

**Moderator:** Simdi rapora ozel 11 kritik sorunu siraSiyla tartisacagiz.

---

### K-01: Dosya Tabanli IPC Atomiklik Sorunu

**Prof. Hendershott:** Bu sorun, benim 2011 calismamdaki "system latency as a source of risk" tezinin en net ornegi. Iki isletim sistemi arasinda `File.ReadAllText()` ile veri paylasimi, 1990'larin mimarisidir. `try-catch` blogunun hatayiYutup varsayilan carpan kullanmasi ise sessiz bir felaket. Bir gun robot 3x kaldiracle islem yapabilir cunku bridge dosyasi yarim okundu ve multiplier parse edilemedi.

**Prof. Bouchaud:** Hendershott'in soyledigine ek olarak, bu deterministik bir hata degil -- stokastik. Bazen calisir, bazen calismaz. Bu tur "arasira olan" hatalarin tespiti en zordur cunku sistem cogu zaman dogru calisir gibi gorunur. Istatistiksel fizikteki "intermittent fault" kavramina benzer.

**Prof. Gulay:** Pratik bir cozum onerisi: bridge dosyasi yerine SQLite veya Redis gibi atomik okuma/yazma garantisi veren bir ara katman kullanilabilir. Bu, Python ve C# tarafindan es zamanli olarak guvenle erisilebiilir.

### K-03 ve K-04: Sahte Pozisyon Takibi ve Rejected Order

**Prof. Kyle:** Bu iki sorun birlestiginde ortaya cikan tablo sok edici. Robot bir alis emri gonderir, emir reddedilir, ama robot pozisyon girilmis zanneder. Sonra bu "hayalet pozisyon" icin stop-loss hesaplar, trailing stop hesaplar. Gercekte olmayan bir pozisyonu yonetiyor. Daha da kotusu, bir gun gercekten satis emri gonderdignde, olmayan bir pozisyonu satmaya calismis olacak.

**Prof. Lopez de Prado:** Albert'in soyledigine bir sey ekleyeyim -- bu, ML modelinin performansini da dogrudan bozar. Eger model sonuclari geri besleme icin kaydediliyorsa (ki anka_ogrenme.py bunu yapiyor), hayalet pozisyonlarin sonuclari da ogrenme verisine giriyor. Model, gercekte hic yapilmamis islemlerden "ogreniyor". Bu, veri zehirlenmesidir.

**Prof. Salih:** Portfoy acisindan da kritik. RiskYoneticisi sinifinda pozisyon sayisi kontrolu var ama robot gercek pozisyon durumunu bilmedigine gore, bu kontrol de calismaz. Portfoy 5 pozisyon sinirina ulastigini zannedebilir ama aslinda 3 gercek + 2 hayalet pozisyona sahiptir.

### K-05: SendOrderSequential Kilitleme

**Prof. Hendershott:** Multi-symbol stratejide sequential order gonderimi performans katilindir. Benim Berkeley'deki ogrencilerim bunu birinci sinifta ogrenir. 5 sembol ayni anda sinyal verdiginde, sadece birincisi zamaninda islem gorur. Kalan 4 sembol icin fiyat coktan degismis olabilir. Bu, "execution risk" in ders kitabindaki ornegi.

**Prof. Ulku:** BIST baglaminla konusursak, BIST'te acilis seansinda (09:40-10:00) cok sayida hisse ayni anda hareket eder. Sequential order gonderimi bu kritik pencereyi tamamen kacirir.

### K-06: Yahoo Finance Veri Guvenilirligi

**Prof. Bildik:** Bu beni en cok etkileyen sorunlardan biri. BIST verisi icin Yahoo Finance kullanmak, akademik arastirmada bile artik kabul edilmez. Bolunme duzeltmeleri, sermaye artirimlari, OTC islemler -- hepsi yanlis olabilir. Ben kendi arastirmalarimda Borsa Istanbul'un resmi veri kaynagini veya Matriks/Foreks gibi yerel saglayicilari kullaniyorum.

**Prof. Lo:** Recep Hocam'in soyledigine katiliyorum. MIT'te biz CRSP veritabani kullaniriz ve o bile zaman zaman hata iceriyor. Yahoo Finance, profesyonel islem icin veri kaynagi olamaz. Ancak burada bir nuana dikkat cekmek istiyorum: ML modeli Yahoo verisiyle egitiliyorsa ve canli islem de Yahoo verisiyle yapiliyorsa, tutarsizlik yoktur. Sorun, ML Yahoo ile egitilip canli islemin Matriks IQ verisiyle yapilmasi. Bu iki veri kaynaginin FARKLI fiyatlar gostermesi mumkun.

**Prof. Gulay:** Andrew Hoca'nin soyledigi cok onemli. Ekonometride buna "data source mismatch" denir ve ozellikle BIST gibi piyasalarda kapaniS fiyati taniminda bile farkliliklar olabilir -- surekli islem kapanisi mi, kapanisseansifiyati mi? Bu tutarsizlik ML modelini sessizce zehirler.

### K-07: AUC 0.5982

**Prof. Lopez de Prado:** Bu rapordaki en onemli bulgu budur. AUC 0.5982 demek, modelin 100 ornekten 60'inda dogru siralama yapmasi demek. Komisyon ve slippage sonrasi net beklenen getiri negatif. Benim "The 7 Reasons Most Machine Learning Funds Fail" makalemdeki 3. sebep tam olarak budur: zayif sinyallerle islem yapildiginda, islem maliyetleri alfayi sifirlar.

**Prof. Lo:** Marcos, sana katiliyorum ama bir kaydimla. BIST'te bilgi etkinligi ABD piyasalarindan dusuk. Benim 2004 AMH cercevemde, etkinlik zamana ve piyasaya gore degisir. BIST'te AUC 0.60 belki ABD'de AUC 0.65'e karsilik gelebilir -- ama yine de yetersiz.

**Prof. Bouchaud:** Ben farkli bir aciyla bakiyorum. AUC sadece ortalama performansi olcer. Kuyruk performansi tamamen farkli olabilir. Model, %90 dogru sinyal verip %10 felaket sinyal verebilir. Bu %10'luk kisim portfoyu yok edebilir. AUC bunu gostermez.

**Prof. Lopez de Prado:** Jean-Philippe, haklisn. O yuzden ben AUC'nun yaninda Precision-Recall curve, Brier score ve ozellikle "strategy return distribution" talep ediyorum. Bunlarin hicbiri raporda yok. Model performansinin tek bir metrikle degerlendirililmesi 2015 oncesi bir yaklasimdir.

### K-08 ve K-09: Portfoy Korumasi ve Korelasyon

**Prof. Salih:** Bu iki bulgu birlikte ele alinmali. `risk_yonetimi.py` dosyasinda Kelly kriteri, korelasyon filtresi, drawdown limiti -- hepsi guzelce kodlanmis. Ama C# robotu bunlari HICBIR ZAMAN OKMUYOR. Bu, teorik olarak mukemmel bir risk yonetimi cercevesinin pratikte sifir koruma saglamasi demek. Benim Bilkent'teki portfoy yonetimi dersimde bunu "implementation gap" olarak ogretirim.

**Prof. Akgiray:** Aslihan Hoca'nin soyledigi regulatif acisindan da gecerli. SPK denetimine girdiginde "risk yonetimimiz var" demek yetmez -- risk yonetiminin fiilen CALISTIGINI gostermek gerekir. Bu sistemde risk yonetimi bir masktir, fonksiyonel degil dekoratiftir.

**Prof. Ulku:** Korelasyon konusunda bir ornek vereyim: 2024'te BIST'te enerji sektoru toplu olarak dusus yasadi. AYEN, AKSEN, ENJSA -- hepsi ayni hafta icinde %8-12 dusus yasadi. ANKA'nin bomba taramasi bu uc hisseyi de secmis olabilir cunku hepsi benzer teknik goruntu verir. Sonuc: 3 x %3.5 stop = %10.5 tek gunde kayip. Korelasyon filtresi bunu engellerdi ama calismadigi icin engelleyemez.

### K-10 ve K-11: Operasyonel Risk ve Alfa Kaniti

**Prof. Hendershott:** K-10 benim icin en sasirtici bulgu. Mac laptop kapanirsa BUTUN SISTEM durur ve bunu KIMSE FARK ETMEZ. 2026'da bir trading sisteminin launchd bile kullanmamasi... Benim Berkeley'deki yuksek lisans ogrencileri bile AWS'de redundant deployment yapiyorlar.

**Prof. Lo:** K-11 ise tum tartismanin ozeti. Gercek alfa kanitlanmamis. Kapsamli geri test yok, benchmark karsilastirmasi yok, Sharpe orani hesaplanmamis. Bu, bir doktora tezinde "hipotez test edilmemis" demekle esdegerdir. Bilimsel yontem acisindan, alfanin varligini VARSAYARAK para yatirmak, hipotezi test etmeden sonucu kabul etmektir.

**Prof. Bildik:** Andrew Hoca'ya katiliyorum. BIST'te alfa vardir -- ama bu alfayi yakalamak icin BIST'e ozgu faktorler gerekir. ANKA genel bir ML yaklasimiyla gelirken, BIST'in kendine ozgu dinamiklerini -- mesela TCMB faiz kararlari sonrasi momentum, yabanci net alis verileri, VIOP pozisyon degisiklikleri -- kullanmiyor.

---

## ROUND 4: ANLASILMAZLIKLAR VE KARSI ARGUMANLAR

**Moderator:** Simdi en tartiSmali konulara geciyoruz. Goruslerin kesin olarak ayrildigi noktalari tartisalim.

---

### TARTISMA 1: ML Modeli Tamamen Kapatilmali mi?

**Prof. Lopez de Prado:** Evet, kesinlikle kapatilmali. AUC 0.5982 ile islem yapmak, yazI-tura atarak islem yapmaktan sadece marjinal olarak iyi ve komisyon maliyetleri bu marji siler. Sistem saf teknik sinyallerle (EMA crossover + RSI + MOST) calismali ve ML ancak AUC 0.65+ oldugunda yeniden devreye girmeli.

**Prof. Lo:** Marcos, burada sana katilmiyorum. ML'yi tamamen kapatmak bebegi banyo suyuyla birlikte atmaktir. Benim onerim: ML'yi "filtre" olarak kullan, "sinyal uretici" olarak degil. Yani teknik sinyal geldiginde, ML "bu sinyal gercekten guvenilir mi?" sorusunu cevaplasn. Meta-labeling yaklasiminla tutarli aslinda.

**Prof. Lopez de Prado:** Andrew, meta-labeling benim kavramim ve tam da su anda tavsiye edecegim sey. Ama bunu yapmak icin once BASE modelin AUC'si yeterli olmali ki meta-label ekleyebilelim. Su anki model base model olarak bile zayif.

**Prof. Bouchaud:** Ben farkli dusunuyorum. ML'nin sorunu AUC degil, HEDEF fonksiyonu. Rapordaki `hedef_olustur` fonksiyonu "5 gunluk pencerede en yuksek fiyat %3+ mi?" diyor. Bu, gercek islemde ulasilamaz bir hedeftir. Eger hedef fonksiyonunu "risk/odul bazli triple barrier" yontemiyle yeniden tanimlarsaniz ve modeli yeniden egitirseniz, AUC dramatik sekilde degisebilir -- yukari da asagi da. Modeli kapatmadan once en azindan dogru hedefle bir deneme yapilmali.

**Prof. Gulay:** Jean-Philippe Hoca'ya katiliyorum. Ekonometride "garbage in, garbage out" ilkesi gecerli. Model kotu degil, model YANLIS SORUYU cevapliyor. Hedef degiskenini duzeltmek, modeli sifirdan degistirmekten daha kolay ve etkili.

**Prof. Lopez de Prado:** Jean-Philippe ve Guzhan Hoca, ikinizle de kismen hemfikirim. Evet, hedef fonksiyonu sorunlu. Ama sorun sadece hedef degil -- 73+ koreleli feature, 5 fold walk-forward, Yahoo Finance verisi... Bunlarin HEPSINI duzeltmeden ML'yi acmanin anlami yok.

### TARTISMA 2: BIST'te Perakende Algo Trading Mantikli mi?

**Prof. Ulku:** Bu tartismanin en temel sorusu bu. BIST'te yabanci kurumsal yatirimcilar fiyat hareketlerinin %60-70'ini yonlendiriyor. Onlar milisaniye gecikmeli, co-location avantajli, Level-3 veriye sahip. ANKA gibi bir perakende sistem bunlarla REKABET EDEMEZ.

**Prof. Bildik:** Numan Hoca, sana kismen katilmiyorum. Evet, yabanci kurumsal yatirimcilar guclu. Ama BIST'te hala istismar edilebilir anomaliler var cunku piyasa tam etkin degil. Kucuk sermayeli hisseler, sektor rotasyonu, KAP bildirimleri sonrasi momentum -- bunlar kurumsal yatirimcilarin odaklanmadigi alanlar. ANKA dogru nise odaklanirsa avantaj bulabilir.

**Prof. Kyle:** Recep Hoca'nin soyledigi onemli bir nokta. Benim modelimde, bilgili islemci her zaman avantajli degildir -- bilgi avantaji NISPI olmali. BIST'teki kucuk sermayeli hisselerde kurumsal katilim dusukse, ANKA bir bilgi avantaji yaratabilir. Ama bunun icin Yahoo Finance degil, gercek veri; AUC 0.5982 degil, gercek sinyal kalitesi gerekir.

**Prof. Akgiray:** Bir regulasyon perspektifi ekleyeyim: BIST, gelisen piyasalar arasinda nispeten iyi duzenlanmis bir piyasa. Ancak piyasa gozlem kapasitesi sinirli. Bu, bir yandan ANKA gibi sistemlerin denetimden kaçirabileceAi anlamina gelir (kotu), diger yandan piyasa anomalilerinin daha uzun sure devam edebilecegi anlamina gelir (potansiyel olarak iyi).

**Prof. Lo:** Bence asil soru "perakende algo trading mantikli mi" degil, "bu SPESIFIK yaklasim mantikli mi". Warren Buffett perakende yatirimci, Renaissance Technologies kurumsal. Ikisi de kazaniyor ama tamamen farkli yontemlerle. ANKA'nin hatasi, kurumsal stratejileri (yuksek frekansli ML) perakende altyapiyla (laptop + VM) uygulamaya calismak. Strateji-altyapi uyumsuzlugu var.

**Prof. Hendershott:** Andrew'un soyledigine guclu sekilde katiliyorum. Bu "strategy-infrastructure mismatch" kavramini biz Berkeley'de cok tartisiyoruz. ANKA, $100 milyonluk hedge fund altyapisini 100.000 TL ile taklit etmeye calisiyor. Bunun yerine kendi nise'ini bulmali -- mesela daha uzun vadeli, daha az islem yapan, fundamental agirliki bir strateji laptop'tan da calisabilir.

### TARTISMA 3: Sistem Tamamen Kapatilmali mi, Yoksa Duzeltilmeli mi?

**Prof. Lopez de Prado:** Denetim raporunun onerisi ile hemfikirim: canli islemi DERHAL durdurun. En az 3 ay paper trade. Bu tartisilamaz.

**Prof. Bildik:** Marcos Hoca'ya katiliyorum ama bir sey ekleyeyim: paper trade sirasinda BIST'e ozgu faktorleri modele eklesin. Yabanci akis verisi, VIOP pozisyon degisiklikleri, KAP bildirimleri -- bunlar bedava ve guclu sinyallerdir.

**Prof. Salih:** Ben daha radikal bir oneriye sahibim: mevcut sistemi tamamen SIFIRLAMAYIN. Mimari tasarim iyi -- multi-agent, bridge, dashboard -- bunlar degerli. Sorun uygulamada. Once K-03, K-04, K-08'i duzelt (bunlar 2-3 gunluk is), sonra paper trade baslat.

**Prof. Bouchaud:** Ben de Aslihan Hoca'ya yakinim. CFM'de biz hicbir stratejiyi tamamen atmayiz -- once sorunlari duzeltir, sonra kucuk sermayeyle test ederiz. Ama burada kritik fark su: CFM'de bu sureci profesyonel bir ekip yonetir. ANKA'da tek bir kisi. Tek kisinin K-01'den K-11'e kadar 11 kritik sorunu duzeltmesi aylar alir. O aylar boyunca canli islem yapmak intihardir.

**Prof. Akgiray:** Jean-Philippe Hoca haklI. Ve bir regulasyon uyarisi daha: eger sistem hatalari nedeniyle piyasada anormal islem kaliplari olusursa ve SPK sorusturma baslatirsa, "sistemi duzeltiyorduk" savunma olmaz. Once TAMAMEN kapat, sonra duzelt, sonra paper trade, sonra kuçuk sermayeyle canli.

**Prof. Lo:** Panelin genel gorusunu ozetlersem: ANKA'nin vizyonu ve mimarisi takdire deger, ama uygulamasi tehlikeli. Canli islemi durdurmak sart, duzeltme plani net ve adimli olmali, ve BIST'e ozgu avantajlar sisteme entegre edilmeli.

---

## ROUND 5: NIHAI KARARLAR VE ONERILER

**Moderator:** Son raundda her panel uyesi harf notu ve en onemli onerisi verecek.

---

**Prof. Lo (MIT):**
- **Not: C+**
- **Gerekce:** Vizyon A-, uygulama D. Adaptive Markets cercevesinde bu sistem "evrimin erken asamasinda" -- potansiyel var ama hayatta kalma garantisi yok. AUC 0.5982 ile canli piyasada alfa negatif.
- **1 Numarali Oneri:** Sistemin alfa uretip uretmedigini kanitlayacak kapsamli bir backtesting calisma yapilsin: komisyon dahil, en az 3 yillik veri, XU100 benchmark, Sharpe > 1.0 hedefi.

**Prof. Lopez de Prado (Cornell):**
- **Not: D+**
- **Gerekce:** ML implementasyonunda temel metodolojik hatalar var. Lookahead bias, yetersiz walk-forward, koreleli featurelar, kalibre edilmemis olasiliklar. Bunlar finans ML'inin "olumcul gunah"laridir.
- **1 Numarali Oneri:** Hedef fonksiyonunu triple-barrier method ile yeniden tanimlayin, CPCV ile en az 100 yol test edin, ve feature importance ile ilk 20 bagimsiz feature'a inin.

**Prof. Kyle (Maryland):**
- **Not: C-**
- **Gerekce:** Piyasa mikro yapisi acisindan kabul edilemez hatalar var. Robotun kendi pozisyonunu bilmemesi, dolum fiyatini yanlis kaydetmesi, rejected order'lari gormezden gelmesi -- bunlar "islem yapma" eyleminin en temel gereksinimleridir.
- **1 Numarali Oneri:** C# robotundaki `OnOrderUpdate` callback'ini K-03 cozumune gore HEMEN duzelt. Bu, 2 saatlik bir is ve en kritik duzeltme.

**Prof. Bouchaud (Polytechnique):**
- **Not: C**
- **Gerekce:** Sistem normal dagilim varsayimini sorgulamiyor ve kuyruk riskleri modellenmiyor. BIST gibi gelisen piyasalarda kuyruk olaylari daha sik ve daha siddeltli. Kara kugu korumasinin olmamasi, tek bir kotu gunde tum sermayenin onemli bir kisminin kaybedilmesi riskini tasiyor.
- **1 Numarali Oneri:** Portfoy bazinda gunluk maksimum kayip limiti (%3) koyun. Bu limit asildiginda TUM pozisyonlar kapansin ve gun sonuna kadar yeni islem yapilmasin.

**Prof. Hendershott (Berkeley):**
- **Not: D**
- **Gerekce:** Muhendislik olgunlugu kabul edilemez. Dosya tabanli IPC, tek nokta arizasi, process monitoring yoklugu, launchd bile kullanilmamis olmasi -- bunlar bir trading sistemi degil, bir prototip bile degil, bir hack-night projesi.
- **1 Numarali Oneri:** VPS'e gecis ve Docker konteynerizasyonu ile infrastructure'i stabilize edin. Watchdog + heartbeat + Telegram bildirim sistemi kurun.

**Prof. Ulku (Borsa Istanbul):**
- **Not: C**
- **Gerekce:** BIST'e ozgu dinamikler tamamen goz ardi edilmis. Yabanci akis verisi, TCMB etkisi, seans yapisi, takas donemi -- bunlarin hicbiri modelde yok. BIST'te alfa ariyorsan, BIST'i tanimak zorundasin.
- **1 Numarali Oneri:** Yabanci yatirimci net alis/satis verisini (BIST'ten veya KAP'tan bedava edinilebilir) modele feature olarak ekleyin. Bu tek basina AUC'yi anlamli olcude artirabilir.

**Prof. Salih (Bilkent):**
- **Not: C+**
- **Gerekce:** Portfoy yonetimi acisindan ciddi bosluklar var. Risk yonetimi kodda var ama calismasi icin entegrasyonu yapilmamis. Korelasyon filtresi, drawdown limiti, Kelly -- hepsi kagit uzerinde. Ama mimari vizyon guclu, duzeltilmeye deger.
- **1 Numarali Oneri:** `risk_yonetimi.py`'yi bridge uzerinden C# robotuna entegre edin. Portfoy seviyesinde max 5 pozisyon, max 2 ayni sektor, max %10 gunluk drawdown kurallari FIILEN calismali.

**Prof. Bildik (Borsa Istanbul):**
- **Not: C+**
- **Gerekce:** BIST'te gercek anomaliler var ve ANKA dogru nise'i bulursa basarili olabilir. Ancak suan genel bir ML yaklasimi ile BIST'e ozgu avantajlari kaciyor. Enerji yuksek, yon yanlis.
- **1 Numarali Oneri:** ML modelini tamamen yeniden tasarlamak yerine, BIST'e ozgu kural tabanli stratejiler (KAP sinyal, endeks rebalance, temettü momentum) ekleyin ve ML'yi bunlarin uzerine filtre olarak kullanin.

**Prof. Gulay (Sabanci):**
- **Not: C-**
- **Gerekce:** Volatilite ve rejim modelleme zayif. 60 saniyelik bridge guncellemesi ile rejim degisikligini yakalamak imkansiz. GARCH ailesi veya Markov-switching modeli kullanilmali. VIX proxy hesaplamasi da cok kaba.
- **1 Numarali Oneri:** Rejim tespitini Hidden Markov Model ile yeniden tasarlayin ve VIX proxy yerine BIST opsiyonlarindan implied volatility hesaplayin (VIOP verileri mevcuttur).

**Prof. Akgiray (Bogazici / eski SPK):**
- **Not: C-**
- **Gerekce:** Regulatif uyumluluk riskleri yuksek. Kill-switch yoklugu, emir kayitlarinin sistematik tutulmamasi, manipulasyon tespit mekanizmasinin olmamasi -- bunlar SPK denetimine girilirse ciddi sorunlara yol acar. Ayrica tek kisinin gelistirdigi, denetlenmeyen bir sistem operasyonel risk acisindan endise verici.
- **1 Numarali Oneri:** Gunluk max emir sayisi limiti, tek emir max buyuklugu limiti, ve gunluk max kayip limiti olmak uzere uc katmanli bir guvenlik mekanizmasi DERHAL uygulansin.

---

## KONSENSUS RAPORU

### Panel Ortalama Notu: **C- / C** (2.15 / 4.00)

### Not Dagilimi:
| Profesor | Kurum | Not | Sayisal |
|----------|-------|-----|---------|
| Lo | MIT | C+ | 2.3 |
| Lopez de Prado | Cornell | D+ | 1.3 |
| Kyle | Maryland | C- | 1.7 |
| Bouchaud | Polytechnique | C | 2.0 |
| Hendershott | Berkeley | D | 1.0 |
| Ulku | Borsa Istanbul | C | 2.0 |
| Salih | Bilkent | C+ | 2.3 |
| Bildik | Borsa Istanbul | C+ | 2.3 |
| Gulay | Sabanci | C- | 1.7 |
| Akgiray | Bogazici | C- | 1.7 |
| **ORTALAMA** | | **C-/C** | **1.83** |

### Konsensus Degerlendirmesi:

Panel, oybirligiyle asagidaki tespitleri yapmistir:

**GUCLU YONLER:**
1. Tek bir kisinin bu karmasiklikta bir sistem gelistirmis olmasi teknik beceri acisindan takdire deger
2. Multi-agent mimari kavramsai olarak saglamdir
3. Risk yonetimi cercevesi (risk_yonetimi.py) dogru tasarlanmis -- ama entegrasyonu yapilmamis
4. Bridge sistemi ve dashboard gibi operasyonel bileskenler profesyonel bir vizyon gosteriyor
5. Walk-forward validasyon doğru yaklaşımı kullanmış (purge + expanding window)

**KRITIK ZAYIFLIKLAR:**
1. AUC 0.5982 komisyon sonrasi net alfa uretmeye yetmez (10/10 uzlasma)
2. Pozisyon takibi ve emir yonetimi hatalari hayalet pozisyon riski olusturur (10/10 uzlasma)
3. Risk yonetimi kodda var ama fiilen calismıyor (10/10 uzlasma)
4. BIST'e ozgu dinamikler modelde yok (8/10 uzlasma)
5. Altyapi (laptop + VM) kurumsal standardlarin cok altinda (9/10 uzlasma)
6. Kara kugu ve kuyruk riski koruması yok (10/10 uzlasma)

### Oncelikli Aksiyon Listesi (Panel Oncelik Sirasina Gore):

| Oncelik | Aksiyon | Sorumlu Bileşen | Tahmini Sure | Panel Destegi |
|---------|---------|-----------------|--------------|---------------|
| **1** | CANLI ISLEMI DERHAL DURDURUN | Genel | Simdi | 10/10 |
| **2** | OnOrderUpdate duzeltmesi (K-03, K-04) | C# Robot | 1 gun | 10/10 |
| **3** | Portfoy bazinda gunluk max kayip limiti (%3) | Bridge + C# | 1 gun | 10/10 |
| **4** | Kill-switch mekanizmasi | Bridge + C# | 2 gun | 10/10 |
| **5** | risk_yonetimi.py'nin C# entegrasyonu | Bridge + C# | 3 gun | 9/10 |
| **6** | Korelasyon filtresi aktivasyonu (max 2 ayni sektor) | Bomba tarama | 2 gun | 9/10 |
| **7** | Watchdog + heartbeat + bildirim sistemi | Python | 3 gun | 9/10 |
| **8** | ML hedef fonksiyonu duzeltmesi (triple barrier) | tahmin_motoru | 1 hafta | 8/10 |
| **9** | BIST-spesifik feature eklenmesi (yabanci akis, VIOP) | ML Pipeline | 1 hafta | 8/10 |
| **10** | Kapsamli backtest (komisyon dahil, 3 yil, XU100 kiyaslama) | Yeni modul | 2 hafta | 10/10 |
| **11** | Walk-forward fold sayisini 5'ten 50+'ya cikarma | tahmin_motoru | 3 gun | 7/10 |
| **12** | Feature secimi (73+ -> en onemli 20-25) | ML Pipeline | 1 hafta | 8/10 |
| **13** | VPS gecisi | Altyapi | 2 hafta | 7/10 |
| **14** | Paper trade modu (DRY_RUN) | C# Robot | 2 gun | 10/10 |
| **15** | Rejim tespiti iyilestirmesi (HMM) | v3_risk_motor | 2 hafta | 6/10 |

### Minimum Canli Isleme Donus Kosullari:

Panel, canli isleme donulebilmesi icin asagidaki BUTUN kosullarin saglanmasini oybirligiyle talep etmektedir:

1. K-03, K-04, K-05 duzeltilmis ve test edilmis olmali
2. Portfoy bazinda gunluk max kayip limiti FIILEN calisiyor olmali
3. En az 3 aylik paper trade tamamlanmis olmali
4. Paper trade doneminde XU100 buy-and-hold'dan daha iyi performans gosterilmis olmali
5. Sharpe orani > 0.5 (minimum) saglanmis olmali
6. Maksimum drawdown < %15 gozlenmis olmali
7. Kill-switch mekanizmasi kurulmus ve test edilmis olmali
8. Watchdog / heartbeat sistemi calisiyor olmali

Bu kosullar saglanana kadar CANLI ISLEM YAPILMAMALIDIR.

---

### Kapanıs Notu:

Bu panel tartismasi, ANKA Trading System'in "yikilmasi gereken kotu bir sistem" degil, "potansiyeli olan ama tehlikeli bir sistem" oldugu tespitinde birlesit. Gelistiricinin teknik yetenegi tartismasizdir. Eksik olan, finans muhendisligi disiplini, istatistiksel titizlik ve operasyonel olgunluktur. Bu rapordaki 15 maddelik aksiyon planini siraSiyla uygulamak, ANKA'yi bir "hack-night projesi"nden "ciddi bir trading sistemi"ne donusturme potansiyeline sahiptir.

Ancak bu donusum sureci CANLI PARA ILE DEGIL, paper trade ile yapilmalidir.

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

**Tarih:** 3 Nisan 2026
**Yer:** Istanbul / Virtual Panel Session

---

*Bu akademik panel tartismasi, ANKA Trading System denetim raporunun bagimsiz degerlendirmesi icin duzenlenmistir. Yatirim tavsiyesi icermez. Tum gorusler panel uyelerinin akademik perspektiflerini yansitir.*
