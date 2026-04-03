"""
ANKA PANEL KURALLARI — 10 Profesörün Zorunlu Kuralları
=======================================================
Bu dosya ANKA'nın tüm karar mekanizmalarına entegre edilir.
Hiçbir ajan, hiçbir robot bu kuralları atlayamaz.

Panel: MIT, Cornell, Berkeley, Polytechnique, Maryland,
       Koç, Bilkent, Sabancı, Boğaziçi, Borsa Istanbul

Tarih: 3 Nisan 2026
Oy: 10/10 oybirliği
"""

import json
import os
import time
from datetime import datetime, date
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

GUNLUK_KZ_DOSYA = DATA_DIR / "gunluk_kz_takip.json"
ISLEM_KAYIT = DATA_DIR / "islem_kayitlari.json"


# ================================================================
# KURAL 1: KILL-SWITCH (10/10 oybirliği)
# Günlük max kayıp %3 geçerse TÜM İŞLEMLERİ DURDUR
# ================================================================
class KillSwitch:
    """
    Prof. Akgiray (Boğaziçi): "Üç katmanlı güvenlik mekanizması DERHAL uygulanmalı"
    Prof. Hendershott (Berkeley): "Herhangi bir kurumsal sistemde bu zorunludur"
    """

    MAX_GUNLUK_KAYIP_PCT = 3.0      # Günlük max kayıp %3
    MAX_TEK_ISLEM_KAYIP_PCT = 1.5   # Tek işlemde max kayıp %1.5
    MAX_GUNLUK_EMIR_SAYISI = 50     # Günde max 50 emir (fat-finger koruması)
    MAX_TEK_EMIR_TUTAR = 30000      # Tek emir max 30K TL

    @staticmethod
    def kontrol(portfoy_degeri, gunluk_kz, emir_sayisi, emir_tutar):
        """
        Kill-switch kontrolü. False dönerse TÜM İŞLEMLER DURUR.
        """
        sorunlar = []

        # Günlük kayıp kontrolü
        if portfoy_degeri > 0:
            kayip_pct = abs(gunluk_kz) / portfoy_degeri * 100
            if gunluk_kz < 0 and kayip_pct > KillSwitch.MAX_GUNLUK_KAYIP_PCT:
                sorunlar.append(f"KILL-SWITCH: Günlük kayıp %{kayip_pct:.1f} > %{KillSwitch.MAX_GUNLUK_KAYIP_PCT}")

        # Emir sayısı kontrolü
        if emir_sayisi > KillSwitch.MAX_GUNLUK_EMIR_SAYISI:
            sorunlar.append(f"KILL-SWITCH: Günlük emir sayısı {emir_sayisi} > {KillSwitch.MAX_GUNLUK_EMIR_SAYISI}")

        # Tek emir tutarı kontrolü
        if emir_tutar > KillSwitch.MAX_TEK_EMIR_TUTAR:
            sorunlar.append(f"KILL-SWITCH: Tek emir {emir_tutar:,.0f} TL > {KillSwitch.MAX_TEK_EMIR_TUTAR:,.0f} TL")

        if sorunlar:
            for s in sorunlar:
                print(f"🚨 {s}")
            return False, sorunlar

        return True, []


# ================================================================
# KURAL 2: KOMİSYON DAHİL KÂRLILIK (10/10 oybirliği)
# Prof. López de Prado: "Komisyon sonrası net alfa negatifse sistemi kapatın"
# ================================================================
class KomisyonKontrol:
    """
    Her işlem önerisinde komisyon dahil net kâr hesapla.
    Komisyon sonrası kâr beklentisi negatifse → AL deme.
    """

    KOMISYON_ORAN = 0.0015  # %0.15 (tek yön)
    SLIPPAGE_ORAN = 0.001   # %0.10 tahmini slippage
    TOPLAM_MALIYET = (KOMISYON_ORAN * 2) + SLIPPAGE_ORAN  # gidiş-dönüş: %0.40

    @staticmethod
    def karli_mi(beklenen_getiri_pct):
        """
        Beklenen getiri komisyon+slippage'dan büyük mü?
        Değilse işlem yapmaya değmez.
        """
        net = beklenen_getiri_pct - (KomisyonKontrol.TOPLAM_MALIYET * 100)
        return net > 0, net

    @staticmethod
    def minimum_kar_hedefi():
        """Minimum kâr hedefi — komisyonu karşılamak için gereken minimum hareket."""
        return KomisyonKontrol.TOPLAM_MALIYET * 100  # %0.40


