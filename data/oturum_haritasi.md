# 🦅 ANKA Oturum Mimari Haritası (2026-06-02 22:40 → 06-03)

Doğruluk etiketleri: ✅ Kanıtlandı · 🟡 Beklenen · ⚠️ Doğrulanmadı · ❌ Çalışmıyor

## Katmanlar
- **Cloud Claude (sandbox):** kod yazar, PR açar. VPS'e ağ erişimi ❌ ENGELLİ (tüm portlar HTTP 000). Canlı emir tetikleme ❌ yasak (HARD LIMIT korundu).
- **GitHub repo:** 13 PR (11 merge), 66 .py, 4 workflow, ruff PASS. Köprü görevi: workflow'lar VPS'e SSH yapar.
- **VPS (78.135.87.29):** gerçek çalışma. `git pull` ✅, bot ✅ PID 14060 CANLI, MatriksIQ ✅ TCP 18890 açık.

## Merge edilen PR'lar
| # | İş | Doğruluk |
|---|---|---|
| 5 | 2 bug + 195 lint + markdown -3.4K satır | ✅ |
| 6 | Final lint config (0 uyarı) | ✅ |
| 8 | 3 fazla UI silindi + muhendis heartbeat | ✅ |
| 9 | Raporlar Merkezi (CSV) | 🟡 UI çalıştırılmadı |
| 10 | Beyin→trader (default KAPALI, fail-open) | ✅ 5/5 test |
| 11 | Sentetik vs gerçek veri + outlier filtre | ✅ |
| 12 | VS Code Canlı Durum task | 🟡 |
| 13 | canli_durum.yml (15dk VPS izleme) | ✅ çalıştı |
| 15 | vps_bakim.yml (git pull + teşhis) | ✅ çalıştı |
| 16 | baslat_kontrol.yml (proses mod) | ✅ çalıştı |
| 17 | start_otonom.bat (eksik launcher) | ✅ deploy |
| 19 | Filtre 35→25 | ✅ kod / ⚠️ bot bellekte 35 |
| 20 | tarama.yml (emirsiz canlı tarama) | ✅ skor üretti |

## Bot durumu (2026-06-03 kanıt)
- PID 14060 `otonom_trader.py` MOD: CANLI ✅
- Bugün canlı tarama: AEFES 61, TOASO 56, AYEN 53, EREGL 50, HEKTS 50 ✅
- 17:30 gün sonu satış çalıştı ("açık poz yok") ✅
- **Bugün gerçek emir: 0** (otonom_trades.json boş) ✅

## Alımı engelleyen sebepler (çözülmüş/açık)
1. start_otonom.bat eksikti → ✅ çözüldü
2. Görev Devre Dışıydı → ✅ Enable edildi
3. Bot 16:53 başladı, 08:30 tarama kaçtı → bugünkü liste üretilmedi
4. Alım saati 09:05 geçmiş → bot disiplini
5. tetikle_simdi.flag sadece açılışta okunuyor + yanlış klasördeydi

## Güvenlik
- HARD LIMIT ihlali: 0 ✅
- VPS parolası: CLAUDE.md'den çıkarıldı (PR #14 bekliyor) ama git tarihinde + chat'te SIZDI → ⚠️ kullanıcı DEĞİŞTİRMELİ
- .env git'te değil ✅ · GitHub Secret VPS_PASSWORD ✅

## Genel doğruluk
| Soru | Oran |
|---|---|
| Kod doğru çalışıyor mu | %95 |
| VPS deploy başarılı mı | %100 |
| Bot canlı mı | %100 |
| Bot bugün al-sat yaptı mı | %0 |
| Yarın 09:05 al-sat yapacak mı | %70 (koşullu) |
| Şifre güvenliği | %30 (sızdı, değişmedi) |

## Yarın için bilinmeyenler (%70'in sebebi)
1. Gece bot proseste kaldı mı? 05:00 görevi ÇİFT bot başlatabilir.
2. Filtre 25 ancak bot RESTART olunca aktif (şu an bellekte 35).
3. Sabah ML/tarama hata verirse aday listesi olmaz.
4. MatriksIQ TCP 09:05'te ayakta mı?

## Net yargı
Bot çalışıyor, kanal açık, tarama doğrulandı — ama **gerçek emir döngüsü henüz GÖRÜLMEDİ.** İlk gerçek test: yarın 09:05.
