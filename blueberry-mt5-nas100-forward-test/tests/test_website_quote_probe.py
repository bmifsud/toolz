import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("website_quote_probe", Path(__file__).resolve().parents[1] / "website_quote_probe.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def html(bid, ask):
    return f'<div class="NAS100-bid" data-symbol="NAS100" data-type="bid">{bid}</div><div data-symbol="NAS100" data-type="ask">{ask}</div>'

def test_valid_indicative_quote():
    q = mod.parse_quote(html("24,000.50", "24002.00"))
    assert q["spread"] == "1.50"

@pytest.mark.parametrize("bid,ask", [("--", "--"), ("0", "1"), ("100", "99"), ("abc", "101")])
def test_reject_invalid(bid, ask):
    with pytest.raises(ValueError):
        mod.parse_quote(html(bid, ask))

def test_reject_missing():
    with pytest.raises(ValueError):
        mod.parse_quote("<html></html>")