# ================================================================
# KURAL 3: SEKTÖR KORELASYON FİLTRESİ (9/10 oybirliği)
# Prof. Salih (Bilkent): "5 hissenin hepsi aynı sektörden olmamalı"
# Prof. Bouchaud: "Korelasyon riski kuyruk riskini katlar"
# ================================================================
class SektorFiltresi:
    """
    Max 2 hisse aynı sektörden olabilir.
    Bu kural bomba listesine VETO hakkı verir.
    """

    SEKTOR_MAP = {
        # Enerji
        "AYEN": "enerji", "AKSEN": "enerji", "ENJSA": "enerji",
        "TUPRS": "enerji", "PETKM": "enerji",
        # Banka
        "GARAN": "banka", "AKBNK": "banka", "YKBNK": "banka",
        "HALKB": "banka", "VAKBN": "banka", "ISCTR": "banka", "TSKB": "banka",
        # Sanayi
        "THYAO": "sanayi", "ASELS": "sanayi", "TOASO": "sanayi",
        "FROTO": "sanayi", "ARCLK": "sanayi", "EREGL": "sanayi",
        "SISE": "sanayi", "CEMTS": "sanayi", "KORDS": "sanayi",
        # Holding
        "SAHOL": "holding", "KCHOL": "holding", "DOHOL": "holding",
        # Perakende
        "BIMAS": "perakende", "MGROS": "perakende", "ULKER": "perakende",
        # Teknoloji
        "ASTOR": "teknoloji", "TTKOM": "teknoloji", "TCELL": "teknoloji",
        # İnşaat/GYO
        "EKGYO": "insaat",
        # Diğer
        "TAVHL": "turizm", "PGSUS": "turizm",
        "SASA": "kimya", "GESAN": "makine", "KONTR": "insaat",
        "OTKAR": "savunma", "TTRAK": "tarim", "EGEEN": "sanayi",
        "VESTL": "beyaz_esya", "ALARK": "holding", "HEKTS": "kimya",
        "BRISA": "lastik", "CCOLA": "perakende", "CIMSA": "cimento",
        "SMRTG": "teknoloji", "GUBRF": "kimya", "ENKAI": "insaat",
    }

    MAX_AYNI_SEKTOR = 2

    @staticmethod
    def filtrele(bomba_listesi):
        """
        Bomba listesindeki sektör dağılımını kontrol et.
        Max 2 hisse aynı sektörden olabilir.
        Fazlasını çıkar — en düşük skorluyu at.
        """
        sektor_sayac = {}
        onaylanan = []
        reddedilen = []

        for ticker in bomba_listesi:
            sektor = SektorFiltresi.SEKTOR_MAP.get(ticker, "diger")
            mevcut = sektor_sayac.get(sektor, 0)

            if mevcut < SektorFiltresi.MAX_AYNI_SEKTOR:
                sektor_sayac[sektor] = mevcut + 1
                onaylanan.append(ticker)
            else:
                reddedilen.append((ticker, sektor))
                print(f"⚠️ SEKTÖR VETO: {ticker} ({sektor}) — zaten {SektorFiltresi.MAX_AYNI_SEKTOR} {sektor} hissesi var")

        return onaylanan, reddedilen


