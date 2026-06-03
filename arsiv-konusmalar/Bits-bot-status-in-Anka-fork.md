# Bits bot status in Anka (fork)
_Code (web) · /Users/onurbodur/adsız klasör/.claude/worktrees/busy-jemison-3c2ba2 · PR:None · 1779727607701_


**🧑 Sen:**

10 hisse hep sabit aynı hissemi hergün değişirmi benim bits 100 özelinde t1 ve t2 ler hariç her biri bir hisseye bakan ajanlarım vardı


**🤖 Claude:**

Hızlı özet, Onur:

**Coin listesi — sabit, her gün değişmiyor**
- `coin_otonom.py` içindeki `COINS` listesi **15 coin sabit** (25 May backtest sonrası ETH/ADA/ATOM/NEAR çıkarıldı, kazanan paterne odaklan).
- Bot her tarama (4dk) bu 15 coin'i skorlar, üst 6'sı pozisyona girer (`MAX_POZISYON=6`).
- **IZLENEN_POZISYONLAR** ayrı bir liste — risk-off SAT için bakıyor (Earn'den gelen ENA/FIL/JUP/TIA + ETH/XRP/ADA/OP + LUNC).
- "Her gün değişen" tarafı pending: **yeni listing tracker** (Onur 25 May 15:38 talimatı) — Binance yeni listing'leri 24h sonra otomatik COINS'e eklesin. Henüz yazılmadı (TASKS #10).

**"Her coin'e bir ajan" — şu an YOK**
- Mevcut mimari: **9 ajan TÜM coinleri tarıyor** (Harvey, Makarov, Liu, Cong, Capponi, Caner, Salih, Gulay, Akgiray). Per-coin uzmanlık yok, aynı framework her coin'e uygulanıyor.
- 9 ajan **boyut** uzmanı (sentiment / funding / correlation / makro), sembol değil.

**Netleştirme gerek:**
1. "Bits 100" — şu an iskelet (`~/bits-bot/`, strateji bekliyor). Sen muhtemelen **COIN bot $1300** sermayesini mi kastediyorsun yoksa Bits ayrı cep mi olsun?
2. "T1 / T2" — hangisi?
   - **Apollo ICP** (Tier 1 Maden / Tier 2 Geri Dönüşüm) — mıknatıs işi
   - **BIST T1/T2** (kapsam dışı, 23 May reddi)
   - Yoksa coin için yeni bir Tier yapısı mı düşünüyorsun?
3. "Her biri bir hisseye bakan ajanlarım" — bu BIST tarafındaki **553 BOMBA_*.cs algosunu** mu kastediyorsun (her .cs bir sembol için)? Yoksa farklı bir tasarım mı?

Hangi yöne gideyim — coin için sembol-başına ajan mimarisi mi tasarlayalım, yoksa mevcut 9-ajan'ı per-coin tune edelim mi?
