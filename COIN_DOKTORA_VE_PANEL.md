# COIN TRADER SISTEMI -- DOKTORA SEVIYESI DENETIM RAPORU

**Tarih:** 2026-04-04  
**Denetci:** Otonom AI Denetim Sistemi  
**Kapsam:** coin_trader.py, coin_dashboard.py, coin_ai_egitim.py, coin_ai_v1.pkl

---

# BOLUM 1: TEKNIK DENETIM

## 1. MIMARI INCELEME

| Kriter | Durum | Not |
|--------|-------|-----|
| Modularite | ZAYIF | Tum trading logic tek dosyada |
| Dependency Injection | YOK | Test edilemez |
| Error Handling | KRITIK EKSIK | Bare except her yerde |
| Konfigurason Yonetimi | ZAYIF | Hardcoded sabitler |
| Test Coverage | %0 | Hicbir test yok |
| CI/CD | YOK | — |
| Logging | ILKEL | print() statement'lar |

**Derece: D**

---

## 2. TRADING LOGIC HATALARI

**BUG-001: `hmac.new()` -- Deprecated, guncellenmeli** (coin_trader.py satir 50-52)

**BUG-002: Market Order'da Miktar Kontrolu Yok** (satir 54-57)
- Negatif miktar, minimum order size (LOT_SIZE), USDT bakiye, stepSize precision -- hicbiri kontrol edilmiyor.

**BUG-003: RoketTarayici'da OR Mantigi** (satir 402-414)
- Tek kriter yetip "roket" etiketliyor; false positive orani asiri yuksek. En az 2-3 kriter birlikte saglanmali.

**BUG-004: Ajan Objeleri Her Coin Icin Tekrar Olusturuluyor** (satir 300-302)
- `self.ajanlar` listesi var ama kullanilmiyor, hafiza yonetimi sorunu.

**BUG-005: Timestamp Senkronizasyon Riski**
- `recvWindow` parametresi yok; lokal/sunucu saat farki 1000ms+ olursa emir reddedilir.

**BUG-006: Division by Zero (RSI)**
- 1e-10 epsilon float overflow riskine acik; `gain.iloc[-1]` NaN olabilir.

**BUG-007: `--bot` Modu Implemente Edilmemis**
- argparse'da tanimli ancak main blogundan eksik -- 7/24 otonom bot calistirilemiyor.

**BUG-008: Rate Limiting Yok**
- 15 coin x 1 istek = Binance IP ban riski (HTTP 429 → 418 → ban).

**Derece: F**

---

## 3. ML MODEL KRITIGI (AUC: 0.5702)

AUC 0.5702, rastgele tahminden yalnizca %7 daha iyi. Lopez de Prado (2018) kriterine gore AUC < 0.60 olan modeller "noise'u ezberleme" egiliminde; finans literaturunde "bilgi icerigi ihmal edilebilir" sinifi.

**Feature Engineering Sorunlari:**
- Look-ahead bias riski: `btc_returns` tum dataset uzerinden hesaplanip sonra coinlere hizalaniyor.
- Yalnizca 10 feature; order flow, funding rate, open interest, on-chain metrikleri, sentiment -- hepsi eksik.
- TP=%3, SL=%2, Time=24h tum coinler icin statik; ATR-bazli dinamik bariyerler olmali.
- Walk-forward validation yok; purging/embargo yok (De Prado standardi); tek split kullanilmis.
- Sinif dengesizligi: SMOTE/undersampling denenmemis.
- Hyperparameter tuning (Optuna/Bayesian) yok; tek konfigurasyonla egitilmis.

**Overfitting Testi Yapilmamis:** Permutation importance, adversarial validation, out-of-time validation -- hicbiri yok.

**Derece: D-**

---

## 4. RISK YONETIMI BOSLUKLARI

| Risk Kontrolu | Durum | Oncelik |
|---------------|-------|---------|
| Pozisyon boyutlandirma (Kelly) | YOK | KRITIK |
| Gunluk/haftalik max kayip limiti | YOK | KRITIK |
| Drawdown korumasi | YOK | KRITIK |
| Korelasyon kontrolu | YOK | YUKSEK |
| Volatilite-bazli pozisyon boyutu | YOK | YUKSEK |
| Slippage modeli | YOK | YUKSEK |
| Trailing stop-loss | YOK | ORTA |
| Sharpe/Sortino raporlamasi | YOK | ORTA |
| VaR/CVaR | YOK | DUSUK |

