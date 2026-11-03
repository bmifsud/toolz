"""
Unit tests for Yahoo Finance Five Markets ingestion, walk-forward evaluation, and fail-closed validation.
Covers GC=F, ^NDX, BTC-USD, EURUSD=X, EURGBP=X.
"""

import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from yahoo_ingestion import YahooIngestion, SUPPORTED_SYMBOLS
from yahoo_walkforward import YahooWalkForwardEvaluator

def test_supported_symbols():
    assert SUPPORTED_SYMBOLS == {"GC=F", "^NDX", "BTC-USD", "EURUSD=X", "EURGBP=X"}

def test_ingestion_valid_csv():
    csv_data = (
        "Date,Open,High,Low,Close,Adj Close,Volume\n"
        "2026-11-01,2000.0,2010.0,1995.0,2005.0,2005.0,15000\n"
        "2026-11-02,2005.0,2020.0,2000.0,2015.0,2015.0,18000\n"
    )
    for sym in SUPPORTED_SYMBOLS:
        ingestor = YahooIngestion(sym)
        # Default parse (local CSV) should have provenance status 'parsed'
        records = ingestor.parse_csv_data(csv_data, source_verified=False)
        assert len(records) == 2
        assert records[0]["symbol"] == sym
        assert records[0]["close"] == 2005.0
        assert records[0]["provenance"]["status"] == "parsed"

        # Source verified parse should have provenance status 'source_verified'
        records_verified = ingestor.parse_csv_data(csv_data, source_verified=True)
        assert records_verified[0]["provenance"]["status"] == "source_verified"

def test_ingestion_fail_closed_validation():
    ingestor = YahooIngestion("GC=F")

    # 1. Invalid date format
    bad_date_csv = (
        "Date,Open,High,Low,Close,Volume\n"
        "invalid_date,2000.0,2010.0,1995.0,2005.0,1000\n"
    )
    with pytest.raises(ValueError, match="Unrecognized date format|Failed to parse date|Missing or invalid date"):
        ingestor.parse_csv_data(bad_date_csv)

    # 2. Negative price
    bad_price_csv = (
        "Date,Open,High,Low,Close,Volume\n"
        "2026-11-01,-100.0,2010.0,1995.0,2005.0,1000\n"
    )
    with pytest.raises(ValueError, match="Non-finite or non-positive price values"):
        ingestor.parse_csv_data(bad_price_csv)

    # 3. Inverted High < Low
    bad_hl_csv = (
        "Date,Open,High,Low,Close,Volume\n"
        "2026-11-01,2000.0,1990.0,1995.0,2005.0,1000\n"
    )
    with pytest.raises(ValueError, match="Inverted High/Low"):
        ingestor.parse_csv_data(bad_hl_csv)

    # 4. Out-of-order timestamps
    out_of_order_csv = (
        "Date,Open,High,Low,Close,Volume\n"
        "2026-11-02,2000.0,2010.0,1995.0,2005.0,1000\n"
        "2026-11-01,2000.0,2010.0,1995.0,2005.0,1000\n"
    )
    with pytest.raises(ValueError, match="Out-of-order or duplicate chronological timestamp"):
        ingestor.parse_csv_data(out_of_order_csv)

    # 5. Duplicate timestamps
    duplicate_csv = (
        "Date,Open,High,Low,Close,Volume\n"
        "2026-11-01,2000.0,2010.0,1995.0,2005.0,1000\n"
        "2026-11-01,2005.0,2015.0,2000.0,2010.0,1000\n"
    )
    with pytest.raises(ValueError, match="Duplicate timestamp detected"):
        ingestor.parse_csv_data(duplicate_csv)

    # 6. Missing required columns
    missing_cols_csv = (
        "Date,Open,High,Close,Volume\n"
        "2026-11-01,2000.0,2010.0,2005.0,1000\n"
    )
    with pytest.raises(ValueError, match="Missing required CSV columns"):
        ingestor.parse_csv_data(missing_cols_csv)

def test_walk_forward_evaluator():
    records = [
        {
            "timestamp": datetime(2026, 11, i, tzinfo=timezone.utc),
            "symbol": "^NDX",
            "open": 18000.0 + i * 10,
            "high": 18020.0 + i * 10,
            "low": 17980.0 + i * 10,
            "close": 18010.0 + i * 10,
            "volume": 100000.0
        } for i in range(1, 15)
    ]
    
    # Simple strategy: buy on index 5, sell on index 10
    def dummy_strategy(history):
        if len(history) == 6:
            return "buy"
        if len(history) == 11:
            return "sell"
        return "hold"

    evaluator = YahooWalkForwardEvaluator("^NDX", initial_capital=10000.0)
    result = evaluator.evaluate_walk_forward(records, dummy_strategy)
    assert result["symbol"] == "^NDX"
    assert result["status"] == "success"
    assert result["total_trades"] == 2
    assert "final_equity" in result
    assert result["provenance"]["fail_closed"] is True

