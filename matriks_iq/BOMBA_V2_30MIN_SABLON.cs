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
    public class BOMBA_TICKER : MatriksAlgo
    {
        [SymbolParameter("TICKER")]
        public string Symbol;

        [Parameter(SymbolPeriod.Min30)]
        public SymbolPeriod SymbolPeriod;

        [Parameter(15000)]
        public decimal MaxPositionValue;

        [Parameter(10)]
        public int FastPeriod;

        [Parameter(20)]
        public int SlowPeriod;

        [Parameter(14)]
        public int RsiPeriod;

        [Parameter(50)]
        public decimal RsiThreshold;

        [Parameter(3.5)]
        public decimal StopLossPercent;

        [Parameter(1.8)]
        public decimal TrailingStopPercent;

        MOV fastMov, slowMov;
        RSI rsi;
        MOST most;

        bool inPosition = false;
        decimal entryPrice = 0m;
        decimal highestPrice = 0m;
        decimal posQty = 0m;

        public override void OnInit()
        {
            AddSymbol(Symbol, SymbolPeriod);
            fastMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            slowMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);
            rsi = RSIIndicator(Symbol, SymbolPeriod, OHLCType.Close, RsiPeriod);
            most = MOSTIndicator(Symbol, SymbolPeriod, OHLCType.Close, 3, 2, MovMethod.Exponential);
            SendOrderSequential(true);
            WorkWithPermanentSignal(true);
        }

        public override void OnInitCompleted()
        {
            Debug("BOMBA_TICKER HAZIR - V2 30DK");
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (barData == null || barData.BarData == null) return;
            decimal close = barData.BarData.Close;

            bool emaCross = fastMov.CurrentValue > slowMov.CurrentValue;
            bool rsiOk = rsi.CurrentValue > RsiThreshold;
            bool trendOk = close > most.CurrentValue;

            if (inPosition)
            {
                if (close > highestPrice) highestPrice = close;
                decimal hardStop = entryPrice * (1 - StopLossPercent / 100m);
                decimal trailingStop = highestPrice * (1 - TrailingStopPercent / 100m);
                decimal currentStop = (highestPrice >= entryPrice * 1.012m) ? Math.Max(hardStop, trailingStop) : hardStop;

                if (close <= currentStop || !emaCross)
                {
                    SendMarketOrder(Symbol, posQty, OrderSide.Sell);
                    ResetPosition();
                }
            }
            else
            {
                if (emaCross && rsiOk && trendOk)
                {
                    decimal qty = Math.Floor(MaxPositionValue / close);
                    if (qty < 1) qty = 1;
                    posQty = qty;
                    entryPrice = close;
                    highestPrice = close;
                    SendMarketOrder(Symbol, qty, OrderSide.Buy);
                    inPosition = true;
                }
            }
        }

        private void ResetPosition() { inPosition = false; entryPrice = 0m; highestPrice = 0m; posQty = 0m; }
        public override void OnOrderUpdate(IOrder order) { if (order.OrdStatus.Obj == OrdStatus.Filled && order.Side.Obj == Side.Sell) ResetPosition(); }
    }
}
