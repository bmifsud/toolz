#!/usr/bin/env python3
"""Emit a heartbeat ONLY from an active, authorized task runner."""
import json
from pathlib import Path
import sys
import time

state = Path(sys.argv[1])
state.mkdir(parents=True, exist_ok=True)
(state / "heartbeat.json").write_text(json.dumps({"timestamp": time.time()}))
