# 🦅 BIST Walk-Forward Backtest — DÜRÜST OOS edge

_İlk VPS koşusu: 2026-06-04 00:07 TR · yfinance BIST50 (5y) · look-ahead YOK_

> NOT: Bu rapor ilk koşunun (f674ee4) kısmi çıktısıdır — CLIXML kodlaması fold
> tablosunu ve bileşik getiri satırlarını yedi. `edge.yml` artık base64 capture
> ile düzeltildi + harness'e veri cache eklendi; tam tablolu temiz koşu yfinance
> rate-limit'i soğuyunca otomatik gelecek.

## Özet (OUT-OF-SAMPLE, look-ahead YOK)
- **Genel OOS AUC:** 0.5670  → zayıf ama **gerçek** sinyal (rastgele = 0.50)
- **Ort. net trade getirisi:** **%+0.446** (komisyon + slippage sonrası)
  → sinyal işlem maliyetini **yeniyor** (trade-bazında pozitif edge)
- **Benchmark (XU100 Al&Tut):** %+161.4 (nominal TRY — enflasyonla şişmiş)

## Yorum (dürüst)
1. **Sinyalin gerçek bir edge'i var ama zayıf.** OOS AUC 0.567 ve trade başına
   net +%0.446 → ML skoru, hisse yönünü rastgeleden iyi tahmin ediyor ve bu
   maliyeti aşacak kadar güçlü. backtest_bist.py'nin +%19.6/yıl in-sample sonucu
   look-ahead ile şişmişti; gerçek OOS edge çok daha mütevazı.
2. **Toplam getiri vs B&H:** Strateji çoğu zaman nakitte (5 günlük tutuş, top-3),
   bu yüzden nominal-TRY +%161 endeks Al&Tut'u toplam getiride yakalaması zor.
   Bu, 2 yıllık coin backtest'inin "aktif strateji < B&H" bulgusuyla **tutarlı**.
3. **Sonuç:** Edge trade seviyesinde POZİTİF; mesele sermaye kullanımı. Strateji
   enflasyon-beta'sını kaçırıyor. Seçenekler: (a) daha sürekli yatırım/daha çok
   pozisyon, (b) sinyali B&H çekirdeği üzerine "overlay" (timing), (c) feature
   mühendisliği ile AUC'yi 0.57'den yukarı çekmek (kesitsel sıralama, rejim).

## Sonraki adım
- Temiz tam tablo: `edge.yml` yeniden koşacak (base64 + cache fix sonrası).
- Edge'i büyütmek: feature mühendisliği (kesitsel relative-strength, sektör
  rotasyonu, XU100 rejim filtresi) — AUC 0.57→0.60+ hedefi.
