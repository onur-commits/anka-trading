#!/bin/bash
# ═══════════════════════════════════════════════════
# BIST ALPHA V3 — VPS PAKETLEME
# Mac'te çalıştır → ZIP dosyası oluşturur → VPS'e RDP ile taşı
# ═══════════════════════════════════════════════════

cd "$(dirname "$0")"

echo "📦 VPS paketi hazırlanıyor..."

# Geçici klasör
rm -rf /tmp/BistAlpha_VPS
mkdir -p /tmp/BistAlpha_VPS/data
mkdir -p /tmp/BistAlpha_VPS/matriks_iq
mkdir -p /tmp/BistAlpha_VPS/models

# Ana dosyalar
cp motor_v3.py /tmp/BistAlpha_VPS/
cp tahmin_motoru_v2.py /tmp/BistAlpha_VPS/
cp risk_yonetimi.py /tmp/BistAlpha_VPS/
cp haber_sentiment.py /tmp/BistAlpha_VPS/
cp gunluk_bomba.py /tmp/BistAlpha_VPS/
cp vps_kurulum.bat /tmp/BistAlpha_VPS/

# Robot şablonu
cp matriks_iq/AKILLI_ROBOT_SABLONU.cs /tmp/BistAlpha_VPS/matriks_iq/

# Eğitilmiş model (varsa)
if [ -f models/ensemble_v2.pkl ]; then
    cp models/ensemble_v2.pkl /tmp/BistAlpha_VPS/models/
    echo "  ✅ ML model eklendi"
fi

# ZIP oluştur
cd /tmp
ZIP_NAME="BistAlpha_VPS_$(date +%Y%m%d).zip"
zip -r ~/Desktop/"$ZIP_NAME" BistAlpha_VPS/

echo ""
echo "✅ Paket hazır: ~/Desktop/$ZIP_NAME"
echo ""
echo "Sonraki adım:"
echo "  1. VPS'e RDP ile bağlan"
echo "  2. ZIP dosyasını VPS'e kopyala (sürükle-bırak)"
echo "  3. C:\\BistAlpha klasörüne çıkart"
echo "  4. vps_kurulum.bat dosyasını çalıştır"
echo ""

# Temizle
rm -rf /tmp/BistAlpha_VPS
