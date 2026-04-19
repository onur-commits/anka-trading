# ANKA Trading System - Claude Code Rehberi 
. 
## Sistem Ozeti 
ANKA, BIST (Borsa Istanbul) ve Kripto (Binance) icin otonom trading sistemidir. 
VPS uzerinde 7/24 calisir. Mac'ten SSH ile yonetilebilir. 
. 
## VPS Bilgileri 
- IP: 78.135.87.29 
- OS: Windows Server 2022 
- User: Administrator 
- SSH: Port 22 (aktif, otomatik baslatma) 
- Python: 3.12.8 (C:\Program Files\Python312\python.exe) 
- Git: 2.47.1 (C:\Program Files\Git\bin\git.exe) 
- Proje: C:\ANKA 
. 
## Calisan Servisler 
- BIST Dashboard: http://78.135.87.29:8501 (Streamlit, app.py) 
- COIN Dashboard: http://78.135.87.29:8502 (Streamlit, coin_dashboard.py) 
- Auto-startup: Registry HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\ANKA_Trading 
. 
## Binance API 
- .env dosyasinda: BINANCE_API_KEY ve BINANCE_API_SECRET 
- IP Restriction: 78.135.87.29 
- Izinler: Reading + Spot Trading 
- Withdrawal: KAPALI (guvenlik) 
. 
## Dosya Yapisi 
### BIST Modulleri 
- app.py - Ana BIST dashboard (Streamlit, port 8501) 
- anka_scanner.py - Hisse tarama motoru 
- sabah_scanner.py - Sabah taramasi 
- hibrit_scanner.py - Hibrit tarama 
- gunluk_bomba.py - Gunluk bomba skor hesaplama 
- tahmin_motoru.py / tahmin_motoru_v2.py - ML tahmin motorlari (V1 deprecated, V2 aktif)
- tahmin_motoru_v3.py - ML V3 Stacking Ensemble (Level-2 meta-model, Optuna, calibration)
- paper_trader.py - Pessimist Paper Trading (slippage, partial fill, market impact sim)
- motor_v3.py - V3 trading motoru 
- anka_api.py - MatriksIQ REST API (TCP 18890) 
- risk_yonetimi.py - Risk yonetimi (ATR stop, Kelly Criterion) 
- anka_karar_verici.py - Karar verici modul 
- anka_panel_kurallari.py - Panel kurallari 
- anka_watchdog.py - Sistem izleme 
- dogruluk_kontrol.py - Tahmin dogruluk kontrolu 
- veri_isleyici.py - Veri isleme 
. 
### Kripto Modulleri 
- coin_dashboard.py - COIN dashboard (Streamlit, port 8502) 
- coin_trader.py - Binance API trader (BinanceClient sinifi) 
- coin_fullscan.py - Tam coin taramasi 
- coin_katmanli_scan.py - Katmanli tarama 
- coin_strateji.py - Kripto stratejileri 
- coin_ajanlar.py - Multi-agent kripto sistemi 
- coin_ai_egitim.py - Kripto ML egitim 
. 
### Ortak Moduller 
- bot.py - Temel bot altyapisi 
- otonom_trader.py - Otonom trader 
- alpha_v2_bot.py - Alpha V2 bot 
- anka_v2.py - ANKA V2 motor 
- haber_ajan.py - Haber ajani 
- haber_sentiment.py - Haber sentiment analizi 
- kontrol_paneli.py - Kontrol paneli 
- matriks_scraper.py - MatriksIQ scraper 
- bomba_robot_log_bridge.py - MatriksIQ robot log koprusu (SORUN-009) 
- v3_bridge_writer.py - V3 bridge writer 
- v3_risk_motor.py - V3 risk motoru 
- anka_ogrenme.py - Ogrenme modulu 
- anka_scalper.py - Scalper modul 
- anka_ai_egitim.py - BIST ML egitim 
. 
### Dizinler 
- data/ - Veri dosyalari 
- logs/ - Log dosyalari 
- models/ - ML modelleri (.pkl, .json) 
- pages/ - Streamlit sayfalari 
- matriks_iq/ - MatriksIQ dosyalari 
. 
## Bomba Skor Sistemi 
0-100 arasi puanlama: ML (%40) + Teknik (%25) + Momentum (%20) + Hacim (%15) 
ML: XGBoost + LightGBM + MLP ensemble, 73 feature 
. 
## Panel Kurallari 
- Fat-finger limiti: 30.000 TL 
- Gunluk emir limiti: 50 
- Stop-loss: ATR bazli 
. 
## MatriksIQ Entegrasyonu 
- TCP port 18890, JSON + char(11) terminator 
- C# stratejileri: BOMBA_*.cs dosyalari 
- anka_api.py uzerinden REST API 
. 
## SSH Erisim (Mac'ten) 
ssh Administrator@78.135.87.29 
Sifre: .env dosyasinda veya kullanicidan sor 
. 
## Yeni Moduller (2026-04-09)
- anka_muhendis.py - Otonom bakim & onarim (7/24, 30dk kontrol, otomatik restart)
- pages/2_ANKA_Danisman.py - Zeka sohbet paneli (4 ajan analiz, komisyon dahil)
- ANKA_BILINEN_SORUNLAR.md - Bilinen sorunlar veritabani (Muhendis okur)
- MATRIKS_IQ_STRATEJI_REHBER.md - 66 built-in strateji + API referansi
.
## Yeni Moduller (2026-04-16)
- tahmin_motoru_v3.py - V3 ML: Stacking Ensemble, sample weighting, feature interaction, Platt calibration, Optuna tuning
- paper_trader.py - Pessimist Paper Trading: MarketFriction (slippage/latency/partial fill/market impact), PaperTrader (order lifecycle, trailing stop, kill-switch, sector control, perf reporting)
- bomba_robot_log_bridge.py - MatriksIQ robot log koprusu (SORUN-009 cozumu)
- app.py guncellendi: V2 import, tab error boundaries, cache_resource, ensemble feature importance
- coin_dashboard.py guncellendi: error handling, alarm fix, cross-platform notifications, auto-refresh
- coin_trader.py guncellendi: dotenv, dry-run mode, position tracking, bot loop, risk limits
- sabah_scanner.py guncellendi: V2 import, risk_yonetimi + paper_trader entegrasyonu
- anka_scanner.py guncellendi: logging module, risk validation, paper trade kaydi, VPS path fallback
.
## Onemli: Midas API Durumu
- Midas Menkul bireysellere API/algo erisimi VERMIYOR (kesinlesti)
- Alternatif: Algolab (Deniz Yatirim) veya Tacirler + MatriksIQ
- Paper Trading modu aktif — gercekci simulasyon ile test devam ediyor
.
## Gelistirme Notlari 
- Windows'ta PYTHONUTF8=1 environment variable gerekli (Turkce karakter) 
- Python calistirirken HER ZAMAN -X utf8 flag kullan
- Streamlit --server.headless true --server.address 0.0.0.0 ile baslatilmali 
- .env dosyasi git'e EKLENMEMELI (.gitignore'da) 
- Bilinen sorunlar ANKA_BILINEN_SORUNLAR.md dosyasinda
- Erisim noktalari ayni dosyada ve bu dosyada
.
## Otonom Trading (2026-04-16 CANLI)
- MatriksIQ TCP API uzerinden Midas'a GERCEK emir gonderilebiliyor
- otonom_trader.py v3: Tam otonom karar dongusu
  - 09:05 Bomba skor >= 60 olan hisselere market order
  - 11:00/13:00/14:00 Stop-loss ve trailing stop kontrolu
  - 17:30 Gun sonu tum pozisyonlari kapat (intraday)
  - Kill-switch: %10 drawdown'da islem durur
  - Risk: Kelly Criterion lot, max 5 pozisyon, sektor limiti %40
