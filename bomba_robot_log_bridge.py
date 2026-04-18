"""
Bomba Robot Log Bridge — SORUN-009 Cozumu
==========================================
MatriksIQ C# robotlari IQ'nun kendi log sistemine yazar,
C:\ANKA\data dizinine yazmaz. Bu script:

1. aktif_bombalar.txt'den aktif bomba listesini okur
2. MatriksIQ log dizinlerini tarar (C:\MatriksIQ\Logs\, %APPDATA%\MatriksIQ\)
3. IQ API uzerinden canli robot durumunu sorgular
4. data/bomba_robot_status.json ve data/bomba_robot_log.json'a yazar

Kullanim:
  python -X utf8 bomba_robot_log_bridge.py              # Tek seferlik
  python -X utf8 bomba_robot_log_bridge.py --surekli    # 5dk arayla surekli
"""

import sys
import os
import json
import time
import glob as glob_mod
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# MatriksIQ log dizinleri (Windows VPS uzerinde)
IQ_LOG_PATHS = [
    Path(r"C:\MatriksIQ\Logs"),
    Path(os.path.expandvars(r"%APPDATA%\MatriksIQ\Logs")),
    Path(os.path.expandvars(r"%APPDATA%\MatriksIQ")),
    Path(r"C:\MatriksIQ\RobotLogs"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\MatriksIQ\Logs")),
]

AKTIF_BOMBALAR_DOSYA = DATA_DIR / "aktif_bombalar.txt"
STATUS_DOSYA = DATA_DIR / "bomba_robot_status.json"
LOG_DOSYA = DATA_DIR / "bomba_robot_log.json"


def aktif_bombalari_oku():
    """data/aktif_bombalar.txt'den aktif bomba sembollerini oku."""
    if not AKTIF_BOMBALAR_DOSYA.exists():
        # VPS'te C:\Robot\aktif_bombalar.txt de olabilir
        alt_yol = Path(r"C:\Robot\aktif_bombalar.txt")
        if alt_yol.exists():
            icerik = alt_yol.read_text(encoding="utf-8").strip()
        else:
            print("[WARN] aktif_bombalar.txt bulunamadi")
            return []
    else:
        icerik = AKTIF_BOMBALAR_DOSYA.read_text(encoding="utf-8").strip()

    if not icerik:
        return []
    return [s.strip() for s in icerik.split(",") if s.strip()]


def iq_log_dizinlerini_tara(bombalar):
    """MatriksIQ log dizinlerinde bomba robotlarina ait log dosyalarini bul."""
    bulunan_loglar = {}

    for log_dir in IQ_LOG_PATHS:
        if not log_dir.exists():
            continue

        # Tum log dosyalarini tara
        for log_dosya in log_dir.rglob("*.log"):
            dosya_adi = log_dosya.stem.upper()
            for bomba in bombalar:
                if bomba.upper() in dosya_adi or f"BOMBA_{bomba.upper()}" in dosya_adi:
                    if bomba not in bulunan_loglar:
                        bulunan_loglar[bomba] = []
                    bulunan_loglar[bomba].append({
                        "dosya": str(log_dosya),
                        "boyut": log_dosya.stat().st_size,
                        "son_degisiklik": datetime.fromtimestamp(
                            log_dosya.stat().st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    })

        # txt log dosyalari da olabilir
        for log_dosya in log_dir.rglob("*.txt"):
            dosya_adi = log_dosya.stem.upper()
            for bomba in bombalar:
                if bomba.upper() in dosya_adi:
                    if bomba not in bulunan_loglar:
                        bulunan_loglar[bomba] = []
                    bulunan_loglar[bomba].append({
                        "dosya": str(log_dosya),
                        "boyut": log_dosya.stat().st_size,
                        "son_degisiklik": datetime.fromtimestamp(
                            log_dosya.stat().st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                    })

    return bulunan_loglar


def iq_log_icerik_oku(log_dosyalari, son_satir=20):
    """Bulunan log dosyalarindan son satirlari oku."""
    icerikler = {}
    for bomba, dosya_listesi in log_dosyalari.items():
        icerikler[bomba] = []
        for dosya_bilgi in dosya_listesi:
            try:
                with open(dosya_bilgi["dosya"], encoding="utf-8", errors="ignore") as f:
                    satirlar = f.readlines()
                    son = satirlar[-son_satir:] if len(satirlar) > son_satir else satirlar
                    icerikler[bomba].append({
                        "dosya": dosya_bilgi["dosya"],
                        "son_satirlar": [s.strip() for s in son if s.strip()],
                    })
            except Exception as e:
                icerikler[bomba].append({
                    "dosya": dosya_bilgi["dosya"],
                    "hata": str(e),
                })
    return icerikler


def iq_api_durum_sorgula():
    """AnkaAPI uzerinden IQ'dan canli durum al."""
    try:
        from anka_api import AnkaAPI
        api = AnkaAPI()
        return api.bomba_robot_log_topla(data_dir=str(DATA_DIR))
    except Exception as e:
        return {"hata": str(e), "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}


def status_dosyasi_yaz(bombalar, iq_loglar, log_icerikleri, api_sonuc):
    """Birlesik durum dosyasini data/bomba_robot_status.json'a yaz."""
    status = {
        "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "aktif_bombalar": bombalar,
        "robot_sayisi": len(bombalar),
        "robotlar": {},
        "iq_api_durum": api_sonuc,
    }

    for bomba in bombalar:
        robot_durum = {
            "sembol": bomba,
            "iq_log_bulundu": bomba in iq_loglar,
            "log_dosyalari": iq_loglar.get(bomba, []),
            "son_log_satirlari": [],
            "durum": "BILINMIYOR",
        }

        # Log iceriklerinden durum cikar
        if bomba in log_icerikleri:
            for icerik in log_icerikleri[bomba]:
                if "son_satirlar" in icerik:
                    robot_durum["son_log_satirlari"] = icerik["son_satirlar"][-5:]
                    # Son satirlardan sinyal/trade bilgisi cikar
                    for satir in icerik.get("son_satirlar", []):
                        satir_lower = satir.lower()
                        if any(k in satir_lower for k in ["alis", "buy", "long"]):
                            robot_durum["durum"] = "ALIS_SINYALI"
                        elif any(k in satir_lower for k in ["satis", "sell", "short"]):
                            robot_durum["durum"] = "SATIS_SINYALI"
                        elif any(k in satir_lower for k in ["error", "hata", "exception"]):
                            robot_durum["durum"] = "HATA"
                        elif any(k in satir_lower for k in ["running", "aktif", "calisiyor"]):
                            robot_durum["durum"] = "AKTIF"

        # API sonucundan pozisyon bilgisi ekle
        if isinstance(api_sonuc, dict) and "detay" in api_sonuc:
            detay = api_sonuc["detay"]
            for poz in detay.get("pozisyonlar", []):
                if poz.get("symbol", "").replace(".E", "") == bomba:
                    robot_durum["pozisyon"] = poz
                    robot_durum["durum"] = "POZISYONDA"

        status["robotlar"][bomba] = robot_durum

    # Dosyaya yaz
    try:
        with open(STATUS_DOSYA, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        print(f"[OK] Status yazildi: {STATUS_DOSYA}")
    except Exception as e:
        print(f"[HATA] Status yazma hatasi: {e}")

    return status


def tek_calisma():
    """Tek seferlik log toplama ve status yazma."""
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{zaman}] Bomba Robot Log Bridge baslatildi")
    print(f"{'='*60}")

    # 1. Aktif bombalari oku
    bombalar = aktif_bombalari_oku()
    print(f"[INFO] Aktif bombalar ({len(bombalar)}): {', '.join(bombalar)}")

    if not bombalar:
        print("[WARN] Aktif bomba yok, cikiliyor")
        return

    # 2. IQ log dizinlerini tara
    print("[INFO] MatriksIQ log dizinleri taraniyor...")
    iq_loglar = iq_log_dizinlerini_tara(bombalar)
    bulunan = sum(len(v) for v in iq_loglar.values())
    print(f"[INFO] {bulunan} log dosyasi bulundu ({len(iq_loglar)} bomba icin)")

    # 3. Log iceriklerini oku
    log_icerikleri = iq_log_icerik_oku(iq_loglar)

    # 4. IQ API uzerinden canli durum
    print("[INFO] IQ API uzerinden durum sorgulanyor...")
    api_sonuc = iq_api_durum_sorgula()
    if isinstance(api_sonuc, dict) and "hata" not in api_sonuc:
        print(f"[OK] API sonucu: {api_sonuc.get('mesaj', 'OK')}")
    else:
        hata = api_sonuc.get("hata", "Bilinmiyor") if isinstance(api_sonuc, dict) else str(api_sonuc)
        print(f"[WARN] API hatasi: {hata}")

    # 5. Birlesik status dosyasi yaz
    status = status_dosyasi_yaz(bombalar, iq_loglar, log_icerikleri, api_sonuc)

    # Ozet
    print(f"\n[OZET] {len(bombalar)} bomba | "
          f"{bulunan} IQ log | "
          f"API: {'OK' if isinstance(api_sonuc, dict) and 'hata' not in api_sonuc else 'HATA'}")
    for bomba, bilgi in status.get("robotlar", {}).items():
        print(f"  {bomba}: {bilgi['durum']} | "
              f"IQ Log: {'EVET' if bilgi['iq_log_bulundu'] else 'HAYIR'}")

    return status


def surekli_calisma(aralik_dk=5):
    """Belirli araliklarla surekli log toplama."""
    print(f"[INFO] Surekli mod baslatildi ({aralik_dk}dk aralikla)")
    while True:
        try:
            tek_calisma()
        except Exception as e:
            print(f"[HATA] Dongu hatasi: {e}")
        print(f"\n[INFO] {aralik_dk}dk bekleniyor...")
        time.sleep(aralik_dk * 60)


if __name__ == "__main__":
    if "--surekli" in sys.argv:
        aralik = 5
        for i, arg in enumerate(sys.argv):
            if arg == "--aralik" and i + 1 < len(sys.argv):
                aralik = int(sys.argv[i + 1])
        surekli_calisma(aralik)
    else:
        tek_calisma()
