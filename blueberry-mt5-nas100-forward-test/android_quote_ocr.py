"""Conservative OCR of a fixed MT5 Android Quotes layout; never authorizes trades."""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import io
import json
from pathlib import Path
import re
import subprocess
import sys

NUMBER = re.compile(r"^\d{4,6}[.]\d{2}$")

def extract(tsv, image_width=960, image_height=1536, min_conf=85):
    rows = list(csv.DictReader(io.StringIO(tsv), delimiter="\t"))
    def words(x0, x1, y0, y1):
        result = []
        for r in rows:
            try:
                x, y = int(r["left"]), int(r["top"])
                conf = float(r["conf"])
                token = r["text"].strip()
            except (KeyError, ValueError):
                continue
            if x0 <= x < x1 and y0 <= y < y1 and conf >= min_conf and token:
                result.append((x, token))
        return sorted(result)
    # Tablet split view reference: NAS100 label at x~95 y~495, bid x~306, ask x~407.
    scale_x, scale_y = image_width/960, image_height/1536
    def region(x0,x1,y0,y1):
        return words(x0*scale_x,x1*scale_x,y0*scale_y,y1*scale_y)
    label = region(80,210,465,525)
    if not any(t.upper()=="NAS100" for _,t in label):
        raise ValueError("NAS100 label not confidently located")
    bid = [t for _,t in region(280,405,465,525) if NUMBER.fullmatch(t)]
    ask = [t for _,t in region(405,515,465,525) if NUMBER.fullmatch(t)]
    if len(bid)!=1 or len(ask)!=1:
        raise ValueError("Bid/ask not uniquely recognized at expected locations")
    b,a = Decimal(bid[0]),Decimal(ask[0])
    if b<=0 or a<b or a-b>Decimal("100"):
        raise ValueError("Invalid or implausible spread")
    return {"symbol":"NAS100","bid":str(b),"ask":str(a),"spread":str(a-b),
            "status":"OCR_UNVERIFIED","tradable":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("screenshot",type=Path)
    args=p.parse_args()
    try:
        # Restrict to validated reference resolution; fail closed on layout changes.
        png=args.screenshot.read_bytes()
        if png[:8]!=b"\x89PNG\r\n\x1a\n":
            raise ValueError("Not PNG")
        width=int.from_bytes(png[16:20],"big")
        height=int.from_bytes(png[20:24],"big")
        if (width,height)!=(1200,1920):
            raise ValueError(f"Unvalidated screen layout {width}x{height}")
        proc=subprocess.run(["tesseract",str(args.screenshot),"stdout","tsv"],
                            capture_output=True,text=True,timeout=30,check=True)
        result=extract(proc.stdout,width,height)
        result["captured_at_utc"]=datetime.now(timezone.utc).isoformat()
        print(json.dumps(result))
        return 0
    except (OSError,ValueError,subprocess.SubprocessError) as e:
        print(json.dumps({"status":"UNAVAILABLE","tradable":False,"reason":str(e)}))
        return 2

if __name__=="__main__":
    sys.exit(main())
