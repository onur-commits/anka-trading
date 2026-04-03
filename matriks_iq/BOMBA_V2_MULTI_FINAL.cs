using System;
using System.Collections.Generic;
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
	public class BOMBA_V2_MULTI_FINAL : MatriksAlgo
	{
		[Parameter("AYEN,KONTR,EREGL,SASA,GESAN")]
		public string SymbolList;

		[Parameter(SymbolPeriod.Min30)]
		public SymbolPeriod Period;

		[Parameter(15000)]
		public decimal MaxPosValuePerSymbol;

		// Strateji Parametreleri
		[Parameter(1.2)]
		public decimal ProfitTriggerPercent; // %1.2 Kar sonrası izsüren aktif olur

		[Parameter(3.5)]
		public decimal StopLossPercent; // %3.5 Sabit Stop

		[Parameter(1.8)]
		public decimal TrailingStopPercent; // %1.8 Zirveden dönüş stopu

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

				inPosition[s] = false;
				entryPrices[s] = 0m;
				highestPrices[s] = 0m;
				posQuantities[s] = 0m;
			}

			SendOrderSequential(true);
			WorkWithPermanentSignal(true);
		}

		public override void OnDataUpdate(BarDataEventArgs barData)
		{
			if (barData == null || barData.BarData == null) return;

			if (!symbolCache.TryGetValue(barData.SymbolId, out string s)) return;

			decimal close = barData.BarData.Close;

			if (!fastMovs.ContainsKey(s)) return;

			bool emaCross = fastMovs[s].CurrentValue > slowMovs[s].CurrentValue;
			bool rsiOk = rsis[s].CurrentValue > 50;
			bool trendOk = close > mosts[s].CurrentValue;

			// --- POZİSYON YÖNETİMİ ---
			if (inPosition[s])
			{
				if (close > highestPrices[s]) highestPrices[s] = close;

				decimal currentProfit = (close - entryPrices[s]) / entryPrices[s] * 100m;

				// %3.5 Sabit Sert Stop
				decimal hardStop = entryPrices[s] * (1 - StopLossPercent / 100m);

				// %1.8 İzsüren Stop (Zirveden dönüş)
				decimal trail = highestPrices[s] * (1 - TrailingStopPercent / 100m);

				// KRİTİK: %1.2 karı gördüyse izsüren stopu (trail) kullan, yoksa sert stopu (hardStop) kullan.
				decimal currentStop = (currentProfit >= ProfitTriggerPercent)
					? Math.Max(hardStop, trail) : hardStop;

				if (close <= currentStop || !emaCross)
				{
					decimal qty = posQuantities[s];
					if (qty > 0)
					{
						SendMarketOrder(s, qty, OrderSide.Sell);
						Debug($"{s} SATILDI | Kar: %{currentProfit:F2} | Fiyat: {close:F2}");
						ResetSymbol(s);
					}
				}
			}
			// --- YENİ GİRİŞ ---
			else
			{
				if (emaCross && rsiOk && trendOk)
				{
					decimal qty = Math.Floor(MaxPosValuePerSymbol / close);
					if (qty < 1) return;

					SendMarketOrder(s, qty, OrderSide.Buy);
					inPosition[s] = true;
					posQuantities[s] = qty;
					entryPrices[s] = close;
					highestPrices[s] = close;
					Debug($"{s} ALINDI | Adet: {qty} | Fiyat: {close:F2}");
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
			if (order.OrdStatus.Obj == OrdStatus.Filled)
			{
				if (order.Side.Obj == Side.Sell) ResetSymbol(order.Symbol);
			}
		}

		public override void OnStopped()
		{
			Debug("BOMBA_V2_MULTI_FINAL DURDURULDU.");
		}
	}
}
