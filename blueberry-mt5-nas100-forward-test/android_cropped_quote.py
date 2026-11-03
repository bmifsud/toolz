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
DISPLAY_CLOCK = re.compile(r"\b([01]\d|2[0-3]):[0-5]\d:[0-5]\d\b")
WIDTH, HEIGHT = 1200, 1920

def parse_text(text, spread_text=None):
    rows = [line for line in text.splitlines() if "NAS100" in line.upper()]
    if len(rows) != 1:
        raise ValueError("Missing or ambiguous NAS100 row")
    match = ROW.search(rows[0])
    spread = SPREAD.search(text) if spread_text is None else re.search(r"(\d{1,5})\s*$", spread_text.strip())
    clock = DISPLAY_CLOCK.search(text)
    if not match or not spread or not clock:
        raise ValueError("Bid, ask, or MT5 spread not recognized")
    bid, ask = (Decimal(x) for x in match.groups())
    points = int(spread.group(1))
    if bid <= 0 or ask <= bid or points <= 0 or (ask-bid)*100 != points:
        raise ValueError("Spread mismatch")
    return {"symbol": "NAS100", "bid": str(bid), "ask": str(ask),
            "spread_mt5_points": points, "spread_price_units": str(ask-bid),
            "mt5_display_clock_unzoned": clock.group(0), "broker_timezone_verified": False,
            "status": "OCR_SINGLE_CAPTURE_UNVERIFIED", "tradable": False}

def extract(path):
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or (int.from_bytes(data[16:20],"big"),int.from_bytes(data[20:24],"big")) != (WIDTH,HEIGHT):
        raise ValueError("Unsupported screenshot dimensions or format")
    def recognize(vf, psm):
        cropped = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
                                  "-vf", vf, "-f", "image2pipe", "-vcodec", "png", "-"],
                                 capture_output=True, timeout=15, check=True)
        ocr = subprocess.run(["tesseract", "stdin", "stdout", "--psm", str(psm)],
                             input=cropped.stdout, capture_output=True, timeout=15,
                             env=__import__("os").environ | {"OMP_THREAD_LIMIT":"1"}, check=True)
        return ocr.stdout.decode("utf-8", errors="replace")

    candidates = []
    for layout, row_crop, spread_crop in (
        ("split_screen", "crop=570:100:90:555", "crop=165:35:90:625,scale=660:140:flags=neighbor"),
        ("full_screen", "crop=620:105:95:550", "crop=170:35:95:625,scale=680:140:flags=neighbor"),
        ("wide_quotes", "crop=690:110:90:550", "crop=165:35:90:625,scale=660:140:flags=neighbor"),
    ):
        try:
            row_text = recognize(row_crop, 6)
            spread_text = recognize(spread_crop, 7)
            result = parse_text(row_text, spread_text)
            # The spread crop is independently required to contain the same display clock.
            spread_clock = DISPLAY_CLOCK.search(spread_text)
            if not spread_clock:
                raise ValueError("Missing clock in spread crop")
            if spread_clock.group(0) != result["mt5_display_clock_unzoned"]:
                result["mt5_display_clock_unzoned"] = spread_clock.group(0)
                result["clock_ocr_disagreement"] = True
            result["layout_candidate"] = layout
            candidates.append(result)
        except ValueError:
            continue
    if not candidates:
        raise ValueError("No validated MT5 layout")
    if len(candidates) > 1:
        keys = ("symbol", "bid", "ask", "spread_mt5_points", "mt5_display_clock_unzoned")
        if any(tuple(candidate[k] for k in keys) != tuple(candidates[0][k] for k in keys)
               for candidate in candidates[1:]):
            raise ValueError("Conflicting MT5 layout OCR candidates")
        candidates[0]["layout_candidate"] = "overlapping_layouts_agree"
    return candidates[0]

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
