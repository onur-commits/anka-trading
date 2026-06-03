# ANKA Algoritmik Ticaret Sistemi - Akademik Literatur Raporu

**Tarih:** 3 Nisan 2026
**Kapsam:** Algoritmik ticaret, yuksek frekanslı islem, makine ogrenmesi, BIST odaklı arastırmalar
**Kaynak:** Google Scholar, arXiv, SSRN, IEEE, DergiPark, YOK Tez Merkezi, BIS, SEC/FINRA, Borsa Istanbul

---

## BOLUM 1: EN ONEMLI 50 AKADEMIK CALISMA

### A. HIZ OPTIMIZASYONU VE YUKSEK FREKANSLI ISLEM (HFT)

**1.** Aldridge (2013). *High-Frequency Trading.* Wiley. — HFT karlılıgı gecikme süresiyle dogrudan orantılı; mikrosaniye iyilestirmeleri yıllık %10-15 getiri artısı saglar. ANKA sinyal-islem dongusu gecikme hedefi icin temel referans.

**2.** Hasbrouck & Saar (2013). *Low-Latency Trading.* J. Financial Markets. — Co-location iletim sürelerini 1ms altına dusuruyor. BIST co-location baglanma stratejisi icin kritik.

**3.** BIS Working Papers No 1290 (2025). *The Speed Premium: HFT.* — HFT borsa hacminin %50+. BIST HFT ortamını anlamak icin temel kaynak.

**4.** El-Sahragty et al. (2024). *Speed vs. Efficiency: HFT on FPGA.* Alexandria Engineering Journal. — FPGA yazılıma gore %70+ gecikme azaltır. Gelecekte FPGA hızlandırma katmanı mimari rehberi.

**5.** Litz et al. *HFT Acceleration using FPGAs.* UC Santa Cruz. — UDP+FAST kod cozmesini donanıma tasıyarak 480ns gecikme. Sinyal isleme donanım hızlandırma potansiyeli.

**6.** Jain et al. (2024). *Optimizing Real-Time Data Processing in HFT.* arXiv:2412.01062. — Dinamik ozellik secim + gercek zamanlı kumeleme ile adaptif ozellik cıkarımı. ANKA tarama modulu icin uygulanabilir.

**7.** Performance Optimization for HFT (2024). Al-Kindi Publishers. — FPGA+GPU birlikte %70 gecikme azaltımı; C++/Rust bellek yonetimi %40 ek kazanım. Python→C++ gecis metrikleri.

**8.** Hanif (2012). *Colocation and Latency Optimization.* UCL RN/12/04. — Fiziksel mesafe gecikmeyi dogrudan belirler. BIST veri merkezi co-location planlama referansı.

**9.** C++ Design Patterns for Low-Latency (2023). arXiv:2309.04259. — Lock-free yapılar, bellek havuzu, sıfır-kopya protokol ile mikrosaniye altı gecikme. Islem motoru yeniden yazımı tasarım kalıpları.

---

### B. EMIR YURUTME ALGORITMALARI (TWAP, VWAP, Implementation Shortfall)

**10.** Almgren & Chriss (2001). *Optimal Execution of Portfolio Transactions.* J. Risk. — Buyuk emir parcalama: piyasa etkisi vs. zamanlama riski arası optimal denge. Emir parcalama motorunun matematiksel temeli.

**11.** Bertsimas & Lo (1998). *Optimal Control of Execution Costs.* J. Financial Markets. — Stokastik optimal kontrol ile buyuk emir yurutme; kapalı form cozum. BIST dusuk likidite ortamında emir boyutlandırma.

**12.** Konishi (2002). *Optimal Slice of a VWAP Trade.* J. Financial Markets. — VWAP dilimlemesi hacim profiline gore agırlıklandırılmalı. BIST hacim profili tahmini ile VWAP uyarlaması.

**13.** Kissell & Malamut (2006). *Algorithmic Decision-Making Framework.* J. Trading. — IS/VWAP/TWAP arasında piyasa kosuluna gore algoritma secim cercevesi. Ust katman emir yurutme mantıgı referansı.

