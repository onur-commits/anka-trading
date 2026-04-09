"""
ANKA ORKESTRA — Ana Motor
==========================
Tum modulleri tek dongu altinda yonetir:
- Beyin (rejim tespiti)
- Rotasyon (hisse degistirme)
- Muhendis (bakim)
- Bomba tarama
- Config okuma
- Ogrenme dongusu

Kullanim:
  python anka_orkestra.py           # Ana dongu (7/24)
  python anka_orkestra.py --durum   # Anlık durum
"""

import sys
import json
import time
import traceback
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "anka_config.json"
ORKESTRA_LOG = DATA_DIR / "orkestra_log.json"

sys.path.insert(0, str(BASE_DIR))


def log(mesaj, seviye="INFO"):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{zaman}] [{seviye}] {mesaj}")
    try:
        logs = []
        if ORKESTRA_LOG.exists():
            with open(ORKESTRA_LOG, encoding="utf-8") as f:
                logs = json.load(f)
        logs.append({"zaman": zaman, "seviye": seviye, "mesaj": mesaj})
        logs = logs[-500:]
        with open(ORKESTRA_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def config_oku():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def borsa_acik_mi(cfg):
    saat = datetime.now().hour
    dakika = datetime.now().minute
    baslangic = cfg.get("genel", {}).get("borsa_baslangic", "10:00")
    bitis = cfg.get("genel", {}).get("borsa_bitis", "18:00")
    bas_s, bas_d = map(int, baslangic.split(":"))
    bit_s, bit_d = map(int, bitis.split(":"))
    simdi = saat * 60 + dakika
    return bas_s * 60 + bas_d <= simdi <= bit_s * 60 + bit_d


def hafta_ici_mi():
    return datetime.now().weekday() < 5


def calistir_beyin(cfg):
    """Beyin analizi calistir."""
    if not cfg.get("rejim_motor", {}).get("aktif", True):
        return None
    try:
        from anka_beyin import tam_analiz
        return tam_analiz()
    except Exception as e:
        log(f"Beyin hatasi: {e}", "ERROR")
        return None


def calistir_rotasyon(cfg, beyin_state):
    """Rotasyon kontrolu calistir."""
    if not cfg.get("rotasyon", {}).get("aktif", True):
        return
    try:
        from anka_rotasyon import rotasyon_kontrol, state_yukle
        state = state_yukle()
        rotasyon_kontrol(state)
    except Exception as e:
        log(f"Rotasyon hatasi: {e}", "ERROR")


def calistir_muhendis(cfg):
    """Muhendis hizli kontrol."""
    if not cfg.get("muhendis", {}).get("aktif", True):
        return
    try:
        from anka_muhendis import hizli_kontrol
        hizli_kontrol()
    except Exception as e:
        log(f"Muhendis hatasi: {e}", "ERROR")


def calistir_bomba_tarama(cfg):
    """Sabah bomba taramasi (gunluk 1 kere)."""
    try:
        bomba_file = DATA_DIR / "gunluk_bomba.json"
        if bomba_file.exists():
            with open(bomba_file, encoding="utf-8") as f:
                data = json.load(f)
            tarih = data.get("tarih", "")
            if tarih.startswith(datetime.now().strftime("%Y-%m-%d")):
                return  # Bugun zaten tarandi
        log("Sabah bomba taramasi basliyor...", "INFO")
        import subprocess
        subprocess.run(
            [sys.executable, "-X", "utf8", str(BASE_DIR / "gunluk_bomba.py"), "--sadece-tara"],
            timeout=300, capture_output=True,
        )
        log("Bomba taramasi tamamlandi", "INFO")
    except Exception as e:
        log(f"Bomba tarama hatasi: {e}", "ERROR")


def gun_sonu_ogrenme(cfg):
    """Gun sonu ogrenme analizi."""
    if not cfg.get("ogrenme", {}).get("aktif", True):
        return
    try:
        from anka_beyin import hafiza_yukle, gun_sonu_analiz
        hafiza = hafiza_yukle()
        rapor = gun_sonu_analiz(hafiza)
        if rapor.get("islem_sayisi", 0) > 0:
            log(f"Gun sonu: {rapor['kazanc']} kazanc, {rapor['kayip']} kayip, net %{rapor['toplam_kar']}", "INFO")
            for ders in rapor.get("dersler", [])[:3]:
                log(f"  DERS: {ders[:100]}", "INFO")
    except Exception as e:
        log(f"Ogrenme hatasi: {e}", "ERROR")


def ana_dongu():
    log("=" * 60)
    log("ANKA ORKESTRA BASLATILDI")
    log("=" * 60)

    cfg = config_oku()
    aralik = cfg.get("rejim_motor", {}).get("kontrol_aralik_dk", 30)
    log(f"  Config yuklendi")
    log(f"  Kontrol aralik: {aralik} dk")
    log(f"  Max pozisyon: {cfg.get('genel', {}).get('max_pozisyon_sayisi', 5)}")
    log(f"  Strateji sayisi: {sum(1 for s in cfg.get('strateji_havuzu', {}).values() if s.get('aktif'))}")

    son_bomba = None
    son_gun_sonu = None

    while True:
        try:
            cfg = config_oku()  # Her dongude config taze oku
            simdi = datetime.now()
            saat = simdi.hour

            log("-" * 40)
            log(f"DONGU: {simdi.strftime('%H:%M')}")

            # 1. Muhendis her zaman calisir (7/24)
            log("[1/5] Muhendis kontrol...")
            calistir_muhendis(cfg)

            # 2. Borsa acik ve hafta ici mi?
            if not hafta_ici_mi():
                log("Hafta sonu — borsa kapali, bekliyorum")
                time.sleep(aralik * 60)
                continue

            if not borsa_acik_mi(cfg):
                # Borsa kapali ama sabah taramasi ve gun sonu ogrenme yapilabilir
                if saat == 9 and son_bomba != simdi.date():
                    log("[OZEL] Sabah taramasi...")
                    calistir_bomba_tarama(cfg)
                    son_bomba = simdi.date()

                if saat == 18 and son_gun_sonu != simdi.date():
                    log("[OZEL] Gun sonu ogrenme...")
                    gun_sonu_ogrenme(cfg)
                    son_gun_sonu = simdi.date()

                log(f"Borsa kapali (saat {saat}), bekliyorum")
                time.sleep(aralik * 60)
                continue

            # 3. Beyin analizi
            log("[2/5] Beyin analizi...")
            beyin = calistir_beyin(cfg)
            if beyin:
                rejim = beyin.get("rejim", {})
                log(f"  Rejim: {rejim.get('rejim', '?')} | Strateji: {rejim.get('strateji', '?')} | Agresiflik: {rejim.get('agresiflik', 0):.0%}")

                # Kill switch kontrolu
                ks = beyin.get("kill_switch", {})
                if ks.get("dur"):
                    log(f"  KILL SWITCH: {ks['sebep']} — islem yapilmiyor!", "WARNING")
                    time.sleep(aralik * 60)
                    continue

            # 4. Rotasyon (hisse degistirme)
            log("[3/5] Rotasyon kontrol...")
            calistir_rotasyon(cfg, beyin)

            # 5. Bomba tarama (gunluk 1 kere sabah)
            if saat <= 10 and son_bomba != simdi.date():
                log("[4/5] Sabah bomba taramasi...")
                calistir_bomba_tarama(cfg)
                son_bomba = simdi.date()
            else:
                log("[4/5] Bomba tarama: bugun yapildi")

            # 6. Durum ozeti
            log("[5/5] Durum ozeti:")
            try:
                rot = json.load(open(DATA_DIR / "rotasyon_state.json", encoding="utf-8"))
                poz_sayisi = len(rot.get("pozisyonlar", {}))
                for t, p in rot.get("pozisyonlar", {}).items():
                    log(f"  {t:8} {p.get('adet', 0)} lot @ {p.get('giris_fiyat', 0)} TL")
                log(f"  Toplam: {poz_sayisi}/5 pozisyon")
            except Exception:
                log("  Rotasyon state okunamadi")

            log(f"Sonraki kontrol: {aralik} dk sonra")
            time.sleep(aralik * 60)

        except KeyboardInterrupt:
            log("Orkestra durduruldu (Ctrl+C)")
            break
        except Exception as e:
            log(f"ORKESTRA HATA: {e}", "ERROR")
            traceback.print_exc()
            time.sleep(60)


def durum_goster():
    cfg = config_oku()
    print("\n=== ANKA ORKESTRA DURUMU ===")
    print(f"Borsa acik: {borsa_acik_mi(cfg) and hafta_ici_mi()}")
    print(f"Config: {len(cfg)} bolum")

    # Beyin
    beyin_file = DATA_DIR / "beyin_state.json"
    if beyin_file.exists():
        beyin = json.load(open(beyin_file, encoding="utf-8"))
        r = beyin.get("rejim", {})
        print(f"Rejim: {r.get('rejim', '?')} | Strateji: {r.get('strateji', '?')} | Agresiflik: {r.get('agresiflik', 0):.0%}")
    else:
        print("Beyin: henuz analiz yapilmadi")

    # Pozisyonlar
    rot_file = DATA_DIR / "rotasyon_state.json"
    if rot_file.exists():
        rot = json.load(open(rot_file, encoding="utf-8"))
        pozlar = rot.get("pozisyonlar", {})
        print(f"Pozisyon: {len(pozlar)}/5")
        for t, p in pozlar.items():
            print(f"  {t:8} {p.get('adet', 0)} lot @ {p.get('giris_fiyat', 0)} TL")

    # Bildirimler
    bildirim_file = DATA_DIR / "acil_bildirim.json"
    if bildirim_file.exists():
        bild = json.load(open(bildirim_file, encoding="utf-8"))
        okunmamis = [b for b in bild if not b.get("okundu")]
        if okunmamis:
            print(f"\n!!! {len(okunmamis)} OKUNMAMIS BILDIRIM:")
            for b in okunmamis[-3:]:
                print(f"  [{b['zaman']}] {b['mesaj']}")


if __name__ == "__main__":
    if "--durum" in sys.argv:
        durum_goster()
    else:
        ana_dongu()
