"""keychain.py — one function: give it a prompt, get a response."""
import asyncio, os, time, yaml
from . import quota_state as qs
from . import provider as prov


# Budget floor the GENERAL executor must leave untouched, per provider, so the
# oracle's gap-finding (deciding WHAT to build -- higher leverage than one more
# build step) always has a sliver. The oracle calls with reserve=0; everything
# else uses this default. Small on purpose: only needs to cover a few short
# gap-brief calls per window.
EXECUTOR_RESERVE = 40


def _load_config() -> list:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)["providers"]


class Keychain:
    def __init__(self):
        self.providers = _load_config()
        self.state = qs.load_state(self.providers)

    def available_providers(self, reserve: int = 0) -> list:
        return [p for p in self.providers
                if qs.is_available_with_reserve(self.state, p["key"], p, reserve)]

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 2048,
                       reserve: int = EXECUTOR_RESERVE) -> str:
        """
        Send prompt through the highest-priority available provider.
        Returns response text. Raises RuntimeError if all quota exhausted.
        Distinguishes transient failures (retry) from real exhaustion (sleep).

        `reserve` is a per-provider budget floor this call will not cross. The
        general executor uses EXECUTOR_RESERVE so it cannot drain the last of the
        budget; the oracle calls with reserve=0 so gap-finding survives when the
        executor is throttled. The probe path (everything exhausted) ignores
        reserve -- a probe must always be allowed to test for reset.
        """
        available = self.available_providers(reserve=reserve)
        # If nothing is available, still attempt all providers as a probe.
        # The probe IS the real next prompt — a 429 means 'not yet',
        # a success means quota reset and we record the interval.
        probe_mode = not available
        if probe_mode:
            available = self.providers  # try everyone regardless of is_available

        had_transient = False
        for cfg in available:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            for attempt in range(3):
                result = await prov.call(cfg, messages, max_tokens=max_tokens)

                if result["error"] is None:
                    usage = 1 if cfg["quota"].get("type") == "daily_calls" else result["tokens_used"]
                    qs.record_usage(self.state, cfg["key"], usage)
                    # If we just recovered from exhaustion, record the reset interval
                    exhausted_at = self.state[cfg["key"]].get("exhausted_at")
                    if exhausted_at:
                        interval = time.time() - exhausted_at
                        self.state[cfg["key"]]["discovered_reset_interval"] = interval
                        del self.state[cfg["key"]]["exhausted_at"]
                        qs.save_state(self.state)
                    return result["text"]

                err = str(result["error"])
                # Check quota exhaustion first — a "quota exceeded" 429
                # must not be misclassified as a transient per-minute limit.
                err_l = err.lower()
                # Per-minute rate limits look like quota errors but must not
                # trigger daily exhaustion — they should retry with backoff.
                is_per_minute = (
                    ("rate_limit" in err_l or "too_many_requests" in err_l) and
                    ("per minute" in err_l or "per-minute" in err_l or
                     "per_minute" in err_l or "rpm" in err_l)
                )
                is_quota = not is_per_minute and (
                    "quota" in err_l or
                    "rate_limit_exceeded" in err_l or
                    "exceeded" in err_l or
                    "billing" in err_l
                )
                if is_quota:
                    current_used = self.state[cfg["key"]].get("used", 0)
                    self.state[cfg["key"]]["used"] = current_used + 1  # mark exhausted
                    # Start the clock on the first hit this window.
                    # Subsequent probe rejections leave exhausted_at untouched.
                    if "exhausted_at" not in self.state[cfg["key"]]:
                        self.state[cfg["key"]]["exhausted_at"] = time.time()
                    # Only update discovered_limit if we genuinely ran this window
                    # (current_used > 0 and reached at least the previous ceiling).
                    # Probe rejections at used=0 or 1 must not trash last window's value.
                    prev = self.state[cfg["key"]].get("discovered_limit", 0)
                    if current_used > 0 and current_used >= max(prev, 1):
                        self.state[cfg["key"]]["discovered_limit"] = current_used
                    qs.save_state(self.state)
                    break  # move to next provider

                # Transient: retry same provider with backoff
                is_transient = is_per_minute or (
                    "429" in err or
                    "too_many_requests" in err_l or
                    "high traffic" in err_l or
                    "HTTP 500" in err or
                    "HTTP 502" in err or
                    "HTTP 503" in err or
                    "HTTP 504" in err
                )
                if is_transient:
                    had_transient = True
                    if attempt < 2:
                        backoff = 3 * (2 ** attempt)  # 3s then 6s
                        await asyncio.sleep(backoff)
                        continue  # retry same provider
                    break  # exhausted retries, move to next provider

                # hard error - raise immediately
                raise RuntimeError(f"Provider {cfg['key']} error: {err}")
                break  # move to next provider (unreachable but clear)

        if had_transient:
            raise RuntimeError("All providers temporarily unavailable.")
        raise RuntimeError("All providers failed or exhausted.")

    def any_available(self, reserve: int = 0) -> bool:
        return bool(self.available_providers(reserve=reserve))
