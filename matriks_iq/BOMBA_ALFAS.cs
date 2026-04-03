// ═══════════════════════════════════════════════════
// BIST ALPHA V2 — AKILLI ROBOT ŞABLONU
// Her sabah Python dosyayı günceller.
// Robot listede varsa işlem yapar, yoksa bekler.
// ═══════════════════════════════════════════════════
//
// KULLANIM: ALFAS kelimesini hisse koduyla değiştir
// Örnek: ALFAS → GARAN
//
using System;
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
using Matriks.Data.Tick;
using Matriks.Enumeration;
using Newtonsoft.Json;

namespace Matriks.Lean.Algotrader
{
    public class BOMBA_ALFAS : MatriksAlgo
    {
        [SymbolParameter("ALFAS")]
        public string Symbol;

        [Parameter(SymbolPeriod.Min60)]
        public SymbolPeriod SymbolPeriod;

        [Parameter(5000)]
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

        // Bomba listesi dosya yolu
        private string bombaListePath = @"C:\Users\onurbodur\Desktop\IQ_Deploy\aktif_bombalar.txt";

        MOV fastMov, slowMov;
        RSI rsi;
        bool inPosition = false;
        decimal entryPrice = 0m;
        decimal highestPrice = 0m;
        decimal posQty = 0m;
        int barCount = 0;

        [Output] public decimal RSIValue;
        [Output] public decimal PnL;
        [Output] public decimal BombaAktif;

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
            Debug("BOMBA_ALFAS hazir - akilli mod");
        }

        private bool BombaListesindeVarMi()
        {
            try
            {
                if (!File.Exists(bombaListePath))
                    return false;

                string icerik = File.ReadAllText(bombaListePath).Trim().ToUpper();
                string benimTicker = Symbol.ToUpper();

                string[] liste = icerik.Split(',');
                foreach (string item in liste)
                {
                    if (item.Trim() == benimTicker)
                        return true;
                }
                return false;
            }
            catch
            {
                return false;
            }
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (barData == null || barData.BarData == null) return;
            decimal close = barData.BarData.Close;
            if (close <= 0) return;

            barCount++;

            // Her 6 barda (6 saat) bomba listesini kontrol et
            bool bombaAktif = false;
            if (barCount % 6 == 1 || barCount == 1)
            {
                bombaAktif = BombaListesindeVarMi();
            }
            BombaAktif = bombaAktif ? 1m : 0m;

            bool emaOk = fastMov.CurrentValue > slowMov.CurrentValue;
            bool rsiOk = rsi.CurrentValue > RsiThreshold;
            RSIValue = Math.Round(rsi.CurrentValue, 2);

            // === POZİSYONDAYSAK: her zaman stop kontrolü yap ===
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
            // === POZİSYON YOKSA: sadece bomba listesindeyse al ===
            else
            {
                if (bombaAktif && emaOk && rsiOk)
                {
                    decimal qty = Math.Floor(MaxPositionValue / close);
                    if (qty < 1) qty = 1;
                    posQty = qty;
                    SendMarketOrder(Symbol, qty, OrderSide.Buy);
                    entryPrice = close;
                    highestPrice = close;
                    Debug("ALIS: " + qty + " lot x " + Math.Round(close, 2) + " TL [BOMBA AKTIF]");
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