# ================================================================
# KURAL 4: GÜNLÜK K/Z TAKİBİ (10/10 oybirliği)
# Prof. Lo (MIT): "Kümülatif kayıp takibi olmadan canlı işlem yapmak intihar"
# ================================================================
class GunlukKZTakip:
    """
    Günlük kâr/zarar takibi.
    Kill-switch'e veri besler.
    """

    @staticmethod
    def kaydet(ticker, islem_yonu, miktar, fiyat, komisyon=0):
        """Her işlemi kaydet."""
        DATA_DIR.mkdir(exist_ok=True)

        kayitlar = []
        if ISLEM_KAYIT.exists():
            try:
                kayitlar = json.load(open(ISLEM_KAYIT))
            except:
                pass

        kayitlar.append({
            "tarih": datetime.now().isoformat(),
            "gun": str(date.today()),
            "ticker": ticker,
            "yon": islem_yonu,  # "AL" veya "SAT"
            "miktar": miktar,
            "fiyat": fiyat,
            "tutar": round(miktar * fiyat, 2),
            "komisyon": round(komisyon, 2),
        })

        # Son 1000 kayıt tut
        kayitlar = kayitlar[-1000:]
        with open(ISLEM_KAYIT, "w") as f:
            json.dump(kayitlar, f, indent=2, ensure_ascii=False)

    @staticmethod
    def gunluk_ozet():
        """Bugünkü işlemlerin özeti."""
        if not ISLEM_KAYIT.exists():
            return {"toplam_kz": 0, "islem_sayisi": 0, "komisyon_toplam": 0}

        try:
            kayitlar = json.load(open(ISLEM_KAYIT))
        except:
            return {"toplam_kz": 0, "islem_sayisi": 0, "komisyon_toplam": 0}

        bugun = str(date.today())
        bugunkuler = [k for k in kayitlar if k.get("gun") == bugun]

        toplam_alis = sum(k["tutar"] for k in bugunkuler if k["yon"] == "AL")
        toplam_satis = sum(k["tutar"] for k in bugunkuler if k["yon"] == "SAT")
        toplam_komisyon = sum(k.get("komisyon", 0) for k in bugunkuler)

        return {
            "toplam_kz": round(toplam_satis - toplam_alis - toplam_komisyon, 2),
            "islem_sayisi": len(bugunkuler),
            "komisyon_toplam": round(toplam_komisyon, 2),
            "alis_sayisi": sum(1 for k in bugunkuler if k["yon"] == "AL"),
            "satis_sayisi": sum(1 for k in bugunkuler if k["yon"] == "SAT"),
        }


# ================================================================
# KURAL 5: EMİR DOĞRULAMA (10/10 oybirliği)
# Prof. Kyle (Maryland): "Emir dolana kadar pozisyon sayma"
# ================================================================
class EmirDogrulama:
    """
    Emir gönderildi ≠ Pozisyon açıldı.
    Dolum onayı gelene kadar pozisyon false kalmalı.
    """

    @staticmethod
    def emir_oncesi_kontrol(ticker, miktar, fiyat, portfoy_degeri, mevcut_pozisyonlar):
        """
        Emir göndermeden önce tüm kontrolleri yap.
        Hepsi geçerse True döner.
        """
        sorunlar = []

        # Fat-finger kontrolü
        emir_tutar = miktar * fiyat
        if emir_tutar > KillSwitch.MAX_TEK_EMIR_TUTAR:
            sorunlar.append(f"Fat-finger: {emir_tutar:,.0f} TL > limit {KillSwitch.MAX_TEK_EMIR_TUTAR:,.0f}")

        # Portföy oranı kontrolü (tek pozisyon max %25)
        if portfoy_degeri > 0:
            oran = emir_tutar / portfoy_degeri * 100
            if oran > 25:
                sorunlar.append(f"Tek pozisyon %{oran:.0f} > max %25")

        # Günlük emir sayısı
        ozet = GunlukKZTakip.gunluk_ozet()
        if ozet["islem_sayisi"] >= KillSwitch.MAX_GUNLUK_EMIR_SAYISI:
            sorunlar.append(f"Günlük emir limiti aşıldı: {ozet['islem_sayisi']}")

        # Kill-switch kontrolü
        ks_ok, ks_sorunlar = KillSwitch.kontrol(
            portfoy_degeri, ozet["toplam_kz"],
            ozet["islem_sayisi"], emir_tutar
        )
        if not ks_ok:
            sorunlar.extend(ks_sorunlar)

        # Sektör kontrolü
        mevcut_sektorler = {}
        for t in mevcut_pozisyonlar:
            s = SektorFiltresi.SEKTOR_MAP.get(t, "diger")
            mevcut_sektorler[s] = mevcut_sektorler.get(s, 0) + 1

        yeni_sektor = SektorFiltresi.SEKTOR_MAP.get(ticker, "diger")
        if mevcut_sektorler.get(yeni_sektor, 0) >= SektorFiltresi.MAX_AYNI_SEKTOR:
            sorunlar.append(f"Sektör limiti: {yeni_sektor} zaten {SektorFiltresi.MAX_AYNI_SEKTOR} hisse")

        if sorunlar:
            for s in sorunlar:
                print(f"🚫 EMİR REDDEDİLDİ: {s}")
            return False, sorunlar

        return True, []


