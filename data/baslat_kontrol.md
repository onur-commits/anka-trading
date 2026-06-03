# 🔍 ANKA Baslat Kontrol

_2026-06-03 16:48:36 TR — run 26889079789_

Warning: Permanently added '78.135.87.29' (ED25519) to the list of known hosts.
#< CLIXML
## start_otonom.bat icerigi
```
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
```

## Calisan python prosesleri + KOMUT SATIRI (--dry-run var mi?)
```
PID 3888 | "C:\Program Files\Python312\python.exe" -X utf8 -u C:\ANKA\coin_otonom.py
```

## otonom_trader calisiyor mu + hangi mod?
```
otonom_trader CALISMIYOR (gorev henuz baslamamis ya da hemen bitmis)
```
<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress" RefId="0"><TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj><Obj S="progress" RefId="1"><TNRef RefId="0" /><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj><Obj S="progress" RefId="2"><TNRef RefId="0" /><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj></Objs>