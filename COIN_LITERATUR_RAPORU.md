# COIN TRADER — Akademik Literatur Raporu (52 Makale)

**Tarih:** 9 Nisan 2026
**Kapsam:** Kripto algoritmik ticaret, ML/DL, on-chain metrikler, volatilite, risk yonetimi
**Kaynak:** Google Scholar, arXiv, SSRN, NBER, IEEE, DergiPark, Financial Innovation, Journal of Finance

---

## A. ANKETLER VE KAPSAMLI INCELEMELER

**1.** Zhang, J., Cai, K., & Wen, J. (2023). "A Survey of Deep Learning Applications in Cryptocurrency." *iScience*, 27(1), 108509.
- **Bulgu:** CNN, RNN, DBN ve DRL karsilastirmasi. LSTM fiyat tahmininde baskin; hibrit yaklasimlar dogrulugu artiriyor.
- **COIN Bot Ilgisi:** Model secimi icin yol haritasi — LSTM + hibrit mimariler oncelikli.

**2.** Jabbar, A. & Jalil, S.Q. (2024). "A Comprehensive Analysis of ML Models for Algorithmic Trading of Bitcoin." *arXiv:2407.18334*.
- **Bulgu:** 41 ML modeli test edildi. Random Forest ve SGD karlilik/risk yonetiminde en iyi. Sharpe Ratio dahil trading metrikleri kullanildi.
- **COIN Bot Ilgisi:** Model benchmark referansi — RF coin bot icin guvenilir secenek.

**3.** Fang, F. et al. (2022). "Cryptocurrency Trading: A Comprehensive Survey." *Financial Innovation*, 8, 13.
- **Bulgu:** 146 makale sistematik taramasi. Trading sistemleri, portfoy optimizasyonu, piyasa analizi kapsami.
- **COIN Bot Ilgisi:** Tam bir kripto trading sisteminin tum bilesenlerini tanimliyor.

**4.** Akyildirim, E., Goncu, A., & Sensoy, A. (2021). "Prediction of Cryptocurrency Returns Using ML." *Annals of Operations Research*, 297, 3-36.
- **Bulgu:** SVM, LR, ANN, RF karsilastirmasi; yon tahmini dogrulugu %55+ teknik indikator feature'lari ile.
- **COIN Bot Ilgisi:** Gercekci performans beklentisi — %55 ustu basari hedeli.

---

## B. MAKINE OGRENMESI VE DERIN OGRENME

**5.** Omole, F. & Enke, D. (2025). "Using ML/DL, On-Chain Data and Technical Analysis for Predicting BTC." *Engineering Applications of AI*.
- **Bulgu:** Boruta-CNN-LSTM modeli 225 feature ile %82.44 dogruluk. 92 on-chain + 138 teknik indikator.
- **COIN Bot Ilgisi:** KRITIK — on-chain veri tahmin dogrulugunu ciddi artiriyor.

**6.** Tripathy, N. et al. (2024). "Revolutionizing BTC Price Forecasts: Hybrid Deep Learning." *Finance Research Letters*.
- **Bulgu:** LSTM-GRU hibrit ARIMA, XGBoost, saf LSTM'i geciyor (RMSE 0.323).
- **COIN Bot Ilgisi:** Hibrit ensemble mimarisi tek modelden her zaman iyi.

**7.** Chen, J. et al. (2024). "Deep Learning for BTC Price Direction Prediction." *Financial Innovation*, 10, 643.
- **Bulgu:** Transformer uzun vade, LSTM kisa vade icin iyi. Backtest'te buy-and-hold'u geciyor.
- **COIN Bot Ilgisi:** Tahmin ufkuna gore mimari sec.

**8.** Song, Y. et al. (2025). "BTC Price Prediction Using Enhanced Transformer and Greed Index." *IET Blockchain*.
- **Bulgu:** Fourier-wavelet ayristirma + Fear&Greed Index. Frekans domaininde tahmin daha basarili.
- **COIN Bot Ilgisi:** Fear&Greed Index'i feature olarak ekle.

