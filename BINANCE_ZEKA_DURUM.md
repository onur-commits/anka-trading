# Binance Zeka Durum Raporu

**Tarih:** 2026-05-20
**Branch:** `claude/check-binance-integration-CNT9j`
**Hazırlayan:** Claude Code (kod tabanı incelemesi)

> **Uyarı:** Bu rapor repo'nun bulut kopyası üzerinden hazırlandı.
> Botlar VPS'te (78.135.87.29) çalışır; canlı process durumu VPS'ten
> doğrulanmalıdır (bkz. "Canlı durum kontrolü").

---

## 1. Binance'de çalışan zekalar (kodda mevcut)

| Zeka | Dosya | Görev | Çalışma şekli |
|------|-------|-------|---------------|
| Coin Otonom Trader | `coin_otonom_trader.py` | 7/24 otonom kripto trading, 25 coin tara | VPS'te sürekli proses |
| 5+2 Ajan kurulu | `coin_otonom_trader.py` (gömülü) | TeknikAjan, HacimAjan, MakroAjan, LikiditeAjan + SEN/FUN/COR uzmanları → oylama | Trader içinde |
| 6 Uzman Ajan | `coin_ajanlar.py` | FUNDING, ONCHAIN, SENTIMENT, LIQUIDATION, ORDERBOOK, CORRELATION | Trader'a beslenir |
| COIN Dashboard | `coin_dashboard.py` | Streamlit panel | Port 8502 |
| A/B Karşılaştırma | `ab_karsilastirma.py` | Bot vs BTC Buy&Hold ölçümü | Scheduler `ANKA_AB_Karsilastirma`, her gün 23:00 |

## 2. Karar mantığı (`coin_otonom_trader.py` Config)

- **Alış sinyali:** Skor >= 75 **ve** en az 3 ajan >= 60
- **Coin evreni:** Top 25 likit coin (BTC, ETH, BNB, SOL, ...)
- **Risk:** Max 5 pozisyon, pozisyon başına max %15 sermaye
- **Stop:** ATR x 3.5 (fallback %7), trailing %3 kârda aktif / %2 mesafe
- **Take-profit:** %8'de yarısı, %15'te tümü
- **Kill-switch:** %15 drawdown → tüm pozisyonları kapat
- **BTC koruma kalkanı:** BTC SMA20 altındaysa altcoin alma (BTC/ETH muaf)
- **Mod:** `--dry-run` ile simülasyon; bayraksız çalışınca CANLI emir

## 3. Geçmiş bulgular (CLAUDE.md kayıtları)

- **14 saatlik paper deneme (2026-04-18/19):** Bot 65 eşiğini hiç geçemedi —
  **0 alım**, 2 stop-loss satışı. Momentum bot bu piyasada sinyal üretmiyor.
- **2 yıllık backtest:** Grid, DCA ve momentum dahil tüm aktif stratejiler
  zararda. Kazanan tek strateji "BTC al, tut" (+20.5%).
- Bu bulgular sonrası `MIN_SKOR_AL` 65 → **75**'e sıkılaştırıldı.

## 4. A/B Karşılaştırma Deneyi — süresi doldu

- **Pencere:** 2026-04-19 → **2026-05-19** (30 gün) — bugün itibarıyla **bitti**.
- **Amaç:** Bot vs BTC Buy&Hold, eşit sermaye, gerçek piyasa.
- **Sonuç:** `data/ab_karsilastirma.json` (state) yalnızca VPS'te tutuluyor;
  bu repo kopyasında yok. Sonucu çıkarmak için `ab_sonuc.py` eklendi.
- **Karar kuralı:** Bot önde → momentum stratejiye devam; B&H önde →
  momentum bot rafa, BTC Buy&Hold'a dönülür.

## 5. Canlı durum kontrolü (VPS'te çalıştır)

```powershell
# Hangi zekalar ayakta?
Get-CimInstance Win32_Process | Where CommandLine -like '*coin_otonom_trader*' -or CommandLine -like '*coin_dashboard*'

# A/B scheduler durumu
schtasks /Query /TN ANKA_AB_Karsilastirma

# A/B nihai sonuç + karar
cd C:\ANKA && git pull && python -X utf8 ab_sonuc.py
```

## 6. Açık konular

- A/B deneyi bitti — nihai sonuç çıkarılıp karar verilmeli (`ab_sonuc.py`).
- `earn_to_spot.py` hâlâ çalıştırılmadı — Earn'de hayalet ATOM/BTC/MOVR var.
- `toplam_portfoy_degeri()` hayalet (Earn'deki) pozisyonları topluyor.
