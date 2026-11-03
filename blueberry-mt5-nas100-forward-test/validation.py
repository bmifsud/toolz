"""
Freshness and Market-Hours Validation Module for NAS100 CFD data.
Validates quote timestamps and checks whether quotes fall within active trading hours.
"""

import logging
from datetime import datetime, timezone, time
from typing import Dict, Any, Optional

logger = logging.getLogger("blueberry_validation")

# NASDAQ index / CFD trading hours (UTC approximate or general CME/CFD hours: Sun 22:00 to Fri 21:15 UTC)
# Daily maintenance break: 21:15 - 22:00 UTC (approximate)

class MarketValidator:
    def __init__(self, max_data_age_seconds: int = 300):
        self.max_data_age_seconds = max_data_age_seconds

    def is_fresh(self, quote_timestamp: datetime, current_time: Optional[datetime] = None) -> bool:
        """
        Validates that the quote timestamp is within acceptable freshness limits.
        """
        now = current_time or datetime.now(timezone.utc)
        if quote_timestamp.tzinfo is None:
            # Assume UTC if naive
            quote_timestamp = quote_timestamp.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        age = (now - quote_timestamp).total_seconds()
        if 0 <= age <= self.max_data_age_seconds:
            return True
        logger.warning(f"Quote data stale. Age: {age} seconds (max allowed: {self.max_data_age_seconds})")
        return False

    def is_market_open(self, quote_timestamp: datetime) -> bool:
        """
        Checks if the given timestamp falls within active NASDAQ index CFD trading hours.
        Standard CFD hours: Sunday ~22:00 UTC to Friday ~21:15 UTC, with daily pauses.
        """
        weekday = quote_timestamp.weekday() # 0 = Monday, 5 = Saturday, 6 = Sunday
        t = quote_timestamp.time()

        # Saturday is closed
        if weekday == 5:
            return False

        # Sunday before 22:00 UTC is closed
        if weekday == 6 and t < time(22, 0):
            return False

        # Friday after 21:15 UTC is closed
        if weekday == 4 and t > time(21, 15):
            return False

        # Daily break between 21:15 and 22:00 UTC on Mon-Thu
        if weekday in (0, 1, 2, 3) and time(21, 15) <= t < time(22, 0):
            return False

        return True
