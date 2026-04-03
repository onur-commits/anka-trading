@echo off
REM ═══════════════════════════════════════════════════
REM BIST ALPHA V3 — VPS KURULUM SCRIPTİ (Windows)
REM ═══════════════════════════════════════════════════
REM Bu dosyayı VPS'te çalıştır — her şeyi kurar.
REM ═══════════════════════════════════════════════════

echo.
echo ============================================
echo   BIST ALPHA V3 — VPS KURULUM
echo ============================================
echo.

REM 1. Python kontrolü
echo [1/6] Python kontrol ediliyor...
python --version 2>nul
if %errorlevel% neq 0 (
    echo HATA: Python kurulu degil!
    echo https://www.python.org/downloads/ adresinden indir
    echo Kurulumda "Add to PATH" kutusunu isaretle!
    pause
    exit /b 1
)

REM 2. Proje klasörü oluştur
echo [2/6] Proje klasoru olusturuluyor...
mkdir C:\BistAlpha 2>nul
mkdir C:\BistAlpha\data 2>nul
mkdir C:\BistAlpha\matriks_iq 2>nul
mkdir C:\BistAlpha\models 2>nul
mkdir C:\Users\onurbodur\Desktop\IQ_Deploy 2>nul

REM 3. Python paketlerini kur
echo [3/6] Python paketleri kuruluyor...
pip install yfinance pandas numpy scikit-learn xgboost lightgbm schedule feedparser joblib

REM 4. Dosyaları kopyala (USB/RDP ile taşınmış olmalı)
echo [4/6] Dosyalar kontrol ediliyor...
if exist C:\BistAlpha\motor_v3.py (
    echo   motor_v3.py ✓
) else (
    echo   UYARI: motor_v3.py bulunamadi!
    echo   Asagidaki dosyalari C:\BistAlpha klasorune kopyala:
    echo     - motor_v3.py
    echo     - tahmin_motoru_v2.py
    echo     - risk_yonetimi.py
    echo     - haber_sentiment.py
    echo     - gunluk_bomba.py
    echo     - matriks_iq\AKILLI_ROBOT_SABLONU.cs
    echo     - models\ensemble_v2.pkl (varsa)
)

REM 5. IQ_Deploy klasörünü ayarla
echo [5/6] IQ_Deploy hazirlaniyor...
if not exist C:\Users\onurbodur\Desktop\IQ_Deploy\aktif_bombalar.txt (
    echo. > C:\Users\onurbodur\Desktop\IQ_Deploy\aktif_bombalar.txt
    echo   aktif_bombalar.txt olusturuldu
)

REM 6. Test
echo [6/6] Sistem testi...
cd C:\BistAlpha
python motor_v3.py --vps --durum

echo.
echo ============================================
echo   KURULUM TAMAMLANDI!
echo ============================================
echo.
echo Sonraki adimlar:
echo   1. MatriksIQ'yu kur ve giris yap
echo   2. Telegram bot token'i motor_v3.py icinde ayarla
echo   3. Robotlari uret: python motor_v3.py --vps --setup
echo   4. Robotlari IQ'ya import et
echo   5. Motoru baslat: python motor_v3.py --vps
echo.
pause
