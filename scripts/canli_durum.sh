#!/usr/bin/env bash
# ============================================================
# ANKA Canli Durum (VPS) — tek tikla durum raporu (salt-okuma)
# ============================================================
# Ne yapar:
#   1. VPS'te otonom_trader.py --durum cagirir (mevcut poz, K/Z,
#      kill-switch, mod).
#   2. Bugunkü trade log son 10 satir (otonom_trades.json).
#   3. Son sistem logu son 15 satir (otonom_log.json).
#   4. Muhendis heartbeat (canli mi).
#
# GUVENLIK: SALT-OKUMA. Emir vermez, dosya yazmaz, proses oldurmez.
# Gereksinim: .env'de VPS_HOST/USER/PASSWORD (sshpass icin).
# ============================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi
HOST="${VPS_HOST:-78.135.87.29}"
VUSER="${VPS_USER:-Administrator}"

echo "🦅 ANKA CANLI DURUM — $HOST"
echo "================================================"
echo "TR saati: $(TZ=Europe/Istanbul date '+%H:%M, %a %d %b')"
echo ""

# SSH kurulum
SSH=(ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)
if command -v sshpass >/dev/null 2>&1 && [ -n "${VPS_PASSWORD:-}" ]; then
  SSH=(sshpass -p "$VPS_PASSWORD" "${SSH[@]}")
fi

# Tek SSH oturumunda 4 komut — PowerShell ile
read -r -d '' PS <<'PSEOF' || true
$ErrorActionPreference='SilentlyContinue'
Write-Output '── [1/4] Bot durumu (otonom_trader.py --durum) ──'
cd C:\ANKA
$env:PYTHONUTF8='1'
& 'C:\Program Files\Python312\python.exe' -X utf8 otonom_trader.py --durum 2>&1 | Out-String -Width 200
Write-Output ''
Write-Output '── [2/4] Bugun emir verildi mi? (otonom_trades.json son 10) ──'
if (Test-Path C:\ANKA\data\otonom_trades.json) {
  $j = Get-Content C:\ANKA\data\otonom_trades.json -Raw | ConvertFrom-Json
  if ($j.Count -gt 0) {
    $j | Select-Object -Last 10 | Format-Table -AutoSize | Out-String -Width 200
    Write-Output ("  Toplam kayit: " + $j.Count)
  } else { Write-Output '  (otonom_trades.json BOS — bot henuz emir vermemis)' }
} else { Write-Output '  (otonom_trades.json YOK — bot henuz emir vermemis)' }
Write-Output ''
Write-Output '── [3/4] Son sistem aksiyonu (otonom_log.json son 15) ──'
if (Test-Path C:\ANKA\data\otonom_log.json) {
  $l = Get-Content C:\ANKA\data\otonom_log.json -Raw | ConvertFrom-Json
  $l | Select-Object -Last 15 | ForEach-Object { "  [" + $_.zaman + "] [" + $_.seviye + "] " + $_.mesaj }
} else { Write-Output '  (otonom_log.json yok)' }
Write-Output ''
Write-Output '── [4/4] Muhendis heartbeat ──'
if (Test-Path C:\ANKA\data\muhendis_heartbeat.json) {
  Get-Content C:\ANKA\data\muhendis_heartbeat.json
} else { Write-Output '  (heartbeat dosyasi yok — muhendis hic calismamis)' }
PSEOF

ENC=$(printf '%s' "$PS" | iconv -t UTF-16LE | base64 | tr -d '\n')

if ! "${SSH[@]}" "$VUSER@$HOST" "powershell -NoProfile -EncodedCommand $ENC"; then
  echo ""
  echo "❌ SSH basarisiz. .env'deki VPS_PASSWORD veya VPS erisimini kontrol et."
  echo "   Alternatif: tarayicidan http://$HOST:8501 acmayi dene."
  exit 1
fi

echo ""
echo "================================================"
echo "✅ Rapor bitti. Yorum icin Claude'a yapistir."
