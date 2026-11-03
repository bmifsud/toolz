# Blueberry Markets MT5 NAS100 Paper Forward-Testing Skill

## Overview
This skill provides a modular, read-only market data collection and EUR 500 paper forward-testing framework for NASDAQ 100 (NAS100) CFDs on Blueberry Markets MT5.

## Architecture
- **Symbol Discovery (`symbol_discovery.py`)**: Dynamically discovers NAS100/US100 CFD symbols across broker suffix variations and validates contract specs.
- **Data Ingestion (`data_ingestion.py`)**: Ingests bid/ask quotes and timestamps from MT5 terminal CSV exports.
- **Validation (`validation.py`)**: Enforces data freshness (<= 300s) and market-hours validation.
- **Paper Ledger (`ledger.py`)**: Manages EUR 500 initial capital, EUR conversion, and trade fills.
- **Risk Management (`risk.py`)**: Enforces conservative sizing, 1% per trade risk, 3% daily DD limit, and 6% weekly DD limit. No leverage or real orders are permitted.

## Operational Guardrails
- Read-only & paper forward testing only.
- Do not access credentials, modify backup modules, change cron, push, or merge.
- Do not invent data or report forward test started.
