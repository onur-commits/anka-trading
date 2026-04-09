"""
ANKA Mühendis — Otonom Bakım & Onarım Sistemi
================================================
Sen yokken ANKA'nın teknik işlerini yapar:
- Dashboard'lar çöktüyse yeniden başlatır
- Disk/bellek/CPU kontrolü
- Veri bütünlüğü kontrolü (JSON bozuk mu?)
- Log temizliği
- Hata tespiti ve otomatik düzeltme
- Günlük sağlık raporu

Kullanım:
  python anka_muhendis.py              # Tam bakım döngüsü (sürekli)
  python anka_muhendis.py --kontrol    # Tek seferlik kontrol
  python anka_muhendis.py --rapor      # Sağlık raporu
"""

import sys
import os
import json
import time
import subprocess
import traceback
import shutil
import schedule
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
MUHENDIS_LOG = LOG_DIR / "muhendis_log.json"
LOG_DIR.mkdir(exist_ok=True)

# ============================================================
# LOG SİSTEMİ
# ============================================================

def log(mesaj, seviye="INFO", kategori="GENEL"):
    """Yapılandırılmış log."""
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "zaman": zaman,
        "seviye": seviye,
        "kategori": kategori,
        "mesaj": mesaj,
    }
    print(f"[{zaman}] [{seviye}] [{kategori}] {mesaj}")

    try:
        logs = []
        if MUHENDIS_LOG.exists():
            with open(MUHENDIS_LOG) as f:
                logs = json.load(f)
        logs.append(entry)
        logs = logs[-1000:]  # Son 1000 kayıt
        with open(MUHENDIS_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=1)
    except Exception:
        pass

    return entry


# ============================================================
# KONTROLLER
# ============================================================

def kontrol_dashboard():
    """Streamlit dashboard'lar çalışıyor mu?"""
    sonuc = {"bist": False, "coin": False, "sorunlar": []}

    try:
        import psutil
    except ImportError:
        # psutil yoksa netstat ile kontrol
        try:
            r = subprocess.run(
                ["netstat", "-an"], capture_output=True, text=True, timeout=10
            )
            output = r.stdout
            sonuc["bist"] = ":8501" in output and "LISTENING" in output
            sonuc["coin"] = ":8502" in output and "LISTENING" in output
        except Exception as e:
            sonuc["sorunlar"].append(f"Port kontrol hatası: {e}")
            return sonuc
    else:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if "streamlit" in cmdline and "app.py" in cmdline:
                    sonuc["bist"] = True
                if "streamlit" in cmdline and "coin_dashboard" in cmdline:
                    sonuc["coin"] = True
            except Exception:
                continue

    if not sonuc["bist"]:
        sonuc["sorunlar"].append("BIST Dashboard (8501) çalışmıyor!")
    if not sonuc["coin"]:
        sonuc["sorunlar"].append("COIN Dashboard (8502) çalışmıyor!")

    return sonuc


def kontrol_veri_butunlugu():
    """JSON dosyaları bozuk mu?"""
    sorunlar = []
    json_dosyalar = list(DATA_DIR.glob("*.json"))

    for f in json_dosyalar:
        try:
            with open(f, encoding="utf-8") as fp:
                json.load(fp)
        except json.JSONDecodeError as e:
            sorunlar.append(f"BOZUK JSON: {f.name} — {e}")
            # Yedekle ve sıfırla
            yedek = f.with_suffix(".json.bak")
            shutil.copy2(f, yedek)
            with open(f, "w", encoding="utf-8") as fp:
                if "log" in f.name:
                    json.dump([], fp)
                else:
                    json.dump({}, fp)
            sorunlar.append(f"  → {f.name} yedeklendi ve sıfırlandı")
        except Exception as e:
            sorunlar.append(f"OKUNAMADI: {f.name} — {e}")

    return sorunlar


def kontrol_disk():
    """Disk doluluk kontrolü."""
    sorunlar = []
    try:
        usage = shutil.disk_usage(str(BASE_DIR))
        yuzde = usage.used / usage.total * 100
        bos_gb = usage.free / (1024**3)

        if yuzde > 90:
            sorunlar.append(f"KRİTİK: Disk %{yuzde:.0f} dolu! Sadece {bos_gb:.1f} GB boş!")
        elif yuzde > 80:
            sorunlar.append(f"UYARI: Disk %{yuzde:.0f} dolu, {bos_gb:.1f} GB boş")
    except Exception as e:
        sorunlar.append(f"Disk kontrol hatası: {e}")

    return sorunlar


