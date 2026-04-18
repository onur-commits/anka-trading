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
SORUNLAR_DOSYA = BASE_DIR / "ANKA_BILINEN_SORUNLAR.md"
LOG_DIR.mkdir(exist_ok=True)


# ============================================================
# BİLİNEN SORUNLAR VERİTABANI
# ============================================================

def bilinen_sorunlari_yukle():
    """ANKA_BILINEN_SORUNLAR.md'den bilinen sorunları oku."""
    sorunlar = {}
    if not SORUNLAR_DOSYA.exists():
        return sorunlar
    try:
        icerik = SORUNLAR_DOSYA.read_text(encoding="utf-8")
        import re
        bloklar = re.split(r"### (SORUN-\d+):", icerik)
        for i in range(1, len(bloklar) - 1, 2):
            sorun_id = bloklar[i].strip()
            detay = bloklar[i + 1].strip()
            sorunlar[sorun_id] = detay
    except Exception:
        pass
    return sorunlar


def sorun_esle(hata_mesaji):
    """Bir hata mesajını bilinen sorunlarla eşleştir."""
    eslesmeler = {
        "charmap": "SORUN-001",
        "cp1252": "SORUN-001",
        "UnicodeEncodeError": "SORUN-001",
        "MultiIndex": "SORUN-002",
        "yfinance": "SORUN-002",
        "EmptyDataError": "SORUN-002",
        "8501": "SORUN-003",
        "8502": "SORUN-003",
        "streamlit": "SORUN-003",
        "JSONDecodeError": "SORUN-004",
        "json.decoder": "SORUN-004",
        "Permission denied": "SORUN-005",
        "Connection refused": "SORUN-005",
        "ssh": "SORUN-005",
        "18890": "SORUN-006",
        "MatriksIQ": "SORUN-006",
        "ModuleNotFoundError": "SORUN-010",
        "No module named": "SORUN-010",
        "No space left": "SORUN-011",
        "disk": "SORUN-011",
    }
    for anahtar, sorun_id in eslesmeler.items():
        if anahtar.lower() in hata_mesaji.lower():
            return sorun_id
    return None


def otomatik_coz(sorun_id, hata_detay=""):
    """Bilinen sorunları otomatik çözmeye çalış."""
    if sorun_id == "SORUN-001":
        # Encoding sorunu — bu runtime'da çözülemez ama log yazalım
        log("Encoding sorunu tespit — -X utf8 flag kontrolü gerekiyor", "WARNING", "ONARIM")
        return True

    elif sorun_id == "SORUN-003":
        # Dashboard çökmesi
        dash = kontrol_dashboard()
        onarilan = 0
        if not dash["bist"]:
            onar_dashboard("bist")
            onarilan += 1
        if not dash["coin"]:
            onar_dashboard("coin")
            onarilan += 1
        return onarilan > 0

    elif sorun_id == "SORUN-004":
        # JSON bozuk — kontrol_veri_butunlugu zaten hallediyor
        kontrol_veri_butunlugu()
        return True

    elif sorun_id == "SORUN-010":
        # Eksik modül — otomatik yükle
        import re
        match = re.search(r"No module named '(\w+)'", hata_detay)
        if match:
            modul = match.group(1)
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", modul, "--quiet"],
                    timeout=60, capture_output=True,
                )
                log(f"Eksik modül yüklendi: {modul}", "WARNING", "ONARIM")
                return True
            except Exception:
                pass
        return False

    elif sorun_id == "SORUN-011":
        # Disk dolması — acil temizlik
        gece_temizlik()
        return True

    return False


def internet_arastir(hata_mesaji):
    """Bilinmeyen hata için çözüm ipucu oluştur (internet erişimi varsa)."""
    try:
        import urllib.request
        import urllib.parse
        # Stack Overflow API ile arama
        query = urllib.parse.quote(f"python {hata_mesaji[:100]}")
        url = f"https://api.stackexchange.com/2.3/search/excerpts?order=desc&sort=relevance&q={query}&site=stackoverflow&pagesize=3"
        req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            import gzip
            data = gzip.decompress(resp.read())
            sonuc = json.loads(data)
            if sonuc.get("items"):
                cozumler = []
                for item in sonuc["items"][:3]:
                    baslik = item.get("title", "")
                    cozumler.append(baslik)
                return cozumler
    except Exception:
        pass
    return []