**9.** Katsafados, A. et al. (2025). "Helformer: Attention-Based DL for Crypto Price Forecasting." *Journal of Big Data*, 12, 1135.
- **Bulgu:** Holt-Winters + Transformer. Trend/mevsimsellik ayristirmasi sonrasi attention.
- **COIN Bot Ilgisi:** Veriyi once ayristir, sonra modele ver.

---

## C. TRIPLE BARRIER VE FINANSAL ML

**10.** Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- **Bulgu:** Triple barrier labeling, meta-labeling, purged CV, information bars, fractional differencing.
- **COIN Bot Ilgisi:** TEMEL REFERANS — CPCV ve purging olmadan model gecersiz.

**11.** Bae, K. et al. (2024). "GA-Driven Triple Barrier for Crypto Pairs Trading." *Mathematics*, 12(5), 780.
- **Bulgu:** Genetik algoritma ile triple barrier parametre optimizasyonu. BTC-ETH pair trading'de statik bariyerlerden iyi.
- **COIN Bot Ilgisi:** Triple barrier parametrelerini otomatik optimize et.

**12.** Ata, S. et al. (2025). "Algorithmic Crypto Trading Using Information-Driven Bars and Triple Barrier." *Financial Innovation*, 11, 866.
- **Bulgu:** Volume bars, dollar bars + triple barrier + DL. Information-driven bars zaman barlarindan daha iyi.
- **COIN Bot Ilgisi:** KRITIK — tick data → volume bars → triple barrier → DL pipeline.

**13.** Easley, D., Lopez de Prado, M., & O'Hara, M. (2012). "The Volume Clock." *Journal of Portfolio Management*, 39(1), 19-29.
- **Bulgu:** VPIN (Volume-Synchronized Probability of Informed Trading) — bilgilendirilmis islem tespiti.
- **COIN Bot Ilgisi:** Hacim anomali tespitinde VPIN kullan.

---

## D. WALK-FORWARD VE BACKTEST

**14.** Gort, B.J.D. et al. (2023). "DRL for Crypto Trading: Practical Approach to Backtest Overfitting." *arXiv:2209.05559*.
- **Bulgu:** Overfitting'i hipotez testi ile tespit. Daha az overfit DRL modeller 2022 crash'inda basarili.
- **COIN Bot Ilgisi:** Overfitting detection sart.

**15.** Bailey, D.H. et al. (2024). "Backtest Overfitting in the ML Era." *Knowledge-Based Systems*.
- **Bulgu:** CPCV walk-forward'dan ustun. Deflated Sharpe Ratio daha iyi istatistik testi.
- **COIN Bot Ilgisi:** CPCV varsayilan validation yontemi olmali.

**16.** Wang, Y. et al. (2025). "Walk-Forward Validation for Market Microstructure Signals." *arXiv:2512.12924*.
- **Bulgu:** Walk-forward + coklu test duzeltmesi (Bonferroni, BH) birlestirmesi.
- **COIN Bot Ilgisi:** Sinyal kesfinde istatistiksel rigor.

---

## E. ON-CHAIN METRIKLER

**17.** Ramirez, P. et al. (2025). "BTC Price Direction Using On-Chain Data." *Expert Systems with Applications*.
- **Bulgu:** 196 on-chain feature (Glassnode). TCN ve CNN-LSTM ile. Aktif adres, exchange flow, miner metrikleri.
- **COIN Bot Ilgisi:** Glassnode API ile on-chain feature pipeline kur.

**18.** Luo, J. et al. (2024). "From On-Chain to Macro: Data Source Diversity in Crypto Forecasting." *VLDB FAB Workshop*.
- **Bulgu:** Coklu kaynak (on-chain + teknik + makro) tek kaynagi her zaman geciyor. On-chain 7-30 gun ufkunda en degerli.
- **COIN Bot Ilgisi:** Veri mimarisi karari — hangi kaynak hangi ufukta onemli.

