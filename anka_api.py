"""
ANKA API — MatriksIQ Dışarıdan Emir Kabulü Python Client
=========================================================
TCP soket ile IQ'ya bağlanır, doğrudan emir gönderir.
C# robota gerek kalmaz!

Bağlantı: localhost:18890 (IQ açıkken)
Protokol: JSON + char(11) sonlandırıcı
"""

import socket
import json
import time
from datetime import datetime


class AnkaAPI:
    """MatriksIQ API Python Client."""

    def __init__(self, host="127.0.0.1", port=18890):
        self.host = host
        self.port = port
        self.sock = None
        self.TERMINATOR = chr(11)  # char(11) paket sonu

    # ── BAĞLANTI ────────────────────────────────────
    def baglan(self):
        """IQ'ya TCP bağlantısı kur."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            # JSON modu seç
            self._gonder({"SetMessageType0": "MessageType"})
            print(f"✅ IQ'ya bağlandı ({self.host}:{self.port})")
            return True
        except Exception as e:
            print(f"❌ Bağlantı hatası: {e}")
            return False

    def kapat(self):
        """Bağlantıyı kapat."""
        if self.sock:
            self.sock.close()
            self.sock = None

    def _gonder(self, data):
        """JSON paketi gönder + char(11) sonlandırıcı."""
        paket = json.dumps(data) + self.TERMINATOR
        self.sock.sendall(paket.encode('utf-8'))

    def _al(self, timeout=5):
        """Yanıt al."""
        self.sock.settimeout(timeout)
        try:
            buf = b""
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                if chr(11) in buf.decode('utf-8', errors='ignore'):
                    break
            text = buf.decode('utf-8', errors='ignore').replace(chr(11), '')
            return json.loads(text) if text.strip() else None
        except socket.timeout:
            return None
        except:
            return None

    # ── HESAP BİLGİLERİ ────────────────────────────
    def hesaplari_listele(self):
        """Giriş yapılmış hesapları listele. (ApiCommands: 0)"""
        self._gonder({"ApiCommands": 0})
        return self._al()

    def pozisyonlari_oku(self, brokage_id, account_id, exchange_id=4):
        """Hesaptaki pozisyonları oku. (ApiCommands: 1)
        exchange_id: 4=BIST, 9=VIOP
        """
        self._gonder({
            "BrokageId": brokage_id,
            "AccountId": account_id,
            "ExchangeId": exchange_id,
            "ApiCommands": 1
        })
        return self._al()

    def emirleri_oku(self, brokage_id, account_id, exchange_id=4):
        """Bekleyen emirleri oku. (ApiCommands: 2)"""
        self._gonder({
            "BrokageId": brokage_id,
            "AccountId": account_id,
            "ExchangeId": exchange_id,
            "ApiCommands": 2
        })
        return self._al()

    # ── EMİR GÖNDERME ──────────────────────────────
    def alis_emri(self, symbol, adet, fiyat, account_id, brokage_id,
                  order_type="2", time_in_force="0"):
        """
        ALIŞ emri gönder. (ApiCommands: 3)

        order_type: "2" = Limit, "1" = Piyasa
        time_in_force: "0" = Günlük
        OrderSide: 0 = Alış
        TransactionType: "1" = Alım
        """
        emir = {
            "OrderSide": 0,
            "OrderID": None,
            "OrderID2": None,
            "OrderQty": float(adet),
            "OrdStatus": "0",
            "LeavesQty": float(adet),
            "FilledQty": 0.0,
            "AvgPx": 0.0,
            "TradeDate": "0001-01-01T00:00:00",
            "TransactTime": "00:00:00",
            "StopPx": 0.0,
            "Explanation": None,
            "ExpireDate": "0001-01-01T00:00:00",
            "Symbol": symbol,
            "Price": float(fiyat),
            "Quantity": float(adet),
            "IncludeAfterSession": False,
            "OrderType": order_type,
            "TransactionType": "1",
            "AccountId": account_id,
            "BrokageId": brokage_id,
            "ApiCommands": 3
        }
        self._gonder(emir)
        return self._al()

    def satis_emri(self, symbol, adet, fiyat, account_id, brokage_id,
                   order_type="2", time_in_force="0"):
        """
        SATIŞ emri gönder. (ApiCommands: 3)
        OrderSide: 1 = Satış
        TransactionType: "1" = Satım
        """
        emir = {
            "OrderSide": 1,
            "OrderID": None,
            "OrderID2": None,
            "OrderQty": float(adet),
            "OrdStatus": "0",
            "LeavesQty": float(adet),
            "FilledQty": 0.0,
            "AvgPx": 0.0,
            "TradeDate": "0001-01-01T00:00:00",
            "TransactTime": "00:00:00",
            "StopPx": 0.0,
            "Explanation": None,
            "ExpireDate": "0001-01-01T00:00:00",
            "Symbol": symbol,
            "Price": float(fiyat),
            "Quantity": float(adet),
            "IncludeAfterSession": False,
            "OrderType": order_type,
            "TransactionType": "1",
            "AccountId": account_id,
            "BrokageId": brokage_id,
            "ApiCommands": 3
        }
        self._gonder(emir)
        return self._al()

    def emir_iptal(self, order_id, order_id2, symbol, fiyat, adet,
                   account_id, brokage_id):
        """Emir iptal et. (ApiCommands: 4)"""
        emir = {
            "OrderSide": 1,
            "OrderID": order_id,
            "OrderID2": order_id2,
            "OrderQty": float(adet),
            "OrdStatus": "0",
            "LeavesQty": float(adet),
            "FilledQty": 0.0,
            "AvgPx": 0.0,
            "TradeDate": "0001-01-01T00:00:00",
            "TransactTime": "00:00:00",
            "StopPx": 0.0,
            "Explanation": None,
            "ExpireDate": "0001-01-01T00:00:00",
            "Symbol": symbol,
            "Price": float(fiyat),
            "Quantity": float(adet),
            "IncludeAfterSession": False,
            "OrderType": "2",
            "TransactionType": "1",
            "AccountId": account_id,
            "BrokageId": brokage_id,
            "ApiCommands": 4
        }
        self._gonder(emir)
        return self._al()

    def gerceklesen_emirler(self, brokage_id, account_id, exchange_id=4):
        """Gerçekleşen emirleri oku. (ApiCommands: 8)"""
        self._gonder({
            "BrokageId": brokage_id,
            "AccountId": account_id,
            "ExchangeId": exchange_id,
            "ApiCommands": 8
        })
        return self._al()

    def hesap_bilgileri(self, brokage_id, account_id, exchange_id=4):
        """Hesap bilgilerini oku. (ApiCommands: 7)"""
        self._gonder({
            "BrokageId": brokage_id,
            "AccountId": account_id,
            "ExchangeId": exchange_id,
            "ApiCommands": 7
        })
        return self._al()

    def keepalive(self):
        """Bağlantıyı canlı tut. (ApiCommands: 6)"""
        self._gonder({"ApiCommands": 6})


# ════════════════════════════════════════════════════
# KULLANIM ÖRNEĞİ
# ════════════════════════════════════════════════════
if __name__ == "__main__":
    api = AnkaAPI()

    if api.baglan():
        print("\n1. Hesapları listeliyorum...")
        hesaplar = api.hesaplari_listele()
        print(json.dumps(hesaplar, indent=2, ensure_ascii=False) if hesaplar else "Yanıt yok")

        if hesaplar and "Accounts" in hesaplar:
            acc = hesaplar["Accounts"][0]
            brokage = acc["BrokageId"]
            account = acc["AccountIdList"][0]["AccountId"]
            exchange = acc["AccountIdList"][0]["ExchangeId"]

            print(f"\nHesap: {account} | Kurum: {acc['BrokageName']}")

            print("\n2. Pozisyonları okuyorum...")
            poz = api.pozisyonlari_oku(brokage, account, exchange)
            if poz and "PositionResponseList" in poz:
                for p in poz["PositionResponseList"]:
                    if p.get("QtyNet", 0) > 0:
                        print(f"   {p['Symbol']}: {p['QtyNet']} lot @ {p.get('AvgCost',0):.2f} | K/Z: {p.get('PL',0):.2f}")

            print("\n3. Bekleyen emirleri okuyorum...")
            emirler = api.emirleri_oku(brokage, account, exchange)
            print(json.dumps(emirler, indent=2, ensure_ascii=False)[:500] if emirler else "Emir yok")

        api.kapat()
        print("\n✅ Bağlantı kapatıldı")
    else:
        print("IQ açık mı? Port 18890 dinliyor mu?")
