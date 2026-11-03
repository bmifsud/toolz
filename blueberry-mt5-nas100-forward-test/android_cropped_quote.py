"""One-shot read-only OCR of fixed MT5 NAS100 quote row. No trading actions."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import re
import subprocess
import sys

PRICE = r"(\d{4,6}\.\d{2})"
ROW = re.compile(r"\bNAS100\s+" + PRICE + r"\s+" + PRICE + r"\b")
SPREAD = re.compile(r"\b(\d{1,5})\s+L:")
WIDTH, HEIGHT = 1200, 1920

def parse_text(text):
    rows = [line for line in text.splitlines() if "NAS100" in line.upper()]
    if len(rows) != 1:
        raise ValueError("Missing or ambiguous NAS100 row")
    match = ROW.search(rows[0])
    spread = SPREAD.search(text)
    if not match or not spread:
        raise ValueError("Bid, ask, or MT5 spread not recognized")
    bid, ask = (Decimal(x) for x in match.groups())
    points = int(spread.group(1))
    if bid <= 0 or ask <= bid or points <= 0 or (ask-bid)*100 != points:
        raise ValueError("Spread mismatch")
    return {"symbol": "NAS100", "bid": str(bid), "ask": str(ask),
            "spread_mt5_points": points, "spread_price_units": str(ask-bid),
            "status": "OCR_SINGLE_CAPTURE_UNVERIFIED", "tradable": False}

def extract(path):
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or (int.from_bytes(data[16:20],"big"),int.from_bytes(data[20:24],"big")) != (WIDTH,HEIGHT):
        raise ValueError("Unsupported screenshot dimensions or format")
    crop = subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",str(path),
                           "-vf","crop=570:100:90:555","-f","image2pipe","-vcodec","png","-"],
                          capture_output=True,timeout=15,check=True)
    ocr = subprocess.run(["tesseract","stdin","stdout","--psm","6"],
                         input=crop.stdout,capture_output=True,timeout=15,
                         env=__import__("os").environ | {"OMP_THREAD_LIMIT":"1"},check=True)
    return parse_text(ocr.stdout.decode("utf-8",errors="replace"))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("screenshot")
    args=p.parse_args()
    try:
        print(json.dumps(extract(args.screenshot)))
        return 0
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        print(json.dumps({"status":"UNAVAILABLE","tradable":False,"reason":str(e)}))
        return 2

if __name__=="__main__":
    sys.exit(main())
