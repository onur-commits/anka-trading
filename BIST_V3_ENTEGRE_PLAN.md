# BIST V3 ML Modelinin Entegrasyonu — Adım Adım

**Durum:** V3 kodu (`tahmin_motoru_v3.py`) hazır, wrapper (`bist_predict.py`) hazır. Live kodda hâlâ V2 var.

## 1. Mevcut tablo

| Bileşen | Durum |
|---|---|
| `tahmin_motoru_v2.py` | ✅ Aktif. `models/ensemble_v2.pkl` var (AUC 0.566 — zayıf). |
| `tahmin_motoru_v3.py` | ✅ Yazılmış (Stacking + Optuna + Calibration). **Hiç eğitilmemiş.** |
| `models/ensemble_v3.pkl` | ❌ Yok. |
| `bist_predict.py` | ✅ Yeni wrapper. V3 → V2 → None graceful fallback. |
| Kullanıcı kod (`app.py`, `otonom_trader.py`, vs.) | V2'yi doğrudan çağırıyor. |

## 2. V3 Modelini Eğit

```bash
cd /path/to/anka-trading
python -X utf8 -c "
from tahmin_motoru_v3 import StackingEnsembleV3
import yfinance as yf
from gunluk_bomba import TICKERS

veri = {}
for t in TICKERS:
    try:
        df = yf.download(t, period='2y', progress=False)
        if len(df) >= 200:
            veri[t] = df
    except Exception:
        pass

model = StackingEnsembleV3()
meta = model.egit_v3(veri, use_optuna=False)  # use_optuna=True icin optuna paketi gerek
model.kaydet_v3()
print(meta)
"
```

İlk eğitim ~15-30 dk. Çıktı: `models/ensemble_v3.pkl` + `models/ensemble_v3_meta.json`.

**Optuna ile hyperparameter tune** istersen:
```bash
pip install optuna       # zaten requirements.txt'de
# Yukaridaki egitim cagrisinda use_optuna=True
```
Bu ~1-2 saat sürer ama AUC'u +%2-5 artırabilir.

## 3. Doğrulama (entegre etmeden)

```bash
python -X utf8 bist_predict.py
```
Çıktı V3 yüklendiğini göstermeli:
```
Yuklenen model: {'versiyon': 'V3', 'hazir': True, 'tip': 'StackingEnsemble'}
```

## 4. Bot'a bağlama (eğitim ve doğrulamadan sonra)

Her dosyada 2 satır değişiklik. **Tek seferde yap, hep birden test et.**

### 4a. `otonom_trader.py`
```python
# ESKİ (38-46):
from tahmin_motoru_v2 import (
    EnsembleModelV2, feature_olustur_v2, market_rejim_tespit,
    sektor_momentum_hesapla, hisse_analiz_v2, atr_hesapla,
)
# YENİ — sadece şu 2'sini bist_predict'ten al, gerisi aynı:
from tahmin_motoru_v2 import (
    feature_olustur_v2, market_rejim_tespit,
    sektor_momentum_hesapla, atr_hesapla,
)
from bist_predict import yukle_model, analiz_et

# ESKİ (566, 574, 770 civarı):
model = EnsembleModelV2.yukle()
# YENİ:
model = yukle_model()  # V3 varsa V3, yoksa V2

# ESKİ (190):
analiz = hisse_analiz_v2(ticker, df, model, rejim)
# YENİ:
analiz = analiz_et(ticker, df, model, rejim)
```

### 4b. `sabah_scanner.py`
- Line 17: `from tahmin_motoru_v2 import EnsembleModelV2, hisse_analiz_v2, feature_olustur_v2`
  → `feature_olustur_v2` import kalır + `from bist_predict import yukle_model, analiz_et`
- Line 214: `EnsembleModelV2.yukle()` → `yukle_model()`
- Line 254: `hisse_analiz_v2(...)` → `analiz_et(...)`

### 4c. `gunluk_bomba.py`
- Aynı pattern: V2 import'unu trim et + bist_predict ekle, `EnsembleModelV2.yukle()` ve `hisse_analiz_v2()` çağrılarını değiştir.

### 4d. `app.py` (Streamlit)
- Line 14: V2 import trim
- Line 37 (`yukle_kayitli_model`): `EnsembleModelV2.yukle()` → `yukle_model()`
- Line 147, 302: `hisse_analiz_v2(...)` → `analiz_et(...)`

### 4e. `motor_v3.py`
Adından V3 olmasına rağmen muhtemelen V2 kullanıyor (kontrol et). Aynı pattern.

## 5. ML eğitim cron'u (opsiyonel)

`otonom_trader.gorev_05_30_egitim()` şu an V2 eğitiyor. V3'e geçiş için aynı fonksiyonda:
```python
# ESKİ:
model = EnsembleModelV2()
meta = model.egit(veri, market_rejim=rejim)
# YENİ:
from tahmin_motoru_v3 import StackingEnsembleV3
model = StackingEnsembleV3()
meta = model.egit_v3(veri, market_rejim=rejim)
model.kaydet_v3()
```
Böylece her sabah 05:30'da V3 modeli güncellenir.

## 6. Riskler

1. **V3 sample weighting + calibration eski V2'den farklı kararlar verir.** Önce paper trading ile 1-2 hafta test.
2. **Feature interaction'lar yeni kolonlar ekler** — eski model dosyası uyumsuz olabilir. V3 eğitimi her seferinde sıfırdan başlamalı.
3. **Optuna tuning 1-2 saat sürer** — günlük 05:30 cron'da `use_optuna=False` kullan, ayda bir manuel `use_optuna=True` ile derin tune yap.

## 7. Geri alma

`bist_predict.yukle_model()` zaten graceful: `models/ensemble_v3.pkl`'i sil veya rename et → otomatik V2'ye düşer. Kod değişikliği gerekmez.

```bash
mv models/ensemble_v3.pkl models/ensemble_v3.pkl.disabled
# Artik V2 kullanılır, restart bile gerekmez (yeni session'lar V2 yukler)
```

## 8. Beklenen kazanç

V2'nin AUC 0.566 — yazı-tura'ya yakın. V3 iyileştirmeleri:
- Sample weighting (yakın veri ağırlıklı)
- Calibration (olasılık doğru)
- Stacking (model fikirleri birleştirir)
- Threshold optimization (F1 max)

Literatürde benzer setup'lar AUC +0.03-0.08 iyileşme verir. V3 AUC ~0.60-0.64 beklenir. Karar verilebilir seviye değil ama AUC>0.60 + threshold tuning ile faydalı sinyal olur.

**Eğer eğitim sonrası V3 AUC < V2 AUC çıkarsa** (overfitting), V3'ü devreye alma. `bist_predict.py` zaten yoksaymaya hazır.
