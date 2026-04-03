"""
MatriksIQ Strateji Otomatik Yükleyici
======================================
Windows'taki MatriksIQ'ya strateji yükler:
- Kod yapıştırma
- Derleme
- Çalıştırma

Mac'ten çalışır, Parallels üzerinden Windows'u kontrol eder.
"""

import subprocess
import time
import sys
import os
from pathlib import Path

STRATEGIES = {
    "BOMBA_ENJSA": {
        "file": "BOMBA_ENJSA.cs",
        "symbol": "ENJSA",
    },
    "BOMBA_HALKB": {
        "file": "BOMBA_HALKB.cs",
        "symbol": "HALKB",
    },
    "BOMBA_GUBRF": {
        "file": "BOMBA_GUBRF.cs",
        "symbol": "GUBRF",
    },
    "BOMBA_GARAN": {
        "file": "BOMBA_GARAN.cs",
        "symbol": "GARAN",
    },
}

VM_NAME = "Windows 11"
WIN_DEPLOY_DIR = r"C:\Users\onurbodur\Desktop\IQ_Deploy"


def run_win(cmd, timeout=30):
    """Windows'ta komut çalıştır."""
    try:
        result = subprocess.run(
            ["prlctl", "exec", VM_NAME, "cmd", "/c", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"  ⚠ Hata: {e}")
        return ""


def run_ps(script, timeout=30):
    """Windows'ta PowerShell çalıştır."""
    try:
        result = subprocess.run(
            ["prlctl", "exec", VM_NAME, "powershell", "-Command", script],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"  ⚠ PS Hata: {e}")
        return ""


def check_iq_running():
    """MatriksIQ çalışıyor mu?"""
    out = run_win("tasklist /FI \"IMAGENAME eq MatriksIQ.exe\" /NH")
    return "MatriksIQ.exe" in out


def copy_files_to_windows():
    """Strateji dosyalarını Windows'a kopyala."""
    print("📁 Dosyalar Windows'a kopyalanıyor...")
    run_win(f'mkdir "{WIN_DEPLOY_DIR}" 2>nul')

    base = Path(__file__).parent
    for name, info in STRATEGIES.items():
        src = f'\\\\Mac\\Home\\adsız klasör\\borsa_surpriz\\matriks_iq\\{info["file"]}'
        dst = f'{WIN_DEPLOY_DIR}\\{info["file"]}'
        run_win(f'copy "{src}" "{dst}" /Y')
        print(f"  ✅ {name}")


def deploy_strategy_powershell(name, info):
    """
    PowerShell ile strateji yükle:
    1. Kodu clipboard'a kopyala
    2. MatriksIQ'ya odaklan
    3. Keyboard shortcut ile yeni strateji aç
    4. Yapıştır + Derle + Çalıştır
    """
    filepath = f'{WIN_DEPLOY_DIR}\\{info["file"]}'

    print(f"\n🚀 {name} yükleniyor...")

    # 1. Kodu clipboard'a kopyala
    ps_clip = f'Get-Content "{filepath}" -Raw | Set-Clipboard'
    run_ps(ps_clip)
    print("  📋 Kod panoya kopyalandı")
    time.sleep(1)

    # 2. PowerShell ile MatriksIQ'ya tuş gönder
    ps_keys = '''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

# MatriksIQ penceresini bul ve öne getir
$iq = Get-Process MatriksIQ -ErrorAction SilentlyContinue | Select-Object -First 1
if ($iq) {
    $hwnd = $iq.MainWindowHandle
    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
"@
    [Win32]::ShowWindow($hwnd, 9)  # SW_RESTORE
    [Win32]::SetForegroundWindow($hwnd)
    Start-Sleep -Milliseconds 500
    Write-Output "IQ_FOCUSED"
} else {
    Write-Output "IQ_NOT_FOUND"
}
'''
    result = run_ps(ps_keys, timeout=15)
    if "IQ_NOT_FOUND" in result:
        print("  ❌ MatriksIQ bulunamadı!")
        return False

    print("  🪟 IQ penceresi öne getirildi")
    return True


def create_ahk_script():
    """
    AutoHotKey benzeri PowerShell otomasyon scripti.
    Tüm stratejileri sırayla yükler.
    """
    ahk_script = r'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

function Focus-IQ {
    $iq = Get-Process MatriksIQ -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $iq) { return $false }

    Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class Win32Focus {
        [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
        [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
"@
    [Win32Focus]::ShowWindow($iq.MainWindowHandle, 9)
    [Win32Focus]::SetForegroundWindow($iq.MainWindowHandle)
    Start-Sleep -Milliseconds 800
    return $true
}

function Deploy-Strategy($filePath, $strategyName) {
    Write-Host "=== $strategyName yukluyor ===" -ForegroundColor Cyan

    # 1. Kodu panoya al
    $code = Get-Content $filePath -Raw -Encoding UTF8
    [System.Windows.Forms.Clipboard]::SetText($code)
    Write-Host "  Kod panoda" -ForegroundColor Green

    # 2. IQ'ya odaklan
    if (-not (Focus-IQ)) {
        Write-Host "  HATA: IQ bulunamadi!" -ForegroundColor Red
        return
    }

    # 3. Kod editörüne odaklan ve tümünü seç + yapıştır
    # Ctrl+A (tümünü seç) → Delete → Ctrl+V (yapıştır)
    Start-Sleep -Milliseconds 500
    [System.Windows.Forms.SendKeys]::SendWait("^a")      # Ctrl+A
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("{DELETE}")  # Sil
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("^v")       # Ctrl+V
    Start-Sleep -Milliseconds 1000

    Write-Host "  Kod yapıştırıldı" -ForegroundColor Green
    Write-Host "  >> Simdi DERLE butonuna bas, sonra ENTER'a bas <<" -ForegroundColor Yellow
    Read-Host "  DERLE'ye bastın mı? (Enter)"

    Write-Host "  >> Simdi CALISTIR butonuna bas, sonra ENTER'a bas <<" -ForegroundColor Yellow
    Read-Host "  CALISTIR'a bastın mı? (Enter)"

    Write-Host "  $strategyName TAMAM!" -ForegroundColor Green
    Write-Host ""
}

# === ANA AKIS ===
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  MatriksIQ Strateji Yukleyici" -ForegroundColor Cyan
Write-Host "  4 strateji yuklenecek" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$deployDir = "DEPLOY_DIR_PLACEHOLDER"

Write-Host "MatriksIQ'da yeni strateji editoru acik mi?" -ForegroundColor Yellow
Write-Host "Acik degilse: Algo sekmesi > Yeni Strateji > Bos strateji ac" -ForegroundColor Yellow
Read-Host "Hazirsan Enter'a bas"

Deploy-Strategy "$deployDir\BOMBA_ENJSA.cs" "BOMBA_ENJSA"
Deploy-Strategy "$deployDir\BOMBA_HALKB.cs" "BOMBA_HALKB"
Deploy-Strategy "$deployDir\BOMBA_GUBRF.cs" "BOMBA_GUBRF"
Deploy-Strategy "$deployDir\BOMBA_GARAN.cs" "BOMBA_GARAN"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  TAMAMLANDI! 4 strateji yuklendi." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
'''

    ahk_script = ahk_script.replace("DEPLOY_DIR_PLACEHOLDER", WIN_DEPLOY_DIR)
    return ahk_script


def deploy_all():
    """Ana fonksiyon — tüm stratejileri yükle."""
    print("=" * 50)
    print("🤖 MatriksIQ Strateji Yükleyici")
    print("=" * 50)
    print()

    # 1. IQ çalışıyor mu?
    print("🔍 MatriksIQ kontrol ediliyor...")
    if not check_iq_running():
        print("❌ MatriksIQ çalışmıyor! Önce IQ'yu aç.")
        return False
    print("  ✅ MatriksIQ çalışıyor")

    # 2. Dosyaları kopyala
    copy_files_to_windows()

    # 3. PowerShell otomasyon scriptini oluştur ve Windows'a kaydet
    print("\n📝 Otomasyon scripti hazırlanıyor...")
    script = create_ahk_script()
    script_path = f"{WIN_DEPLOY_DIR}\\deploy_strategies.ps1"

    # Scripti Windows'a yaz
    # Önce Mac'te temp dosyaya yaz, sonra kopyala
    temp_path = "/tmp/deploy_strategies.ps1"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(script)

    run_win(f'copy "\\\\Mac\\Home\\..\\..\\tmp\\deploy_strategies.ps1" "{script_path}" /Y')
    print("  ✅ Script hazır")

    # 4. Scripti çalıştır
    print("\n🚀 Otomasyon başlatılıyor...")
    print("  Windows'ta PowerShell penceresi açılacak.")
    print("  Adımları takip et — her strateji için:")
    print("    1. Kod otomatik yapıştırılacak")
    print("    2. Sen DERLE butonuna bas")
    print("    3. Sen ÇALIŞTIR butonuna bas")
    print("    4. Enter'a bas → sonraki strateji")
    print()

    # PowerShell scriptini Windows'ta çalıştır
    run_win(
        f'start powershell -ExecutionPolicy Bypass -File "{script_path}"'
    )
    print("✅ Windows'ta script başlatıldı!")
    return True


def check_strategies():
    """Çalışan stratejileri kontrol et."""
    print("🔍 Strateji durumu kontrol ediliyor...")

    if not check_iq_running():
        print("❌ MatriksIQ çalışmıyor!")
        return

    # Log dosyalarını kontrol et
    for name in STRATEGIES:
        log_dir = f"C:\\MatriksIQ\\Logs\\AlgoTrading\\{name}"
        out = run_win(f'dir "{log_dir}" /b /o-d 2>nul')
        if out:
            print(f"  ✅ {name} — log var: {out.split(chr(10))[0]}")
        else:
            print(f"  ❌ {name} — log yok (çalışmamış olabilir)")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_strategies()
    elif "--copy" in sys.argv:
        copy_files_to_windows()
    else:
        deploy_all()
