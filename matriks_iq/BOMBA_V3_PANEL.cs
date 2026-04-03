using System;
using System.Collections.Generic;
using System.IO;
using Matriks.Data.Symbol;
using Matriks.Engines;
using Matriks.Indicators;
using Matriks.Symbols;
using Matriks.AlgoTrader;
using Matriks.Trader.Core;
using Matriks.Trader.Core.Fields;
using Matriks.Trader.Core.TraderModels;
using Matriks.Lean.Algotrader.AlgoBase;
using Matriks.Lean.Algotrader.Models;
using Matriks.Lean.Algotrader.Trading;
using Matriks.Enumeration;
using Newtonsoft.Json;

namespace Matriks.Lean.Algotrader
{
	// ════════════════════════════════════════════════════════════
	// ANKA V3 PANEL EDITION — 10 Profesör Onaylı Son Versiyon
	// ════════════════════════════════════════════════════════════
	// - Panel kuralları dahil (kill-switch, fat-finger, emir limiti)
	// - OnOrderUpdate tamamen yeniden yazıldı (gerçek dolum fiyatı)
	// - Rejected/Cancelled/PartiallyFilled yönetimi
	// - Dry-run (simülasyon) modu
	// - SendOrderSequential(false) — sinyal kaçırmaz
	// - Günlük K/Z takibi + kill-switch
	// ════════════════════════════════════════════════════════════

	public class BOMBA_V3_TURBO12 : MatriksAlgo
	{
		[Parameter("GARAN,THYAO,ASELS,TUPRS,EREGL,SISE,TOASO,AKBNK,YKBNK,HALKB,SAHOL,KCHOL,TCELL,BIMAS,PGSUS,TAVHL,FROTO,ARCLK,PETKM,ENKAI,TKFEN,EKGYO,TTKOM,VAKBN,MGROS,DOHOL,GUBRF,ISCTR,AKSEN,AYEN,KONTR,SASA,GESAN,OTKAR,ENJSA,TSKB,SMRTG,CCOLA,CIMSA,KORDS,VESTL,ALARK,HEKTS,ULKER,ASTOR,TTRAK,EGEEN,CEMTS,BRISA")]
		public string AllSymbols;

		[Parameter(16000)]
		public decimal BasePosValue;

		[Parameter(SymbolPeriod.Min20)]
		public SymbolPeriod Period;

		[Parameter(1.2)] public double ProfitTrigger;
		[Parameter(3.5)] public double HardStop;
		[Parameter(1.8)] public double TrailingStop;

		string bombaPath = @"C:\Robot\aktif_bombalar.txt";
		string bridgePath = @"C:\Robot\v3_bridge.json";

		Dictionary<string, MOV> fastMovs = new Dictionary<string, MOV>();
		Dictionary<string, MOV> slowMovs = new Dictionary<string, MOV>();
		Dictionary<string, RSI> rsis = new Dictionary<string, RSI>();
		Dictionary<string, MOST> mosts = new Dictionary<string, MOST>();

		Dictionary<string, bool> inPosition = new Dictionary<string, bool>();
		Dictionary<string, decimal> entryPrices = new Dictionary<string, decimal>();
		Dictionary<string, decimal> highestPrices = new Dictionary<string, decimal>();
		Dictionary<string, decimal> posQuantities = new Dictionary<string, decimal>();
		Dictionary<int, string> symbolCache = new Dictionary<int, string>();
		Dictionary<string, int> lastOrderBarIndex = new Dictionary<string, int>();
		Dictionary<string, bool> sellPending = new Dictionary<string, bool>();
		Dictionary<string, bool> buyPending = new Dictionary<string, bool>();

		// PANEL: Günlük takip
		int gunlukEmirSayisi = 0;
		decimal gunlukKZ = 0m;
		int sonGun = 0;
		bool killSwitchAktif = false;
		bool dryRun = false;

		HashSet<string> aktivBombalar = new HashSet<string>();
		int barSayaci = 0;
		bool robotAktif = true;