- anka_api.py: Market order default, ClientOrderID, ExchangeId, ValidityType eklendi
- alis_emri(symbol, adet) → fiyat=0 market, fiyat>0 limit
- satis_emri(symbol, adet) → ayni mantik
- Hesap: Midas [115], AccountId: 0~2205905, ExchangeId: 4
- Calistirma: python otonom_trader.py (canli) veya --paper (simule)
.
## Organizasyon
- CEO: Kullanici (kararlar, yon)
- Direktor: Claude (strateji, gelistirme)
- ANKA Danisman: Hisse analiz (4 ajan: TECHNO, VOLUME, MACRO, FUNDA)
- ANKA Muhendis: Teknik bakim, onarim, hata tespiti
- Otonom Trader: TAM OTONOM — tarama, karar, emir, stop, gun sonu satis
.
## Cowork Oturumu — 2026-04-18 (Paper Deneme AKTIF)
Cowork (onur@miknatis.net) tarafindan baslatildi. Claude Code bir sonraki oturumda devralmali.

### Yeni dosyalar (commit 30e07dc, main'de push edildi)
- earn_to_spot.py — Binance Earn → Spot redeem araci (interaktif, --dry-run, --min-usd, --yes-all)
- backtest_v2.py — 3 strateji karsilastirma (Baseline/v2 Full/Kontrarian F&G)
- paper_saatlik_logger.py — Saatlik snapshot logger (bot kodu degismedi, DISARIDAN okuyor)
- paper_saatlik_rapor.py — Saatlik rapor okuma + markdown ciktisi
- PAPER_DENEME_TALIMAT.md — 15 saatlik deneme adim adim
- _memory_update_20260418.md — Memory'ye aktarilmasi gereken notlar
- data/fear_greed_history.csv (730 gun), data/funding_history.csv (5475 kayit)
- data/price_history_1h.csv (35040 bar), data/backtest_v2_rapor.md
- _paper_bot.bat, _paper_logger.bat — VPS'te paper baslatma wrapper'lari

