"""
A/B Sonuç — Bot vs BTC Buy & Hold deneyinin nihai kararı
=========================================================
30 günlük A/B deneyi (ab_karsilastirma.py) bittiğinde çalıştırılır.
data/ab_karsilastirma.json state dosyasını okur, nihai getiriyi
hesaplar ve CLAUDE.md'deki karar kuralını uygular:

  Bot önde  → momentum stratejiye devam
  B&H önde  → momentum bot rafa, BTC Buy & Hold'a dön

API gerektirmez — sadece kayıtlı snapshot'ları okur, her yerde çalışır.

Kullanım:
  python ab_sonuc.py            # sonuç tablosu + karar, data/ab_sonuc.md yaz
  python ab_sonuc.py --kisa     # sadece tek satır özet
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STATE_DOSYA = Path(__file__).parent / "data" / "ab_karsilastirma.json"
SONUC_DOSYA = Path(__file__).parent / "data" / "ab_sonuc.md"
DENEY_GUN = 30  # planlanan deney süresi


def _parse_zaman(s: str) -> datetime:
    """ISO zaman damgasını timezone-aware datetime'a çevir."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def sonuc_hesapla() -> dict | None:
    """State dosyasından nihai metrikleri hesapla."""
    if not STATE_DOSYA.exists():
        return None
    try:
        s = json.loads(STATE_DOSYA.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None

    snapshots = s.get("snapshots") or []
    t0 = s.get("t0")
    if not snapshots or not t0:
        return None

    son = snapshots[-1]
    bot_t0 = t0.get("bot_baslangic_deger", 0) or 0
    bh_t0 = t0.get("bh_baslangic_usdt", 0) or 0

    bot_pct = (son["bot_deger"] / bot_t0 - 1) * 100 if bot_t0 > 0 else 0.0
    bh_pct = (son["bh_deger"] / bh_t0 - 1) * 100 if bh_t0 > 0 else 0.0
    fark = bot_pct - bh_pct

    t0_zaman = _parse_zaman(t0["zaman"])
    son_zaman = _parse_zaman(son["zaman"])
    gecen_gun = (son_zaman - t0_zaman).total_seconds() / 86400

    if fark > 0.5:
        kazanan = "BOT"
        karar = "Momentum strateji önde — bota DEVAM."
    elif fark < -0.5:
        kazanan = "B&H"
        karar = "BTC Buy & Hold önde — momentum bot RAFA, B&H'a dönülmeli."
    else:
        kazanan = "BERABERE"
        karar = "Fark anlamsız — deney uzatılabilir veya B&H tercih edilir (basitlik)."

    return {
        "t0_zaman": t0["zaman"],
        "son_zaman": son["zaman"],
        "gecen_gun": gecen_gun,
        "tamamlandi": gecen_gun >= DENEY_GUN,
        "snapshot_sayisi": len(snapshots),
        "bot_t0": bot_t0,
        "bot_son": son["bot_deger"],
        "bot_pct": bot_pct,
        "bh_t0": bh_t0,
        "bh_son": son["bh_deger"],
        "bh_pct": bh_pct,
        "fark": fark,
        "kazanan": kazanan,
        "karar": karar,
        "btc_t0": t0.get("btc_fiyat", 0),
        "btc_son": son.get("btc_fiyat", 0),
    }


def rapor_yaz(r: dict):
    """Sonuç markdown raporunu data/ab_sonuc.md olarak yaz."""
    durum = "TAMAMLANDI" if r["tamamlandi"] else f"DEVAM EDIYOR ({r['gecen_gun']:.1f}/{DENEY_GUN} gün)"
    lines = [
        "# A/B Sonuç — Bot vs BTC Buy & Hold",
        "",
        f"**Deney durumu:** {durum}",
        f"**T0:** {r['t0_zaman'][:19]} UTC",
        f"**Son snapshot:** {r['son_zaman'][:19]} UTC ({r['snapshot_sayisi']} snapshot)",
        f"**BTC fiyat:** ${r['btc_t0']:,.0f} → ${r['btc_son']:,.0f}",
        "",
        "## Nihai Skor",
        "",
        "| Strateji | Başlangıç | Son | Getiri |",
        "|---|---:|---:|---:|",
        f"| Bot (momentum) | ${r['bot_t0']:.2f} | ${r['bot_son']:.2f} | **{r['bot_pct']:+.2f}%** |",
        f"| BTC Buy & Hold | ${r['bh_t0']:.2f} | ${r['bh_son']:.2f} | **{r['bh_pct']:+.2f}%** |",
        f"| Fark | | | **{r['fark']:+.2f} puan** |",
        "",
        f"## Kazanan: {r['kazanan']}",
        "",
        f"**Karar:** {r['karar']}",
        "",
    ]
    if not r["tamamlandi"]:
        lines.append(
            f"> Not: Deney henüz {DENEY_GUN} güne ulaşmadı; sonuç geçicidir."
        )
        lines.append("")
    SONUC_DOSYA.parent.mkdir(parents=True, exist_ok=True)
    SONUC_DOSYA.write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kisa", action="store_true", help="Tek satır özet")
    args = p.parse_args()

    r = sonuc_hesapla()
    if r is None:
        print("A/B state dosyası yok veya boş:")
        print(f"  {STATE_DOSYA}")
        print("Deney VPS'te (C:\\ANKA) yürütülüyor — orada çalıştırın:")
        print("  cd C:\\ANKA && git pull && python -X utf8 ab_sonuc.py")
        return 1

    if args.kisa:
        durum = "tamam" if r["tamamlandi"] else f"{r['gecen_gun']:.0f}/{DENEY_GUN}g"
        print(f"[{durum}] Bot {r['bot_pct']:+.2f}% | B&H {r['bh_pct']:+.2f}% | "
              f"Fark {r['fark']:+.2f}p → {r['kazanan']}")
        return 0

    print(f"=== A/B Sonuç ({'TAMAMLANDI' if r['tamamlandi'] else 'DEVAM'}) ===")
    print(f"Süre:   {r['gecen_gun']:.1f} gün ({r['snapshot_sayisi']} snapshot)")
    print(f"Bot:    ${r['bot_t0']:.2f} → ${r['bot_son']:.2f}  ({r['bot_pct']:+.2f}%)")
    print(f"B&H:    ${r['bh_t0']:.2f} → ${r['bh_son']:.2f}  ({r['bh_pct']:+.2f}%)")
    print(f"Fark:   {r['fark']:+.2f} puan  → KAZANAN: {r['kazanan']}")
    print(f"Karar:  {r['karar']}")

    rapor_yaz(r)
    print(f"\nRapor: {SONUC_DOSYA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
