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
QUOTA_STATE = os.path.join(REPO, "keychain", "quota_state.json")
CONFIG = os.path.join(REPO, "config.yaml")
FLATLINE_HOURS = 12  # google_gemma sat dead 55h before anyone noticed, 2026-08-02

def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def check_sensor():
    # At boot the Persistent timer fires while the network is still coming up
    # AND before the brain's first ensure_body has respawned the container --
    # both raced to SENSOR:fail(JSONDecodeError) on 2026-07-15/16. Four tries
    # 20s apart cover ~1 min of boot settling; a mid-day run passes on try 1.
    last = "SENSOR:fail(no-attempt)"
    for attempt in range(4):
        if attempt:
            time.sleep(20)
        last = _sensor_once()
        if last.startswith("SENSOR:ok") or last == "SENSOR:MOCK(!!)":
            return last  # ok, or a definitive non-transient verdict
    return last


def _sensor_once():
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

def journal_integrity():
    """Detect + auto-repair torn/interleaved journal lines (abrupt-shutdown
    damage). Recovers the last complete {...} object from a torn line; drops
    only the unrecoverable fragment. Backs up before any rewrite."""
    jpath = os.path.join(MIND, "journal.jsonl")
    try:
        lines = open(jpath, encoding="utf-8", errors="replace").readlines()
    except OSError:
        return "JOURNAL:no-file"
    bad = []
    for i, l in enumerate(lines):
        if not l.strip():
            continue
        try:
            json.loads(l)
        except Exception:
            bad.append(i)
    if not bad:
        return "JOURNAL:clean"
    # repair
    import shutil, time as _t
    shutil.copy(jpath, jpath + ".bak-" + _t.strftime("%Y%m%d-%H%M%S"))
    fixed, recovered, dropped = [], 0, 0
    for l in lines:
        s = l.strip()
        if not s:
            continue
        try:
            json.loads(s)
            fixed.append(l if l.endswith("\n") else l + "\n")
            continue
        except Exception:
            pass
        ok = False
        for start in [i for i, c in enumerate(s) if c == "{"]:
            try:
                obj = json.loads(s[start:])
                fixed.append(json.dumps(obj) + "\n")
                recovered += 1
                ok = True
                break
            except Exception:
                continue
        if not ok:
            dropped += 1
    open(jpath, "w", encoding="utf-8").writelines(fixed)
    return f"JOURNAL:REPAIRED {len(bad)} torn (recovered {recovered}, dropped {dropped})"


def check_flatline():
    """FLATLINE: an ENABLED provider with no success in FLATLINE_HOURS.
    Silence is the failure mode that already bit once -- google_gemma
    (82%% of all thinks) sat with zero successes for 55h, Aug 2->4, 2026,
    masked because smaller thinks kept succeeding elsewhere and nothing
    ever printed "gemma is down". A wall alone is normal (quota exhaustion
    is the free tier working); FLATLINE fires only when last_success is
    older than the threshold, regardless of exhausted_at -- catches a
    provider that keeps failing on every re-probe just as well as one that
    stopped being tried at all."""
    try:
        import yaml
        cfg = yaml.safe_load(open(CONFIG))
        enabled = {p["key"] for p in cfg.get("providers", []) if p.get("enabled", True)}
    except Exception as e:
        return f"FLATLINE:fail(config:{type(e).__name__})"
    try:
        state = json.load(open(QUOTA_STATE))
    except Exception as e:
        return f"FLATLINE:fail(state:{type(e).__name__})"
    now = time.time()
    dead = []
    for key in sorted(enabled):
        last = state.get(key, {}).get("last_success_at")
        age_h = (now - last) / 3600 if last else None
        if age_h is None or age_h >= FLATLINE_HOURS:
            dead.append(f"{key}({'never' if age_h is None else str(int(age_h)) + 'h'})")
    return "FLATLINE:!!" + ",".join(dead) if dead else "FLATLINE:ok"


if __name__ == "__main__":
    line = (time.strftime("%Y-%m-%d %H:%M") + "  "
            + "  ".join([check_sensor(), check_fallbacks(), stub_janitor(),
                         journal_integrity(), check_flatline()]))
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print(line)
