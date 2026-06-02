# Mac Claude'a Devraldırma — 2026-06-02

Bu dosya, web Claude Code (bulut sandbox) oturumundan **Mac'te çalışan
Claude Code**'a geçiş içindir. Mac'te `code .` + Claude Code extension
açtıktan sonra ilk olarak bu dosyayı oku.

## Neden Mac Claude gerekli

Web sandbox kısıtları (bu oturum):
- VPS'e SSH yok (port 22 engelli, ssh aracı bile yüklü değil)
- Binance API 403 (sandbox IP block)
- numpy/pandas yüklü değil — kod çalıştırılamıyor, sadece `ast.parse` syntax check
- Mac dosya sistemine / IDE'ye erişim yok

Mac Claude bunların hepsini yapabilir → gerçek otonom.

## Mevcut durum (bu oturum sonu)

**Branch:** `claude/check-binance-integration-CNT9j` (origin'de güncel)
**Açık PR:** #4 — https://github.com/onur-commits/anka-trading/pull/4 (draft)
**Toplam:** PR #1 + #2 merge edildi; #4 son 3 commit'i bekliyor:
- `b8803b2` VS Code sekme limiti
- `2947483` Python 3.12 sabitleme
- `ff36d8e` atomik write sweep (rotasyon/kontrol_paneli/pages)

## İLK İŞ (Mac'te yapılacak — web'de yapılamadı)

### 1. Venv kur + gerçek import testi
```bash
cd ~/path/to/anka-trading
git pull
bash scripts/setup_venv.sh          # Python 3.12 venv
source .venv/bin/activate
python -X utf8 -c "import xgboost, lightgbm, streamlit, pandas; print('OK')"
```
Bu, web'de YAPILAMADI. xgboost/lightgbm gerçekten yükleniyor mu doğrula.

### 2. Tüm modüllerin import'unu test et (syntax değil, gerçek import)
```bash
for f in coin_otonom_trader coin_otonom coin_trader otonom_trader \
         anka_muhendis anka_orkestra anka_beyin coin_ml_score bist_predict; do
    python -X utf8 -c "import $f" 2>&1 | head -2 && echo "  ^ $f"
done
```
Web'de sadece ast.parse yapıldı; gerçek import (eksik bağımlılık, circular
import, runtime hata) test edilemedi.

### 3. coin ML modelini eğit (web'de yapılamadı)
```bash
python -X utf8 coin_ai_egitim.py
# -> models/coin_ai_v1.pkl uretir, AUC yazdirir
python -X utf8 coin_ml_score.py --test BTCUSDT
```
AUC < 0.55 ise bota bağlama (bkz COIN_ML_ENTEGRE_PLAN.md).

### 4. A/B sonucu (deney 19 Mayıs'ta bitti)
```bash
# VPS'te calismasi lazim — Mac'ten SSH:
ssh Administrator@78.135.87.29
cd C:\ANKA && git pull && python -X utf8 ab_sonuc.py
```

## Bu oturumda TAMAMLANAN işler (PR #1, #2, #4)

### Kritik bug fix'ler
1. **Fantom pozisyon** (4 commit) — coin & BIST trader'larda Binance/IQ
   hata yanıtları sessizce başarı sayılıyordu, bot var olmayan pozisyon
   kaydediyordu. `coin_otonom_trader`, `coin_otonom`, `coin_trader`,
   `otonom_trader` hepsinde düzeltildi.
2. **Atomik write** — tüm state dosyaları `tmp + os.replace` (dashboard
   partial JSON crash önleme). 9 modülde tamamlandı.
3. **Bozuk JSON recovery** — state okuma JSONDecodeError'da sıfırlayıp
   devam ediyor, crash etmiyor.
4. **coin_ai_egitim** — hardcoded Mac yolu, MATIC→POL/FTM→S rebrand,
   deprecated XGBoost arg, BTC korelasyon misalignment.
5. **requirements.txt** — eksik requests/dotenv/schedule.
6. **55 bare except** → `except Exception:`.
7. **12 file handle leak** → `with open()`.
8. **Python 3.12 sabitleme** — .python-version, pyproject, .vscode, uv script.

### Yeni modüller (live koda dokunmadan)
- `coin_ml_score.py` + `COIN_ML_ENTEGRE_PLAN.md` — coin ML entegrasyon altyapısı
- `bist_predict.py` + `BIST_V3_ENTEGRE_PLAN.md` — BIST V3→V2 fallback wrapper
- `ab_sonuc.py` — A/B deney sonuç hesabı
- `DOKTORA_TAKIP_20260525.md` — Nisan doktor raporu takibi
- `SABAH_RAPORU.md` — gece çalışması özeti

## SIRADAKİ İŞLER (öncelik sırası)

1. **[Mac] Venv + import testi** — yukarıdaki adım 1-2 (web'de yapılamadı)
2. **[Mac] coin ML eğit** — adım 3
3. **[VPS via Mac SSH] A/B sonucu** — adım 4
4. **[İnceleme] motor_v3.py** — shell=True subprocess güvenlik gözden geçir
5. **[İnceleme] v3_bridge_writer.py, bot.py, feedback_loop.py** — henüz
   derin taranmadı
6. **[Karar] PR #4 merge** — kullanıcı onayı bekliyor

## HARD LIMIT (değişmedi)
- Claude alım/satım/transfer/VPS'te canlı script TETİKLEMEZ
- Sadece kod yazar, commit + push + PR
- Mac'te bile: trader'ı `--dry-run` olmadan çalıştırma `ask` listesinde +
  PreToolUse hook gate'i var (.claude/settings.json)

## VPS bilgileri (CLAUDE.md'den)
- IP: 78.135.87.29, Windows Server 2022, Administrator
- C:\ANKA, Python 3.12.8
- SSH: `ssh Administrator@78.135.87.29` (şifre .env'de veya kullanıcıdan)
- Dashboards: 8501 (BIST), 8502 (COIN)
