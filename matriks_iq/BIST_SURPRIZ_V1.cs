// ============================================================
// BIST_SURPRIZ_V1 — Surpriz Bulucu + Trend Algo
// Mantik: EMA trend + RSI + Bollinger Squeeze + Hacim Anomali
// Platform: Matriks IQ
// ============================================================

using System;
using System.Collections.Generic;
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
    public class BIST_SURPRIZ_V1 : MatriksAlgo
    {
        // ==================== SEMBOLLER ====================
        [SymbolParameter("GARAN")]
        public string Symbol;

        [SymbolParameter("XU100")]
        public string IndexSymbol;

        [Parameter(SymbolPeriod.Min15)]
        public SymbolPeriod SymbolPeriod;

        // ==================== EMIR ====================
        [Parameter(1)]
        public decimal BuyOrderQuantity;

        [Parameter(1)]
        public decimal SellOrderQuantity;

        // ==================== TREND ====================
        [Parameter(8)]
        public int FastPeriod;

        [Parameter(21)]
        public int SlowPeriod;

        // ==================== RSI ====================
        [Parameter(14)]
        public int RsiPeriod;

        [Parameter(52)]
        public decimal RsiThreshold;

        // ==================== BOLLINGER ====================
        [Parameter(20)]
        public int BollingerPeriod;

        [Parameter(2.0)]
        public decimal BollingerStdDev;

        [Parameter(true)]
        public bool UseBollingerSqueeze;

        // ==================== HACIM ====================
        [Parameter(20)]
        public int VolumeMaPeriod;

        [Parameter(1.5)]
        public decimal VolumeMultiplier;

        [Parameter(true)]
        public bool UseVolumeFilter;

        // ==================== RISK ====================
        [Parameter(2.0)]
        public decimal StopLossPercent;

        [Parameter(1.5)]
        public decimal TrailingStopPercent;

        [Parameter(1.0)]
        public decimal TrailingActivationPercent;

        [Parameter(0.8)]
        public decimal BreakEvenActivationPercent;

        // ==================== FILTRELER ====================
        [Parameter(0.2)]
        public decimal TrendStrengthPercent;

        [Parameter(true)]
        public bool UseIndexFilter;

        // ==================== SAAT ====================
        [Parameter(10)]
        public int StartHour;

        [Parameter(0)]
        public int StartMinute;

        [Parameter(18)]
        public int EndHour;

        [Parameter(0)]
        public int EndMinute;

        // ==================== INDIKATÖRLER ====================
        MOV fastMov;
        MOV slowMov;
        MOV indexFastMov;
        MOV indexSlowMov;
        RSI rsi;
        BollingerBand bollinger;

        // ==================== STATE ====================
        bool inPosition = false;
        decimal entryPrice = 0m;
        decimal highestPriceSinceEntry = 0m;

        // Hacim takibi (son N bar ortalamasi icin)
        List<decimal> volumeHistory = new List<decimal>();

        // ==================== OUTPUT ====================
        [Output] public decimal FastEMA;
        [Output] public decimal SlowEMA;
        [Output] public decimal RSIValue;
        [Output] public decimal BollingerUpper;
        [Output] public decimal BollingerLower;
        [Output] public decimal BollingerWidth;
        [Output] public decimal VolumeRatio;
        [Output] public decimal TrendStrengthValue;
        [Output] public decimal EffectiveStopLevel;
        [Output] public decimal SurprizSkoru;

        public override void OnInit()
        {
            AddSymbol(Symbol, SymbolPeriod);
            AddSymbol(IndexSymbol, SymbolPeriod);

            fastMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            slowMov = MOVIndicator(Symbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);

            indexFastMov = MOVIndicator(IndexSymbol, SymbolPeriod, OHLCType.Close, FastPeriod, MovMethod.Exponential);
            indexSlowMov = MOVIndicator(IndexSymbol, SymbolPeriod, OHLCType.Close, SlowPeriod, MovMethod.Exponential);

            rsi = RSIIndicator(Symbol, SymbolPeriod, OHLCType.Close, RsiPeriod);
            bollinger = BollingerBandIndicator(Symbol, SymbolPeriod, OHLCType.Close, BollingerPeriod, BollingerStdDev);

            SendOrderSequential(true);
            WorkWithPermanentSignal(true);
        }

        public override void OnInitCompleted()
        {
            Debug("BIST_SURPRIZ_V1 hazir. Surpriz + Trend sistemi aktif.");
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (barData == null || barData.BarData == null)
                return;

            DateTime barTime = barData.BarData.Dtime;
            if (!IsTradingTime(barTime))
                return;

            decimal closePrice = barData.BarData.Close;
            decimal volume = barData.BarData.Volume;

            // ==================== HACIM TAKIBI ====================
            volumeHistory.Add(volume);
            if (volumeHistory.Count > VolumeMaPeriod + 5)
                volumeHistory.RemoveAt(0);

            // ==================== TREND HESAPLAMA ====================
            bool trendUp = fastMov.CurrentValue > slowMov.CurrentValue;
            bool trendDown = fastMov.CurrentValue < slowMov.CurrentValue;

            decimal trendStrength = 0m;
            if (slowMov.CurrentValue != 0)
                trendStrength = Math.Abs(fastMov.CurrentValue - slowMov.CurrentValue) / slowMov.CurrentValue * 100m;
            bool trendStrong = trendStrength >= TrendStrengthPercent;

            // ==================== RSI ====================
            bool momentumOk = rsi.CurrentValue > RsiThreshold;
            bool rsiAsirim = rsi.CurrentValue < 30 || rsi.CurrentValue > 70;

            // ==================== XU100 FILTRE ====================
            bool indexOk = true;
            if (UseIndexFilter)
                indexOk = indexFastMov.CurrentValue > indexSlowMov.CurrentValue;

            // ==================== BOLLINGER ====================
            decimal bolUpper = bollinger.BollingerUp.CurrentValue;
            decimal bolLower = bollinger.BollingerDown.CurrentValue;
            decimal bolMiddle = bollinger.BollingerMiddle.CurrentValue;
            decimal bolWidth = 0m;
            if (bolMiddle != 0)
                bolWidth = (bolUpper - bolLower) / bolMiddle * 100m;

            // Bollinger sikisma: band genisligi dusukse = patlama beklentisi
            bool bollingerSqueeze = false;
            if (UseBollingerSqueeze && bolWidth > 0 && bolWidth < 3.0m)
                bollingerSqueeze = true;

            // Fiyat bant disinda mi?
            bool fiyatBandDisinda = closePrice > bolUpper || closePrice < bolLower;

            // ==================== HACIM ANOMALISI ====================
            decimal volumeRatio = 1.0m;
            bool volumeAnomali = false;
            if (UseVolumeFilter && volumeHistory.Count >= VolumeMaPeriod)
            {
                decimal volSum = 0m;
                int startIdx = volumeHistory.Count - VolumeMaPeriod;
                for (int i = startIdx; i < volumeHistory.Count; i++)
                    volSum += volumeHistory[i];
                decimal volAvg = volSum / VolumeMaPeriod;

                if (volAvg > 0)
                {
                    volumeRatio = volume / volAvg;
                    volumeAnomali = volumeRatio >= VolumeMultiplier;
                }
            }

            // ==================== SURPRIZ SKORU (0-100) ====================
            decimal surprizSkor = 50m; // notr

            // RSI asiri bolge (+15)
            if (rsi.CurrentValue < 30)
                surprizSkor += 15m * (30m - rsi.CurrentValue) / 30m;
            else if (rsi.CurrentValue > 70)
                surprizSkor += 15m * (rsi.CurrentValue - 70m) / 30m;

            // Bollinger sikisma (+15)
            if (bollingerSqueeze)
                surprizSkor += 15m;

            // Fiyat band disinda (+10)
            if (fiyatBandDisinda)
                surprizSkor += 10m;

            // Hacim anomalisi (+15)
            if (volumeAnomali)
                surprizSkor += Math.Min(15m, (volumeRatio - 1m) * 5m);

            // Trend gucu (+10)
            if (trendStrength > 0.5m)
                surprizSkor += Math.Min(10m, trendStrength * 5m);

            surprizSkor = Math.Max(0m, Math.Min(100m, surprizSkor));

            // ==================== STOP YONETIMI ====================
            bool stopTriggered = false;
            decimal effectiveStopLevel = 0m;

            if (inPosition && entryPrice > 0)
            {
                if (closePrice > highestPriceSinceEntry)
                    highestPriceSinceEntry = closePrice;

                decimal fixedStop = entryPrice * (1 - StopLossPercent / 100m);
                effectiveStopLevel = fixedStop;

                // Break-even
                decimal beLevel = entryPrice * (1 + BreakEvenActivationPercent / 100m);
                if (highestPriceSinceEntry >= beLevel)
                    effectiveStopLevel = Math.Max(effectiveStopLevel, entryPrice);

                // Trailing
                decimal trailLevel = entryPrice * (1 + TrailingActivationPercent / 100m);
                if (highestPriceSinceEntry >= trailLevel)
                {
                    decimal trailStop = highestPriceSinceEntry * (1 - TrailingStopPercent / 100m);
                    effectiveStopLevel = Math.Max(effectiveStopLevel, trailStop);
                }

                if (closePrice <= effectiveStopLevel)
                    stopTriggered = true;
            }

            // ==================== GIRIS SINYALI ====================
            // Surpriz skoru + trend + momentum + filtreler
            bool surprizOk = surprizSkor >= 60m; // surpriz potansiyeli yuksek

            bool buySignal = trendUp
                             && indexOk
                             && momentumOk
                             && trendStrong
                             && surprizOk
                             && !inPosition;

            bool sellSignal = (trendDown || stopTriggered) && inPosition;

            // ==================== EMIR ====================
            if (buySignal)
            {
                SendMarketOrder(Symbol, BuyOrderQuantity, OrderSide.Buy);
                entryPrice = closePrice;
                highestPriceSinceEntry = closePrice;
                Debug("SURPRIZ ALIS | Skor:" + Math.Round(surprizSkor, 0)
                    + " RSI:" + Math.Round(rsi.CurrentValue, 1)
                    + " BolW:" + Math.Round(bolWidth, 2)
                    + " Vol:" + Math.Round(volumeRatio, 1) + "x");
            }

            if (sellSignal)
            {
                SendMarketOrder(Symbol, SellOrderQuantity, OrderSide.Sell);
                Debug("SATIS | Stop:" + stopTriggered + " Trend:" + trendDown);
            }

            // ==================== OUTPUT ====================
            FastEMA = Math.Round(fastMov.CurrentValue, 2);
            SlowEMA = Math.Round(slowMov.CurrentValue, 2);
            RSIValue = Math.Round(rsi.CurrentValue, 2);
            BollingerUpper = Math.Round(bolUpper, 2);
            BollingerLower = Math.Round(bolLower, 2);
            BollingerWidth = Math.Round(bolWidth, 2);
            VolumeRatio = Math.Round(volumeRatio, 2);
            TrendStrengthValue = Math.Round(trendStrength, 2);
            EffectiveStopLevel = Math.Round(effectiveStopLevel, 2);
            SurprizSkoru = Math.Round(surprizSkor, 0);
        }

        public override void OnOrderUpdate(IOrder order)
        {
            if (order == null || order.Symbol != Symbol)
                return;

            if (order.OrdStatus.Obj == OrdStatus.Filled)
            {
                if (order.Side.Obj == Side.Buy)
                {
                    inPosition = true;
                    Debug("ALIS gerceklesti.");
                }
                if (order.Side.Obj == Side.Sell)
                {
                    inPosition = false;
                    entryPrice = 0m;
                    highestPriceSinceEntry = 0m;
                    EffectiveStopLevel = 0m;
                    Debug("SATIS gerceklesti.");
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
