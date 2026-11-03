# NAS100 Day Trading & Backtesting Framework

## Overview
The **NAS100 Trading Framework** is a robust, risk-first quantitative backtesting and evaluation engine designed for NAS100 CFD trading (noting that NQ futures $\neq$ NAS100 CFD). It enforces strict chronological validation, fail-closed broker cost safety, expanding chronological walk-forward folds, and conservative stop-first execution.

## Key Features
1. **Blueberry MT5 Broker Spec (`config/blueberry-mt5.json`)**:
   - Initial paper capital: €500.00.
   - Fail-closed validation: Blocks monetary simulation if spread, slippage, minimum lot size, or contract value are unknown/missing (while keeping diagnostic signals fully available).
2. **Backtesting Engine (`backtest.py`)**:
   - Strict CSV schema validation (`datetime`, `symbol`, `open`, `high`, `low`, `close`, `volume`).
   - Chronological ordering enforcement and symbol filtering.
   - Expanding chronological folds with past-only lookback tuning (3 / 5 / 10 bars) to eliminate look-ahead bias.
   - Baseline comparison: Flat baseline vs fixed momentum 5 vs tuned momentum.
   - Stop-first conservative exit ordering and one-bar next-open execution.
3. **TimesFM Forecasting Overlay (`nas100-day-trader-timesfm`)**:
   - Optional local causal forecast overlay (`datetime`, `predicted_close`).
   - Strict adherence to TimesFM 3 noncommercial weights restriction warning without asserting out-of-sample improvement without empirical evaluation.
4. **Comprehensive Unit Tests (`tests/test_nas100.py`)**:
   - Full test coverage for schema validation, chronological ordering, fail-closed spec behavior, fold splitting, baseline comparison, and TimesFM overlay.
5. **Educational Disclaimers**:
   - Prominent risk disclaimers across CLI execution and documentation.
   - No live trades, no network connections, and no real credentials used.

## Getting Started & Usage

### Run Backtest CLI
```bash
python3 backtest.py path/to/data.csv --config config/blueberry-mt5.json --train-bars 100 --test-bars 20
```

### Run with TimesFM Forecast Overlay
```bash
python3 backtest.py path/to/data.csv --config config/blueberry-mt5.json --forecasts path/to/forecasts.csv
```

### Run Unit Tests
```bash
PYTHONPATH=. pytest tests/test_nas100.py
```
