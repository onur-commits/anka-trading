# COIN TRADER — Akademik Literatur Raporu (52 Makale)

**Tarih:** 9 Nisan 2026
**Kapsam:** Kripto algoritmik ticaret, ML/DL, on-chain metrikler, volatilite, risk yonetimi
**Kaynak:** Google Scholar, arXiv, SSRN, NBER, IEEE, DergiPark, Financial Innovation, Journal of Finance

---

## A. ANKETLER VE KAPSAMLI INCELEMELER
[P1] Zhang et al. (2023) *iScience* — CNN/RNN/DBN/DRL karsilastirmasi; LSTM baskin, hibrit mimariler daha iyi. | [P2] Jabbar & Jalil (2024) *arXiv:2407.18334* — 41 ML modeli; RF ve SGD en iyi Sharpe/karlilik. | [P3] Fang et al. (2022) *Financial Innovation* — 146 makale taramasi; tam kripto sistem haritasi. | [P4] Akyildirim et al. (2021) *Annals of OR* — SVM/LR/ANN/RF; teknik indikatorlerle yon tahmini %55+.

## B. MAKINE OGRENMESI VE DERIN OGRENME
[P5] Omole & Enke (2025) *Eng. Appl. AI* — Boruta-CNN-LSTM; 225 feature (92 on-chain + 138 teknik); %82.44 dogruluk → on-chain veri tahmini ciddi artiriyor. | [P6] Tripathy et al. (2024) *Finance Research Letters* — LSTM-GRU hibrit; ARIMA/XGBoost'u geciyor (RMSE 0.323). | [P7] Chen et al. (2024) *Financial Innovation* — Transformer uzun vade, LSTM kisa vade; backtest'te B&H'u geciyor. | [P8] Song et al. (2025) *IET Blockchain* — Fourier-wavelet + Fear&Greed Index; F&G'yi feature olarak ekle. | [P9] Katsafados et al. (2025) *Journal of Big Data* — Holt-Winters + Transformer; once trend/mevsimsellik ayristir, sonra modele ver.

## C. TRIPLE BARRIER VE FINANSAL ML
[P10] Lopez de Prado (2018) *Advances in Financial ML* — Triple barrier, meta-labeling, purged CV, info bars, fractional differencing → TEMEL REFERANS; CPCV ve purging olmadan model gecersiz. | [P11] Bae et al. (2024) *Mathematics* — Genetik algoritma ile triple barrier parametre optimizasyonu; statik bariyerlerden iyi. | [P12] Ata et al. (2025) *Financial Innovation* — Volume/dollar bars + triple barrier + DL → KRITIK pipeline. | [P13] Easley et al. (2012) *JPM* — VPIN: hacim senkronize bilgilendirilmis islem tespiti.

## D. WALK-FORWARD VE BACKTEST
[P14] Gort et al. (2023) *arXiv:2209.05559* — Overfitting hipotez testi; az overfit DRL 2022 crash'inda basarili. | [P15] Bailey et al. (2024) *Knowledge-Based Systems* — CPCV walk-forward'dan ustun; Deflated Sharpe daha iyi test istatistigi → varsayilan validation. | [P16] Wang et al. (2025) *arXiv:2512.12924* — Walk-forward + Bonferroni/BH coklu test duzeltmesi.

## E. ON-CHAIN METRIKLER
[P17] Ramirez et al. (2025) *Expert Syst. Appl.* — 196 on-chain feature (Glassnode); TCN ve CNN-LSTM; aktif adres, exchange flow, miner metrikleri → Glassnode API pipeline kur. | [P18] Luo et al. (2024) *VLDB FAB* — On-chain+teknik+makro kombinasyonu tek kaynagi geciyor; on-chain 7-30 gun ufkunda en degerli. | [P19] Li et al. (2024) *SSRN:4703167* — RF; SHAP: MVRV orani ve adres metrikleri en onemli feature.

## F. VOLATILITE MODELLEME
[P20] Catania & Grassi (2022) *Intl. J. Forecasting* — HAR-RV intraday'de GARCH'tan iyi → KRITIK: intraday HAR-RV, gunluk GARCH. | [P21] Naimy & Hayek (2021) *Mathematics* — Bayesian SV modeli GARCH ailesini geciyor. | [P22] Segnon & Bekiros (2022) *Applied Economics* — BTC'de ters kaldirac etkisi; jump modelleri basarili → KRITIK: kripto'da ters kaldirac var. | [P23] Dong et al. (2025) *arXiv:2508.15922* — HAR+GARCH+ARFIMA + ML kuantil RF; pozisyon boyutlandirma icin olasiliksal guven araliklari.

## G. EMIR DEFTERI VE PIYASA MIKRO YAPISI
[P24] Bieganowski & Slepaczuk (2026) *arXiv:2602.00776* — Emir akis dengesizligi, spread, bilgi asimetrisi; Binance Futures'ta kararli; coinler arasi tasinabilir → kompakt LOB feature seti. | [P25] Makarov & Schoar (2020) *JFE* — Borsalar arasi buyuk arbitraj; ortak hacim bileseni BTC getirilerinin %80'ini aciklar. | [P26] Brauneis et al. (2022) *Annals of OR* — 127 makale; kripto mikro yapisi geleneksel piyasadan temelden farkli (7/24, parca parca).

