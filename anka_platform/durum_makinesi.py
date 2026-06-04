"""
State Machine + Health (Gün 8) — sinyal akışı + websocket/latency gate
======================================================================
Sinyal yaşam döngüsü: scanning → watch → armed → confirm → execute →
manage → exit → reset. Her geçiş loglanır, geçersiz geçiş engellenir.
Health gate: latency/bağlantı bozulursa 'execute'a geçişi durdurur.
"""
from datetime import datetime

DURUMLAR = ["scanning", "watch", "armed", "confirm", "execute",
            "manage", "exit", "reset"]

# İzin verilen geçişler
GECISLER = {
    "scanning": {"watch", "reset"},
    "watch": {"armed", "scanning", "reset"},
    "armed": {"confirm", "watch", "reset"},
    "confirm": {"execute", "armed", "reset"},   # execute health-gate'e tabi
    "execute": {"manage", "reset"},
    "manage": {"exit", "manage", "reset"},
    "exit": {"reset"},
    "reset": {"scanning"},
}


class SinyalDurumu:
    def __init__(self, sembol, health_check=None):
        self.sembol = sembol
        self.durum = "scanning"
        self.gecmis = [("scanning", datetime.now())]
        self.health_check = health_check or (lambda: (True, "ok"))

    def gecebilir_mi(self, hedef):
        return hedef in GECISLER.get(self.durum, set())

    def gec(self, hedef, sebep=""):
        if not self.gecebilir_mi(hedef):
            raise ValueError(f"Geçersiz geçiş: {self.durum} → {hedef}")
        # Health gate: execute'a geçişte bağlantı/latency kontrolü
        if hedef == "execute":
            saglik, mesaj = self.health_check()
            if not saglik:
                raise RuntimeError(f"HEALTH GATE: execute engellendi ({mesaj})")
        self.durum = hedef
        self.gecmis.append((hedef, datetime.now()))
        return True

    def __repr__(self):
        return f"<{self.sembol}: {self.durum}>"


def varsayilan_health(max_latency_ms=500):
    """Latency modülünden son ölçüme bakan health-check üretir."""
    def kontrol():
        try:
            from anka_platform.raporlama import latency_ozet
            o = latency_ozet()
            if o.get("adet", 0) == 0:
                return True, "latency verisi yok (izin)"
            if o.get("p95_ms", 0) > max_latency_ms:
                return False, f"latency yüksek p95={o['p95_ms']}ms"
            if o.get("basari_orani", 100) < 90:
                return False, f"başarı düşük %{o['basari_orani']}"
            return True, "ok"
        except Exception:
            return True, "health okunamadı (fail-open)"
    return kontrol


if __name__ == "__main__":
    print("=== STATE MACHINE ===")
    s = SinyalDurumu("THYAO")
    for h in ["watch", "armed", "confirm", "execute", "manage", "exit", "reset"]:
        try:
            s.gec(h)
            print(f"  → {h} ✅")
        except Exception as e:
            print(f"  → {h} ❌ {e}")
    print("Geçersiz geçiş testi (reset→execute):")
    try:
        s.gec("execute")
    except ValueError as e:
        print("  ", e)
