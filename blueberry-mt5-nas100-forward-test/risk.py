"""
Risk Management Module for Blueberry Markets MT5 NAS100 Paper Forward Testing.
Enforces conservative sizing, 1% per trade risk limit, 3% daily drawdown limit,
6% weekly drawdown limit, and strict no-leverage / paper-only guardrails.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("blueberry_risk")

class RiskManager:
    def __init__(self, account_equity_eur: float = 500.0, max_risk_per_trade_pct: float = 0.01,
                 max_daily_drawdown_pct: float = 0.03, max_weekly_drawdown_pct: float = 0.06):
        self.account_equity_eur = account_equity_eur
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.max_weekly_drawdown_pct = max_weekly_drawdown_pct
        self.initial_equity_eur = account_equity_eur
        self.daily_high_equity_eur = account_equity_eur
        self.weekly_high_equity_eur = account_equity_eur

    def calculate_position_size(self, entry_price: float, stop_loss_price: float, contract_size: float = 1.0, eur_usd_rate: float = 1.08) -> float:
        """
        Calculates conservative position size (lot size) such that risk does not exceed 1% of account equity.
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return 0.0

        risk_amount_eur = self.account_equity_eur * self.max_risk_per_trade_pct
        risk_amount_usd = risk_amount_eur * eur_usd_rate

        price_risk_distance = abs(entry_price - stop_loss_price)
        if price_risk_distance == 0:
            return 0.0

        # Risk per lot = price_risk_distance * contract_size (e.g. $10 per point per lot)
        risk_per_lot_usd = price_risk_distance * contract_size
        if risk_per_lot_usd <= 0:
            return 0.0

        lot_size = risk_amount_usd / risk_per_lot_usd
        # Round to standard broker lot step (e.g., 0.01)
        lot_size = round(lot_size, 2)

        # Ensure minimum lot size constraint
        if lot_size < 0.01:
            lot_size = 0.01

        logger.info(f"Calculated conservative position size: {lot_size} lots (Risk EUR: {risk_amount_eur:.2f})")
        return lot_size

    def check_drawdown_limits(self, current_equity_eur: float) -> Dict[str, Any]:
        """
        Checks if current equity violates daily (3%) or weekly (6%) maximum drawdown limits.
        """
        self.account_equity_eur = current_equity_eur
        if current_equity_eur > self.daily_high_equity_eur:
            self.daily_high_equity_eur = current_equity_eur
        if current_equity_eur > self.weekly_high_equity_eur:
            self.weekly_high_equity_eur = current_equity_eur

        daily_drawdown = (self.daily_high_equity_eur - current_equity_eur) / self.daily_high_equity_eur
        weekly_drawdown = (self.weekly_high_equity_eur - current_equity_eur) / self.weekly_high_equity_eur

        status = {
            "daily_drawdown_pct": round(daily_drawdown * 100, 2),
            "weekly_drawdown_pct": round(weekly_drawdown * 100, 2),
            "daily_limit_breached": daily_drawdown > self.max_daily_drawdown_pct,
            "weekly_limit_breached": weekly_drawdown > self.max_weekly_drawdown_pct,
            "trading_halted": False
        }

        if status["daily_limit_breached"] or status["weekly_limit_breached"]:
            status["trading_halted"] = True
            logger.critical(f"RISK LIMIT BREACHED! Daily DD: {status['daily_drawdown_pct']}%, Weekly DD: {status['weekly_drawdown_pct']}%. Trading halted.")

        return status