## H. DUYGU ANALIZI (SENTIMENT)
[P27] Khedr et al. (2025) *Intl. J. Forecasting* — TikTok kisa vade, Twitter uzun vade; cok platformlu sentiment gerekli. | [P28] Nemes & Kiss (2024) *BDCC* — RoBERTa + BART MNLI en yuksek dogruluk. | [P29] Pano & Kashef (2020) *BDCC* — VADER kisa vadeli BTC hareketi korelasyonu; hafif ve hizli baseline.

## I. REJIM TESPITI
[P30] Giudici & Abu Hashish (2020) *QRE* — 3 durumlu HMM (boga/stabil/ayi); rejim gecisleri tahmin edilebilir → TEMEL. | [P31] Nystrup et al. (2024) *Digital Finance* — 4 durumlu NHHM + makro/sentiment kovariyatlari en iyi. | [P32] Alemany et al. (2025) *Mathematics* — Fed faizi ve BTC hashrate en guclu rejim suruculeri.

## J. RISK YONETIMI
[P33] Trucios et al. (2020) *Applied Economics* — Vine copula VaR/ES; asimetrik kuyruk bagimliligi. | [P34] Zhang et al. (2024) *Risks* — CVaR tabanli optimizasyon kripto icin mean-variance'dan iyi → KRITIK: CVaR kullan. | [P35] Genet et al. (2022) *Economic Modelling* — CVaR kisitlamali DRL mean-variance ve esit agirlikli portfoyleri geciyor.

## K. YURUTME ALGORITMALARI
[P36] Genet (2025) *arXiv:2502.13722* — VWAP kaymasini dogrudan DL ile optimize et; hacim tahmininden iyi. | [P37] Makarov & Schoar (2020) *JFE* — Borsalar arasi tekrarlayan arbitraj; sermaye kontrolleri deviasyonlari artiriyor. | [P38] Barbon & Ranaldo (2024) *Management Science* — CEX spot ~15bps, DEX ~12bps; kucuk emirler CEX, buyuk emirler DEX.

## L. TEMEL ARASTIRMACILAR
[P39] Liu & Tsyvinski (2021) *RFS* — Kripto momentum ve Google/Twitter dikkat sinyalleri getirileri ongoruyor → KRITIK cekirdek feature. | [P40] Liu, Tsyvinski & Wu (2022) *JF* — 3 faktorlu model (piyasa, boyut, momentum); kripto Fama-French. | [P41] Harvey et al. (2022) *SSRN:4124576* — Kripto taksonomi, degerleme, risk, portfoy entegrasyonu cercevesi. | [P42] Makarov & Schoar (2022) *NBER WP30006* — DeFi zorluklar; BTC ekosistemi yogun oyuncular tarafindan domine.

## M. TAKVIYELI OGRENME (RL)
[P43] Kim et al. (2024) *arXiv:2511.20678* — SAC, DDPG ve MPT'yi geciyor; LSTM gelismis durum temsili → SAC+LSTM tercih edilen DRL. | [P44] Sattarov et al. (2023) *Neural Comput. Appl.* — PPO/A2C + teknik trend filtreleri; drawdown azaliyor → kural bazli trend filtresi + DRL hibrit.

## N. PAIRS TRADING VE ISTATISTIKSEL ARBITRAJ
[P45] Tadi & Koshiyama (2024) *Financial Innovation* — Copula BTC-ETH pair trading yillik %16.34; dogrusal koentegrasyondan iyi → dogrudan uygulanabilir. | [P46] Palazzi et al. (2025) *J. Futures Markets* — Pairs trading boga piyasasinda da B&H'u geciyor (2019-2024, 10 kripto).

## O. GRAF NEURAL AGLAR
[P48] Chen et al. (2025) *Financial Innovation* — Evrilen GNN; kripto-geleneksel piyasa etkilesimleri; hiyerarsik grafik yapisi. | [P49] Wen et al. (2025) *IEEE Blockchain* — GNN + meta-ogrenme; sinirli verili yeni/dusuk likidite tokenlara hizli adaptasyon.

## P. TURKIYE OZEL ARASTIRMALAR
[P50] Karadeniz (2021) *Istanbul Bilgi U. Tezi* — COVID sonrasi kripto-BIST korelasyonu artmis; diversifikasyon faydasi azalmis. | [P51] DergiPark (2025) *Turkish Journal of Forecasting* — XGBoost/RF kripto trend donusu tespitinde basarili. | [P52] DergiPark (2025) *Makuiibf Journal* — LSTM-GARCH hibrit cok ufuklu volatilite; yatirim ufku model secimini etkiliyor.

**Regulasyon Notu:** Kanun No. 7518 (Temmuz 2024) ilk kripto yasal cercevesi; SPK ve MASAK duzenliyor. Turkiye dunyanin 4. buyuk kripto piyasasi (2024). Kripto odemeleri Nisan 2021'den beri yasak, islem/sahiplik yasal.

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