**19.** Li, X., Liu, Y. et al. (2024). "Cryptocurrency Return Prediction: ML Analysis." *SSRN:4703167*.
- **Bulgu:** RF neural network'lerden iyi. SHAP analizi: MVRV orani ve adres metrikleri en onemli on-chain faktorler.
- **COIN Bot Ilgisi:** MVRV ratio ve adres metrikleri oncelikli feature'lar.

---

## F. VOLATILITE MODELLEME

**20.** Catania, L. & Grassi, S. (2022). "Forecasting Cryptocurrency Volatility." *International Journal of Forecasting*, 38(3), 878-894.
- **Bulgu:** HAR-RV intradayde GARCH'tan iyi. Signed bilgi ve jump bilesenleri tahminleri iyilestiriyor.
- **COIN Bot Ilgisi:** KRITIK — intraday icin HAR-RV, gunluk icin GARCH kullan.

**21.** Naimy, V. & Hayek, M. (2021). "Forecasting Crypto Volatility by GARCH and SV." *Mathematics*, 9(14), 1614.
- **Bulgu:** Bayesian SV modeli GARCH ailesini geciyor.
- **COIN Bot Ilgisi:** Risk modulu icin SV modelleri daha dogruu vol tahmini verebilir.

**22.** Segnon, M. & Bekiros, S. (2022). "HAR-GARCH with Jumps for BTC Realized Volatility." *Applied Economics*.
- **Bulgu:** BTC'de ters kaldırac etkisi (vol fiyat yukseldikce artar — hisselerinin tersi!). Jump modelleri basarili.
- **COIN Bot Ilgisi:** KRITIK BULGU — kripto'da ters kaldırac var, modeli buna adapte et.

**23.** Dong, Y. et al. (2025). "Probabilistic Forecasting Crypto Volatility." *arXiv:2508.15922*.
- **Bulgu:** HAR + GARCH + ARFIMA noktasal tahminleri + ML kuantil tahmini. Kuantil regresyon ormanlari saglam kuyruk risk tahmini.
- **COIN Bot Ilgisi:** Pozisyon boyutlandırma icin olasiliksal guven araliklarikz.

---

## G. EMIR DEFTERI VE PIYASA MIKRO YAPISI

**24.** Bieganowski, B. & Slepaczuk, R. (2026). "Explainable Patterns in Crypto Microstructure." *arXiv:2602.00776*.
- **Bulgu:** Emir akis dengesizligi, spread, bilgi asimetrisi feature'lari Binance Futures'ta kararlı onem gosteriyor. Feature kutuphanesi coinler arasi tasinabilir.
- **COIN Bot Ilgisi:** Kompakt, tasinabilir LOB feature seti — tum coinlerde calisir.

**25.** Makarov, I. & Schoar, A. (2020). "Trading and Arbitrage in Cryptocurrency Markets." *Journal of Financial Economics*, 135(2), 293-319.
- **Bulgu:** Borsalar arasi buyuk arbitraj firsatlari var. Ortak hacim bileseni BTC getirilerinin %80'ini aciklar.
- **COIN Bot Ilgisi:** Cross-exchange fiyat olusumu ve arbitraj sinirlamalarini anla.

**26.** Brauneis, A. et al. (2022). "Cryptocurrency Market Microstructure." *Annals of Operations Research*, 332, 1057-1092.
- **Bulgu:** 127 makale taramasi. Kripto mikro yapisi geleneksel piyasalardan temelden farkli (7/24, parca parca).
- **COIN Bot Ilgisi:** Kripto piyasa yapisinin hisse senedinden farkini anla.

---

## H. DUYGU ANALIZI (SENTIMENT)

**27.** Khedr, A. et al. (2025). "Deep Learning and NLP in Crypto Forecasting." *International Journal of Forecasting*.
- **Bulgu:** TikTok + Twitter sentiment entegrasyonu dogrulugu artiriyor. TikTok kisa vade, Twitter uzun vade.
- **COIN Bot Ilgisi:** Cok platformlu sentiment — sadece Twitter degil.

