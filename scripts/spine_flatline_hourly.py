#!/usr/bin/env python3
"""Hourly tripwire: runs ONLY check_flatline() from spine_health.py. Exists
because the daily 06:30 run alone let google_gemma sit dead for 55h before
anyone noticed (2026-08-02->04) -- an hourly cadence bounds that to ~1h."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spine_health as H

LOG = os.path.expanduser("~/spine-health.log")
line = time.strftime("%Y-%m-%d %H:%M") + "  HOURLY  " + H.check_flatline()
with open(LOG, "a") as f:
    f.write(line + "\n")
print(line)
