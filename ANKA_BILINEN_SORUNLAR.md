# ANKA Bilinen Sorunlar & Çözümler + Erişim Noktaları
# ====================================================
# Bu dosya ANKA Mühendis tarafından okunur.
# Her yeni sorun buraya eklenir, Mühendis otomatik öğrenir.

## ERIŞIM NOKTALARI

### VPS
- IP: 78.135.87.29
- OS: Windows Server 2022
- User: Administrator
- SSH: Port 22
- Python: C:\Program Files\Python312\python.exe (3.12.8)
- Git: C:\Program Files\Git\bin\git.exe (2.47.1)
- Proje: C:\ANKA
- MatriksIQ: C:\MatriksIQ\MatriksIQ.exe

### Servisler
- BIST Dashboard: http://78.135.87.29:8501 (Streamlit, app.py)
- COIN Dashboard: http://78.135.87.29:8502 (Streamlit, coin_dashboard.py)
- ANKA Danışman: http://78.135.87.29:8501 → Sayfa 2
- MatriksIQ API: TCP port 18890 (anka_api.py)
- ANKA Mühendis: Arka plan servisi (anka_muhendis.py)
- Otonom Trader: Zamanlı görevler (otonom_trader.py)

### Startup
- Auto-start: Registry HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\ANKA_Trading
- Script: C:\ANKA\anka_startup.bat
- Sıra: BIST Dashboard → (5sn) → COIN Dashboard → (5sn) → Mühendis

### API Anahtarları (.env dosyasında, git'e EKLENMEZ)
- BINANCE_API_KEY / BINANCE_API_SECRET
- VPS_PASSWORD / VPS_HOST / VPS_USER

### SSH Erişim (Mac'ten)
```
sshpass -p 'SIFRE' ssh -o StrictHostKeyChecking=no Administrator@78.135.87.29
```

### GitHub
- Repo: https://github.com/onur-commits/anka-trading.git
- Lokal: ~/Desktop/ANKA

---

## BİLİNEN SORUNLAR & ÇÖZÜMLERİ

### SORUN-001: Windows Türkçe Karakter Encoding (cp1252)
**Belirti:** `UnicodeEncodeError: 'charmap' codec can't encode character`
**Sebep:** Windows cmd.exe varsayılan encoding'i cp1252, Türkçe ğ/ü/ş/ı/ö/ç desteklemiyor
**Çözüm:**
1. Python çalıştırırken HER ZAMAN `-X utf8` flag'i kullan
2. anka_startup.bat'ta `set PYTHONUTF8=1` satırı var
3. `PYTHONUTF8=1` env variable'ı `set` ile ayarlanırsa Python başlamadan önce olmalı
4. print() yerine logging kullanıldığında dosyaya `encoding="utf-8"` parametre ekle
**Önem:** KRİTİK — bu sorun her yeni script'te tekrar çıkar

### SORUN-002: yfinance Veri Çekme Hataları
**Belirti:** Boş DataFrame, NaN değerler, MultiIndex columns
**Sebep:** yfinance API bazen MultiIndex döndürür, bazen timeout olur
**Çözüm:**
1. `if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)`
2. Her veri çekimden sonra `if df.empty: return None` kontrolü
3. `progress=False` parametresi ekle (Streamlit uyumluluğu)
4. Ticker formatı: "GARAN.IS" (Yahoo Finance Türkiye)
**Önem:** YÜKSEK — tarama ve analiz bu veriye bağlı

### SORUN-003: Streamlit Dashboard Çökmesi
**Belirti:** Port 8501/8502 LISTENING değil, web sayfası açılmıyor
**Sebep:** Bellek dolması, Python exception, Windows update restart
**Çözüm:**
1. Mühendis 30dk'da bir kontrol eder, çökmüşse `start /B streamlit run ...` ile yeniden başlatır
2. `--server.headless true --server.address 0.0.0.0` parametreleri şart
3. Windows Task Scheduler'da da startup script var
**Önem:** YÜKSEK — dashboard'lar ana kullanıcı arayüzü

### SORUN-004: JSON Dosya Bozulması
**Belirti:** `json.JSONDecodeError`, dosya okunmuyor
**Sebep:** Yazma sırasında çökme, eşzamanlı yazma, disk dolu
**Çözüm:**
1. Mühendis otomatik tespit eder → yedekler (.bak) → sıfırlar
2. JSON yazarken `ensure_ascii=False, indent=2` kullan
3. Büyük JSON'ları yazmadan önce temp dosyaya yaz, sonra rename
**Önem:** ORTA — veri kaybı olabilir ama yedekleniyor

### SORUN-005: SSH Bağlantı Kopması
**Belirti:** `Permission denied`, `Connection refused`, timeout
**Sebep:** SSH servisi durmuş, firewall, yanlış şifre
**Çözüm:**
1. Şifre .env dosyasında
2. `-o ConnectTimeout=10 -o StrictHostKeyChecking=no` parametreleri kullan
3. `sshpass -p 'SIFRE'` ile otomatik şifre gir
4. Bağlanamıyorsa VPS provider panelinden restart
**Önem:** YÜKSEK — uzaktan yönetimin tek yolu

