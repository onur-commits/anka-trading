"""
Raporlama paketi (Gün 6) — PDF/CSV export, latency, execution kalitesi
=======================================================================
- CSV export (her zaman çalışır).
- PDF export: reportlab varsa gerçek PDF, yoksa düz metin .txt fallback.
- Latency kaydı: API/emir gecikmesi ölçümü ve özet.
- Execution kalitesi: beklenen vs gerçekleşen fiyat (slippage).
- Session/region analizi: işlem saatine göre performans.
"""
import csv
import io
import json
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
LATENCY = DATA / "latency_log.json"


def csv_uret(satirlar, basliklar=None):
    """list[dict] → CSV string (utf-8-sig, Excel TR uyumlu)."""
    if not satirlar:
        return ""
    basliklar = basliklar or list(satirlar[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=basliklar, extrasaction="ignore")
    w.writeheader()
    w.writerows(satirlar)
    return buf.getvalue()


def pdf_uret(baslik, satirlar, dosya):
    """PDF üret (reportlab varsa), yoksa .txt fallback. Dosya yolunu döner."""
    dosya = Path(dosya)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(dosya), pagesize=A4)
        y = 800
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, baslik)
        c.setFont("Helvetica", 9)
        y -= 30
        for s in satirlar:
            c.drawString(40, y, str(s)[:110])
            y -= 14
            if y < 40:
                c.showPage()
                y = 800
        c.save()
        return str(dosya)
    except ImportError:
        # Fallback: düz metin
        txt = dosya.with_suffix(".txt")
        txt.write_text(baslik + "\n\n" + "\n".join(str(s) for s in satirlar),
                       encoding="utf-8")
        return str(txt)


# ── Latency ölçümü ──
def latency_kaydet(islem, ms, basarili=True):
    kayitlar = []
    if LATENCY.exists():
        try:
            kayitlar = json.loads(LATENCY.read_text(encoding="utf-8"))
        except Exception:
            kayitlar = []
    kayitlar.append({"zaman": datetime.now().isoformat(timespec="seconds"),
                     "islem": islem, "ms": round(ms, 1), "ok": basarili})
    kayitlar = kayitlar[-2000:]
    DATA.mkdir(exist_ok=True)
    LATENCY.write_text(json.dumps(kayitlar, ensure_ascii=False), encoding="utf-8")


def latency_ozet():
    if not LATENCY.exists():
        return {"adet": 0}
    try:
        k = json.loads(LATENCY.read_text(encoding="utf-8"))
    except Exception:
        return {"adet": 0}
    msler = [x["ms"] for x in k]
    if not msler:
        return {"adet": 0}
    msler_s = sorted(msler)
    return {
        "adet": len(msler),
        "ort_ms": round(sum(msler) / len(msler), 1),
        "min_ms": min(msler),
        "max_ms": max(msler),
        "p95_ms": msler_s[int(len(msler_s) * 0.95) - 1],
        "basari_orani": round(sum(1 for x in k if x["ok"]) / len(k) * 100, 1),
    }


def execution_kalite(beklenen, gerceklesen, yon="ALIS"):
    """Slippage hesapla (%)."""
    if beklenen <= 0:
        return 0.0
    fark = (gerceklesen - beklenen) / beklenen * 100
    # ALIŞ'ta yüksek fiyat kötü, SATIŞ'ta düşük fiyat kötü
    return round(fark if yon == "ALIS" else -fark, 3)


def session_analiz(islemler):
    """İşlemleri saat dilimine göre grupla (açılış/öğlen/kapanış)."""
    gruplar = {"açılış (10-11)": [], "öğlen (12-14)": [], "kapanış (15-18)": [], "diğer": []}
    for i in islemler:
        try:
            saat = datetime.fromisoformat(i.get("zaman", "")).hour
        except Exception:
            gruplar["diğer"].append(i)
            continue
        kz = i.get("kar_zarar_pct", i.get("kz_pct", 0)) or 0
        if 10 <= saat < 11:
            gruplar["açılış (10-11)"].append(kz)
        elif 12 <= saat < 14:
            gruplar["öğlen (12-14)"].append(kz)
        elif 15 <= saat < 18:
            gruplar["kapanış (15-18)"].append(kz)
        else:
            gruplar["diğer"].append(kz)
    ozet = {}
    for k, v in gruplar.items():
        sayilar = [x for x in v if isinstance(x, (int, float))]
        if sayilar:
            ozet[k] = {"adet": len(sayilar),
                       "ort_kz": round(sum(sayilar) / len(sayilar), 2)}
    return ozet


if __name__ == "__main__":
    print("=== RAPORLAMA MODÜLÜ ===")
    print("CSV:", csv_uret([{"a": 1, "b": 2}])[:30])
    latency_kaydet("emir", 45.3)
    latency_kaydet("emir", 120.5)
    print("Latency özet:", latency_ozet())
    print("Slippage (100→100.5 alış):", execution_kalite(100, 100.5), "%")
