@echo off
REM ============================================================
REM ANKA BIST Otonom Trader - CANLI baslatma
REM ------------------------------------------------------------
REM UYARI: Bu script GERCEK EMIR verir (otonom_trader.py'nin
REM paper/dry-run modu yoktur). Kullanici 2026-06-03'te acik
REM onayla CANLI calismayi istedi.
REM
REM Guvenlik: alim emirleri risk_yonetimi limitleriyle sinirli
REM (kill-switch %10 drawdown, max pozisyon, fat-finger 30K TL).
REM Acil durdurmak icin: Gorev Zamanlayici > ANKA_OtonomTrader >
REM Sonlandir, VEYA Task Manager'dan python.exe (otonom_trader).
REM
REM Canli yerine TEK DONGU test icin (yine canli emir!):
REM   python -X utf8 otonom_trader.py --simdi
REM Sadece durum gormek icin (emir vermez):
REM   python -X utf8 otonom_trader.py --durum
REM ============================================================
set PYTHONUTF8=1
cd /d C:\ANKA
if not exist logs mkdir logs
echo [%date% %time%] ANKA BIST Otonom Trader (CANLI) baslatiliyor... >> logs\otonom_trader.out.log
"C:\Program Files\Python312\python.exe" -X utf8 -u otonom_trader.py >> logs\otonom_trader.out.log 2>&1
echo [%date% %time%] ANKA BIST Otonom Trader sonlandi (exit %errorlevel%). >> logs\otonom_trader.out.log
