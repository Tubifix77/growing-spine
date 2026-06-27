"""quota_state.py — per-provider quota tracking, persisted to disk.

Two numbers per provider, nothing else:
  last_success_at      — unix timestamp of the most recent successful call.
                         "how long has it been failing" = now - last_success_at
  last_window_duration — how long the previous open window lasted, measured as
                         the gap between two consecutive exhaustion events.
                         "how long should I expect to wait" = this value.
  exhausted_at         — set on the first 429 this window, cleared on recovery.

No token counting. No limits. No reserve floors. No config-based arithmetic.
Just try, fail, remember the gap, wait about that long, try again.
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
    """Call succeeded — clear exhausted flag, record timestamp."""
    s = state.setdefault(key, {})
    s.pop("exhausted_at", None)
    s["last_success_at"] = time.time()
    save_state(state)


def record_exhaustion(state: dict, key: str):
    """Got a 429 — if this is the first 429 this window, mark exhausted and
    shift the previous exhausted_at into prev_exhausted_at so we can measure
    the window duration on the next exhaustion."""
    s = state.setdefault(key, {})
    if "exhausted_at" in s:
        return  # already marked exhausted this window, nothing to update
    # First 429 this window: measure previous window duration if we have data
    prev = s.get("exhausted_at_prev")
    now = time.time()
    if prev is not None:
        s["last_window_duration"] = now - prev
    s["exhausted_at_prev"] = now   # save for next window measurement
    s["exhausted_at"] = now
    save_state(state)


def is_exhausted(state: dict, key: str) -> bool:
    """True if the provider is currently marked as exhausted."""
    return "exhausted_at" in state.get(key, {})
