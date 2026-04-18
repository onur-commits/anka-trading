"""
ANKA — Binance Simple Earn (Flexible) → Spot Transfer Aracı
============================================================

Ne yapar:
  Binance Simple Earn (Flexible) cüzdanındaki coinleri listeler,
  her biri için kullanıcıya "Transfer edilsin mi? (y/n)" diye sorar,
  onay verilenleri Spot cüzdana redeem eder.

Kullanım:
  python earn_to_spot.py              # canlı (ama her coin için onay sorar)
  python earn_to_spot.py --dry-run    # hiçbir şey göndermez, sadece listeler
  python earn_to_spot.py --min-usd 1  # $1 altındaki "toz"u atla (default 1)
  python earn_to_spot.py --yes-all    # TEHLİKELİ: tüm coinleri soru sormadan redeem eder

Gereksinim:
  - C:\\ANKA\\.env içinde BINANCE_API_KEY ve BINANCE_API_SECRET
  - API key izinleri: "Enable Spot & Margin Trading" + "Enable Simple Earn"
  - python-dotenv, requests

Log:
  data/earn_transfer_log.json dosyasına append eder.

GÜVENLİK NOTU:
  Bu script yalnızca kullanıcı tarafından manuel çalıştırılmak üzere yazılmıştır.
  Claude/agent bu scripti ASLA kendi tetiklemez.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

# ----------------------------- Sabitler ---------------------------------------

BASE_URL = "https://api.binance.com"
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
LOG_PATH = SCRIPT_DIR / "data" / "earn_transfer_log.json"
RECV_WINDOW = 5000  # ms

# ----------------------------- Yardımcılar ------------------------------------


def _sign(query: str, secret: str) -> str:
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


def _signed_request(
    method: str,
    path: str,
    api_key: str,
    api_secret: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = dict(params or {})
    params["timestamp"] = _timestamp_ms()
    params["recvWindow"] = RECV_WINDOW
    query = urlencode(params, doseq=True)
    signature = _sign(query, api_secret)
    url = f"{BASE_URL}{path}?{query}&signature={signature}"
    headers = {"X-MBX-APIKEY": api_key}
    resp = requests.request(method, url, headers=headers, timeout=15)
    if resp.status_code >= 400:
        raise RuntimeError(f"Binance hata {resp.status_code}: {resp.text}")
    return resp.json()


def _usd_price(symbol: str) -> float:
    """USDT fiyatını çek. USDT'nin kendisi için 1.0 döner."""
    if symbol.upper() in {"USDT", "BUSD", "USDC", "FDUSD"}:
        return 1.0
    try:
        resp = requests.get(
            f"{BASE_URL}/api/v3/ticker/price",
            params={"symbol": f"{symbol}USDT"},
            timeout=10,
        )
        if resp.status_code == 200:
            return float(resp.json().get("price", 0) or 0)
    except Exception:
        pass
    return 0.0