### SORUN-006: MatriksIQ Bağlantı Sorunu
**Belirti:** TCP 18890 LISTENING değil, IQ komutları çalışmıyor
**Sebep:** MatriksIQ programı kapalı, TCP listener başlamamış
**Çözüm:**
1. MatriksIQ'nun açık olduğunu kontrol et
2. anka_api.py TCP bağlantısında retry mekanizması var
3. JSON + char(11) terminator formatı şart
**Önem:** ORTA — canlı trade için gerekli

### SORUN-007: Midas Menkul İşlem Yetkisi — KAPANDI
**Belirti:** İşlem limiti 0 görünüyor, emir gönderilemiyor
**Sebep:** Midas Menkul bireysellere API/algo erişimi VERMİYOR (kesinleşti 2026-04-15)
**Durum:** KAPANDI — Midas ile BIST canlı trade mümkün değil
**Alternatifler:**
1. Algolab (Deniz Yatırım) — Python API ile direkt BIST erişimi
2. Tacirler + MatriksIQ — C# robotlar ile algo trading
3. Paper Trading modu aktif (paper_trader.py) — gerçekçi simülasyon
**Önem:** KRİTİK — çözüm yolu değişti, alternatif aracı kurum gerekli

### SORUN-008: ML Model Düşük Performans — İYİLEŞTİRİLDİ (2026-04-16)
**Belirti:** AUC 0.56, TECHNO ajanı %33.7 doğruluk
**Sebep:** BIST'in yüksek noise/sinyal oranı, yetersiz feature, veri sızıntısı
**Uygulanan iyileştirmeler:**
1. tahmin_motoru_v2.py: EnsembleModelV2 (XGBoost + LightGBM + MLP), Purged Walk-Forward CV, Triple Barrier labeling
2. tahmin_motoru_v3.py: StackingEnsembleV3 — Level-2 meta-model (LogisticRegression), sample weighting (exponential decay), feature interactions (5 cross-feature), probability calibration (Platt scaling), F1-optimized threshold, Optuna hyperparameter tuning
3. paper_trader.py: Pessimist Paper Trading — slippage, partial fill, market impact, latency simulation (gerçekten daha kötü koşullar)
4. Tüm scanner'lar V2 modele güncellendi, risk_yonetimi entegre edildi
**Durum:** V3 model hazır, veri üzerinde test gerekli
**Önem:** ORTA → İYİLEŞTİRİLDİ

### SORUN-009: Bomba Robotları Log Üretmiyor — COZULDU (2026-04-16)
**Belirti:** "BOMBA_AYEN: Log yok" mesajları
**Sebep:** IQ robotları çalışıyor ama C:\ANKA\data'ya log yazmıyor
**Cozum uygulandı:**
1. `anka_api.py` — `robot_durum_sorgula()` ve `bomba_robot_log_topla()` metodlari eklendi
   - IQ TCP API uzerinden pozisyon/emir/gerceklesen bilgisi toplanir
   - `data/bomba_robot_log.json` dosyasina muhendis formatiyla uyumlu log yazilir
2. `bomba_robot_log_bridge.py` — Bagimsiz log koprusu scripti olusturuldu
   - `data/aktif_bombalar.txt` ve `C:\Robot\aktif_bombalar.txt` okur
   - MatriksIQ log dizinlerini tarar (C:\MatriksIQ\Logs\, %APPDATA%\MatriksIQ\)
   - IQ API uzerinden canli durum sorgular
   - `data/bomba_robot_status.json` birlesik status dosyasi yazar
   - `--surekli` moduyla 5dk arayla otomatik calisabilir
**Onem:** COZULDU

### SORUN-010: pip Paket Eksiklikleri
**Belirti:** `ModuleNotFoundError: No module named 'XXX'`
**Sebep:** Yeni script eklendiğinde gerekli paket yüklenmemiş
**Çözüm:**
1. `"C:\Program Files\Python312\python.exe" -m pip install PAKET --quiet`
2. requirements.txt güncel tutulmalı
3. Mühendis yeni script eklendiğinde import kontrolü yapmalı
**Bilinen paketler:** streamlit, yfinance, pandas, numpy, xgboost, lightgbm, schedule, psutil
**Önem:** DÜŞÜK — kolay çözüm ama sık tekrarlar

### SORUN-011: Disk Dolması
**Belirti:** Yazma hataları, JSON bozulması, crash
**Sebep:** Log dosyaları büyüyor, yfinance cache
**Çözüm:**
1. Mühendis gece 02:00'da eski log/rapor temizliği yapar
2. 50MB üstü loglar kesilir (son 5000 satır)
3. 7 günden eski raporlar silinir
4. .bak dosyaları 3 gün sonra temizlenir
**Önem:** ORTA

### SORUN-012: Komisyon Hesaba Katılmama
**Belirti:** Kârsız işlemler yapılıyor, net getiri negatif
**Sebep:** Komisyon filtresi tanımlı ama entegre edilmemişti
**Çözüm:** gunluk_bomba.py'ya KomisyonKontrol entegre edildi (2026-04-09)
**Maliyet:** %0.15 komisyon (tek yön) + %0.10 slippage = %0.40 toplam
**Önem:** YÜKSEK — artık çözüldü

---

## SORUN EKLEME ŞABLONU
```
### SORUN-XXX: Başlık
**Belirti:** Ne görüyorsun
**Sebep:** Neden oluyor
**Çözüm:** Nasıl çözülür
**Önem:** KRİTİK / YÜKSEK / ORTA / DÜŞÜK
```
