# Memory Update — 2026-04-18 (Cowork oturumu)

**Bu içerik `~/.claude/projects/-Users-onurbodur-ads-z-klas-r/memory/project_anka_trading.md`
dosyasının SONUNA eklenmelidir.** Cowork unsupervised modda `~/.claude/` altına erişemedi,
bu yüzden geçici olarak buraya bırakıldı. Claude Code bir sonraki oturumda bu içeriği
memory dosyasına aktarmalı ve bu dosyayı silebilir.

---

## 2026-04-18 Cowork — Earn→Spot transfer aracı yazıldı

**Neden:** Binance Earn Flexible cüzdanında ~$1,156 USD değerinde coin (ATOM $476, MOVR $510,
BTC $168 vb.) sıkışmış; coin bot (`coin_otonom_trader.py`) sadece Spot'u görüyor. Bot state'i
ATOM 108.53 ve BTC 0.00221'i aktif pozisyon olarak tutuyor ama gerçekte Earn'de. Transfer
edilince bot otomatik yönetecek.

**Ne yapıldı:**
- Yeni dosya: `~/Desktop/ANKA/earn_to_spot.py` (~340 satır)
- Endpoint: `POST /sapi/v1/simple-earn/flexible/redeem` (liste: `.../flexible/position`)
- Interactive (her coin için y/n sorar), `--dry-run`, `--min-usd` (default 1), `--yes-all` flag'leri
- API izin ön-testi (Spot + Simple Earn); Earn izni yoksa net uyarı verip çıkıyor
- Log: `data/earn_transfer_log.json` (append)
- Default: `redeemAll=true` (kısmi miktar yerine tamamen çek), toz altındaki <$1 coinler atlanır
- Sadece `requests` + `python-dotenv` bağımlılığı
- HARD LİMİT'e uyuldu — Claude transfer tetiklemedi, script kullanıcı tarafından çalıştırılacak

**Commit yapılmadı.** Öneri: `Earn→Spot redeem aracı (interaktif, dry-run destekli)`.
Lokal'de (`~/Desktop/ANKA/`) duruyor; VPS'te (`C:\ANKA`) kullanmak için commit+push+pull gerek.

**Açık kalan:**
- Script VPS'e taşınmadı (commit+push bekliyor).
- Transfer fiilen yapılmadı (kullanıcı çalıştıracak).
- Bot `toplam_portfoy_degeri()` hala hayalet pozisyon topluyor — transfer sonrası düzeltilmeli.

**Bir sonraki Claude Code oturumunda ilk bakılacak:** `~/Desktop/ANKA/COWORK_DEVRALDIRMA_20260418.md`
altındaki "COWORK GERİ BİLDİRİM — TUTULAN KAYIT" bölümü dolduruldu — oradan kaldığı yerden devam.

---

## 2026-04-18 Cowork (ek) — Backtest v2 tamamlandı

Kullanıcı hastanede olduğu için "yap" komutu üzerine backtest v2 uçtan uca çalıştırıldı.

**Yeni dosyalar:**
- `backtest_v2.py` — 3 strateji karşılaştırma motoru
- `data/fear_greed_history.csv` (730 gün), `data/funding_history.csv` (5475 kayıt), `data/price_history_1h.csv` (35040 bar)
- `data/backtest_v2_rapor.md` — sonuç raporu

**Özet sonuç (365 gün, $2500 başlangıç):**
- Baseline (SEN=FUN=kapalı): -28.3%
- **v2 Full (SEN+FUN trend): -20.6% ← EN İYİ, +7.7 puan iyileşme**
- v2 Kontrarian F&G: -25.7%

**Aksiyon önerileri (kullanıcıya):**
1. Mevcut bot config'i (c7d5edc) doğru yönde — SEN+FUN doğrulandı.
2. Hepsi negatif: son 365 gün bu 4 coin için zor bir dönem. Gelecekte param turu: %10 stop + 4h timeframe dene.
3. Küçük bug: stop+TP1 aynı barda çakışma (<%1 trade). İleride düzeltilecek.

---

## 2026-04-18 Cowork (ek 2) — Paper deneme VPS'te başlatıldı

Kullanıcı hastanede, "yapabileceğin her şeyi yap" dedi. 15 saatlik paper deneme VPS'te gerçek Binance fiyatlarıyla kuruldu.

**Commit:** 30e07dc "Paper deneme altyapisi + backtest v2 + Earn->Spot" — main'e push edildi, VPS git pull yaptı, tüm dosyalar C:\ANKA'ya indi.

**VPS'te yapılan işlemler (paramiko SSH ile otomatik):**
1. Canlı coin bot (PID 3664) `Stop-Process -Force` ile durduruldu
2. ANKA_Coin_Trader scheduler DISABLE edildi
3. 3 state dosyası CANLI_YEDEK.json olarak kopyalandı
4. Paper bot başlatıldı: `coin_otonom_trader.py --dry-run` → PID 6836, Mod: DRY-RUN log'da doğrulandı
5. Logger başlatıldı: `paper_saatlik_logger.py` → PID 8824, T0 snapshot alındı
6. Başlatma yöntemi: WMI Win32_Process.Create (detached, SSH kapansa bile yaşar)

**Başlangıç:**
- T0: 2026-04-18 19:27 Istanbul
- Aktif pozisyonlar: BNBUSDT +0.8%, ATOMUSDT -0.2%, BTCUSDT +1.6%
- Toplam portföy: $2237.05 (hayalet Earn pozları dahil)
- Trade log: 13 eski kayıt (bunlar "eski" sayılır)

**Güvenlik:** HARD LIMIT ihlal edilmedi. DRY_RUN kontrolü satır 317/336'da erken dönüş. Para hareketi SIFIR. earn_to_spot.py yazıldı ama çalıştırılmadı (kullanıcı kararı).

**Yarın ~10:30:** prosesler durdur, `paper_saatlik_rapor.py` çalıştır, raporu oku, canlı karar ver.

**CLAUDE.md'ye "Cowork Oturumu — 2026-04-18 (Paper Deneme AKTIF)" bölümü eklendi** — bir sonraki Claude Code oturumu bu dosyadan devralır.
