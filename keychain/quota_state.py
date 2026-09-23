"""quota_state.py — per-provider quota tracking, persisted to disk.

Timestamps only, no token counting:
  last_success_at    — unix time of the most recent successful call.
                       "how long has it been failing" = now - last_success_at
  exhausted_at       — set on the FIRST 429 of a dark period, cleared on the
                       success that ends it. Presence means "currently failing".
  last_recovery_secs — length of the most recent dark period: the gap between
                       the first failure that started it and the success that
                       ended it (b -> g on a timeline a,b,c,d,e,f,g where a & g
                       are successes and b..f are failures). "how long did it
                       take to come back last time" = this value.

No limits. No reserve floors. No config-based arithmetic.
Just try, fail, remember how long the outage lasted, try again.
"""
import json, os, time

STATE_FILE = os.path.join(os.path.dirname(__file__), "quota_state.json")


def load_state(providers: list) -> dict:
    """Load persisted quota state, initialising missing providers."""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    for p in providers:
        k = p["key"]
        if k not in state:
            state[k] = {}
    return state


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def record_success(state: dict, key: str):
    """Call succeeded. If we were in a dark period (exhausted_at set), this is
    the success that ends it -> record how long the outage lasted (now minus the
    first failure), then clear the flag."""
    s = state.setdefault(key, {})
    ex = s.pop("exhausted_at", None)
    now = time.time()
    if ex is not None:
        s["last_recovery_secs"] = now - ex   # b -> g: full outage length
    s["last_success_at"] = now
    save_state(state)


def record_exhaustion(state: dict, key: str, retry_after_s=None):
    """Got a 429. If this is the FIRST failure of a new dark period, stamp
    exhausted_at = now (this is 'b'). Subsequent failures in the same period
    leave it untouched, so the eventual recovery measures from the first failure,
    not the last."""
    s = state.setdefault(key, {})
    if "exhausted_at" in s:
        return  # already inside a dark period; keep the original first-failure time
    s["exhausted_at"] = time.time()
    # WHEN THE PROVIDER SAYS TO COME BACK, written down as an absolute time.
    # Google's 429 carries `retryDelay: 41s` and we used to sleep a flat 120,
    # so roughly a third of every dark period was ours rather than theirs
    # (139 quota sleeps in 17 h, measured 2026-09-23). Absent when the
    # provider said nothing -- never invented.
    if retry_after_s and retry_after_s > 0:
        s["retry_at"] = time.time() + float(retry_after_s)
    save_state(state)


def earliest_retry_seconds(state: dict, now=None):
    """Soonest moment any walled rung SAID it would be ready, in seconds.

    Only rungs that actually told us are considered; a rung that said nothing
    contributes nothing, so this returns None when nobody spoke and the caller
    keeps its own default. Never negative.
    """
    now = time.time() if now is None else now
    waits = [s["retry_at"] - now
             for s in state.values()
             if isinstance(s, dict) and "exhausted_at" in s and "retry_at" in s]
    waits = [w for w in waits if w is not None]
    return max(0.0, min(waits)) if waits else None


def is_exhausted(state: dict, key: str) -> bool:
    """True if the provider is currently marked as exhausted."""
    return "exhausted_at" in state.get(key, {})
