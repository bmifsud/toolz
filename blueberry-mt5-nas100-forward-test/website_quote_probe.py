"""Read-only probe of Blueberry public indices HTML. Not an execution-price feed."""
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from decimal import Decimal, InvalidOperation
import argparse
import json
import re
import sys
import time

URL = "https://blueberrymarkets.com/trading/indices/"

class QuoteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = None
        self.values = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-symbol") == "NAS100" and attrs.get("data-type") in ("bid", "ask", "spread"):
            self.active = attrs["data-type"]
    def handle_data(self, data):
        if self.active is not None:
            self.values[self.active] = self.values.get(self.active, "") + data.strip()
    def handle_endtag(self, tag):
        if self.active is not None and tag == "div":
            self.active = None

def parse_quote(html):
    parser = QuoteParser()
    parser.feed(html)
    raw = parser.values
    if not all(raw.get(k) for k in ("bid", "ask")):
        raise ValueError("NAS100 bid/ask missing or placeholders")
    try:
        bid = Decimal(raw["bid"].replace(",", ""))
        ask = Decimal(raw["ask"].replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("NAS100 bid/ask not numeric") from exc
    if not (bid > 0 and ask >= bid):
        raise ValueError("NAS100 prices invalid")
    return {"symbol": "NAS100", "bid": str(bid), "ask": str(ask), "spread": str(ask-bid)}

def probe():
    req = Request(URL, headers={"User-Agent": "NAS100-readonly-quote-validation/1.0"})
    with urlopen(req, timeout=12) as response:
        html = response.read(2_000_000).decode("utf-8", "replace")
    result = parse_quote(html)
    result.update({"source": URL, "retrieved_at_unix": int(time.time()), "status": "INDICATIVE_UNVERIFIED", "tradable": False})
    return result

def main():
    try:
        result = probe()
    except (ValueError, HTTPError, URLError, TimeoutError) as exc:
        print(json.dumps({"status": "UNAVAILABLE", "tradable": False, "reason": str(exc)}))
        return 2
    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