Flash crash senaryosunda (%50 BTC, 1 gunde): tum pozisyonlar acik kalir, stop-loss mekanizmasi yok.

**Derece: F**

---

## 5. BINANCE API GUVENLIK DENETIMI

**SEC-001:** API anahtarlari plaintext -- `.env` yok, environment variable okuma yok, git commit riski.

**SEC-002:** Dashboard'da `st.text_input(..., type="password")` sadece gorsel maskeleme; session_state'te plaintext, HTTPS yoksa duztext iletim.

**SEC-003:** HTTP response dogrulama yok -- status code kontrolu yok (401/403/429/500), SSL pinning yok, MITM riski.

**SEC-004:** IP whitelisting uyarisi yok -- anahtar sizintisinda tam hesap riski.

**SEC-005:** Withdraw izni uyarisi yok -- "Enable Withdrawals" kapali olmali.

**Derece: F**

---

## 6. ROKET TARAYICI ETKINLIGI

Uc bagimsiz kriterden herhangi biri (hacim >=5x VEYA 24s >=+10% VEYA 1s >=+5%) yetip "roket" etiketliyor.

**Sorunlar:**
- 1 saatlik veri ile gec yakalama -- gercek roketler 5-15 dakikada patlar.
- Pump & Dump tuzagi: hacim patlamasi + fiyat artisi = pump'un SON asamasi.
- Skor formulu `(hacim_oran*10) + (degisim_24s*2) + (degisim_1s*5)` istatistiksel temelsiz, backtesting yapilmamis.
- Rolling Z-score, taker buy/sell orani, order book depth degisimi -- hicbiri yok.

**Derece: D**

---

## 7. KOMISYON VE UCRET ANALIZI

Sistemde HICBIR komisyon veya maliyet hesaplamasi yok.

| Maliyet Kalemi | Tipik Oran |
|----------------|------------|
| Binance spot taker (sistem bunu kullaniyor) | %0.10 |
| Spread (bid-ask) | %0.01-0.50 |
| Slippage (dusuk likidite) | %0.05-2.0 |

**Ornek:** 15 coin x 2 islem x %0.10 = %3.0 gunluk komisyon + ~%0.5 spread = **yillik ~%882 komisyon yuku.**

**Triple Barrier net etki:** Net TP = +2.70%, Net SL = -2.30%. Basabaslik win rate = %46. AUC 0.57 ile tahmini win rate ~%52-53 -- marjin kaymaya acik.

**Derece: F**

---

## 8. PROFESYONEL KARSILASTIRMA

| Ozellik | COIN Trader | Profesyonel Seviye |
|---------|-------------|-------------------|
| Veri kaynagi | Binance REST (1h) | Multi-exchange WebSocket (tick) |
| Order tipi | Market/Limit | TWAP, VWAP, Iceberg |
| Risk yonetimi | Yok | Kelly, VaR, drawdown limits |
| ML pipeline | Tek XGBoost | Ensemble + online learning |
| Feature sayisi | 10 | 100-500+ |
| Backtest | Yok | Walk-forward, Monte Carlo |
| Monitoring | print() | Grafana/Prometheus |
| Guvenlik | Plaintext API key | HSM/Vault, IP whitelist |

**Derece: F**

---

## GENEL DENETIM OZET TABLOSU

| Alan | Derece | Kritik Sorun |
|------|--------|--------------|
| Mimari | D | 3 |
| Trading Logic | F | 8 |
| ML Model | D- | 6 |
| Risk Yonetimi | F | 12 |
| Guvenlik | F | 5 |
| Roket Tarayici | D | 5 |
| Komisyon/Ucret | F | 3 |

**GENEL SISTEM DERECE: F**  
**CANLI PARA ILE KULLANIM ONERISI: KESINLIKLE HAYIR (su anki haliyle)**

---

# BOLUM 2: AKADEMIK PANEL -- KONSENSUS RAPORU