		public override void OnInit()
		{
			string[] symbols = AllSymbols.Split(',');
			foreach (var sym in symbols)
			{
				string s = sym.Trim().ToUpper();
				if (string.IsNullOrEmpty(s)) continue;

				AddSymbol(s, Period);
				symbolCache[GetSymbolId(s)] = s;

				fastMovs[s] = MOVIndicator(s, Period, OHLCType.Close, 10, MovMethod.Exponential);
				slowMovs[s] = MOVIndicator(s, Period, OHLCType.Close, 20, MovMethod.Exponential);
				rsis[s] = RSIIndicator(s, Period, OHLCType.Close, 14);
				mosts[s] = MOSTIndicator(s, Period, OHLCType.Close, 3, 2m, MovMethod.Exponential);

				inPosition[s] = false;
				entryPrices[s] = 0m;
				highestPrices[s] = 0m;
				posQuantities[s] = 0m;
				lastOrderBarIndex[s] = -1;
				sellPending[s] = false;
				buyPending[s] = false;
			}

			BombaOku();
			SendOrderSequential(false);
			WorkWithPermanentSignal(false);
			Debug($"ANKA PANEL EDITION — {symbols.Length} sembol, {aktivBombalar.Count} bomba");
		}

		private void BombaOku()
		{
			try
			{
				if (!File.Exists(bombaPath)) return;
				string icerik = File.ReadAllText(bombaPath).Trim().ToUpper();
				if (string.IsNullOrEmpty(icerik)) return;

				var yeni = new HashSet<string>();
				foreach (var item in icerik.Split(','))
				{
					string s = item.Trim();
					if (!string.IsNullOrEmpty(s) && symbolCache.ContainsValue(s))
						yeni.Add(s);
				}

				if (!yeni.SetEquals(aktivBombalar))
				{
					aktivBombalar = yeni;
					Debug($"BOMBA GUNCELLENDI: {string.Join(",", aktivBombalar)}");
				}
			}
			catch { }
		}

		private void GunSifirla()
		{
			int bugun = DateTime.Now.DayOfYear;
			if (bugun != sonGun)
			{
				gunlukEmirSayisi = 0;
				gunlukKZ = 0m;
				killSwitchAktif = false;
				sonGun = bugun;
				Debug("Yeni gun — sayaclar sifirlandi");
			}
		}

