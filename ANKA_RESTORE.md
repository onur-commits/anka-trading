# 🔥 ANKA TRADING SYSTEM — Restore Guide
## Tarih: 2 Nisan 2026
## Versiyon: V3 ALPHA/TURBO

---

## SİSTEM MİMARİSİ

```
Mac (Python)                     Windows VM (Parallels)
├── otonom_trader.py              ├── MatriksIQ
│   05:30 ML eğitim              │   └── BOMBA_V3_TURBO (C# robot)
│   08:30 Bomba tarama           ├── C:\Robot\
│   → aktif_bombalar.txt yaz     │   ├── aktif_bombalar.txt
├── v3_risk_motor.py             │   └── v3_bridge.json
│   Her 60sn VIX+XU100+USD/TRY  └── Midas aracı kurum bağlantısı
│   → v3_bridge.json yaz
├── kontrol_paneli.py (Streamlit)
└── motor_v3.py (V3 otonom)
```

## DOSYA HARİTASI

### Python Dosyaları (Mac)
- `borsa_surpriz/otonom_trader.py` — Ana zamanlayıcı (05:30, 08:30, 09:35, 12:00, 15:00, 17:35)
- `borsa_surpriz/motor_v3.py` — V3 otonom motor (VPS-ready)
- `borsa_surpriz/v3_risk_motor.py` — Makro risk motoru (VIX, XU100, USD/TRY → bridge.json)
- `borsa_surpriz/kontrol_paneli.py` — Streamlit web kontrol paneli
- `borsa_surpriz/tahmin_motoru_v2.py` — ML ensemble (XGBoost + LightGBM + MLP, 73 feature)
- `borsa_surpriz/risk_yonetimi.py` — Risk yönetimi (ATR stop, Kelly Criterion, drawdown)
- `borsa_surpriz/haber_sentiment.py` — Türkçe haber sentiment analizi
- `borsa_surpriz/gunluk_bomba.py` — Bomba skor hesaplama (0-100) + IQ kod üretici
- `borsa_surpriz/v3_bridge_writer.py` — Detaylı bridge writer (ML skorlu, eski versiyon)

### C# Robot Dosyaları (IQ)
- `borsa_surpriz/matriks_iq/BOMBA_V3_TURBO.cs` — Aktif çalışan robot
- `borsa_surpriz/matriks_iq/BOMBA_V3_ALPHA.cs` — 30dk ALPHA versiyon
- `borsa_surpriz/matriks_iq/BOMBA_V3_FINAL.cs` — 49 sembol tam otonom (henüz derlenmedi)
- `borsa_surpriz/matriks_iq/BOMBA_V2_MULTI_FINAL.cs` — V2 multi-symbol
- `borsa_surpriz/matriks_iq/AKILLI_ROBOT_SABLONU.cs` — Eski tek sembol şablonu

### Veri Dosyaları
- `borsa_surpriz/data/otonom_log.json` — Otonom trader logları
- `borsa_surpriz/data/otonom_state.json` — Günlük durum (bombalar, rejim)
- `borsa_surpriz/data/v3_bridge.json` — Risk bridge (lokal kopya)
- `borsa_surpriz/data/motor_v3_log.json` — V3 motor logları
- `borsa_surpriz/models/ensemble_v2.pkl` — Eğitilmiş ML model

### Windows Dosyaları (C:\Robot\)
- `aktif_bombalar.txt` — Günün bomba hisseleri (virgülle ayrılmış)
- `v3_bridge.json` — Risk verisi (multiplier, regime, vix, xu100, usd)

---

## AKTİF ROBOT PARAMETRELERİ (2 Nisan 2026)

### BOMBA_V3_TURBO (ALPHA parametreleriyle)
- Semboller: AYEN, TUPRS, AKSEN, PETKM, BRISA
- Periyot: 30 dakika (Min30)
- BasePosValue: 20,000 TL
- EMA: 10/20
- RSI eşik: 50
- MOST: period=3, percent=2.0
- ProfitTrigger: %1.2
- HardStop: %3.5
- TrailingStop: %1.8
- Zaman filtresi: Öğlen 12:00-13:45 blok, kapanış 17:30 sonrası giriş yok
- Kapanış çıkışı: 17:50'de %0.5+ kârda ise sat
- Açılış agresif: 10:00-10:30 çarpan x1.3
- Kapanış defansif: 17:30+ çarpan x0.6

### Bridge Formatı (v3_bridge.json)
```json
{
    "multiplier": 1.0,
    "regime": "BULL",
    "xu100_change": 1.15,
    "vix": 24.53,
    "usd_change": -0.01,
    "pos_value": 20000,
    "last_update": "08:47:40"
}
```

