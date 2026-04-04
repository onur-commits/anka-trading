"""
ANKA/COIN Watchdog & Heartbeat Sistemi
=======================================
- otonom_trader.py calisma kontrolu
- v3_risk_motor.py calisma kontrolu
- Matriks IQ VM kontrolu (prlctl exec)
- Bridge dosyasi tazelik kontrolu (<5 dk)
- Otomatik yeniden baslatma
- macOS bildirimi
- 60 saniyede bir kontrol
- data/watchdog_log.json'a loglama

Kullanim:
  python watchdog.py           # Surekli izleme (60sn dongu)
  python watchdog.py --once    # Tek kontrol
  python watchdog.py --status  # Durum goster
"""

import os
import sys
import json
import time
import subprocess
import platform
from datetime import datetime, timedelta
from pathlib import Path


# ── YAPILANDIRMA ───────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

LOG_FILE = DATA_DIR / "watchdog_log.json"
STATUS_FILE = DATA_DIR / "watchdog_status.json"

BRIDGE_FILE = DATA_DIR / "v3_bridge.json"
BRIDGE_MAX_AGE_MIN = 5

CHECK_INTERVAL = 60  # saniye

# Izlenecek process'ler
MONITORED = {
    "otonom_trader": {
        "script": "otonom_trader.py",
        "process_name": "otonom_trader.py",
        "restart_cmd": [sys.executable, str(BASE_DIR / "otonom_trader.py")],
        "critical": True,
    },
    "v3_risk_motor": {
        "script": "v3_risk_motor.py",
        "process_name": "v3_risk_motor.py",
        "restart_cmd": [sys.executable, str(BASE_DIR / "v3_risk_motor.py")],
        "critical": True,
    },
}

IS_MAC = platform.system() == "Darwin"


# ============================================================
# YARDIMCI FONKSIYONLAR
# ============================================================

def mac_notify(title: str, message: str):
    """macOS bildirim gonder."""
    if not IS_MAC:
        return
    try:
        script = f'display notification "{message}" with title "{title}" sound name "Basso"'
        subprocess.run(
            ["osascript", "-e", script],
            timeout=5,
            capture_output=True,
        )
    except Exception:
        pass


def is_process_running(process_name: str) -> bool:
    """Bir Python script'inin calisip calismadigini kontrol et."""
    try:
        if IS_MAC or platform.system() == "Linux":
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True, text=True, timeout=5
            )
            # pgrep kendi PID'ini ve watchdog PID'ini cikar
            pids = result.stdout.strip().split("\n")
            own_pid = str(os.getpid())
            valid_pids = [p for p in pids if p.strip() and p.strip() != own_pid]
            return len(valid_pids) > 0
        else:
            # Windows
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq python*"],
                capture_output=True, text=True, timeout=5
            )
            return process_name in result.stdout
    except Exception:
        return False