		public override void OnDataUpdate(BarDataEventArgs barData)
		{
			if (barData == null || barData.BarData == null) return;
			if (!symbolCache.TryGetValue(barData.SymbolId, out string s)) return;

			GunSifirla();

			barSayaci++;
			if (barSayaci % 3 == 0) BombaOku();

			decimal close = barData.BarData.Close;
			int currentHour = Hour(barData.BarData);
			int currentMinute = Minute(barData.BarData);
			int currentBarIndex = barData.BarDataIndex;

			// === BRIDGE OKUMA ===
			decimal macroMultiplier = 1.0m;
			try {
				if (File.Exists(bridgePath)) {
					dynamic data = JsonConvert.DeserializeObject(File.ReadAllText(bridgePath));
					if (data != null) {
						macroMultiplier = (decimal)data.multiplier;
						if (data.pos_value != null) BasePosValue = (decimal)data.pos_value;
						if (data.hard_stop != null) HardStop = (double)data.hard_stop;
						if (data.trailing_stop != null) TrailingStop = (double)data.trailing_stop;
						if (data.profit_trigger != null) ProfitTrigger = (double)data.profit_trigger;
						if (data.robot_active != null) robotAktif = (bool)data.robot_active;
						if (data.dry_run != null) dryRun = (bool)data.dry_run;
						if ((string)data.regime == "DANGER_CRASH" || (string)data.regime == "KILL_SWITCH")
							robotAktif = false;

						try {
							if (data.panel_rules != null && (bool)data.panel_rules.kill_switch_active)
								killSwitchAktif = true;
						} catch { }
					}
				}
			} catch { macroMultiplier = 1.0m; }

			// KILL-SWITCH
			if (killSwitchAktif)
			{
				if (inPosition[s] && !sellPending[s])
				{
					decimal qty = posQuantities[s];
					if (qty > 0)
					{
						if (dryRun)
						{
							decimal pnl = (close - entryPrices[s]) / entryPrices[s] * 100m;
							Debug($"🔬 [SIM-KILL-SAT] {s} | PnL: %{pnl:F2}");
							ResetSymbol(s);
						}
						else
						{
							sellPending[s] = true;
							SendMarketOrder(s, qty, OrderSide.Sell);
							Debug($"🚨 [KILL-SWITCH SAT] {s} | Adet: {qty}");
						}
					}
				}
				return;
			}

			if (!robotAktif && !inPosition[s]) return;

			// Öğlen bloğu
			if (currentHour == 12 || (currentHour == 13 && currentMinute < 45)) return;

			decimal timeMultiplier = 1.0m;
			if (currentHour == 10 && currentMinute <= 30) timeMultiplier = 1.3m;
			if (currentHour == 17 && currentMinute >= 30) timeMultiplier = 0.6m;

			if (!fastMovs.ContainsKey(s)) return;
			bool emaOk = fastMovs[s].CurrentValue > slowMovs[s].CurrentValue;
			bool rsiOk = rsis[s].CurrentValue > 50;
			bool trendOk = close > mosts[s].CurrentValue;

			// === POZİSYON YÖNETİMİ ===
			if (inPosition[s])
			{
				if (sellPending[s]) return;

				if (close > highestPrices[s]) highestPrices[s] = close;
				decimal pnl = (close - entryPrices[s]) / entryPrices[s] * 100m;

				bool exitBeforeClose = (currentHour == 17 && currentMinute >= 50 && pnl > 0.5m);
				bool bombadenCikti = !aktivBombalar.Contains(s) && pnl > 0;
				bool manuelDurdur = !robotAktif;

				decimal stopPrice = entryPrices[s] * (1 - (decimal)HardStop / 100m);
				if (pnl >= (decimal)ProfitTrigger) {
					stopPrice = Math.Max(stopPrice, highestPrices[s] * (1 - (decimal)TrailingStop / 100m));
				}

				if (close <= stopPrice || !emaOk || exitBeforeClose || bombadenCikti || manuelDurdur)
				{
					decimal qty = posQuantities[s];
					if (qty > 0)
					{
						string sebep = manuelDurdur ? "Manuel" : exitBeforeClose ? "GunSonu" : bombadenCikti ? "BombadenCikti" : "Stop/Trend";

						if (dryRun)
						{
							Debug($"🔬 [SIM-SAT] {s} | PnL: %{pnl:F2} | Sebep: {sebep}");
							gunlukKZ += pnl * entryPrices[s] * qty / 100m;
							ResetSymbol(s);
						}
						else
						{
							sellPending[s] = true;
							SendMarketOrder(s, qty, OrderSide.Sell);
							Debug($"[SAT] {s} | PnL: %{pnl:F2} | Sebep: {sebep}");
						}
					}
				}
			}
			// === YENİ GİRİŞ ===
			else
			{
				if (!aktivBombalar.Contains(s)) return;
				if (currentHour == 17 && currentMinute >= 30) return;
				if (currentBarIndex == lastOrderBarIndex[s]) return;
				if (buyPending[s]) return;

				// PANEL: Günlük emir limiti
				if (gunlukEmirSayisi >= 50) return;

				if (emaOk && rsiOk && trendOk)
				{
					decimal finalValue = BasePosValue * macroMultiplier * timeMultiplier;
					decimal qty = Math.Floor(finalValue / close);
					if (qty < 1) return;

					// PANEL: Fat-finger kontrolü
					decimal emirTutar = qty * close;
					if (emirTutar > 30000m)
					{
						qty = Math.Floor(30000m / close);
						if (qty < 1) return;
					}

					lastOrderBarIndex[s] = currentBarIndex;
					gunlukEmirSayisi++;

					if (dryRun)
					{
						// SİMÜLASYON: Emir gönderme, sadece logla ve sanal pozisyon aç
						inPosition[s] = true;
						buyPending[s] = false;
						posQuantities[s] = qty;
						entryPrices[s] = close;
						highestPrices[s] = close;
						Debug($"🔬 [SIM-AL] {s} | Adet: {qty} | Fiyat: {close:F2} | Carpan: {macroMultiplier * timeMultiplier:F2}");
					}
					else
					{
						// GERÇEK EMİR: Dolum bekle
						buyPending[s] = true;
						SendMarketOrder(s, qty, OrderSide.Buy);
						Debug($"[AL-BEKLE] {s} | Adet: {qty} | Fiyat: {close:F2}");
					}
				}
			}
		}

