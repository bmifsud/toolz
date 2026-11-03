# Architecture and Specifications

## 1. Overview
The Blueberry Markets MT5 NAS100 Paper Forward-Testing system is designed for robust, secure, read-only data collection and paper simulation of NASDAQ 100 Index CFDs with an initial capital allocation of EUR 500.

## 2. Components
- **Symbol Discovery**: Scans symbol lists or CSV exports for NASDAQ 100 variations (`NAS100`, `US100`, `USTEC`, etc.) without hardcoding broker-specific suffixes.
- **Data Ingestion**: Parses MT5 CSV exports containing timestamps, bid, ask, and volume.
- **Validation**: Checks quote freshness and verifies active CME/CFD market hours.
- **Ledger & EUR Conversion**: Tracks EUR 500 capital and converts USD-denominated index PnL to EUR.
- **Risk Management**: Strict limits (1% risk/trade, 3% daily DD, 6% weekly DD). No real execution or leverage.