def check_iq_running() -> bool:
    """Matriks IQ'nun Parallels VM'de calisip calismadigini kontrol et."""
    try:
        # Parallels VM listesi
        result = subprocess.run(
            ["prlctl", "list", "-a"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return False

        # Calisan Windows VM var mi?
        lines = result.stdout.strip().split("\n")
        running_vms = [l for l in lines if "running" in l.lower()]
        if not running_vms:
            return False

        # VM icinde IQ calisma kontrolu
        for line in running_vms:
            # VM name'i parse et
            parts = line.split()
            if len(parts) < 2:
                continue
            vm_id = parts[0]  # UUID

            try:
                iq_check = subprocess.run(
                    ["prlctl", "exec", vm_id, "tasklist", "/FI",
                     "IMAGENAME eq MatriksIQ*"],
                    capture_output=True, text=True, timeout=15
                )
                if "MatriksIQ" in iq_check.stdout:
                    return True
            except Exception:
                continue

        return False
    except FileNotFoundError:
        # prlctl yok = Parallels kurulu degil, atla
        return None  # None = kontrol edilemedi
    except Exception:
        return None


def check_bridge_fresh() -> dict:
    """Bridge dosyasinin tazelik kontrolu."""
    if not BRIDGE_FILE.exists():
        return {"fresh": False, "reason": "dosya_yok", "age_min": None}

    try:
        mtime = datetime.fromtimestamp(BRIDGE_FILE.stat().st_mtime)
        age = datetime.now() - mtime
        age_min = round(age.total_seconds() / 60, 1)

        if age_min > BRIDGE_MAX_AGE_MIN:
            return {"fresh": False, "reason": "eski", "age_min": age_min}

        # Icerik kontrolu
        data = json.loads(BRIDGE_FILE.read_text())
        if not data:
            return {"fresh": False, "reason": "bos_dosya", "age_min": age_min}

        return {"fresh": True, "reason": "ok", "age_min": age_min}

    except Exception as e:
        return {"fresh": False, "reason": str(e)[:100], "age_min": None}


def restart_process(name: str, config: dict) -> bool:
    """Process'i yeniden baslat."""
    try:
        print(f"  [RESTART] {name} baslatiliyor...")
        # Nohup benzeri arka planda baslat
        proc = subprocess.Popen(
            config["restart_cmd"],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(2)  # Baslamasi icin kisa bekle

        # Basariyla basladigini kontrol et
        if proc.poll() is None:
            print(f"  [OK] {name} baslatildi (PID: {proc.pid})")
            mac_notify("Watchdog Restart", f"{name} yeniden baslatildi (PID: {proc.pid})")
            return True
        else:
            print(f"  [FAIL] {name} baslatilamadi (exit: {proc.returncode})")
            mac_notify("Watchdog HATA", f"{name} baslatilamadi!")
            return False
    except Exception as e:
        print(f"  [ERROR] {name} restart hatasi: {e}")
        mac_notify("Watchdog HATA", f"{name} restart hatasi: {str(e)[:50]}")
        return False


def restart_iq_vm() -> bool:
    """Matriks IQ VM'i yeniden baslat."""
    try:
        # Calisan Windows VM'i bul
        result = subprocess.run(
            ["prlctl", "list", "-a"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")

        for line in lines:
            if "windows" in line.lower() or "win" in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    vm_id = parts[0]
                    # VM'i durdur ve baslat
                    subprocess.run(["prlctl", "stop", vm_id], timeout=30, capture_output=True)
                    time.sleep(5)
                    subprocess.run(["prlctl", "start", vm_id], timeout=30, capture_output=True)
                    mac_notify("Watchdog", "Matriks IQ VM yeniden baslatildi")
                    return True

        return False
    except Exception:
        return False


# ============================================================
# LOGLAMA
# ============================================================

def log_status(status: dict):
    """Durum logla."""
    try:
        log = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    except Exception:
        log = []

    log.append(status)
    # Son 1440 kayit tut (24 saat x 60 kontrol)
    log = log[-1440:]

    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False))

    # Guncel durum dosyasi
    STATUS_FILE.write_text(json.dumps(status, indent=2, ensure_ascii=False))


# ============================================================
# ANA KONTROL DONGUSU
# ============================================================

def run_check(auto_restart: bool = True) -> dict:
    """Tek bir kontrol dongusu calistir."""
    ts = datetime.now().isoformat()
    status = {
        "ts": ts,
        "checks": {},
        "alerts": [],
        "restarts": [],
        "all_ok": True,
    }

    print(f"\n[{ts}] Watchdog kontrol...")

    # 1) Python process'leri kontrol et
    for name, config in MONITORED.items():
        running = is_process_running(config["process_name"])
        status["checks"][name] = {
            "running": running,
            "script": config["script"],
        }

        if running:
            print(f"  [OK] {name}")
        else:
            status["all_ok"] = False
            msg = f"{name} CALISMYIOR!"
            print(f"  [ALARM] {msg}")
            status["alerts"].append(msg)

            if auto_restart and config.get("critical"):
                success = restart_process(name, config)
                status["restarts"].append({
                    "name": name,
                    "success": success,
                    "ts": datetime.now().isoformat(),
                })

    # 2) IQ VM kontrolu
    iq_status = check_iq_running()
    if iq_status is None:
        status["checks"]["matriks_iq"] = {"running": None, "note": "kontrol_edilemedi"}
        print("  [SKIP] Matriks IQ (Parallels bulunamadi)")
    elif iq_status:
        status["checks"]["matriks_iq"] = {"running": True}
        print("  [OK] Matriks IQ")
    else:
        status["checks"]["matriks_iq"] = {"running": False}
        status["all_ok"] = False
        msg = "Matriks IQ CALISMYIOR!"
        print(f"  [ALARM] {msg}")
        status["alerts"].append(msg)
        mac_notify("Watchdog ALARM", msg)

        if auto_restart:
            success = restart_iq_vm()
            status["restarts"].append({
                "name": "matriks_iq",
                "success": success,
                "ts": datetime.now().isoformat(),
            })

    # 3) Bridge dosyasi kontrolu
    bridge = check_bridge_fresh()
    status["checks"]["bridge_file"] = bridge

    if bridge["fresh"]:
        print(f"  [OK] Bridge dosyasi (yas: {bridge['age_min']} dk)")
    else:
        status["all_ok"] = False
        msg = f"Bridge dosyasi sorunlu: {bridge['reason']}"
        if bridge["age_min"]:
            msg += f" (yas: {bridge['age_min']} dk)"
        print(f"  [ALARM] {msg}")
        status["alerts"].append(msg)
        mac_notify("Watchdog ALARM", msg)

    # Genel durum
    if status["all_ok"]:
        print("  === TUM SISTEMLER NORMAL ===")
    else:
        alert_count = len(status["alerts"])
        print(f"  === {alert_count} ALARM AKTIF ===")
        mac_notify(
            "Watchdog Ozet",
            f"{alert_count} sistem sorunu tespit edildi!"
        )

    log_status(status)
    return status


def show_status():
    """Son durumu goster."""
    if not STATUS_FILE.exists():
        print("Henuz kontrol yapilmamis. 'python watchdog.py --once' ile baslatin.")
        return

    data = json.loads(STATUS_FILE.read_text())
    print("\n" + "=" * 50)
    print("  WATCHDOG SON DURUM")
    print(f"  Son kontrol: {data['ts']}")
    print("=" * 50)

    for name, info in data.get("checks", {}).items():
        running = info.get("running")
        if running is True:
            sym = "[OK]"
        elif running is False:
            sym = "[XX]"
        elif running is None:
            sym = "[--]"
        else:
            # Bridge kontrolu
            if info.get("fresh"):
                sym = "[OK]"
            else:
                sym = "[XX]"

        extra = ""
        if "age_min" in info and info["age_min"]:
            extra = f" (yas: {info['age_min']} dk)"
        if "note" in info:
            extra = f" ({info['note']})"

        print(f"  {sym} {name}{extra}")

    alerts = data.get("alerts", [])
    if alerts:
        print(f"\n  ALARMLAR ({len(alerts)}):")
        for a in alerts:
            print(f"    ! {a}")

    restarts = data.get("restarts", [])
    if restarts:
        print(f"\n  YENIDEN BASLATMALAR ({len(restarts)}):")
        for r in restarts:
            ok = "BASARILI" if r["success"] else "BASARISIZ"
            print(f"    - {r['name']}: {ok} ({r['ts']})")

    print("=" * 50 + "\n")


def show_log_summary():
    """Log ozetini goster."""
    if not LOG_FILE.exists():
        print("Log dosyasi bulunamadi.")
        return

    log = json.loads(LOG_FILE.read_text())
    total = len(log)
    alerts = sum(1 for entry in log if not entry.get("all_ok"))
    restarts = sum(len(entry.get("restarts", [])) for entry in log)

    print(f"\nLog ozeti: {total} kontrol | {alerts} alarmli | {restarts} restart")

    # Son 5 alarmli kayit
    alarmed = [e for e in log if not e.get("all_ok")]
    if alarmed:
        print("\nSon alarmlar:")
        for e in alarmed[-5:]:
            print(f"  {e['ts']}: {', '.join(e.get('alerts', []))}")


# ============================================================
# CLI
# ============================================================

def main():
    if "--status" in sys.argv or "--durum" in sys.argv:
        show_status()
        return

    if "--log" in sys.argv:
        show_log_summary()
        return

    if "--once" in sys.argv or "--tek" in sys.argv:
        run_check(auto_restart=True)
        return

    # Surekli izleme dongusu
    print("=" * 50)
    print("  WATCHDOG BASLATILDI")
    print(f"  Kontrol araligi: {CHECK_INTERVAL} saniye")
    print(f"  Log: {LOG_FILE}")
    print("=" * 50)

    mac_notify("Watchdog", "Izleme sistemi baslatildi")

    while True:
        try:
            run_check(auto_restart=True)
        except Exception as e:
            print(f"  [HATA] Kontrol hatasi: {e}")
            mac_notify("Watchdog HATA", f"Kontrol hatasi: {str(e)[:50]}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
