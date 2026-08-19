#!/usr/bin/env python3
"""Hourly tripwire: runs the two checks that must not wait for 06:30:
check_flatline (which rung went quiet) and check_throughput (is the
creature still thinking at all). Exists
because the daily 06:30 run alone let google_gemma sit dead for 55h before
anyone noticed (2026-08-02->04) -- an hourly cadence bounds that to ~1h."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spine_health as H

LOG = os.path.expanduser("~/spine-health.log")
line = (time.strftime("%Y-%m-%d %H:%M") + "  HOURLY  " + H.check_flatline()
        + "  " + H.check_throughput())
# Exit non-zero when a TRAFFIC-CARRYING rung is the silent one, so systemd marks
# the unit failed instead of the finding living only in a log nothing reads.
# Quiet low rungs stay exit-0 noise (see spine_health.exit_code).
rc = H.exit_code(H.SILENT_KEYS, H.DEAD_KEYS)
if rc:
    line += f"  SERIOUS:{','.join(sorted(H.SILENT_KEYS & H.DEAD_KEYS))}"
with open(LOG, "a") as f:
    f.write(line + "\n")
print(line)
sys.exit(rc)
