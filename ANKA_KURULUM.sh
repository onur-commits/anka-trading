#!/bin/bash
# ANKA TAM KURULUM — Bu scripti çalıştır, her şey kurulur
echo "🦅 ANKA Kurulum Başlıyor..."

cd "/Users/onurbodur/adsız klasör"

# 1. Yedekten geri yükle
if [ -f ~/Desktop/ANKA_TAM_YEDEK_20260403.tar.gz ]; then
    tar xzf ~/Desktop/ANKA_TAM_YEDEK_20260403.tar.gz
    echo "✅ Dosyalar geri yüklendi"
fi

# 2. Python ortamı
python3 -m venv .venv 2>/dev/null
source .venv/bin/activate
pip install yfinance pandas numpy xgboost lightgbm scikit-learn schedule streamlit joblib requests 2>/dev/null
echo "✅ Python paketleri kuruldu"

# 3. Otonom trader başlat
nohup .venv/bin/python borsa_surpriz/otonom_trader.py > /dev/null 2>&1 &
echo "✅ Otonom trader başlatıldı"

# 4. Risk motoru başlat
nohup .venv/bin/python borsa_surpriz/v3_risk_motor.py > /tmp/risk_motor.log 2>&1 &
echo "✅ Risk motoru başlatıldı"

# 5. Uyku engeli
caffeinate -d -i -s &
echo "✅ Caffeinate aktif"

# 6. Dashboard
nohup .venv/bin/streamlit run borsa_surpriz/anka_dashboard.py --server.port 8501 --server.headless true > /tmp/dashboard.log 2>&1 &
echo "✅ Dashboard: http://localhost:8501"

echo ""
echo "🦅 ANKA HAZIR!"
echo "IQ'da BOMBA_V3_TURBO12 robotunu başlat"
echo "C:\Robot\aktif_bombalar.txt dosyasını kontrol et"
