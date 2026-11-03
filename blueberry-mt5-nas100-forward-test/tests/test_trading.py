"""
Comprehensive unit tests for Blueberry Markets MT5 NAS100 paper forward-testing modules.
"""

import os
import tempfile
from datetime import datetime, timezone, time
import pytest

from symbol_discovery import SymbolDiscovery
from data_ingestion import DataIngestion
from validation import MarketValidator
from ledger import PaperLedger
from risk import RiskManager

def test_symbol_discovery():
    sd = SymbolDiscovery()
    raw_symbols = [
        {"symbol": "EURUSD", "Description": "Euro vs US Dollar", "Currency": "USD", "ContractSize": 100000, "Digits": 5},
        {"symbol": "NAS100.cash", "Description": "US Tech 100 Cash", "Currency": "USD", "ContractSize": 1.0, "Digits": 2},
        {"symbol": "US100", "Description": "US 100 Index", "Currency": "USD", "ContractSize": 1.0, "Digits": 2},
    ]
    matched = sd.discover_symbols(raw_symbols=raw_symbols)
    assert len(matched) == 2
    symbols = [m["symbol"] for m in matched]
    assert "NAS100.CASH" in symbols
    assert "US100" in symbols

    assert sd.validate_contract_metadata(matched[0]) is True
    invalid_contract = {"symbol": "NAS100", "currency": "USD", "contract_size": 0, "digits": 2}
    assert sd.validate_contract_metadata(invalid_contract) is False

def test_data_ingestion():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tf:
        tf.write("timestamp,symbol,bid,ask,volume\n")
        tf.write("2026-11-03 10:00:00,NAS100,20000.50,20001.00,1.5\n")
        tf.write("2026-11-03 10:01:00,NAS100,20002.00,20002.50,2.0\n")
        csv_path = tf.name

    try:
        ingestion = DataIngestion(csv_path)
        ticks = ingestion.load_ticks()
        assert len(ticks) == 2
        assert ticks[0]["symbol"] == "NAS100"
        assert ticks[0]["bid"] == 20000.50
        assert ticks[0]["ask"] == 20001.00
        assert ticks[0]["spread"] == 0.50
    finally:
        os.unlink(csv_path)

def test_market_validator():
    validator = MarketValidator(max_data_age_seconds=60)
    now = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc) # Monday 12:00 UTC (Market open)
    recent_ts = datetime(2026, 11, 3, 11, 59, 30, tzinfo=timezone.utc)
    old_ts = datetime(2026, 11, 3, 11, 50, 0, tzinfo=timezone.utc)

    assert validator.is_fresh(recent_ts, current_time=now) is True
    assert validator.is_fresh(old_ts, current_time=now) is False

    # Test market hours (Monday 12:00 UTC is open)
    assert validator.is_market_open(now) is True
    # Saturday 12:00 UTC is closed
    sat_dt = datetime(2026, 11, 7, 12, 0, 0, tzinfo=timezone.utc)
    assert validator.is_market_open(sat_dt) is False

def test_paper_ledger():
    ledger = PaperLedger(initial_capital_eur=500.0)
    assert ledger.balance_eur == 500.0

    pos = ledger.open_position("NAS100", "BUY", 0.1, 20000.0, "USD")
    assert len(ledger.open_positions) == 1

    closed = ledger.close_position(pos["id"], 20100.0)
    assert closed["status"] == "CLOSED"
    assert ledger.balance_eur > 500.0 # Profit made

def test_risk_manager():
    risk = RiskManager(account_equity_eur=500.0, max_risk_per_trade_pct=0.01)
    # Entry 20000, SL 19900 (risk 100 points). Contract size 1.0. EUR/USD 1.08.
    # Risk amount = 500 * 0.01 = 5 EUR = 5.40 USD.
    # Risk per lot = 100 * 1.0 = $100. Lot size = 5.40 / 100 = 0.054 -> rounds to 0.05 or min 0.01.
    lot_size = risk.calculate_position_size(20000.0, 19900.0, contract_size=1.0, eur_usd_rate=1.08)
    assert lot_size > 0.0

    # Test drawdown limits
    dd_status = risk.check_drawdown_limits(480.0) # 20 EUR loss (~4%)
    assert dd_status["daily_limit_breached"] is True
    assert dd_status["trading_halted"] is True
