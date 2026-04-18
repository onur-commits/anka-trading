"""
🔍 DOĞRULUK KONTROL AI — Sistemin Bekçisi
============================================
Tek görevi: ANKA ve COIN'in doğru çalışıp çalışmadığını kontrol etmek.
Her sinyal sonrası "gerçekten doğru muydu?" sorusuna cevap verir.
Yanlış sinyalleri loglar, ajan güvenilirliğini günceller.

7/24 çalışır — hem BIST hem Kripto.
"""

import json
import os
import time
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SINYAL_LOG = DATA_DIR / "sinyal_dogruluk.json"
RAPOR_DOSYA = DATA_DIR / "dogruluk_raporu.json"


class DogrulukKontrol:
    """
    Her sinyal için:
    1. Sinyal zamanı + fiyatı kaydet
    2. N saat/gün sonra kontrol et
    3. Doğru mu yanlış mı → logla
    4. Ajan güvenilirliğini güncelle
    """

    def __init__(self):
        self.sinyaller = self._oku()

    def _oku(self):
        if SINYAL_LOG.exists():
            try:
                return json.load(open(SINYAL_LOG))
            except:
                pass
        return []

    def _kaydet(self):
        with open(SINYAL_LOG, "w") as f:
            json.dump(self.sinyaller[-500:], f, indent=2, ensure_ascii=False)

    # ── SİNYAL KAYDET ──────────────────────────────────
    def sinyal_kaydet(self, sistem, symbol, karar, skor, fiyat, ajanlar=None):
        """Yeni sinyal kaydet — sonra kontrol edilecek."""
        sinyal = {
            "id": len(self.sinyaller),
            "sistem": sistem,  # "ANKA" veya "COIN"
            "symbol": symbol,
            "karar": karar,  # "AL", "SAT", "BEKLE"
            "skor": skor,
            "fiyat": fiyat,
            "ajanlar": ajanlar or {},
            "zaman": datetime.now().isoformat(),
            "kontrol_edildi": False,
            "sonuc": None,
        }
        self.sinyaller.append(sinyal)
        self._kaydet()
        return sinyal["id"]

    # ── SİNYAL KONTROL ET ──────────────────────────────
    def kontrol_et(self, bekleme_saat=24):
        """
        Bekleyen sinyalleri kontrol et.
        N saat geçmiş mi? Geçmişse fiyatı çek, doğru mu bak.
        """
        simdi = datetime.now()
        kontrol_edilenler = 0
        dogrular = 0
        yanlislar = 0

        for sinyal in self.sinyaller:
            if sinyal["kontrol_edildi"]:
                continue

            sinyal_zamani = datetime.fromisoformat(sinyal["zaman"])
            gecen_saat = (simdi - sinyal_zamani).total_seconds() / 3600

            if gecen_saat < bekleme_saat:
                continue  # Henüz erken

            # Şu anki fiyatı çek
            symbol = sinyal["symbol"]
            sistem = sinyal["sistem"]

            try:
                if sistem == "COIN":
                    r = requests.get("https://api.binance.com/api/v3/ticker/price",
                                   params={"symbol": symbol}, timeout=5)
                    guncel_fiyat = float(r.json()["price"])
                else:  # ANKA
                    df = yf.download(f"{symbol}.IS", period="2d", progress=False)
                    guncel_fiyat = float(df['Close'].iloc[-1]) if len(df) > 0 else 0
            except:
                continue

            if guncel_fiyat == 0:
                continue

            giris_fiyat = sinyal["fiyat"]
            degisim = (guncel_fiyat / giris_fiyat - 1) * 100

            # DOĞRULUK DEĞERLENDİRME
            if sinyal["karar"] == "AL":
                dogru = degisim > 0  # AL dediyse ve yükseldiyse doğru
                kar_zarar = degisim
            elif sinyal["karar"] == "SAT":
                dogru = degisim < 0  # SAT dediyse ve düştüyse doğru
                kar_zarar = -degisim
            else:  # BEKLE
                dogru = abs(degisim) < 2  # BEKLE dediyse ve fazla oynamadıysa doğru
                kar_zarar = 0

            sinyal["kontrol_edildi"] = True
            sinyal["sonuc"] = {
                "guncel_fiyat": round(guncel_fiyat, 4),
                "degisim_pct": round(degisim, 2),
                "dogru": dogru,
                "kontrol_zamani": simdi.isoformat(),
                "gecen_saat": round(gecen_saat, 1),
            }

            kontrol_edilenler += 1
            if dogru:
                dogrular += 1
            else:
                yanlislar += 1

        self._kaydet()
        return kontrol_edilenler, dogrular, yanlislar

    # ── RAPOR ──────────────────────────────────────────
    def rapor(self):
        """Doğruluk raporu — sistem bazlı ve ajan bazlı."""
        kontrol_edilmis = [s for s in self.sinyaller if s["kontrol_edildi"]]

        if not kontrol_edilmis:
            print("📊 Henüz kontrol edilmiş sinyal yok")
            return

        print(f"\n🔍 DOĞRULUK RAPORU")
        print("=" * 60)
        print(f"Toplam sinyal: {len(self.sinyaller)}")
        print(f"Kontrol edilmiş: {len(kontrol_edilmis)}")

        # Sistem bazlı
        for sistem in ["ANKA", "COIN"]:
            sinyaller = [s for s in kontrol_edilmis if s["sistem"] == sistem]
            if not sinyaller:
                continue

            dogrular = [s for s in sinyaller if s["sonuc"]["dogru"]]
            ort_degisim = np.mean([s["sonuc"]["degisim_pct"] for s in sinyaller])

            print(f"\n{'🦅' if sistem == 'ANKA' else '🪙'} {sistem}:")
            print(f"   Sinyal: {len(sinyaller)} | Doğru: {len(dogrular)} | Başarı: %{len(dogrular)/len(sinyaller)*100:.0f}")
            print(f"   Ort değişim: %{ort_degisim:+.2f}")

            # Karar bazlı
            for karar in ["AL", "SAT", "BEKLE"]:
                k_sinyaller = [s for s in sinyaller if s["karar"] == karar]
                if k_sinyaller:
                    k_dogrular = [s for s in k_sinyaller if s["sonuc"]["dogru"]]
                    print(f"   {karar}: {len(k_sinyaller)} sinyal → %{len(k_dogrular)/len(k_sinyaller)*100:.0f} doğru")

        # En iyi ve en kötü sinyaller
        print(f"\n📊 EN İYİ 3 SİNYAL:")
        en_iyi = sorted(kontrol_edilmis, key=lambda x: x["sonuc"]["degisim_pct"], reverse=True)[:3]
        for s in en_iyi:
            print(f"   🟢 {s['symbol']} {s['karar']} @ {s['fiyat']:.2f} → %{s['sonuc']['degisim_pct']:+.1f}")

        print(f"\n📊 EN KÖTÜ 3 SİNYAL:")
        en_kotu = sorted(kontrol_edilmis, key=lambda x: x["sonuc"]["degisim_pct"])[:3]
        for s in en_kotu:
            print(f"   🔴 {s['symbol']} {s['karar']} @ {s['fiyat']:.2f} → %{s['sonuc']['degisim_pct']:+.1f}")

        # Rapor dosyasına kaydet
        rapor = {
            "zaman": datetime.now().isoformat(),
            "toplam_sinyal": len(self.sinyaller),
            "kontrol_edilmis": len(kontrol_edilmis),
            "basari_orani": round(len([s for s in kontrol_edilmis if s["sonuc"]["dogru"]]) / max(1, len(kontrol_edilmis)) * 100, 1),
        }
        with open(RAPOR_DOSYA, "w") as f:
            json.dump(rapor, f, indent=2)

    # ── OTOMATİK DÖNGÜ ────────────────────────────────
    def surekli_kontrol(self, aralik_dk=30):
        """Her 30 dakikada kontrol et."""
        print(f"🔍 DOĞRULUK KONTROL 7/24 — Her {aralik_dk} dk")
        while True:
            kontrol, dogru, yanlis = self.kontrol_et(bekleme_saat=24)
            if kontrol > 0:
                print(f"[{datetime.now().strftime('%H:%M')}] {kontrol} sinyal kontrol edildi: {dogru}✅ {yanlis}❌")
            time.sleep(aralik_dk * 60)


if __name__ == "__main__":
    import sys

    dk = DogrulukKontrol()

    if "--rapor" in sys.argv:
        dk.rapor()
    elif "--kontrol" in sys.argv:
        kontrol, dogru, yanlis = dk.kontrol_et(bekleme_saat=1)
        print(f"Kontrol: {kontrol} sinyal | Doğru: {dogru} | Yanlış: {yanlis}")
    elif "--loop" in sys.argv:
        dk.surekli_kontrol()
    else:
        # Test: mevcut coin sinyallerini kaydet
        print("🔍 Test — mevcut coin sinyalleri kaydediliyor...")
        try:
            from coin_trader import CoinBrain
            brain = CoinBrain()
            bombalar = brain.tara()
            for b in bombalar:
                sid = dk.sinyal_kaydet(
                    sistem="COIN", symbol=b["symbol"],
                    karar=b["karar"], skor=b["skor"],
                    fiyat=b["fiyat"], ajanlar=b.get("puanlar", {})
                )
                print(f"  Kaydedildi: {b['symbol']} {b['karar']} Skor:{b['skor']:.0f} → ID:{sid}")
        except Exception as e:
            print(f"Hata: {e}")

        dk.rapor()