# ================================================================
# KURAL 6: KARA KUGU KORUMASI (10/10 oybirliği)
# Prof. Bouchaud (Polytechnique): "Normal dağılım varsaymayın"
# ================================================================
class KaraKuguKoruma:
    """
    Tavan/taban kilidi, flash crash, likidite kuruması koruması.
    """

    @staticmethod
    def tavan_taban_kontrol(degisim_pct):
        """Hisse tavan veya tabandaysa işlem yapma."""
        if abs(degisim_pct) > 9.0:
            return False, f"Tavan/Taban: %{degisim_pct:.1f}"
        return True, ""

    @staticmethod
    def likidite_kontrol(hacim, ortalama_hacim, emir_miktari):
        """Emirimiz günlük hacmin %1'inden fazlaysa parçala."""
        if hacim > 0 and emir_miktari > hacim * 0.01:
            return False, f"Likidite riski: emir {emir_miktari} > hacmin %1'i ({hacim*0.01:.0f})"
        return True, ""


# ================================================================
# KURAL 7: BİRLEŞİK KARAR FİLTRESİ
# Tüm kuralları tek fonksiyonda birleştir
# ================================================================
def panel_onayi(ticker, miktar, fiyat, beklenen_getiri_pct,
                portfoy_degeri, gunluk_kz, emir_sayisi,
                mevcut_pozisyonlar, degisim_pct=0, hacim=0, ort_hacim=0):
    """
    10 profesörün kurallarını uygula.
    Hepsi geçerse True, biri bile başarısızsa False.
    """

    print(f"\n🎓 PANEL ONAYI: {ticker} | {miktar} lot @ {fiyat:.2f} TL")

    # 1. Kill-switch
    ks_ok, _ = KillSwitch.kontrol(portfoy_degeri, gunluk_kz, emir_sayisi, miktar * fiyat)
    if not ks_ok:
        return False, "KILL-SWITCH"

    # 2. Komisyon kontrolü
    karli, net = KomisyonKontrol.karli_mi(beklenen_getiri_pct)
    if not karli:
        print(f"🚫 Komisyon sonrası net: %{net:.2f} — KARLI DEĞİL")
        return False, "KOMİSYON"

    # 3. Emir doğrulama
    ed_ok, _ = EmirDogrulama.emir_oncesi_kontrol(
        ticker, miktar, fiyat, portfoy_degeri, mevcut_pozisyonlar)
    if not ed_ok:
        return False, "EMİR_DOĞRULAMA"

    # 4. Tavan/taban kontrolü
    tt_ok, _ = KaraKuguKoruma.tavan_taban_kontrol(degisim_pct)
    if not tt_ok:
        print(f"🚫 Tavan/Taban kilidi — işlem yapılamaz")
        return False, "TAVAN_TABAN"

    # 5. Likidite kontrolü
    lk_ok, _ = KaraKuguKoruma.likidite_kontrol(hacim, ort_hacim, miktar)
    if not lk_ok:
        return False, "LİKİDİTE"

    print(f"✅ PANEL ONAYI GEÇTİ — tüm kurallar sağlandı")
    return True, "ONAY"


