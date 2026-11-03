import pytest
import os
import csv
from datetime import datetime, timedelta
from backtest import (
    load_csv_data,
    load_forecasts,
    load_config,
    check_broker_specs,
    compute_momentum_signal,
    run_strategy_simulation,
    run_backtest
)


def create_sample_csv(tmp_path, filename="data.csv", rows=None):
    filepath = tmp_path / filename
    fieldnames = ["datetime", "symbol", "open", "high", "low", "close", "volume"]
    if rows is None:
        base_time = datetime(2026, 1, 1, 9, 0, 0)
        rows = []
        price = 18000.0
        for i in range(150):
            dt = base_time + timedelta(minutes=i)
            price += (1.0 if i % 2 == 0 else -0.5)
            rows.append({
                "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": "NAS100",
                "open": price,
                "high": price + 5.0,
                "low": price - 5.0,
                "close": price + 2.0,
                "volume": 1000.0
            })
            
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return str(filepath)


def test_schema_validation_success(tmp_path):
    csv_path = create_sample_csv(tmp_path)
    data = load_csv_data(csv_path)
    assert len(data) == 150
    assert data[0]["symbol"] == "NAS100"
    assert isinstance(data[0]["datetime"], datetime)
    assert isinstance(data[0]["close"], float)


def test_schema_validation_missing_columns(tmp_path):
    filepath = tmp_path / "bad.csv"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("datetime,symbol,open\n2026-01-01 09:00:00,NAS100,18000.0\n")
    with pytest.raises(ValueError, match="CSV missing required columns"):
        load_csv_data(str(filepath))


def test_chronological_ordering_enforcement(tmp_path):
    rows = [
        {"datetime": "2026-01-01 09:02:00", "symbol": "NAS100", "open": "18000", "high": "18010", "low": "17990", "close": "18005", "volume": "100"},
        {"datetime": "2026-01-01 09:01:00", "symbol": "NAS100", "open": "18005", "high": "18015", "low": "17995", "close": "18010", "volume": "100"}
    ]
    csv_path = create_sample_csv(tmp_path, filename="unordered.csv", rows=rows)
    with pytest.raises(ValueError, match="Chronological violation"):
        load_csv_data(csv_path)


def test_fail_closed_unknown_specification():
    config_unknown = {
        "initial_equity_eur": 500.0,
        "instrument": "NAS100_CFD",
        "spread": None,
        "slippage": None,
        "min_lot": None,
        "contract_value": None,
        "fail_closed_unknown_costs": True
    }
    with pytest.raises(ValueError, match="FAIL-CLOSED: Unknown broker specifications"):
        check_broker_specs(config_unknown)
        
    config_known = {
        "initial_equity_eur": 500.0,
        "instrument": "NAS100_CFD",
        "spread": 0.5,
        "slippage": 0.1,
        "min_lot": 0.01,
        "contract_value": 1.0,
        "fail_closed_unknown_costs": True
    }
    assert check_broker_specs(config_known) == []


def test_fold_splitting_and_tuning(tmp_path):
    csv_path = create_sample_csv(tmp_path)
    data = load_csv_data(csv_path)
    config = {
        "initial_equity_eur": 500.0,
        "spread": 0.5,
        "slippage": 0.1,
        "min_lot": 0.01,
        "contract_value": 1.0,
        "fail_closed_unknown_costs": True,
        "backtest": {
            "train_bars": 50,
            "test_bars": 20,
            "lookback_options": [3, 5, 10]
        }
    }
    folds = run_backtest(data, config)
    assert len(folds) > 0
    for fold in folds:
        assert "train_start_dt" in fold
        assert "flat" in fold
        assert "momentum_fixed_5" in fold
        assert "momentum_tuned" in fold
        assert fold["tuned_lookback"] in [3, 5, 10]


def test_baseline_vs_momentum_comparison(tmp_path):
    csv_path = create_sample_csv(tmp_path)
    data = load_csv_data(csv_path)
    test_data = data[100:130]
    
    flat_res = run_strategy_simulation(test_data, "flat")
    mom_res = run_strategy_simulation(test_data, "momentum", lookback=5)
    
    assert "trades" in flat_res
    assert flat_res["trades"] == 0
    assert "trades" in mom_res


def test_optional_timesfm_overlay(tmp_path):
    csv_path = create_sample_csv(tmp_path)
    data = load_csv_data(csv_path)
    
    # Create forecast csv
    forecast_path = tmp_path / "forecasts.csv"
    with open(forecast_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["datetime", "predicted_close"])
        writer.writeheader()
        for bar in data:
            writer.writerow({
                "datetime": bar["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                "predicted_close": bar["close"] + 10.0
            })
            
    forecasts = load_forecasts(str(forecast_path))
    assert len(forecasts) == len(data)
    
    config = {
        "initial_equity_eur": 500.0,
        "spread": 0.5,
        "slippage": 0.1,
        "min_lot": 0.01,
        "contract_value": 1.0,
        "fail_closed_unknown_costs": True,
        "backtest": {
            "train_bars": 50,
            "test_bars": 20,
            "lookback_options": [3, 5, 10]
        }
    }
    folds = run_backtest(data, config, forecasts=forecasts)
    assert len(folds) > 0
    for fold in folds:
        assert fold["timesfm_overlay"] is not None
        assert "return_pct" in fold["timesfm_overlay"]
