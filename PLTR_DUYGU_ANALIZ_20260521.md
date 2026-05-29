# PLTR (Palantir) — Piyasa Duygusu Analizi

**Tarih:** 2026-05-21
**Fiyat (analiz anı):** $137,66
**Zaman dilimi:** 1G intraday
**Branch:** `claude/market-sentiment-analysis-d7Mjp`

---

## 1. Teknik Görünüm (1G grafik)

| Gösterge | Değer / Durum | Yorum |
|---|---|---|
| SMA dizilimi | Fiyat > SMA20 ($137,4) > SMA50 ($136,6) > SMA200 ($134,3) | Tam boğa dizilimi — trend yukarı |
| Bollinger | Fiyat üst banda yakın | Güçlü ama gerilmiş |
| RSI(14) | ~58–60 | Pozitif, aşırı alım değil |
| MACD(12,26,9) | Hafif pozitif, düz | İvme zayıflıyor |
| Hacim | Gün sonuna doğru azalıyor | Alıcı yorgun |
| Son mum | Kırmızı (gün sonu kâr realizasyonu) | Kısa vadeli satış baskısı |

**Teknik özet:** Trend sağlam yukarı; günün son saatinde alıcı yorgun, dar bantta tıkanma.

---

## 2. Temel & Haber Duygusu (güncel)

### Q1 2026 Bilançosu (4 Mayıs 2026)
- EPS: **$0,33** vs beklenti $0,27 (+%22 sürpriz)
- Toplam gelir büyüme: **%85 YoY** (şirket tarihinin en yükseği)
- ABD geliri büyüme: **%104 YoY**
- "Rule of 40" skoru: **%145** (NVIDIA / Micron / SK hynix seviyesi)

### Kılavuz (FY2026 yukarı revize)
- Toplam gelir büyüme: **%71**
- ABD ticari gelir büyüme: **%120**
- Tahmini yıllık gelir: **~$7,19 milyar**

### Analist Konsensüsü (21 Mayıs 2026)
- 21–29 analist kapsıyor, konsensüs: **AL**
- Dağılım: %43 Güçlü Al, %19 Al, %33 Tut, %5 Sat, %0 Güçlü Sat
- Ortalama fiyat hedefi: **~$194** (≈%45 yukarı potansiyel)
- Rosenblatt (21 Mayıs): Buy, hedef **$225**

---

## 3. Risk / Karşıt Sinyaller

| Risk | Detay |
|---|---|
| **Değerleme** | Forward P/E ~96,6 (NVIDIA/CrowdStrike üstünde). GF Value $129,70 → fiyat ~%5 pahalı |
| **İçeriden satış** | Son 3 ayda yöneticiler **$434M** sattı, **0 alım** — uyarı |
| **Retail euphoria** | Capital.com: %92,1 long, %7,9 short — tek yönlü, kontrarian risk |
| **Sözleşme belirsizliği** | UK NHS £330M Federated Data Platform sözleşmesinde fesih maddesi gündemde |
| **Makro** | Tarife belirsizliği, temkinli Fed |

---

## 4. Yüzdesel Skor: TUT / SAT

| Faktör | Ağırlık | Yön | Katkı |
|---|---:|---|---:|
| Trend (SMA dizilimi) | %15 | Boğa | +%12 TUT |
| Momentum (RSI/MACD) | %10 | Nötr-pozitif | +%7 TUT |
| Bilanço (Q1 2026) | %20 | Olağanüstü güçlü | +%18 TUT |
| Analist konsensüsü | %15 | Buy, +%45 hedef | +%11 TUT |
| Değerleme (P/E 96,6) | %15 | Aşırı pahalı | -%12 SAT |
| İçeriden satış | %10 | $434M satış | -%9 SAT |
| Retail euphoria | %8 | %92 long | -%6 SAT |
| Makro & NHS belirsizliği | %7 | Olumsuz | -%5 SAT |

### **Toplam: TUT %62 / SAT %38**

---

## 5. Pratik Karar

**Genel duygu: POZİTİF ama AŞIRI GERGİN — "güçlü şirket, pahalı hisse"**

- **Kısa vade (günler):** Nötr/temkinli. Üst banda yapışmış, hacim düşüyor, içeriden satış sürüyor.
- **Orta vade (haftalar/aylar):** Pozitif. %85 büyüme, %145 Rule of 40, hedefler $194–225.
- **Asıl risk fiyatın kendisinde:** 96x forward P/E hatalara tahammülsüz — bir kötü çeyrek veya makro şok sert düzeltme getirir.

### Pozisyon Yönetimi
- **Mevcut pozisyon varsa →** Sat sinyali yok. Pozisyonun %30-40'ını burada ($137-138) kısmi realize et, gerisini trailing stop ile taşı.
- **Yeni giriş için →** $134 (SMA200) civarı geri çekilme bekle; üst bantta kovalama.

### Kritik Seviyeler
- **Stop:** $136,60 altı kapanış (SMA50 kırılırsa TUT skoru %50'ye düşer)
- **Onay:** $138,50 üstü kapanış (yeni bacak → TUT %70'e çıkar)
- **Hedef:** $194 (analist ortalaması), $225 (Rosenblatt boğa hedefi)

---

## 6. Notlar

- PLTR ABD hissesi — ANKA sistemi BIST/Kripto odaklı, doğrudan trading entegrasyonu yok.
- Bu rapor yatırım tavsiyesi değil; mevcut piyasa verisi + grafik sentiment sentezi.
- Bilgi kaynakları: Q1 2026 SEC 8-K, MarketBeat, Public.com, Rosenblatt, GuruFocus, Capital.com, Simply Wall St.

### Kaynaklar
- SEC 8-K (Q1 2026 Press Release): https://www.sec.gov/Archives/edgar/data/0001321655/000132165526000026/a2026q1ex991pressrelease.htm
- MarketBeat Forecast: https://www.marketbeat.com/stocks/NASDAQ/PLTR/forecast/
- Public.com Forecast: https://public.com/stocks/pltr/forecast-price-target
- Rosenblatt Buy $225 — GuruFocus: https://www.gurufocus.com/news/8874990/pltr-maintains-buy-rating-by-rosenblatt-price-target-remains-at-225
- Valuation Concerns — GuruFocus: https://www.gurufocus.com/news/8872268/palantir-technologies-pltr-sees-record-revenue-growth-amid-valuation-concerns
- Capital.com Sentiment: https://capital.com/en-int/market-updates/palantir-stock-forecast-04-05-2026
- Simply Wall St: https://simplywall.st/stocks/us/software/nasdaq-pltr/palantir-technologies
