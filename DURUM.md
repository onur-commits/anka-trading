# 🦅 ANKA DURUM — Tek Kontrol Paneli

_Güncelleme: 2026-06-03 19:52:59 TR · run 26899749614_

## ⚡ ANLIK (VPS'ten canlı)
```
Warning: Permanently added '78.135.87.29' (ED25519) to the list of known hosts.
#< CLIXML
### Kod guncelleme
Saved working directory and index state On main: auto-yedek

 delete mode 100644 .github/workflows/tarama.yml
 delete mode 100644 .github/workflows/vps_bakim.yml
 create mode 100644 data/durum_statik.md

HEAD: b3cffa5

### BIST bot
CALISIYOR (PID 14060) MOD: CANLI

### MatriksIQ + TCP
ACIK PID 8604
TCP 18890: ACIK

### Bugun emir verildi mi?
Bugun emir YOK (toplam kayit: 200)

### Son 10 log
[2026-04-05 17:35:03] ==================================================
[2026-04-05 17:35:03] dY"? [17:35] GAoN SONU RAPORU
[2026-04-05 17:35:06] dY"S 05.04.2026 Raporu
Piyasa: BEAR
  AYEN: 34.40 (-5.4%) Skor:60
  DOHOL: 19.46 (-1.7%) Skor:58
  KONTR: 7.77 (-4.0%) Skor:53
  TUPRS: 255.25 (-0.3%) Skor:50
  KORDS: 56.60 (-4.6%) Skor:45
[2026-04-05 17:35:06] GA�n sonu rapor haz��r
[2026-04-06 05:30:13] ==================================================
[2026-04-06 05:30:13] dY� [05:30] ML MODEL E�z��T��M��
[2026-04-06 05:30:44]   52 hisse (2 y��l)
[2026-04-06 05:31:09]   �o. AUC:0.5664 F1:0.6073
[2026-04-06 05:31:09] ML gA�ncellendi �?" AUC:0.5664
[2026-06-03 03:18:01] beyin_rejim_onay hata (fail-open): Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress" RefId="0"><TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj><Obj S="progress" RefId="1"><TNRef RefId="0" /><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj><Obj S="progress" RefId="2"><TNRef RefId="0" /><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj></Objs>```

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
