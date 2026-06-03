# ANKA + COIN TRADING SISTEMI -- BIRLESIK PANEL V2 DEGERLENDIRMESI

**Tarih:** 6 Nisan 2026
**Format:** Onceki Denetimden Bu Yana Degisikliklerin Incelenmesi (10 Akademisyen, 5 Tur)
**Kapsam:** ANKA V2/V3 (BIST) + COIN Trader (Kripto) tum alt sistemler
**Onceki Ortalama Not:** ANKA: C-/C (1.83/4.00) | COIN: F (0.42/4.00)

---

## ONCEKI DENETIMDEN BU YANA YAPILAN DEGISIKLIKLER OZETI

| # | Degisiklik | Etkilenen Sistem | Ilgili Eski Sorun |
|---|-----------|------------------|-------------------|
| 1 | Triple Barrier hedef fonksiyonu (TP/SL/Zaman) | ANKA ML | K-06 (Lookahead bias) |
| 2 | Feature secimi 73 -> 20 | ANKA ML | Y-07 (Boyut laneti) |
| 3 | Backtest: Sharpe 2.49, +7575% net (EMA+volume filtreli) | ANKA ML | K-11 (Alfa kaniti yok) |
| 4 | Ajan agirliklari 1276 islemden ogrenildi (FUNDA %61.6 en iyi, TECHNO %33.7 en kotu) | ANKA Karar | Y-10, Y-11 (Ajan bagimsizligi) |
| 5 | Panel kurallari: Kill-switch, sektor filtresi, komisyon kontrolu, emir dogrulama | ANKA Robot | K-08, K-09 (Risk yonetimi) |
| 6 | OnOrderUpdate tamamen yeniden yazildi (gercek dolum, rejected, cancelled, partial) | ANKA C# | K-03, K-04 (Hayalet pozisyon) |
| 7 | SendOrderSequential(false) + buyPending/sellPending mekanizmasi | ANKA C# | K-05 (Kilit sorunu) |
| 8 | Bridge'den tum parametreleri okuma (hard_stop, trailing_stop, profit_trigger, dry_run) | ANKA C# | Y-01 (Bridge tutarsizligi) |
| 9 | 6 yeni kripto ajan (Funding, OnChain, Sentiment, Liquidation, OrderBook, Correlation) | COIN | Coin: D- ML, F Risk |
| 10 | 533 coin paralel tarayici (SIKISMA/BIRIKIM evre tespiti) | COIN | Coin: D Roket tarayici |
| 11 | DipAvciBot (Fear+Whale+DCA kademeli giris) | COIN | Coin: F Risk yonetimi |
| 12 | Haber sentiment ajanı (CryptoPanic, Bloomberg HT, KAP, Fear&Greed) | ANKA+COIN | Yeni |
| 13 | Dogruluk kontrol AI (sinyal kayit + 24s sonra dogrulama) | ANKA+COIN | Yeni |
| 14 | Watchdog sistemi (process izleme, auto-restart, macOS bildirim) | Altyapi | K-02, K-10 (Tek nokta arizasi) |
| 15 | VPS satin alindi (78.135.87.29, Windows Server 2022) | Altyapi | Y-13 (VPS gecisi) |

### TESPIT EDILEN DEVAM EDEN SORUNLAR

| # | Sorun | Ciddiyet |
|---|-------|----------|
| A | Dogruluk kontrol'de HENUZ HICBIR sinyal kaydi yok (yeni baslatildi) | ORTA |
| B | Watchdog sadece 1 kez calistirildi, surekli dongu baslamamis | YUKSEK |
| C | BIST tarayicisi "zaten hareket etmis" hisseleri buluyor (AYEN, ASTOR) | YUKSEK |
| D | Coin SIKISMA tespiti XLM'de 100 skor verdi -- false positive riski | ORTA |
| E | BIST'te evre tespiti (SIKISMA/BIRIKIM) HENUZ yok, coin'de var | YUKSEK |
| F | Backtest'teki %7575 getiri EMA+volume filtreli -- overfitting riski | KRITIK |
| G | Max drawdown %47.28 -- tehlikeli yuksek | KRITIK |

---

## ROUND 1-5 OZET: PANEL BULGULARI VE KARARLAR

### Backtest Guvenilirligi (Round 2 -- 10/10 panel uzlasmasi)

- Sharpe 2.49 ve %7575 net getiri "cok iyi olmak icin cok iyi" sinirinda; panel GUVENMIYOR.
- `kar_esik_pct: 4.0`, `zarar_limiti_pct: -2.0` parametrelerinin backtest icinde optimize edilmis olmasi kuvvetle muhtemel -- CIRKIN overfitting riski.
- EMA+volume filtresi in-sample secilmis olabilir (data snooping).
- Sharpe 2.49 ile max drawdown %47.28 kombinasyonu TUTARSIZ; tipik beklenti %15-20 drawdown.
- 3 yillik backtest donemi (2023-2025) BIST'in en buyuk boga dalgasini kapsiyor; her momentum stratejisi bu donemde iyi gorunur.
- Win rate %47.46 ama ortalama kazanc (%3.43) > ortalama kayip (%2.48): asimetri Triple Barrier'in dogru calistigini gosteriyor -- tek olumlu sinyal.
- CPCV (Combinatorial Purged Cross-Validation) HALA YAPILMAMIS.

