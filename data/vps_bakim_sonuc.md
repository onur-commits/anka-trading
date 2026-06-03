# ðŸ”§ ANKA VPS Bakim Sonucu

_2026-06-03 16:15:44 TR â€” run 26887227167_

Warning: Permanently added '78.135.87.29' (ED25519) to the list of known hosts.
#< CLIXML
## 1) Kod guncelleme (git stash + pull)
```
Saved working directory and index state On main: vps-auto-yedek

Updating cf44291..923c249
Fast-forward
 .claude/settings.json                           |  95 ++++
 .env.example                                    |   6 +
 .github/workflows/canli_durum.yml               | 114 ++++
 .github/workflows/vps_bakim.yml                 | 102 ++++
 .gitignore                                      |  24 +
 .python-version                                 |   1 +
 .vscode/extensions.json                         |   8 +
 .vscode/launch.json                             |  72 +++
 .vscode/settings.json                           |  60 ++
 .vscode/tasks.json                              |  52 ++
 AGENTS.md                                       |   9 +
 ANKA_COIN_PANEL_V2.md                           | 340 +-----------
 ANKA_DOKTORA_RAPORU.md                          | 602 ++++++--------------
 ANKA_KURULUM.sh                                 |  73 ++-
 ANKA_LITERATUR_RAPORU.md                        | 232 +++-----
 ANKA_PANEL_TARTISMA.md                          | 406 +++-----------
 BIST_V3_ENTEGRE_PLAN.md                         | 145 +++++
 CLAUDE.md                                       |  33 +-
 COIN_DOKTORA_VE_PANEL.md                        | 693 ++++--------------------
 COIN_LITERATUR_RAPORU.md                        | 250 +--------
 COIN_ML_ENTEGRE_PLAN.md                         |  98 ++++
 COWORK_DEVRALDIRMA_20260418.md                  | 283 ----------
 COWORK_GOREV.md                                 | 106 ----
 DURUM_RAPORU_20260415.md                        | 327 -----------
 PAPER_DENEME_TALIMAT.md                         | 185 -------
 PLAN_ARACI_KURUM_GECIS.md                       |  76 ---
 _memory_update_20260418.md                      |  85 ---
 ab_karsilastirma.py                             |   7 +-
 ab_sonuc.py                                     | 158 ++++++
 alpha_v2_bot.py                                 |  21 +-
 anka_ai_egitim.py                               |  10 +-
 anka_api.py                                     |   2 -
 anka_beyin.py                                   |  66 ++-
 anka_dashboard.py                               | 658 ----------------------
 anka_karar_verici.py                            |  31 +-
 anka_muhendis.py                                | 120 +++-
 anka_ogrenme.py                                 |  12 +-
 anka_orkestra.py                                |  36 +-
 anka_panel_kurallari.py                         |  19 +-
 anka_rotasyon.py                                |  42 +-
 anka_scalper.py                                 |  20 +-
 anka_scanner.py                                 |   4 +-
 anka_startup.bat                                |   4 +-
 anka_v2.py                                      |  39 +-
 anka_watchdog.py                                |   4 +-
 app.py                                          |   9 +-
 backtest_v2.py                                  |   4 +-
 baslat.sh                                       |  20 +-
 bist_predict.py                                 | 107 ++++
 bomba_robot_log_bridge.py                       |   1 -
 bot.py                                          |   9 +-
 coin_ai_egitim.py                               |  21 +-
 coin_ajanlar.py                                 |  23 +-
 coin_dashboard.py                               | 585 --------------------
 coin_fullscan.py                                |  20 +-
 coin_katmanli_scan.py                           |  20 +-
 coin_ml_score.py                                | 263 +++++++++
 coin_otonom.py                                  | 114 ++--
 coin_otonom_trader.py                           |  64 ++-
 coin_strateji.py                                |  30 +-
 coin_trader.py                                  |  42 +-
 data/canli_durum.md                             |  81 +++
 data/otonom_log.json                            |   5 +
 dca_backtest.py                                 |   6 +-
 dogruluk_kontrol.py                             |  20 +-
 earn_to_spot.py                                 |   4 +-
 feedback_loop.py                                |   5 +-
 grid_backtest.py                                |   2 -
 gunluk_bomba.py                                 |   7 +-
 haber_ajan.py                                   |   5 +-
 haber_sentiment.py                              |   3 +-
 hibrit_scanner.py                               |  13 +-
 kontrol_paneli.py                               | 412 --------------
 makro_veri.py                                   |   4 +-
 matriks_iq/iq_deployer.py                       |   3 +-
 motor_v3.py                                     |  12 +-
 otonom_trader.py                                | 179 +++++-
 "pages/1_\360\237\217\206_Alpha_V2.py"          |  11 +-
 pages/2_ANKA_Danisman.py                        |   5 +-
 "pages/2_ANKA_Danis\320\274\320\260\320\275.py" | 642 ----------------------
 pages/3_ANKA_Beyin.py                           |   5 +-
 pages/4_Otonom_Trader.py                        |  28 +-
 pages/5_Sistem_Saglik.py                        |   3 +-
 pages/6_Raporlar.py                             | 250 +++++++++
 paper_trader.py                                 |   7 +-
 piyasa_takvim.py                                |  36 +-
 pyproject.toml                                  |  48 ++
 rejim_modeller.py                               |   5 +-
 requirements.txt                                |  14 +
 risk_yonetimi.py                                |   1 -
 sabah_scanner.py                                |   8 +-
 scripts/canli_durum.sh                          |  73 +++
 scripts/setup_venv.sh                           |  86 +++
 scripts/vps_kontrol.sh                          |  91 ++++
 tahmin_motoru.py                                |   2 +-
 tahmin_motoru_v2.py                             |  15 +-
 tahmin_motoru_v3.py                             |  16 +-
 v3_bridge_writer.py                             |   6 +-
 v3_risk_motor.py                                |   7 +-
 veri_isleyici.py                                |   2 -
 100 files changed, 3333 insertions(+), 5851 deletions(-)
 create mode 100644 .claude/settings.json
 create mode 100644 .env.example
 create mode 100644 .github/workflows/canli_durum.yml
 create mode 100644 .github/workflows/vps_bakim.yml
 create mode 100644 .python-version
 create mode 100644 .vscode/extensions.json
 create mode 100644 .vscode/launch.json
 create mode 100644 .vscode/settings.json
 create mode 100644 .vscode/tasks.json
 create mode 100644 AGENTS.md
 create mode 100644 BIST_V3_ENTEGRE_PLAN.md
 create mode 100644 COIN_ML_ENTEGRE_PLAN.md
 delete mode 100644 COWORK_DEVRALDIRMA_20260418.md
 delete mode 100644 COWORK_GOREV.md
 delete mode 100644 DURUM_RAPORU_20260415.md
 delete mode 100644 PAPER_DENEME_TALIMAT.md
 delete mode 100644 PLAN_ARACI_KURUM_GECIS.md
 delete mode 100644 _memory_update_20260418.md
 create mode 100644 ab_sonuc.py
 delete mode 100644 anka_dashboard.py
 create mode 100644 bist_predict.py
 delete mode 100644 coin_dashboard.py
 create mode 100644 coin_ml_score.py
 create mode 100644 data/canli_durum.md
 delete mode 100644 kontrol_paneli.py
 delete mode 100644 "pages/2_ANKA_Danis\320\274\320\260\320\275.py"
 create mode 100644 pages/6_Raporlar.py
 create mode 100644 pyproject.toml
 create mode 100755 scripts/canli_durum.sh
 create mode 100755 scripts/setup_venv.sh
 create mode 100755 scripts/vps_kontrol.sh

HEAD: 923c249
```

