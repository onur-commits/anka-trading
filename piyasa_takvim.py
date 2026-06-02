"""
BIST Piyasa Takvimi — Hafta sonu ve resmi tatil kontrolü
=========================================================
BIST botları bu modülü kullanarak piyasa kapalı günlerde
gereksiz tarama/işlem yapmaz.

Kullanım:
  from piyasa_takvim import bist_acik_mi, sadece_bist_acikken

  acik, sebep = bist_acik_mi()
  if not acik:
      print(f"Piyasa kapalı: {sebep}")
      return

  # veya schedule job'ı için:
  @sadece_bist_acikken
  def gorev_09_05_alis():
      ...
"""

from datetime import date, datetime, time as dtime
from functools import wraps

# BIST seans saatleri (yerel TR saati)
# Surekli isleme: 10:00-18:00 (acilis muzayedesi 09:55-10:00, kapanis muzayedesi 18:00-18:05)
BIST_SEANS_BASLA = dtime(10, 0)
BIST_SEANS_BIT   = dtime(18, 5)

# BIST resmi tatil günleri (yıllık güncellenmeli)
# Sabit tarihler + dini bayramlar (yaklaşık — yıl başında doğrulayın)
BIST_TATIL_GUNLERI = {
    # 2026
    "2026-01-01": "Yılbaşı",
    "2026-03-19": "Ramazan Bayramı arifesi (yarım gün)",
    "2026-03-20": "Ramazan Bayramı 1. gün",
    "2026-03-21": "Ramazan Bayramı 2. gün",
    "2026-03-22": "Ramazan Bayramı 3. gün",
    "2026-04-23": "Ulusal Egemenlik ve Çocuk Bayramı",
    "2026-05-01": "Emek ve Dayanışma Günü",
    "2026-05-19": "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
    "2026-05-26": "Kurban Bayramı arifesi (yarım gün)",
    "2026-05-27": "Kurban Bayramı 1. gün",
    "2026-05-28": "Kurban Bayramı 2. gün",
    "2026-05-29": "Kurban Bayramı 3. gün",
    "2026-05-30": "Kurban Bayramı 4. gün",
    "2026-07-15": "Demokrasi ve Milli Birlik Günü",
    "2026-08-30": "Zafer Bayramı",
    "2026-10-28": "Cumhuriyet Bayramı arifesi (yarım gün)",
    "2026-10-29": "Cumhuriyet Bayramı",
    # 2027 — güncellenecek
    "2027-01-01": "Yılbaşı",
}


def bist_acik_mi(tarih=None):
    """
    BIST o tarihte açık mı kontrol eder.

    Args:
        tarih: datetime.date veya None (bugün)

    Returns:
        (acik: bool, sebep: str)
        acik=True ise sebep="Piyasa açık"
        acik=False ise sebep kapalı olma nedeni
    """
    if tarih is None:
        tarih = date.today()
    elif isinstance(tarih, datetime):
        tarih = tarih.date()

    # Hafta sonu kontrolü
    hafta_gunu = tarih.weekday()  # 0=Pzt, 5=Cmt, 6=Pzr
    if hafta_gunu == 5:
        return False, "Cumartesi — hafta sonu"
    if hafta_gunu == 6:
        return False, "Pazar — hafta sonu"

    # Resmi tatil kontrolü
    iso = tarih.isoformat()
    if iso in BIST_TATIL_GUNLERI:
        return False, f"Resmi tatil: {BIST_TATIL_GUNLERI[iso]}"

    return True, "Piyasa açık"


def bist_seans_acik_mi(an=None):
    """
    BIST seans saati AKTIF mi (tarih + saat kontrolu).
    bist_acik_mi yalnizca gunluk kontrol yapar — bu fonksiyon ayrica
    seans saatlerini de dogrular (varsayilan 10:00-18:05 TR saati).

    Args:
        an: datetime veya None (su an)

    Returns:
        (acik: bool, sebep: str)
    """
    if an is None:
        an = datetime.now()
    elif isinstance(an, date) and not isinstance(an, datetime):
        an = datetime.combine(an, dtime(12, 0))

    acik, sebep = bist_acik_mi(an)
    if not acik:
        return False, sebep

    saat = an.time()
    if saat < BIST_SEANS_BASLA:
        return False, f"Seans henuz acilmadi (acilis {BIST_SEANS_BASLA.strftime('%H:%M')})"
    if saat > BIST_SEANS_BIT:
        return False, f"Seans kapandi (kapanis {BIST_SEANS_BIT.strftime('%H:%M')})"
    return True, "Seans acik"


def sadece_bist_acikken(fn):
    """
    Schedule job decorator — BIST kapalıysa job'u atlar.

    Kullanım:
        @sadece_bist_acikken
        def gorev():
            ...
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        acik, sebep = bist_acik_mi()
        if not acik:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏸️  {fn.__name__} atlandı — {sebep}")
            return None
        return fn(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        t = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        t = date.today()

    acik, sebep = bist_acik_mi(t)
    print(f"{t} ({t.strftime('%A')}): {'🟢 AÇIK' if acik else '🔴 KAPALI'} — {sebep}")
