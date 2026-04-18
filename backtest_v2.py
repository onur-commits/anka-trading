"""
ANKA Backtest v2 — Gerçekçi geçmiş simülasyon
==============================================

Veri kaynakları (data/ altında):
  - price_history_1h.csv  : Binance spot 1h OHLCV (365 gün)
  - fear_greed_history.csv: alternative.me günlük F&G (730 gün)
  - funding_history.csv   : Binance futures funding rate (365 gün, 8h/4h)

Skor formülü (coin bot c7d5edc commit'inden):
  SKOR = TEK*0.30 + HAC*0.20 + MAK*0.15 + LIK*0.10 + SEN*0.15 + FUN*0.10 ± COR

Bu backtest sadece SEN (sentiment=F&G) ve FUN (funding) için gerçek veri
kullanır; TEK/HAC/MAK/LIK için fiyat+volume'den türetilmiş basit proksi
skorlar hesaplar. Amaç: "SEN ve FUN'u dahil etmek getiriyi nasıl değiştirir?"
sorusunu cevaplamak.

Simülasyon kuralları:
  - Spot alım/satım, sadece long
  - MIN_SKOR_AL = 65 (c7d5edc)
  - Stop: -%7 sabit (ATR yerine basit), Trailing: +%3 üstünden -%3
  - TP1: +%8'de yarısını sat, TP2: +%15'te tamamen kapat
  - Komisyon: %0.1 (Binance spot maker/taker)
  - Slippage: %0.1 (paper_trader MarketFriction varsayılanı)
  - Max pozisyon: 5, pozisyon başına sermaye: toplam/5
  - Başlangıç: $2500 (yaklaşık kullanıcının toplam portföy değeri)

Karşılaştırma: üç strateji çalıştırılır
  A) "Baseline" — sadece teknik + hacim (SEN=FUN=0)
  B) "v2 Full" — tüm sinyaller dahil (SEN + FUN)
  C) "v2 + Kontrarian" — F&G aşırı korku için bonus, aşırı açgözlülük için ceza

Çıktı: data/backtest_v2_rapor.md
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
PRICE_CSV = DATA_DIR / "price_history_1h.csv"
FG_CSV = DATA_DIR / "fear_greed_history.csv"
FUNDING_CSV = DATA_DIR / "funding_history.csv"
REPORT_MD = DATA_DIR / "backtest_v2_rapor.md"

# ---------- Config (coin_otonom_trader.py'den) --------------------------------

MIN_SKOR_AL = 65
STOP_LOSS_PCT = 7.0
TRAILING_BASLA_PCT = 3.0
TRAILING_GERI_PCT = 3.0
TAKE_PROFIT_1_PCT = 8.0
TAKE_PROFIT_2_PCT = 15.0
KOMISYON_PCT = 0.1   # tek yön
SLIPPAGE_PCT = 0.1   # tek yön
MAX_POZISYON = 5
BASLANGIC_SERMAYE = 2500.0

SYMBOLS = ["BNBUSDT", "ATOMUSDT", "BTCUSDT", "MOVRUSDT"]

# ---------- Veri yükleme ------------------------------------------------------


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fiyatlari_yukle() -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with open(PRICE_CSV) as f:
        r = csv.DictReader(f)
        for row in r:
            data[row["symbol"]].append(
                {
                    "dt": _parse_iso(row["datetime"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
            )
    for sym in data:
        data[sym].sort(key=lambda x: x["dt"])
    return dict(data)


def fg_yukle() -> dict[str, int]:
    out: dict[str, int] = {}
    with open(FG_CSV) as f:
        r = csv.DictReader(f)
        for row in r:
            out[row["date"]] = int(row["value"])
    return out


def funding_yukle() -> dict[str, list[tuple[datetime, float]]]:
    out: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    with open(FUNDING_CSV) as f:
        r = csv.DictReader(f)
        for row in r:
            out[row["symbol"]].append((_parse_iso(row["datetime"]), float(row["funding_rate"])))
    for sym in out:
        out[sym].sort(key=lambda x: x[0])
    return dict(out)


# ---------- İndikatörler ------------------------------------------------------


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(values: list[float], period: int = 14) -> list[float]:
    if len(values) < period + 1:
        return [50.0] * len(values)
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    out = [50.0] * (period + 1)
    for i in range(period, len(deltas)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
        rs = avg_g / avg_l if avg_l > 0 else 100
        out.append(100 - 100 / (1 + rs))
    # align to values length
    while len(out) < len(values):
        out.append(out[-1])
    return out[: len(values)]


# ---------- Skor hesaplama ----------------------------------------------------


def tek_skor_serisi(closes: list[float]) -> list[float]:
    """Tüm bar için teknik skor: RSI + EMA eğimi. 0-100."""
    n = len(closes)
    if n < 50:
        return [50.0] * n
    r_series = rsi(closes)
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    out: list[float] = []
    for i in range(n):
        if i < 30:
            out.append(50.0)
            continue
        r = r_series[i]
        rsi_score = max(0, min(100, (r - 30) * (100 / 40)))
        trend_bonus = 15 if ema20[i] > ema50[i] else -10
        out.append(max(0, min(100, rsi_score + trend_bonus)))
    return out


def hac_skor_serisi(volumes: list[float]) -> list[float]:
    n = len(volumes)
    out = [50.0] * n
    if n < 25:
        return out
    # rolling sum with cumulative
    csum = [0.0]
    for v in volumes:
        csum.append(csum[-1] + v)
    for i in range(24, n):
        ort = (csum[i] - csum[i - 24]) / 24
        if ort <= 0:
            continue
        ratio = volumes[i] / ort
        out[i] = max(0, min(100, 50 + (ratio - 1) * 25))
    return out


def lik_skor_serisi(volumes_usd: list[float]) -> list[float]:
    n = len(volumes_usd)
    out = [50.0] * n
    if n < 25:
        return out
    csum = [0.0]
    for v in volumes_usd:
        csum.append(csum[-1] + v)
    for i in range(24, n):
        son24 = csum[i] - csum[i - 24]
        if son24 > 100_000_000:
            out[i] = 100
        elif son24 > 10_000_000:
            out[i] = 60 + (son24 - 10_000_000) / 90_000_000 * 40
        elif son24 > 1_000_000:
            out[i] = 30 + (son24 - 1_000_000) / 9_000_000 * 30
        else:
            out[i] = max(0, son24 / 1_000_000 * 30)
    return out


def mak_skor(fg: int) -> float:
    """Makro proksi — F&G'nin oynaklık bölgesini kullan (25-75 normal)."""
    # Aşırı korku/açgözlülük makro riskli, orta bölge sakin
    dist = abs(fg - 50)
    return max(0, 100 - dist * 2)


