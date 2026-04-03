"""
BOMBA V3 — KONTROL PANELİ
===========================
Tüm robot parametrelerini uzaktan yönet.
Mac'ten, VPS'ten, telefondan — her yerden erişilebilir.

Kullanım:
  streamlit run kontrol_paneli.py --server.port 8501

Uzaktan erişim:
  http://SUNUCU_IP:8501
"""

import streamlit as st
import json
import os
import time
import subprocess
import platform
from datetime import datetime
from pathlib import Path

# --- YAPILANDIRMA ---
IS_WINDOWS = platform.system() == "Windows"
BASE_DIR = Path(__file__).parent

if IS_WINDOWS:
    BRIDGE_FILE = Path(r"C:\Robot\v3_bridge.json")
    BOMBA_FILE = Path(r"C:\Robot\aktif_bombalar.txt")
    PARAMS_FILE = Path(r"C:\Robot\v3_params.json")
else:
    BRIDGE_FILE = BASE_DIR / "data" / "v3_bridge.json"
    BOMBA_FILE = BASE_DIR / "data" / "aktif_bombalar_local.txt"
    PARAMS_FILE = BASE_DIR / "data" / "v3_params.json"

# --- VARSAYILAN PARAMETRELER ---
DEFAULT_PARAMS = {
    "pos_value": 15000,
    "multiplier": 1.0,
    "regime": "MANUAL",
    "symbol_list": "AYEN,KONTR,EREGL,SASA,GESAN",
    "period_minutes": 30,
    "profit_trigger": 1.2,
    "hard_stop": 3.5,
    "trailing_stop": 1.8,
    "rsi_threshold": 50,
    "ema_fast": 10,
    "ema_slow": 20,
    "most_period": 3,
    "most_percent": 2.0,
    "lunch_block": True,
    "closing_exit": True,
    "opening_aggressive": True,
    "robot_active": True,
    "last_update": "",
}


def load_params():
    """Parametre dosyasını oku."""
    if PARAMS_FILE.exists():
        try:
            with open(PARAMS_FILE) as f:
                saved = json.load(f)
            # Eksik parametreleri default ile tamamla
            for k, v in DEFAULT_PARAMS.items():
                if k not in saved:
                    saved[k] = v
            return saved
        except:
            pass
    return DEFAULT_PARAMS.copy()


