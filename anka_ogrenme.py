"""
ANKA ÖĞRENME — Ajan Performans Takibi & Otomatik Ağırlık Ayarlama
=================================================================
Her işlem sonrası:
  - Hangi ajan "AL" dedi?
  - Sonuç ne oldu? (kâr/zarar)
  - Doğru çıkan ajanın ağırlığını artır
  - Yanlış çıkanın ağırlığını düşür

İleride: Reinforcement Learning ile tam otonom ağırlık optimizasyonu.
"""

import json
import os
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
ISLEM_LOG = DATA_DIR / "islem_gecmisi.json"
AJAN_SKOR = DATA_DIR / "ajan_skorlari.json"

# Başlangıç ağırlıkları
VARSAYILAN_AGIRLIKLAR = {
    "TEKNİK": 0.25,
    "MAKRO": 0.25,
    "HABER": 0.15,
    "KURUMSAL": 0.15,
    "MOMENTUM": 0.20,
}


def islem_logla(ticker, karar_detay, giris_fiyat):
    """Yeni işlem başladığında logla — hangi ajan ne dedi."""
    DATA_DIR.mkdir(exist_ok=True)

    log = _oku_log()
    log.append({
        "id": len(log),
        "ticker": ticker,
        "tarih": datetime.now().isoformat(),
        "giris_fiyat": giris_fiyat,
        "cikis_fiyat": None,
        "kar_zarar_pct": None,
        "ajan_kararlari": karar_detay,  # {"TEKNİK": "AL", "MAKRO": "BEKLE", ...}
        "rejim": karar_detay.get("_rejim", "?"),
        "durum": "ACIK",
    })

    with open(ISLEM_LOG, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    return log[-1]["id"]


def islem_kapat(islem_id, cikis_fiyat):
    """İşlem kapandığında sonucu kaydet ve ajan skorlarını güncelle."""
    log = _oku_log()

    for islem in log:
        if islem["id"] == islem_id and islem["durum"] == "ACIK":
            islem["cikis_fiyat"] = cikis_fiyat
            islem["kar_zarar_pct"] = round(
                (cikis_fiyat - islem["giris_fiyat"]) / islem["giris_fiyat"] * 100, 2
            )
            islem["durum"] = "KAPANDI"
            islem["kapanis_tarihi"] = datetime.now().isoformat()

            # Ajan skorlarını güncelle
            _ajan_skor_guncelle(islem)

            with open(ISLEM_LOG, "w") as f:
                json.dump(log, f, indent=2, ensure_ascii=False)

            return islem

    return None


def _ajan_skor_guncelle(islem):
    """
    ÖDÜL/CEZA SİSTEMİ:
    - Ajan "AL" dedi ve kâr oldu → +1 puan
    - Ajan "AL" dedi ve zarar oldu → -1 puan
    - Ajan "BEKLE/SAT" dedi ve zarar oldu → +0.5 puan (doğru uyarı)
    - Ajan "BEKLE/SAT" dedi ve kâr oldu → -0.5 puan (fırsatı kaçırdı)
    """
    skorlar = _oku_skorlar()
    kar = islem.get("kar_zarar_pct", 0)
    karli = kar > 0

    for ajan, karar in islem.get("ajan_kararlari", {}).items():
        if ajan.startswith("_"):
            continue  # _rejim gibi meta alanları atla

        if ajan not in skorlar:
            skorlar[ajan] = {"dogru": 0, "yanlis": 0, "toplam": 0, "guven": 50}

        if karar == "AL":
            if karli:
                skorlar[ajan]["dogru"] += 1
            else:
                skorlar[ajan]["yanlis"] += 1
        elif karar in ("SAT", "BEKLE"):
            if not karli:
                skorlar[ajan]["dogru"] += 0.5  # Doğru uyardı
            else:
                skorlar[ajan]["yanlis"] += 0.5  # Fırsatı kaçırdı

        skorlar[ajan]["toplam"] += 1

        # Güven skoru güncelle (0-100)
        d = skorlar[ajan]["dogru"]
        y = skorlar[ajan]["yanlis"]
        toplam = d + y
        if toplam > 0:
            skorlar[ajan]["guven"] = round(d / toplam * 100, 1)

    with open(AJAN_SKOR, "w") as f:
        json.dump(skorlar, f, indent=2, ensure_ascii=False)


def dinamik_agirlik_hesapla():
    """
    Ajan güven skorlarına göre dinamik ağırlık hesapla.
    Güveni yüksek ajanın ağırlığı artar, düşük olanın azalır.
    Minimum 10 işlem sonrası aktif olur.
    """
    skorlar = _oku_skorlar()

    # Yeterli veri yoksa varsayılan ağırlıkları kullan
    min_islem = min(s.get("toplam", 0) for s in skorlar.values()) if skorlar else 0
    if min_islem < 10:
        return VARSAYILAN_AGIRLIKLAR.copy(), False

    # Güven skorlarına göre ağırlık
    toplam_guven = sum(s["guven"] for s in skorlar.values())
    if toplam_guven == 0:
        return VARSAYILAN_AGIRLIKLAR.copy(), False

    agirliklar = {}
    for ajan, skor in skorlar.items():
        agirliklar[ajan] = round(skor["guven"] / toplam_guven, 3)

    # Minimum %5, maximum %50 sınırı
    for ajan in agirliklar:
        agirliklar[ajan] = max(0.05, min(0.50, agirliklar[ajan]))

    # Normalize et (toplam = 1.0)
    toplam = sum(agirliklar.values())
    for ajan in agirliklar:
        agirliklar[ajan] = round(agirliklar[ajan] / toplam, 3)

    return agirliklar, True


def ajan_rapor():
    """Ajan performans raporu."""
    skorlar = _oku_skorlar()
    log = _oku_log()

    kapanan = [i for i in log if i["durum"] == "KAPANDI"]
    karli = [i for i in kapanan if i.get("kar_zarar_pct", 0) > 0]

    print("\n📊 ANKA ÖĞRENME RAPORU")
    print("=" * 50)
    print(f"Toplam işlem: {len(kapanan)} | Kârlı: {len(karli)} | Başarı: {len(karli)/max(1,len(kapanan))*100:.0f}%")

    if kapanan:
        ort_kar = sum(i["kar_zarar_pct"] for i in kapanan) / len(kapanan)
        print(f"Ortalama K/Z: %{ort_kar:.2f}")

    print(f"\n{'Ajan':<12} {'Doğru':>7} {'Yanlış':>7} {'Güven':>7} {'Ağırlık':>8}")
    print("-" * 45)

    agirliklar, ogrendi = dinamik_agirlik_hesapla()

    for ajan in ["TEKNİK", "MAKRO", "HABER", "KURUMSAL", "MOMENTUM"]:
        s = skorlar.get(ajan, {"dogru": 0, "yanlis": 0, "guven": 50})
        a = agirliklar.get(ajan, 0.20)
        print(f"{ajan:<12} {s['dogru']:>7.1f} {s['yanlis']:>7.1f} {s['guven']:>6.1f}% {a:>7.1%}")

    if ogrendi:
        print("\n🧠 AI ağırlıkları öğrenilmiş veriden hesaplandı")
    else:
        print("\n⏳ Henüz yeterli veri yok — varsayılan ağırlıklar kullanılıyor (min 10 işlem)")


def _oku_log():
    if ISLEM_LOG.exists():
        try:
            with open(ISLEM_LOG) as f:
                return json.load(f)
        except:
            pass
    return []


def _oku_skorlar():
    if AJAN_SKOR.exists():
        try:
            with open(AJAN_SKOR) as f:
                return json.load(f)
        except:
            pass
    return {}


if __name__ == "__main__":
    ajan_rapor()