def sen_skor(fg: int, kontrarian: bool = False) -> float:
    """Sentiment — F&G. Kontrarian: aşırı korku = fırsat, aşırı açgözlülük = risk."""
    if kontrarian:
        # 0-20: +90, 20-40: +70, 40-60: 50, 60-80: 30, 80-100: 10
        if fg <= 20:
            return 90
        if fg <= 40:
            return 70
        if fg <= 60:
            return 50
        if fg <= 80:
            return 30
        return 10
    # Trend-following: yüksek F&G = momentum
    return fg


def fun_skor(funding: float) -> float:
    """Funding rate — negatif funding = short sıkışması, long fırsatı."""
    # Funding rate 8h'lik (BNB/ATOM/BTC) veya 4h'lik (MOVR), %0.01 normal
    # Aşırı pozitif (>0.05%) short taraf sıkışmış (long açgözlü) — ceza
    # Aşırı negatif (<-0.02%) long sıkışmış — fırsat
    if funding < -0.0002:
        return 80
    if funding < 0:
        return 65
    if funding < 0.0002:
        return 50
    if funding < 0.0005:
        return 35
    return 20


def funding_at_time(funding_list: list[tuple[datetime, float]], dt: datetime) -> float:
    """dt'den önceki en son funding rate (binary search)."""
    if not funding_list:
        return 0.0
    lo, hi = 0, len(funding_list) - 1
    if funding_list[0][0] > dt:
        return 0.0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if funding_list[mid][0] <= dt:
            lo = mid
        else:
            hi = mid - 1
    return funding_list[lo][1]