**28.** Nemes, L. & Kiss, A. (2024). "LLMs and NLP in Crypto Sentiment Analysis." *Big Data and Cognitive Computing*, 8(6), 63.
- **Bulgu:** Twitter-RoBERTa + BART MNLI birlesimi en yuksek dogruluk.
- **COIN Bot Ilgisi:** Sentiment modulu icin RoBERTa + BART onerisi.

**29.** Pano, T. & Kashef, R. (2020). "VADER-Based Sentiment Analysis of BTC Tweets." *Big Data and Cognitive Computing*, 4(4), 33.
- **Bulgu:** VADER sentiment kisa vadeli BTC hareketleriyle korelasyon gosteriyor. Influencer tweet'leri hareketi amplify ediyor.
- **COIN Bot Ilgisi:** VADER hafif ve hizli baseline sentiment motoru.

---

## I. REJIM TESPITI

**30.** Giudici, P. & Abu Hashish, I. (2020). "HMM to Detect Regime Changes in Cryptoassets." *Quality and Reliability Engineering*, 36(6), 2057-2065.
- **Bulgu:** 3 durumlu HMM (boga/stabil/ayi) BTC fiyat evrimini etkili acikliyor. Rejim gecisleri tahmin edilebilir.
- **COIN Bot Ilgisi:** TEMEL — rejim-duyarli trading stratejisi icin HMM uygula.

**31.** Nystrup, P. et al. (2024). "Regime Switching Forecasting for Cryptocurrencies." *Digital Finance*, 123.
- **Bulgu:** 4 durumlu NHHM en iyi tahmin. Makro degiskenler + sentiment gecis kovariyatlari olarak eklenmeli.
- **COIN Bot Ilgisi:** 4 durumlu model dis kovariyatlarla 2-3 durumlu modelden iyi.

**32.** Alemany, N. et al. (2025). "BTC Price Regime Shifts: Bayesian MCMC and HMM." *Mathematics*, 13(10), 1577.
- **Bulgu:** 16 makro/BTC faktorunden Fed politika faizi ve BTC hashrate en guclu rejim gecis suruculeri.
- **COIN Bot Ilgisi:** Rejim gecisinde hangi makro degiskenleri izlemeli — somut liste.

---

## J. RISK YONETIMI

**33.** Trucios, C. et al. (2020). "VaR and ES in Crypto Portfolio: Vine Copula." *Applied Economics*, 52(24), 2580-2593.
- **Bulgu:** Vine copula standart GARCH'tan ustun VaR/ES tahmini verir. Asimetrik kuyruk bagimliligini yakar.
- **COIN Bot Ilgisi:** Coklu coin portfoyunde vine copula risk olcumu.

**34.** Zhang, W. et al. (2024). "Crypto Portfolio Under CVaR Criterion." *Risks*, 12(10), 163.
- **Bulgu:** CVaR tabanli optimizasyon mean-variance'dan kripto icin daha iyi. Asiri kayiplara odaklanir.
- **COIN Bot Ilgisi:** KRITIK — kripto icin VaR degil CVaR kullan.

**35.** Genet, R. et al. (2022). "Portfolio Constructions: CVaR-Based DRL." *Economic Modelling*, 119, 106098.
- **Bulgu:** CVaR kisitlamali DRL mean-variance ve esit agirlikli portfoyleri geciyor. Kuyruk riskini onler.
- **COIN Bot Ilgisi:** DRL + CVaR kisitlamasi uretimde kullanilabilir risk yonetimi.

---

## K. YURUTME ALGORITMALARI

**36.** Genet, R. (2025). "Deep Learning for VWAP Execution in Crypto." *arXiv:2502.13722*.
- **Bulgu:** VWAP kaymasini dogrudan DL ile optimize etmek hacim tahmini uzerinden gitmekten daha iyi.
- **COIN Bot Ilgisi:** Buyuk emirler icin dogrudan uygulanabilir VWAP algoritmasi.

**37.** Makarov, I. & Schoar, A. (2020). "Trading and Arbitrage in Crypto Markets." *JFE*, 135(2), 293-319.
- **Bulgu:** Borsalar arasi buyuk tekrarlanan arbitraj firsatlari. Sermaye kontrolleri deviaasyonlari artiriyor.
- **COIN Bot Ilgisi:** Coklu borsa yurutme lojigi icin temel anlayis.