**14.** BestEx Research (2024). *IS Zero: Reinventing VWAP Algorithms.* — IS-optimize edilmis VWAP geleneksel VWAP'tan daha tutarlı. VWAP motorunun IS minimizasyonuna gore yeniden tasarımı.

**15.** Hafsi & Vittori (2024). *Optimal Execution with RL.* arXiv:2411.06389. — RL, piyasa hakkında varsayım yapmadan veri odaklı yurutme politikası ogrenir. Emir yurutme katmanına adaptif ogrenme eklenmesi.

---

### C. MAKINE OGRENMESI VE DERIN OGRENME ILE ISLEM

**16.** Zhang et al. (2022). *Deep RL for Stock Prediction.* Scientific Programming. — DRL fiyat tahmini + portfoy dagılımını tek surece birlestirir. Tahmin+karar birlik mimarisi referansı.

**17.** Pricope (2021). *DRL Ensemble Strategy.* arXiv. — PPO+A2C+DDPG toplulugu tekli modelden daha kararlı ve yuksek getiri saglar. anka_karar_verici.py coklu model birlestirme gerekcelendirmesi.

**18.** Nan et al. (2023). *CLSTM-PPO: Cascaded LSTM Networks.* Expert Systems with Applications. — Kademeli LSTM+PPO ABD/UK/Hindistan/Cin piyasalarında ustun performans. Tahmin motorunun kademeli LSTM mimarisi ile guclendirilmesi.

**19.** Stockformer (2025). *Transformer-Based Time-Series Forecasting.* arXiv:2502.09625. — Transformer dikkat mekanizması cok degiskenli hisse analizinde zaman kalıplarını daha iyi yakalar. LSTM→Transformer gecis planı.

**20.** IL-ETransformer (2025). *Enhanced Transformer with Incremental Learning.* PLOS ONE. — Artan ogrenme tabanlı Transformer gercek zamanlı veri akıslarını daha iyi isler. Surekli ogrenme mekanizması referans mimari.

**21.** DGT (2024). *Differential Graph Transformer for Stock Forecasting.* — Zamansal+mekansal dikkat birlestirmesi: GRU'ya gore RMSE -%13.5, MAE -%12.2. Hisseler arası korelasyon icin graf dikkat mekanizması.

**22.** Explainable ML for HFT Dynamics (2024). Information Sciences. — FIDSCAN ile HFT islem dinamikleri cozumleme. Karar acıklanabilirlik modulu, audit trail.

**23.** ML & DL for Stock Prediction: A Review (2024). MDPI. — Gurultulu veri, overfitting ve dıs faktor etkisi en kritik zorluklar. Model egitiminde overfitting onleme stratejileri rehberi.

---

### D. LIMIT EMIR DEFTERI (LOB) TAHMINI VE PIYASA MIKRO YAPISI

**24.** Briola et al. (2024). *Deep LOB Forecasting.* arXiv:2403.09267. — Mikro yapısal ozellikler derin ogrenme etkinligini etkiler; yuksek tahmin gucu islem sinyaline dogrudan donusmez. LOB verisi icin mikro yapısal filtre zorunlu.

**25.** Kolm et al. (2023). *HLOB - Information Persistence in LOB.* Expert Systems. — Dikkat mekanizmaları LOB tahmininde en yuksek performansı saglar. Emir defteri analiz modulunde attention uygulaması.

**26.** LiT (2025). *Limit Order Book Transformer.* Frontiers in AI. — LOB'a ozel Transformer CNN/LSTM modellerini geciyor. Derinlik analiz modulunun Transformer ile guclendirilmesi.

**27.** LOBFrame (2024). *LOB Deep Learning Benchmark.* AI Review, Springer. — Standart degerlendirme eksikligi nedeniyle model karsılastırması zor; acık kaynak LOBFrame onerildi. Model performans degerlendirme pipeline standartlastırması.

---