### Backtest v2 sonucu (365 gun, 4 coin, $2500)
- Baseline (SEN=FUN=kapali): -28.3%
- v2 Full (SEN+FUN trend, MEVCUT BOT CONFIG): -20.6% ← EN IYI, +7.7 puan
- Kontrarian F&G (F&G tersine): -25.7%
- Yorum: Mevcut config (c7d5edc) dogru yon. Tum stratejiler negatif — son 365 gun bu 4 coin icin zor donem.

### Paper Deneme — 2026-04-18 19:27 baslangic (VPS'te CALISIYOR)
- VPS: C:\ANKA, Windows 2022, 78.135.87.29
- Canli coin bot DURDURULDU + ANKA_Coin_Trader scheduler DISABLE edildi
- State yedekleri: data/coin_otonom_state.CANLI_YEDEK.json, data/coin_otonom_trades.CANLI_YEDEK.json, data/coin_pozisyonlar_aktif.CANLI_YEDEK.json
- Paper bot: PID 6836 — `python -X utf8 -u coin_otonom_trader.py --dry-run` (Mod: DRY-RUN dogrulandi, log'da gorundu)
- Logger: PID 8824 — `python -X utf8 -u paper_saatlik_logger.py` (T0 snapshot alindi, cycle #14, 3 aktif poz: BNB +0.8%, ATOM -0.2%, BTC +1.6%)
- Config: c7d5edc (SEN+FUN aktif, MIN_SKOR=65, stop %7, TP1=+8 yarim, TP2=+15 tam, trailing +3/-3)
- Loglar: C:\ANKA\logs\paper_bot.err.log (bot stderr=INFO), C:\ANKA\logs\paper_logger.out.log
- State dosyasi: C:\ANKA\data\paper_saatlik.json (her saat append, T0...T+15h)
- Guvenlik: coin_otonom_trader.py satir 317/336'da `if DRY_RUN: return {"status": "DRY_RUN"}` — para hareketi SIFIR
- Baslangic portfoy: $2237.05 (hayalet poz dahil — transfer edilmemis Earn coinleri)

### Paper baslatma prosedurleri (BIR SONRAKI CLAUDE CODE OKUSUN)
Ayni adimlari tekrar calistirmak gerekirse:
1. SSH: `sshpass -p '*AYiMn5ZkX' ssh Administrator@78.135.87.29` (Mac'ten)
2. VPS'te: `cd C:\ANKA && git pull`
3. Canli bot durdur: `Get-CimInstance Win32_Process | Where CommandLine -like '*coin_otonom_trader*' | ForEach {Stop-Process -Id $_.ProcessId -Force}`
4. Scheduler disable: `schtasks /Change /TN ANKA_Coin_Trader /DISABLE`
5. State yedekle: `copy data\coin_otonom_state.json data\coin_otonom_state.CANLI_YEDEK.json` (trades ve pozisyonlar da)
6. Paper bot baslat (WMI ile detached, SSH kapansa yasatir):
   ```
   powershell -Command "Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd /c C:\ANKA\_paper_bot.bat'; CurrentDirectory='C:\ANKA'}"
   ```
7. Logger baslat (ayni mantik, `_paper_logger.bat`)
8. Saglik kontrol: `dir data\paper_saatlik.json` + `Get-Content logs\paper_bot.err.log -Tail 20`

### Paper kapatma + rapor (yarin ~10:30)
1. `Get-CimInstance Win32_Process | Where CommandLine -like '*--dry-run*' -or CommandLine -like '*paper_saatlik_logger*' | ForEach {Stop-Process -Id $_.ProcessId -Force}`
2. `cd C:\ANKA && python -X utf8 paper_saatlik_rapor.py && type data\paper_saatlik_rapor.md`
3. Canli bot geri baslatma (karar pozitifse DEGIL): `schtasks /Change /TN ANKA_Coin_Trader /ENABLE` + state geri yukle (`copy *.CANLI_YEDEK.json *.json`)

### HARD LIMIT (onceki oturumdan miras, ihlal edilmedi)
- Cowork Claude: transfer/alim/satim TETIKLEMEZ — sadece script yazar, kullanici calistirir
- earn_to_spot.py yazildi ama calistirilmadi — kullanici karari

### Acik konular
- `toplam_portfoy_degeri()` hayalet poz topluyor (ATOM/BTC Earn'de, Spot'ta yok). earn_to_spot.py ile transfer sonrasi duzeltilmeli.
- Backtest'te stop+TP1 ayni barda cakismasi (<%1 trade). Kozmetik, ileride fix.
- MOVRUSDT futures 4h funding (8h degil) — backtest'te 2190 kayit dogru.

### Kaynak dosyalar (bir sonraki Claude Code icin)
- `~/Desktop/ANKA/COWORK_DEVRALDIRMA_20260418.md` — tam devir notu (onceki oturum + bu oturum)
- `~/Desktop/ANKA/_memory_update_20260418.md` — memory'e eklenmesi gereken ozet
- `~/Desktop/ANKA/PAPER_DENEME_TALIMAT.md` — deneme prosedurleri

## Cowork Oturumu — 2026-04-19 (Paper sonuc + Backtest turu + A/B setup)

### Paper deneme 15h sonucu (2026-04-18 19:27 → 2026-04-19 09:27)
- Toplam alim: **0** (14 saat boyunca skor 65 esigini gecen coin olmadi, en yuksek ATOM 54.2)
- Toplam satis: **2** (ikisi de STOP_LOSS: ATOM @ $1.765, BNB @ $620.59)
- Ilk aktif poz: 3, son: 1
- Rapor: `C:\ANKA\data\paper_saatlik_rapor.md`
- **Yorum: momentum bot bu piyasa kosullarinda calismiyor**

### Yeni backtest: Grid Trading (2 yil, BTC+ETH)
- Dosya: `grid_backtest.py` (+ `data_fetcher_2yil.py` yeni 2 yillik veri)
- Veri: `data/price_history_2yil.csv` (BTC 17521 + ETH 17521 bar)
- 10 konfigurasyon (FullRange 20/40/80 kademe + DarAralik40 20/40) — **hepsi negatif**
- En iyi: ETH DarAralik40_20k -13.67% (B&H -22.76%'dan +9.1 puan iyi ama yine zarar)
- BTC'de B&H +20.70%, grid -4% ile -15% arasi → BTC trend piyasasinda grid kotu
- Rapor: `data/grid_backtest_rapor.md`

### Yeni backtest: DCA (2 yil, haftalik $25)
- Dosya: `dca_backtest.py`
- 4 varyant (BTC only, ETH only, 50/50, RSI_dip) — **hepsi negatif**
- DCA_BTC_only: -8.16%, DCA_ETH_only: -15.47%, DCA_50_50: -11.81%, DCA_RSI_dip: -10.60%
- Referans: BTC B&H +20.52%, ETH B&H -22.88%
- Rapor: `data/dca_backtest_rapor.md`
- **Yorum: 2 yil icinde kazanan TEK strateji "bastan BTC al, sat-ma" (+20.5%). Her aktif strateji kaybediyor.**

### VPS temizlik (2026-04-19)
- `anka_rotasyon.py` iki kopya calisiyordu (PID 7096 eski, 8324 yeni) → 8324 kapatildi
- Kalan Python prosesleri: streamlit BIST (8501), streamlit COIN (8502), otonom_trader.py (BIST), coin_otonom_trader.py (CANLI, --dry-run YOK), anka_muhendis.py, anka_rotasyon.py (tek)
- `ANKA_Coin_Trader` scheduler DISABLED kaldi (paper'dan miras) → coin bot manuel calisiyor
- Onemli: paper sonrasi canli coin bot yeniden basladi (PID 7780), su an BTC pozisyonu stop'a takilmis (bakiye su an sadece BNB $225)

### A/B Karsilastirma Deneyi (CANLI, 30 gun, 2026-04-19 → 2026-05-19)
**Amac:** Bot vs BTC Buy&Hold hangisi daha iyi? Gercek para, gercek piyasa.

**Kurulum:**
- Dosya: `ab_karsilastirma.py` (VPS'te `C:\ANKA\ab_karsilastirma.py`)
- T0: 2026-04-19 11:06 UTC, BTC fiyat $75238.76
- Bot tarafi: Binance Spot gercek bakiye (T0: $224.63, sadece BNB)
- B&H tarafi: T0'da $224.63 → 0.002986 BTC (sanal, dokunulmayacak)
- Esit sermaye (B&H = bot T0 degeri)
- State: `C:\ANKA\data\ab_karsilastirma.json`
- Rapor: `C:\ANKA\data\ab_rapor.md`

**Scheduler:** `ANKA_AB_Karsilastirma` → her gun 23:00 (VPS saati), SYSTEM user
- Wrapper batch: `C:\ANKA\_ab_karsilastirma.bat`
- Log: `C:\ANKA\logs\ab_karsilastirma.log`
- NextRun: 2026-04-19 23:00:00

**Flag'ler:**
- `python ab_karsilastirma.py` — snapshot al + rapor
- `--rapor` — sadece rapor uret
- `--reset` — T0 sifirla (yedekler eskiyi)

**Bot tarafi nasil hesaplaniyor:**
- `binance_hesap_bakiye()` → Spot'taki tum asset'leri al (free+locked)
- Her asset'i anlik USDT fiyatiyla carp
- Toplam USDT cinsinden "bot degeri"
- Bot alim/satim yaptikca bakiye kompozisyonu degisir ama toplam USDT degeri takip edilir

**B&H tarafi nasil hesaplaniyor:**
- T0'da sabit BTC miktari (0.002986) belirlendi, degismez
- Her snapshot'ta: BTC miktari × guncel BTC fiyat = B&H degeri
- Hic alim/satim YOK (sanal pozisyon)

**Karsilastirma:**
- Bot % = (bot_deger / bot_t0 - 1) × 100
- B&H % = (bh_deger / bh_t0 - 1) × 100
- Fark = Bot % - B&H % (+ = bot onde)

**30 gun sonra karar:**
- Bot onde → momentum strateji isiyor, devam
- B&H onde → momentum bot rafa, B&H'a don (2 yil backtest'in dedigi)

### Yeni dosyalar (2026-04-19)
- `~/Desktop/ANKA/grid_backtest.py` + `data/grid_backtest_rapor.md`
- `~/Desktop/ANKA/dca_backtest.py` + `data/dca_backtest_rapor.md`
- `~/Desktop/ANKA/data_fetcher_2yil.py` + `data/price_history_2yil.csv` (2 yil BTC+ETH 1h)
- `~/Desktop/ANKA/ab_karsilastirma.py` (VPS'te `C:\ANKA\ab_karsilastirma.py` + `_ab_karsilastirma.bat`)
- VPS scheduler: `ANKA_AB_Karsilastirma` (her gun 23:00)

### Acik konular (bir sonraki oturum icin)
- Commit + push gerek (ab_karsilastirma.py, grid_backtest.py, dca_backtest.py, CLAUDE.md update)
- `earn_to_spot.py` hala calistirilmadi (kullanici karari) — Earn'de hayalet ATOM/BTC/MOVR var
- Coin bot `toplam_portfoy_degeri()` hala hayalet poz topluyor
- A/B deneyi 30 gun surecek, her gun 23:00'te snapshot
- **ONEMLI:** Canli coin bot calismaya devam ediyor (kullanici karari)

### HARD LIMIT (devam ediyor)
- Cowork Claude: alim/satim/transfer TETIKLEMEZ
- Sadece script yazar, kullanici calistirir veya izleme altyapisi kurar
- A/B deneyinde: bot dogal olarak kendi islemlerini yapar (zaten canli), Cowork sadece snapshot alir
