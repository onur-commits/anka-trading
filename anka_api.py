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
import os
from datetime import datetime
from pathlib import Path


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
            # Eski soketi temizle
            self.kapat()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            # JSON modu seç
            self._gonder({"SetMessageType0": "MessageType"})
            # Handshake yanıtını oku (buffer'da kalmasın)
            self._al(timeout=3)
            print(f"✅ IQ'ya bağlandı ({self.host}:{self.port})")
            return True
        except Exception as e:
            print(f"❌ Bağlantı hatası: {e}")
            self.sock = None
            return False

    def kapat(self):
        """Bağlantıyı kapat."""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _ensure_conn(self):
        """Soket kapalıysa otomatik yeniden bağlan. True = hazır, False = bağlanamadım."""
        if self.sock is None:
            return self.baglan()
        return True

    def _gonder(self, data):
        """JSON paketi gönder + char(11) sonlandırıcı. Kapalıysa otomatik yeniden bağlan."""
        if not self._ensure_conn():
            raise ConnectionError("IQ TCP bağlantı kurulamadı")
        paket = json.dumps(data) + self.TERMINATOR
        try:
            self.sock.sendall(paket.encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            # Yeniden bağlanmayı dene — 1 kere
            print(f"⚠️ _gonder() soket kırıldı ({e}), yeniden bağlanılıyor...")
            self.sock = None
            if not self._ensure_conn():
                raise ConnectionError(f"IQ yeniden bağlantı kurulamadı: {e}")
            self.sock.sendall(paket.encode('utf-8'))

    def _al(self, timeout=5):
        """Yanıt al."""
        if not self.sock:
            print("⚠️ _al() çağrıldı ama socket yok")
            return None
        self.sock.settimeout(timeout)
        try:
            buf = b""
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    # Karşı taraf bağlantıyı kapattı
                    print("⚠️ Socket kapandı (recv 0 byte)")
                    self.sock = None
                    break
                buf += chunk
                if chr(11) in buf.decode('utf-8', errors='ignore'):
                    break
            text = buf.decode('utf-8', errors='ignore').replace(chr(11), '')
            return json.loads(text) if text.strip() else None
        except socket.timeout:
            print(f"⚠️ _al() timeout ({timeout}s)")
            return None
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"⚠️ _al() socket hatası: {e}")
            self.sock = None
            return None
        except json.JSONDecodeError as e:
            print(f"⚠️ _al() JSON parse hatası: {e}")
            return None
        except Exception as e:
            print(f"⚠️ _al() beklenmeyen hata: {e}")
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
    def alis_emri(self, symbol, adet, fiyat=0, account_id=None, brokage_id=None,
                  order_type="1", time_in_force="0", client_order_id=None):
        """
        ALIŞ emri gönder. (ApiCommands: 3)

        order_type: "1" = Piyasa (default), "2" = Limit
        time_in_force: "0" = Günlük
        OrderSide: 0 = Alış
        TransactionType: "1" = Normal

        fiyat=0 ile market order gönderilir (anında gerçekleşir).
        fiyat>0 ve order_type="2" ile limit order gönderilir.
        """
        import time as _time
        if client_order_id is None:
            client_order_id = f"ANKA_{symbol}_{int(_time.time())}"
        if account_id is None:
            account_id = "0~2205905"
        if brokage_id is None:
            brokage_id = "115"
        # fiyat verilmişse ve order_type default ise, limit yap
        if fiyat > 0 and order_type == "1":
            order_type = "2"
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
            "ClientOrderID": client_order_id,
            "AccountId": account_id,
            "BrokageId": brokage_id,
            "ExchangeId": 4,
            "ValidityType": 0,
            "ApiCommands": 3
        }
        self._gonder(emir)
        return self._al()

    def satis_emri(self, symbol, adet, fiyat=0, account_id=None, brokage_id=None,
                   order_type="1", time_in_force="0", client_order_id=None):
        """
        SATIŞ emri gönder. (ApiCommands: 3)
        OrderSide: 1 = Satış
        TransactionType: "1" = Normal

        fiyat=0 ile market order (default), fiyat>0 ile limit order.
        """
        import time as _time
        if client_order_id is None:
            client_order_id = f"ANKA_S_{symbol}_{int(_time.time())}"
        if account_id is None:
            account_id = "0~2205905"
        if brokage_id is None:
            brokage_id = "115"
        if fiyat > 0 and order_type == "1":
            order_type = "2"
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
            "ClientOrderID": client_order_id,
            "AccountId": account_id,
            "BrokageId": brokage_id,
            "ExchangeId": 4,
            "ValidityType": 0,
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

    # ── BOMBA ROBOT LOG TOPLAMA (SORUN-009) ────────────
    def robot_durum_sorgula(self):
        """Aktif robotların durumunu IQ üzerinden sorgula.
        Hesap bilgileri + pozisyonlar + emirler üzerinden robot aktivitesini tespit eder.
        """
        sonuc = {
            "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "baglanti": False,
            "hesaplar": [],
            "pozisyonlar": [],
            "bekleyen_emirler": [],
            "gerceklesen_emirler": [],
            "hatalar": [],
        }

        try:
            if not self.baglan():
                sonuc["hatalar"].append("IQ baglanti kurulamadi")
                return sonuc

            sonuc["baglanti"] = True

            # Hesaplari al
            hesaplar = self.hesaplari_listele()
            if hesaplar and "Accounts" in hesaplar:
                for acc in hesaplar["Accounts"]:
                    brokage = acc.get("BrokageId")
                    for aid in acc.get("AccountIdList", []):
                        account_id = aid.get("AccountId")
                        exchange_id = aid.get("ExchangeId", 4)
                        sonuc["hesaplar"].append({
                            "brokage": brokage,
                            "account": account_id,
                            "exchange": exchange_id,
                            "kurum": acc.get("BrokageName", ""),
                        })

                        # Pozisyonlari oku
                        try:
                            poz = self.pozisyonlari_oku(brokage, account_id, exchange_id)
                            if poz and "PositionResponseList" in poz:
                                for p in poz["PositionResponseList"]:
                                    if p.get("QtyNet", 0) != 0:
                                        sonuc["pozisyonlar"].append({
                                            "symbol": p.get("Symbol"),
                                            "adet": p.get("QtyNet", 0),
                                            "maliyet": p.get("AvgCost", 0),
                                            "kar_zarar": p.get("PL", 0),
                                        })
                        except Exception as e:
                            sonuc["hatalar"].append(f"Pozisyon okuma: {e}")

                        # Bekleyen emirler
                        try:
                            emirler = self.emirleri_oku(brokage, account_id, exchange_id)
                            if emirler and "OrderResponseList" in emirler:
                                for em in emirler["OrderResponseList"]:
                                    sonuc["bekleyen_emirler"].append({
                                        "symbol": em.get("Symbol"),
                                        "yon": "ALIS" if em.get("OrderSide") == 0 else "SATIS",
                                        "adet": em.get("OrderQty", 0),
                                        "fiyat": em.get("Price", 0),
                                    })
                        except Exception as e:
                            sonuc["hatalar"].append(f"Emir okuma: {e}")

                        # Gerceklesen emirler
                        try:
                            gercek = self.gerceklesen_emirler(brokage, account_id, exchange_id)
                            if gercek and "OrderResponseList" in gercek:
                                for em in gercek["OrderResponseList"]:
                                    sonuc["gerceklesen_emirler"].append({
                                        "symbol": em.get("Symbol"),
                                        "yon": "ALIS" if em.get("OrderSide") == 0 else "SATIS",
                                        "adet": em.get("FilledQty", 0),
                                        "fiyat": em.get("AvgPx", 0),
                                    })
                        except Exception as e:
                            sonuc["hatalar"].append(f"Gerceklesen okuma: {e}")

            self.kapat()

        except Exception as e:
            sonuc["hatalar"].append(f"Genel hata: {e}")
            self.kapat()

        return sonuc

    def bomba_robot_log_topla(self, data_dir=None):
        """Bomba robotlarinin durumunu sorgula ve data/bomba_robot_log.json'a yaz.
        Muhendis modulu ile uyumlu log formati kullanir.

        Returns:
            dict: Toplanan log verisi veya hata bilgisi.
        """
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        else:
            data_dir = Path(data_dir)
        data_dir.mkdir(exist_ok=True)

        log_dosya = data_dir / "bomba_robot_log.json"
        aktif_dosya = data_dir / "aktif_bombalar.txt"

        # Aktif bomba listesini oku
        aktif_bombalar = []
        if aktif_dosya.exists():
            try:
                icerik = aktif_dosya.read_text(encoding="utf-8").strip()
                if icerik:
                    aktif_bombalar = [s.strip() for s in icerik.split(",") if s.strip()]
            except Exception:
                pass

        # IQ'dan durum sorgula
        durum = self.robot_durum_sorgula()

        # Bomba hisseleriyle eslesen pozisyon/emir bilgilerini filtrele
        bomba_pozisyonlar = [
            p for p in durum.get("pozisyonlar", [])
            if p.get("symbol", "").replace(".E", "") in aktif_bombalar
        ]
        bomba_emirler = [
            e for e in durum.get("bekleyen_emirler", [])
            if e.get("symbol", "").replace(".E", "") in aktif_bombalar
        ]
        bomba_gerceklesen = [
            e for e in durum.get("gerceklesen_emirler", [])
            if e.get("symbol", "").replace(".E", "") in aktif_bombalar
        ]

        # Log girdisi olustur (muhendis formatiyla uyumlu)
        log_entry = {
            "zaman": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "seviye": "INFO" if durum["baglanti"] else "WARNING",
            "kategori": "BOMBA_ROBOT",
            "mesaj": f"Robot log toplandi: {len(aktif_bombalar)} aktif bomba, "
                     f"{len(bomba_pozisyonlar)} pozisyon, "
                     f"{len(bomba_emirler)} bekleyen emir, "
                     f"{len(bomba_gerceklesen)} gerceklesen",
            "detay": {
                "aktif_bombalar": aktif_bombalar,
                "iq_baglanti": durum["baglanti"],
                "pozisyonlar": bomba_pozisyonlar,
                "bekleyen_emirler": bomba_emirler,
                "gerceklesen_emirler": bomba_gerceklesen,
                "hatalar": durum.get("hatalar", []),
            }
        }

        # Mevcut loglara ekle (son 500 kayit tut)
        logs = []
        try:
            if log_dosya.exists():
                with open(log_dosya, encoding="utf-8") as f:
                    logs = json.load(f)
        except (json.JSONDecodeError, Exception):
            logs = []

        logs.append(log_entry)
        logs = logs[-500:]

        try:
            with open(log_dosya, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=1)
        except Exception as e:
            log_entry["hatalar"] = [f"Log yazma hatasi: {e}"]

        return log_entry


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
