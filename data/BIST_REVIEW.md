# 🦅 BIST REVIEW — Otonom Trading Çekirdek İncelemesi

_2026-06-04 · Otonom tek-tur review · paket branch_

> Kapsam: 6 dosya (otonom_trader, gunluk_bomba, tahmin_motoru_v2, risk_yonetimi,
> anka_api, backtest_bist). Her bulgu önem (🔴/🟡/🟢) + dosya:satır + kanıt.
> Satır numaraları doğrudan okumayla doğrulandı, uydurma yok.

## Özet Tablo

| # | Önem | Dosya | Bulgu | Durum |
|---|---|---|---|---|
| 1 | 🔴 | otonom_trader.py | gunluk_bomba.json zinciri kopuk (tarama "skor" yazıyor, alış "bomba_skor" okuyor) | ✅ DÜZELTİLDİ (c72d99f) |
| 2 | 🟡 | otonom_trader.py | Etkin alış eşiği 25 (hibrit veto), ama MIN_BOMBA_SKOR_ALIS=15 — kafa karıştırıcı | AÇIK |
| 3 | 🟡 | otonom_trader.py | Bayat yollar: C:\Robot + `\\Mac\Home\adsız klasör\...` | AÇIK |
| 4 | 🟢 | otonom_trader.py | tek_dongu() 09:05 alışı atlar (tasarım, manuel test güvenliği) | BİLGİ |
| 5 | 🟡 | tahmin_motoru_v2 | Train/test split kronolojik değil → manşet AUC iyimser (gerçek ~0.57) | AÇIK (raporlama) |
| 6 | 🟡 | tahmin_motoru_v2 | early_stopping eval_set = test set → leak | AÇIK (raporlama) |
| 7 | 🟢 | tahmin_motoru_v2 | Triple-barrier aynı-bar üst önce → etiket iyimser | BİLGİ |
| 8 | 🟡 | risk_yonetimi | Kelly/ATR/sektör canlı alış yoluna bağlı değil (sabit sizing kullanılıyor) | AÇIK |
| 9 | 🟢 | risk_yonetimi | SEKTOR_MAP eksik, çok hisse "diger"e düşüyor | BİLGİ |
| 10 | 🟢 | anka_api | time_in_force parametresi alınıp kullanılmıyor (ValidityType hardcoded 0) | BİLGİ |
| 11 | 🟡 | backtest_bist | Rapor metni "şu an 25" bayat + 1-gün tutma modeli canlıyla uyuşmuyor | AÇIK |

---

## 🔴 ACİL (canlıyı bozar)

### 1. gunluk_bomba.json zinciri kopuk — ✅ DÜZELTİLDİ
**Dosya:** `otonom_trader.py` (tarama `gorev_08_30_tarama` + alış `gorev_09_05_otonom_alis`)
**Kanıt:** Tarama görevi sonucu `otonom_state.json`'a `"skor"` anahtarıyla yazıyordu;
09:05 alış görevi ise `gunluk_bomba.json`'ı `"bomba_skor"` anahtarıyla okuyor.
İki dosya/şema birbirine bağlı değildi → alış görevi her gün boş liste görüp
**hiç alım yapamıyordu** (~1 aydır).
**Düzeltme (commit c72d99f):** `_gunluk_bomba_yaz(top5, rejim)` helper'ı eklendi,
tarama sonrası doğru şemayla (`bomba_skor`, `ml`, `teknik`, `fiyat`, `atr_pct`,
`sebepler`) `gunluk_bomba.json` yazılıyor. Alış görevine **tarih guard'ı** eklendi:
rapor bugüne ait değilse alış atlanıyor (bayat dosyayla yanlış alım önlendi).
**Kanıt (test):** Şema round-trip — THYAO+ASELS eşik 15'i geçiyor, SASA kara
listeyle eleniyor, KCHOL eşik altı, sebepler okunabilir, bayat-tarih guard tetikleniyor.

---

## 🟡 DİKKAT (canlıyı bozmaz, ama yanıltıcı / borç)

### 2. Etkin alış eşiği 25, ama sabit 15 yazıyor
**Dosya:** `otonom_trader.py:256` (`MIN_BOMBA_SKOR_ALIS = 15`),
hibrit veto `otonom_trader.py:715` (`if s["bomba_skor"] >= 25:`),
`gunluk_bomba.py:667` (CLI `min_skor=25`).
**Kanıt:** Tarama yoluna giren skorlar zaten 25 eşiğinden süzülüyor; dolayısıyla
alış görevindeki `MIN_BOMBA_SKOR_ALIS=15` pratikte **hiç bağlamıyor** — etkin eşik 25.
Kullanıcının "FILTRE=25" beklentisi davranışsal olarak DOĞRU; bellekteki sabit 15
yanıltıcı görünüyor ama sonuca etkisi yok.
**Öneri:** İki yol tek sabite bağlanmalı (tek kaynak). Şimdilik davranış doğru,
sadece dokümantasyon/kod netliği borcu.