**38.** Barbon, A. & Ranaldo, A. (2024). "Quality of Crypto Markets: CEX vs DEX." *Management Science*.
- **Bulgu:** DEX sabit gas maliyetleri kucuk islemleri olumsuz etkiler. CEX spot ~15bps, DEX ~12bps.
- **COIN Bot Ilgisi:** Mekan secimi: kucuk emirler CEX, buyuk emirler potansiyel olarak DEX.

---

## L. TEMEL ARASTIRMACILAR

**39.** Liu, Y. & Tsyvinski, A. (2021). "Risks and Returns of Cryptocurrency." *Review of Financial Studies*, 34(6), 2689-2727.
- **Bulgu:** Kripto getirileri kriptoya ozgu faktorlerle surulur, hisse/doviz/emtia faktorleriyle DEGIL. Guclu momentum etkisi. Yatirimci dikkati (Google, Twitter) getirileri ongoruyor.
- **COIN Bot Ilgisi:** KRITIK — kripto momentum ve dikkat sinyalleri cekirdek feature olmali.

**40.** Liu, Y., Tsyvinski, A., & Wu, X. (2022). "Common Risk Factors in Cryptocurrency." *Journal of Finance*, 77(2), 1133-1177.
- **Bulgu:** 3 faktorlu model (piyasa, boyut, momentum) kripto kesitsel getirilerini acikliyor. Kripto icin Fama-French.
- **COIN Bot Ilgisi:** Faktor bazli sinyal yapisi ve performans atfi.

**41.** Harvey, C.R. et al. (2022). "An Investor's Guide to Crypto." *SSRN:4124576*.
- **Bulgu:** Kripto taksonomi, degerleme yaklasimlari, risk degerlendirmesi, portfoy entegrasyonu cercevesi.
- **COIN Bot Ilgisi:** Coklu varlik trading botu tasarimi icin stratejik genel bakis.

**42.** Makarov, I. & Schoar, A. (2022). "Cryptocurrencies and DeFi." *NBER Working Paper 30006*.
- **Bulgu:** DeFi vergi/AML zorluklari. BTC ekosistemi buyuk yogun oyuncular tarafindan domine ediliyor.
- **COIN Bot Ilgisi:** Yogunlasma riski ve karsi taraf dinamiklerini anla.

---

## M. TAKVIYELI OGRENME (RL)

**43.** Kim, J. et al. (2024). "RL-Based Crypto Portfolio Management Using SAC and DDPG." *arXiv:2511.20678*.
- **Bulgu:** SAC (Soft Actor-Critic) DDPG ve klasik MPT'yi geciyor. LSTM-gelismis durum temsili.
- **COIN Bot Ilgisi:** Kripto portfoy yonetimi icin SAC + LSTM tercih edilen DRL algoritmasi.

**44.** Sattarov, O. et al. (2023). "Combining DRL with Technical Analysis for Crypto." *Neural Computing and Applications*, 35, 12509-12526.
- **Bulgu:** PPO/A2C + teknik trend filtreleri kararlıligi artiriyor, drawdown'u azaltiyor. Trend izleme meta-filtre.
- **COIN Bot Ilgisi:** Kural bazli trend filtreleri + DRL ajanları hibrit mimari.

---

## N. PAIRS TRADING VE ISTATISTIKSEL ARBITRAJ

**45.** Tadi, M. & Koshiyama, A. (2024). "Copula-Based Trading of Cointegrated Crypto Pairs." *Financial Innovation*, 11, 702.
- **Bulgu:** Copula yontemi BTC-ETH pair trading'de yillik %16.34 getiri. Dogrusal koentegrasyondan iyi.
- **COIN Bot Ilgisi:** Dogrudan uygulanabilir pairs trading stratejisi.

**46.** Palazzi, R. et al. (2025). "Trading Games: Beating Passive Strategies in Bullish Crypto." *Journal of Futures Markets*.
- **Bulgu:** Pairs trading boga piyasasinda bile buy-and-hold'u geciyor (2019-2024, 10 kripto).
- **COIN Bot Ilgisi:** Stat arb kripto'da hala karli.