## 2) Calisan python prosesleri
```

  Id StartTime            Dak
  -- ---------            ---
3888 28.05.2026 22:35:54 8260



```

## 3) ANKA zamanlanmis gorevler (scheduler)
```


ANKA_AB_Karsilastirma                    3.06.2026 23:00:00     Ready          
ANKA_Alarm_AlListesi                     4.06.2026 09:45:00     Ready          
ANKA_Alarm_SatNow                        3.06.2026 17:30:00     Ready          
ANKA_Alarm_SatUyari                      3.06.2026 17:25:00     Ready          
ANKA_BistDashboard                       N/A                    Ready          
ANKA_BIST_TGOnay                         N/A                    Ready          
ANKA_CoinBot                             N/A                    Disabled       
ANKA_CoinDashboard                       N/A                    Ready          
ANKA_Coin_Bot                            N/A                    Disabled       
ANKA_Coin_Bot_Paper                      N/A                    Disabled       
ANKA_Coin_DCA                            8.06.2026 10:00:00     Ready          
ANKA_Coin_Trader                         N/A                    Disabled       
ANKA_ConfigCanary                        3.06.2026 16:26:00     Ready          
ANKA_Dashboard                           1.01.2099 00:00:00     Ready          
ANKA_DurumBildirim_OneShot               N/A                    Ready          
ANKA_FeedbackRapor                       3.06.2026 18:30:00     Ready          
ANKA_IQ_Sabah_Check                      4.06.2026 07:55:00     Ready          
ANKA_Orkestra                            N/A                    Disabled       
ANKA_OtonomTrader                        N/A                    Disabled       
ANKA_Otonom_Trader                       N/A                    Disabled       
ANKA_PaperModelB                         N/A                    Disabled       
ANKA_REE_Doctor                          3.06.2026 17:06:00     Ready          
ANKA_REE_Radar                           3.06.2026 16:36:00     Ready          
ANKA_REE_Snapshot                        3.06.2026 16:36:00     Ready          
ANKA_REE_Strateji_Aksam                  3.06.2026 17:00:00     Ready          
ANKA_REE_Strateji_Gece                   4.06.2026 02:00:00     Ready          
ANKA_REE_Strateji_Ogle                   4.06.2026 12:00:00     Ready          
ANKA_REE_Strateji_Sabah                  4.06.2026 08:00:00     Ready          
ANKA_Saat_Duzelt                         N/A                    Ready          
ANKA_Sabah_Hatirlatma                    N/A                    Ready          
ANKA_State_Backup                        3.06.2026 16:42:00     Ready          
ANKA_Telegram_Update                     3.06.2026 16:30:00     Ready          
ANKA_TopGainer                           3.06.2026 16:39:00     Ready          
ANKA_Watchdog                            N/A                    Disabled       



```

