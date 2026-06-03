#!/usr/bin/env bash
# ANKA TAM KURULUM - Mac yerel ortam + dashboardlar

set -euo pipefail

echo "ANKA Kurulum Basliyor..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p logs

if [ -x "scripts/setup_venv.sh" ]; then
    bash scripts/setup_venv.sh
else
    PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.12}"
    if [ ! -x "$PYTHON_BIN" ]; then
        PYTHON_BIN="$(command -v python3.12 || command -v python3)"
    fi

    "$PYTHON_BIN" -m venv .venv
    .venv/bin/python -m pip install --upgrade pip wheel
    .venv/bin/python -m pip install -r requirements.txt
fi

export PYTHONUTF8=1
export PYTHONPATH="$SCRIPT_DIR"

port_acik_mi() {
    local port="$1"
    command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

dashboard_baslat() {
    local app_file="$1"
    local port="$2"
    local log_file="$3"
    local pid_file="$4"

    if port_acik_mi "$port"; then
        echo "Port $port zaten acik: http://localhost:$port"
        return
    fi

    nohup .venv/bin/python -X utf8 -m streamlit run "$app_file" \
        --server.port "$port" \
        --server.headless true \
        > "$log_file" 2>&1 &
    echo "$!" > "$pid_file"
    echo "$app_file baslatildi: http://localhost:$port"
}

dashboard_baslat app.py 8501 logs/bist_dashboard.log logs/bist_dashboard.pid

echo ""
echo "ANKA hazir."