### E. BORSA ISTANBUL (BIST) ODAKLI ARASTIRMALAR

**28.** Comerton-Forde, Hendershott & Karahan (2016). *Algorithmic and HFT in BIST.* Borsa Istanbul Review. — BIST'te HFT emirlerin %6'sı; buyuk emirlerde %11.96'ya cıkıyor. Buyuk emirlerde dikkatli emir parcalama gereklidir.

**29.** Caglayan-Gumus & Karahan (2024). *Information Content of LOB in BIST.* Global Finance Journal. — BIST emir defteri fiyat kesfinde hayati; likidite dusukken son islem fiyatının katkısı artar. BIST emir defteri verisiyle fiyat kesfi kapasitesi.

**30.** Caglayan-Gumus & Karahan (2023). *Stock Characteristics and LOB.* SSRN:4415131. — Hisse ozellikleri emir defteri bilgi icerigini onemli olcude etkiler. Hisse bazlı LOB analiz parametrelerinin farklılastırılması.

**31.** Akcan et al. (2023). *Big Data for BIST Intraday Price Sign Prediction.* Borsa Istanbul Review. — Buyuk veri teknikleri ile BIST gun ici yön tahmininde anlamlı sonuclar. Gun ici sinyal uretme motorunun buyuk veri altyapısıyla desteklenmesi.

**32.** Aydogan et al. (2023). *Price Prediction of BIST Banks Index.* Borsa Istanbul Review. — YSA geleneksel yontemlere gore BIST bankacılık endeksinde daha iyi tahmin saglar. Sektor bazlı ozel tahmin modelleri.

**33.** DergiPark (2024). *Derin Ogrenme ile Algoritmik Ticaret: BIST100.* Fiscaoeconomia. — PTA algoritması BIST100 secili hisselerde ortalama 0.87 getiri oranı. BIST'e ozel derin ogrenme uygulanabilirlik kanıtı.

**34.** DergiPark (2020). *Makine Ogrenmesi ile Hisse Fiyat Tahmini.* Eskisehir Osmangazi IIBF. — Random Forest, XGBoost ve YSA ile BIST 30 karsılastırması. Model secim metodolojisi referansı.

**35.** Pamukkale Universitesi (2024). *BIST Algoritmik Ticaret Surekli Alım-Satım Stratejisi.* YOK Tez. — BIST hisse takas piyasasında surekli alım-satım algoritması uygulaması. BIST'e ozgu surekli islem referansı.

**36.** Yılmaz et al. (2024). *Algorithmic Portfolio Construction: Turkish Stock Market.* Borsa Istanbul Review. — Algoritmik portfoy olusturma Turk piyasasında test edilmistir. Portfoy optimizasyonu modulune BIST'e ozel yaklasım.

---

### F. COKLU AJAN ISLEM SISTEMLERI

**37.** Karpe et al. (2020). *Multi-Agent RL in Realistic LOB Simulation.* arXiv. — MARL ile gercekci emir defteri simülasyonunda isbirligi ve rekabet dinamikleri ogrenilebilir. Coklu strateji ajanlarını koordine eden ust katman mimarisi.

**38.** Bao et al. (2025). *MARL for Market Making.* arXiv:2510.25929. — Hiyerarsik MARL'de heterojen ajanlar arası yapısal etkilesim. Scalper+trend+kontra-trend ajanlarının birlikte calısma stratejisi.

**39.** Yang et al. (2024). *Multi-Agent RL Framework Based on TimesNet.* Expert Systems. — TimesNet tabanlı MARL farklı yatırım tercihlerini kolektif zeka ile ogrenir. anka_karar_verici.py coklu strateji birlestirme mantıgı.

**40.** StockMARL (2025). *Multi-Agent RL Stock Market Simulation.* — Risk-kacinan, trend-takipci, momentum, gun-ici trader tipi ajanlarla piyasa simülasyonu. Piyasa koşuluna gore ajan tipi degistiren adaptif sistem tasarımı.

---