### 3. Bayat yollar (deploy hedefi + Mac kopyalama)
**Dosya:** `otonom_trader.py:53` (`WIN_DEPLOY = r"C:\Robot"`),
`otonom_trader.py:180` (`dosya_windows_kopyala` → `\\Mac\Home\adsız klasör\...`),
`otonom_trader.py:188` (`bomba_listesi_guncelle` → `aktif_bombalar.txt` C:\Robot'a).
**Kanıt:** Mac paylaşım yolu artık geçersiz (eski Parallels kurulumu). C:\Robot
MatriksIQ robot dizini — canlıda var ama Mac kopyalama ölü kod.
**Öneri:** Mac kopyalama bloğu kaldırılmalı veya env-guard'a alınmalı (fail-safe:
zaten try/except'te, canlıyı bozmuyor — sadece her çalışmada hata logluyor).

### 5. ML train/test split kronolojik değil
**Dosya:** `tahmin_motoru_v2.py:686-688` (`split = int(len(X) * 0.85)`).
**Kanıt:** Çok-hisseli birleştirilmiş frame üzerinde pozisyonel split → zaman
sızıntısı. Manşet AUC iyimser çıkıyor. **Gerçek AUC** `purged_walk_forward`
(satır 477) ile ~0.57. Bu canlıyı BOZMAZ — model zaten eğitilmiş .pkl'den
yükleniyor; sadece raporlanan AUC abartılı.
**Öneri:** Manşet AUC raporu purged walk-forward sonucunu göstermeli (3d işi).

### 6. early_stopping eval_set = test set
**Dosya:** `tahmin_motoru_v2.py:702-712` (`early_stopping_rounds=50`,
`eval_set=[(X_test, y_test)]`).
**Kanıt:** Erken durdurma test setine bakıyor → aynı set üzerinde AUC iyimser.
#5 ile aynı kök neden (validation hijyeni). Canlıyı bozmaz.

### 8. Risk yönetimi canlı alış yoluna bağlı değil
**Dosya:** `risk_yonetimi.py` (`RiskYoneticisi`, `kelly_pozisyon_hesapla:68`,
`sinyal_degerlendir:211`) vs `otonom_trader.py:601`
(`adet = int(MAX_POZISYON_TL / fiyat)`, `MAX_POZISYON_TL=20000` satır 255).
**Kanıt:** Canlı 09:05 alış sabit TL sizing kullanıyor; Kelly/ATR-stop/sektör
korelasyon kontrolü devreye girmiyor. Modül yazılmış ama bağlanmamış.
**Öneri:** Canlı trading mantığı değişikliği → main'e gidecek, kullanıcı onayı
gerekir. Bu turda PAKET'te bırakılmalı, otomatik main'e alınMAMALI.

### 11. backtest_bist bayat metin + model uyumsuzluğu
**Dosya:** `backtest_bist.py:225` (`"MIN_BOMBA_SKOR_ALIS = {e} (şu an 25)"`),
tutma modeli `backtest_bist.py:151-160` (al kapanış, ertesi kapanış sat),
aynı-bar stop `:157-158` (tam -%3).
**Kanıt:** 1-günlük tutma modeli, canlının çok-günlü trailing stop stratejisine
uymuyor → backtest sonucu canlı davranışı temsil etmiyor. "şu an 25" metni
elle yazılmış, sabitle senkron değil.
**Öneri:** Backtest çok-günlü tutma + trailing'i modellemeli (3d işi).

---

## 🟢 BİLGİ (kasıtlı tasarım / küçük borç)

### 4. tek_dongu() 09:05 alışı atlar
**Dosya:** `otonom_trader.py:1082-1092`.
**Kanıt:** Manuel tek-tur testte canlı emir tetiklenmesin diye alış görevi
atlanıyor — KASITLI güvenlik. tetikle_simdi.flag self-trigger (satır 1064-1075)
de başlangıçta kontrollü.

### 7. Triple-barrier aynı-bar üst-bariyer önce kontrol
**Dosya:** `tahmin_motoru_v2.py:458-467` (`hedef_olustur`).
**Kanıt:** Aynı barda hem üst hem alt bariyer değerse üst önce kontrol edilip
etiket=1 veriliyor → eğitim etiketi hafif iyimser. Marjinal etki.

### 9. SEKTOR_MAP eksik
**Dosya:** `risk_yonetimi.py:130-139`.
**Kanıt:** Çok ticker "diger" sektörüne düşüyor → sektör korelasyon limiti zayıf.
Zaten #8 nedeniyle canlıda devrede değil.

### 10. anka_api time_in_force kullanılmıyor
**Dosya:** `anka_api.py:143-194` (`alis_emri`), `:196-242` (`satis_emri`).
**Kanıt:** `time_in_force` parametresi alınıyor ama ValidityType=0 hardcoded.
Emir gönderme + auto-reconnect + hata yönetimi sağlam. Küçük API tutarsızlığı.

---

## Sonuç

- **Tek gerçek 🔴** zaten 3b'ydi (gunluk_bomba.json zinciri) → **DÜZELTİLDİ** (c72d99f).
  Bu, botun ~1 aydır neden hiç alım yapmadığının kök nedeniydi.
- Geri kalan 🟡'ler **canlıyı bozmuyor**: ya validation-raporlama hijyeni (#5,#6),
  ya ölü kod/bayat metin (#3,#11), ya bağlanmamış iyileştirme (#8).
- 🟡 #2 (eşik 15 vs etkin 25): kullanıcının "FILTRE=25" beklentisi DAVRANIŞSAL
  DOĞRU — bot etkin 25 eşiğiyle alıyor.
- FAZ 2'de güvenli 🟡'ler paket'te düzeltilecek; canlı trading mantığı (#8 risk
  entegrasyonu) main'e alınMAYACAK (kullanıcı onayı gerekir).
