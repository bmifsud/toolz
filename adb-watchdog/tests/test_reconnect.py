import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('reconnect', Path(__file__).resolve().parents[1] / 'reconnect.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_discovery():
    sample = 'adb-xyz._adb-tls-connect._tcp. 172.20.10.2:44677\n'
    assert module.discover(sample) == ['172.20.10.2:44677']

def test_ignores_pairing_services():
    assert module.discover('adb._adb-tls-pairing._tcp. 172.20.10.2:44677') == []

def test_no_invented_endpoint():
    assert module.discover('List of discovered mdns services') == []