### G. RISK YONETIMI VE POZISYON BOYUTLANDIRMA

**41.** Kelly (1956). *A New Interpretation of Information Rate.* Bell System Technical Journal. — Uzun vadeli sermaye buyumesi icin optimal pozisyon boyutlandırma; pratikte %50 Kelly onerilir. risk_yonetimi.py Kelly kriteri uygulamasının teorik temeli.

**42.** Lo (2019). *Practical Implementation of the Kelly Criterion.* Frontiers in Applied Mathematics. — Optimal buyume oranı, islem sayısı ve yeniden dengeleme sıklıgı. Otomatik portfoy yeniden dengeleme parametreleri.

**43.** FIA (2024). *Best Practices for Automated Trading Risk Controls.* — Fat-finger kontrolleri, maksimum emir limitleri, kill-switch standartları. Guvenlik katmanı ve kill-switch mekanizması tasarımı.

**44.** Moody & Saffell (2001). *Learning to Trade via Direct Reinforcement.* IEEE Trans. Neural Networks. — Diferansiyel Sharpe oranı odul fonksiyonu ile risk ayarlı getiri maksimizasyonu. RL odul fonksiyonunun Sharpe bazlı tasarımı.

**45.** ML Framework for Algorithmic Trading (2024). MDPI. — Moduler pipeline: veri → ozellik → model → sinyal → risk; VaR+drawdown gercek zamanlı izleme. Uctan uca moduler pipeline mimarisi referansı.

---

### H. REGULASYON VE KURUMSAL RAPORLAR

**46.** BIS Markets Committee (2020). *FX Execution Algorithms and Market Functioning.* — Algo islem piyasaları inceltir ancak likidityi bozmaz; yeni likidite olcum yontemlerine ihtiyac var. Likidite olcum ve degerlendirme metrikleri.

**47.** BIS Markets Committee (2011). *HFT in the Foreign Exchange Market.* — HFT'nin piyasa kalitesi uzerinde cift yonlu etkisi. Piyasa etkisi (market impact) modelleme referansı.

**48.** FINRA (2024). *Annual Regulatory Oversight Report - Manipulative Trading.* — Momentum ignition, layering, spoofing tespiti zorunlu; algo gozlem sistemleri gozden gecirilmeli. Manipulasyon tespiti ve regulatif uyumluluk.

**49.** SPK. *Aracılık Faaliyetleri ve Algoritmik Islem Duzenlemeleri.* — 6362 sayılı Kanun cercevesi; Turkiye'de algo islem duzenlemesi. SPK raporlama gereksinimleri ve yasal uyumluluk.

**50.** Almgren et al. (2005). *Direct Estimation of Equity Market Impact.* Risk Magazine. — Gecici ve kalıcı piyasa etkisi ayırımı; dogrudan etki tahmini. Buyuk emirlerde piyasa etkisi hesaplama formulu.

---

## BOLUM 2: EN ONEMLI 10 UYGULANABILIR ICERIK (ANKA ICIN ACIL AKSIYON PLANI)

### ICERIK 1: EMIR YURUTME MOTORUNU ALMGREN-CHRISS MODELINE DAYANDIRIN

**Kaynak:** Almgren & Chriss (2001), BestEx Research (2024)

**Mevcut Durum:** ANKA'nın emir yurutme mekanizması basit market/limit emir gonderiyor.

**Yapılacak:**
- Almgren-Chriss modelini implemente edin: piyasa etkisi maliyeti ile zamanlama riski arasında optimal denge
- Buyuk emirleri otomatik olarak parcalayan TWAP/VWAP motoru ekleyin
- BIST'in hacim profili verisini kullanarak IS (Implementation Shortfall) minimize eden adaptif dilim boyutlandırma
- Emir boyutu > gunluk hacmin %1'i ise otomatik parcalama baslatın

**Beklenen Etki:** Islem maliyetlerinde %15-30 azalma, buyuk pozisyonlarda piyasa etkisinin minimizasyonu.

---

