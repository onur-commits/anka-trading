# ANKA Aracı Kurum Geçiş Planı — 2026-04-27

## Sorun
Midas Menkul bireysel hesaplara algo/API izin vermiyor. ANKA bot şu an Midas üzerinden gidiyor (TCP→MatriksIQ→Midas) ve bugün canlıda çalıştı, ama bu Midas'ın gri alanında — istisnai. Tam otonom için algo onaylı broker gerek.

## Çözüm: Osmanlı Menkul

| Madde | Detay |
|-------|-------|
| **Min portföy** | 50.000 TL — kullanıcıda 140K cash + ~54K pozisyon var, yetiyor |
| **Platform** | MatriksIQ + İdeal + TradingView |
| **Algo izin** | Var (resmi kampanya) |
| **Min hesap** | Online açma + video kimlik (1-2 iş günü) |
| **Avantaj** | ANKA bot kodu zaten MatriksIQ uyumlu — değişiklik minimum |

Yedek seçenekler (Osmanlı çıkmazsa):
- **Tacirler Yatırım** — Tel: 0212 355 46 46
- **Deniz Yatırım** — algoritmikislemler@denizbank.com (kolokasyon dahil HFT)

## Geçiş adımları (sen iyileşince)

### Aşama 1 — Hesap açma (1 hafta)
1. Osmanlı Menkul online başvuru (osmanlimenkul.com.tr)
2. Form doldur, video kimlik
3. 50K+ TL transfer (Midas'tan veya banka)
4. IQ Algo lisansı talebi (Matriks fiyatını sor)

### Aşama 2 — Bot konfigürasyon (1 saat)
`coin_otonom_trader.py` ve `otonom_trader.py` içindeki sabitler güncellenecek:
```python
MIDAS_ACCOUNT_ID = "0~2205905"   → Osmanlı yeni hesap ID
MIDAS_BROKAGE_ID = "115"          → Osmanlı broker ID
```

### Aşama 3 — Test (2 gün)
- 1 lot küçük emir
- Gerçekleşme onayı
- 09:05 + 17:30 zincirini gözle

### Aşama 4 — Geçiş tamamlama
- Midas'ı manuel + ABD borsa için tut
- Algoritmik = Osmanlı'da
- ANKA tam otonom

## Mevcut bot durumu (referans)

Bugün test çalıştı:
- 11:37 ALIS KONTR 1524, AYEN 595, EGEEN 2 — bot kendi kararıyla
- 4 pozisyon canlı (ASELS, GESAN, AKSEN, AYEN)
- Anlık PL: ~+1,447 TL
- 17:30 otomatik kapatma planlı

## Ücretsiz ek araçlar (opsiyonel)

- **borsaci AI Agent** (GitHub: saidsurucu/borsaci) — Gemini ile 758 BIST şirket analizi, ücretsiz
- **TradingView webhook** — sinyal kaynağı genişletme
- **NosyAPI** — yfinance alternatifi

## Kullanıcının yapacağı (önemli)

- Hastaneden çıkınca Osmanlı'ya başvur
- IQ Algo lisans fiyatını sor (tahmin 200-500 TL/ay)
- Hesap aktif olunca bana haber ver, bot konfigürasyonunu yapayım

## Şu an aktif olan otomatik koruma

- Sabah 07:55 → IQ-Midas bağlantı check (Telegram alarm)
- Her gün 09:05 → otomatik bomba alış (sıkı filtre, max 3 pozisyon, max 20K/lot)
- Her gün 17:30 → tüm pozisyonları otomatik kapat (intraday)
- VPS down olursa Markahost panel restart gerek (hosting sorumluluğu)

## Notlar

- Roboritma alternatifti — 200K bakiye + Marbaş hesabı gerekiyor, şu an mantıksız
- Kesman Trading Panel ₺10K-25K/ay — ANKA zaten ücretsiz, gerek yok
- BIST direkt FIX/ITCH erişimi bireysele kapalı — bu yol yok
