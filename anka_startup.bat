@echo off
set PYTHONUTF8=1
echo [%date% %time%] ANKA Startup baslatiliyor...
start /B "" "C:\Program Files\Python312\python.exe" -X utf8 -m streamlit run C:\ANKA\app.py --server.port 8501 --server.headless true --server.address 0.0.0.0
timeout /t 5 /nobreak > nul
start /B "" "C:\Program Files\Python312\python.exe" -X utf8 -m streamlit run C:\ANKA\coin_dashboard.py --server.port 8502 --server.headless true --server.address 0.0.0.0
timeout /t 5 /nobreak > nul
start /B "" "C:\Program Files\Python312\python.exe" -X utf8 C:\ANKA\anka_muhendis.py
echo [%date% %time%] Tum servisler baslatildi.
