"""quota_state.py — per-provider quota tracking, persisted to disk."""
import json, os, time
from datetime import datetime, timezone
import pytz

STATE_FILE = os.path.join(os.path.dirname(__file__), "quota_state.json")


def _now_ts() -> float:
    return time.time()


def _reset_ts(resets_str: str) -> float:
    """Parse 'HH:MM Timezone' and return next reset as unix timestamp."""
    parts = resets_str.strip().split()
    hhmm, tz_name = parts[0], parts[1] if len(parts) > 1 else "UTC"
    hour, minute = int(hhmm.split(":")[0]), int(hhmm.split(":")[1])
    tz = pytz.timezone(tz_name)
    now_local = datetime.now(tz)
    reset_today = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if reset_today <= now_local:
        from datetime import timedelta
        reset_today += timedelta(days=1)
    return reset_today.timestamp()


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
            state[k] = {
                "used": 0,
                "reset_at": _reset_ts(p["quota"].get("resets", "00:00 UTC")),
            }
        # roll over if past reset time
        if _now_ts() >= state[k]["reset_at"]:
            state[k]["used"] = 0
            state[k]["reset_at"] = _reset_ts(p["quota"].get("resets", "00:00 UTC"))
            state[k].pop("exhausted_at", None)  # clear so next 429 starts a fresh interval
            # discovered_limit is kept across resets — it's the last known ceiling,
            # used for display only. No hard stop; creature pushes until the next 429.
    return state


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def effective_limit(state: dict, key: str, cfg: dict) -> int:
    """Use discovered_limit from last 429 if known, else fall back to config."""
    s = state.get(key, {})
    return s.get("discovered_limit", cfg["quota"].get("limit", 9999999))


def remaining(state: dict, key: str, cfg: dict) -> int:
    """Estimated calls/tokens left this window (>=0). Best-effort: discovered or
    configured limit minus usage. Used by reserve-aware availability checks."""
    s = state.get(key, {})
    return max(0, effective_limit(state, key, cfg) - s.get("used", 0))


def is_available(state: dict, key: str, cfg: dict) -> bool:
    if not cfg.get("enabled", True):
        return False
    s = state.get(key, {})
    return s.get("used", 0) < effective_limit(state, key, cfg)


def is_available_with_reserve(state: dict, key: str, cfg: dict, reserve: int) -> bool:
    """Available only if more than `reserve` budget remains. The reserve is a
    floor the general executor must not cross, so the oracle (reserve=0) always
    has a sliver. reserve=0 is identical to is_available."""
    if not cfg.get("enabled", True):
        return False
    return remaining(state, key, cfg) > reserve


def record_usage(state: dict, key: str, tokens: int):
    if key in state:
        state[key]["used"] = state[key].get("used", 0) + tokens
        state[key]["last_success_at"] = _now_ts()  # for Quota tab 'last success' stat
        save_state(state)
