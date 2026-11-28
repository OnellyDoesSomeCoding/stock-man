//+------------------------------------------------------------------+
//| StockmanExportIndicators.mq5                                     |
//| Exports MT5's own indicator values (M15 and H4) to a CSV so      |
//| Stockman can check its Python indicators match (Gate 1).         |
//| READ-ONLY: this script places no orders.                         |
//| Output: <MT5 Common folder>\Files\stockman_indicators.csv        |
//+------------------------------------------------------------------+
#property copyright "Stockman"
#property version   "1.00"
#property script_show_inputs

input string InpSymbol = "";   // Symbol (empty = this chart's symbol)
input int    InpBars   = 300;  // Candles per timeframe

//--- one timeframe: create indicators, wait for them, write rows
bool ExportTF(const string sym, const ENUM_TIMEFRAMES tf, const string tfname, const int fh)
  {
   int h[7];
   h[0] = iMA(sym, tf, 20, 0, MODE_EMA, PRICE_CLOSE);
   h[1] = iMA(sym, tf, 50, 0, MODE_EMA, PRICE_CLOSE);
   h[2] = iMA(sym, tf, 200, 0, MODE_EMA, PRICE_CLOSE);
   h[3] = iRSI(sym, tf, 14, PRICE_CLOSE);
   h[4] = iATR(sym, tf, 14);
   h[5] = iADXWilder(sym, tf, 14);
   h[6] = iADX(sym, tf, 14);
   for(int k = 0; k < 7; k++)
      if(h[k] == INVALID_HANDLE)
        {
         Print("Stockman: could not create indicator ", k, " on ", tfname, ", error ", GetLastError());
         return false;
        }
   //--- indicators calculate in the background; wait up to ~20 s
   for(int k = 0; k < 7; k++)
     {
      int tries = 0;
      while(BarsCalculated(h[k]) < InpBars && tries < 200 && !IsStopped())
        {
         Sleep(100);
         tries++;
        }
     }

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int n = CopyRates(sym, tf, 0, InpBars, rates);
   if(n <= 0)
     {
      Print("Stockman: no candles for ", sym, " ", tfname);
      return false;
     }

   double e20[], e50[], e200[], rsi[], atr[], adxw[], pdi[], ndi[], adx[];
   ArraySetAsSeries(e20, true);  ArraySetAsSeries(e50, true); ArraySetAsSeries(e200, true);
   ArraySetAsSeries(rsi, true);  ArraySetAsSeries(atr, true); ArraySetAsSeries(adxw, true);
   ArraySetAsSeries(pdi, true);  ArraySetAsSeries(ndi, true); ArraySetAsSeries(adx, true);
   bool ok = CopyBuffer(h[0], 0, 0, n, e20) == n && CopyBuffer(h[1], 0, 0, n, e50) == n
             && CopyBuffer(h[2], 0, 0, n, e200) == n && CopyBuffer(h[3], 0, 0, n, rsi) == n
             && CopyBuffer(h[4], 0, 0, n, atr) == n && CopyBuffer(h[5], 0, 0, n, adxw) == n
             && CopyBuffer(h[5], 1, 0, n, pdi) == n && CopyBuffer(h[5], 2, 0, n, ndi) == n
             && CopyBuffer(h[6], 0, 0, n, adx) == n;
   if(ok)
      for(int i = n - 1; i >= 0; i--)   // oldest first
         FileWrite(fh, sym, tfname, (long)rates[i].time, TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                   DoubleToString(rates[i].close, 8), DoubleToString(e20[i], 8), DoubleToString(e50[i], 8),
                   DoubleToString(e200[i], 8), DoubleToString(rsi[i], 8), DoubleToString(atr[i], 8),
                   DoubleToString(adxw[i], 8), DoubleToString(pdi[i], 8), DoubleToString(ndi[i], 8),
                   DoubleToString(adx[i], 8));
   else
      Print("Stockman: indicators not ready on ", tfname, ", error ", GetLastError(), ". Run the script again.");

   for(int k = 0; k < 7; k++)
      IndicatorRelease(h[k]);
   return ok;
  }

void OnStart()
  {
   string sym = (InpSymbol == "") ? _Symbol : InpSymbol;
   int fh = FileOpen("stockman_indicators.csv", FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(fh == INVALID_HANDLE)
     {
      Alert("Stockman: could not create the file, error ", GetLastError());
      return;
     }
   FileWrite(fh, "symbol", "tf", "time_server_raw", "time_server", "close", "ema20", "ema50", "ema200",
             "rsi14", "atr14", "adxw14", "pdi14", "ndi14", "adx14_plain");
   bool ok = ExportTF(sym, PERIOD_M15, "M15", fh) && ExportTF(sym, PERIOD_H4, "H4", fh);
   FileClose(fh);
   if(ok)
      Alert("Stockman: exported ", sym, " indicators. Now run scripts\\check_indicators.py");
   else
      Alert("Stockman: export FAILED, see the Experts tab. Try running the script again.");
  }
//+------------------------------------------------------------------+
