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
using Matriks.Enumeration;
using Newtonsoft.Json;

namespace Matriks.Lean.Algotrader
{
	// ================================================================
	// BOMBA V3 FINAL — Tam Otonom Robot
	// ================================================================
	// - BIST50 hepsini yükler, sadece bomba listesindekilerle işlem yapar
	// - aktif_bombalar.txt her 30dk otomatik okunur (restart gerekmez!)
	// - v3_bridge.json'dan makro risk + bütçe okunur
	// - Zaman filtresi, trailing stop, kapanış çıkışı
	// ================================================================

	public class BOMBA_V3_FINAL : MatriksAlgo
	{
		// Tüm olası semboller (OnInit'te hepsi yüklenir)
		[Parameter("GARAN,THYAO,ASELS,TUPRS,EREGL,SISE,TOASO,AKBNK,YKBNK,HALKB,SAHOL,KCHOL,TCELL,BIMAS,PGSUS,TAVHL,FROTO,ARCLK,PETKM,ENKAI,TKFEN,EKGYO,TTKOM,VAKBN,KOZAL,MGROS,DOHOL,GUBRF,ISCTR,AKSEN,AYEN,KONTR,SASA,GESAN,OTKAR,ENJSA,TSKB,SMRTG,CCOLA,CIMSA,KORDS,VESTL,ALARK,HEKTS,ULKER,ASTOR,TTRAK,EGEEN,CEMTS")]
		public string AllSymbols;

		[Parameter(15000)]
		public decimal BasePosValue;

		[Parameter(SymbolPeriod.Min30)]
		public SymbolPeriod Period;

		[Parameter(1.2)] public double ProfitTrigger;
		[Parameter(3.5)] public double HardStop;
		[Parameter(1.8)] public double TrailingStop;
		[Parameter(0.04)] public double KomisyonOrani; // % olarak (alış+satış toplam = x2)

		// Dosya yolları
		string bombaPath = @"C:\Robot\aktif_bombalar.txt";
		string bridgePath = @"C:\Robot\v3_bridge.json";

		// İndikatörler (tüm semboller için)
		Dictionary<string, MOV> fastMovs = new Dictionary<string, MOV>();
		Dictionary<string, MOV> slowMovs = new Dictionary<string, MOV>();
		Dictionary<string, RSI> rsis = new Dictionary<string, RSI>();
		Dictionary<string, MOST> mosts = new Dictionary<string, MOST>();

		// Pozisyon takibi
		Dictionary<string, bool> inPosition = new Dictionary<string, bool>();
		Dictionary<string, decimal> entryPrices = new Dictionary<string, decimal>();
		Dictionary<string, decimal> highestPrices = new Dictionary<string, decimal>();
		Dictionary<string, decimal> posQuantities = new Dictionary<string, decimal>();
		Dictionary<int, string> symbolCache = new Dictionary<int, string>();
		Dictionary<string, int> lastOrderBarIndex = new Dictionary<string, int>();

		// Bomba listesi (dinamik — periyodik güncellenir)
		HashSet<string> aktivBombalar = new HashSet<string>();
		int bombaOkumaSayaci = 0;
		int bombaOkumaAraligi = 6; // Her 6 barda bir oku (30dk bar = her 3 saatte)

		public override void OnInit()
		{
			// 1. TÜM SEMBOLLERİ YÜKLE
			string[] symbols = AllSymbols.Split(',');
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
				lastOrderBarIndex[s] = -1;
			}

			// 2. İLK BOMBA LİSTESİNİ OKU
			BombaListesiGuncelle();

			SendOrderSequential(true);
			WorkWithPermanentSignal(false);

			Debug($"BOMBA_V3_FINAL HAZIR — {symbols.Length} sembol yuklu, {aktivBombalar.Count} bomba aktif");
		}

		// ================================================================
		// BOMBA LİSTESİ OKUMA (PERİYODİK)
		// ================================================================
		private void BombaListesiGuncelle()
		{
			try
			{
				if (!File.Exists(bombaPath)) return;

				string icerik = File.ReadAllText(bombaPath).Trim().ToUpper();
				if (string.IsNullOrEmpty(icerik)) return;

				var yeniListe = new HashSet<string>();
				foreach (var item in icerik.Split(','))
				{
					string s = item.Trim();
					if (!string.IsNullOrEmpty(s) && symbolCache.ContainsValue(s))
						yeniListe.Add(s);
				}

				// Değişiklik varsa logla
				if (!yeniListe.SetEquals(aktivBombalar))
				{
					var eklenen = yeniListe.Except(aktivBombalar).ToList();
					var cikan = aktivBombalar.Except(yeniListe).ToList();

					if (eklenen.Count > 0) Debug($"BOMBA EKLENEN: {string.Join(",", eklenen)}");
					if (cikan.Count > 0) Debug($"BOMBA CIKAN: {string.Join(",", cikan)}");

					aktivBombalar = yeniListe;
					Debug($"AKTİF BOMBALAR: {string.Join(",", aktivBombalar)} ({aktivBombalar.Count} adet)");
				}
			}
			catch (Exception ex)
			{
				Debug($"Bomba okuma hatasi: {ex.Message}");
			}
		}

