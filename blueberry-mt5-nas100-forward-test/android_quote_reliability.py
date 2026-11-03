"""Evaluate consecutive read-only OCR observations. No orders or ledger integration."""
import argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from pathlib import Path
import sys

def evaluate(records, max_age_seconds=30):
    if len(records) < 3:
        return {"status": "INSUFFICIENT_SAMPLES", "tradable": False}
    previous = None
    now = datetime.now(timezone.utc)
    unique = set()
    for record in records:
        try:
            if record["status"] != "OCR_SINGLE_CAPTURE_UNVERIFIED" or record["tradable"] is not False:
                raise ValueError("Non-OCR observation")
            at = datetime.fromisoformat(record["captured_at_utc"].replace("Z","+00:00"))
            if at.tzinfo is None:
                raise ValueError("Missing timezone")
            bid, ask = Decimal(record["bid"]), Decimal(record["ask"])
            points = int(record["spread_mt5_points"])
            if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask <= bid or points <= 0 or (ask-bid)*100 != points:
                raise ValueError("Spread inconsistency")
            if at > now + timedelta(seconds=2):
                raise ValueError("Future capture time")
            if (now-at).total_seconds() > max_age_seconds:
                return {"status":"STALE_CAPTURE","tradable":False}
            if previous and at <= previous:
                raise ValueError("Non-increasing capture times")
            previous = at
            unique.add((bid, ask))
        except (ValueError,KeyError,TypeError,ArithmeticError) as e:
            return {"status":"REJECTED","tradable":False,"reason":str(e)}
    if (now-previous).total_seconds()>max_age_seconds:
        return {"status":"STALE_CAPTURE","tradable":False}
    if len(unique)<2:
        return {"status":"NO_PRICE_CHANGE_OBSERVED","tradable":False}
    return {"status":"CONSISTENT_CAPTURES_BROKER_TIME_UNVERIFIED",
            "samples":len(records),"tradable":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("jsonl",type=Path)
    args=p.parse_args()
    try:
        records=[json.loads(line) for line in args.jsonl.read_text().splitlines() if line.strip()]
        print(json.dumps(evaluate(records)))
        return 0
    except (OSError,ValueError) as e:
        print(json.dumps({"status":"UNAVAILABLE","tradable":False,"reason":str(e)}))
        return 2

if __name__=="__main__":
    sys.exit(main())
