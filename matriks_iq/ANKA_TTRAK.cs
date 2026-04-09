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
using Matriks.IntermediaryInstitutionAnalysis.Enums;
using Newtonsoft.Json;

namespace Matriks.Lean.Algotrader
{
    public class ANKA_TTRAK : MatriksAlgo
    {
        [SymbolParameter("TTRAK")]
        public string Symbol;

        [SymbolParameter("XU100")]
        public string IndexSymbol;

        [Parameter(SymbolPeriod.Min15)]
        public SymbolPeriod SymbolPeriod;

        // --- POZİSYON BOYUTU ---
        // MaxPositionValue > 0 ise otomatik hesapla (TL cinsinden bütçe)
        // MaxPositionValue = 0 ise ManualQuantity kullan
        [Parameter(15000)]
        public decimal MaxPositionValue;   // Örn: 10000 = bu hisseye max 10.000 TL

        [Parameter(1)]
        public decimal ManualQuantity;     // MaxPositionValue=0 ise bu adet kullanılır

        [Parameter(8)]
        public int FastPeriod;

        [Parameter(21)]
        public int SlowPeriod;

        [Parameter(14)]
        public int RsiPeriod;

        [Parameter(52)]
        public decimal RsiThreshold;

        [Parameter(2.0)]
        public decimal StopLossPercent;

        [Parameter(1.5)]
        public decimal TrailingStopPercent;

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
        decimal currentPositionQty = 0m;   // Aldığımız lot adedi (satışta kullanılır)

        [Output] public decimal FastEMA;
        [Output] public decimal SlowEMA;
        [Output] public decimal IndexFastEMA;
        [Output] public decimal IndexSlowEMA;
        [Output] public decimal RSIValue;
        [Output] public decimal StopLevel;
        [Output] public decimal TrailingStopLevel;
        [Output] public decimal HighestPrice;
        [Output] public decimal TrailingActivationLevel;
        [Output] public decimal BreakEvenActivationLevel;
        [Output] public decimal EffectiveStopLevel;
        [Output] public decimal TrendStrengthValue;
        [Output] public decimal PositionQty;       // Kaç lot pozisyon açıldı
        [Output] public decimal PositionValue;     // Pozisyon TL değeri

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
            string modText = MaxPositionValue > 0
                ? string.Format("Otomatik boyut: {0} TL", MaxPositionValue)
                : string.Format("Manuel adet: {0} lot", ManualQuantity);
            Debug("ANKA_TTRAK hazir. " + modText);
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (barData == null || barData.BarData == null)
                return;

            DateTime barTime = barData.BarData.Dtime;

            if (!IsTradingTime(barTime))
                return;

            decimal closePrice = barData.BarData.Close;
            if (closePrice <= 0)
                return;

            bool indexOk = true;
            if (UseIndexFilter)
                indexOk = indexFastMov.CurrentValue > indexSlowMov.CurrentValue;

            bool momentumOk = rsi.CurrentValue > RsiThreshold;

            decimal trendStrength = 0m;
            if (slowMov.CurrentValue != 0)
                trendStrength = Math.Abs(fastMov.CurrentValue - slowMov.CurrentValue) / slowMov.CurrentValue * 100m;

            bool trendStrong = trendStrength >= TrendStrengthPercent;

            bool stopTriggered = false;
            decimal fixedStopLevel = 0m;
            decimal trailingStopLevel = 0m;
            decimal trailingActivationLevel = 0m;
            decimal breakEvenActivationLevel = 0m;
            decimal effectiveStopLevel = 0m;

