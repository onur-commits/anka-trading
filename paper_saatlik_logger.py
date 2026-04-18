"""
ANKA Paper Mode — Saatlik Snapshot Logger
==========================================

coin_otonom_trader.py'nin --dry-run modunda ürettiği state + trade dosyalarını
her saat okur, saatlik fotoğraf çeker, data/paper_saatlik.json'a append eder.

Bot'a dokunmaz, sadece OKUR. Paralel çalışır.

Kullanım (VPS'te, ayrı pencerede):
  python paper_saatlik_logger.py

Yarın sabah özet için:
  python paper_saatlik_rapor.py
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
STATE_FILE = DATA_DIR / "coin_otonom_state.json"
TRADE_LOG = DATA_DIR / "coin_otonom_trades.json"
SAATLIK = DATA_DIR / "paper_saatlik.json"

INTERVAL_SEC = 3600  # 1 saat


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def snapshot_al(onceki_trade_idx: int) -> tuple[dict, int]:
    state = _load_json(STATE_FILE, {})
    trades_raw = _load_json(TRADE_LOG, [])
    # trades bazen {"trades": [...]} bazen [...] formatında — ikisini de destekle
    if isinstance(trades_raw, dict):
        trades = trades_raw.get("trades", [])
    else:
        trades = trades_raw or []

    yeni_trades = trades[onceki_trade_idx:]
    yeni_idx = len(trades)

    # Aktif pozisyonlardan toplam değeri hesapla (state zaten fiyatları kaydediyor)
    pozisyonlar = state.get("pozisyonlar", {})
    aktif_sayi = len(pozisyonlar) if isinstance(pozisyonlar, dict) else 0

    snap = {
        "zaman": datetime.now(timezone.utc).isoformat(),
        "yerel_zaman": datetime.now().isoformat(),
        "cycle": state.get("cycle"),
        "son_tarama": state.get("son_tarama"),
        "dry_run": state.get("dry_run"),
        "aktif_pozisyon_sayisi": aktif_sayi,
        "aktif_pozisyonlar": pozisyonlar if isinstance(pozisyonlar, dict) else {},
        "toplam_trade_sayisi": len(trades),
        "bu_saatki_yeni_trade": len(yeni_trades),
        "yeni_trade_ozet": [
            {
                "zaman": t.get("zaman") or t.get("dt") or t.get("time"),
                "sembol": t.get("sembol") or t.get("symbol"),
                "yon": t.get("yon") or t.get("tip") or t.get("side"),
                "fiyat": t.get("fiyat") or t.get("price"),
                "miktar": t.get("miktar") or t.get("quantity"),
                "skor": t.get("skor"),
                "sebep": t.get("sebep"),
                "mod": t.get("mod"),
            }
            for t in yeni_trades
        ],
    }
    return snap, yeni_idx


def main() -> None:
    SAATLIK.parent.mkdir(parents=True, exist_ok=True)
    # Mevcut saatlik dosyayı yükle
    mevcut = _load_json(SAATLIK, {"baslangic": None, "snapshots": []})
    if mevcut.get("baslangic") is None:
        mevcut["baslangic"] = datetime.now(timezone.utc).isoformat()

    # İlk trade index — çalışmaya başladığımızda trade log'da ne varsa "eski"
    ilk_trades = _load_json(TRADE_LOG, [])
    if isinstance(ilk_trades, dict):
        ilk_trades = ilk_trades.get("trades", [])
    onceki_idx = len(ilk_trades)
    print(f"[logger] başlatıldı. Mevcut trade log: {onceki_idx} kayıt (bunlar 'eski' sayılacak)")
    print(f"[logger] saatlik dosya: {SAATLIK}")
    print(f"[logger] periyod: {INTERVAL_SEC}s")

    # İlk anlık snapshot (sıfır noktası)
    snap0, onceki_idx = snapshot_al(onceki_idx)
    snap0["etiket"] = "T0_baslangic"
    mevcut["snapshots"].append(snap0)
    SAATLIK.write_text(json.dumps(mevcut, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[logger] T0 snapshot alındı — aktif poz: {snap0['aktif_pozisyon_sayisi']}")

    saat = 1
    try:
        while True:
            time.sleep(INTERVAL_SEC)
            snap, onceki_idx = snapshot_al(onceki_idx)
            snap["etiket"] = f"T+{saat}h"
            mevcut["snapshots"].append(snap)
            SAATLIK.write_text(json.dumps(mevcut, indent=2, ensure_ascii=False), encoding="utf-8")
            print(
                f"[logger] T+{saat}h — aktif poz: {snap['aktif_pozisyon_sayisi']}, "
                f"yeni trade: {snap['bu_saatki_yeni_trade']}"
            )
            saat += 1
    except KeyboardInterrupt:
        print(f"\n[logger] durduruldu. Toplam snapshot: {len(mevcut['snapshots'])}")


if __name__ == "__main__":
    main()
