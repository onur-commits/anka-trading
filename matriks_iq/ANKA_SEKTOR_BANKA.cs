using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
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
using Matriks.Data.Tick;
using Matriks.Enumeration;

namespace Matriks.Lean.Algotrader
{
    public class ANKA_SEKTOR_BANKA : MatriksAlgo
    {
        string[] symbols = { "AKBNK", "GARAN", "HALKB", "ISCTR", "SKBNK", "TSKB", "VAKBN", "YKBNK" };

        [SymbolParameter("XU100")]
        public string IndexSymbol;

        [Parameter(SymbolPeriod.Min15)]
        public SymbolPeriod SymbolPeriod;

        [Parameter(15000)]
        public decimal MaxPositionValue;

        [Parameter(8)]
        public int FastPeriod;

        [Parameter(21)]
        public int SlowPeriod;

        [Parameter(14)]
        public int RsiPeriod;

        [Parameter(50)]
        public decimal RsiThreshold;

        [Parameter(2.5)]
        public decimal StopLossPercent;

        [Parameter(2.0)]
        public decimal TrailingStopPercent;

        [Parameter(1.0)]
        public decimal TrailingActivationPercent;

        [Parameter(0.8)]
        public decimal BreakEvenActivationPercent;

        [Parameter(0.3)]
        public decimal TrendStrengthPercent;

        [Parameter(true)]
        public bool UseIndexFilter;

        [Parameter(true)]
        public bool UseAiSignal;

        [Parameter(10)]
        public int StartHour;

        [Parameter(18)]
        public int EndHour;

        string sinyalDosyasi = @"C:\ANKA\data\ai_sinyaller.txt";

        Dictionary<string, bool> inPosition;
        Dictionary<string, decimal> entryPrice;
        Dictionary<string, decimal> highestPrice;
        Dictionary<string, decimal> positionQty;
        Dictionary<string, MOV> fastMovs;
        Dictionary<string, MOV> slowMovs;
        Dictionary<string, RSI> rsiIndicators;

        MOV indexFastMov;
        MOV indexSlowMov;