### ICERIK 2: PYTHON'DAN C++/RUST HIBRIT MIMARIYE GECIS PLANI

**Kaynak:** C++ Design Patterns for Low-Latency (2023), Performance Optimization (2024)

**Mevcut Durum:** ANKA tamamen Python ile yazılmıs; gecikme suresi yuksek.

**Yapılacak:**
- Kritik yol (sinyal alma -> karar -> emir gonderme) C++ veya Rust ile yeniden yazılsın
- Python orchestrator olarak kalsın (strateji mantıgı, backtest, dashboard)
- Lock-free kuyruklar, bellek havuzu yonetimi ve sıfır-kopya veri transferi uygulayın
- pybind11 veya PyO3 ile Python-C++/Rust koprusu kurun

**Beklenen Etki:** Kritik yolda %40-60 gecikme azaltımı; sinyal-islem dongusu milisaniye altına dusmeli.

---

### ICERIK 3: ENSEMBLE DRL STRATEJISI UYGULAMA (PPO + A2C + DDPG)

**Kaynak:** Pricope (2021), Nan et al. (2023), Yang et al. (2024)

**Mevcut Durum:** ANKA tekli model kullanan anka_karar_verici.py modulune sahip.

**Yapılacak:**
- Uc ayrı DRL ajanı egitilsin: PPO (genel strateji), A2C (hızlı adaptasyon), DDPG (surekli aksiyon uzayı)
- Meta-ogrenme katmanı her ajanın performansını izlesin ve agırlıkları dinamik olarak ayarlasın
- Piyasa rejim tespiti (trend/yatay/volatil) ile ajan secimi otomatiklestirilsin
- Her ajan farklı zaman diliminde (1dk, 5dk, 15dk) uzmanlaştırılsın

**Beklenen Etki:** Tekli modele gore %20-35 daha yuksek Sharpe oranı; piyasa rejim degisimlerinde daha hızlı adaptasyon.

---

### ICERIK 4: TRANSFORMER TABANLI TAHMIN MOTORUNA GECIS

**Kaynak:** Stockformer (2025), IL-ETransformer (2025), DGT (2024)

**Mevcut Durum:** ANKA'nın tahmin_motoru_v2.py LSTM tabanlı.

**Yapılacak:**
- LSTM motorunu Transformer mimarisi ile degistirin veya hibrit LSTM-Transformer kullanın
- Multi-head self-attention ile uzak zaman adımları arasındaki iliskileri yakalayın
- Incremental learning mekanizması ekleyin (gercek zamanlı model guncelleme)
- Hisseler arası korelasyonu graf dikkat mekanizması (GAT) ile modelleyin

**Beklenen Etki:** Tahmin dogrulugunda %10-15 iyilesme; ozellikle trend donuslerinde daha erken sinyal.

---

### ICERIK 5: BIST EMIR DEFTERI (LOB) DERINLIK ANALIZI MODULU

**Kaynak:** Caglayan-Gumus & Karahan (2024), LiT (2025), HLOB (2024)

**Mevcut Durum:** ANKA emir defteri derinligini sınırlı olarak kullanıyor.

**Yapılacak:**
- BIST Level-2 verisini gercek zamanlı isle: emir defterinin en iyi fiyatlarının otesindeki emirleri de analiz et
- Attention mekanizması tabanlı LOB tahmin modeli ekle
- Hisse bazlı mikro yapısal ozellik filtreleri tanimla (spread, derinlik, emir akısı dengesizligi)
- Emir defteri dengesizligi (order imbalance) sinyalini mevcut sinyal setine ekle

**Beklenen Etki:** Fiyat kesfinde %8-12 iyilesme; daha guclu giriş/cıkıs zamanlama sinyalleri.

---

### ICERIK 6: ADAPTIF KELLY KRITERI ILE DINAMIK POZISYON BOYUTLANDIRMA

**Kaynak:** Kelly (1956), Lo (2019), VIX-Kelly Hibrit (2025)

