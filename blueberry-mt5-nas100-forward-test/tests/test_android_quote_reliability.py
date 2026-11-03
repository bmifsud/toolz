from datetime import datetime, timedelta, timezone
from android_quote_reliability import evaluate

def samples():
    now=datetime.now(timezone.utc)
    return [
        {"status":"OCR_SINGLE_CAPTURE_UNVERIFIED","tradable":False,
         "captured_at_utc":(now-timedelta(seconds=5-i)).isoformat(),
         "bid":str(28108+i/100),"ask":str(28109.22+i/100),
         "spread_mt5_points":122} for i in range(3)
    ]
def test_three_consistent_still_not_tradable():
    result=evaluate(samples())
    assert result["status"]=="CONSISTENT_CAPTURES_BROKER_TIME_UNVERIFIED"
    assert result["tradable"] is False
def test_reject_spread():
    rows=samples()
    rows[1]["spread_mt5_points"]=121
    assert evaluate(rows)["status"]=="REJECTED"
def test_reject_stale():
    rows=samples()
    for row in rows:
        row["captured_at_utc"]=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
    assert evaluate(rows)["status"]=="REJECTED" or evaluate(rows)["status"]=="STALE_CAPTURE"
def test_reject_insufficient():
    assert evaluate(samples()[:2])["status"]=="INSUFFICIENT_SAMPLES"