        public override void OnInit()
        {
            inPosition = new Dictionary<string, bool>();
            entryPrice = new Dictionary<string, decimal>();
            highestPrice = new Dictionary<string, decimal>();
            positionQty = new Dictionary<string, decimal>();
            fastMovs = new Dictionary<string, MOV>();
            slowMovs = new Dictionary<string, MOV>();
            rsiIndicators = new Dictionary<string, RSI>();

            foreach (var sym in symbols)
            {
                AddSymbol(sym, SymbolPeriod);
                fastMovs[sym] = MOVIndicator(sym, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
                slowMovs[sym] = MOVIndicator(sym, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);
                rsiIndicators[sym] = RSIIndicator(sym, SymbolPeriod, OHLCType.Close, RsiPeriod);
                inPosition[sym] = false;
                entryPrice[sym] = 0m;
                highestPrice[sym] = 0m;
                positionQty[sym] = 0m;
            }

            AddSymbol(IndexSymbol, SymbolPeriod);
            indexFastMov = MOVIndicator(IndexSymbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            indexSlowMov = MOVIndicator(IndexSymbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);

            SendOrderSequential(true);
            WorkWithPermanentSignal(true);
        }

        public override void OnInitCompleted()
        {
            Debug("ANKA_SEKTOR_BANKA hazir. " + symbols.Length + " sembol takipte.");
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (barData == null || barData.BarData == null) return;

            string sym = barData.Symbol;

            if (!symbols.Contains(sym)) return;

            decimal closePrice = barData.BarData.Close;
            if (closePrice <= 0) return;

            DateTime barTime = barData.BarData.Dtime;
            int nowVal = barTime.Hour * 100 + barTime.Minute;
            if (nowVal < StartHour * 100 || nowVal > EndHour * 100) return;

            // AI sinyal
            bool aiBuy = false;
            bool aiSell = false;
            if (UseAiSignal)
            {
                try
                {
                    if (File.Exists(sinyalDosyasi))
                    {
                        var satirlar = File.ReadAllLines(sinyalDosyasi);
                        aiBuy = satirlar.Contains(sym + "_AL");
                        aiSell = satirlar.Contains(sym + "_SAT");
                    }
                }
                catch { }
            }

            // Endeks filtresi
            bool indexOk = true;
            if (UseIndexFilter)
                indexOk = indexFastMov.CurrentValue > indexSlowMov.CurrentValue;

            // Teknik
            bool emaOk = fastMovs[sym].CurrentValue > slowMovs[sym].CurrentValue;
            bool momentumOk = rsiIndicators[sym].CurrentValue > RsiThreshold;

            decimal trendStrength = 0m;
            if (slowMovs[sym].CurrentValue != 0)
                trendStrength = Math.Abs(fastMovs[sym].CurrentValue - slowMovs[sym].CurrentValue) / slowMovs[sym].CurrentValue * 100m;
            bool trendStrong = trendStrength >= TrendStrengthPercent;

            // Stop sistemi
            bool stopTriggered = false;
            if (inPosition[sym] && entryPrice[sym] > 0)
            {
                if (closePrice > highestPrice[sym])
                    highestPrice[sym] = closePrice;

                decimal fixedStop = entryPrice[sym] * (1 - StopLossPercent / 100m);
                decimal effectiveStop = fixedStop;

                if (highestPrice[sym] >= entryPrice[sym] * (1 + BreakEvenActivationPercent / 100m))
                    effectiveStop = Math.Max(effectiveStop, entryPrice[sym]);

                if (highestPrice[sym] >= entryPrice[sym] * (1 + TrailingActivationPercent / 100m))
                {
                    decimal trailStop = highestPrice[sym] * (1 - TrailingStopPercent / 100m);
                    effectiveStop = Math.Max(effectiveStop, trailStop);
                }

                if (closePrice <= effectiveStop)
                {
                    stopTriggered = true;
                    Debug(sym + " STOP @ " + Math.Round(closePrice, 2));
                }
            }

            // Sinyal
            bool buySignal;
            bool sellSignal;

            if (UseAiSignal && (aiBuy || aiSell))
            {
                buySignal = aiBuy && indexOk && !inPosition[sym];
                sellSignal = (aiSell || stopTriggered) && inPosition[sym];
            }
            else
            {
                buySignal = emaOk && indexOk && momentumOk && trendStrong && !inPosition[sym];
                sellSignal = (!emaOk || stopTriggered) && inPosition[sym];
            }

            // Alis
            if (buySignal)
            {
                decimal buyQty = 1;
                if (MaxPositionValue > 0)
                {
                    buyQty = Math.Floor(MaxPositionValue / closePrice);
                    if (buyQty < 1) buyQty = 1;
                }
                positionQty[sym] = buyQty;
                SendMarketOrder(sym, buyQty, OrderSide.Buy);
                entryPrice[sym] = closePrice;
                highestPrice[sym] = closePrice;
                Debug(sym + " ALIS: " + buyQty + " lot @ " + Math.Round(closePrice, 2));
            }

            // Satis
            if (sellSignal)
            {
                decimal sellQty = positionQty[sym] > 0 ? positionQty[sym] : 1;
                SendMarketOrder(sym, sellQty, OrderSide.Sell);
                Debug(sym + " SATIS: " + sellQty + " lot");
            }
        }

        public override void OnOrderUpdate(IOrder order)
        {
            if (order == null) return;
            string sym = order.Symbol;
            if (!symbols.Contains(sym)) return;

            if (order.OrdStatus.Obj == OrdStatus.Filled)
            {
                if (order.Side.Obj == Side.Buy)
                {
                    inPosition[sym] = true;
                    Debug(sym + " ALIS gerceklesti: " + positionQty[sym] + " lot");
                }
                if (order.Side.Obj == Side.Sell)
                {
                    inPosition[sym] = false;
                    entryPrice[sym] = 0m;
                    highestPrice[sym] = 0m;
                    positionQty[sym] = 0m;
                    Debug(sym + " SATIS gerceklesti. Pozisyon kapatildi.");
                }
            }
        }

        public override void OnStopped()
        {
            Debug("ANKA_SEKTOR_BANKA durduruldu.");
        }
    }
}
