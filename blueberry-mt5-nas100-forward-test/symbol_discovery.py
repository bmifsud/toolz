"""
Symbol Discovery and Contract Metadata Module for Blueberry Markets MT5 NAS100.
Strictly discovers NAS100 / US100 index CFD symbols across various broker suffix conventions
and validates contract specifications.
"""

import csv
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("blueberry_symbol_discovery")

CANDIDATE_PREFIXES = ["NAS100", "US100", "USTEC", "NQ"]

class SymbolDiscovery:
    def __init__(self, symbols_csv_path: Optional[str] = None):
        self.symbols_csv_path = symbols_csv_path

    def discover_symbols(self, raw_symbols: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Discovers matching NASDAQ 100 CFD symbols from a list of symbol dictionaries or a CSV file.
        Does not assume an exact suffix (e.g. handles NAS100, NAS100.cash, US100m, etc.).
        """
        symbols = raw_symbols or []
        if self.symbols_csv_path and not symbols:
            try:
                with open(self.symbols_csv_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        symbols.append(row)
            except Exception as e:
                logger.error(f"Failed to read symbols CSV: {e}")

        matched = []
        for sym in symbols:
            name = str(sym.get("symbol", sym.get("Name", ""))).strip().upper()
            if not name:
                continue

            # Check if any candidate prefix matches the start or core of the symbol name
            is_match = False
            for prefix in CANDIDATE_PREFIXES:
                if prefix in name:
                    is_match = True
                    break

            if is_match:
                contract_meta = {
                    "symbol": name,
                    "description": sym.get("description", sym.get("Description", "NASDAQ 100 Index CFD")),
                    "currency": sym.get("currency", sym.get("Currency", "USD")).upper(),
                    "contract_size": float(sym.get("contract_size", sym.get("ContractSize", 1.0))),
                    "digits": int(sym.get("digits", sym.get("Digits", 2))),
                    "min_lot": float(sym.get("min_lot", sym.get("MinVolume", 0.01))),
                    "max_lot": float(sym.get("max_lot", sym.get("MaxVolume", 100.0))),
                    "lot_step": float(sym.get("lot_step", sym.get("VolumeStep", 0.01))),
                    "raw_data": sym
                }
                matched.append(contract_meta)

        return matched

    def validate_contract_metadata(self, contract: Dict[str, Any]) -> bool:
        """
        Validates mandatory contract metadata fields for safe paper trading.
        """
        required_keys = ["symbol", "currency", "contract_size", "digits", "min_lot"]
        for key in required_keys:
            if key not in contract:
                logger.warning(f"Missing mandatory contract key: {key}")
                return False
        if contract["contract_size"] <= 0:
            logger.warning(f"Invalid contract size: {contract['contract_size']}")
            return False
        return True
