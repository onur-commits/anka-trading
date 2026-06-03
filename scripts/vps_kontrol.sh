#!/usr/bin/env bash
# ============================================================
# ANKA VPS Panel Kontrol & Güvenli Başlatma  (Mac'ten çalışır)
# ============================================================
# Ne yapar:
#   1. VPS'teki BIST (8501) ve COIN (8502) Streamlit panellerinin
#      ayakta olup olmadığını kontrol eder.
#   2. BIST paneli düşmüşse, onay alıp SSH ile YALNIZCA panelleri
#      yeniden başlatır.
#
# GÜVENLİK (HARD LIMIT):
#   - SADECE Streamlit panellerini (app.py / coin_dashboard.py) başlatır.
#   - anka_muhendis.py'yi BAŞLATMAZ (o canlı trader'ı diriltir).
#   - otonom_trader.py / coin_otonom_trader.py'ye DOKUNMAZ.
#   - Hiçbir alım/satım/transfer tetiklemez — sadece UI panelleri.
#
# Gereksinim:
#   - .env içinde VPS_HOST, VPS_USER, VPS_PASSWORD (sshpass için).
#   - sshpass yoksa SSH parolayı interaktif sorar.
# ============================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi
HOST="${VPS_HOST:-78.135.87.29}"
VUSER="${VPS_USER:-Administrator}"

echo "🦅 ANKA VPS Panel Kontrol — $HOST"
echo "=========================================="

port_ok() { curl -s -o /dev/null --max-time 8 "http://$HOST:$1"; }

printf "1) BIST paneli (8501)... "
if port_ok 8501; then bist=1; echo "✅ çalışıyor"; else bist=0; echo "❌ düşmüş"; fi
printf "2) COIN paneli (8502)... "
if port_ok 8502; then coin=1; echo "✅ çalışıyor"; else coin=0; echo "❌ düşmüş"; fi

if [ "$bist" = 1 ]; then
  echo ""
  echo "✅ BIST paneli ayakta. Tarayıcıda aç:"
  echo "   👉 http://$HOST:8501"
  exit 0
fi

echo ""
echo "⚠️  BIST paneli düşmüş."
echo "    SSH ile YALNIZCA panelleri başlatayım mı?"
echo "    (trader'a/muhendis'e dokunulmaz, emir verilmez)"
printf "    Devam edeyim mi? [e/H] "
read -r ans
case "$ans" in e|E|evet|Evet) ;; *) echo "İptal edildi."; exit 0;; esac

# SSH: sshpass + .env parolası varsa otomatik, yoksa interaktif sorar
SSH=(ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)
if command -v sshpass >/dev/null 2>&1 && [ -n "${VPS_PASSWORD:-}" ]; then
  SSH=(sshpass -p "$VPS_PASSWORD" "${SSH[@]}")
else
  echo "    (sshpass/parola yok — SSH parolayı kendisi soracak)"
fi

# Windows'ta panelleri SSH oturumundan bağımsız (detached) başlat:
# Win32_Process.Create kullanırız ki SSH kapansa bile yaşasın.
PY='C:\Program Files\Python312\python.exe'
read -r -d '' PS <<PSEOF || true
\$py = '$PY'
\$bist = 'cmd /c "' + \$py + '" -X utf8 -m streamlit run C:\ANKA\app.py --server.port 8501 --server.headless true --server.address 0.0.0.0'
\$coin = 'cmd /c "' + \$py + '" -X utf8 -m streamlit run C:\ANKA\coin_dashboard.py --server.port 8502 --server.headless true --server.address 0.0.0.0'
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=\$bist; CurrentDirectory='C:\ANKA'} | Out-Null
Start-Sleep -Seconds 3
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=\$coin; CurrentDirectory='C:\ANKA'} | Out-Null
Write-Output 'PANELLER_BASLATILDI'
PSEOF

# UTF-16LE base64 -> powershell -EncodedCommand (SSH/Windows tırnak sorununu bitirir)
ENC=$(printf '%s' "$PS" | iconv -t UTF-16LE | base64 | tr -d '\n')

echo "→ VPS'te paneller başlatılıyor..."
if ! "${SSH[@]}" "$VUSER@$HOST" "powershell -NoProfile -EncodedCommand $ENC"; then
  echo "❌ SSH başarısız oldu. .env'deki VPS_PASSWORD / erişimi kontrol et."
  exit 1
fi

echo "→ Streamlit ısınıyor, 12 sn bekleniyor..."
sleep 12
printf "Sonuç: BIST 8501... "
if port_ok 8501; then
  echo "✅ AÇILDI"
  echo "   👉 http://$HOST:8501"
else
  echo "⚠️  Hâlâ kapalı. VPS'te log'a bakmak gerekebilir (logs/)."
fi