# ---------- Simülatör ---------------------------------------------------------


@dataclass
class Pozisyon:
    sembol: str
    giris_fiyat: float
    giris_dt: datetime
    miktar: float  # coin cinsinden
    kalan_miktar: float
    en_yuksek: float
    tp1_alindi: bool = False
    stop_fiyat: float = 0.0


@dataclass
class Sonuc:
    strateji: str
    baslangic: float
    bitis: float
    toplam_getiri_pct: float
    islem_sayisi: int
    kazanan: int
    kaybeden: int
    winrate: float
    ort_kazanc_pct: float
    ort_kayip_pct: float
    max_drawdown_pct: float
    sharpe_benzeri: float
    trade_log: list[dict[str, Any]] = field(default_factory=list)


def backtest_calistir(
    strateji: str,
    fiyatlar: dict[str, list[dict[str, Any]]],
    fg: dict[str, int],
    funding: dict[str, list[tuple[datetime, float]]],
    kontrarian: bool = False,
    sen_fun_acik: bool = True,
) -> Sonuc:
    # Tüm sembolleri zamanda birleştir
    nakit = BASLANGIC_SERMAYE
    pozisyonlar: dict[str, Pozisyon] = {}
    equity_curve: list[tuple[datetime, float]] = []
    trade_log: list[dict[str, Any]] = []
    kazanan = kaybeden = 0
    kazanc_yuzdeler: list[float] = []
    kayip_yuzdeler: list[float] = []

    # Ortak zaman çizgisi — BNBUSDT baz alsın (en uzun, tam veri)
    if "BNBUSDT" not in fiyatlar:
        raise RuntimeError("BNBUSDT fiyat verisi yok")
    timeline = [x["dt"] for x in fiyatlar["BNBUSDT"]]

    # Sembol→index mapper (hızlı lookup için)
    sym_index: dict[str, dict[datetime, int]] = {
        s: {bar["dt"]: i for i, bar in enumerate(fiyatlar[s])} for s in fiyatlar
    }

    # Ön-hesaplanan skor serileri (performans)
    tek_cache: dict[str, list[float]] = {}
    hac_cache: dict[str, list[float]] = {}
    lik_cache: dict[str, list[float]] = {}
    for s in fiyatlar:
        closes = [b["close"] for b in fiyatlar[s]]
        vols = [b["volume"] for b in fiyatlar[s]]
        vols_usd = [b["volume"] * b["close"] for b in fiyatlar[s]]
        tek_cache[s] = tek_skor_serisi(closes)
        hac_cache[s] = hac_skor_serisi(vols)
        lik_cache[s] = lik_skor_serisi(vols_usd)

    for dt in timeline:
        gun_str = dt.strftime("%Y-%m-%d")
        fg_deger = fg.get(gun_str, 50)

        # 1) Açık pozisyonları yönet (her saat)
        for sym, poz in list(pozisyonlar.items()):
            if sym not in sym_index or dt not in sym_index[sym]:
                continue
            bar = fiyatlar[sym][sym_index[sym][dt]]
            fiyat = bar["close"]
            high = bar["high"]
            low = bar["low"]

            if high > poz.en_yuksek:
                poz.en_yuksek = high

            # Stop-loss kontrolü (low düşüşte)
            stop_tetiklendi = low <= poz.stop_fiyat

            # TP1
            tp1_fiyat = poz.giris_fiyat * (1 + TAKE_PROFIT_1_PCT / 100)
            # TP2
            tp2_fiyat = poz.giris_fiyat * (1 + TAKE_PROFIT_2_PCT / 100)

            sat_fiyat: float | None = None
            sat_sebep = ""
            sat_miktar = 0.0

            if stop_tetiklendi:
                sat_fiyat = poz.stop_fiyat
                sat_miktar = poz.kalan_miktar
                sat_sebep = "STOP"
            elif not poz.tp1_alindi and high >= tp1_fiyat:
                # Yarısını sat
                sat_fiyat = tp1_fiyat
                sat_miktar = poz.kalan_miktar / 2
                sat_sebep = "TP1"
                poz.tp1_alindi = True
                # Trailing başlat
                if poz.en_yuksek * (1 - TRAILING_GERI_PCT / 100) > poz.stop_fiyat:
                    poz.stop_fiyat = poz.en_yuksek * (1 - TRAILING_GERI_PCT / 100)
            elif high >= tp2_fiyat:
                sat_fiyat = tp2_fiyat
                sat_miktar = poz.kalan_miktar
                sat_sebep = "TP2"
            else:
                # Trailing güncelle
                if poz.en_yuksek >= poz.giris_fiyat * (1 + TRAILING_BASLA_PCT / 100):
                    yeni_stop = poz.en_yuksek * (1 - TRAILING_GERI_PCT / 100)
                    if yeni_stop > poz.stop_fiyat:
                        poz.stop_fiyat = yeni_stop

            if sat_fiyat is not None and sat_miktar > 0:
                etkin_fiyat = sat_fiyat * (1 - SLIPPAGE_PCT / 100)
                gelir = etkin_fiyat * sat_miktar * (1 - KOMISYON_PCT / 100)
                maliyet_kismi = poz.giris_fiyat * sat_miktar
                kar = gelir - maliyet_kismi
                kar_pct = (kar / maliyet_kismi) * 100
                nakit += gelir
                poz.kalan_miktar -= sat_miktar
                trade_log.append(
                    {
                        "dt": dt.isoformat(),
                        "sembol": sym,
                        "yon": "SAT",
                        "fiyat": round(etkin_fiyat, 6),
                        "miktar": round(sat_miktar, 6),
                        "sebep": sat_sebep,
                        "kar_pct": round(kar_pct, 2),
                    }
                )
                if poz.kalan_miktar <= 1e-9:
                    # pozisyon kapandı — toplam kar/zarar bu trade serisi üzerinden
                    if kar_pct > 0:
                        kazanan += 1
                        kazanc_yuzdeler.append(kar_pct)
                    else:
                        kaybeden += 1
                        kayip_yuzdeler.append(kar_pct)
                    del pozisyonlar[sym]

        # 2) Yeni alım sinyali ara (max pozisyon limiti altındaysak)
        if len(pozisyonlar) < MAX_POZISYON:
            adaylar: list[tuple[str, float]] = []
            for sym in SYMBOLS:
                if sym in pozisyonlar:
                    continue
                if sym not in sym_index or dt not in sym_index[sym]:
                    continue
                idx = sym_index[sym][dt]
                if idx < 50:
                    continue
                tek = tek_cache[sym][idx]
                hac = hac_cache[sym][idx]
                mak = mak_skor(fg_deger)
                lik = lik_cache[sym][idx]
                if sen_fun_acik:
                    sen = sen_skor(fg_deger, kontrarian=kontrarian)
                    f_rate = funding_at_time(funding.get(sym, []), dt)
                    fun = fun_skor(f_rate)
                else:
                    sen = 50.0
                    fun = 50.0
                # Korelasyon düzeltmesi basitleştirildi — 0
                skor = tek * 0.30 + hac * 0.20 + mak * 0.15 + lik * 0.10 + sen * 0.15 + fun * 0.10
                if skor >= MIN_SKOR_AL:
                    adaylar.append((sym, skor))

            # En yüksek skordan başla
            adaylar.sort(key=lambda x: -x[1])
            for sym, skor in adaylar:
                if len(pozisyonlar) >= MAX_POZISYON:
                    break
                # Pozisyon başına sermaye: kalan nakdin 1/(MAX - açık) kadarı
                slotlar_kalan = MAX_POZISYON - len(pozisyonlar)
                butce = nakit / slotlar_kalan
                if butce < 50:  # min $50
                    continue
                idx = sym_index[sym][dt]
                bar = fiyatlar[sym][idx]
                al_fiyat = bar["close"] * (1 + SLIPPAGE_PCT / 100)
                miktar = (butce * (1 - KOMISYON_PCT / 100)) / al_fiyat
                if miktar <= 0:
                    continue
                nakit -= butce
                stop_fiyat = al_fiyat * (1 - STOP_LOSS_PCT / 100)
                pozisyonlar[sym] = Pozisyon(
                    sembol=sym,
                    giris_fiyat=al_fiyat,
                    giris_dt=dt,
                    miktar=miktar,
                    kalan_miktar=miktar,
                    en_yuksek=bar["high"],
                    stop_fiyat=stop_fiyat,
                )
                trade_log.append(
                    {
                        "dt": dt.isoformat(),
                        "sembol": sym,
                        "yon": "AL",
                        "fiyat": round(al_fiyat, 6),
                        "miktar": round(miktar, 6),
                        "sebep": f"SKOR={skor:.1f}",
                        "kar_pct": None,
                    }
                )

        # 3) Equity snapshot (günlük)
        if dt.hour == 0:
            toplam = nakit
            for sym, poz in pozisyonlar.items():
                if sym in sym_index and dt in sym_index[sym]:
                    toplam += poz.kalan_miktar * fiyatlar[sym][sym_index[sym][dt]]["close"]
            equity_curve.append((dt, toplam))

    # Kalan pozisyonları son fiyattan kapat (mark-to-market)
    son_dt = timeline[-1]
    for sym, poz in list(pozisyonlar.items()):
        if sym in sym_index and son_dt in sym_index[sym]:
            fiyat = fiyatlar[sym][sym_index[sym][son_dt]]["close"]
            gelir = fiyat * poz.kalan_miktar * (1 - KOMISYON_PCT / 100)
            nakit += gelir
            kar = gelir - poz.giris_fiyat * poz.kalan_miktar
            kar_pct = (kar / (poz.giris_fiyat * poz.kalan_miktar)) * 100
            if kar_pct > 0:
                kazanan += 1
                kazanc_yuzdeler.append(kar_pct)
            else:
                kaybeden += 1
                kayip_yuzdeler.append(kar_pct)
            trade_log.append(
                {
                    "dt": son_dt.isoformat(),
                    "sembol": sym,
                    "yon": "SAT",
                    "fiyat": round(fiyat, 6),
                    "miktar": round(poz.kalan_miktar, 6),
                    "sebep": "EOT",
                    "kar_pct": round(kar_pct, 2),
                }
            )

    # Metrikler
    bitis = nakit
    toplam_getiri = (bitis - BASLANGIC_SERMAYE) / BASLANGIC_SERMAYE * 100

    # Max drawdown
    peak = BASLANGIC_SERMAYE
    max_dd = 0.0
    for _, eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Günlük getirilerden Sharpe-benzeri
    if len(equity_curve) > 2:
        daily_rets = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1][1]
            cur = equity_curve[i][1]
            if prev > 0:
                daily_rets.append((cur - prev) / prev)
        if daily_rets and statistics.stdev(daily_rets) > 0:
            sharpe = (statistics.mean(daily_rets) / statistics.stdev(daily_rets)) * math.sqrt(365)
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    toplam_islem = kazanan + kaybeden
    winrate = kazanan / toplam_islem * 100 if toplam_islem else 0
    ort_kazanc = statistics.mean(kazanc_yuzdeler) if kazanc_yuzdeler else 0
    ort_kayip = statistics.mean(kayip_yuzdeler) if kayip_yuzdeler else 0

    return Sonuc(
        strateji=strateji,
        baslangic=BASLANGIC_SERMAYE,
        bitis=bitis,
        toplam_getiri_pct=toplam_getiri,
        islem_sayisi=toplam_islem,
        kazanan=kazanan,
        kaybeden=kaybeden,
        winrate=winrate,
        ort_kazanc_pct=ort_kazanc,
        ort_kayip_pct=ort_kayip,
        max_drawdown_pct=max_dd,
        sharpe_benzeri=sharpe,
        trade_log=trade_log,
    )


