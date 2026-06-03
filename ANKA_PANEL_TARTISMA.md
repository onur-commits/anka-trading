# ANKA Trading System — Akademik Panel Denetim Raporu

**Tarih:** 3 Nisan 2026 | **Format:** 10 Uluslararasi Akademisyen, Doktora Seviyesi Denetim

---

## ROUND 1–2 BULGULARI

- **AUC 0.5982:** Komisyon ve slippage sonrasi net alfa negatif. Walk-forward 5 fold yetersiz; CPCV ile test edilseydi AUC 0.55 altina duser.
- **Veri kaynagi uyumsuzlugu:** ML Yahoo verisiyle egitilmis, canli islem Matriks IQ verisiyle yapiliyor — kapanis fiyati tanimi bile farkli olabilir.
- **Hayalet pozisyon:** Robot `SendMarketOrder` gonderir, emir reddedilir, pozisyon girilmis zanneder. Rejected order yonetimi yok.
- **BIST dinamikleri eksik:** Yabanci yatirimci akislari fiyat hareketinin %60-70'ini yonlendiriyor; T+2 kurali, TCMB etkisi modelde yok.
- **Strateji-altyapi uyumsuzlugu:** Kurumsal ML stratejisi perakende altyapiyla (laptop + VM) uygulanamaz.
- **Risk yonetimi dekoratif:** Python'da dogru kodlanmis, C# robotu hicbir zaman okmuyor.

---

## ROUND 3: 11 KRITIK SORUN

**K-01 — Dosya tabanli IPC atomiklik sorunu**
Bridge dosyasi `File.ReadAllText()` ile okunuyor; yarim okumada `try-catch` hatayi yutar, robot yanlis multiplier ile islem yapar. Stokastik hata — cogu zaman dogru gorunur, tespiti zordur. **Cozum:** SQLite veya Redis.

**K-03/K-04 — Hayalet pozisyon ve veri zehirlenmesi**
Reddedilen emir pozisyon olarak kaydedilir → `anka_ogrenme.py` bu hayalet sonuclari ML'ye geri besler → model gercekte yapilmamis islemlerden "ogrenir". Pozisyon sayisi kontrolu da bozulur. **Cozum:** C# `OnOrderUpdate` callback duzeltmesi (tahmini 2 saat).

**K-05 — Sequential emir kilitleme**
5 sembol ayni anda sinyal verdiginde emirler sirali gonderilir; kalan 4 icin fiyat coktan degismistir. BIST acilis seansinda (09:40–10:00) kritik pencere kaciriilir. **Cozum:** Paralel emir gonderimi.

**K-06 — Yahoo Finance guvenilirligi**
Bolunme/sermaye artirimi duzeltmeleri yanlis olabilir; akademik arastirmada artik kabul edilmiyor. **Cozum:** Egitim verisini Matriks / BIST resmi kaynagina tasi.

**K-07 — AUC 0.5982 ve yanlis hedef fonksiyonu**
100 ornekten 60'inda dogru siralama komisyon sonrasi net beklentiyi negatife iter. `hedef_olustur` "5 gunluk pencerede en yuksek fiyat %3+ mi?" sorusunu cevapliyor — gercek islemde ulasilamaz. Precision-Recall, Brier score, Sharpe raporda yok. **Cozum:** Triple-barrier hedef, CPCV 100+ yol.

**K-08/K-09 — Risk yonetimi entegrasyonu ve korelasyon**
Kelly, korelasyon filtresi, drawdown limiti Python'da guzel kodlanmis — C# robotu hic okumamis. Enerji hisseleri (AYEN, AKSEN, ENJSA) ayni hafta %8-12 duser; ANKA ucunu birden secebilir → tek gunde %10.5 kayip. **Cozum:** `risk_yonetimi.py`'yi bridge uzerinden C#'a entegre et, max 2 ayni sektor kuralini FIILEN calistir.

**K-10 — Operasyonel risk**
Mac laptop kapanirsa sistem durur, kimse fark etmez. Launchd, process monitoring, watchdog yok. **Cozum:** Watchdog + heartbeat + Telegram bildirim.

**K-11 — Alfa kanitlanmamis**
Komisyon dahil kapsamli backtest, benchmark karsilastirmasi, Sharpe orani yok. BIST-spesifik faktorler (TCMB faiz sonrasi momentum, yabanci net alis, VIOP) hicbiri modelde degil. **Cozum:** 3 yillik backtest, XU100 benchmark, Sharpe > 1.0 hedef.

---

## ROUND 4 UZLASMALARI

- **ML kapatilmali mi?** Hayir — once hedef fonksiyonunu triple-barrier ile duzelt, yeniden egit. Ama K-01'den K-11'e 11 sorun duzeltilmeden ML acmak anlamsiz.
- **BIST'te perakende algo mantikli mi?** Bu kombinasyon degil. Dogru nis: daha uzun vadeli, daha az islem, BIST anomalilerini (KAP sinyali, endeks rebalance, temettü) kullanan, laptop'tan da calisan strateji.
- **Sistem kapatilmali mi?** Once TAMAMEN kapat → K-03/K-04/K-08 duzelt (2-3 gun) → paper trade (3 ay) → kucuk sermayeyle canli. Bu sira degistirilemez.

---

## ROUND 5: NIHAI KARARLAR VE ONERILER