		// ================================================================
		// ANA DÖNGÜ
		// ================================================================
		public override void OnDataUpdate(BarDataEventArgs barData)
		{
			if (barData == null || barData.BarData == null) return;
			if (!symbolCache.TryGetValue(barData.SymbolId, out string s)) return;

			// PERİYODİK BOMBA OKUMA
			bombaOkumaSayaci++;
			if (bombaOkumaSayaci % bombaOkumaAraligi == 0)
			{
				BombaListesiGuncelle();
			}

			// Bridge okuma (makro risk + bütçe)
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

			decimal close = barData.BarData.Close;
			int currentHour = Hour(barData.BarData);
			int currentMinute = Minute(barData.BarData);
			int currentBarIndex = barData.BarDataIndex;

			// Zaman filtresi
			if (currentHour == 12 || (currentHour == 13 && currentMinute < 45)) return;

			// Teknik sinyaller
			if (!fastMovs.ContainsKey(s)) return;
			bool emaOk = fastMovs[s].CurrentValue > slowMovs[s].CurrentValue;
			bool rsiOk = rsis[s].CurrentValue > 50;
			bool trendOk = close > mosts[s].CurrentValue;

			// === POZİSYON YÖNETİMİ ===
			if (inPosition[s])
			{
				if (close > highestPrices[s]) highestPrices[s] = close;
				decimal pnl = (close - entryPrices[s]) / entryPrices[s] * 100m;

				// Komisyon maliyeti (alış + satış)
				decimal komisyonMaliyet = (decimal)KomisyonOrani * 2m;
				decimal netPnl = pnl - komisyonMaliyet;

				// Kapanış öncesi kâr realize (komisyon düşüldükten sonra)
				bool exitBeforeClose = (currentHour == 17 && currentMinute >= 50 && netPnl > 0.2m);

				// Stop hesaplama
				decimal stopPrice = entryPrices[s] * (1 - (decimal)HardStop / 100m);
				if (pnl >= (decimal)ProfitTrigger)
				{
					stopPrice = Math.Max(stopPrice, highestPrices[s] * (1 - (decimal)TrailingStop / 100m));
				}

				// Sembol bomba listesinden çıktıysa ve NET kârdaysa sat
				bool bombadenCikti = !aktivBombalar.Contains(s) && netPnl > 0;

				if (close <= stopPrice || !emaOk || exitBeforeClose || bombadenCikti)
				{
					SendMarketOrder(s, posQuantities[s], OrderSide.Sell);
					string sebep = exitBeforeClose ? "GunSonu" : bombadenCikti ? "BombadenCikti" : "Stop/Trend";
					Debug($"{s} SATILDI | BrutPnL: %{pnl:F2} | NetPnL: %{netPnl:F2} | Komisyon: %{komisyonMaliyet:F2} | Sebep: {sebep}");
					ResetSymbol(s);
				}
			}
			// === YENİ GİRİŞ ===
			else
			{
				// SADECE BOMBA LİSTESİNDEKİLERLE İŞLEM YAP
				if (!aktivBombalar.Contains(s)) return;

				if (currentHour == 17 && currentMinute >= 30) return;
				if (currentBarIndex == lastOrderBarIndex[s]) return;

				if (emaOk && rsiOk && trendOk)
				{
					// Dinamik pozisyon boyutu
					decimal timeMultiplier = 1.0m;
					if (currentHour == 10 && currentMinute <= 30) timeMultiplier = 1.3m;
					if (currentHour == 17 && currentMinute >= 30) timeMultiplier = 0.6m;

					decimal finalValue = BasePosValue * macroMultiplier * timeMultiplier;
					decimal qty = Math.Floor(finalValue / close);
					if (qty < 1) return;

					SendMarketOrder(s, qty, OrderSide.Buy);
					inPosition[s] = true;
					posQuantities[s] = qty;
					entryPrices[s] = close;
					highestPrices[s] = close;
					lastOrderBarIndex[s] = currentBarIndex;

					Debug($"{s} ALINDI | Carpan: {macroMultiplier * timeMultiplier:F2} | Adet: {qty} | Fiyat: {close:F2} | MinNetKar: %{(decimal)ProfitTrigger - (decimal)KomisyonOrani * 2m:F2}");
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

		public override void OnStopped()
		{
			Debug("BOMBA_V3_FINAL DURDURULDU — Acik pozisyonlari kontrol edin!");
		}
	}
}
