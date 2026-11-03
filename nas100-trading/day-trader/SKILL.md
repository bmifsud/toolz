---
name: nas100-day-trader
description: Risk-first NAS100 day trading evaluation and backtesting framework using expanding chronological folds and conservative stop-first exit logic.
---

# NAS100 Day Trader Skill Specification

## Overview
This skill implements a risk-first, documentation-only workflow for day trading NAS100 CFDs (Note: NQ futures $\neq$ NAS100 CFD). It mandates chronological causal provenance, offline evaluation, and strict risk management without executing live trades or making network model calls.

## Shared CLI Backtest Spec
The standard library CLI interface is specified as:
```bash
python3 nas100-trading/backtest.py DATA.csv --config nas100-trading/config/blueberry-mt5.json --train-bars 100 --test-bars 20 [--forecasts FILE.csv]
```
- **DATA.csv**: Historical price data CSV with columns including datetime and close.
- **Config**: JSON config file path (default template: `nas100-trading/config/blueberry-mt5.json`). If config defaults are unknown or missing, monetary simulation is blocked (fixed €500 initial equity required), but diagnostic signals and backtest metrics are still reported.
- **Train/Test Bars**: Expanding chronological folds with configurable lookback tuning (3 / 5 / 10 bars) evaluated on past data only.
- **Forecasts CSV**: Optional locally generated artifact (`datetime,predicted_close`) providing causal directional overlay.

## Strategy Rules
1. **Execution**: One-bar next-open execution. Close exits and stops/targets use conservative stop-first ordering.
2. **Lookback Tuning**: Expanding chronological folds tune lookback parameters (3, 5, 10 bars) strictly on past data to prevent look-ahead bias.
3. **Benchmarks**: Compare flat baseline against fixed momentum (5-bar lookback).
4. **Risk First**: €500 fixed initial equity. Unknown config defaults block monetary simulation, but trading signals and diagnostics remain fully reported.
