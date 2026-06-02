#!/usr/bin/env bash
# ANKA Trading — yerel venv kurulumu (Python 3.12)
# ================================================
# VPS 3.12.8 kullaniyor; yerelde de 3.12 sabit.
# 3.13/3.15-alpha xgboost/lightgbm wheel'lerini bulamiyor.
#
# Kullanim:
#   bash scripts/setup_venv.sh           # uv varsa uv, yoksa python3.12
#   bash scripts/setup_venv.sh --force   # mevcut .venv'i sil, sifirdan kur

set -euo pipefail

cd "$(dirname "$0")/.."

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
    FORCE=1
fi

if [[ -d .venv && $FORCE -eq 1 ]]; then
    echo "[-] Eski .venv siliniyor (--force)"
    rm -rf .venv
fi

if [[ -d .venv ]]; then
    echo "[*] .venv zaten var. Yeniden olusturmak icin --force kullan."
else
    # Sirayla dene: uv -> pyenv -> python3.12 -> brew python@3.12
    if command -v uv >/dev/null 2>&1; then
        echo "[+] uv ile venv olusturuluyor (Python 3.12)"
        uv venv --python 3.12 .venv
    elif command -v pyenv >/dev/null 2>&1 && pyenv versions --bare | grep -qE '^3\.12'; then
        PY=$(pyenv which python3.12)
        echo "[+] pyenv 3.12 ile venv olusturuluyor: $PY"
        "$PY" -m venv .venv
    elif command -v python3.12 >/dev/null 2>&1; then
        echo "[+] python3.12 ile venv olusturuluyor"
        python3.12 -m venv .venv
    elif command -v brew >/dev/null 2>&1 && brew list python@3.12 >/dev/null 2>&1; then
        PY="$(brew --prefix python@3.12)/bin/python3.12"
        echo "[+] Homebrew python@3.12 ile venv olusturuluyor: $PY"
        "$PY" -m venv .venv
    else
        echo "[!] Python 3.12 bulunamadi. Yuklemek icin:"
        echo "    macOS:   brew install python@3.12  veya  uv python install 3.12"
        echo "    Linux:   apt install python3.12 / dnf install python3.12"
        echo "    Windows: choco install python --version=3.12"
        exit 1
    fi
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "[+] Python: $(python --version)"

echo "[+] pip yukseltiliyor"
python -m pip install --upgrade pip wheel

echo "[+] requirements.txt yukleniyor"
if command -v uv >/dev/null 2>&1; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt
fi

echo
echo "[OK] Venv hazir."
echo "    Activate:  source .venv/bin/activate"
echo "    Run:       python -X utf8 app.py"
echo "    Test:      python -X utf8 coin_ml_score.py --meta"