def kontrol_log_boyut():
    """Log dosyaları çok büyümüş mü?"""
    sorunlar = []
    temizlenen = 0

    for log_file in LOG_DIR.glob("*.log"):
        boyut_mb = log_file.stat().st_size / (1024 * 1024)
        if boyut_mb > 50:
            # 50MB üstü logları kes
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                # Son 5000 satırı tut
                with open(log_file, "w", encoding="utf-8") as f:
                    f.writelines(lines[-5000:])
                sorunlar.append(f"LOG KESILDI: {log_file.name} ({boyut_mb:.0f}MB → kesildi)")
                temizlenen += 1
            except Exception as e:
                sorunlar.append(f"Log kesme hatası: {log_file.name} — {e}")

    # data/otonom_output.log kontrolü
    otonom_log = DATA_DIR / "otonom_output.log"
    if otonom_log.exists():
        boyut_mb = otonom_log.stat().st_size / (1024 * 1024)
        if boyut_mb > 20:
            try:
                with open(otonom_log, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                with open(otonom_log, "w", encoding="utf-8") as f:
                    f.writelines(lines[-3000:])
                sorunlar.append(f"OTONOM LOG KESILDI: {boyut_mb:.0f}MB → kesildi")
            except Exception:
                pass

    return sorunlar


def kontrol_python_hatalari():
    """Son hataları analiz et."""
    sorunlar = []

    # otonom_log.json son hataları
    try:
        if (DATA_DIR / "otonom_log.json").exists():
            with open(DATA_DIR / "otonom_log.json") as f:
                logs = json.load(f)
            hatalar = [l for l in logs[-50:] if l.get("seviye") in ("ERROR", "CRITICAL")]
            if hatalar:
                sorunlar.append(f"Son 50 log'da {len(hatalar)} hata var:")
                for h in hatalar[-3:]:
                    sorunlar.append(f"  [{h['zaman']}] {h['mesaj'][:100]}")
    except Exception:
        pass

    return sorunlar


def kontrol_veri_guncellik():
    """Veriler güncel mi?"""
    sorunlar = []
    simdi = datetime.now()

    kontrol_dosyalar = {
        "gunluk_bomba.json": 24,    # 24 saat
        "otonom_state.json": 24,
        "sabah_secim.json": 48,     # 48 saat
        "ajan_skorlari.json": 168,  # 1 hafta
    }

    for dosya, max_saat in kontrol_dosyalar.items():
        yol = DATA_DIR / dosya
        if yol.exists():
            mod_time = datetime.fromtimestamp(yol.stat().st_mtime)
            fark_saat = (simdi - mod_time).total_seconds() / 3600
            if fark_saat > max_saat:
                sorunlar.append(
                    f"ESKİMİŞ: {dosya} — {fark_saat:.0f} saat önce güncellendi "
                    f"(limit: {max_saat} saat)"
                )
        else:
            sorunlar.append(f"EKSİK: {dosya} bulunamadı!")

    return sorunlar


# ============================================================
# OTOMATİK ONARIM
# ============================================================

def onar_dashboard(hangisi):
    """Çökmüş dashboard'ı yeniden başlat."""
    if hangisi == "bist":
        cmd = 'start /B streamlit run C:\\ANKA\\app.py --server.port 8501 --server.headless true --server.address 0.0.0.0'
    elif hangisi == "coin":
        cmd = 'start /B streamlit run C:\\ANKA\\coin_dashboard.py --server.port 8502 --server.headless true --server.address 0.0.0.0'
    else:
        return False

    try:
        subprocess.Popen(cmd, shell=True)
        log(f"{hangisi.upper()} Dashboard yeniden başlatıldı", "WARNING", "ONARIM")
        return True
    except Exception as e:
        log(f"{hangisi.upper()} Dashboard başlatılamadı: {e}", "ERROR", "ONARIM")
        return False


# ============================================================
# SAĞLIK RAPORU
# ============================================================

def saglik_raporu():
    """Tam sistem sağlık raporu üret."""
    rapor = {
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kontroller": {},
        "toplam_sorun": 0,
        "toplam_onarim": 0,
        "durum": "SAGLIKLI",
    }

    # 1. Dashboard kontrolü
    log("Dashboard kontrolü...", "INFO", "KONTROL")
    dash = kontrol_dashboard()
    rapor["kontroller"]["dashboard"] = dash
    if dash["sorunlar"]:
        rapor["toplam_sorun"] += len(dash["sorunlar"])
        # Otomatik onarım dene
        if not dash["bist"]:
            if onar_dashboard("bist"):
                rapor["toplam_onarim"] += 1
        if not dash["coin"]:
            if onar_dashboard("coin"):
                rapor["toplam_onarim"] += 1

    # 2. Veri bütünlüğü
    log("Veri bütünlüğü kontrolü...", "INFO", "KONTROL")
    veri_sorunlar = kontrol_veri_butunlugu()
    rapor["kontroller"]["veri_butunlugu"] = veri_sorunlar
    rapor["toplam_sorun"] += len([s for s in veri_sorunlar if "BOZUK" in s])

    # 3. Disk
    log("Disk kontrolü...", "INFO", "KONTROL")
    disk_sorunlar = kontrol_disk()
    rapor["kontroller"]["disk"] = disk_sorunlar
    rapor["toplam_sorun"] += len(disk_sorunlar)

    # 4. Log boyutları
    log("Log boyut kontrolü...", "INFO", "KONTROL")
    log_sorunlar = kontrol_log_boyut()
    rapor["kontroller"]["log_boyut"] = log_sorunlar

    # 5. Python hataları
    log("Hata analizi...", "INFO", "KONTROL")
    hata_sorunlar = kontrol_python_hatalari()
    rapor["kontroller"]["hatalar"] = hata_sorunlar
    rapor["toplam_sorun"] += len(hata_sorunlar)

    # 6. Veri güncelliği
    log("Veri güncellik kontrolü...", "INFO", "KONTROL")
    guncellik = kontrol_veri_guncellik()
    rapor["kontroller"]["guncellik"] = guncellik
    rapor["toplam_sorun"] += len(guncellik)

    # Genel durum
    if rapor["toplam_sorun"] == 0:
        rapor["durum"] = "SAGLIKLI"
    elif rapor["toplam_sorun"] <= 3:
        rapor["durum"] = "UYARI"
    else:
        rapor["durum"] = "KRITIK"

    # Raporu kaydet
    rapor_dosya = DATA_DIR / f"saglik_rapor_{datetime.now().strftime('%Y%m%d')}.json"
    with open(rapor_dosya, "w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)

    log(
        f"Sağlık raporu: {rapor['durum']} — "
        f"{rapor['toplam_sorun']} sorun, {rapor['toplam_onarim']} onarım",
        "WARNING" if rapor["toplam_sorun"] > 0 else "INFO",
        "RAPOR",
    )

    return rapor


# ============================================================
# ZAMANLAYICI
# ============================================================

def bakim_dongusu():
    """Her 30 dakikada bir temel kontrol, günde 2 kere tam rapor."""
    log("=" * 50, "INFO", "SISTEM")
    log("ANKA Mühendis başlatıldı — otonom bakım aktif", "INFO", "SISTEM")
    log("=" * 50, "INFO", "SISTEM")

    # İlk kontrol
    saglik_raporu()

    # Zamanlamalar
    schedule.every(30).minutes.do(hizli_kontrol)
    schedule.every().day.at("06:00").do(saglik_raporu)
    schedule.every().day.at("18:00").do(saglik_raporu)
    schedule.every().day.at("02:00").do(gece_temizlik)

    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except KeyboardInterrupt:
            log("Mühendis durduruldu", "WARNING", "SISTEM")
            break
        except Exception as e:
            log(f"Döngü hatası: {e}", "ERROR", "SISTEM")
            time.sleep(300)


def hizli_kontrol():
    """30 dakikalık hızlı kontrol — sadece dashboard ve kritik sorunlar."""
    log("Hızlı kontrol başladı", "INFO", "KONTROL")

    dash = kontrol_dashboard()
    if dash["sorunlar"]:
        for s in dash["sorunlar"]:
            log(s, "WARNING", "DASHBOARD")
        if not dash["bist"]:
            onar_dashboard("bist")
        if not dash["coin"]:
            onar_dashboard("coin")

    # Kritik JSON kontrolü
    for dosya in ["otonom_state.json", "gunluk_bomba.json"]:
        yol = DATA_DIR / dosya
        if yol.exists():
            try:
                with open(yol) as f:
                    json.load(f)
            except json.JSONDecodeError:
                log(f"BOZUK JSON tespit: {dosya} — onarılıyor", "ERROR", "VERI")
                shutil.copy2(yol, yol.with_suffix(".json.bak"))
                with open(yol, "w") as f:
                    json.dump({}, f)

    log("Hızlı kontrol tamamlandı", "INFO", "KONTROL")


def gece_temizlik():
    """Gece 02:00 — eski log ve rapor temizliği."""
    log("Gece temizliği başladı", "INFO", "TEMIZLIK")

    simdi = datetime.now()
    temizlenen = 0

    # 7 günden eski raporları sil
    for f in DATA_DIR.glob("saglik_rapor_*.json"):
        try:
            mod = datetime.fromtimestamp(f.stat().st_mtime)
            if (simdi - mod).days > 7:
                f.unlink()
                temizlenen += 1
        except Exception:
            pass

    # 7 günden eski rapor txt'lerini sil
    for f in DATA_DIR.glob("rapor_*.txt"):
        try:
            mod = datetime.fromtimestamp(f.stat().st_mtime)
            if (simdi - mod).days > 14:
                f.unlink()
                temizlenen += 1
        except Exception:
            pass

    # .bak dosyalarını temizle (3 günden eski)
    for f in DATA_DIR.glob("*.bak"):
        try:
            mod = datetime.fromtimestamp(f.stat().st_mtime)
            if (simdi - mod).days > 3:
                f.unlink()
                temizlenen += 1
        except Exception:
            pass

    log(f"Gece temizliği tamamlandı: {temizlenen} dosya silindi", "INFO", "TEMIZLIK")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if "--kontrol" in sys.argv:
        rapor = saglik_raporu()
        print(f"\nDurum: {rapor['durum']}")
        print(f"Sorun: {rapor['toplam_sorun']}")
        print(f"Onarım: {rapor['toplam_onarim']}")

    elif "--rapor" in sys.argv:
        rapor = saglik_raporu()
        print(json.dumps(rapor, ensure_ascii=False, indent=2))

    else:
        bakim_dongusu()