            if (inPosition && entryPrice > 0)
            {
                if (closePrice > highestPriceSinceEntry)
                    highestPriceSinceEntry = closePrice;

                fixedStopLevel = entryPrice * (1 - StopLossPercent / 100m);
                trailingActivationLevel = entryPrice * (1 + TrailingActivationPercent / 100m);
                breakEvenActivationLevel = entryPrice * (1 + BreakEvenActivationPercent / 100m);

                effectiveStopLevel = fixedStopLevel;

                if (highestPriceSinceEntry >= breakEvenActivationLevel)
                    effectiveStopLevel = Math.Max(effectiveStopLevel, entryPrice);

                if (highestPriceSinceEntry >= trailingActivationLevel)
                {
                    trailingStopLevel = highestPriceSinceEntry * (1 - TrailingStopPercent / 100m);
                    effectiveStopLevel = Math.Max(effectiveStopLevel, trailingStopLevel);
                    TrailingStopLevel = Math.Round(trailingStopLevel, 2);
                }
                else
                {
                    TrailingStopLevel = 0m;
                }

                StopLevel = Math.Round(fixedStopLevel, 2);
                TrailingActivationLevel = Math.Round(trailingActivationLevel, 2);
                BreakEvenActivationLevel = Math.Round(breakEvenActivationLevel, 2);
                HighestPrice = Math.Round(highestPriceSinceEntry, 2);
                EffectiveStopLevel = Math.Round(effectiveStopLevel, 2);

                if (closePrice <= effectiveStopLevel)
                {
                    if (effectiveStopLevel == entryPrice)
                        Debug("BREAK-EVEN CALISTI");
                    else if (trailingStopLevel > 0m && effectiveStopLevel == trailingStopLevel)
                        Debug("TRAILING STOP CALISTI");
                    else
                        Debug("SABIT STOP CALISTI");

                    stopTriggered = true;
                }
            }
            else
            {
                StopLevel = 0m;
                TrailingStopLevel = 0m;
                HighestPrice = 0m;
                TrailingActivationLevel = 0m;
                BreakEvenActivationLevel = 0m;
                EffectiveStopLevel = 0m;
            }

            bool buySignal = fastMov.CurrentValue > slowMov.CurrentValue
                             && indexOk
                             && momentumOk
                             && trendStrong
                             && !inPosition;

            bool sellSignal = (fastMov.CurrentValue < slowMov.CurrentValue || stopTriggered)
                              && inPosition;

            if (buySignal)
            {
                // --- OTOMATİK POZİSYON BOYUTU ---
                decimal buyQty;
                if (MaxPositionValue > 0)
                {
                    buyQty = Math.Floor(MaxPositionValue / closePrice);
                    if (buyQty < 1) buyQty = 1;
                }
                else
                {
                    buyQty = ManualQuantity;
                }

                currentPositionQty = buyQty;
                SendMarketOrder(Symbol, buyQty, OrderSide.Buy);
                entryPrice = closePrice;
                highestPriceSinceEntry = closePrice;

                Debug(string.Format("ALIS emri: {0} lot x {1} TL = {2} TL",
                    buyQty, Math.Round(closePrice, 2), Math.Round(buyQty * closePrice, 0)));
            }

            if (sellSignal)
            {
                decimal sellQty = currentPositionQty > 0 ? currentPositionQty : ManualQuantity;
                SendMarketOrder(Symbol, sellQty, OrderSide.Sell);
                Debug(string.Format("SATIS emri: {0} lot", sellQty));
            }

            FastEMA = Math.Round(fastMov.CurrentValue, 2);
            SlowEMA = Math.Round(slowMov.CurrentValue, 2);
            IndexFastEMA = Math.Round(indexFastMov.CurrentValue, 2);
            IndexSlowEMA = Math.Round(indexSlowMov.CurrentValue, 2);
            RSIValue = Math.Round(rsi.CurrentValue, 2);
            TrendStrengthValue = Math.Round(trendStrength, 2);
            PositionQty = currentPositionQty;
            PositionValue = inPosition ? Math.Round(currentPositionQty * closePrice, 0) : 0m;
        }

        public override void OnOrderUpdate(IOrder order)
        {
            if (order == null)
                return;

            if (order.Symbol != Symbol)
                return;

            if (order.OrdStatus.Obj == OrdStatus.Filled)
            {
                if (order.Side.Obj == Side.Buy)
                {
                    inPosition = true;
                    Debug(string.Format("ALIS gerceklesti: {0} lot", currentPositionQty));
                }

                if (order.Side.Obj == Side.Sell)
                {
                    inPosition = false;
                    entryPrice = 0m;
                    highestPriceSinceEntry = 0m;
                    currentPositionQty = 0m;
                    StopLevel = 0m;
                    TrailingStopLevel = 0m;
                    HighestPrice = 0m;
                    TrailingActivationLevel = 0m;
                    BreakEvenActivationLevel = 0m;
                    EffectiveStopLevel = 0m;
                    PositionQty = 0m;
                    PositionValue = 0m;
                    Debug("SATIS gerceklesti. Pozisyon kapatildi.");
                }
            }
        }

        public override void OnStopped()
        {
        }

        private bool IsTradingTime(DateTime barTime)
        {
            int nowValue = barTime.Hour * 100 + barTime.Minute;
            int startValue = StartHour * 100 + StartMinute;
            int endValue = EndHour * 100 + EndMinute;
            return nowValue >= startValue && nowValue <= endValue;
        }
    }
}
