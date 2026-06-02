# Coin ML Modelinin Bot'a Entegrasyonu — Adım Adım Plan

**Durum:** Helper modül (`coin_ml_score.py`) hazır. Live bot'a (`coin_otonom_trader.py`) henüz **dokunulmadı** — entegrasyon kararı sende.

## 1. Mevcut durum

| Bileşen | Durum |
|---|---|
| `coin_ai_egitim.py` | ✅ Düzeltildi (Mac yolu / POL/S sembolleri / XGBoost / BTC korelasyon). Çalıştırınca `models/coin_ai_v1.pkl` üretir. |
| `models/coin_ai_v1.pkl` | ❌ Henüz yok. `python coin_ai_egitim.py` çalıştırılınca oluşur. |
| `coin_ml_score.py` | ✅ Yeni. Model'i yükler, herhangi bir coin için 0–1 TP olasılığı verir. |
| `coin_otonom_trader.py` | Rule-based ajan oylama (5+2 uzman). **ML hâlâ kullanmıyor.** |

## 2. Modelin üretimi (1 kere, ~10 dk)

Mac veya VPS'te:
```bash
cd /path/to/anka-trading
python -X utf8 coin_ai_egitim.py
```

Çıktı:
- `models/coin_ai_v1.pkl` (XGBoost + feature_cols + metadata)
- Konsola AUC, F1, feature importance, per-coin accuracy yazar.

**Beklenti:** AUC 0.55–0.65 aralığı. Daha düşükse model kullanılmasın (kural-bazlı kal). Daha yüksekse devreye alma anlamlı.

## 3. Doğrulama (entegrasyondan önce)

```bash
python -X utf8 coin_ml_score.py --meta              # model yüklendi mi
python -X utf8 coin_ml_score.py --test BTCUSDT      # bir coin için skor
python -X utf8 coin_ml_score.py --test ETHUSDT      # başka coin
```

Skorlar 0–100 dönmeli. 0.5 (50) dönüyorsa model yüklenememiş demektir (log'a bak).

## 4. Bot'a bağlama (sen onaylayınca yapılacak)

`coin_otonom_trader.py` içinde 3 küçük değişiklik:

### 4a. Sınıf başına ML skorlayıcı yükle
```python
# CoinOtonomTrader.__init__ içine:
from coin_ml_score import CoinMLSkorlayici
self.ml = CoinMLSkorlayici()
if self.ml.hazir:
    logger.info("Coin ML modeli aktif (AUC=%s)", self.ml.train_meta.get("auc"))
else:
    logger.info("Coin ML modeli yok — sadece kural-bazlı skorlama")
```

### 4b. Tarama sırasında ML puanını ajan oylamaya kat
`tara()` içinde, mevcut puan toplama bloğunun ALTINA:
```python
ml_puan = self.ml.puana_cevir(self.ml.skor(symbol, df)) if self.ml.hazir else 50
puanlar["ML"] = ml_puan
# Ağırlıkları yeniden dengele — ML için %15 alan açıyoruz:
if self._uzman_ajanlar_aktif:
    skor = (tek_p * 0.25 + hac_p * 0.15 + mak_p * 0.15 + lik_p * 0.10 +
            sen_p * 0.10 + fun_p * 0.10 + ml_puan * 0.15)
else:
    skor = (tek_p * 0.30 + hac_p * 0.20 + mak_p * 0.20 + lik_p * 0.15 +
            ml_puan * 0.15)
```

### 4c. CLI flag ile aç/kapa
```python
# argparse:
parser.add_argument("--no-ml", action="store_true",
                    help="ML skorlayiciyi devre disi birak (kural-bazli mod)")
# init'te:
if _args.no_ml:
    self.ml.hazir = False
```

## 5. Riskler & dikkat noktaları

1. **Modelin AUC'u düşükse zarara çevirir.** Önce backtest yap (paper_trader.py + ab_karsilastirma.py). AUC < 0.55 ise entegre etme.
2. **BTC verisi her tarama döngüsünde çekilir** — `CoinMLSkorlayici` 5 dk cache yapıyor ama yine de network bağımlı. Network sorununda model 0.5 (notr) döner, bot rule-based davranmaya devam eder. **Crash riski yok.**
3. **Feature shape'i bozulursa model error.** `coin_ai_egitim.py`'deki `feature_cols` listesi değişirse, eski .pkl uyumsuz olur. Yeni model üret.
4. **MIN_SKOR_AL=75 hâlâ sıkı.** ML eklenince ortalama skor yükselebilir (model olumlu görüyorsa). Backtest sonrası eşiği ayarla.

## 6. Geri alma (rollback)

ML çıkarmak için `coin_otonom_trader.py` çağırırken `--no-ml` ekle veya:
```bash
mv models/coin_ai_v1.pkl models/coin_ai_v1.pkl.disabled
```
Bot otomatik kural-bazlı moda döner (CoinMLSkorlayici hazır=False).

## 7. Aşamalı önerim

1. **Bugün:** Mac'te `python coin_ai_egitim.py` çalıştır, model üret.
2. **Bugün:** `coin_ml_score.py --test BTCUSDT/ETHUSDT/SOLUSDT` ile 3-5 coin için skor al, mantıklı görünüyor mu bak (BTC bull'da yüksek, bear'da düşük olmalı).
3. **Yarın:** `paper_trader.py` ile 1 hafta backtest — ML'li vs ML'siz fark.
4. **Sonuç pozitifse:** 4a/b/c değişikliklerini yap, **önce `--dry-run`** ile 1 hafta paper, sonra canlıya geç.
5. **Aylik retrain:** Her ay yeni veriyle model güncelle (`coin_ai_egitim.py` tekrar koş).
