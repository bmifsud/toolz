#property strict
#property version "1.00"
#property description "Read-only broker quote exporter; never places orders."
input string InpSymbol = ""; // Set exact Blueberry Market Watch symbol; blank uses chart symbol
input int InpIntervalSeconds = 5;
string name;
int OnInit()
{
   name = (StringLen(InpSymbol)>0 ? InpSymbol : _Symbol);
   if(!SymbolSelect(name,true)) { Print("Symbol unavailable: ",name); return INIT_FAILED; }
   if(InpIntervalSeconds<1) return INIT_PARAMETERS_INCORRECT;
   EventSetTimer(InpIntervalSeconds);
   Print("Read-only export of ",name," to MT5 Common Files");
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason) { EventKillTimer(); }
void OnTimer()
{
   MqlTick tick;
   if(!SymbolInfoTick(name,tick) || tick.time_msc<=0 || tick.bid<=0 || tick.ask<=0 || tick.ask<tick.bid)
   { Print("No valid broker tick: ",name); return; }
   int h=FileOpen("blueberry_nas100_quotes.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
   if(h==INVALID_HANDLE) { Print("CSV open failed: ",GetLastError()); return; }
   FileWrite(h,"symbol","server_time_epoch_ms","bid","ask","last","volume","capture_local_epoch_seconds");
   FileWrite(h,name,(string)tick.time_msc,DoubleToString(tick.bid,(int)SymbolInfoInteger(name,SYMBOL_DIGITS)),
      DoubleToString(tick.ask,(int)SymbolInfoInteger(name,SYMBOL_DIGITS)),DoubleToString(tick.last,(int)SymbolInfoInteger(name,SYMBOL_DIGITS)),
      (string)tick.volume,(string)TimeLocal());
   FileFlush(h); FileClose(h);
   h=FileOpen("blueberry_nas100_specs.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
   if(h==INVALID_HANDLE) return;
   FileWrite(h,"symbol","digits","point","tick_size","tick_value","contract_size","currency_profit","volume_min","volume_step","volume_max","trade_mode","server_time_epoch_seconds");
   FileWrite(h,name,(string)SymbolInfoInteger(name,SYMBOL_DIGITS),
      DoubleToString(SymbolInfoDouble(name,SYMBOL_POINT),8),
      DoubleToString(SymbolInfoDouble(name,SYMBOL_TRADE_TICK_SIZE),8),
      DoubleToString(SymbolInfoDouble(name,SYMBOL_TRADE_TICK_VALUE),8),
      DoubleToString(SymbolInfoDouble(name,SYMBOL_TRADE_CONTRACT_SIZE),4),
      SymbolInfoString(name,SYMBOL_CURRENCY_PROFIT),
      DoubleToString(SymbolInfoDouble(name,SYMBOL_VOLUME_MIN),4),
      DoubleToString(SymbolInfoDouble(name,SYMBOL_VOLUME_STEP),4),
      DoubleToString(SymbolInfoDouble(name,SYMBOL_VOLUME_MAX),4),
      (string)SymbolInfoInteger(name,SYMBOL_TRADE_MODE),(string)TimeTradeServer());
   FileFlush(h); FileClose(h);
}
