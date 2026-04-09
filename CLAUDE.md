# ANKA Trading System - Claude Code Rehberi 
. 
## Sistem Ozeti 
ANKA, BIST (Borsa Istanbul) ve Kripto (Binance) icin otonom trading sistemidir. 
VPS uzerinde 7/24 calisir. Mac'ten SSH ile yonetilebilir. 
. 
## VPS Bilgileri 
- IP: 78.135.87.29 
- OS: Windows Server 2022 
- User: Administrator 
- SSH: Port 22 (aktif, otomatik baslatma) 
- Python: 3.12.8 (C:\Program Files\Python312\python.exe) 
- Git: 2.47.1 (C:\Program Files\Git\bin\git.exe) 
- Proje: C:\ANKA 
. 
## Calisan Servisler 
- BIST Dashboard: http://78.135.87.29:8501 (Streamlit, app.py) 
- COIN Dashboard: http://78.135.87.29:8502 (Streamlit, coin_dashboard.py) 
- Auto-startup: Registry HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run\ANKA_Trading 
. 
## Binance API 
- .env dosyasinda: BINANCE_API_KEY ve BINANCE_API_SECRET 
- IP Restriction: 78.135.87.29 
- Izinler: Reading + Spot Trading 
- Withdrawal: KAPALI (guvenlik) 
. 
## Dosya Yapisi 
### BIST Modulleri 
- app.py - Ana BIST dashboard (Streamlit, port 8501) 
- anka_scanner.py - Hisse tarama motoru 
- sabah_scanner.py - Sabah taramasi 
- hibrit_scanner.py - Hibrit tarama 
- gunluk_bomba.py - Gunluk bomba skor hesaplama 
- tahmin_motoru.py / tahmin_motoru_v2.py - ML tahmin motorlari 
- motor_v3.py - V3 trading motoru 
- anka_api.py - MatriksIQ REST API (TCP 18890) 
- risk_yonetimi.py - Risk yonetimi (ATR stop, Kelly Criterion) 
- anka_karar_verici.py - Karar verici modul 
- anka_panel_kurallari.py - Panel kurallari 
- anka_watchdog.py - Sistem izleme 
- dogruluk_kontrol.py - Tahmin dogruluk kontrolu 
- veri_isleyici.py - Veri isleme 
. 
### Kripto Modulleri 
- coin_dashboard.py - COIN dashboard (Streamlit, port 8502) 
- coin_trader.py - Binance API trader (BinanceClient sinifi) 
- coin_fullscan.py - Tam coin taramasi 
- coin_katmanli_scan.py - Katmanli tarama 
- coin_strateji.py - Kripto stratejileri 
- coin_ajanlar.py - Multi-agent kripto sistemi 
- coin_ai_egitim.py - Kripto ML egitim 
. 
### Ortak Moduller 
- bot.py - Temel bot altyapisi 
- otonom_trader.py - Otonom trader 
- alpha_v2_bot.py - Alpha V2 bot 
- anka_v2.py - ANKA V2 motor 
- haber_ajan.py - Haber ajani 
- haber_sentiment.py - Haber sentiment analizi 
- kontrol_paneli.py - Kontrol paneli 
- matriks_scraper.py - MatriksIQ scraper 
- v3_bridge_writer.py - V3 bridge writer 
- v3_risk_motor.py - V3 risk motoru 
- anka_ogrenme.py - Ogrenme modulu 
- anka_scalper.py - Scalper modul 
- anka_ai_egitim.py - BIST ML egitim 
. 
### Dizinler 
- data/ - Veri dosyalari 
- logs/ - Log dosyalari 
- models/ - ML modelleri (.pkl, .json) 
- pages/ - Streamlit sayfalari 
- matriks_iq/ - MatriksIQ dosyalari 
. 
## Bomba Skor Sistemi 
0-100 arasi puanlama: ML (%40) + Teknik (%25) + Momentum (%20) + Hacim (%15) 
ML: XGBoost + LightGBM + MLP ensemble, 73 feature 
. 
## Panel Kurallari 
- Fat-finger limiti: 30.000 TL 
- Gunluk emir limiti: 50 
- Stop-loss: ATR bazli 
. 
## MatriksIQ Entegrasyonu 
- TCP port 18890, JSON + char(11) terminator 
- C# stratejileri: BOMBA_*.cs dosyalari 
- anka_api.py uzerinden REST API 
. 
## SSH Erisim (Mac'ten) 
ssh Administrator@78.135.87.29 
Sifre: .env dosyasinda veya kullanicidan sor 
. 
## Yeni Moduller (2026-04-09)
- anka_muhendis.py - Otonom bakim & onarim (7/24, 30dk kontrol, otomatik restart)
- pages/2_ANKA_Danisman.py - Zeka sohbet paneli (4 ajan analiz, komisyon dahil)
- ANKA_BILINEN_SORUNLAR.md - Bilinen sorunlar veritabani (Muhendis okur)
- MATRIKS_IQ_STRATEJI_REHBER.md - 66 built-in strateji + API referansi
.
## Gelistirme Notlari 
- Windows'ta PYTHONUTF8=1 environment variable gerekli (Turkce karakter) 
- Python calistirirken HER ZAMAN -X utf8 flag kullan
- Streamlit --server.headless true --server.address 0.0.0.0 ile baslatilmali 
- .env dosyasi git'e EKLENMEMELI (.gitignore'da) 
- Bilinen sorunlar ANKA_BILINEN_SORUNLAR.md dosyasinda
- Erisim noktalari ayni dosyada ve bu dosyada
.
## Organizasyon
- CEO: Kullanici (kararlar, yon)
- Direktor: Claude (strateji, gelistirme)
- ANKA Danisman: Hisse analiz (4 ajan: TECHNO, VOLUME, MACRO, FUNDA)
- ANKA Muhendis: Teknik bakim, onarim, hata tespiti
- Otonom Trader: Zamanli gorevler (ML egitim, tarama, rapor)