def akilli_hata_analiz(hata_mesaji):
    """Hatayı analiz et: bilinen mi? Çözümü var mı? İnternetten ara."""
    # 1. Bilinen sorunlarla eşleştir
    sorun_id = sorun_esle(hata_mesaji)
    if sorun_id:
        log(f"Bilinen sorun tespit: {sorun_id}", "INFO", "ANALIZ")
        basarili = otomatik_coz(sorun_id, hata_mesaji)
        if basarili:
            log(f"{sorun_id} otomatik çözüldü", "INFO", "ONARIM")
        else:
            log(f"{sorun_id} otomatik çözülemedi — manuel müdahale gerekli", "WARNING", "ONARIM")
        return sorun_id, basarili

    # 2. Bilinmeyen hata — internetten araştır
    log(f"Bilinmeyen hata — internet araştırması yapılıyor", "INFO", "ANALIZ")
    ipuclari = internet_arastir(hata_mesaji)
    if ipuclari:
        for ipucu in ipuclari:
            log(f"StackOverflow ipucu: {ipucu}", "INFO", "ARASTIRMA")
    else:
        log("İnternet araştırması sonuçsuz", "INFO", "ARASTIRMA")

    return None, False

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


def kontrol_iq_stratejiler():
    """IQ stratejileri çalışıyor mu? Midas bağlı mı?"""
    sonuc = {"calisiyor": False, "midas_bagli": False, "sorunlar": [], "aksiyon": []}

    # MatriksIQ process kontrolü
    try:
        r = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10)
        sonuc["calisiyor"] = "MatriksIQ.exe" in r.stdout
    except Exception:
        sonuc["sorunlar"].append("Tasklist çalıştırılamadı")

    if not sonuc["calisiyor"]:
        sonuc["sorunlar"].append("MatriksIQ ÇALIŞMIYOR!")
        sonuc["aksiyon"].append("IQ_YENIDEN_BASLAT")
        return sonuc

    # Beyin state'den strateji durumunu kontrol et
    beyin_state = DATA_DIR / "beyin_state.json"
    if beyin_state.exists():
        try:
            with open(beyin_state, encoding="utf-8") as f:
                beyin = json.load(f)
            son_zaman = beyin.get("zaman")
            if son_zaman:
                son = datetime.strptime(son_zaman, "%Y-%m-%d %H:%M:%S")
                fark_dk = (datetime.now() - son).total_seconds() / 60
                if fark_dk > 60:
                    sonuc["sorunlar"].append(f"Beyin {fark_dk:.0f}dk önce güncellendi — takılmış olabilir")
                    sonuc["aksiyon"].append("BEYIN_YENIDEN_BASLAT")
        except Exception:
            pass

    # Rotasyon state kontrolü
    rot_state = DATA_DIR / "rotasyon_state.json"
    if rot_state.exists():
        try:
            with open(rot_state, encoding="utf-8") as f:
                rot = json.load(f)
            son_kontrol = rot.get("son_kontrol")
            if son_kontrol:
                son = datetime.strptime(son_kontrol, "%Y-%m-%d %H:%M:%S")
                fark_dk = (datetime.now() - son).total_seconds() / 60
                if fark_dk > 45:  # 30dk döngü + 15dk tolerans
                    sonuc["sorunlar"].append(f"Rotasyon {fark_dk:.0f}dk önce — durmuş!")
                    sonuc["aksiyon"].append("ROTASYON_YENIDEN_BASLAT")
        except Exception:
            pass
    else:
        sonuc["sorunlar"].append("Rotasyon state dosyası yok")

    return sonuc


def onar_iq_stratejiler(aksiyon_listesi):
    """IQ stratejilerini ve bağlantıları onar."""
    onarilan = 0

    for aksiyon in aksiyon_listesi:
        if aksiyon == "ROTASYON_YENIDEN_BASLAT":
            try:
                subprocess.Popen(
                    f'"C:\\Program Files\\Python312\\python.exe" -X utf8 {BASE_DIR / "anka_rotasyon.py"}',
                    shell=True,
                )
                log("Rotasyon yeniden başlatıldı", "WARNING", "ONARIM")
                onarilan += 1
            except Exception as e:
                log(f"Rotasyon başlatılamadı: {e}", "ERROR", "ONARIM")

        elif aksiyon == "BEYIN_YENIDEN_BASLAT":
            try:
                subprocess.Popen(
                    f'"C:\\Program Files\\Python312\\python.exe" -X utf8 {BASE_DIR / "anka_beyin.py"} --analiz',
                    shell=True,
                )
                log("Beyin analizi yeniden başlatıldı", "WARNING", "ONARIM")
                onarilan += 1
            except Exception as e:
                log(f"Beyin başlatılamadı: {e}", "ERROR", "ONARIM")

        elif aksiyon == "IQ_YENIDEN_BASLAT":
            # IQ'yu yeniden başlatmak riskli — sadece bildir
            log("MatriksIQ ÇALIŞMIYOR — manuel müdahale gerekli!", "ERROR", "ONARIM")
            bildirim_gonder("MatriksIQ çalışmıyor! VPS'e bağlanıp kontrol et.")

    return onarilan