def save_params(params):
    """Parametreleri kaydet ve bridge dosyasını güncelle."""
    params["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Params dosyasına yaz
    PARAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PARAMS_FILE, "w") as f:
        json.dump(params, f, indent=4, ensure_ascii=False)

    # Bridge dosyasını güncelle (robot bunu okur)
    bridge = {
        "multiplier": params["multiplier"] if params["robot_active"] else 0.0,
        "regime": params["regime"] if params["robot_active"] else "MANUAL_STOP",
        "pos_value": params["pos_value"],
        "profit_trigger": params["profit_trigger"],
        "hard_stop": params["hard_stop"],
        "trailing_stop": params["trailing_stop"],
        "rsi_threshold": params["rsi_threshold"],
        "ema_fast": params["ema_fast"],
        "ema_slow": params["ema_slow"],
        "robot_active": params["robot_active"],
        "last_update": params["last_update"],
    }

    BRIDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(BRIDGE_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(bridge, f, indent=4)
    if BRIDGE_FILE.exists():
        os.remove(str(BRIDGE_FILE))
    os.rename(tmp, str(BRIDGE_FILE))

    # Windows'a kopyala (Mac'teyse)
    if not IS_WINDOWS:
        try:
            mac_path = str(BRIDGE_FILE).replace("/Users/onurbodur/", "\\\\Mac\\Home\\")
            mac_path = mac_path.replace("/", "\\")
            subprocess.run(
                ["prlctl", "exec", "Windows 11", "cmd", "/c",
                 f'copy "{mac_path}" "C:\\Robot\\v3_bridge.json" /Y'],
                timeout=10, capture_output=True)
            # Params dosyasını da kopyala
            mac_params = str(PARAMS_FILE).replace("/Users/onurbodur/", "\\\\Mac\\Home\\")
            mac_params = mac_params.replace("/", "\\")
            subprocess.run(
                ["prlctl", "exec", "Windows 11", "cmd", "/c",
                 f'copy "{mac_params}" "C:\\Robot\\v3_params.json" /Y'],
                timeout=10, capture_output=True)
        except:
            pass

    return True


def update_bomba_list(symbol_list):
    """Bomba listesini güncelle."""
    BOMBA_FILE.parent.mkdir(parents=True, exist_ok=True)
    BOMBA_FILE.write_text(symbol_list)

    if not IS_WINDOWS:
        try:
            subprocess.run(
                ["prlctl", "exec", "Windows 11", "cmd", "/c",
                 f'echo {symbol_list} > C:\\Robot\\aktif_bombalar.txt'],
                timeout=10, capture_output=True)
        except:
            pass


def read_bridge():
    """Mevcut bridge dosyasını oku."""
    if BRIDGE_FILE.exists():
        try:
            with open(BRIDGE_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


# ================================================================
# STREAMLIT ARAYÜZÜ
# ================================================================

st.set_page_config(
    page_title="BOMBA V3 Kontrol Paneli",
    page_icon="🎛️",
    layout="wide",
)

st.title("🎛️ BOMBA V3 — Kontrol Paneli")
st.caption(f"Platform: {'VPS (Windows)' if IS_WINDOWS else 'Mac + Parallels'} | Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")

# Parametreleri yükle
params = load_params()

# --- ÜST BANT: ACİL KONTROLLER ---
col_status, col_stop, col_reset = st.columns([2, 1, 1])

with col_status:
    bridge = read_bridge()
    if bridge:
        regime = bridge.get("regime", "?")
        mult = bridge.get("multiplier", "?")
        color = "🟢" if mult == 1.0 else "🟡" if mult > 0 else "🔴"
        st.metric("Robot Durumu", f"{color} {regime}", f"Çarpan: {mult}")
    else:
        st.metric("Robot Durumu", "⚪ Bridge yok", "Bağlantı kesilmiş")

with col_stop:
    if st.button("🛑 ACİL DURDUR", type="primary", use_container_width=True):
        params["robot_active"] = False
        params["multiplier"] = 0.0
        params["regime"] = "EMERGENCY_STOP"
        save_params(params)
        st.error("Robot DURDURULDU!")
        st.rerun()

with col_reset:
    if st.button("🔄 RESET & BAŞLAT", use_container_width=True):
        params["robot_active"] = True
        params["multiplier"] = 1.0
        params["regime"] = "MANUAL"
        save_params(params)
        st.success("Robot YENİDEN BAŞLATILDI!")
        st.rerun()

st.divider()

# --- ANA BÖLÜM: PARAMETRE YÖNETİMİ ---
tab1, tab2, tab3, tab4 = st.tabs(["💰 Bütçe & Risk", "📊 Teknik Ayarlar", "📋 Sembol Listesi", "📈 Durum"])

with tab1:
    st.subheader("Bütçe & Risk Yönetimi")

    col1, col2 = st.columns(2)

    with col1:
        params["pos_value"] = st.number_input(
            "💰 Pozisyon Bütçesi (TL)",
            min_value=500, max_value=100000, step=500,
            value=int(params["pos_value"]),
            help="Her hisse için max pozisyon değeri"
        )

        params["multiplier"] = st.slider(
            "📊 Çarpan (Multiplier)",
            min_value=0.0, max_value=2.0, step=0.1,
            value=float(params["multiplier"]),
            help="0=Durdur, 0.5=Yarı, 1.0=Normal, 1.5=Agresif"
        )

    with col2:
        params["hard_stop"] = st.number_input(
            "🛑 Hard Stop (%)",
            min_value=0.5, max_value=10.0, step=0.5,
            value=float(params["hard_stop"]),
            help="Sabit stop-loss yüzdesi"
        )

        params["trailing_stop"] = st.number_input(
            "📉 Trailing Stop (%)",
            min_value=0.1, max_value=5.0, step=0.1,
            value=float(params["trailing_stop"]),
            help="Zirveden dönüş stop yüzdesi"
        )

        params["profit_trigger"] = st.number_input(
            "🎯 Kâr Tetikleyici (%)",
            min_value=0.1, max_value=5.0, step=0.1,
            value=float(params["profit_trigger"]),
            help="Bu kâr sonrası trailing stop aktif olur"
        )

    # Rejim seçimi
    params["regime"] = st.selectbox(
        "🎭 Rejim",
        ["MANUAL", "BULL", "BEAR", "SIDEWAYS", "TURBO_TEST", "DANGER_CRASH"],
        index=["MANUAL", "BULL", "BEAR", "SIDEWAYS", "TURBO_TEST", "DANGER_CRASH"].index(params.get("regime", "MANUAL")),
        help="DANGER_CRASH = tüm alımlar bloke"
    )

    params["robot_active"] = st.toggle("🤖 Robot Aktif", value=params["robot_active"])

with tab2:
    st.subheader("Teknik İndikatör Ayarları")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**EMA (Hareketli Ortalama)**")
        params["ema_fast"] = st.number_input("Hızlı EMA", min_value=2, max_value=50, value=int(params["ema_fast"]))
        params["ema_slow"] = st.number_input("Yavaş EMA", min_value=5, max_value=100, value=int(params["ema_slow"]))

    with col2:
        st.markdown("**RSI**")
        params["rsi_threshold"] = st.number_input("RSI Eşiği", min_value=30, max_value=70, value=int(params["rsi_threshold"]))

    with col3:
        st.markdown("**MOST**")
        params["most_period"] = st.number_input("MOST Periyot", min_value=1, max_value=20, value=int(params["most_period"]))
        params["most_percent"] = st.number_input("MOST Yüzde", min_value=0.5, max_value=5.0, step=0.5, value=float(params["most_percent"]))

    st.divider()

    st.markdown("**Periyot**")
    period_options = {"5 Dakika": 5, "15 Dakika": 15, "30 Dakika": 30, "60 Dakika": 60}
    selected_period = st.selectbox("Bar Periyodu", list(period_options.keys()),
        index=list(period_options.values()).index(params.get("period_minutes", 30)))
    params["period_minutes"] = period_options[selected_period]

    st.warning("⚠️ Periyot ve indikatör değişiklikleri robot yeniden derlenince aktif olur. Bütçe ve stop değerleri anında uygulanır.")

    col1, col2, col3 = st.columns(3)
    with col1:
        params["lunch_block"] = st.toggle("🍽️ Öğlen Bloğu", value=params.get("lunch_block", True))
    with col2:
        params["closing_exit"] = st.toggle("🌅 Kapanış Çıkışı", value=params.get("closing_exit", True))
    with col3:
        params["opening_aggressive"] = st.toggle("🌅 Açılış Agresif", value=params.get("opening_aggressive", True))

with tab3:
    st.subheader("Sembol Listesi Yönetimi")

    current_list = params.get("symbol_list", "AYEN,KONTR,EREGL,SASA,GESAN")

    # Mevcut liste
    st.markdown(f"**Mevcut:** `{current_list}`")

    # Yeni liste
    new_list = st.text_input("Sembol Listesi (virgülle ayır)", value=current_list)
    params["symbol_list"] = new_list.upper().strip()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Listeyi Güncelle", use_container_width=True):
            update_bomba_list(params["symbol_list"])
            st.success(f"Liste güncellendi: {params['symbol_list']}")

    with col2:
        if st.button("🔍 Yeni Bomba Tara", use_container_width=True):
            with st.spinner("ML taraması yapılıyor..."):
                try:
                    result = subprocess.run(
                        ["python", "-c", """
import sys; sys.path.insert(0,'.')
from otonom_trader import gorev_08_30_tarama
gorev_08_30_tarama()
"""],
                        capture_output=True, text=True, timeout=180,
                        cwd=str(BASE_DIR))
                    st.code(result.stdout[-500:] if result.stdout else "Çıktı yok")
                except Exception as e:
                    st.error(f"Hata: {e}")

    # Hızlı ekleme
    st.markdown("**Hızlı Ekle/Çıkar:**")
    popular = ["GARAN", "THYAO", "ASELS", "TUPRS", "EREGL", "SISE", "TOASO", "AKBNK", "YKBNK", "HALKB",
               "AYEN", "KONTR", "SASA", "AKSEN", "OTKAR", "GESAN", "TKFEN", "ENJSA", "TSKB", "SAHOL"]

    current_symbols = [s.strip() for s in params["symbol_list"].split(",")]
    cols = st.columns(5)
    for i, sym in enumerate(popular):
        with cols[i % 5]:
            is_active = sym in current_symbols
            if st.checkbox(sym, value=is_active, key=f"sym_{sym}"):
                if sym not in current_symbols:
                    current_symbols.append(sym)
            else:
                if sym in current_symbols:
                    current_symbols.remove(sym)

    params["symbol_list"] = ",".join([s for s in current_symbols if s])

with tab4:
    st.subheader("Sistem Durumu")

    # Bridge durumu
    bridge = read_bridge()
    if bridge:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Çarpan", bridge.get("multiplier", "?"))
        with col2:
            st.metric("Rejim", bridge.get("regime", "?"))
        with col3:
            st.metric("Bütçe", f"{bridge.get('pos_value', '?')} TL")
        with col4:
            st.metric("Son Güncelleme", bridge.get("last_update", "?"))

        # Ham JSON
        with st.expander("Ham Bridge JSON"):
            st.json(bridge)
    else:
        st.warning("Bridge dosyası bulunamadı")

    # Risk motoru
    st.markdown("**Risk Motoru:**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Risk Motorunu Başlat"):
            subprocess.Popen(
                ["python", "v3_risk_motor.py"],
                cwd=str(BASE_DIR),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            st.success("Risk motoru başlatıldı")
    with col2:
        if st.button("⏹️ Risk Motorunu Durdur"):
            os.system("pkill -f v3_risk_motor")
            st.success("Risk motoru durduruldu")

    # Log dosyası
    log_file = BASE_DIR / "data" / "motor_v3_log.json"
    if log_file.exists():
        with st.expander("Son Loglar"):
            try:
                with open(log_file) as f:
                    logs = json.load(f)
                for entry in logs[-20:]:
                    st.text(f"{entry['zaman']} [{entry['seviye']}] {entry['mesaj']}")
            except:
                st.warning("Log okunamadı")

# --- KAYDET BUTONU ---
st.divider()
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("💾 KAYDET & UYGULA", type="primary", use_container_width=True):
        if save_params(params):
            update_bomba_list(params["symbol_list"])
            st.success("✅ Tüm parametreler kaydedildi ve robota gönderildi!")
            st.balloons()
        else:
            st.error("Kaydetme başarısız!")

# --- FOOTER ---
st.divider()
st.caption(f"BOMBA V3 Kontrol Paneli | {datetime.now().strftime('%d.%m.%Y %H:%M')} | {'VPS' if IS_WINDOWS else 'Mac'}")