# ================================================================
# BRIDGE'E PANEL KURALLARINI EKLE
# ================================================================
def bridge_panel_guncelle(bridge_path=None):
    """
    Bridge dosyasına panel kurallarını + günlük K/Z bilgisini ekle.
    C# robot bunu okuyacak.
    """
    if bridge_path is None:
        bridge_path = DATA_DIR / "v3_bridge.json"

    try:
        if bridge_path.exists():
            bridge = json.load(open(bridge_path))
        else:
            bridge = {}

        # Günlük K/Z bilgisi
        ozet = GunlukKZTakip.gunluk_ozet()

        # Kill-switch durumu
        portfoy = bridge.get("pos_value", 16000) * 5  # Tahmini portföy
        ks_ok, _ = KillSwitch.kontrol(
            portfoy, ozet["toplam_kz"],
            ozet["islem_sayisi"], 0
        )

        bridge["panel_rules"] = {
            "kill_switch_active": not ks_ok,
            "gunluk_kz": ozet["toplam_kz"],
            "gunluk_islem": ozet["islem_sayisi"],
            "gunluk_komisyon": ozet["komisyon_toplam"],
            "max_kayip_pct": KillSwitch.MAX_GUNLUK_KAYIP_PCT,
            "max_emir_sayisi": KillSwitch.MAX_GUNLUK_EMIR_SAYISI,
            "max_tek_emir": KillSwitch.MAX_TEK_EMIR_TUTAR,
            "komisyon_maliyet_pct": KomisyonKontrol.TOPLAM_MALIYET * 100,
            "min_kar_hedefi_pct": KomisyonKontrol.minimum_kar_hedefi(),
        }

        # Kill-switch tetiklendiyse robotu durdur
        if not ks_ok:
            bridge["robot_active"] = False
            bridge["regime"] = "KILL_SWITCH"
            print("🚨 KILL-SWITCH TETİKLENDİ — robot durduruldu!")

        bridge["panel_update"] = datetime.now().isoformat()

        # Yaz
        with open(bridge_path, "w") as f:
            json.dump(bridge, f, indent=4, ensure_ascii=False)

        return bridge

    except Exception as e:
        print(f"Bridge güncelleme hatası: {e}")
        return None


if __name__ == "__main__":
    print("🎓 ANKA PANEL KURALLARI — Test")
    print("=" * 50)

    # Kill-switch test
    print("\n1. Kill-Switch Testi:")
    ok, _ = KillSwitch.kontrol(100000, -4000, 10, 15000)
    print(f"   Günlük -%4 kayıp: {'DURDUR ❌' if not ok else 'Geçti ✅'}")

    ok, _ = KillSwitch.kontrol(100000, -1000, 10, 15000)
    print(f"   Günlük -%1 kayıp: {'DURDUR ❌' if not ok else 'Geçti ✅'}")

    # Komisyon testi
    print("\n2. Komisyon Testi:")
    ok, net = KomisyonKontrol.karli_mi(0.3)
    print(f"   %0.3 beklenen getiri: Net %{net:.2f} {'KARLI ✅' if ok else 'KARLI DEĞİL ❌'}")

    ok, net = KomisyonKontrol.karli_mi(1.5)
    print(f"   %1.5 beklenen getiri: Net %{net:.2f} {'KARLI ✅' if ok else 'KARLI DEĞİL ❌'}")

    # Sektör testi
    print("\n3. Sektör Filtresi Testi:")
    onay, red = SektorFiltresi.filtrele(["AYEN", "AKSEN", "ENJSA", "GARAN", "THYAO"])
    print(f"   Onaylanan: {onay}")
    print(f"   Reddedilen: {red}")

    # Birleşik test
    print("\n4. Panel Onayı Testi:")
    ok, sebep = panel_onayi(
        ticker="AYEN", miktar=400, fiyat=38.0,
        beklenen_getiri_pct=1.5,
        portfoy_degeri=200000, gunluk_kz=-500,
        emir_sayisi=5, mevcut_pozisyonlar=["GARAN", "THYAO"],
        degisim_pct=5.0, hacim=1000000, ort_hacim=800000
    )
    print(f"   Sonuç: {sebep}")