		// ════════════════════════════════════════════════════════
		// PANEL: OnOrderUpdate TAMAMEN YENİDEN YAZILDI
		// ════════════════════════════════════════════════════════
		public override void OnOrderUpdate(IOrder order)
		{
			string sym = order.Symbol;
			if (!symbolCache.ContainsValue(sym)) return;

			// Dry-run modunda gerçek emir gelmez, bu fonksiyon çağrılmaz
			if (dryRun) return;

			// === EMİR DOLDU ===
			if (order.OrdStatus.Obj == OrdStatus.Filled)
			{
				if (order.Side.Obj == Side.Buy)
				{
					inPosition[sym] = true;
					buyPending[sym] = false;
					entryPrices[sym] = order.AvgPx > 0 ? order.AvgPx : order.Price;
					posQuantities[sym] = order.FilledAmount > 0 ? order.FilledAmount : order.OrderQty;
					highestPrices[sym] = entryPrices[sym];
					Debug($"✅ [DOLDU-AL] {sym} | Fiyat: {entryPrices[sym]:F2} | Adet: {posQuantities[sym]}");
				}
				else if (order.Side.Obj == Side.Sell)
				{
					decimal satisFiyat = order.AvgPx > 0 ? order.AvgPx : order.Price;
					decimal kz = (satisFiyat - entryPrices[sym]) * posQuantities[sym];
					gunlukKZ += kz;

					Debug($"✅ [DOLDU-SAT] {sym} | Fiyat: {satisFiyat:F2} | K/Z: {kz:F2} TL | Gunluk: {gunlukKZ:F2}");

					// KILL-SWITCH kontrolü
					decimal tahminiPortfoy = BasePosValue * 5;
					if (gunlukKZ < 0 && tahminiPortfoy > 0)
					{
						decimal kayipPct = Math.Abs(gunlukKZ) / tahminiPortfoy * 100m;
						if (kayipPct > 3.0m)
						{
							killSwitchAktif = true;
							Debug($"🚨 KILL-SWITCH! Gunluk kayip %{kayipPct:F1} > %3");
						}
					}
					ResetSymbol(sym);
				}
			}
			// === REDDEDİLDİ ===
			else if (order.OrdStatus.Obj == OrdStatus.Rejected)
			{
				if (order.Side.Obj == Side.Buy)
				{
					buyPending[sym] = false;
					ResetSymbol(sym);
					Debug($"❌ [RED-AL] {sym}");
				}
				else
				{
					sellPending[sym] = false;
					Debug($"❌ [RED-SAT] {sym}");
				}
			}
			// === İPTAL ===
			else if (order.OrdStatus.Obj == OrdStatus.Canceled)
			{
				if (order.Side.Obj == Side.Buy)
				{
					buyPending[sym] = false;
					ResetSymbol(sym);
					Debug($"⚠️ [IPTAL-AL] {sym}");
				}
				else
				{
					sellPending[sym] = false;
					Debug($"⚠️ [IPTAL-SAT] {sym}");
				}
			}
			// === KISMİ DOLUM ===
			else if (order.OrdStatus.Obj == OrdStatus.PartiallyFilled)
			{
				if (order.Side.Obj == Side.Buy)
				{
					inPosition[sym] = true;
					buyPending[sym] = false;
					entryPrices[sym] = order.AvgPx > 0 ? order.AvgPx : order.Price;
					posQuantities[sym] = order.FilledAmount;
					highestPrices[sym] = entryPrices[sym];
					Debug($"⚠️ [KISMI-AL] {sym} | {order.FilledAmount}/{order.OrderQty} @ {entryPrices[sym]:F2}");
				}
			}
		}

		private void ResetSymbol(string s)
		{
			inPosition[s] = false;
			posQuantities[s] = 0m;
			entryPrices[s] = 0m;
			highestPrices[s] = 0m;
			sellPending[s] = false;
			buyPending[s] = false;
		}

		public override void OnStopped()
		{
			Debug($"ANKA DURDURULDU | Gunluk K/Z: {gunlukKZ:F2} TL | Emir: {gunlukEmirSayisi} | DryRun: {dryRun}");
		}
	}
}
