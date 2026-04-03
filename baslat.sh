#!/bin/bash
# BIST ALPHA V2 — Otonom Trader Başlatıcı
# Bu scripti çift tıkla veya terminalde çalıştır

cd "/Users/onurbodur/adsız klasör"
echo "🤖 BIST ALPHA V2 Otonom Trader başlıyor..."
echo ""

# Virtual env aktif et ve çalıştır
.venv/bin/python borsa_surpriz/otonom_trader.py "$@"
