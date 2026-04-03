import yfinance as yf
import json
import time
import os
import platform
import subprocess

# --- YOLLAR ---
IS_WINDOWS = platform.system() == "Windows"
LOCAL_BRIDGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "v3_bridge.json")
WIN_BRIDGE = r"C:\Robot\v3_bridge.json"

# Global değişkenler
last_known_vix = 20.0
last_known_usdtry_change = 0.0
POS_VALUE = 16000  # ← BÜTÇE: Bu değeri değiştir, robot otomatik alır

def get_master_risk():
    global last_known_vix, last_known_usdtry_change
    try:
        # 1. XU100 Endeks Analizi
        xu100 = yf.download("XU100.IS", period="5d", progress=False)
        if not xu100.empty and len(xu100) >= 2:
            xu100_change = float((xu100['Close'].iloc[-1] / xu100['Close'].iloc[-2] - 1) * 100)
        else:
            xu100_change = 0.0

        # 2. Global Risk (VIX) - Gece/Hafta sonu boş gelirse son değeri kullan
        vix_df = yf.download("^VIX", period="1d", interval="1m", progress=False)
        if not vix_df.empty:
            last_known_vix = float(vix_df['Close'].iloc[-1])

        # 3. Döviz Şoku (USD/TRY) - Period 5d ve interval 15m
        usd = yf.download("USDTRY=X", period="5d", interval="15m", progress=False)
        if not usd.empty and len(usd) > 1:
            last_known_usdtry_change = float((usd['Close'].iloc[-1] / usd['Close'].iloc[-2] - 1) * 100)

        # --- KARAR MOTORU ---
        multiplier = 1.0
        risk_status = "SIDEWAYS"

        if xu100_change < -0.5: risk_status = "BEAR"
        elif xu100_change > 0.5: risk_status = "BULL"

        if xu100_change < -1.0 or last_known_vix > 30:
            multiplier = 0.0
            risk_status = "DANGER_CRASH"
        elif last_known_usdtry_change > 0.8:
            multiplier = 0.5
            risk_status = "CAUTION_CURRENCY"

        # Mevcut bridge'deki dry_run'ı koru — üzerine yazma
        mevcut_dry_run = False
        try:
            import json as _json
            mevcut = _json.load(open(LOCAL_BRIDGE))
            mevcut_dry_run = mevcut.get("dry_run", False)
        except:
            pass

        return {
            "multiplier": round(float(multiplier), 2),
            "regime": risk_status,
            "xu100_change": round(float(xu100_change), 2),
            "vix": round(last_known_vix, 2),
            "usd_change": round(last_known_usdtry_change, 2),
            "dry_run": mevcut_dry_run,
            "pos_value": POS_VALUE,
            "last_update": time.strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"⚠️ Hata: {e}")
        return None

def save_to_bridge(data):
    json_str = json.dumps(data, indent=4)

    # Lokale yaz
    os.makedirs(os.path.dirname(LOCAL_BRIDGE), exist_ok=True)
    tmp = LOCAL_BRIDGE + ".tmp"
    with open(tmp, 'w') as f:
        f.write(json_str)
    if os.path.exists(LOCAL_BRIDGE): os.remove(LOCAL_BRIDGE)
    os.rename(tmp, LOCAL_BRIDGE)

    # Windows'a kopyala
    if IS_WINDOWS:
        os.makedirs(os.path.dirname(WIN_BRIDGE), exist_ok=True)
        with open(WIN_BRIDGE, 'w') as f:
            f.write(json_str)
    else:
        try:
            mac_path = LOCAL_BRIDGE.replace("/Users/onurbodur/", "\\\\Mac\\Home\\")
            mac_path = mac_path.replace("/", "\\")
            subprocess.run(
                ["prlctl", "exec", "Windows 11", "cmd", "/c",
                 f'copy "{mac_path}" "{WIN_BRIDGE}" /Y'],
                timeout=10, capture_output=True)
        except:
            pass

    print(f"[{data['last_update']}] REJİM: {data['regime']} | XU100: %{data['xu100_change']} | VIX: {data['vix']} | ÇARPAN: {data['multiplier']}")

# --- ANA DÖNGÜ ---
print("🛡️ BOMBA_V3 Risk Motoru Aktif...")
data = get_master_risk()
if data:
    save_to_bridge(data)
    print("✅ İlk veri yazıldı")
else:
    print("❌ İlk veri alınamadı")

while True:
    time.sleep(60)
    data = get_master_risk()
    if data: save_to_bridge(data)
