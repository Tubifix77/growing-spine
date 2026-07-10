#!/usr/bin/env python3
"""spine_health.py -- daily behavioral invariant probe + stub janitor.

Static sweeps find fictions; only running the invariants finds rot.
Checks (all side-effect-free except the janitor move):
  1. SENSOR: wake_catchup_fetcher returns real news (throwaway state file,
     so the creature's own seen-list is untouched). Mock output = the
     network is down OR the mock regressed back in.
  2. STALE FALLBACKS: any composition/breadth fallback title that exists
     as a built tool (own/ or attic/) -- the disease that bit twice.
  3. STUB JANITOR: placeholder stubs in own/ older than AGE_OUT_DAYS move
     to the attic (birth debris must not become permanent residents).
Appends one line per run to ~/spine-health.log.
"""
import json, os, re, subprocess, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIND = os.path.expanduser("~/growing-spine-mind")
OWN, ATTIC = os.path.join(MIND, "tools", "own"), os.path.join(MIND, "tools", "attic")
LOG = os.path.expanduser("~/spine-health.log")
AGE_OUT_DAYS = 3
PLACEHOLDER = "DESCRIBE WHAT THIS TOOL DOES"

def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def check_sensor():
    try:
        out = subprocess.run(
            ["docker", "exec", "-e", "WAKE_CATCHUP_STATE=/tmp/health_probe_state.json",
             "growing-spine-body", "wake_catchup_fetcher"],
            capture_output=True, text=True, timeout=40).stdout.strip()
        items = json.loads(out)
        if not isinstance(items, list) or not items:
            return "SENSOR:empty"
        if any("Mock News Item" in (i.get("title") or "") for i in items):
            return "SENSOR:MOCK(!!)"
        return f"SENSOR:ok({len(items)} fresh)"
    except Exception as e:
        return f"SENSOR:fail({type(e).__name__})"

def check_fallbacks():
    sys.path.insert(0, REPO)
    try:
        from executive.loop import _COMPOSITION_FALLBACKS, _FALLBACK_GAPS
    except Exception as e:
        return f"FALLBACKS:import-fail({type(e).__name__})"
    built = set()
    for d in (OWN, ATTIC):
        try:
            built |= {norm(n) for n in os.listdir(d)}
        except OSError:
            pass
    stale = []
    for fb in _COMPOSITION_FALLBACKS:
        if norm(fb.get("title", "")) in built:
            stale.append("comp:" + fb.get("title", ""))
    for cat, fb in _FALLBACK_GAPS.items():
        if norm(fb.get("title", "")) in built:
            stale.append("gap:" + fb.get("title", ""))
    return f"STALE-FALLBACKS:{len(stale)}[{'; '.join(stale)}]" if stale else "STALE-FALLBACKS:0"

def stub_janitor():
    moved, now = [], time.time()
    try:
        names = os.listdir(OWN)
    except OSError:
        return "JANITOR:no-own-dir"
    os.makedirs(ATTIC, exist_ok=True)
    for n in names:
        p = os.path.join(OWN, n)
        if not os.path.isfile(p):
            continue
        try:
            if PLACEHOLDER not in open(p, encoding="utf-8", errors="replace").read(2000):
                continue
            if (now - os.path.getmtime(p)) / 86400 < AGE_OUT_DAYS:
                continue
            os.replace(p, os.path.join(ATTIC, n))
            moved.append(n)
        except OSError:
            continue
    return f"JANITOR:aged-out {len(moved)}" + (f"[{'; '.join(moved)}]" if moved else "")

if __name__ == "__main__":
    line = (time.strftime("%Y-%m-%d %H:%M") + "  "
            + "  ".join([check_sensor(), check_fallbacks(), stub_janitor()]))
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line)
