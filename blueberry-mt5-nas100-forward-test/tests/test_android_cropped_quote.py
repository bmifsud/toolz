import pytest
from android_cropped_quote import parse_text

GOOD = "+1769 0.06% iz\nNAS100 28098.84 28100.06 |\n04:28:54 = 122 L:27991.02 H:28141.66"

def test_real_observed_quote():
    result = parse_text(GOOD)
    assert result["bid"] == "28098.84"
    assert result["ask"] == "28100.06"
    assert result["spread_mt5_points"] == 122
    assert result["tradable"] is False

@pytest.mark.parametrize("text", [
    GOOD.replace("122 L:", "121 L:"),
    GOOD.replace("28100.06", "28090.06"),
    GOOD.replace("NAS100", "SP500"),
    GOOD + "\nNAS100 28098.84 28100.06",
    GOOD.replace("28100.06", "2810O.06"),
])
def test_reject_invalid(text):
    with pytest.raises(ValueError):
        parse_text(text)
