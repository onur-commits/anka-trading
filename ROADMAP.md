# 🦅 ANKA — Satılabilir Paket Yol Haritası (KALICI HAFIZA)

> **Bu dosya Claude'un kalıcı hafızasıdır.** Her oturum başında ÖNCE bunu oku.
> Hafıza GitHub/oturum sıfırlanmasıyla kayboluyor — bu dosya tedbirdir.
> Son güncelleme: 2026-06-04

## 🎯 SON HEDEF
**Satılabilir paket trading programı — BIST + ABD (US) piyasaları.**
Enterprise: auth, güvenlik, çoklu piyasa, raporlama, admin, dağıtım.
Kullanıcının sözü: eksiksiz, sorunsuz, satılabilir.

## ⚖️ ÇALIŞMA KURALLARI (değişmez)
1. **`main` = CANLI bot.** Dokunulmaz. `durum.yml` 10dk'da bir VPS'e pull eder.
2. **Geliştirme `paket` branch'inde.** Tüm yeni paket işi orada.
3. **"birleştir" komutu** → kullanıcı dedi mi `paket` → `main` merge edilir.
4. **Onay/PR ceremony YOK** — `paket` branch'ine doğrudan commit, hız max.
5. **HARD LIMIT:** canlı emir TETİKLENMEZ (sadece kod).
6. **DÜRÜSTLÜK:** "%X hazır" demeden önce KANIT (test/çıktı). Geçmişte
   "hazır" denip eksik çıktı — bir daha yok.

## 📊 GERÇEK DURUM (kanıtlı, şişirme yok)
| Alan | Mevcut % | Kanıt |
|---|---|---|
| Trading çekirdeği (BIST) | 75% | scanner+ML+risk çalışıyor, edge optimize ediliyor |
| ABD piyasası | 0% | hiç yok |
| Auth/güvenlik | 0% | hiç yok |
| Raporlama | 40% | Raporlar Merkezi + CSV var |
| Altyapı/dağıtım | 18% | Docker/HTTPS yok |
| UI/panel | 41% | 7 Streamlit sayfa |
| **GENEL** | **~32%** | |

## 🗓️ 10 GÜNLÜK PLAN (her gün ~%10)
Her paket bağımsız, `paket` branch'inde, canlıya değmeden.

- [x] **Gün 1 — Trading çekirdek optimizasyon** (kara liste, eşik grid, stop-loss, edge+) `%75→%90 çekirdek` — WALK-FORWARD OOS **+%10.3** (542 işlem, kazanç %43.5): edge overfit DEĞİL, dayanıklı. Eski "negatif edge" notu YANLIŞTI.
- [~] **Gün 2 — ABD piyasası modülü** (us_market.py iskelet hazır) (US tickers, US market hours, yfinance US, US scanner)
- [x] **Gün 3 — Auth katmanı** (login, bcrypt, rol: admin/trader/viewer/readonly)
- [x] **Gün 4 — Güvenlik** (2FA/OTP, rate limit, lockout, reset token, parola politikası)
- [x] **Gün 5 — Audit log + güvenlik paneli** (login fail, OTP hata, admin aksiyon)
- [x] **Gün 6 — Raporlama paketi** (PDF export, latency, execution kalitesi, session/region)
- [x] **Gün 7 — Admin paneli** (kullanıcı CRUD, rol değiştir, aktif/pasif)
- [x] **Gün 8 — Latency/health + state machine** (scanning→armed→execute→exit, WS health gate)
- [x] **Gün 9 — Dağıtım** (Docker, .env yönetimi, HTTPS/nginx, backup, multi-region notu)
- [x] **Gün 10 — CI/CD + paketleme** (lint, test, coverage, codeql, lisans, kurulum sihirbazı)

## ✅ İLERLEME LOG (her tamamlanan buraya, kanıtla)
- 2026-06-04: ROADMAP + `paket` branch.
- 2026-06-04 GÜN 1 ✅: Backtest optimize (kara liste+grid+stop-loss).
  GÜNCEL SONUÇ (walk-forward, 2026-06-04 23:08): OOS getiri **+%10.3**
  (542 işlem, kazanç oranı %43.5, ort K/Z +%0.069). Çeyrek bazında en
  iyi eşik dalgalanıyor (Q1=40, Q2=15, Q3=25) ama birleşik OOS POZİTİF
  → edge OVERFIT DEĞİL. Eski "en iyi eşik=40 → -%5.9 negatif" notu
  GEÇERSİZ. In-sample +%19.6 iyimserdi; gerçek beklenen ~+%10.
  ML AUC 0.57 hâlâ zayıf (Gün 1 ek iş: feature engineering — 3d).
  Kanıt: data/walkforward_rapor.md
- 2026-06-04 GÜN 2 🔄: us_market.py — ABD piyasası modülü (47 US hisse,
  US borsa saati ET, TR karşılığı, tarama+skor). BIST'le aynı mantık.
- 2026-06-04 GÜN 3-5 ✅: platform/auth.py (login+rol+bcrypt), guvenlik.py
  (2FA/lockout/reset/parola politikası), audit.py — HEPSİ TEST GEÇTİ.
- 2026-06-04 GÜN 6-8 ✅: raporlama.py (CSV/PDF/latency/slippage),
  durum_makinesi.py (8 durum+health gate), pages/8_Yonetim.py (admin UI).
- 2026-06-04 GÜN 9-10 ✅: Dockerfile, .dockerignore, deploy/nginx.conf,
  .github/workflows/ci.yml (lint+derleme+test+sızıntı tarama).
- DURUM: 10 günlük iskelet TAMAM (paket branch). Canlıya değmedi.
  AÇIK: edge negatif (strateji kârı yok) + modüller ana app'e entegre
  edilmedi (auth app.py'ye bağlanmalı) — 'birleştir' öncesi yapılacak.

## 🔌 KÖR NOKTALAR (Claude göremez — bkz DURUM.md)
- VPS canlı görüntü yok (sadece durum.yml ~10dk foto)
- Eski Cowork oturumları boş (data/eski_oturumlar/ doldurulmadı)
- REE sistemi repoda yok