| Profesör | Kurum | Not | Sayisal | 1 Numarali Oneri |
|----------|-------|-----|---------|------------------|
| Lo | MIT | C+ | 2.3 | Komisyon dahil 3 yillik backtest, XU100 benchmark, Sharpe > 1.0 |
| Lopez de Prado | Cornell | D+ | 1.3 | Triple-barrier hedef, CPCV 100+ yol, en onemli 20 feature |
| Kyle | Maryland | C- | 1.7 | C# `OnOrderUpdate` callback HEMEN duzelt (K-03) — 2 saatlik is |
| Bouchaud | Polytechnique | C | 2.0 | Portfoy bazinda gunluk max kayip limiti %3; asilinca tum pozisyon kapansin |
| Hendershott | Berkeley | D | 1.0 | VPS + Docker; watchdog + heartbeat + Telegram bildirim |
| Ulku | Borsa Istanbul | C | 2.0 | Yabanci net alis/satis (KAP'tan bedava) modele feature olarak ekle |
| Salih | Bilkent | C+ | 2.3 | `risk_yonetimi.py`'yi bridge → C# entegre; max 5 poz / 2 sektor / %10 gunluk drawdown FIILEN calismali |
| Bildik | Borsa Istanbul | C+ | 2.3 | BIST-ozgu kural katmani ekle (KAP, endeks, temettü); ML bunlarin uzerine filtre |
| Gulay | Sabanci | C- | 1.7 | Rejim tespiti HMM ile; VIX proxy yerine VIOP implied volatility |
| Akgiray | Bogazici | C- | 1.7 | Uc katmanli guvenlik: gunluk max emir + tek emir max buyukluk + gunluk max kayip — DERHAL |
| **ORTALAMA** | | **C-/C** | **1.83** | |

---

## KONSENSUS RAPORU

**Panel Notu: C- / C (1.83 / 4.00)**

**Guclu Yonler:**
1. Tek kisinin bu karmasiklikta sistem gelistirmesi teknik acidan takdire deger
2. Multi-agent mimari kavramsal olarak saglamdir
3. `risk_yonetimi.py` dogru tasarlanmis — entegrasyon eksik
4. Bridge + dashboard profesyonel vizyon gosteriyor
5. Walk-forward validasyon dogru yaklasim kullanmis (purge + expanding window)

**Kritik Zayifliklar (10/10 uzlasma aksi belirtilmedikce):**
1. AUC 0.5982 komisyon sonrasi net alfa uretmeye yetmez
2. Pozisyon takibi / emir yonetimi hatalari hayalet pozisyon olusturur
3. Risk yonetimi kodda var, fiilen calismiyor
4. BIST dinamikleri modelde yok (8/10)
5. Altyapi kurumsal standartlarin cok altinda (9/10)
6. Kara kugu / kuyruk riski korumasi yok

**Oncelikli Aksiyon Listesi:**

| Oncelik | Aksiyon | Bileşen | Sure | Destek |
|---------|---------|---------|------|--------|
| **1** | CANLI ISLEMI DERHAL DURDURUN | Genel | Simdi | 10/10 |
| **2** | OnOrderUpdate duzeltmesi (K-03/K-04) | C# Robot | 1 gun | 10/10 |
| **3** | Portfoy gunluk max kayip limiti (%3) | Bridge + C# | 1 gun | 10/10 |
| **4** | Kill-switch mekanizmasi | Bridge + C# | 2 gun | 10/10 |
| **5** | `risk_yonetimi.py` C# entegrasyonu | Bridge + C# | 3 gun | 9/10 |
| **6** | Korelasyon filtresi (max 2 ayni sektor) | Bomba tarama | 2 gun | 9/10 |
| **7** | Watchdog + heartbeat + bildirim | Python | 3 gun | 9/10 |
| **8** | ML triple-barrier hedef duzeltmesi | tahmin_motoru | 1 hafta | 8/10 |
| **9** | BIST feature eklenmesi (yabanci akis, VIOP) | ML Pipeline | 1 hafta | 8/10 |
| **10** | Kapsamli backtest (komisyon dahil, 3 yil, XU100) | Yeni modul | 2 hafta | 10/10 |
| **11** | Walk-forward fold: 5 → 50+ | tahmin_motoru | 3 gun | 7/10 |
| **12** | Feature secimi: 73+ → 20-25 | ML Pipeline | 1 hafta | 8/10 |
| **13** | VPS gecisi | Altyapi | 2 hafta | 7/10 |
| **14** | Paper trade modu (DRY_RUN) | C# Robot | 2 gun | 10/10 |
| **15** | Rejim tespiti HMM ile yeniden tasarim | v3_risk_motor | 2 hafta | 6/10 |

**Canli Isleme Donus Minimum Kosullari (oybirligi):**
1. K-03, K-04, K-05 duzeltilmis ve test edilmis
2. Portfoy gunluk max kayip limiti FIILEN calisiyor
3. En az 3 aylik paper trade tamamlanmis
4. Paper trade doneminde XU100 buy-and-hold'dan iyi performans
5. Sharpe > 0.5
6. Maksimum drawdown < %15
7. Kill-switch kurulmus ve test edilmis
8. Watchdog / heartbeat calisiyor

**Bu kosullar saglanana kadar CANLI ISLEM YAPILMAMALIDIR.**

---

Panel uzlasmasi: ANKA "yikilmasi gereken kotu sistem" degil, "potansiyeli olan ama tehlikeli sistem"dir. Gelistiricinin teknik yetenegi tartismasizdir; eksik olan finans muhendisligi disiplini, istatistiksel titizlik ve operasyonel olgunluktur. 15 maddelik aksiyon plani sirasiyla uygulanirsa ANKA ciddi bir trading sistemine donusme potansiyeline sahiptir — ancak bu CANLI PARA ILE DEGIL, paper trade ile yapilmalidir.

*Bu degerlendirme bagimsiz akademik incelemedir. Yatirim tavsiyesi icermez.*
