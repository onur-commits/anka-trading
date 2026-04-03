using System;
using System.Collections.Generic;
using System.IO;
using Matriks.Data.Symbol;
using Matriks.Engines;
using Matriks.Indicators;
using Matriks.Symbols;
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
	public class BOMBA_V3_TURBO : MatriksAlgo
	{
		[Parameter("AYEN,KONTR,EREGL,SASA,GESAN")]
		public string SymbolList;

		[Parameter(1000)]
		public decimal BasePosValue;

		[Parameter(SymbolPeriod.Min5)]
		public SymbolPeriod Period;

		[Parameter(0.7)] public double ProfitTrigger;
		[Parameter(2.0)] public double HardStop;
		[Parameter(0.5)] public double TrailingStop;

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

		// --- EMİR KİLİDİ: Aynı barda tekrar alımı engeller ---
		Dictionary<string, int> lastOrderBarIndex = new Dictionary<string, int>();

		public override void OnInit()
		{
			string path = @"C:\Robot\aktif_bombalar.txt";
			if (File.Exists(path))
			{
				string fileContent = File.ReadAllText(path);
				if (!string.IsNullOrEmpty(fileContent)) SymbolList = fileContent;
			}

			string[] symbols = SymbolList.Split(',');
			foreach (var sym in symbols)
			{
				string s = sym.Trim().ToUpper();
				if (string.IsNullOrEmpty(s)) continue;

				AddSymbol(s, Period);
				symbolCache[GetSymbolId(s)] = s;

				fastMovs[s] = MOVIndicator(s, Period, OHLCType.Close, 5, MovMethod.Exponential);
				slowMovs[s] = MOVIndicator(s, Period, OHLCType.Close, 13, MovMethod.Exponential);
				rsis[s] = RSIIndicator(s, Period, OHLCType.Close, 14);
				mosts[s] = MOSTIndicator(s, Period, OHLCType.Close, 3, 1.5m, MovMethod.Exponential);

				inPosition[s] = false;
				entryPrices[s] = 0m;
				highestPrices[s] = 0m;
				posQuantities[s] = 0m;
				lastOrderBarIndex[s] = -1;
			}
			SendOrderSequential(true);
			WorkWithPermanentSignal(false);
		}

		public override void OnDataUpdate(BarDataEventArgs barData)
		{
			if (barData == null || barData.BarData == null) return;
			if (!symbolCache.TryGetValue(barData.SymbolId, out string s)) return;

			decimal close = barData.BarData.Close;
			int currentHour = Hour(barData.BarData);
			int currentMinute = Minute(barData.BarData);
			int currentBarIndex = barData.BarDataIndex;

			// Bridge Okuma
			decimal macroMultiplier = 1.0m;
			try {
				if (File.Exists(bridgePath)) {
					dynamic data = JsonConvert.DeserializeObject(File.ReadAllText(bridgePath));
					if (data != null) {
						macroMultiplier = (decimal)data.multiplier;
						if (data.pos_value != null) BasePosValue = (decimal)data.pos_value;
						if ((string)data.regime == "DANGER_CRASH" && !inPosition[s]) return;
					}
				}
			} catch { macroMultiplier = 1.0m; }

			if (currentHour == 12 || (currentHour == 13 && currentMinute < 30)) return;

			bool emaOk = fastMovs[s].CurrentValue > slowMovs[s].CurrentValue;
			bool rsiOk = rsis[s].CurrentValue > 45;
			bool trendOk = close > mosts[s].CurrentValue;

			if (inPosition[s])
			{
				if (close > highestPrices[s]) highestPrices[s] = close;
				decimal pnl = (close - entryPrices[s]) / entryPrices[s] * 100m;

				decimal stopPrice = entryPrices[s] * (1 - (decimal)HardStop / 100m);
				if (pnl >= (decimal)ProfitTrigger) {
					stopPrice = Math.Max(stopPrice, highestPrices[s] * (1 - (decimal)TrailingStop / 100m));
				}

				if (close <= stopPrice || !emaOk)
				{
					SendMarketOrder(s, posQuantities[s], OrderSide.Sell);
					Debug($"[TURBO-SAT] {s} | PnL: %{pnl:F2}");
					ResetSymbol(s);
				}
			}
			else
			{
				if (currentHour == 17 && currentMinute >= 45) return;

				// --- KİLİT KONTROLÜ ---
				if (currentBarIndex == lastOrderBarIndex[s]) return;

				if (emaOk && rsiOk && trendOk)
				{
					decimal finalValue = BasePosValue * macroMultiplier;
					decimal qty = Math.Floor(finalValue / close);
					if (qty < 1) return;

					SendMarketOrder(s, qty, OrderSide.Buy);

					inPosition[s] = true;
					posQuantities[s] = qty;
					entryPrices[s] = close;
					highestPrices[s] = close;
					lastOrderBarIndex[s] = currentBarIndex;

					Debug($"[TURBO-AL] {s} | Adet: {qty} | Fiyat: {close:F2}");
				}
			}
		}

		private void ResetSymbol(string s)
		{
			inPosition[s] = false;
			posQuantities[s] = 0m;
			entryPrices[s] = 0m;
			highestPrices[s] = 0m;
		}

		public override void OnOrderUpdate(IOrder order)
		{
			if (order.OrdStatus.Obj == OrdStatus.Filled && order.Side.Obj == Side.Sell)
			{
				if (symbolCache.ContainsValue(order.Symbol)) ResetSymbol(order.Symbol);
			}
		}
	}
}