## 4) MatriksIQ + TCP 18890 (emirler bunun icin gitmiyordu)
```
MatriksIQ ACIK (PID 8604)
Port 18890:

  TCP    0.0.0.0:18890          0.0.0.0:0              LISTENING



```

## 5) Son 15 sistem logu
```
[2026-04-05 15:00:01] [INFO]   BOMBA_AYEN: ƒ?O Log yok
[2026-04-05 15:00:01] [INFO]   BOMBA_DOHOL: ƒ?O Log yok
[2026-04-05 15:00:01] [INFO]   BOMBA_KONTR: ƒ?O Log yok
[2026-04-05 15:00:01] [INFO]   BOMBA_TUPRS: ƒ?O Log yok
[2026-04-05 15:00:01] [INFO]   BOMBA_KORDS: ƒ?O Log yok
[2026-04-05 17:35:03] [INFO] ==================================================
[2026-04-05 17:35:03] [INFO] dY"? [17:35] GAoN SONU RAPORU
[2026-04-05 17:35:06] [INFO] dY"S 05.04.2026 Raporu
Piyasa: BEAR
  AYEN: 34.40 (-5.4%) Skor:60
  DOHOL: 19.46 (-1.7%) Skor:58
  KONTR: 7.77 (-4.0%) Skor:53
  TUPRS: 255.25 (-0.3%) Skor:50
  KORDS: 56.60 (-4.6%) Skor:45
[2026-04-05 17:35:06] [BILDIRIM] GA¬n sonu rapor hazŽñr
[2026-04-06 05:30:13] [INFO] ==================================================
[2026-04-06 05:30:13] [INFO] dYÿ [05:30] ML MODEL EŽzŽøTŽøMŽø
[2026-04-06 05:30:44] [INFO]   52 hisse (2 yŽñl)
[2026-04-06 05:31:09] [INFO]   ƒo. AUC:0.5664 F1:0.6073
[2026-04-06 05:31:09] [BILDIRIM] ML gA¬ncellendi ƒ?" AUC:0.5664
[2026-06-03 03:18:01] [WARN] beyin_rejim_onay hata (fail-open): Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

## 6) Gozcu / HARD BREAKER durumu
```
```
<Objs Version="1.1.0.1" xmlns="http://schemas.microsoft.com/powershell/2004/04"><Obj S="progress" RefId="0"><TN RefId="0"><T>System.Management.Automation.PSCustomObject</T><T>System.Object</T></TN><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj><Obj S="progress" RefId="1"><TNRef RefId="0" /><MS><I64 N="SourceId">1</I64><PR N="Record"><AV>Preparing modules for first use.</AV><AI>0</AI><Nil /><PI>-1</PI><PC>-1</PC><T>Completed</T><SR>-1</SR><SD> </SD></PR></MS></Obj></Objs>