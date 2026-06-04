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

- [ ] **Gün 1 — Trading çekirdek optimizasyon** (kara liste, eşik grid, stop-loss, edge+) `%75→%90 çekirdek`
- [ ] **Gün 2 — ABD piyasası modülü** (US tickers, US market hours, yfinance US, US scanner)
- [ ] **Gün 3 — Auth katmanı** (login, bcrypt, rol: admin/trader/viewer/readonly)
- [ ] **Gün 4 — Güvenlik** (2FA/OTP, rate limit, lockout, reset token, parola politikası)
- [ ] **Gün 5 — Audit log + güvenlik paneli** (login fail, OTP hata, admin aksiyon)
- [ ] **Gün 6 — Raporlama paketi** (PDF export, latency, execution kalitesi, session/region)
- [ ] **Gün 7 — Admin paneli** (kullanıcı CRUD, rol değiştir, aktif/pasif)
- [ ] **Gün 8 — Latency/health + state machine** (scanning→armed→execute→exit, WS health gate)
- [ ] **Gün 9 — Dağıtım** (Docker, .env yönetimi, HTTPS/nginx, backup, multi-region notu)
- [ ] **Gün 10 — CI/CD + paketleme** (lint, test, coverage, codeql, lisans, kurulum sihirbazı)

## ✅ İLERLEME LOG (her tamamlanan buraya, kanıtla)
- 2026-06-04: ROADMAP oluşturuldu, `paket` branch açıldı.
- (Gün 1 başlıyor...)

## 🔌 KÖR NOKTALAR (Claude göremez — bkz DURUM.md)
- VPS canlı görüntü yok (sadece durum.yml ~10dk foto)
- Eski Cowork oturumları boş (data/eski_oturumlar/ doldurulmadı)
- REE sistemi repoda yok