### C# / Emir Altyapisi (Round 1 -- piyasa mikro yapisi)

- `OnOrderUpdate` yeniden yazilmasi: gercek dolum fiyati, Rejected/Cancelled/PartiallyFilled ayrimi, buyPending/sellPending flag -- DOGRU ve EKSIKSIZ. Hayalet pozisyon sorunu COZULDU.
- `SendOrderSequential(false)`: 5 sembol eszamanli sinyal verebilir -- DOGRU.
- Kalan eksik: `sellPending=true` iken emir reddedilirse retry yok; pozisyon acik kalir.
- Kill-switch sadece REALIZE kayiplarda tetikleniyor; unrealized loss icin portfoy bazli koruma YOK.
- Sektor filtresi Python tarafinda; C# robot Python crash ederse koreleli pozisyon acabilir.

### Coin Sistemi (Round 3)

- 533 coin paralel tarayici muhendislik basarisi (8 thread, 1-2 dk); SIKISMA/BIRIKIM kavrami dogru.
- Kritik eksik: her coin icin sadece 50 mum (2 gunluk veri) -- evre tespiti icin en az 7-14 gun gerekli. Esikler istatistiksel temelsiz, arbitrary.
- 6 yeni ajan (`FundingAgent`, `OnChainAgent`, `SentimentAgent`, `LiquidationAgent`, `OrderBookAgent`, `CorrelationAgent`) YAZILMIS ama `coin_trader.py`'de CAGIRILMIYOR -- DEKORATIF. Bu en buyuk coin sorunu.
- `OnChainAgent` gercek on-chain veri degil; Binance 24h ticker'dan hacim/fiyat -- isim yaniltici.
- DipAvci (Fear+Whale+DCA, %33/%33/%34 kademeli giris) dogru strateji; ama sadece BTC/ETH/SOL'a bakiyor, 533 coin tarayiciyla baglantili degil.
- ML modeli hala AUC 0.57; Triple Barrier coin tarafinda YOK.

### Watchdog ve Dogruluk Kontrol (Round 4)

- Watchdog tasarimi dogru ama 1 kez calistirmak = yok hukmu. `launchd`/`systemd`/NSSM ile demonize edilmeli.
- Watchdog sadece `otonom_trader.py` ve `v3_risk_motor.py` izliyor; `coin_trader.py`, `coin_fullscan.py`, `dogruluk_kontrol.py`, `haber_ajan.py` kapsam DISINDA.
- Dogruluk kontrol sistemi sifir kayitla ISLEVSIZ; en az 100+ sinyal kaydi lazim, su an sifir.
- Haber ajanı iyi tasarim (5 kaynak, cache, retry, keyword scoring) ama ANKA ve COIN karar mekanizmasina ENTEGRE DEGIL.
- BIST tarafinda evre tespiti (SIKISMA/BIRIKIM) hala yok; coin'de var, BIST'te en acil eklenmesi gereken ozellik bu.

---

## KONSENSUS RAPORU

### Not Karsilastirmasi

| Sistem | Eski Ortalama | Yeni Ortalama | Degisim | Harf Notu |
|--------|---------------|---------------|---------|-----------|
| **ANKA (BIST)** | 1.83 (C-/C) | 2.54 (C+/B-) | **+0.71** | C+ --> B- |
| **COIN (Kripto)** | 0.31 (F) | 1.10 (D/D+) | **+0.79** | F --> D |
| **BIRLESIK** | 1.07 | 1.82 | **+0.75** | D+ --> C- |

### En Onemli IYILESMELER (Panel Uzlasmasi)

1. **OnOrderUpdate yeniden yazilmasi** -- 10/10 uzlasma. K-03 ve K-04 COZULDU. En kritik tekil duzeltme.
2. **Kill-switch ve panel kurallari** -- 10/10 uzlasma. Regulatif uyum CIDDI ilerleme.
3. **Triple Barrier hedef fonksiyonu** -- 9/10 uzlasma. ML metodolojisinin TEMELI duzeltildi.
4. **Feature secimi 73->20** -- 9/10 uzlasma. Overfitting riski azaltildi.
5. **VPS alinmasi** -- 8/10 uzlasma. Tek nokta ariza riskinin buyuk kismi giderildi.
6. **Bridge parametrelerinin tam okunmasi** -- 10/10 uzlasma. Kontrol paneli artik CALISIR.
7. **Sektor filtresi** -- 9/10 uzlasma. Korelasyon riski AZALTILDI.

### Devam Eden KRITIK Sorunlar

