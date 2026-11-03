"""
Yahoo Finance Walk-Forward Evaluation & Realistic Cost Model.
Provides chronological walk-forward evaluation across the 5 markets:
- GC=F (Gold Futures)
- ^NDX (Nasdaq 100 Index)
- BTC-USD (Bitcoin USD)
- EURUSD=X (EUR/USD FX)
- EURGBP=X (EUR/GBP FX)

Assumes realistic transaction costs (spread/slippage/commissions) based on asset class.
No live execution or executable bid/ask claims. Fail-closed provenance.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("yahoo_walkforward")

# Asset-class specific cost models (basis points or fixed commission per trade)
ASSET_COST_MODELS = {
    "GC=F": {"slippage_bps": 2.0, "commission_flat": 1.50},    # Gold Futures
    "^NDX": {"slippage_bps": 1.5, "commission_flat": 1.00},    # Nasdaq 100 Index
    "BTC-USD": {"slippage_bps": 5.0, "commission_flat": 0.0},  # Bitcoin Crypto
    "EURUSD=X": {"slippage_bps": 0.8, "commission_flat": 0.5}, # Major FX
    "EURGBP=X": {"slippage_bps": 1.2, "commission_flat": 0.5}, # Cross FX
}

class YahooWalkForwardEvaluator:
    def __init__(self, symbol: str, initial_capital: float = 10000.0):
        if symbol not in ASSET_COST_MODELS:
            raise ValueError(f"Unknown symbol for cost model: {symbol}")
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.cost_model = ASSET_COST_MODELS[symbol]

    def calculate_trade_cost(self, trade_value: float) -> float:
        slippage = trade_value * (self.cost_model["slippage_bps"] / 10000.0)
        commission = self.cost_model["commission_flat"]
        return slippage + commission

    def evaluate_walk_forward(self, records: List[Dict[str, Any]], strategy_func) -> Dict[str, Any]:
        """
        Runs strict chronological walk-forward evaluation over records.
        strategy_func(history_window) -> 'buy', 'sell', or 'hold'
        """
        if not records:
            return {
                "symbol": self.symbol,
                "status": "fail_closed_no_data",
                "final_equity": self.initial_capital,
                "total_trades": 0
            }

        # Sort records strictly by timestamp
        sorted_records = sorted(records, key=lambda x: x["timestamp"])
        
        capital = self.initial_capital
        position = 0.0 # units held
        entry_price = 0.0
        trades_count = 0
        history_window = []

        for record in sorted_records:
            history_window.append(record)
            # Ensure window is chronological
            if len(history_window) < 5:
                continue

            signal = strategy_func(history_window)
            current_price = record["close"]

            if signal == "buy" and position == 0:
                trade_value = capital * 0.95 # allocate 95% of capital
                cost = self.calculate_trade_cost(trade_value)
                if capital >= (trade_value + cost):
                    position = (trade_value) / current_price
                    capital -= (trade_value + cost)
                    entry_price = current_price
                    trades_count += 1
            elif signal == "sell" and position > 0:
                gross_value = position * current_price
                cost = self.calculate_trade_cost(gross_value)
                capital += (gross_value - cost)
                position = 0.0
                trades_count += 1

        # Mark-to-market final equity
        final_equity = capital + (position * sorted_records[-1]["close"] if position > 0 else 0.0)
        return {
            "symbol": self.symbol,
            "status": "success",
            "initial_capital": self.initial_capital,
            "final_equity": round(final_equity, 2),
            "return_pct": round(((final_equity - self.initial_capital) / self.initial_capital) * 100, 4),
            "total_trades": trades_count,
            "provenance": {
                "evaluator": "YahooWalkForwardEvaluator",
                "cost_model": self.cost_model,
                "fail_closed": True
            }
        }