def _log_entry(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: list[dict[str, Any]] = []
    if LOG_PATH.exists():
        try:
            data = json.loads(LOG_PATH.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            data = []
    data.append(entry)
    LOG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ----------------------------- Binance çağrıları ------------------------------


def test_api_izinleri(api_key: str, api_secret: str) -> tuple[bool, bool]:
    """(spot_ok, earn_ok) döner."""
    spot_ok = False
    earn_ok = False
    try:
        _signed_request("GET", "/api/v3/account", api_key, api_secret)
        spot_ok = True
    except Exception as e:
        print(f"  Spot izni test HATA: {e}")
    try:
        _signed_request(
            "GET",
            "/sapi/v1/simple-earn/flexible/position",
            api_key,
            api_secret,
            {"size": 1},
        )
        earn_ok = True
    except Exception as e:
        print(f"  Simple Earn izni test HATA: {e}")
    return spot_ok, earn_ok


def flexible_pozisyonlari_getir(api_key: str, api_secret: str) -> list[dict[str, Any]]:
    """Tüm flexible earn pozisyonlarını toplar (sayfa sayfa)."""
    all_rows: list[dict[str, Any]] = []
    current = 1
    size = 100
    while True:
        data = _signed_request(
            "GET",
            "/sapi/v1/simple-earn/flexible/position",
            api_key,
            api_secret,
            {"current": current, "size": size},
        )
        rows = data.get("rows", []) if isinstance(data, dict) else []
        all_rows.extend(rows)
        total = data.get("total", len(all_rows)) if isinstance(data, dict) else len(all_rows)
        if len(all_rows) >= total or not rows:
            break
        current += 1
    return all_rows


def flexible_redeem(
    api_key: str,
    api_secret: str,
    product_id: str,
    amount: float,
    redeem_all: bool = False,
) -> dict[str, Any]:
    """Flexible product redeem. destAccount=SPOT default."""
    params: dict[str, Any] = {
        "productId": product_id,
        "destAccount": "SPOT",
    }
    if redeem_all:
        params["redeemAll"] = "true"
    else:
        params["amount"] = f"{amount:.8f}".rstrip("0").rstrip(".")
    return _signed_request(
        "POST",
        "/sapi/v1/simple-earn/flexible/redeem",
        api_key,
        api_secret,
        params,
    )


# ----------------------------- Ana akış ---------------------------------------


def _ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    suffix = " (y/N): " if default_no else " (Y/n): "
    try:
        cevap = input(prompt + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not cevap:
        return not default_no
    return cevap in {"y", "yes", "evet", "e"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Binance Earn → Spot transfer aracı")
    parser.add_argument("--dry-run", action="store_true", help="Hiçbir şey gönderme, sadece listele")
    parser.add_argument("--min-usd", type=float, default=1.0, help="Bu USD değerinin altındaki coinleri atla")
    parser.add_argument("--yes-all", action="store_true", help="Tüm coinleri onay sormadan redeem et (TEHLİKELİ)")
    args = parser.parse_args()

    load_dotenv(ENV_PATH)
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        print(f"HATA: {ENV_PATH} içinde BINANCE_API_KEY / BINANCE_API_SECRET yok.")
        return 2

    print("=" * 60)
    print("ANKA — Earn → Spot Transfer")
    print(f"Zaman: {datetime.now().isoformat(timespec='seconds')}")
    print(f"Mod:   {'DRY-RUN (test)' if args.dry_run else 'CANLI'}")
    print("=" * 60)

    # 1) İzin testi
    print("\n[1/3] API izinleri test ediliyor...")
    spot_ok, earn_ok = test_api_izinleri(api_key, api_secret)
    print(f"  Spot  : {'OK' if spot_ok else 'YOK'}")
    print(f"  Earn  : {'OK' if earn_ok else 'YOK'}")
    if not earn_ok:
        print("\nUYARI: Simple Earn izni yok veya test başarısız.")
        print("Binance → API Management → key ayarlarından 'Enable Simple Earn' işaretle.")
        print("Ya da transferi manuel olarak Binance arayüzünden yap.")
        return 3
    if not spot_ok:
        print("\nUYARI: Spot izni yok. Redeem gider ama bot trade edemez.")
        if not _ask_yes_no("Yine de devam edilsin mi?"):
            return 3

    # 2) Pozisyonları çek
    print("\n[2/3] Flexible Earn pozisyonları alınıyor...")
    try:
        pozisyonlar = flexible_pozisyonlari_getir(api_key, api_secret)
    except Exception as e:
        print(f"  HATA: {e}")
        return 4

    if not pozisyonlar:
        print("  Earn'de pozisyon yok. Yapacak bir şey kalmadı.")
        return 0

    # Her pozisyon için USD değerini hesapla
    zenginlestirilmis: list[dict[str, Any]] = []
    for p in pozisyonlar:
        asset = p.get("asset", "")
        try:
            miktar = float(p.get("totalAmount", 0) or 0)
        except (TypeError, ValueError):
            miktar = 0.0
        fiyat = _usd_price(asset) if miktar > 0 else 0.0
        usd = miktar * fiyat
        zenginlestirilmis.append(
            {
                "asset": asset,
                "productId": p.get("productId", ""),
                "amount": miktar,
                "usd_price": fiyat,
                "usd_value": usd,
                "raw": p,
            }
        )

    # USD değerine göre büyükten küçüğe sırala
    zenginlestirilmis.sort(key=lambda x: x["usd_value"], reverse=True)

    print(f"\n  {len(zenginlestirilmis)} pozisyon bulundu:\n")
    print(f"  {'COIN':<8} {'MİKTAR':>18} {'FİYAT($)':>12} {'DEĞER($)':>12}")
    print(f"  {'-' * 8} {'-' * 18} {'-' * 12} {'-' * 12}")
    toplam_usd = 0.0
    for z in zenginlestirilmis:
        toplam_usd += z["usd_value"]
        print(
            f"  {z['asset']:<8} {z['amount']:>18.8f} "
            f"{z['usd_price']:>12.4f} {z['usd_value']:>12.2f}"
        )
    print(f"  {'-' * 52}")
    print(f"  {'TOPLAM':<8} {'':>18} {'':>12} {toplam_usd:>12.2f}")

    # 3) Her biri için sor
    print("\n[3/3] Transfer seçimi\n")
    if args.yes_all and not args.dry_run:
        print("UYARI: --yes-all verildi. Tüm coinler soru sormadan redeem edilecek.")
        if not _ask_yes_no("Devam?"):
            return 0

    islem_kayitlari: list[dict[str, Any]] = []
    transfer_sayisi = 0
    atlanan_sayisi = 0
    hata_sayisi = 0

    for z in zenginlestirilmis:
        asset = z["asset"]
        miktar = z["amount"]
        usd = z["usd_value"]
        product_id = z["productId"]

        if miktar <= 0:
            continue

        if usd < args.min_usd:
            print(f"  [{asset}] ${usd:.2f} < min ${args.min_usd:.2f} — atlandı (toz)")
            atlanan_sayisi += 1
            continue

        prompt = f"  [{asset}] {miktar:.8f} (~${usd:.2f}) → Spot'a aktarılsın mı?"
        if args.yes_all:
            secim = True
            print(f"{prompt} (y - yes-all)")
        else:
            secim = _ask_yes_no(prompt)

        if not secim:
            print(f"     atlandı.")
            atlanan_sayisi += 1
            continue

        kayit: dict[str, Any] = {
            "zaman": datetime.now(timezone.utc).isoformat(),
            "asset": asset,
            "productId": product_id,
            "miktar": miktar,
            "usd_degeri": usd,
            "mod": "dry-run" if args.dry_run else "canli",
            "durum": "bilinmiyor",
            "yanit": None,
            "hata": None,
        }

        if args.dry_run:
            kayit["durum"] = "dry-run"
            print(f"     DRY-RUN: redeem isteği gönderilmedi.")
            transfer_sayisi += 1
        else:
            try:
                yanit = flexible_redeem(
                    api_key,
                    api_secret,
                    product_id=product_id,
                    amount=miktar,
                    redeem_all=True,  # en güvenlisi: tamamını çek
                )
                kayit["durum"] = "basarili"
                kayit["yanit"] = yanit
                print(f"     OK — redeem gönderildi. İşlem: {yanit}")
                transfer_sayisi += 1
            except Exception as e:
                kayit["durum"] = "hata"
                kayit["hata"] = str(e)
                print(f"     HATA: {e}")
                hata_sayisi += 1

        islem_kayitlari.append(kayit)
        time.sleep(0.3)  # rate limit nezaket

    # Log yaz
    if islem_kayitlari:
        _log_entry(
            {
                "oturum_zamani": datetime.now(timezone.utc).isoformat(),
                "mod": "dry-run" if args.dry_run else "canli",
                "islemler": islem_kayitlari,
            }
        )

    # Özet
    print("\n" + "=" * 60)
    print("ÖZET")
    print(f"  Transfer edildi : {transfer_sayisi}")
    print(f"  Atlandı         : {atlanan_sayisi}")
    print(f"  Hata            : {hata_sayisi}")
    print(f"  Log             : {LOG_PATH}")
    print("=" * 60)
    print("\nNot: Redeem işlemleri Binance tarafında birkaç saniye - dakika içinde")
    print("Spot cüzdana yansır. Spot'ta gördükten sonra bot otomatik yönetir.")
    return 0 if hata_sayisi == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nİptal edildi.")
        sys.exit(130)
