# Doktora Raporu Takip — 2026-05-25 PR #2 Sonrasi

**Önceki rapor:** [`ANKA_DOKTORA_RAPORU.md`](./ANKA_DOKTORA_RAPORU.md) (Nisan 2026, 47 sorun, 11 kritik)
**Bu rapor:** PR #2 (`claude/check-binance-integration-CNT9j`) sonrası durum

## Kritik Sorunlar — Güncel Durum

| # | Doktor Tespiti | Önceki Durum | Bu PR'da | Notlar |
|---|---|---|---|---|
| **K-01** | Dosya tabanlı IPC atomiklik yok | C# + Python ikisinde de yok | 🟡 **Python tarafı düzeldi** (commit `5d3ba7d`, `d3e69ab`) | C# tarafı hâlâ açık |
| K-03 | Sahte pozisyon takibi (PnL yanlış) | Açık | Açık | OnOrderUpdate düzeltmesi C# tarafında |
| **K-04** | Rejected order yönetimi yok → hayalet pozisyonlar | Açık | 🟢 **TAMAMEN DÜZELDİ** | 4 commit: `1e27d05`, `f510a70`, `68d31f2`, `06ab431`, `2cddcc9` — hem coin hem BIST trader'larında IQ/Binance hata kodlarını tespit edip pozisyon dosyasını güncellemiyor |
| K-05 | SendOrderSequential kilitleme | Açık | Açık | C# bot tarafı |
| K-06 | Yahoo Finance güvenilirliği | Açık | 🟡 **Kısmi** — `yf.download` çağrıları artık try/except'le sarılı (commit `085ddf1`) | Cross-validation hâlâ yok |
| K-07 | AUC 0.5982 yetersiz | Açık | 🟡 **Altyapı hazır** | `bist_predict.py` + `BIST_V3_ENTEGRE_PLAN.md` — V3 modeli (Stacking + calibration) eğitildiğinde AUC artmalı |
| K-08 | Portföy drawdown koruması çalışmıyor | Açık | Açık | risk_yonetimi.py BIST robot tarafına entegre değil |
| K-09 | Korelasyon kontrolü yok | Açık | Açık | Sektör limiti coin tarafında var, BIST'te yok |
| K-10 | Mac yeniden başlamayla tüm sistem kaybedilir | Açık | 🟡 **Kısmi** | `anka_muhendis.onar_coin_bot` 4 katmanlı fallback'a çıkarıldı (commit `2937902`); ama Mac-side launchd hâlâ yok |
| K-11 | Gerçek alfa kanıtlanmamış | Açık | 🟡 **Devam ediyor** | A/B karşılaştırma 19-Mayıs'ta bitti — sonuç bekleniyor |

**Skor:** 11 kritikten **1 tamamen çözüldü** (K-04 hayalet pozisyon), **4'ü kısmi iyileşti** (K-01, K-06, K-07, K-10), **6'sı hâlâ açık**.

## Bu PR'da Eklenen Yeni Koruma Katmanları (Doktor Listesinde Yoktu)

| Koruma | Commit | Açıklama |
|---|---|---|
| Bare except → Exception (55 yer) | `052314a` | Ctrl+C ile bot durdurulabilir, KeyboardInterrupt yutulmaz |
| File handle leak fix (12 yer) | `d7b3fa4` | Dashboard rerun'larında ulimit ihlali riski |
| `requirements.txt` 3 paket eksikti | `e7eccf0` | Fresh clone'da import-error |
| Hardcoded Mac path (coin_ai_egitim) | `3fdc026` | Coin ML model üretilemiyordu |
| Delist sembol (MATIC→POL, FTM→S) | `3fdc026` | Eğitim verisi çekilemiyordu |
| Deprecated XGBoost arg | `3fdc026` | XGBoost ≥2.0'da error |
| BTC korelasyon misalignment | `3fdc026` | Pozisyonel reindex yanlış sonuç veriyordu |
| Sessiz API key hatası | `58e5231` | Bot "Bakiye yetersiz" loglayıp gerçek IP/key hatasını gizliyordu |
| BIST seans saati kontrolü | `045c7fb` | Schedule dışı çalıştırmada gece yarısı tarama yapıyordu |
| logs/ dir yoksa oluştur | `8baadc2` | Fresh clone'da coin dashboard kalkmıyordu |
| Division-by-zero guard | `e8b1888` | Hacim 0'lı delisting'de crash |
| ZeroDivisionError (XU100) | `085ddf1` | Sabah taraması network'te çöküyordu |
| Bozuk JSON recovery | `a6aac1a` | State dosyaları bozulursa bot çökmüyor, sıfırlayıp devam ediyor |
| Cyrillic-isimli duplicate page | `23b600d` | Streamlit sidebar'da iki kere görünüyordu |
| Mühendis scheduler adı + fallback | `2937902` | `ANKA_CoinBot` → `ANKA_Coin_Trader` + 4 katman fallback |

