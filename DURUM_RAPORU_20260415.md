# ANKA Trading Sistemi — Tam Durum Raporu
**Tarih:** 15 Nisan 2026, 17:45
**Hazırlayan:** Claude (Direktör AI)
**CEO:** Ahmet Onur Bodur

---

## 1. SİSTEM MİMARİSİ

### 1.1 Altyapı
- **VPS:** Windows Server 2022, IP: 78.135.87.29
- **Python:** 3.12.8
- **Lokal geliştirme:** macOS, ~/Desktop/ANKA
- **GitHub:** https://github.com/onur-commits/anka-trading.git

### 1.2 Çalışan Servisler (VPS)

| Servis | Port/Tip | Durum | Açıklama |
|--------|----------|-------|----------|
| ANKA_BistDashboard | :8501 (Streamlit) | RUNNING | BIST ana dashboard + ANKA Danışman |
| ANKA_CoinDashboard | :8502 (Streamlit) | RUNNING | Crypto dashboard |
| ANKA_CoinBot | Background | RUNNING | 7/24 coin otonom trading botu |
| ANKA_Watchdog | Background | RUNNING | Her 5dk dashboard sağlık kontrolü, düşeni yeniden başlatır |
| ANKA_FeedbackRapor | Scheduled 18:30 | READY | Günlük ML tahmin sonuç kontrolü |
| ANKA_Orkestra | Scheduled | READY | Sistem orkestrasyon servisi |
| ANKA_Sabah_Hatirlatma | Scheduled | READY | Sabah bildirimleri |
| ANKA_Saat_Duzelt | Scheduled | READY | VPS saat senkronizasyonu |

### 1.3 Dosya Yapısı (56 Python dosyası)