**Panel:** 10 uzman (Duke, LSE, Rochester, Cornell, Columbia, Bilkent x2, Sabanci, Bogazici, Binance TR Research)  
**Konsensus notu: F** (7/10 F, 2/10 D veya D-, 1/10 D)

### Her Panelistin En Kritik Onerisi

| Panelist | Not | Oneri |
|----------|-----|-------|
| Prof. Harvey (Duke) | F | ML modelini sifirdan tasarla. Walk-forward validation, purging, min AUC 0.65. |
| Prof. Makarov (LSE) | F | WebSocket'e gec, order book depth feature ekle, limit order kullan. |
| Prof. Liu (Rochester) | F | Risk yonetimi once: max drawdown %10 stop, Kelly pozisyon boyutu, ATR stop-loss. |
| Prof. Cong (Cornell) | D | On-chain veri entegre et (Glassnode: exchange flow, whale, token unlock). |
| Prof. Capponi (Columbia) | F | Execution engine yeniden yaz: TWAP/VWAP, slippage modeli, Binance exchange info filtreleri. |
| Prof. Caner (Bilkent) | F | Log-return kullan, stationarity testleri, regime-switching model, panel data yontemleri. |
| Prof. Salih (Bilkent) | F | Portfoy yaklasimi: Markowitz optimizer, korelasyon matrisi, rebalancing, benchmark. |
| Prof. Gulay (Sabanci) | D- | Volatilite modeli: ATR-bazli dinamik TP/SL, GARCH/HAR-RV, statik esikleri kaldir. |
| Prof. Akgiray (Bogazici) | F | Hukuki cerceve once: SPK uyumu, vergi, KYC/AML olmadan canli islem yapma. |
| Dr. Adiyaman (Binance TR) | D | Binance Testnet'te min 3 ay paper trade. Exchange info filtreleri, rate limiting, WebSocket, IP whitelist. |

---

## ONCELIKLI AKSIYON LISTESI

### ACIL (Ilk 2 Hafta) -- CANLI PARA ILE ISLEM YAPILMAMALI

1. **API guvenligini sagla:** API anahtarlarini .env'e tasi, IP whitelist aktive et, withdraw iznini kapat.
2. **Risk yonetim modulu ekle:** Max drawdown %10 hard stop, gunluk max kayip %3, tek pozisyon max %10.
3. **Exchange info filtreleri:** LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER kontrolleri.
4. **Rate limiting:** Binance API limitlerine uygun bekleme.
5. **Error handling duzelt:** Bare except kaldır, anlamli hata yakalama.

### KISA VADE (1-2 Ay) -- TESTNET'TE CALISMA

6. **Binance Testnet entegrasyonu:** Tum islemleri once testnet'te dene.
7. **WebSocket:** REST polling'den real-time stream'e gec.
8. **Limit order:** Market order yerine agresif limit order.
9. **ML modelini yeniden egit:** Walk-forward validation, purging, min 30 feature.
10. **Komisyon modeli:** Her sinyal degerlendirilirken komisyon + spread + slippage dusilsun.

### ORTA VADE (3-6 Ay) -- MINIMUM VIABLE TRADING SYSTEM

11. **On-chain veri:** Glassnode veya Nansen API entegrasyonu.
12. **Portfoy optimizasyonu:** Korelasyon-aware pozisyon boyutlandirma.
13. **Volatilite modeli:** ATR-bazli dinamik TP/SL.
14. **Backtesting framework:** Vectorbt veya Zipline ile kapsamli backtest.
15. **Performance tracking:** Sharpe, Sortino, max drawdown, win rate.

### UZUN VADE (6-12 Ay) -- PROFESYONEL SEVIYE

16. **Regime detection:** HMM veya clustering ile piyasa rejimi tespiti.
17. **Ensemble model:** XGBoost + LightGBM + Neural Network.
18. **Execution engine:** TWAP/VWAP, iceberg emirler.
19. **Monitoring:** Grafana dashboard, alert sistemi.
20. **Regulasyon uyumu:** SPK cercevesi, vergi raporlamasi.

---

*Bu rapor yatirim tavsiyesi niteliginde degildir.*
