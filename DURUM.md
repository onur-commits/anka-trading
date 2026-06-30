# 🦅 ANKA DURUM — Tek Kontrol Paneli

_Güncelleme: 2026-06-30 12:22:34 TR · run 28434000256_

## ⚡ ANLIK (VPS'ten canlı)
```
ssh: connect to host 78.135.87.29 port 22: Connection refused
SSH HATA — VPS/parola kontrol
```

## 🌅 Sabah İzleme (09:10 TR, EMIRSIZ)

_2026-06-29 14:21:59 TR · run 28368358998_

```
ssh: connect to host 78.135.87.29 port 22: Connection refused
SSH HATA — VPS/parola kontrol
```


## ✅ ÇALIŞAN (kanıtlı)
- BIST otonom_trader CANLI (PID değişebilir) — `start_otonom.bat` ile başlar
- MatriksIQ + TCP 18890 açık → emir kanalı hazır
- ML her gün eğitiliyor (AUC ~0.57)
- Tarama + skorlama doğru (AEFES/AYEN/HEKTS yakalandı)
- GitHub Actions → VPS köprüsü (deploy + izleme)
- Risk limitleri: kill-switch %10, max 3 poz, fat-finger 30K TL
- Beyin danışmanı bağlı (default KAPALI, fail-open)

## ❌ KÖR NOKTALAR (Claude bunları GÖREMEZ)
- **VPS canlı görüntü:** YOK. Sadece bu workflow ile ~90sn gecikmeli foto.
- **Eski hafıza:** YOK. Claude her oturum sıfırdan; "hafıza" = repo + CLAUDE.md.
- **REE sistemi:** KARANLIK. 7+ scheduler görevi (REE_Radar/Doctor/Snapshot/
  Strateji) repoda DEĞİL — kodu görülmedi. "HARD BREAKER" alarmı buradan.
- **git stash:** VPS'teki yerel değişiklikler stash'te, içeriği bilinmiyor.
- **coin_otonom.py:** VPS'te 7/24 çalışıyor (kullanıcı "coin'le işim yok" dedi).

## 📋 AÇIK İŞLER (öncelik sırası)
1. 🔴 **VPS parolası DEĞİŞTİR** — git tarihinde + chat'te sızdı, hâlâ aktif.
2. 🟡 **Filtre 25 aktif değil** — çalışan bot bellekte 35; restart gerek.
3. 🟡 **Çift-bot riski** — 05:00 görevi, çalışan bota ek 2. kopya açabilir.
4. 🟢 PR #14 (parola temizliği) merge bekliyor.
5. 🟢 Gerçek emir döngüsü henüz GÖRÜLMEDİ — ilk test 09:05.

## 🗺️ MİMARİ ÖZET
- **BIST (17 modül):** app, otonom_trader, beyin, orkestra, muhendis,
  tahmin_motoru v1/v2/v3, gunluk_bomba, anka_scanner, risk_yonetimi, anka_api...
- **COIN (10 modül):** coin_otonom(_trader), coin_trader, coin_strateji,
  coin_ml_score, coin_ajanlar... (UI'dan çıkarıldı, biri VPS'te çalışıyor)
- **MatriksIQ:** 100+ C# robot (ANKA_*.cs, BOMBA_*.cs) + iq_deployer
- **REE (VPS-only):** nadir toprak/ABD hisse sistemi — repoda YOK
- **Pages (7 UI):** Alpha_V2, Danisman, Beyin, Otonom_Trader, Sistem_Saglik,
  Raporlar, Kod_Tarayici
- **Otomasyon:** durum.yml (bu) — git pull + VPS izleme, tek yer

## 🔌 CLAUDE'UN ERİŞİMİ (dürüst)
| Kaynak | Durum |
|---|---|
| GitHub repo + PR + Actions | ✅ Çalışıyor |
| VPS doğrudan (SSH/HTTP) | ❌ Engelli (sadece Actions ile dolaylı) |
| Mac / ekran | ❌ Sadece gönderdiğin screenshot |
| Geçmiş oturum hafızası | ❌ Yok (repo = hafıza) |

---
_Bu panelin canlı kısmı `durum.yml` workflow'u ile güncellenir. Statik kısım
`data/durum_statik.md`'de — düzenlenebilir._
