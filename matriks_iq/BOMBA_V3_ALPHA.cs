using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
using Matriks.Data.Tick;
using Matriks.Enumeration;
using Newtonsoft.Json;

namespace Matriks.Lean.Algotrader
{
	public class BOMBA_V3_ALPHA : MatriksAlgo
	{
		[Parameter("AYEN,KONTR,EREGL,SASA,GESAN")]
		public string SymbolList;

		[Parameter(15000)]
		public decimal BasePosValue;

		[Parameter(SymbolPeriod.Min30)]
		public SymbolPeriod Period;

		[Parameter(1.2)] public double ProfitTrigger;
		[Parameter(3.5)] public double HardStop;
		[Parameter(1.8)] public double TrailingStop;

		// Köprü Dosyası Yolu
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

		public override void OnInit()
		{
			// 1. Python'dan gelen bomba listesini oku
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

				fastMovs[s] = MOVIndicator(s, Period, OHLCType.Close, 10, MovMethod.Exponential);
				slowMovs[s] = MOVIndicator(s, Period, OHLCType.Close, 20, MovMethod.Exponential);
				rsis[s] = RSIIndicator(s, Period, OHLCType.Close, 14);
				mosts[s] = MOSTIndicator(s, Period, OHLCType.Close, 3, 2m, MovMethod.Exponential);

				ResetSymbol(s);
			}

			SendOrderSequential(true);
		}

		public override void OnDataUpdate(BarDataEventArgs barData)
		{
			if (barData == null || barData.BarData == null) return;
			if (!symbolCache.TryGetValue(barData.SymbolId, out string s)) return;

			// --- [V3 BRIDGE KATMANI - PYTHON'DAN RİSK OKUMA] ---
			decimal macroMultiplier = 1.0m;
			bool isDanger = false;
			try {
				if (File.Exists(bridgePath)) {
					var json = File.ReadAllText(bridgePath);
					dynamic data = JsonConvert.DeserializeObject(json);
					macroMultiplier = (decimal)data.multiplier;
					isDanger = (string)data.regime == "DANGER_CRASH" || macroMultiplier == 0.0m;
				}
			} catch { macroMultiplier = 0.5m; } // Hata anında defansif mod

			// Eğer Python "TEHLİKE" dediyse yeni alımı BLOKE ET
			if (isDanger && !inPosition[s]) return;

			// Bar verileri ve zamanı al
			var barDataModel = GetBarData();
			decimal close = barDataModel.Close[barData.BarDataIndex];
			int currentHour = Hour(barData.BarData);
			int currentMinute = Minute(barData.BarData);

			// 1. ZAMAN FİLTRESİ
			if (currentHour == 12 || (currentHour == 13 && currentMinute < 45)) return;

			// 2. DİNAMİK POZİSYON ÇARPANLARI (Zaman + Makro)
			decimal timeMultiplier = 1.0m;
			if (currentHour == 10 && currentMinute <= 30) timeMultiplier = 1.3m;
			if (currentHour == 17 && currentMinute >= 30) timeMultiplier = 0.6m;

			decimal finalMultiplier = timeMultiplier * macroMultiplier;

			// Teknik Sinyaller
			bool emaOk = fastMovs[s].CurrentValue > slowMovs[s].CurrentValue;
			bool rsiOk = rsis[s].CurrentValue > 50;
			bool trendOk = close > mosts[s].CurrentValue;

			// --- POZİSYON YÖNETİMİ ---
			if (inPosition[s])
			{
				if (close > highestPrices[s]) highestPrices[s] = close;
				decimal pnl = (close - entryPrices[s]) / entryPrices[s] * 100m;

				// Kapanış öncesi kâr realize (>%0.5 kârda ise çık)
				bool exitBeforeClose = (currentHour == 17 && currentMinute >= 50 && pnl > 0.5m);

				decimal stopPrice = entryPrices[s] * (1 - (decimal)HardStop / 100m);
				if (pnl >= (decimal)ProfitTrigger) {
					stopPrice = Math.Max(stopPrice, highestPrices[s] * (1 - (decimal)TrailingStop / 100m));
				}

				if (close <= stopPrice || !emaOk || exitBeforeClose)
				{
					SendMarketOrder(s, posQuantities[s], OrderSide.Sell);
					Debug($"{s} SATILDI | PnL: %{pnl:F2} | Sebep: {(exitBeforeClose ? "GünSonu" : "Stop/Trend")}");
					ResetSymbol(s);
				}
			}
			// --- YENİ GİRİŞ ---
			else
			{
				if (currentHour == 17 && currentMinute >= 30) return;

				if (emaOk && rsiOk && trendOk)
				{
					decimal finalValue = BasePosValue * finalMultiplier;
					decimal qty = Math.Floor(finalValue / close);
					if (qty < 1) return;

					SendMarketOrder(s, qty, OrderSide.Buy);
					inPosition[s] = true;
					posQuantities[s] = qty;
					entryPrices[s] = close;
					highestPrices[s] = close;
					Debug($"{s} ALINDI | Çarpan: {finalMultiplier:F2} | Fiyat: {close:F2}");
				}
			}
		}

		private void ResetSymbol(string s) {
			inPosition[s] = false; posQuantities[s] = 0m; entryPrices[s] = 0m; highestPrices[s] = 0m;
		}

		public override void OnOrderUpdate(IOrder order) {
			if (order.OrdStatus.Obj == OrdStatus.Filled && order.Side.Obj == Side.Sell) {
				if (symbolCache.ContainsValue(order.Symbol)) ResetSymbol(order.Symbol);
			}
		}
	}
}
