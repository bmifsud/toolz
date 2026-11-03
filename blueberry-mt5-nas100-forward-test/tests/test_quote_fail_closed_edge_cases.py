from datetime import datetime, timedelta, timezone
from android_cropped_quote import parse_text
from android_quote_reliability import evaluate

ROW = 'NAS100 28050.61 28051.83\n05:54:55 122 L:27991.02'

def test_spread_clock_and_points():
    record = parse_text(ROW, '05:54:55 E122')
    assert record['spread_mt5_points'] == 122
    assert record['tradable'] is False

def records():
    now = datetime.now(timezone.utc)
    return [dict(status='OCR_SINGLE_CAPTURE_UNVERIFIED', tradable=False,
        captured_at_utc=(now-timedelta(seconds=3-i)).isoformat(),
        bid=f'{28050+i}.61', ask=f'{28051+i}.83', spread_mt5_points=122)
        for i in range(3)]

def test_future_timestamp_rejected():
    rows = records()
    rows[-1]['captured_at_utc'] = (datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()
    assert evaluate(rows)['status'] == 'REJECTED'

def test_old_first_sample_rejected():
    rows = records()
    rows[0]['captured_at_utc'] = (datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
    assert evaluate(rows)['status'] == 'STALE_CAPTURE'

def test_nan_quote_rejected():
    rows = records()
    rows[1]['bid'] = 'NaN'
    assert evaluate(rows)['status'] == 'REJECTED'

def test_no_price_movement_not_tradable():
    rows = records()
    for row in rows:
        row['bid'] = '28050.61'
        row['ask'] = '28051.83'
    assert evaluate(rows)['status'] == 'NO_PRICE_CHANGE_OBSERVED'
