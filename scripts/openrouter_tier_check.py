#!/usr/bin/env python3
"""Weekly OpenRouter free-tier diff -- REPORTS ONLY, never edits config.

The free tier rotates (models appear and get purged); this sensor diffs
the :free listing against last week's snapshot and appends to
~/openrouter-tier.log. Vetting what joins the hierarchy is a judgment
call (quality-floor doctrine, 2026-07-17) made by Tue + a session, with
the live page https://openrouter.ai/models?q=free open -- the "going
away" banners exist only on the page, not in the API, so GONE here means
"already removed", one step after the banner.
"""
import json, sys, time, urllib.request, pathlib

API = "https://openrouter.ai/api/v1/models"
SEEN = pathlib.Path.home() / ".openrouter_free_seen.json"
LOG = pathlib.Path.home() / "openrouter-tier.log"
CONFIG = pathlib.Path.home() / "growing-spine/config.yaml"


def fetch_free_ids():
    req = urllib.request.Request(API, headers={"User-Agent": "growing-spine-tier-check"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    out = {}
    for m in data.get("data", []):
        mid = m.get("id", "")
        if mid.endswith(":free"):
            out[mid] = {"ctx": m.get("context_length"), "name": m.get("name", "")}
    return out


def configured_rungs():
    try:
        import yaml
        cfg = yaml.safe_load(CONFIG.read_text())
        return {p["model_id"]: p["key"] for p in cfg.get("providers", [])
                if p.get("enabled", True) and "openrouter" in p.get("key", "")}
    except Exception:
        return {}


def diff_report(prev_ids, now_ids, rungs):
    """Pure diff -> report lines. prev_ids/now_ids: iterables of model ids;
    rungs: {model_id: config_key} for enabled openrouter entries."""
    new = sorted(set(now_ids) - set(prev_ids))
    gone = sorted(set(prev_ids) - set(now_ids))
    lines = [f"NEW({len(new)}): " + (", ".join(new) if new else "-"),
             f"GONE({len(gone)}): " + (", ".join(gone) if gone else "-")]
    dead = sorted(m for m in rungs if m not in set(now_ids))
    if dead:
        lines.append("!! CONFIGURED RUNG VANISHED: "
                     + ", ".join(f"{rungs[m]}={m}" for m in dead))
    return lines


def main():
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    try:
        now = fetch_free_ids()
    except Exception as e:
        with LOG.open("a") as f:
            f.write(f"{ts}  SKIPPED (fetch failed: {e})\n")
        print("fetch failed:", e)
        return 0
    prev = {}
    if SEEN.exists():
        try:
            prev = json.loads(SEEN.read_text())
        except Exception:
            prev = {}
    lines = diff_report(prev, now, configured_rungs())
    with LOG.open("a") as f:
        f.write(f"{ts}  free-models={len(now)}\n")
        for ln in lines:
            f.write(f"  {ln}\n")
    SEEN.write_text(json.dumps(now))
    print(f"{len(now)} free models; " + "; ".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
