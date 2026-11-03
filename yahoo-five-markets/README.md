# Yahoo Finance Five Markets Research & Ingestion Module

## Overview
This module provides safe, read-only historical data ingestion, strict chronological walk-forward evaluation, and realistic cost modeling for five key Yahoo Finance symbols:
1. **GC=F** (Gold Futures proxy, COMEX gold futures, NOT XAU/USD spot)
2. **^NDX** (Cash Nasdaq 100 Index)
3. **BTC-USD** (Bitcoin USD spot/proxy pair)
4. **EURUSD=X** (Euro / US Dollar FX rate)
5. **EURGBP=X** (Euro / British Pound FX rate)

## Key Rules & Limitations
- **Data Source**: Yahoo Finance public endpoints / CSV exports (delayed data, historical EOD/intraday).
- **Execution**: Read-only ingestion and backtesting/walk-forward evaluation ONLY. No live or paper trading execution. No order placement. No Binance/Blueberry dependencies.
- **Quotes**: Yahoo Finance provides historical Close/Open/High/Low/Volume and delayed price feeds. It does **not** provide live executable bid/ask quotes for cash indexes or FX. We explicitly model assumed transaction costs (spread/slippage/commissions) based on asset class rather than claiming executable bid/ask.
- **Fail-Closed Provenance**: Any data anomaly (missing timestamps, negative prices, NaN, out-of-order data, inverted high/low) triggers fail-closed rejection. Provenance metadata (fetch time, source symbol, validation status) is tracked.
- **Dependencies**: Uses Python standard library only (`urllib.request`, `csv`, `json`, `datetime`, `math`, `logging`), avoiding heavy third-party dependencies like `yfinance`.
