#!/usr/bin/env python3
"""
NAS100 Day Trading Backtesting Engine
--------------------------------------------------
Shared bias-controlled chronological walk-forward backtesting engine.
"""

import sys
import os
import csv
import json
import argparse
from datetime import datetime

DISCLAIMER_HEADER = "=" * 78
EDUCATIONAL_DISCLAIMER = (
    f"{DISCLAIMER_HEADER}\n"
    "EDUCATIONAL & RISK DISCLAIMER:\n"
    "This software is an educational simulation framework for quantitative trading research.\n"
    "Trading CFDs, futures, and leveraged financial instruments involves substantial risk of loss.\n"
    "Operates offline with simulated EUR 500 paper capital. Fail-closed on unknown broker specs.\n"
    "No live trades, real credentials, or network model calls are made.\n"
    f"{DISCLAIMER_HEADER}"
)

def print_disclaimer():
    print(EDUCATIONAL_DISCLAIMER)

def parse_datetime(dt_str):
    dt_str = dt_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(dt_str)
    except Exception as e:
        raise ValueError(f"Invalid datetime format: '{dt_str}'") from e

def load_csv_data(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")
    rows = []
    required_cols = {"datetime", "symbol", "open", "high", "low", "close", "volume"}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV file {filepath} is empty or missing headers.")
        headers = [h.strip().lower() for h in reader.fieldnames]
        missing = required_cols - set(headers)
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}. Found: {headers}")
        for r_idx, row in enumerate(reader, start=2):
            norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            try:
                dt = parse_datetime(norm_row["datetime"])
                sym = norm_row["symbol"]
                op = float(norm_row["open"])
                hi = float(norm_row["high"])
                lo = float(norm_row["low"])
                cl = float(norm_row["close"])
                vol = float(norm_row["volume"])
            except Exception as e:
                raise ValueError(f"Error parsing row {r_idx} in {filepath}: {e}") from e
            rows.append({"datetime": dt, "symbol": sym, "open": op, "high": hi, "low": lo, "close": cl, "volume": vol})
    if not rows:
        raise ValueError(f"CSV file {filepath} contains no data rows.")
    for i in range(1, len(rows)):
        if rows[i]["datetime"] < rows[i-1]["datetime"]:
            raise ValueError(f"Chronological violation at row {i+1}: datetime {rows[i]['datetime']} is earlier than previous datetime {rows[i-1]['datetime']}.")
    return rows


