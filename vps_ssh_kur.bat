@echo off
echo SSH KURULUYOR...
powershell -Command "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0"
powershell -Command "Start-Service sshd"
powershell -Command "Set-Service -Name sshd -StartupType Automatic"
powershell -Command "New-NetFirewallRule -Name sshd -DisplayName 'SSH' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22"
echo.
echo SSH KURULDU! Artik Mac'ten baglanabilirsiniz.
echo.
echo ANKA KURULUYOR...
git clone https://github.com/onur-commits/anka-trading.git C:\ANKA
cd C:\ANKA
pip install yfinance pandas numpy scikit-learn schedule streamlit joblib requests feedparser xgboost lightgbm
mkdir C:\Robot
echo AYEN,GARAN > C:\Robot\aktif_bombalar.txt
echo.
echo KURULUM TAMAMLANDI!
pause