## Önemli Mimari Eklemeler

| Modül | Açıklama |
|---|---|
| `coin_ml_score.py` + `COIN_ML_ENTEGRE_PLAN.md` | Coin botu ML'le güçlendirme altyapısı (live bot'a dokunulmadı, kullanıcı kararı) |
| `bist_predict.py` + `BIST_V3_ENTEGRE_PLAN.md` | BIST V3 → V2 → None graceful fallback wrapper |
| `ab_sonuc.py` (önceki PR) | A/B deneyi nihai sonuç hesabı + karar |
| `.claude/settings.json` | Otonom çalışma için permission + hook gate (canlı emir koruması) |

## Hâlâ Çözülmemiş Kritik Sorunlar (Doktor + Bu Oturum)

### C# tarafı (5 sorun — Python'dan müdahale edilemiyor)
- K-01 atomiklik (C# file lock)
- K-03 OnOrderUpdate fiyat fix
- K-05 SendOrderSequential
- K-08 drawdown koruması robot içine
- K-09 sektör/korelasyon limiti

### Operasyonel
- K-10 Mac launchd / watchdog
- K-11 A/B sonuç değerlendirme (`ab_sonuc.py` ile, deney bitti)

## Sıradaki Öncelikler (önerim)

1. **A/B karşılaştırma sonucunu çıkar** — `python ab_sonuc.py` VPS'te çalıştır, momentum bot vs BTC B&H kararı.
2. **Coin ML modelini eğit** — `python coin_ai_egitim.py` Mac'te ~10 dk. AUC ölç, mantıklıysa `COIN_ML_ENTEGRE_PLAN.md` adımlarıyla bota bağla.
3. **BIST V3 modelini eğit** — `BIST_V3_ENTEGRE_PLAN.md` adımlarıyla. V2'nin AUC 0.566'sını aşarsa devreye al.
4. **C# robot K-04 fix** — Python tarafı düzeldi ama C# tarafında hâlâ "OrdStatus !=2 ama bot kayıt tutuyor" patterni olabilir. C# tarafına Claude müdahale edemez (kod taranabilir, derlenip deploy edilemez).

## Mühendis Modülü (`anka_muhendis.py`) Durumu

- ✅ `onar_coin_bot` fix edildi (commit `2937902`) — 4 katmanlı fallback
- 🟡 `kontrol_iq_stratejiler` / `onar_iq_stratejiler` — gözden geçirilmedi (bu turun dışında)
- 🟡 `bilinen_sorunlari_yukle` — `ANKA_BILINEN_SORUNLAR.md` parser, regex tabanlı, OK
- ✅ `hizli_kontrol` her 30 dk otonom_trader + coin_otonom_trader process check, çökmüşse subprocess.Popen ile yeniden başlatma

Mühendis kendi kendine onarım yapıyor — bu PR sonrası daha sağlam çalışacak çünkü:
- Trader script'leri artık fantom poz yaratmıyor → state bozulmuyor
- State dosyaları atomik yazılıyor → mühendis bozuk state algılamıyor
- Bozuk JSON recovery → mühendis state'i bulamadığında crash etmiyor