# ---------- Rapor -------------------------------------------------------------


def rapor_yaz(sonuclar: list[Sonuc]) -> None:
    lines: list[str] = []
    lines.append("# ANKA Backtest v2 — Sonuç Raporu")
    lines.append("")
    lines.append(f"**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Dönem:** Son 365 gün (1h mumlar)")
    lines.append(f"**Semboller:** {', '.join(SYMBOLS)}")
    lines.append(f"**Başlangıç sermaye:** ${BASLANGIC_SERMAYE:.2f}")
    lines.append(f"**Komisyon/yön:** %{KOMISYON_PCT} | **Slippage/yön:** %{SLIPPAGE_PCT}")
    lines.append("")
    lines.append("## Parametreler")
    lines.append(f"- MIN_SKOR_AL: **{MIN_SKOR_AL}**")
    lines.append(f"- Stop-loss: **%{STOP_LOSS_PCT}**")
    lines.append(f"- Trailing başlangıç: **+%{TRAILING_BASLA_PCT}** üstünden **-%{TRAILING_GERI_PCT}**")
    lines.append(f"- TP1: **+%{TAKE_PROFIT_1_PCT}** (yarısı) | TP2: **+%{TAKE_PROFIT_2_PCT}** (tamamı)")
    lines.append(f"- Max pozisyon: **{MAX_POZISYON}**")
    lines.append("")
    lines.append("## Skor formülü")
    lines.append("`SKOR = TEK*0.30 + HAC*0.20 + MAK*0.15 + LIK*0.10 + SEN*0.15 + FUN*0.10`")
    lines.append("")
    lines.append("## Özet Tablo")
    lines.append("")
    lines.append(
        "| Strateji | Bitiş $ | Getiri % | Trade | Winrate | Ort Kazanç | Ort Kayıp | MaxDD | Sharpe~ |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for s in sonuclar:
        lines.append(
            f"| {s.strateji} | ${s.bitis:.2f} | {s.toplam_getiri_pct:+.1f}% | "
            f"{s.islem_sayisi} | {s.winrate:.1f}% | "
            f"{s.ort_kazanc_pct:+.2f}% | {s.ort_kayip_pct:+.2f}% | "
            f"{s.max_drawdown_pct:.1f}% | {s.sharpe_benzeri:.2f} |"
        )
    lines.append("")

    # Her strateji için detaylar
    for s in sonuclar:
        lines.append(f"## {s.strateji}")
        lines.append("")
        lines.append(f"- Başlangıç → Bitiş: **${s.baslangic:.2f} → ${s.bitis:.2f}**")
        lines.append(f"- Toplam getiri: **{s.toplam_getiri_pct:+.2f}%**")
        lines.append(f"- İşlem: {s.islem_sayisi} (kazanan {s.kazanan}, kaybeden {s.kaybeden})")
        lines.append(f"- Winrate: **{s.winrate:.1f}%**")
        lines.append(f"- Max drawdown: **{s.max_drawdown_pct:.1f}%**")
        lines.append(f"- Sharpe-benzeri (yıllık): **{s.sharpe_benzeri:.2f}**")
        # İlk 5 ve son 5 trade
        lines.append("")
        lines.append("### İlk 5 işlem")
        lines.append("| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |")
        lines.append("|---|---|---|---:|---|---:|")
        for t in s.trade_log[:5]:
            kar = f"{t['kar_pct']:+.2f}" if t.get("kar_pct") is not None else "—"
            lines.append(
                f"| {t['dt'][:16]} | {t['sembol']} | {t['yon']} | "
                f"{t['fiyat']} | {t['sebep']} | {kar} |"
            )
        lines.append("")
        lines.append("### Son 5 işlem")
        lines.append("| Zaman | Sembol | Yön | Fiyat | Sebep | Kar% |")
        lines.append("|---|---|---|---:|---|---:|")
        for t in s.trade_log[-5:]:
            kar = f"{t['kar_pct']:+.2f}" if t.get("kar_pct") is not None else "—"
            lines.append(
                f"| {t['dt'][:16]} | {t['sembol']} | {t['yon']} | "
                f"{t['fiyat']} | {t['sebep']} | {kar} |"
            )
        lines.append("")

    lines.append("## Yorum")
    lines.append("")
    a, b, c = sonuclar
    if b.toplam_getiri_pct > a.toplam_getiri_pct:
        lines.append(
            f"- **SEN + FUN dahil etmek getiriyi {b.toplam_getiri_pct - a.toplam_getiri_pct:+.1f} puan değiştirdi** "
            f"({a.toplam_getiri_pct:+.1f}% → {b.toplam_getiri_pct:+.1f}%)."
        )
    else:
        lines.append(
            f"- **SEN + FUN eklemek baseline'a göre getiriyi {b.toplam_getiri_pct - a.toplam_getiri_pct:+.1f} puan değiştirdi** — trend-following sentiment bu dönemde yardımcı olmadı."
        )
    if c.toplam_getiri_pct > b.toplam_getiri_pct:
        lines.append(
            f"- **Kontrarian F&G ({c.toplam_getiri_pct:+.1f}%)** — trend-following sürümüne ({b.toplam_getiri_pct:+.1f}%) göre **daha iyi**."
        )
    else:
        lines.append(
            f"- Kontrarian F&G ({c.toplam_getiri_pct:+.1f}%) bu dönemde trend-following'e ({b.toplam_getiri_pct:+.1f}%) göre **daha zayıf**."
        )
    lines.append("- Not: Bu backtest survivorship-bias içerebilir (sadece MOVR/ATOM/BNB/BTC).")
    lines.append("- Not: Funding rate sadece futures'a yansır; spot'ta dolaylı etkidir.")
    lines.append("- Not: F&G günlük, funding 8h/4h — skor yavaş değişir. İntraday sinyal değil rejim filtresi olarak güçlü.")
    lines.append("")

    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapor yazıldı: {REPORT_MD}")


def main():
    print("Veriler yükleniyor...")
    fiyatlar = fiyatlari_yukle()
    fg = fg_yukle()
    funding = funding_yukle()
    print(f"  Fiyat: {sum(len(v) for v in fiyatlar.values())} bar ({len(fiyatlar)} sembol)")
    print(f"  F&G: {len(fg)} gün")
    print(f"  Funding: {sum(len(v) for v in funding.values())} kayıt")

    print("\n[1/3] Baseline (SEN=FUN=kapalı) çalıştırılıyor...")
    a = backtest_calistir("A) Baseline (teknik+hacim)", fiyatlar, fg, funding, sen_fun_acik=False)
    print(f"  Bitiş: ${a.bitis:.2f} ({a.toplam_getiri_pct:+.1f}%)")

    print("\n[2/3] v2 Full (SEN+FUN açık, trend-following) çalıştırılıyor...")
    b = backtest_calistir("B) v2 Full (SEN+FUN trend)", fiyatlar, fg, funding, sen_fun_acik=True)
    print(f"  Bitiş: ${b.bitis:.2f} ({b.toplam_getiri_pct:+.1f}%)")

    print("\n[3/3] v2 Kontrarian (F&G aşırı korku=fırsat) çalıştırılıyor...")
    c = backtest_calistir("C) v2 Kontrarian F&G", fiyatlar, fg, funding, kontrarian=True, sen_fun_acik=True)
    print(f"  Bitiş: ${c.bitis:.2f} ({c.toplam_getiri_pct:+.1f}%)")

    rapor_yaz([a, b, c])


if __name__ == "__main__":
    main()