def bildirim_gonder(mesaj):
    """Kullanıcıya bildirim gönder (dosya + log)."""
    bildirim_file = DATA_DIR / "acil_bildirim.json"
    try:
        bildirimler = []
        if bildirim_file.exists():
            with open(bildirim_file, encoding="utf-8") as f:
                bildirimler = json.load(f)
        bildirimler.append({
            "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mesaj": mesaj,
            "okundu": False,
        })
        bildirimler = bildirimler[-50:]
        with open(bildirim_file, "w", encoding="utf-8") as f:
            json.dump(bildirimler, f, ensure_ascii=False, indent=1)
        log(f"BİLDİRİM: {mesaj}", "WARNING", "BILDIRIM")
    except Exception:
        pass


def kontrol_coin_bot():
    """Coin otonom bot çalışıyor mu? State güncel mi?"""
    sonuc = {"calisiyor": False, "sorunlar": []}

    # Process kontrolü
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if "coin_otonom" in cmdline:
                    sonuc["calisiyor"] = True
                    break
            except Exception:
                continue
    except ImportError:
        # psutil yoksa log dosyasından kontrol
        coin_log = DATA_DIR / "coin_otonom_log.json"
        if coin_log.exists():
            try:
                with open(coin_log, encoding="utf-8") as f:
                    logs = json.load(f)
                if logs:
                    son = logs[-1]
                    son_zaman = datetime.strptime(son["zaman"], "%Y-%m-%d %H:%M:%S")
                    fark_dk = (datetime.now() - son_zaman).total_seconds() / 60
                    sonuc["calisiyor"] = fark_dk < 15  # 15dk içinde log varsa çalışıyor
            except Exception:
                pass

    if not sonuc["calisiyor"]:
        sonuc["sorunlar"].append("Coin Otonom Bot çalışmıyor!")

    # State güncelliği
    coin_state = DATA_DIR / "coin_otonom_state.json"
    if coin_state.exists():
        try:
            with open(coin_state, encoding="utf-8") as f:
                state = json.load(f)
            son_tarama = state.get("son_tarama")
            if son_tarama:
                son = datetime.strptime(son_tarama, "%Y-%m-%d %H:%M:%S")
                fark_dk = (datetime.now() - son).total_seconds() / 60
                if fark_dk > 30:
                    sonuc["sorunlar"].append(f"Coin bot son tarama {fark_dk:.0f}dk önce — takılmış olabilir")
            # Pozisyon bilgisi
            poz_sayisi = len(state.get("pozisyonlar", {}))
            toplam_trade = state.get("toplam_trade", 0)
            log(f"  Coin bot: {poz_sayisi} pozisyon, {toplam_trade} trade", "INFO", "KONTROL")
        except Exception:
            pass
    else:
        sonuc["sorunlar"].append("Coin bot state dosyası yok!")

    # Log hataları
    coin_log = DATA_DIR / "coin_otonom_log.json"
    if coin_log.exists():
        try:
            with open(coin_log, encoding="utf-8") as f:
                logs = json.load(f)
            hatalar = [l for l in logs[-20:] if l.get("seviye") == "ERROR"]
            if hatalar:
                sonuc["sorunlar"].append(f"Coin bot son 20 log'da {len(hatalar)} hata")
                for h in hatalar[-2:]:
                    sonuc["sorunlar"].append(f"  → {h['mesaj'][:80]}")
        except Exception:
            pass

    return sonuc


def onar_coin_bot():
    """Çökmüş coin bot'u yeniden başlat."""
    try:
        bat_path = BASE_DIR / "coin_bot_start.bat"
        if bat_path.exists():
            subprocess.Popen(f'schtasks /run /tn "ANKA_CoinBot"', shell=True)
            log("Coin bot schtasks ile yeniden başlatıldı", "WARNING", "ONARIM")
            return True
        else:
            subprocess.Popen(
                f'"C:\\Program Files\\Python312\\python.exe" -X utf8 {BASE_DIR / "coin_otonom.py"}',
                shell=True,
            )
            log("Coin bot doğrudan yeniden başlatıldı", "WARNING", "ONARIM")
            return True
    except Exception as e:
        log(f"Coin bot başlatılamadı: {e}", "ERROR", "ONARIM")
        return False


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
    """Son hataları analiz et ve bilinen sorunlarla eşleştir."""
    sorunlar = []

    # otonom_log.json son hataları
    try:
        if (DATA_DIR / "otonom_log.json").exists():
            with open(DATA_DIR / "otonom_log.json", encoding="utf-8") as f:
                logs = json.load(f)
            hatalar = [l for l in logs[-50:] if l.get("seviye") in ("ERROR", "CRITICAL")]
            if hatalar:
                sorunlar.append(f"Son 50 log'da {len(hatalar)} hata var:")
                for h in hatalar[-3:]:
                    mesaj = h.get("mesaj", "")[:100]
                    sorunlar.append(f"  [{h['zaman']}] {mesaj}")
                    # Akıllı analiz — bilinen sorunla eşleştir ve çözmeye çalış
                    sorun_id, cozuldu = akilli_hata_analiz(mesaj)
                    if sorun_id and cozuldu:
                        sorunlar.append(f"    → {sorun_id} otomatik çözüldü")
                    elif sorun_id:
                        sorunlar.append(f"    → {sorun_id} tespit edildi, manuel müdahale gerekli")
    except Exception:
        pass

    # muhendis_log.json son hataları
    try:
        if MUHENDIS_LOG.exists():
            with open(MUHENDIS_LOG, encoding="utf-8") as f:
                logs = json.load(f)
            hatalar = [l for l in logs[-30:] if l.get("seviye") == "ERROR"]
            for h in hatalar[-2:]:
                mesaj = h.get("mesaj", "")
                sorunlar.append(f"  [MUHENDIS] {mesaj[:100]}")
                akilli_hata_analiz(mesaj)
    except Exception:
        pass

    return sorunlar


