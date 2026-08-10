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

# Run as a bare path by systemd, so sys.path[0] is scripts/ and `keychain` is
# not importable without this. configured_rungs() swallows exceptions, so a
# missing import would have made the VANISHED report silently empty rather than
# loud -- the failure mode this whole file exists to prevent.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

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
    """{model_id: config_key} for enabled openrouter entries.

    A rung may declare several model ids (one account, one quota, an ordered
    preference list -- see keychain/provider.model_ids), so this flattens rather
    than assuming one id per rung. Before 2026-08-10 a list here silently became
    an unhashable dict key and the whole report fell into the bare `except`,
    reporting no configured rungs at all.
    """
    try:
        import yaml
        from keychain.provider import model_ids
        cfg = yaml.safe_load(CONFIG.read_text())
        return {mid: p["key"] for p in cfg.get("providers", [])
                if p.get("enabled", True) and "openrouter" in p.get("key", "")
                for mid in model_ids(p)}
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
