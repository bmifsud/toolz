from pathlib import Path
import android_capture

def test_capture_requires_mt5_foreground(monkeypatch, tmp_path):
    class Result:
        stdout = "mCurrentFocus=other.app"
    monkeypatch.setattr(android_capture.subprocess, "run", lambda *args, **kwargs: Result())
    try:
        android_capture.capture(tmp_path)
        assert False, "capture should reject wrong app"
    except RuntimeError as e:
        assert "not foreground" in str(e)
    assert not list(tmp_path.iterdir())

def test_package_name():
    assert android_capture.MT5_PACKAGE == "net.metaquotes.metatrader5"
