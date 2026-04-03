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
using Newtonsoft.Json;

namespace Matriks.Lean.Algotrader
{
    // 2026-04-02 - Bomba Skor: 53/100
    // Sebepler: 🧠 ML:78% GÜÇLÜ + ⬇️ RSI7:6 AŞIRI SATIM + 📉 Boll ALT BAND
    public class BOMBA_KONTR : MatriksAlgo
    {
        [SymbolParameter("KONTR")]
        public string Symbol;

        [Parameter(SymbolPeriod.Min60)]
        public SymbolPeriod SymbolPeriod;

        [Parameter(15000)]
        public decimal MaxPositionValue;

        [Parameter(1)]
        public decimal ManualQuantity;

        [Parameter(10)]
        public int FastPeriod;

        [Parameter(20)]
        public int SlowPeriod;

        [Parameter(14)]
        public int RsiPeriod;

        [Parameter(50)]
        public decimal RsiThreshold;

        [Parameter(6.0)]
        public decimal StopLossPercent;

        [Parameter(2.5)]
        public decimal TrailingStopPercent;

        MOV fastMov, slowMov;
        RSI rsi;
        bool inPosition = false;
        decimal entryPrice = 0m;
        decimal highestPrice = 0m;
        decimal posQty = 0m;

        [Output] public decimal RSIValue;
        [Output] public decimal PnL;

        public override void OnInit()
        {
            AddSymbol(Symbol, SymbolPeriod);
            fastMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            slowMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);
            rsi = RSIIndicator(Symbol, SymbolPeriod, OHLCType.Close, RsiPeriod);
            SendOrderSequential(true);
            WorkWithPermanentSignal(true);
        }

        public override void OnInitCompleted()
        {
            Debug("BOMBA_KONTR AKTIF - Skor:53");
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (barData == null || barData.BarData == null) return;
            decimal close = barData.BarData.Close;
            if (close <= 0) return;

            bool emaOk = fastMov.CurrentValue > slowMov.CurrentValue;
            bool rsiOk = rsi.CurrentValue > RsiThreshold;
            RSIValue = Math.Round(rsi.CurrentValue, 2);

            if (inPosition && entryPrice > 0)
            {
                if (close > highestPrice) highestPrice = close;
                decimal stop = entryPrice * (1 - StopLossPercent / 100m);
                if (highestPrice >= entryPrice * 1.015m)
                {
                    decimal trail = highestPrice * (1 - TrailingStopPercent / 100m);
                    stop = Math.Max(stop, trail);
                }
                PnL = Math.Round((close - entryPrice) / entryPrice * 100m, 2);
                if (close <= stop || !emaOk)
                {
                    SendMarketOrder(Symbol, posQty, OrderSide.Sell);
                    Debug("SATIS: " + posQty + " lot | PnL: %" + PnL);
                }
            }
            else
            {
                if (emaOk && rsiOk)
                {
                    decimal qty = Math.Floor(MaxPositionValue / close);
                    if (qty < 1) qty = 1;
                    posQty = qty;
                    SendMarketOrder(Symbol, qty, OrderSide.Buy);
                    entryPrice = close;
                    highestPrice = close;
                    Debug("ALIS: " + qty + " lot x " + Math.Round(close, 2) + " TL");
                }
            }
        }

        public override void OnOrderUpdate(IOrder order)
        {
            if (order == null || order.Symbol != Symbol) return;
            if (order.OrdStatus.Obj == OrdStatus.Filled)
            {
                if (order.Side.Obj == Side.Buy) inPosition = true;
                if (order.Side.Obj == Side.Sell)
                { inPosition = false; entryPrice = 0m; highestPrice = 0m; posQty = 0m; PnL = 0m; }
            }
        }

        public override void OnStopped() { }
    }
}