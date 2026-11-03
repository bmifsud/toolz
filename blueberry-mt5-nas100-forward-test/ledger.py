"""
Paper Trading Ledger and EUR Currency Conversion Module.
Initial capital: EUR 500. Tracks paper balances, open positions, closed trades, and equity.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("blueberry_ledger")

class PaperLedger:
    def __init__(self, initial_capital_eur: float = 500.0, base_currency: str = "EUR"):
        self.initial_capital_eur = initial_capital_eur
        self.base_currency = base_currency
        self.balance_eur = initial_capital_eur
        self.equity_eur = initial_capital_eur
        self.open_positions: List[Dict[str, Any]] = []
        self.closed_trades: List[Dict[str, Any]] = []
        self.exchange_rates: Dict[str, float] = {"USD": 1.08, "EUR": 1.0} # e.g. 1 EUR = 1.08 USD

    def set_exchange_rate(self, quote_currency: str, rate_to_eur: float) -> None:
        """Sets conversion rate to EUR."""
        self.exchange_rates[quote_currency.upper()] = rate_to_eur

    def convert_to_eur(self, amount: float, currency: str) -> float:
        """Converts an amount from a given currency to EUR."""
        curr = currency.upper()
        if curr == "EUR":
            return amount
        rate = self.exchange_rates.get(curr, 1.0)
        # If rate is EUR per unit of curr (e.g. USD/EUR exchange rate), multiply or divide accordingly.
        # Assuming exchange_rates stores how many USD per EUR (e.g. 1.08 USD per 1 EUR),
        # then amount in USD divided by 1.08 gives EUR.
        if curr == "USD":
            usd_per_eur = self.exchange_rates.get("USD", 1.08)
            return amount / usd_per_eur
        return amount / rate

    def open_position(self, symbol: str, direction: str, volume: float, entry_price: float, currency: str = "USD") -> Dict[str, Any]:
        """
        Opens a simulated paper position (no leverage / real orders).
        """
        position = {
            "id": len(self.open_positions) + len(self.closed_trades) + 1,
            "symbol": symbol,
            "direction": direction.upper(), # BUY or SELL
            "volume": volume,
            "entry_price": entry_price,
            "currency": currency,
            "status": "OPEN"
        }
        self.open_positions.append(position)
        logger.info(f"Opened paper position #{position['id']}: {direction} {volume} {symbol} @ {entry_price}")
        return position

    def close_position(self, position_id: int, exit_price: float) -> Optional[Dict[str, Any]]:
        """
        Closes an open paper position and updates ledger balance/equity in EUR.
        """
        target_pos = None
        for pos in self.open_positions:
            if pos["id"] == position_id:
                target_pos = pos
                break

        if not target_pos:
            logger.warning(f"Position #{position_id} not found.")
            return None

        self.open_positions.remove(target_pos)

        entry = target_pos["entry_price"]
        vol = target_pos["volume"]
        direction = target_pos["direction"]

        # Calculate profit/loss in instrument currency (USD for US indices)
        # For CFD index, PnL = (Exit - Entry) * Volume * ContractSize (assuming contract size 1 or multiplier)
        price_diff = (exit_price - entry) if direction == "BUY" else (entry - exit_price)
        pnl_instrument_currency = price_diff * vol * 10.0 # Standard CFD multiplier or contract spec

        pnl_eur = self.convert_to_eur(pnl_instrument_currency, target_pos["currency"])

        self.balance_eur += pnl_eur
        self.equity_eur = self.balance_eur

        closed_trade = {
            **target_pos,
            "exit_price": exit_price,
            "pnl_eur": pnl_eur,
            "status": "CLOSED"
        }
        self.closed_trades.append(closed_trade)
        logger.info(f"Closed paper position #{position_id}: PnL = {pnl_eur:.2f} EUR. New balance: {self.balance_eur:.2f} EUR")
        return closed_trade