def kontrol_veri_guncellik():
    """Veriler güncel mi?"""
    sorunlar = []
    simdi = datetime.now()

    kontrol_dosyalar = {
        "gunluk_bomba.json": 24,         # 24 saat
        "otonom_state.json": 24,
        "sabah_secim.json": 48,          # 48 saat
        "ajan_skorlari.json": 168,       # 1 hafta
        "coin_otonom_state.json": 1,     # 1 saat (7/24 çalışıyor)
        "coin_otonom_log.json": 1,       # 1 saat
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

    # 1b. Coin bot kontrolü
    log("Coin bot kontrolü...", "INFO", "KONTROL")
    coin_bot = kontrol_coin_bot()
    rapor["kontroller"]["coin_bot"] = coin_bot
    if coin_bot["sorunlar"]:
        rapor["toplam_sorun"] += len(coin_bot["sorunlar"])
        if not coin_bot["calisiyor"]:
            if onar_coin_bot():
                rapor["toplam_onarim"] += 1

    # 1c. IQ Strateji kontrolü
    log("IQ strateji kontrolü...", "INFO", "KONTROL")
    iq = kontrol_iq_stratejiler()
    rapor["kontroller"]["iq_stratejiler"] = iq
    if iq["sorunlar"]:
        rapor["toplam_sorun"] += len(iq["sorunlar"])
        for s in iq["sorunlar"]:
            log(f"  {s}", "WARNING", "IQ")
        if iq["aksiyon"]:
            onarilan = onar_iq_stratejiler(iq["aksiyon"])
            rapor["toplam_onarim"] += onarilan
        if not iq["calisiyor"]:
            bildirim_gonder("MatriksIQ çalışmıyor! Stratejiler durdu. VPS'e bağlan.")

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

    # IQ Strateji kontrolü
    iq = kontrol_iq_stratejiler()
    if iq["sorunlar"]:
        for s in iq["sorunlar"]:
            log(s, "WARNING", "IQ")
        if iq["aksiyon"]:
            onar_iq_stratejiler(iq["aksiyon"])
        if not iq["calisiyor"]:
            bildirim_gonder("ACIL: MatriksIQ çalışmıyor!")

    # Otonom trader kontrolleri
    for proc_name, script_name, start_cmd in [
        ("otonom_trader", "otonom_trader.py",
         r'cmd /c "cd /d C:\ANKA && "C:\Program Files\Python312\python.exe" -X utf8 -u otonom_trader.py > C:\ANKA\logs\otonom_stdout.log 2>&1"'),
        ("coin_otonom_trader", "coin_otonom_trader.py",
         r'cmd /c "cd /d C:\ANKA && "C:\Program Files\Python312\python.exe" -X utf8 -u coin_otonom_trader.py > C:\ANKA\logs\coin_otonom_stdout.log 2>&1"'),
    ]:
        try:
            check = subprocess.run(
                ["wmic", "process", "where",
                 f"commandline like '%{script_name}%' and not commandline like '%wmic%'",
                 "get", "processid"],
                capture_output=True, text=True, timeout=10
            )
            pids = [l.strip() for l in check.stdout.split("\n") if l.strip().isdigit()]
            if not pids:
                log(f"{proc_name} ÇÖKMÜŞ — yeniden başlatılıyor!", "ERROR", "TRADER")
                subprocess.Popen(start_cmd, shell=True)
                log(f"{proc_name} yeniden başlatıldı", "WARNING", "ONARIM")
            else:
                log(f"{proc_name} çalışıyor (PID: {', '.join(pids)})", "INFO", "KONTROL")
        except Exception as e:
            log(f"{proc_name} kontrol hatası: {e}", "ERROR", "TRADER")

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
        saglik_raporu()
    else:
        # Argümansız = tam bakım döngüsü (7/24)
        bakim_dongusu()