### Risk Motoru Kuralları
- XU100 < -%1.0 VEYA VIX > 30 → multiplier=0 (DANGER_CRASH, alım bloke)
- USD/TRY > %0.8 → multiplier=0.5 (CAUTION_CURRENCY, yarı pozisyon)
- XU100 > %0.5 → BULL rejimi
- XU100 < -%0.5 → BEAR rejimi

---

## KURULUM ADIMLARI (SIFIRDAN)

### 1. Python Ortamı
```bash
cd "/Users/onurbodur/adsız klasör"
python3 -m venv .venv
source .venv/bin/activate
pip install yfinance pandas numpy xgboost lightgbm scikit-learn schedule streamlit
```

### 2. Otonom Trader Başlat
```bash
cd "/Users/onurbodur/adsız klasör"
nohup .venv/bin/python borsa_surpriz/otonom_trader.py > /dev/null 2>&1 &
```

### 3. Risk Motoru Başlat
```bash
nohup .venv/bin/python borsa_surpriz/v3_risk_motor.py > /tmp/risk_motor.log 2>&1 &
```

### 4. Mac Uyuma Engeli
```bash
caffeinate -d -i -s &
```

### 5. Windows'ta C:\Robot Klasörü
```bash
prlctl exec "Windows 11" cmd /c "mkdir C:\Robot"
prlctl exec "Windows 11" cmd /c "echo AYEN,TUPRS,AKSEN,PETKM,BRISA > C:\Robot\aktif_bombalar.txt"
```

### 6. MatriksIQ Robot
- IQ'da yeni strateji oluştur: BOMBA_V3_TURBO
- C# kodunu yapıştır (BOMBA_V3_TURBO.cs)
- Derle → Başlat
- Midas hesabına bağlan

### 7. Kontrol Paneli (opsiyonel)
```bash
streamlit run borsa_surpriz/kontrol_paneli.py --server.port 8501
```

---

## KRİTİK NOTLAR

1. **Path uyumu**: Python `C:\Robot\` yoluna yazmalı, robot `C:\Robot\` okumalı
2. **Midas bağlantısı**: IQ her açılışta Midas'a bağlanmalı yoksa emir gitmez
3. **Mac uyuma**: caffeinate + sudo pmset -c disablesleep 1
4. **Windows Update**: Otomatik güncellemeyi kapat, IQ'yu kapatıyor
5. **GetSymbolId()**: Multi-symbol çalışmasının anahtarı, symbolCache dictionary
6. **Atomik yazma**: Bridge dosyası temp+rename ile yazılmalı (IQ yarım okuma riski)
7. **Bomba listesi OnInit'te okunur**: Robot yeniden başlatılmadan yeni liste alınmaz (V3_FINAL bu sorunu çözer)

## İLERİ HEDEFLER

1. VPS (MarkaHost Profesyonel 674 TL/ay) — laptop bağımlılığını kaldır
2. Telegram bot — telefondan bildirim
3. V3_FINAL — 49 sembol yüklü, otomatik bomba okuma
4. AI self-learning — her işlemden öğrenen parametre optimizasyonu
5. Kripto (Binance API) — 7/24 otonom trading
6. Kontrol paneli V2 — multi-strateji, performans dashboard

## PROJE ADI: ANKA 🔥
Türk mitolojisindeki Anka Kuşu — ateşten doğar, asla ölmez.
- A: Otonom
- N: Nöral
- K: Koruma
- A: Alfa

## ÖNEMLİ: BİLİNEN SORUNLAR VE ÇÖZÜMLER

### Robot önceden alınmış hisseleri yönetemez
Robot sadece KENDİSİ aldığı hisseleri satabilir. Önceden portföyde olan hisseleri bilmez (inPosition = false).
ÇÖZÜM: Elle sat. Veya robotu geliştir — başlangıçta portföyü oku ve inPosition'ı buna göre ayarla.

### Bomba listesinden çıkan hisse otomatik satılmıyor (eğer robot almadıysa)
bombadenCikti mantığı sadece inPosition[s] == true olduğunda çalışır.
ÇÖZÜM: İleride OnInit'te Midas portföyünü oku, mevcut pozisyonları inPosition'a yaz.

### SendOrderSequential çakışması
Aynı anda birden fazla emir → "sıralı gitmesi seçeneği aktif" hatası.
ÇÖZÜM: SendOrderSequential(false) veya emirleri sırayla gönder.

### T+2 kısıtlaması
Aynı gün alınan hisse satılamayabilir (broker'a bağlı).
ÇÖZÜM: Robot aynı gün aldığını satmaya çalışmasın — giriş zamanı takibi ekle.
