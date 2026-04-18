# ANKA Paper Mode — 15 Saatlik Deneme Talimatı

**Hedef:** Bot şu anki config'le (c7d5edc: SEN+FUN aktif, MIN_SKOR=65, stop=%7)
Binance gerçek fiyatlarıyla karar verir, ama **hiçbir emir gitmez**.
15 saat sonra rapor birlikte okunur, canlı karar verilir.

---

## Adım 1 — VPS'e bağlan

```
sshpass -p '*AYiMn5ZkX' ssh Administrator@78.135.87.29
```

---

## Adım 2 — Dosyaları VPS'e taşı

Mac'ten (yerel terminalde):

```
cd ~/Desktop/ANKA
git add earn_to_spot.py backtest_v2.py paper_saatlik_logger.py paper_saatlik_rapor.py \
        data/backtest_v2_rapor.md data/fear_greed_history.csv \
        data/funding_history.csv data/price_history_1h.csv
git commit -m "Paper deneme altyapisi + backtest v2"
git push
```

VPS'te:

```
cd C:\ANKA
git pull
```

---

## Adım 3 — Canlı coin bot'u durdur (ÖNEMLİ)

Şu an coin bot canlı modda çalışıyor olabilir. Paper ile aynı state'e yazarsa
veri karışır. Önce durdur.

VPS'te PowerShell:

```
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -like '*Python*' -and (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -like '*coin_otonom_trader*'
} | Stop-Process -Force
```

Ya da Task Scheduler'dan:
```
schtasks /End /TN ANKA_Coin_Trader
```

Durduğunu doğrula:
```
Get-CimInstance Win32_Process | Where-Object CommandLine -like '*coin_otonom_trader*' | Select ProcessId, CommandLine
```

Boş dönmeli.

---

## Adım 4 — State dosyalarını yedekle ve temizle

Paper deneme temiz başlasın. Mevcut state'i yedekle:

```
cd C:\ANKA\data
copy coin_otonom_state.json coin_otonom_state.CANLI_YEDEK.json
copy coin_otonom_trades.json coin_otonom_trades.CANLI_YEDEK.json
copy coin_pozisyonlar_aktif.json coin_pozisyonlar_aktif.CANLI_YEDEK.json 2>nul
```

---

## Adım 5 — Paper modda başlat

**3 ayrı terminal (veya 3 ayrı `start` komutu) gerekli.** PowerShell'de:

### Terminal 1 — Bot (dry-run)

```
cd C:\ANKA
python -X utf8 coin_otonom_trader.py --dry-run
```

Beklenen: "Mod: DRY-RUN" yazısı + 15 dakikada bir tarama döngüsü.

### Terminal 2 — Saatlik logger

```
cd C:\ANKA
python -X utf8 paper_saatlik_logger.py
```

Beklenen: `[logger] başlatıldı` + her saat T+1h, T+2h... snapshot.

### Terminal 3 (opsiyonel) — Log tail

```
cd C:\ANKA\logs
Get-Content coin_otonom.log -Tail 20 -Wait
```

Canlı log izlemek için.

---

## Adım 6 — 15 saat bekle

Başlangıç saati: _(başlarken not düş)_
Bitiş saati:     _(+15 saat)_

Bu süre boyunca:
- Terminal 1 ve 2 açık kalsın
- Bilgisayarı kapatma (VPS, uyku kapalı)
- Bir şey ters giderse bildirim gelir (varsa Telegram)

---

## Adım 7 — Rapor al

15 saat sonra, aynı VPS'te:

```
cd C:\ANKA
python -X utf8 paper_saatlik_rapor.py
type data\paper_saatlik_rapor.md
```

Beklenen: 15 satırlık saatlik tablo, alım/satış sayıları, sembol dağılımı.

---

## Adım 8 — Deneme bitir, canlı karar ver

Terminal 1 ve 2'yi `Ctrl+C` ile kapat.

Raporu paylaş — birlikte okuyacağız:
- Kaç alım sinyali geldi?
- Hangi skorlarda?
- Satışlar TP ile mi STOP ile mi çıktı?
- Genel bir "kâr sinyali" var mı?

Pozitifse: küçük sermayeyle (sadece $500) canlı başla.
Negatifse: param turu (stop %10, 4h timeframe) sonra tekrar paper.

---

## Güvenlik notları

- **Para hareketi SIFIR.** DRY_RUN=True olduğu sürece `alis_piyasa` ve
  `satis_piyasa` fonksiyonları erken dönüş yapar (coin_otonom_trader.py satır 317, 336).
- **State yedeklendi.** Canlı pozisyonlar `*.CANLI_YEDEK.json` olarak korunuyor.
  İstersen deneme sonrası geri yüklenebilir.
- **Bot kodu değişmedi.** Sadece harici bir "logger" eklendi — bot'u okuyor,
  yazmıyor.
- **Earn'deki coinler dokunulmadı.** ATOM/BTC/MOVR Earn'de faiz kazanmaya devam ediyor.

---

## Sorun çıkarsa

**Bot başlamıyor:**
```
cd C:\ANKA
python -X utf8 coin_otonom_trader.py --dry-run --tara
```
(tek tarama, hatayı gösterir)

**Logger başlamıyor:**
`data/coin_otonom_state.json` dosyasının var olduğundan emin ol. Bot en az bir
kere döngü tamamlamalı ki state yazılsın.

**İki bot aynı anda çalıştı (canlı + paper):**
ACİL: Canlı bot'u durdur. Paper bot'u kapat. `*.CANLI_YEDEK.json` dosyasından
state'i geri yükle:
```
copy coin_otonom_state.CANLI_YEDEK.json coin_otonom_state.json
copy coin_otonom_trades.CANLI_YEDEK.json coin_otonom_trades.json
```
Sonra canlı bot'u geri başlat (normal task scheduler).