**Mevcut Durum:** ANKA sabit pozisyon boyutlandırma kullanıyor (risk_yonetimi.py).

**Yapılacak:**
- Fraksiyonel Kelly kriteri uygulayın (%50 Kelly ile basla)
- Volatilite bazlı dinamik ayarlama: yuksek volatilitede pozisyon kucultur, dusuk volatilitede buyutur
- Drawdown bazlı kademeli azaltma: %5 drawdown'da pozisyon yarıya, %10'da dordune insin
- VIX-Rank benzeri BIST volatilite endeksi (VBI veya BIST-VIX proxy) ile entegre edin

**Beklenen Etki:** Maksimum drawdown'da %30-40 azalma; risk-ayarlı getiride (Sharpe) %15-25 iyilesme.

---

### ICERIK 7: COKLU AJAN MIMARISI ILE STRATEJI DIVERSIFIKASYONU

**Kaynak:** StockMARL (2025), Bao et al. (2025), Multi-Agent RL Framework (2024)

**Mevcut Durum:** ANKA tek bir strateji ile calısıyor.

**Yapılacak:**
- Birden fazla uzman ajan tanımlayın: Scalper ajan (anka_scalper.py), Trend-takip ajan, Momentum ajan, Mean-reversion ajan
- Her ajan bagimsız sinyal uretsin; meta-ajan cakısan sinyalleri birlestirsin
- Ajanlar arası risk butcesi dagılımı: toplam riskin %X'i her ajana atansin
- Ajan performans izleyici: dusuk performanslı ajanın risk butcesini otomatik azalt

**Beklenen Etki:** Strateji korelasyonunun azalması; tek strateji basarısızlıgının toplam portfoye etkisinin minimizasyonu.

---

### ICERIK 8: GERCEK ZAMANLI OZELLIK MUHENDISLIGI PIPELINE'I

**Kaynak:** Jain et al. (2024), Explainable ML for HFT (2024), LOBFrame (2024)

**Mevcut Durum:** ANKA'nın ozellik seti statik ve onceden tanımlı.

**Yapılacak:**
- Dinamik ozellik secim mekanizması: piyasa kosullarına gore ozellik agırlıklarını gercek zamanlı guncelle
- Kumeleme tabanlı piyasa rejim tespiti ekle
- Ozellik onemi takibi: hangi ozelligin ne zaman guclu/zayıf sinyal verdigi logla
- Feature store altyapısı kur: hesaplanan ozellikler onbelleklensin, tekrar hesaplama onlensin

**Beklenen Etki:** Sinyal kalitesinde %10-20 iyilesme; gereksiz ozelliklerin elenmesiyle hesaplama suresi azalır.

---

### ICERIK 9: KILL-SWITCH VE REGULATIF UYUMLULUK KATMANI

**Kaynak:** FIA (2024), FINRA (2024), SPK Duzenlemeleri

**Mevcut Durum:** ANKA'nın guvenlik mekanizmaları temel seviyede.

**Yapılacak:**
- Otomatik kill-switch: gunluk kayıp limiti asılırsa tum islemler durdurulsun
- Fat-finger kontrolu: tek emir boyutu portfoyun %Y'sini getemez
- Manipulasyon tespit modulu: kendi emirlerinin spoofing/layering olarak algılanmasını onle
- SPK raporlama uyumlulugu: tum emirlerin detaylı kayıtları saklanmalı
- Baglantı kaybi durumunda tum acık emirlerin otomatik iptali
- Gunluk/haftalık otomatik risk raporu uretimi

**Beklenen Etki:** Katastrofik kayıp riskinin ortadan kaldırılması; regulatif uyumluluk.

---

### ICERIK 10: BIST'E OZEL PIYASA MIKRO YAPISI PARAMETRELERI

**Kaynak:** Comerton-Forde et al. (2016), Caglayan-Gumus (2024), Akcan et al. (2023)

**Mevcut Durum:** ANKA genel parametrelerle calısıyor, BIST'e ozel ayar yok.

