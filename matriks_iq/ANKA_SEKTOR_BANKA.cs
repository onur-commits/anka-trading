using System;
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
    // ================================================================
    // ANKA BANKA SEKTORU STRATEJISI
    // Karakter: Agir abi, endeks lokomotifi, CDS duyarli
    // Hisseler: GARAN, AKBNK, ISCTR, YKBNK, HALKB, VAKBN, TSKB, SKBNK
    // Ozel: Genis stop (%2.5), yavas trend takip, faiz hassasiyeti
    // ================================================================
    public class ANKA_SEKTOR_BANKA : MatriksAlgo
    {
        [SymbolParameter("GARAN")]
        public string Symbol;

        [SymbolParameter("XU100")]
        public string IndexSymbol;

        [Parameter(SymbolPeriod.Min15)]
        public SymbolPeriod SymbolPeriod;

        [Parameter(15000)]
        public decimal MaxPositionValue;

        [Parameter(1)]
        public decimal ManualQuantity;

        // BANKA PARAMETRELERI — agir abi karakteri
        [Parameter(8)]
        public int FastPeriod;

        [Parameter(21)]
        public int SlowPeriod;

        [Parameter(14)]
        public int RsiPeriod;

        [Parameter(50)]
        public decimal RsiThreshold;  // Bankalar icin 50 (daha dusuk esik)

        [Parameter(2.5)]
        public decimal StopLossPercent;  // Genis stop — bankalar yavas hareket eder

        [Parameter(2.0)]
        public decimal TrailingStopPercent;  // Genis trailing

        [Parameter(1.0)]
        public decimal TrailingActivationPercent;

        [Parameter(0.8)]
        public decimal BreakEvenActivationPercent;

        [Parameter(0.3)]
        public decimal TrendStrengthPercent;

        [Parameter(true)]
        public bool UseIndexFilter;

        [Parameter(10)]
        public int StartHour;

        [Parameter(0)]
        public int StartMinute;

        [Parameter(18)]
        public int EndHour;

        [Parameter(0)]
        public int EndMinute;

        MOV fastMov;
        MOV slowMov;
        MOV indexFastMov;
        MOV indexSlowMov;
        RSI rsi;

        bool inPosition = false;
        decimal entryPrice = 0m;
        decimal highestPriceSinceEntry = 0m;
        decimal currentPositionQty = 0m;

        [Output] public decimal FastEMA;
        [Output] public decimal SlowEMA;
        [Output] public decimal RSIValue;
        [Output] public decimal EffectiveStopLevel;
        [Output] public decimal PositionQty;
        [Output] public decimal PositionValue;

        public override void OnInit()
        {
            AddSymbol(Symbol, SymbolPeriod);
            AddSymbol(IndexSymbol, SymbolPeriod);
            fastMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            slowMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);
            indexFastMov = MOVIndicator(IndexSymbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            indexSlowMov = MOVIndicator(IndexSymbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);
            rsi = RSIIndicator(Symbol, SymbolPeriod, OHLCType.Close, RsiPeriod);
            SendOrderSequential(true);
            WorkWithPermanentSignal(true);
        }

        public override void OnInitCompleted()
        {
            Debug("ANKA BANKA [" + Symbol + "] hazir. Max:" + MaxPositionValue + " TL Stop:" + StopLossPercent + "%");
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (barData == null || barData.BarData == null) return;
            DateTime barTime = barData.BarData.Dtime;
            if (!IsTradingTime(barTime)) return;
            decimal closePrice = barData.BarData.Close;
            if (closePrice <= 0) return;

            // Endeks filtresi
            bool indexOk = true;
            if (UseIndexFilter)
                indexOk = indexFastMov.CurrentValue > indexSlowMov.CurrentValue;

            // Momentum — bankalar icin daha dusuk esik
            bool momentumOk = rsi.CurrentValue > RsiThreshold;

            // Trend gucu
            decimal trendStrength = 0m;
            if (slowMov.CurrentValue != 0)
                trendStrength = Math.Abs(fastMov.CurrentValue - slowMov.CurrentValue) / slowMov.CurrentValue * 100m;
            bool trendStrong = trendStrength >= TrendStrengthPercent;

            // STOP SISTEMI — bankalar icin genis
            bool stopTriggered = false;
            decimal effectiveStopLevel = 0m;

            if (inPosition && entryPrice > 0)
            {
                if (closePrice > highestPriceSinceEntry) highestPriceSinceEntry = closePrice;

                decimal fixedStop = entryPrice * (1 - StopLossPercent / 100m);
                effectiveStopLevel = fixedStop;

                // Break-even
                if (highestPriceSinceEntry >= entryPrice * (1 + BreakEvenActivationPercent / 100m))
                    effectiveStopLevel = Math.Max(effectiveStopLevel, entryPrice);

                // Trailing
                if (highestPriceSinceEntry >= entryPrice * (1 + TrailingActivationPercent / 100m))
                {
                    decimal trail = highestPriceSinceEntry * (1 - TrailingStopPercent / 100m);
                    effectiveStopLevel = Math.Max(effectiveStopLevel, trail);
                }

                EffectiveStopLevel = Math.Round(effectiveStopLevel, 2);
                if (closePrice <= effectiveStopLevel) stopTriggered = true;
            }
            else
            {
                EffectiveStopLevel = 0m;
            }

            // SINYALLER
            bool buySignal = fastMov.CurrentValue > slowMov.CurrentValue
                             && indexOk && momentumOk && trendStrong && !inPosition;

            bool sellSignal = (fastMov.CurrentValue < slowMov.CurrentValue || stopTriggered)
                              && inPosition;

            // ALIS — otomatik adet hesaplama
            if (buySignal)
            {
                decimal buyQty;
                if (MaxPositionValue > 0)
                { buyQty = Math.Floor(MaxPositionValue / closePrice); if (buyQty < 1) buyQty = 1; }
                else { buyQty = ManualQuantity; }
                currentPositionQty = buyQty;
                SendMarketOrder(Symbol, buyQty, OrderSide.Buy);
                entryPrice = closePrice;
                highestPriceSinceEntry = closePrice;
                Debug("BANKA ALIS: " + Symbol + " " + buyQty + " lot @ " + Math.Round(closePrice, 2));
            }

            // SATIS
            if (sellSignal)
            {
                decimal sellQty = currentPositionQty > 0 ? currentPositionQty : ManualQuantity;
                SendMarketOrder(Symbol, sellQty, OrderSide.Sell);
                Debug("BANKA SATIS: " + Symbol + " " + sellQty + " lot");
            }

            FastEMA = Math.Round(fastMov.CurrentValue, 2);
            SlowEMA = Math.Round(slowMov.CurrentValue, 2);
            RSIValue = Math.Round(rsi.CurrentValue, 2);
            PositionQty = currentPositionQty;
            PositionValue = inPosition ? Math.Round(currentPositionQty * closePrice, 0) : 0m;
        }

        public override void OnOrderUpdate(IOrder order)
        {
            if (order == null || order.Symbol != Symbol) return;
            if (order.OrdStatus.Obj == OrdStatus.Filled)
            {
                if (order.Side.Obj == Side.Buy) { inPosition = true; }
                if (order.Side.Obj == Side.Sell)
                {
                    inPosition = false; entryPrice = 0m; highestPriceSinceEntry = 0m;
                    currentPositionQty = 0m; EffectiveStopLevel = 0m;
                    PositionQty = 0m; PositionValue = 0m;
                }
            }
        }

        public override void OnStopped() { }

        private bool IsTradingTime(DateTime barTime)
        {
            int nowValue = barTime.Hour * 100 + barTime.Minute;
            int startValue = StartHour * 100 + StartMinute;
            int endValue = EndHour * 100 + EndMinute;
            return nowValue >= startValue && nowValue <= endValue;
        }
    }
}
