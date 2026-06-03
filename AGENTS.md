# ANKA Trading Yerel Talimatlari

- Dil: Turkce, kisa ve net.
- Python: proje `.venv` icinde Python 3.12 kullanir. Mac'te tercih edilen kurulum: `bash scripts/setup_venv.sh`.
- Calistirirken `PYTHONUTF8=1`, `PYTHONPATH=.` ve gerekirse `-X utf8` kullan.
- Ana paneller: `app.py` port 8501, `coin_dashboard.py` port 8502.
- Kod/VS Code uyumu icin `.vscode/settings.json`, `tasks.json` ve `launch.json` kaynak kabul edilir.
- Canli alim/satim tetikleme: kullanici acikca istemedikce calistirma. COIN tarafinda varsayilan test komutu `coin_otonom_trader.py --dry-run --tara`; BIST tarafinda guvenli kontrol `otonom_trader.py --durum`.
- `.env` git'e eklenmez; ornek degiskenler `.env.example` dosyasindadir.