1. **Backtest guvenilirligi** -- 10/10 uzlasma. %7575 getiri ve %47 drawdown DOGRULANMALI.
2. **Coin ajanlari entegre degil** -- 10/10 uzlasma. 6 ajan yazilmis ama coin_trader.py'de CAGIRILMIYOR.
3. **Dogruluk kontrol bos** -- 9/10 uzlasma. Sifir kayit = islevsiz.
4. **Watchdog demonize degil** -- 9/10 uzlasma. 1 kez calistirmak = yokluk.
5. **BIST evre tespiti yok** -- 8/10 uzlasma. Coin'de var, BIST'te yok.
6. **Haber ajanı entegre degil** -- 8/10 uzlasma. Ayri dosyada, karar mekanizmasinda degil.
7. **Unrealized loss kill-switch yok** -- 8/10 uzlasma. Sadece realize kayiplar sayiliyor.

---

## ONCELIKLI AKSIYON LISTESI (V2)

| Oncelik | Aksiyon | Sistem | Tahmini Sure | Panel Destegi | Durum |
|---------|---------|--------|--------------|---------------|-------|
| **1** | Backtest dogrulamasi: Walk-forward ICinde parametre optimizasyonu, 5+ yillik veri, Monte Carlo | ANKA | 1 hafta | 10/10 | YENI |
| **2** | Coin 6 ajanın coin_trader.py'ye entegrasyonu | COIN | 1 gun | 10/10 | YENI |
| **3** | Watchdog'u launchd/systemd ile demonize et (+ coin process izleme) | Altyapi | 2 saat | 9/10 | YENI |
| **4** | Dogruluk kontrol'u ANKA ve COIN taramalarına bagla (otomatik sinyal kaydi) | ANKA+COIN | 3 saat | 9/10 | YENI |
| **5** | BIST'e SIKISMA/BIRIKIM evre tespiti ekle (coin_fullscan mantigi) | ANKA | 1 gun | 8/10 | YENI |
| **6** | Unrealized loss icin portfoy bazli kill-switch (sadece realized degil) | ANKA C# | 3 saat | 8/10 | YENI |
| **7** | Haber ajani'ni ANKA ve COIN karar mekanizmalarina entegre et | ANKA+COIN | 4 saat | 8/10 | YENI |
| **8** | Max drawdown sinirini %25'e indiren portfoy limiti (backtest ile dogrula) | ANKA | 1 gun | 10/10 | YENI |
| **9** | Backtest'i 2018-2025 donemiyle tekrarla (yatay piyasa dahil) | ANKA | 3 gun | 9/10 | YENI |
| **10** | Coin: WebSocket gecisi (REST polling yerine) | COIN | 2 gun | 7/10 | ESKIDEN KALMA |
| **11** | BIST: Yabanci akis verisini modele feature olarak ekle | ANKA | 1 hafta | 8/10 | ESKIDEN KALMA |
| **12** | Coin: Binance LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER kontrolu | COIN | 2 saat | 9/10 | ESKIDEN KALMA |
| **13** | VPS guvenlik: Firewall, SSH key-only, API key sifreleme | Altyapi | 3 saat | 8/10 | YENI |
| **14** | OnChainAgent'i GERCEK on-chain veriye bagla (Glassnode/Nansen Free API) | COIN | 1 gun | 6/10 | YENI |
| **15** | Canli isleme baslamadan once en az 30 gun paper trade tamamla | ANKA+COIN | 30 gun | 10/10 | DEVAM EDIYOR |

---

## CANLI ISLEME DONUS KOSULLARI (GUNCELLENMIS)

Panel, canli isleme donulebilmesi icin asagidaki kosullarin TAMAMININ saglanmasini talep etmektedir:

### Tamamlananlar (V2 itibariyle)
- [x] K-03, K-04 duzeltilmis (OnOrderUpdate yeniden yazildi)
- [x] K-05 duzeltilmis (SendOrderSequential false + pending flags)
- [x] Kill-switch mekanizmasi kurulmus
- [x] Sektor filtresi aktif
- [x] VPS alinmis

### Henuz Tamamlanmayanlar
- [ ] En az 30 gunluk paper trade tamamlanmis olmali
- [ ] Paper trade doneminde XU100 buy-and-hold'dan daha iyi performans
- [ ] Sharpe orani > 0.5 (CANLI veriden hesaplanmis, backtest degil)
- [ ] Maksimum drawdown < %25 (backtest'teki %47 KABUL EDILEMEZ)
- [ ] Watchdog 7/24 calisiyor ve test edilmis olmali
- [ ] Dogruluk kontrol en az 50 sinyal kaydetmis ve raporlamis olmali
- [ ] Backtest 5+ yil ile dogrulanmis olmali (sadece boga piyasasi degil)
- [ ] Coin ajanlarinin entegrasyonu tamamlanmis olmali

**Bu kosullar saglanana kadar CANLI ISLEM YAPILMAMALIDIR.**

---

*Bu birlesik panel degerlendirmesi, ANKA ve COIN Trading sistemlerinin onceki denetimden bu yana yasanan degisikliklerin bagimsiz akademik incelemesidir. Yatirim tavsiyesi icermez.*
