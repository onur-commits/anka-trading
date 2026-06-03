# ðŸ”§ ANKA VPS Bakim Sonucu

_2026-06-03 16:41:15 TR â€” run 26888656739_

Warning: Permanently added '78.135.87.29' (ED25519) to the list of known hosts.
#< CLIXML
## 1) Kod guncelleme (git stash + pull)
```
Saved working directory and index state On main: vps-auto-yedek

Updating 923c249..f9c6e3a
Fast-forward
 .github/workflows/baslat_kontrol.yml |  71 ++++++++++
 data/baslat_kontrol.md               |  21 +++
 data/vps_bakim_sonuc.md              | 242 +++++++++++++++++++++++++++++++++++
 start_otonom.bat                     |  24 ++++
 4 files changed, 358 insertions(+)
 create mode 100644 .github/workflows/baslat_kontrol.yml
 create mode 100644 data/baslat_kontrol.md
 create mode 100644 data/vps_bakim_sonuc.md
 create mode 100644 start_otonom.bat

HEAD: f9c6e3a
```

## 2) Calisan python prosesleri
```

  Id StartTime            Dak
  -- ---------            ---
3888 28.05.2026 22:35:54 8285



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
ANKA_ConfigCanary                        3.06.2026 16:56:00     Ready          
ANKA_Dashboard                           1.01.2099 00:00:00     Ready          
ANKA_DurumBildirim_OneShot               N/A                    Ready          
ANKA_FeedbackRapor                       3.06.2026 18:30:00     Ready          
ANKA_IQ_Sabah_Check                      4.06.2026 07:55:00     Ready          
ANKA_Orkestra                            N/A                    Disabled       
ANKA_OtonomTrader                        N/A                    Ready          
ANKA_Otonom_Trader                       N/A                    Disabled       
ANKA_PaperModelB                         N/A                    Disabled       
ANKA_REE_Doctor                          3.06.2026 17:06:00     Ready          
ANKA_REE_Radar                           3.06.2026 17:06:00     Ready          
ANKA_REE_Snapshot                        3.06.2026 17:06:00     Ready          
ANKA_REE_Strateji_Aksam                  3.06.2026 17:00:00     Ready          
ANKA_REE_Strateji_Gece                   4.06.2026 02:00:00     Ready          
ANKA_REE_Strateji_Ogle                   4.06.2026 12:00:00     Ready          
ANKA_REE_Strateji_Sabah                  4.06.2026 08:00:00     Ready          
ANKA_Saat_Duzelt                         N/A                    Ready          
ANKA_Sabah_Hatirlatma                    N/A                    Ready          
ANKA_State_Backup                        3.06.2026 16:42:00     Ready          
ANKA_Telegram_Update                     3.06.2026 16:55:00     Ready          
ANKA_TopGainer                           3.06.2026 17:09:00     Ready          
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