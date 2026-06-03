# üîç ANKA Baslat Kontrol

_2026-06-03 16:53:51 TR ‚Äî run 26889389381_

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
PID 14060 | "C:\Program Files\Python312\python.exe"  -X utf8 -u otonom_trader.py 
```

## start_otonom.bat son cikti logu (calisti mi / hata mi?)
```
[?ar 03.06.2026 16:53:03,31] ANKA BIST Otonom Trader (CANLI) baslatiliyor... 
[2026-06-03 16:53:06] [INFO] ==================================================
[2026-06-03 16:53:07] [INFO] dY- BIST ALPHA V2 É?" OTONOM TRADER
[2026-06-03 16:53:07] [INFO]   Piyasa: dYYõ AAÿIK É?" Piyasa aAéÒk
[2026-06-03 16:53:07] [INFO] ==================================================
[2026-06-03 16:53:07] [INFO] 
[2026-06-03 16:53:07] [INFO] dY". PROGRAM:
[2026-06-03 16:53:07] [INFO]   05:30 É+' ML model eéYitimi
[2026-06-03 16:53:07] [INFO]   08:30 É+' Bomba tarama + IQ kod A¨retimi
[2026-06-03 16:53:07] [INFO]   08:50 É+' IQ bildirim (kodlar hazéÒr)
[2026-06-03 16:53:07] [INFO]   09:35 É+' AAéÒléÒèY gap kontrolA¨
[2026-06-03 16:53:07] [INFO]   10:00 É+' é¯lk yaréÒm saat raporu
[2026-06-03 16:53:07] [INFO]   12:00 É+' A-éYlen hacim kontrolA¨
[2026-06-03 16:53:07] [INFO]   12:15 É+' Strateji gA¨ncelleme
[2026-06-03 16:53:07] [INFO]   15:00 É+' é¯kindi risk kontrolA¨
[2026-06-03 16:53:07] [INFO]   17:35 É+' GA¨n sonu rapor
[2026-06-03 16:53:07] [INFO] 
[2026-06-03 16:53:07] [BILDIRIM] Otonom Trader baèYladéÒ!
```

## otonom_trader calisiyor mu + hangi mod?
```
CALISIYOR -> MOD: CANLI (gercek emir!)
   cmd: "C:\Program Files\Python312\python.exe"  -X utf8 -u otonom_trader.py 
```
<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress" RefId="0"><TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj><Obj S="progress" RefId="1"><TNRef RefId="0" /><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj><Obj S="progress" RefId="2"><TNRef RefId="0" /><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj></Objs>