**Çekirdek modüller:**
- `tahmin_motoru_v2.py` — ML ensemble model (XGBoost + LightGBM + MLP), 80+ teknik feature, walk-forward CV
- `makro_veri.py` — **[YENİ]** TCMB EVDS + yfinance makro veri katmanı (28 feature)
- `rejim_modeller.py` — **[YENİ]** Bull/bear/sideways rejim-bazlı uzman modeller
- `feedback_loop.py` — **[YENİ]** Tahmin kayıt + sonuç kontrolü + performans raporu
- `bist100.py` — **[YENİ]** BIST100 hisse listesi (91 ticker, ~85'i aktif)

**Trading botları:**
- `coin_otonom.py` — Binance coin trading botu (18 coin, 10dk tarama, stop-loss %3)
- `otonom_trader.py` — BIST zamanlı görevler (05:30 ML eğitim, 08:30 tarama)
- `alpha_v2_bot.py` — BIST Alpha V2 bot modu
- `gunluk_bomba.py` — Günlük bomba hisse bulucu + IQ robot kodu üretici

**Dashboard ve UI:**
- `app.py` — BIST Streamlit dashboard (port 8501)
- `coin_dashboard.py` — Coin Streamlit dashboard (port 8502)
- `anka_beyin.py` — Katmanlı piyasa analiz motoru (trend, volatilite, likidite, duygu)

**Analiz araçları:**
- `haber_ajan.py`, `haber_sentiment.py` — Haber toplama ve sentiment analizi
- `anka_scanner.py`, `sabah_scanner.py`, `hibrit_scanner.py` — Hisse tarama motorları
- `risk_yonetimi.py` — Pozisyon boyutlandırma ve risk kontrolü
- `anka_karar_verici.py` — Çok katmanlı karar verme sistemi

---

## 2. ML MODEL DURUMU

### 2.1 Model Evrimi (Kronolojik)

| Tarih | Model | AUC | WF AUC | Precision | Not |
|-------|-------|-----|--------|-----------|-----|
| 06-04-2026 | Ensemble V2 (sadece teknik) | 0.5664 | ~0.57 | 0.5316 | Yazı-turaya yakın |
| 15-04-2026 | + Makro Faz 1 (30 hisse) | 0.7166 | 0.767 | 0.7318 | İlk makro test |
| 15-04-2026 | + BIST100 (85 hisse) | **0.7255** | **0.759** | **0.6986** | **Canlı model** |

**Toplam iyileşme: AUC +0.16 (yazı-turadan profesyonel seviyeye)**

### 2.2 Aktif Model: Ensemble V2 + Makro (ensemble_v2.pkl)

- **Eğitim tarihi:** 15 Nisan 2026, 17:38
- **Mimari:** XGBoost (w:0.335) + LightGBM (w:0.334) + MLP Neural Net (w:0.331)
- **Eğitim verisi:** 21,161 satır, 85 BIST100 hissesi, 2 yıllık veri
- **Feature sayısı:** 100 ham feature → korelasyon filtresi → XGBoost importance → **25 seçilmiş**
- **Hedef:** Triple Barrier Method (5 gün pencere, +%2 TP, -%1.5 SL)
- **Validasyon:** Purged Walk-Forward CV, 50 fold, 10 gün purge

**Test metrikleri:**
- Ensemble AUC: 0.7255
- F1 Score: 0.695
- Precision: 0.699
- Walk-Forward ortalama AUC: 0.759 (min: 0.667, max: 0.864)

**Top 15 Feature (importance sırasıyla):**

| # | Feature | Importance | Kaynak |
|---|---------|------------|--------|
| 1 | usdtry_trend | 0.0668 | TCMB EVDS + yfinance |
| 2 | usdtry_degisim_5g | 0.0563 | TCMB EVDS + yfinance |
| 3 | eurtry_degisim_5g | 0.0519 | TCMB EVDS + yfinance |
| 4 | xu100_trend | 0.0514 | yfinance |
| 5 | xu100_vol_20g | 0.0486 | yfinance |
| 6 | usdtry_degisim_20g | 0.0461 | TCMB EVDS + yfinance |
| 7 | xu100_degisim_20g | 0.0450 | yfinance |
| 8 | usdtry_vol_10g | 0.0444 | TCMB EVDS + yfinance |
| 9 | xu100_degisim_5g | 0.0443 | yfinance |
| 10 | vix_degisim_5g | 0.0431 | yfinance |
| 11 | petrol_degisim_5g | 0.0429 | yfinance |
| 12 | altin_degisim_5g | 0.0419 | yfinance |
| 13 | usdtry_degisim_1g | 0.0412 | TCMB EVDS + yfinance |
| 14 | vix | 0.0402 | yfinance |
| 15 | altin_degisim_20g | 0.0395 | yfinance |

**Kritik bulgu:** Top 15 feature'ın 15'i de makro. Teknik indikatörler (RSI, MACD, Bollinger vb.) artık ilk 15'e bile giremiyor. BIST dış etkenlere aşırı hassas bir piyasa.

### 2.3 Rejim-Bazlı Modeller (rejim_modeller_v3.pkl)

Her rejim için ayrı XGBoost + LightGBM ensemble:

| Rejim | AUC | F1 | Precision | Veri Boyutu | Top Feature |
|-------|-----|----|-----------|-------------|-------------|
| **Bear** | **0.766** | 0.720 | **0.728** | 6,249 | xu100_degisim_5g |
| Bull | 0.692 | 0.685 | 0.677 | 10,608 | usdtry_degisim_5g |
| Sideways | 0.696 | 0.604 | 0.621 | 4,304 | xu100_vol_20g |

**Bear modeli en güçlü** — düşüş dönemlerinde %73 precision (SAT dediğinde gerçekten düşüyor).

Her rejimin kendi optimal feature seti var:
- **Bull:** Döviz değişimi, DXY trend, S&P500 (global risk iştahı önemli)
- **Bear:** XU100 momentum, VIX, petrol (korku ve emtia baskısı)
- **Sideways:** XU100 volatilite, VIX değişimi, altın (güvenli liman akışları)

### 2.4 Piyasa Rejimi (Anlık)

```
Rejim: BULL
Güven: %84.7
ADX: 42.3 (güçlü trend)
Volatilite: %25.1
SMA20 uzaklık: +%7.86
```

---

## 3. VERİ KAYNAKLARI

### 3.1 Makro Veri Katmanı (makro_veri.py)

**yfinance (8 kaynak, her zaman aktif):**

| Veri | Sembol | Gün | Açıklama |
|------|--------|-----|----------|
| USD/TRY | USDTRY=X | 1300 | Dolar/TL kuru |
| EUR/TRY | EURTRY=X | 1300 | Euro/TL kuru |
| Altın | GC=F | 1258 | Altın USD fiyatı |
| Petrol | CL=F | 1258 | WTI ham petrol |
| VIX | ^VIX | 1256 | Küresel korku endeksi |
| XU100 | XU100.IS | 1248 | BIST100 endeksi |
| S&P500 | ^GSPC | 1256 | ABD piyasası |
| DXY | DX-Y.NYB | 1258 | Dolar endeksi |

**TCMB EVDS API (2 kaynak aktif, 3 kaynak erişim sorunu):**

| Veri | Seri Kodu | Durum | Gün |
|------|-----------|-------|-----|
| USD/TRY (resmi) | TP.DK.USD.A.YTL | ✅ Aktif | 689 |
| EUR/TRY (resmi) | TP.DK.EUR.A.YTL | ✅ Aktif | 689 |
| Politika faizi | TP.PF.PF | ❌ Erişim hatası | — |
| AOFM | TP.TRB.AGIR.ORLAM | ❌ Erişim hatası | — |
| Gecelik repo | TP.PY.P01 | ❌ Erişim hatası | — |

**EVDS API Key:** mLPEXExImW (evds Python kütüphanesi ile çalışıyor)
**Not:** Faiz/repo seri kodları ya yanlış ya da EVDS hesabında o serilere erişim yetkisi yok.

### 3.2 Üretilen Makro Feature'lar (28 adet)

**Döviz (8):** usdtry_degisim_1g/5g/20g, usdtry_vol_10g, usdtry_trend, usdtry_sma_cross, eurtry_degisim_5g, eur_usd_spread_degisim
**VIX (4):** vix, vix_degisim_5g, vix_seviye, vix_spike
**Emtia (4):** altin_degisim_5g/20g, petrol_degisim_5g/20g
**Global (4):** dxy_degisim_5g, dxy_trend, sp500_degisim_5g/20g
**BIST (5):** xu100_degisim_5g/20g, xu100_vol_20g, xu100_trend, xu100_golden_cross
**Türev (2):** risk_on_skor (0-1 birleşik), doviz_baskisi
**TCMB (varsa) (5):** tcmb_faiz, tcmb_faiz_degisim, tcmb_aofm, tcmb_aofm_spread, tcmb_repo

---

## 4. FEEDBACK LOOP SİSTEMİ

### 4.1 Mimari

```
Sabah tarama (08:30)
    │
    ├── gunluk_bomba.py → bomba hisseler bulunur
    │       │
    │       └── feedback_loop.tahmin_kaydet() → her AL sinyali loglanır
    │
    ├── otonom_trader.py → aynı entegrasyon
    │
    └── data/feedback_log.json ← tüm tahminler burada

Akşam kontrol (18:30) — ANKA_FeedbackRapor scheduled task
    │
    ├── feedback_loop.sonuc_guncelle() → 5+ günlük tahminlerin gerçek sonuçları
    │       │
    │       └── yfinance ile gerçek fiyatı çek, doğru/yanlış etiketle
    │
    ├── feedback_loop.performans_raporu() → istatistikler
    │       ├── Genel başarı oranı
    │       ├── Rejim bazlı performans
    │       ├── Sinyal bazlı (AL/SAT/BEKLE)
    │       ├── En iyi/kötü hisseler
    │       └── Son 20 tahmin trendi
    │
    └── feedback_loop.iyilestirme_onerileri() → otomatik öneriler
            ├── Başarı < %55 → "model yeniden eğitilmeli"
            ├── Bear'de kötü → "bear parametreleri ayarla"
            ├── Son 20 düşüş → "piyasa değişmiş, yeniden eğitim"
            └── Rapor data/feedback_rapor_YYYYMMDD.json'a kaydedilir
```

### 4.2 Durum
- Entegrasyon tamamlandı (gunluk_bomba.py + otonom_trader.py)
- Scheduled task aktif (her gün 18:30)
- Henüz feedback verisi yok (bugün bağlandı, 5+ gün sonra ilk sonuçlar gelecek)

---

## 5. COİN TRADING BOTU

- **Dosya:** coin_otonom.py
- **Borsa:** Binance (API key .env'de)
- **İzlenen coinler:** 18 adet
- **Tarama aralığı:** Her 10 dakika
- **Risk parametreleri:** Stop-loss %3, trailing %2, komisyon %0.3
- **AI modeli:** coin_ai_v1.pkl (XGBoost, 15 coin, 2 yıllık saatlik veri)
- **Durum:** RUNNING (VPS'te scheduled task olarak)

---

## 6. BUGÜN (15 NİSAN 2026) YAPILAN İŞLER

### 6.1 Dashboard Stabilizasyonu
**Problem:** Dashboard'lar sürekli düşüyordu, her seferinde elle başlatılıyordu.
**Çözüm:**
- 3 yeni scheduled task oluşturuldu (BistDashboard, CoinDashboard, Watchdog)
- Hepsi "at system startup" ile boot'ta otomatik başlıyor
- Watchdog her 5 dakikada port 8501/8502 kontrol ediyor, düşeni yeniden başlatıyor
- Windows Firewall kuralları eklendi (port 8501, 8502)

### 6.2 Faz 1: Makro Veri Katmanı
**Problem:** ML modeli sadece teknik indikatörlerle çalışıyordu (RSI, MACD, Bollinger vb.), AUC 0.56 ile yazı-turaya yakındı.
**Çözüm:**
- `makro_veri.py` yazıldı — 10 veri kaynağından 28 makro feature
- TCMB EVDS API entegre edildi (evds Python kütüphanesi ile)
- `tahmin_motoru_v2.py`'nin `EnsembleModelV2.egit()` metoduna `makro_veri` parametresi eklendi
- Tüm eğitim noktaları güncellendi (alpha_v2_bot.py, motor_v3.py, otonom_trader.py)
- **Sonuç:** AUC 0.56 → 0.73 (+0.17)

### 6.3 Faz 2A: Rejim-Bazlı Modeller
**Problem:** Tek model bull, bear, sideways dönemlerin hepsine aynı yaklaşıyordu.
**Çözüm:**
- `rejim_modeller.py` yazıldı — XU100'den rejim tespiti (SMA + ADX + momentum bazlı)
- Her rejim için ayrı XGBoost + LightGBM ensemble
- Her rejimin kendi feature selection'ı (20 feature/rejim)
- **Sonuç:** Bear modeli AUC 0.77, precision %73

### 6.4 Faz 2B: Feedback Loop
**Problem:** Model tahmin yapıyordu ama doğru mu yanlış mı öğrenmiyordu.
**Çözüm:**
- `feedback_loop.py` yazıldı — tahmin kayıt + 5 gün sonra sonuç kontrol + rapor
- `gunluk_bomba.py` ve `otonom_trader.py`'ye entegre edildi
- Scheduled task: ANKA_FeedbackRapor (her gün 18:30)

### 6.5 BIST100 Listesi
- `bist100.py` oluşturuldu — 91 ticker (85'i yfinance'ta aktif)
- Eğitim 30 hisseden 85 hisseye genişletildi (daha fazla veri = daha stabil model)

---

## 7. BİLİNEN SORUNLAR VE EKSİKLER

| # | Sorun | Öncelik | Çözüm Yolu |
|---|-------|---------|------------|
| 1 | EVDS faiz/repo seri kodları çalışmıyor | Orta | EVDS sitesinde Tüm Seriler'den doğru kodları bul |
| 2 | VPS'te yfinance geçici timeout'lar | Düşük | Geçici sorun, kendiliğinden düzeliyor |
| 3 | Matriks IQ'da Midas işlem yetkisi 0 | Yüksek | Midas destek'e yazılacak (CEO görevi) |
| 4 | Coin AI modeli VPS'e deploy edilmemiş | Orta | coin_ai_v1.pkl VPS models/ klasörüne kopyalanmalı |
| 5 | ANKA Danışman paneli coin tarafına geçirilmedi | Düşük | Sonraki sprint |

---

## 8. SONRAKI ADIMLAR (Yol Haritası)

### Kısa vade (bu hafta):
- [ ] EVDS'te doğru faiz seri kodlarını bul ve entegre et
- [ ] 1 hafta feedback verisi topla, ilk performans raporu al
- [ ] Midas'a algo işlem yetkisi için başvur

### Orta vade (2-4 hafta):
- [ ] Faz 3: KAP bildirimleri + NLP sentiment entegrasyonu
- [ ] Faz 3: Emir defteri derinliği (Matriks API üzerinden)
- [ ] Haftalık otomatik model yeniden eğitim (her Pazar gece)
- [ ] A/B test altyapısı (eski model vs yeni model paper trading)

### Uzun vade:
- [ ] Temporal Fusion Transformer (zaman serisi derin öğrenme)
- [ ] Portföy optimizasyonu (Markowitz / Black-Litterman)
- [ ] Standalone desktop uygulama (tarayıcıdan bağımsız)
- [ ] Hedef: AUC 0.75+ (kurumsal üstü seviye)

---

## 9. API ANAHTARLARI VE ERİŞİM

| Servis | Key Konumu | Durum |
|--------|-----------|-------|
| Binance | C:\ANKA\.env | ✅ Aktif |
| TCMB EVDS | C:\ANKA\.env | ✅ Aktif (kısmi — döviz OK, faiz erişim yok) |
| VPS SSH | Administrator@78.135.87.29 | ✅ Aktif |

---

## 10. BAŞKA BİR AI İÇİN HIZLI BAŞLANGIÇ

Bu projeye devam edecek bir AI için:

1. **Kaynak kod:** ~/Desktop/ANKA (lokal), C:\ANKA (VPS)
2. **Ana ML motoru:** `tahmin_motoru_v2.py` → `EnsembleModelV2` sınıfı
3. **Makro veri:** `makro_veri.py` → `makro_veri_al()` ve `makro_feature_hesapla()`
4. **Rejim modelleri:** `rejim_modeller.py` → `RejimModelSistemi` sınıfı
5. **Feedback:** `feedback_loop.py` → `tahmin_kaydet()`, `sonuc_guncelle()`, `gunluk_kontrol()`
6. **Eğitim çalıştırma:** `alpha_v2_bot.py` → `model_egit_komut()` veya VPS'te `tam_egitim_bist100.py`
7. **VPS erişim:** `sshpass -p '*AYiMn5ZkX' ssh Administrator@78.135.87.29`
8. **Dashboard'lar otomatik:** Watchdog koruyor, boot'ta başlıyor, müdahale gerekmez
9. **Kullanıcı tercihi:** Otonom çalış, izin sormadan devam et, Türkçe iletişim
10. **Organizasyon:** CEO (kullanıcı) → Direktör (AI) → Danışman + Mühendis + Ajanlar