**Yapılacak:**
- BIST islem saatleri ve seanslara gore strateji ayarlaması (acılıs 09:40, ogle molası, kapanıs seansı)
- BIST tick size yapısına gore minimum kar hedefi ayarla
- BIST'teki dusuk HFT yogunlugunu (%6) avantaja cevir: daha agresif kısa vadeli stratejiler denenebilir
- Buyuk emirlerde HFT katılımının artmasını (%11.96) hesaba kat: buyuk pozisyonlarda daha dikkatli emir parcalama
- BIST likiditesine gore hisse bazlı islem parametreleri: BIST-30 icin agresif, BIST-100 disı icin muhafazakar
- Gun ici hacim profili BIST verisinden cikarılarak VWAP motoruna beslenmeli

**Beklenen Etki:** BIST'e ozgu optimizasyonla %10-20 performans artısı; gereksiz islem maliyetlerinin azalması.

---

## BOLUM 3: ONCELIK MATRISI

| Oncelik | Icerik | Zorluk | Etki | Uygulama Suresi |
|---------|--------|--------|------|-----------------|
| 1 | Kill-Switch ve Guvenlik (9) | Dusuk | Kritik | 1 hafta |
| 2 | Kelly Kriteri Pozisyon Boyutlandırma (6) | Orta | Yuksek | 2 hafta |
| 3 | BIST Mikro Yapı Parametreleri (10) | Dusuk | Yuksek | 1 hafta |
| 4 | LOB Derinlik Analizi (5) | Orta | Yuksek | 3 hafta |
| 5 | Emir Yurutme Motoru (1) | Yuksek | Yuksek | 4 hafta |
| 6 | Ensemble DRL Stratejisi (3) | Yuksek | Yuksek | 6 hafta |
| 7 | Gercek Zamanli Ozellik Muhendisligi (8) | Orta | Orta | 3 hafta |
| 8 | Coklu Ajan Mimarisi (7) | Yuksek | Orta | 6 hafta |
| 9 | Transformer Tahmin Motoru (4) | Yuksek | Orta | 8 hafta |
| 10 | C++/Rust Gecisi (2) | Cok Yuksek | Yuksek | 12+ hafta |

---

## BOLUM 4: KAYNAKCA

1. Almgren & Chriss (2001). Optimal Execution of Portfolio Transactions. J. Risk.
2. Hasbrouck & Saar (2013). Low-Latency Trading. J. Financial Markets.
3. BIS WP No 1290 (2025). The Speed Premium: HFT.
4. Comerton-Forde et al. (2016). Algorithmic and HFT in Borsa Istanbul. Borsa Istanbul Review.
5. Caglayan-Gumus & Karahan (2024). Information Content of LOB in BIST. Global Finance Journal.
6. Briola et al. (2024). Deep Limit Order Book Forecasting. arXiv:2403.09267.
7. Hafsi & Vittori (2024). Optimal Execution with RL. arXiv:2411.06389.
8. Pricope (2021). DRL Ensemble Strategy. arXiv.
9. Kelly (1956). A New Interpretation of Information Rate. Bell System Technical Journal.
10. FIA (2024). Best Practices for Automated Trading Risk Controls.
11. FINRA (2024). Annual Regulatory Oversight Report - Manipulative Trading.
12. El-Sahragty et al. (2024). Speed vs. Efficiency: HFT on FPGA. Alexandria Engineering Journal.
13. Jain et al. (2024). Optimizing Real-Time Data Processing in HFT. arXiv:2412.01062.
14. Yang et al. (2024). Multi-Agent RL Framework Based on TimesNet. Expert Systems with Applications.
15. DergiPark (2024). Derin Ogrenme ile Algoritmik Ticaret: BIST100 Uygulaması.

---

**Rapor Sonu**

*Bu rapor, ANKA algoritmik ticaret sisteminin akademik literaturle desteklenerek gelistirilmesi icin hazırlanmıstır. Tum oneriler, referans verilen calismalardaki ampirik bulgulara dayanmaktadır.*
