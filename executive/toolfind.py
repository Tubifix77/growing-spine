"""On-demand semantic tool search for the creature (2026-08-03, Tue's design).

The body has no embedding model (packages are fixed facts of its world), so
the /mind mount is the bus: the creature's `tool-find` builtin writes a
request file into /mind/state, this watcher thread answers it from the SAME
live embedding index the idea gate uses -- one geometry, no LLM, sub-second.
The watcher never raises: a busy index answers honestly and the tool falls
back to `tools | grep`.
"""
import json
import os
import threading
import time

REQ = "toolfind_req.json"
RES_PREFIX = "toolfind_res_"


def answer(query, k=6):
    """(ok, results-or-error). results = [(bare_name, similarity)], live only."""
    q = str(query or "").strip()
    if not q:
        return False, "empty query"
    from . import embed_gate
    if not embed_gate.available():
        return False, "index unavailable"
    try:
        hits = embed_gate.top_matches(q, k=max(1, min(int(k or 6), 12)),
                                      labels=["live"])
    except Exception as e:  # refresh race, torn read -- honest, retryable
        return False, "index busy (%s)" % type(e).__name__
    return True, [(n.split(":", 1)[1], round(s, 3)) for n, s in hits]


def _handle_once(state_dir):
    req_path = os.path.join(state_dir, REQ)
    if not os.path.exists(req_path):
        return False
    try:
        with open(req_path, encoding="utf-8") as f:
            req = json.load(f)
    except Exception:
        req = {}
    try:
        os.remove(req_path)
    except OSError:
        pass
    rid = str(req.get("id", "0"))[:40].replace("/", "_").replace("\\", "_")
    ok, payload = answer(req.get("q", ""), req.get("k", 6))
    res = {"ok": ok, ("results" if ok else "error"): payload}
    tmp = os.path.join(state_dir, RES_PREFIX + rid + ".tmp")
    final = os.path.join(state_dir, RES_PREFIX + rid + ".json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(res, f)
    os.replace(tmp, final)
    return True


def _prune(state_dir, max_age=120):
    now = time.time()
    try:
        names = os.listdir(state_dir)
    except OSError:
        return
    for n in names:
        if n.startswith(RES_PREFIX):
            p = os.path.join(state_dir, n)
            try:
                if now - os.path.getmtime(p) > max_age:
                    os.remove(p)
            except OSError:
                pass


def start_watcher(volume_mount):
    state_dir = os.path.join(volume_mount, "state")

    def _loop():
        last_prune = 0.0
        while True:
            try:
                _handle_once(state_dir)
                if time.time() - last_prune > 60:
                    _prune(state_dir)
                    last_prune = time.time()
            except Exception:
                pass
            time.sleep(0.4)

    t = threading.Thread(target=_loop, name="toolfind-watcher", daemon=True)
    t.start()
    print("[toolfind] watcher up (0.4s poll on /mind/state)")
