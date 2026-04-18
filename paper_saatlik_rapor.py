"""
ANKA Paper Mode — Saatlik Rapor Okuma
======================================

data/paper_saatlik.json'u okur ve özet tablo çıkarır.

Kullanım:
  python paper_saatlik_rapor.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
SAATLIK = PROJECT_DIR / "data" / "paper_saatlik.json"
RAPOR_MD = PROJECT_DIR / "data" / "paper_saatlik_rapor.md"


def main() -> None:
    if not SAATLIK.exists():
        print(f"HATA: {SAATLIK} yok. Önce paper_saatlik_logger.py çalıştır.")
        return
    data = json.loads(SAATLIK.read_text(encoding="utf-8"))
    snaps = data.get("snapshots", [])
    if not snaps:
        print("Snapshot yok.")
        return

    baslangic = data.get("baslangic", "?")
    son_snap = snaps[-1]
    ilk_snap = snaps[0]

    # Tüm yeni trade'leri topla
    tum_trades: list[dict] = []
    for s in snaps:
        tum_trades.extend(s.get("yeni_trade_ozet", []))

    al_trades = [t for t in tum_trades if t.get("yon") in ("AL", "BUY", "al", "buy")]
    sat_trades = [t for t in tum_trades if t.get("yon") in ("SAT", "SELL", "sat", "sell")]

    semboller = Counter(t.get("sembol") for t in al_trades if t.get("sembol"))
    sebepler = Counter(t.get("sebep") for t in sat_trades if t.get("sebep"))

    lines = []
    lines.append("# Paper Mode — Saatlik Rapor")
    lines.append("")
    lines.append(f"**Başlangıç:** {baslangic}")
    lines.append(f"**Şu an:** {datetime.now().isoformat()}")
    lines.append(f"**Toplam snapshot:** {len(snaps)}")
    lines.append("")
    lines.append("## Özet")
    lines.append("")
    lines.append(f"- Toplam alım: **{len(al_trades)}**")
    lines.append(f"- Toplam satış: **{len(sat_trades)}**")
    lines.append(f"- Son aktif pozisyon sayısı: **{son_snap.get('aktif_pozisyon_sayisi', 0)}**")
    lines.append(f"- İlk aktif pozisyon sayısı: **{ilk_snap.get('aktif_pozisyon_sayisi', 0)}**")
    if semboller:
        lines.append("")
        lines.append("## Alım sembol dağılımı")
        lines.append("")
        for s, n in semboller.most_common():
            lines.append(f"- {s}: {n}")
    if sebepler:
        lines.append("")
        lines.append("## Satış sebep dağılımı")
        lines.append("")
        for s, n in sebepler.most_common():
            lines.append(f"- {s}: {n}")

    lines.append("")
    lines.append("## Saatlik tablo")
    lines.append("")
    lines.append("| Etiket | Zaman | Aktif Poz | Yeni AL | Yeni SAT |")
    lines.append("|---|---|---:|---:|---:|")
    for s in snaps:
        yeni = s.get("yeni_trade_ozet", [])
        al_n = sum(1 for t in yeni if t.get("yon") in ("AL", "BUY", "al", "buy"))
        sat_n = sum(1 for t in yeni if t.get("yon") in ("SAT", "SELL", "sat", "sell"))
        zaman = (s.get("yerel_zaman") or s.get("zaman") or "?")[:16]
        lines.append(
            f"| {s.get('etiket','?')} | {zaman} | "
            f"{s.get('aktif_pozisyon_sayisi',0)} | {al_n} | {sat_n} |"
        )

    lines.append("")
    lines.append("## Son 15 trade")
    lines.append("")
    lines.append("| Zaman | Sembol | Yön | Fiyat | Miktar | Skor | Sebep | Mod |")
    lines.append("|---|---|---|---:|---:|---:|---|---|")
    for t in tum_trades[-15:]:
        lines.append(
            f"| {str(t.get('zaman',''))[:16]} | {t.get('sembol','')} | {t.get('yon','')} | "
            f"{t.get('fiyat','')} | {t.get('miktar','')} | {t.get('skor','')} | "
            f"{t.get('sebep','')} | {t.get('mod','')} |"
        )

    RAPOR_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rapor yazıldı: {RAPOR_MD}")
    print(f"\nÖzet: {len(al_trades)} alım, {len(sat_trades)} satış, "
          f"aktif pozisyon: {son_snap.get('aktif_pozisyon_sayisi',0)}")


if __name__ == "__main__":
    main()
