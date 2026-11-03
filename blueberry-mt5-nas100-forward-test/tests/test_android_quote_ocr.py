import pytest
from android_quote_ocr import extract

HEAD="level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
def row(x,y,text,conf=99):
    return f"5\t1\t1\t1\t1\t1\t{x}\t{y}\t80\t20\t{conf}\t{text}\n"
def sample(bid="28106.84",ask="28108.06",conf=99):
    return HEAD+row(100,495,"NAS100")+row(315,495,bid,conf)+row(420,495,ask,conf)
def test_reference_layout():
    result=extract(sample())
    assert result["spread"]=="1.22" and not result["tradable"]
@pytest.mark.parametrize("tsv",[
    HEAD+row(315,495,"28106.84")+row(420,495,"28108.06"),
    sample("28106.84","28105.00"),
    sample("28106.84","28108.06",70),
    sample("28I06.84","28108.06"),
    sample("28106.84","28250.06"),
])
def test_fail_closed(tsv):
    with pytest.raises(ValueError):
        extract(tsv)