---

## O. GRAF NEURAL AGLAR

**48.** Chen, Z. et al. (2025). "Forecasting Crypto Volatility: Evolving Multiscale GNN." *Financial Innovation*, 768.
- **Bulgu:** Evrilen GNN kripto-geleneksel piyasa etkilesimlerini yakalıyor. Hiyerarsik grafik yapisi.
- **COIN Bot Ilgisi:** Piyasalar arasi dinamikleri yakalamak icin yeni mimari.

**49.** Wen, X. et al. (2025). "GNN and Meta-Learning for Crypto Price Prediction." *IEEE Blockchain*.
- **Bulgu:** GNN + meta-ogrenme sinirli verili yeni/dusuk likidite tokenlara hizli adaptasyon saglar.
- **COIN Bot Ilgisi:** Az verili altcoinlere genislemek icin faydali.

---

## P. TURKIYE OZEL ARASTIRMALAR

**50.** Karadeniz, S. (2021). "Cryptocurrencies and Borsa Istanbul: Before and After COVID." *Istanbul Bilgi Universitesi Yuksek Lisans Tezi*.
- **Bulgu:** COVID sonrasi kripto-BIST korelasyonu artmis → diversifikasyon faydasi azalmis.
- **COIN Bot Ilgisi:** Hem BIST hem kripto tutan Turk yatirimcilari icin dogrudan ilgili.

**51.** DergiPark (2025). "BTC Trend Reversal Prediction with Tree-Based Ensemble ML." *Turkish Journal of Forecasting*.
- **Bulgu:** XGBoost, RF kripto trend donusu tespitinde basarili. Yerel dogrulanmis ML yaklasimlari.

**52.** DergiPark (2025). "Volatility Modelling of Cryptocurrencies: BTC." *Makuiibf Journal*.
- **Bulgu:** LSTM-GARCH hibrit cok ufuklu kripto volatilite tahmini. Yatirim ufku model secimini etkiliyor.

**Regulasyon Notu:** Turkiye'de Kanun No. 7518 (Temmuz 2024) ilk kripto yasal cercevesini kurdu. SPK ve MASAK duzenliyor. Turkiye hacim bazinda dunyanin 4. buyuk kripto piyasasi (2024). Kripto odemeleri Nisan 2021'den beri yasak ama islem/sahiplik yasal.

---

## OZET: COIN BOT ICIN ONCELIKLI UYGULAMALAR

| Metodoloji | En Iyi Referans | Bot Tasarim Karari |
|---|---|---|
| ML Model Secimi | Jabbar (2024) [P2] | RF ve SGD; 40+ model test et |
| DL Mimari | Zhang (2023) [P1] | LSTM baskin; hibrit yaklasmlar kazanir |
| Triple Barrier | Ata (2025) [P12] | Info-driven bars + triple barrier |
| Validation | Bailey (2024) [P15] | CPCV walk-forward'dan ustun |
| On-Chain | Omole (2025) [P5] | 225 feature; Boruta secim |
| Volatilite | Catania (2022) [P20] | Intraday: HAR-RV, gunluk: GARCH |
| Emir Defteri | Bieganowski (2026) [P24] | Tasinabilir LOB feature seti |
| Sentiment | Khedr (2025) [P27] | Cok platformlu NLP birlestirme |
| Rejim Tespiti | Nystrup (2024) [P31] | 4 durumlu NHHM makro kovariyatlarla |
| Risk Yonetimi | Zhang (2024) [P34] | CVaR > VaR kripto icin |
| Yurutme | Genet (2025) [P36] | Dogrudan VWAP optimizasyonu DL ile |
| Faktor Model | Liu (2022) [P40] | Kripto 3 faktor: piyasa, boyut, momentum |
| DRL | Kim (2024) [P43] | SAC + LSTM portfoy yonetimi |
| Pairs Trading | Tadi (2024) [P45] | Copula bazli koentegrasyon |