def load_forecasts(filepath):
    if not filepath:
        return {}
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Forecasts file not found: {filepath}")
    forecasts = {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Forecasts CSV {filepath} is empty.")
        headers = [h.strip().lower() for h in reader.fieldnames]
        if "datetime" not in headers or "predicted_close" not in headers:
            raise ValueError(f"Forecasts CSV must contain 'datetime' and 'predicted_close'. Found: {headers}")
        for row in reader:
            norm = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            dt = parse_datetime(norm["datetime"])
            pred = float(norm["predicted_close"])
            forecasts[dt] = pred
    return forecasts

def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def check_broker_specs(config):
    fail_closed = config.get("fail_closed_unknown_costs", True)
    spread = config.get("spread")
    slippage = config.get("slippage")
    min_lot = config.get("min_lot")
    contract_value = config.get("contract_value")
    unknown_fields = []
    if spread is None: unknown_fields.append("spread")
    if slippage is None: unknown_fields.append("slippage")
    if min_lot is None: unknown_fields.append("min_lot")
    if contract_value is None: unknown_fields.append("contract_value")
    if unknown_fields and fail_closed:
        raise ValueError(
            f"FAIL-CLOSED: Unknown broker specifications detected: {unknown_fields}. "
            "Broker spec requires explicit spread, slippage, min_lot, and contract_value "
            "to simulate monetary trades (NAS100 CFD vs NQ futures specification)."
        )
    return unknown_fields

def compute_momentum_signal(prices, lookback):
    if len(prices) <= lookback:
        return 0
    if prices[-1] > prices[-1 - lookback]:
        return 1
    elif prices[-1] < prices[-1 - lookback]:
        return -1
    return 0


def run_strategy_simulation(data, strategy_type, lookback=5, forecasts=None, stop_loss_pct=0.01, take_profit_pct=0.02):
    if not data:
        return {"trades": 0, "wins": 0, "win_rate": 0.0, "final_equity": 1.0, "return_pct": 0.0, "equity_curve": [1.0]}
    equity = 1.0
    equity_curve = [equity]
    trades = 0
    wins = 0
    closes = [bar["close"] for bar in data]
    position = 0
    entry_price = 0.0
    
    for i in range(len(data)):
        bar = data[i]
        dt = bar["datetime"]
        op = bar["open"]
        hi = bar["high"]
        lo = bar["low"]
        cl = bar["close"]
        
        if position != 0:
            sl_price = entry_price * (1.0 - stop_loss_pct) if position == 1 else entry_price * (1.0 + stop_loss_pct)
            tp_price = entry_price * (1.0 + take_profit_pct) if position == 1 else entry_price * (1.0 - take_profit_pct)
            exited = False
            exit_price = cl
            if position == 1:
                hit_sl = lo <= sl_price
                hit_tp = hi >= tp_price
                if hit_sl or hit_tp:
                    exit_price = sl_price if hit_sl else tp_price
                    exited = True
            elif position == -1:
                hit_sl = hi >= sl_price
                hit_tp = lo <= tp_price
                if hit_sl or hit_tp:
                    exit_price = sl_price if hit_sl else tp_price
                    exited = True
            if exited:
                ret = (exit_price - entry_price) / entry_price if position == 1 else (entry_price - exit_price) / entry_price
                equity *= (1.0 + ret)
                if ret > 0: wins += 1
                trades += 1
                position = 0
                equity_curve.append(equity)
                continue
                
        current_closes = closes[:i+1]
        signal = 0
        if strategy_type == "flat":
            signal = 0
        elif strategy_type == "momentum":
            signal = compute_momentum_signal(current_closes, lookback)
        elif strategy_type == "timesfm_overlay":
            base_sig = compute_momentum_signal(current_closes, lookback)
            if forecasts and dt in forecasts:
                pred = forecasts[dt]
                pred_dir = 1 if pred > cl else (-1 if pred < cl else 0)
                signal = pred_dir if pred_dir != 0 else base_sig
            else:
                signal = base_sig
                
        if position == 0 and signal != 0:
            position = signal
            entry_price = op
        elif position != 0 and signal == 0:
            ret = (cl - entry_price) / entry_price if position == 1 else (entry_price - cl) / entry_price
            equity *= (1.0 + ret)
            if ret > 0: wins += 1
            trades += 1
            position = 0
        elif position != 0 and signal != 0 and signal != position:
            ret = (op - entry_price) / entry_price if position == 1 else (entry_price - op) / entry_price
            equity *= (1.0 + ret)
            if ret > 0: wins += 1
            trades += 1
            position = signal
            entry_price = op
        equity_curve.append(equity)
        
    if position != 0:
        final_cl = closes[-1]
        ret = (final_cl - entry_price) / entry_price if position == 1 else (entry_price - final_cl) / entry_price
        equity *= (1.0 + ret)
        if ret > 0: wins += 1
        trades += 1
        position = 0
        equity_curve.append(equity)
        
    return {
        "trades": trades, "wins": wins, "win_rate": (wins / trades) if trades > 0 else 0.0,
        "final_equity": equity, "return_pct": (equity - 1.0) * 100.0, "equity_curve": equity_curve
    }

def run_backtest(data, config, forecasts=None):
    check_broker_specs(config)
    bt_cfg = config.get("backtest", {})
    train_bars = bt_cfg.get("train_bars", 100)
    test_bars = bt_cfg.get("test_bars", 20)
    lookback_options = bt_cfg.get("lookback_options", [3, 5, 10])
    rm_cfg = config.get("risk_management", {})
    stop_loss_pct = rm_cfg.get("stop_loss_pct", 0.01)
    take_profit_pct = rm_cfg.get("take_profit_pct", 0.02)
    
    total_bars = len(data)
    if total_bars < train_bars + test_bars:
        train_bars = max(5, total_bars // 2)
        test_bars = max(2, total_bars - train_bars)
        
    folds = []
    train_end = train_bars
    while train_end + test_bars <= total_bars:
        train_data = data[:train_end]
        test_data = data[train_end:train_end + test_bars]
        
        best_lookback = lookback_options[0]
        best_train_perf = -float("inf")
        for lb in lookback_options:
            res = run_strategy_simulation(train_data, "momentum", lookback=lb, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct)
            if res["return_pct"] > best_train_perf:
                best_train_perf = res["return_pct"]
                best_lookback = lb
                
        flat_res = run_strategy_simulation(test_data, "flat", stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct)
        mom_fixed_res = run_strategy_simulation(test_data, "momentum", lookback=5, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct)
        mom_tuned_res = run_strategy_simulation(test_data, "momentum", lookback=best_lookback, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct)
        timesfm_res = run_strategy_simulation(test_data, "timesfm_overlay", lookback=best_lookback, forecasts=forecasts, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct) if forecasts else None
        
        folds.append({
            "train_start_dt": train_data[0]["datetime"], "train_end_dt": train_data[-1]["datetime"],
            "test_start_dt": test_data[0]["datetime"], "test_end_dt": test_data[-1]["datetime"],
            "tuned_lookback": best_lookback, "flat": flat_res, "momentum_fixed_5": mom_fixed_res,
            "momentum_tuned": mom_tuned_res, "timesfm_overlay": timesfm_res
        })
        train_end += test_bars
    return folds

def main():
    parser = argparse.ArgumentParser(description="NAS100 Day Trading Backtesting Engine")
    parser.add_argument("data_csv", help="Path to historical price data CSV")
    parser.add_argument("--config", default="config/blueberry-mt5.json", help="Path to broker config JSON")
    parser.add_argument("--forecasts", default=None, help="Optional causal TimesFM forecasts CSV")
    parser.add_argument("--train-bars", type=int, default=100, help="Number of training bars for initial fold")
    parser.add_argument("--test-bars", type=int, default=20, help="Number of test bars per fold")
    parser.add_argument("--symbol", default=None, help="Optional symbol filter")
    args = parser.parse_args()
    
    print_disclaimer()
    try:
        config = load_config(args.config)
        data = load_csv_data(args.data_csv)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
        
    if args.symbol:
        data = [d for d in data if d["symbol"].upper() == args.symbol.upper()]
        if not data:
            print(f"[ERROR] No data found for symbol '{args.symbol}'.")
            sys.exit(1)
            
    forecasts = load_forecasts(args.forecasts) if args.forecasts else {}
    try:
        folds = run_backtest(data, config, forecasts=forecasts)
    except Exception as e:
        print(f"[ERROR] Backtest failed: {e}")
        sys.exit(1)
        
    print("\n" + "=" * 78)
    print("BACKTEST RESULTS SUMMARY (EUR 500 Paper Capital)")
    print("=" * 78)
    print(f"Total Folds: {len(folds)}")
    for idx, fold in enumerate(folds, 1):
        print(f"\n--- Fold {idx} ---")
        print(f"Train: {fold['train_start_dt']} to {fold['train_end_dt']} | Test: {fold['test_start_dt']} to {fold['test_end_dt']}")
        print(f"Tuned Lookback: {fold['tuned_lookback']}")
        print(f"  [Flat] Return: {fold['flat']['return_pct']:+.2f}% | Trades: {fold['flat']['trades']}")
        print(f"  [Momentum 5] Return: {fold['momentum_fixed_5']['return_pct']:+.2f}% | Trades: {fold['momentum_fixed_5']['trades']}")
        print(f"  [Momentum Tuned] Return: {fold['momentum_tuned']['return_pct']:+.2f}% | Trades: {fold['momentum_tuned']['trades']}")
        if fold['timesfm_overlay']:
            print(f"  [TimesFM Overlay] Return: {fold['timesfm_overlay']['return_pct']:+.2f}% | Trades: {fold['timesfm_overlay']['trades']}")
    print("=" * 78)

if __name__ == "__main__":
    main()

