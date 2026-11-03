from data_ingestion import DataIngestion

def test_reject_missing_bad_and_inverted_quotes(tmp_path):
    f = tmp_path / "quotes.csv"
    f.write_text("timestamp,symbol,bid,ask\n"
                 "invalid,NAS100,20000,20001\n"
                 "2026-11-03 10:00:00,NAS100,20002,20001\n"
                 "2026-11-03 10:00:00,NAS100,nan,20001\n"
                 "2026-11-03 10:00:00,NAS100,20000,20001\n")
    ticks = DataIngestion(str(f)).load_ticks()
    assert len(ticks) == 1
    assert ticks[0]["timestamp"].isoformat() == "2026-11-03T10:00:00+00:00"
