#!/usr/bin/env bash
# BIST ALPHA V2 — Otonom Trader Başlatıcı
# Bu scripti çift tıkla veya terminalde çalıştır

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONUTF8=1
export PYTHONPATH="$SCRIPT_DIR"

if [ ! -x ".venv/bin/python" ]; then
  echo ".venv yok; once ./ANKA_KURULUM.sh veya bash scripts/setup_venv.sh calistir."
  exit 1
fi

echo "BIST ALPHA V2 Otonom Trader basliyor..."
echo ""

# Virtual env aktif et ve çalıştır
.venv/bin/python -X utf8 otonom_trader.py "$@"
