"""
Data Ingestion Module for Blueberry Markets MT5 NAS100 CSV exports.
Handles reading tick / bar data with bid, ask, timestamps, and volume.
"""

import csv
import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger("blueberry_data_ingestion")

class DataIngestion:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def load_ticks(self) -> List[Dict[str, Any]]:
        """
        Loads tick or bar data from MT5 CSV export file.
        Expected columns (case-insensitive): timestamp (or date/time), symbol, bid, ask, volume (optional).
        """
        ticks = []
        try:
            with open(self.csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}

                    # Extract timestamp
                    ts_str = normalized_row.get("timestamp", normalized_row.get("time", normalized_row.get("date", "")))
                    try:
                        # Try parsing common timestamp formats
                        if "." in ts_str and len(ts_str.split(".")[0]) == 10:
                            # Unix timestamp or similar
                            dt = datetime.fromtimestamp(float(ts_str))
                        else:
                            dt = None
                            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y.%m.%d %H:%M:%S.%f"):
                                try:
                                    dt = datetime.strptime(ts_str, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                continue
                    except Exception:
                        continue

                    if dt is None:
                        continue
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    symbol = normalized_row.get("symbol", normalized_row.get("ticker", "NAS100")).upper()

                    try:
                        bid = float(normalized_row.get("bid", 0.0))
                        ask = float(normalized_row.get("ask", 0.0))
                    except ValueError:
                        continue

                    if not math.isfinite(bid) or not math.isfinite(ask) or bid <= 0 or ask < bid:
                        continue

                    volume = float(normalized_row.get("volume", normalized_row.get("vol", 1.0)))

                    ticks.append({
                        "timestamp": dt,
                        "symbol": symbol,
                        "bid": bid,
                        "ask": ask,
                        "volume": volume,
                        "spread": round(ask - bid, 4)
                    })
        except Exception as e:
            logger.error(f"Error reading MT5 CSV export from {self.csv_path}: {e}")

        return ticks
