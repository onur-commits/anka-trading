"""
BIST Tahmin Wrapper — V3 -> V2 graceful fallback
==================================================
Live BIST kodu (otonom_trader.py, sabah_scanner.py, gunluk_bomba.py, app.py)
dogrudan EnsembleModelV2'yi cagiriyor. Bu wrapper V3 modeli varsa onu
kullanir, yoksa V2'ye duser. Mevcut callerlar 2 satir degisiklikle V3'e
gecirilebilir:

    # ESKI:
    from tahmin_motoru_v2 import EnsembleModelV2, hisse_analiz_v2
    model = EnsembleModelV2.yukle()
    analiz = hisse_analiz_v2(ticker, df, model, rejim)

    # YENI:
    from bist_predict import yukle_model, analiz_et
    model = yukle_model()              # V3 varsa V3, yoksa V2, yoksa None
    analiz = analiz_et(ticker, df, model, rejim)

Live trader'a otomatik bagli degil — entegrasyon karari kullanicida.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from tahmin_motoru_v2 import EnsembleModelV2, hisse_analiz_v2

MODEL_DIR = Path(__file__).parent / "models"
V2_PATH = MODEL_DIR / "ensemble_v2.pkl"
V3_PATH = MODEL_DIR / "ensemble_v3.pkl"

logger = logging.getLogger("bist_predict")

# V3 import — modul yoksa veya bozuksa V2'ye dus
try:
    from tahmin_motoru_v3 import StackingEnsembleV3, hisse_analiz_v3
    _V3_HAZIR = True
except Exception as e:
    logger.warning(f"V3 modulu yuklenemedi ({e}) — sadece V2 kullanilacak")
    StackingEnsembleV3 = None
    hisse_analiz_v3 = None
    _V3_HAZIR = False


def yukle_model() -> Optional[object]:
    """
    Sira: V3 (varsa) -> V2 (varsa) -> None.
    None doner: model dosyasi hic yok demektir, caller fallback davranis ister.
    """
    # 1) V3
    if _V3_HAZIR and V3_PATH.exists():
        try:
            model = StackingEnsembleV3.yukle_v3()
            if model is not None:
                logger.info(f"BIST V3 modeli yuklendi ({V3_PATH.name})")
                return model
        except Exception as e:
            logger.warning(f"V3 yukleme hatasi, V2'ye dusuluyor: {e}")

    # 2) V2
    if V2_PATH.exists():
        try:
            model = EnsembleModelV2.yukle()
            if model is not None:
                logger.info(f"BIST V2 modeli yuklendi ({V2_PATH.name})")
                return model
        except Exception as e:
            logger.warning(f"V2 yukleme hatasi: {e}")

    # 3) Hicbiri yok
    logger.warning("BIST modeli yok — ne V3 ne V2. ML olmadan kural-bazli analiz.")
    return None


def analiz_et(ticker: str, df, model=None, market_rejim=None):
    """
    Model tipine gore uygun analiz fonksiyonu cagrilir.
    StackingEnsembleV3 -> hisse_analiz_v3 (interaction features dahil)
    EnsembleModelV2 / None -> hisse_analiz_v2
    """
    if _V3_HAZIR and model is not None and isinstance(model, StackingEnsembleV3):
        return hisse_analiz_v3(ticker, df, model, market_rejim)
    return hisse_analiz_v2(ticker, df, model, market_rejim)


def model_bilgi(model) -> dict:
    """Yuklenen modelin metadata'si — log/dashboard icin."""
    if model is None:
        return {"versiyon": None, "hazir": False}
    if _V3_HAZIR and isinstance(model, StackingEnsembleV3):
        return {"versiyon": "V3", "hazir": True,
                "tip": "StackingEnsemble"}
    if isinstance(model, EnsembleModelV2):
        return {"versiyon": "V2", "hazir": True,
                "tip": "Ensemble (XGB+LGB+MLP)"}
    return {"versiyon": "?", "hazir": True, "tip": type(model).__name__}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    model = yukle_model()
    bilgi = model_bilgi(model)
    print(f"\nYuklenen model: {bilgi}")
    print(f"V3 modulu mevcut: {_V3_HAZIR}")
    print(f"V3 dosyasi: {V3_PATH} (var: {V3_PATH.exists()})")
    print(f"V2 dosyasi: {V2_PATH} (var: {V2_PATH.exists()})")
