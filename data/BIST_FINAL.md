# 🦅 BIST FINAL — Otonom Tur Sonucu + Yarın 09:05 Hazırlık

_2026-06-04 23:40 TR · Otonom 4-faz tur · kanıtlı_

## ⚠️ TEK AKSİYON GEREKLİ (canlı tetik — senin elin)

**Bot şu an ESKİ kodu çalıştırıyor.** PID 19772, başlangıç **15:37**; git pull
**23:39**'da geldi. Python süreci başlarken kodu RAM'e alır — diskteki 3b fix
çalışan botta **yok**. Fix'in yarın 09:05'te etkili olması için **bot restart şart.**

Restart olmadan: yarın 08:30 taraması eski kodla çalışır → `gunluk_bomba.json`
yazılmaz → 09:05 alış boş liste görür → **yine alım yapmaz** (1 aydır olan bug).

**Restart komutu (sen çalıştır):**
```bash
sshpass -p '*AYiMn5ZkX' ssh Administrator@78.135.87.29 "powershell -Command \"Get-CimInstance Win32_Process | Where-Object {\$_.CommandLine -like '*otonom_trader.py*'} | ForEach-Object {Stop-Process -Id \$_.ProcessId -Force}; Start-Sleep 3; Start-ScheduledTask -TaskName ANKA_OtonomTrader\""
```
Sonra doğrula (yeni PID + başlangıç saati 23:xx olmalı):
```bash
sshpass -p '*AYiMn5ZkX' ssh Administrator@78.135.87.29 "powershell -Command \"Get-CimInstance Win32_Process | Where-Object {\$_.CommandLine -like '*otonom_trader.py*'} | Select ProcessId\""
```

---

## ✅ Yarın 09:05 Hazırlık Checklist

| Kontrol | Durum | Kanıt |
|---|---|---|
| Kod canlıda (VPS HEAD = fix) | ✅ | `6605555 fix(3b)...` — git pull Fast-forward e5dbff5→6605555 |
| 3b fix diskte | ✅ | `def _gunluk_bomba_yaz` otonom_trader.py'de mevcut |
| FILTRE = 15 (etkin 25) | ✅ | satır 256 `MIN_BOMBA_SKOR_ALIS = 15`; tarama hibrit veto + CLI min_skor=25 ile etkin eşik 25 |
| MatriksIQ açık | ✅ | PID 12672 |
| data/ yazılabilir | ✅ | `_wtest.json` yazıldı+silindi |
| İç zamanlama doğru | ✅ | 08:30 tarama → 09:05 alış (otonom_trader.py:1035/1038) |
| VPS saati TR uyumlu | ✅ | VPS 23:39:40 = Mac TR 23:39:48, TZ=Turkey Standard Time (fark ~8 sn, sapma yok) |
| **Fix çalışan botta aktif** | ❌ | **PID 19772 eski kod (15:37 start) — RESTART GEREK** |

**Sonuç:** main→VPS deploy OK, FILTRE=15 (etkin 25), fix DİSKTE canlı, bot **RESTART GEREK**.

---

## Faz Faz Yapılanlar

### FAZ 1 — REVIEW ✅
`data/BIST_REVIEW.md` (commit d35eb46): 6 dosya, 11 bulgu, severity+satır+kanıt.
- Tek gerçek 🔴 = 3b zinciri (zaten düzeltildi).
- Kalan 🟡'ler canlıyı bozmuyor: validation-raporlama hijyeni (#5,#6),
  ölü kod (#3), bağlanmamış risk modülü (#8), bayat metin (#11).

### FAZ 2 — DÜZELT (paket) ✅
- **#3** `dosya_windows_kopyala`: .cs kaynak yolu bozuk `\\Mac\Home\adsız klasör\...`
  → yerel `IQ_DIR/BOMBA_*.cs` (commit 7e7ad57). py_compile OK.
- **#2** eşik netleştirme yorumu (değer değişmedi — davranış zaten doğru).
- **#11** backtest_bist rapor metni "şu an 25" → etkin eşik açıklaması.
- **Main'e GİTMEDİ** (kullanıcı onayı gerekenler, paket'te bekliyor):
  - **#8** risk yönetimi (Kelly/ATR/sektör) canlı alış yoluna bağlama — canlı
    trading mantığı değişikliği.
  - **#5/#6** ML train/test split + early_stopping leak düzeltme — model
    yeniden eğitimi gerektirir (3d işi).

### FAZ 3 — CANLI DEPLOY ✅ (restart hariç)
- Sadece **3b kritik fix** (c72d99f) main'e cherry-pick edildi → **tüm paket
  DEĞİL** (auth/docker/US market canlıya gitmedi, "birleştir" komutuna saklı).
- Rebase + push: `f27781c..6605555 main`.
- VPS git pull: Fast-forward, HEAD=6605555.
- Bot restart komutu yukarıda — **canlı tetik, senin elin.**

### FAZ 4 — KANIT ✅
Bu dosya.

---

## Paket'te Bekleyen (sıradaki "birleştir" / onay)
- FAZ 2 #3/#2/#11 düzeltmeleri (7e7ad57) — istersen ayrıca main'e alınır.
- 🟡 #8 risk entegrasyonu (canlı mantık — onay gerekir).
- 3d: ML AUC 0.57 feature engineering + validation hijyeni (#5/#6).
- 3c: auth/audit app.py entegrasyonu (platform/ isim çakışması engeli var).
