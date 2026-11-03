"""
Yahoo Finance Safe Read-Only Historical Ingestion Module.
Handles downloading and parsing historical OHLCV data for:
- GC=F (Gold Futures)
- ^NDX (Nasdaq 100 Index)
- BTC-USD (Bitcoin USD)
- EURUSD=X (EUR/USD FX)
- EURGBP=X (EUR/GBP FX)

Adheres to strict validation, fail-closed provenance, and standard library only.
"""

import csv
import logging
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger("yahoo_ingestion")
SUPPORTED_SYMBOLS = {"GC=F", "^NDX", "BTC-USD", "EURUSD=X", "EURGBP=X"}

class YahooIngestion:
    def __init__(self, symbol: str, timeout: int = 10):
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {symbol}. Must be one of {SUPPORTED_SYMBOLS}")
        self.symbol = symbol
        self.timeout = timeout

    def parse_csv_data(self, csv_content: str, source_verified: bool = False) -> List[Dict[str, Any]]:
        """
        Parses CSV content with strict fail-closed whole dataset validation.
        Any missing column, unparseable date, non-chronological timestamp, duplicate timestamp,
        invalid/negative/NaN price, inverted high/low, or negative volume raises ValueError.
        Provenance status distinguishes 'parsed' (local CSV) from 'source_verified' (live API).
        """
        records = []
        lines = csv_content.splitlines()
        if not lines:
            raise ValueError("Empty CSV content")

        reader = csv.DictReader(lines)
        if not reader.fieldnames:
            raise ValueError("Missing CSV fieldnames")

        fields = [f.strip().lower() for f in reader.fieldnames]
        required_fields = {"date", "open", "high", "low", "close"}
        if not required_fields.issubset(set(fields)):
            raise ValueError(f"Missing required CSV columns. Found: {fields}, Required: {required_fields}")

        previous_dt = None
        seen_timestamps = set()

        for row_idx, row in enumerate(reader):
            normalized = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            date_str = normalized.get("date", "")
            if not date_str or date_str.lower() in ("null", "nan", "none"):
                raise ValueError(f"Row {row_idx}: Missing or invalid date value: '{date_str}'")

            dt = None
            try:
                if "." in date_str and len(date_str.split(".")[0]) == 10:
                    dt = datetime.fromtimestamp(float(date_str), tz=timezone.utc)
                else:
                    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
                        try:
                            dt = datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue
            except Exception as e:
                raise ValueError(f"Row {row_idx}: Failed to parse date '{date_str}': {e}")

            if dt is None:
                raise ValueError(f"Row {row_idx}: Unrecognized date format: '{date_str}'")

            if dt in seen_timestamps:
                raise ValueError(f"Row {row_idx}: Duplicate timestamp detected: {dt}")
            seen_timestamps.add(dt)

            if previous_dt and dt <= previous_dt:
                raise ValueError(f"Row {row_idx}: Out-of-order or duplicate chronological timestamp {dt} <= {previous_dt}")
            previous_dt = dt

            try:
                open_p = float(normalized.get("open", 0))
                high_p = float(normalized.get("high", 0))
                low_p = float(normalized.get("low", 0))
                close_p = float(normalized.get("close", 0))
                vol_str = normalized.get("volume", "0")
                volume = 0.0 if vol_str.lower() in ("null", "nan", "") else float(vol_str)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Row {row_idx}: Non-numeric OHLCV values: {e}")

            prices = [open_p, high_p, low_p, close_p]
            if any(not math.isfinite(p) or p <= 0 for p in prices):
                raise ValueError(f"Row {row_idx}: Non-finite or non-positive price values: {prices}")

            if high_p < low_p or open_p > high_p or open_p < low_p or close_p > high_p or close_p < low_p:
                raise ValueError(f"Row {row_idx}: Inverted High/Low or Open/Close outside High/Low range: Open={open_p}, High={high_p}, Low={low_p}, Close={close_p}")

            if not math.isfinite(volume) or volume < 0:
                raise ValueError(f"Row {row_idx}: Invalid volume: {volume}")

            prov_status = "source_verified" if source_verified else "parsed"

            records.append({
                "timestamp": dt,
                "symbol": self.symbol,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
                "provenance": {
                    "source": "Yahoo Finance (Read-Only)",
                    "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": prov_status
                }
            })
        return records

    def fetch_historical_data(self, period1: int = 1577836800, period2: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetches historical data from Yahoo Finance v7 download endpoint.
        Note: Yahoo Finance v7 endpoint requires cookies/crumb (often returns HTTP 401 Unauthorized without session).
        Fails closed (returns empty list and logs error) if unauthorized or unreachable.
        """
        if period2 is None:
            period2 = int(datetime.now(timezone.utc).timestamp())
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote(self.symbol)}?period1={period1}&period2={period2}&interval=1d&events=history&includeAdjustedClose=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Compatible; ToolzResearchAgent/1.0)'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    if response.status == 200:
                        content = response.read().decode('utf-8-sig')
                        return self.parse_csv_data(content, source_verified=True)
            except urllib.error.HTTPError as e:
                logger.error(f"Yahoo Finance HTTP error for {self.symbol}: {e.code} {e.reason}. Note: Yahoo v7 download endpoint often requires auth/crumb session cookies.")
                break
            except Exception as e:
                logger.error(f"Yahoo Finance fetch error for {self.symbol}: {e}")
                continue
        return []
