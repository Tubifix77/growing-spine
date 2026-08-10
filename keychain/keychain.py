"""keychain.py — one function: give it a prompt, get a response."""
import asyncio
import time, os, yaml
from . import quota_state as qs
from . import provider as prov


def _load_config() -> list:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)["providers"]


# A saturated upstream usually clears in minutes; 10 min balances "retry
# the smart rung soon" against burning RPM on probes. Each failed upward
# probe refreshes exhausted_at, self-throttling to one attempt per window.
UPWARD_REPROBE_SECS = 600


def order_providers(enabled, state, now, cooldown=UPWARD_REPROBE_SECS):
    """Priority-aware provider order with upward re-probe (2026-07-18).

    A lower rung serving must not lock out smarter rungs whose saturation
    may have cleared: exhausted providers past the cooldown compete at
    their config priority again; still-cooling ones sit at the tail as
    last-resort probes (unchanged all-walled behaviour)."""
    def exhausted(p):
        ps = state.get(p["key"], {})
        return (ps.get("exhausted_at") or 0) > (ps.get("last_success_at") or 0)
    def cooled(p):
        return (now - (state.get(p["key"], {}).get("exhausted_at") or 0)) >= cooldown
    return ([p for p in enabled if not exhausted(p) or cooled(p)] +
            [p for p in enabled if exhausted(p) and not cooled(p)])


def classify_error(err: str) -> str:
    """Sort a provider error string into an action class.
    too_large / quota -> mark exhausted, next provider
    retryable         -> backoff-retry same provider (per-minute, 5xx, traffic)
    flaky             -> next provider immediately (degenerate free-pool
                         responses: empty completions, timeouts, conn resets --
                         2026-07-17: these used to hard-raise and abort the
                         WHOLE chain, losing the cycle even with open windows)
    hard              -> raise
    """
    err_l = err.lower()
    if ("413" in err or "request too large" in err_l or "request_too_large" in err_l
            or "too large for model" in err_l or "context length" in err_l
            or "maximum context" in err_l or "reduce the length" in err_l):
        return "too_large"
    if (("rate_limit" in err_l or "too_many_requests" in err_l)
            and ("per minute" in err_l or "per-minute" in err_l
                 or "per_minute" in err_l or "rpm" in err_l)):
        return "retryable"
    if ("404" in err or "not found" in err_l or "no endpoints" in err_l
            or "model_not_found" in err_l):
        # The model left the shelf (the 2026-07-19 openrouter purge, ling on
        # 2026-08-07). This is NOT the account being out of budget: a rung with
        # other models declared should fall to the next one. Returned as its own
        # class since 2026-08-10 -- it used to be folded into "quota", which
        # walled the whole account because one model id had gone stale. Callers
        # must still never hard-raise on it.
        return "gone"
    if ("quota" in err_l or "rate_limit_exceeded" in err_l or "exceeded" in err_l
            or "billing" in err_l or "429" in err):
        return "quota"
    if ("500" in err or "502" in err or "503" in err or "504" in err
            or "high traffic" in err_l):
        return "retryable"
    if ("empty completion" in err_l or "timed out" in err_l or "timeout" in err_l
            or "connection refused" in err_l or "connection reset" in err_l
            or "temporary failure" in err_l):
        return "flaky"
    return "hard"


class Keychain:
    def __init__(self):
        self.providers = _load_config()
        self.state = qs.load_state(self.providers)
        # Metadata about the most recent successful completion. Truncation was
        # invisible system-wide until 2026-08-05, and WHICH provider answered a
        # given call was never recorded anywhere -- the doctrine is
        # timestamps-only, which is right for scheduling and wrong for
        # diagnosis. Reconstructing "who served the architect at 00:52" during
        # the gemma outage was impossible for exactly this reason.
        self.last_used = None
        # WHICH model of a multi-model rung answered. A rung is an account, not a
        # model (see provider.model_ids), so "openrouter served this" stopped
        # being a complete answer on 2026-08-10.
        self.last_model = None
        self.last_finish_reason = ""
        self.last_truncated = False

    async def complete(self, prompt: str, system: str = "",
                       max_tokens: int = 2048, **_kwargs) -> str:
        """Send prompt through the first available provider.

        Tries non-exhausted providers first, then exhausted ones as a probe
        (a 429 from an exhausted provider means "not yet"; a success means
        the window reopened). Raises RuntimeError if all providers fail.

        **_kwargs swallows any legacy keyword arguments — ignored.
        """
        enabled = [p for p in self.providers if p.get("enabled", True)]
        exhausted_keys = {p["key"] for p in enabled
                          if qs.is_exhausted(self.state, p["key"])}
        # Priority-aware order incl. upward re-probe of cooled smart rungs.
        ordered = order_providers(enabled, self.state, time.time())

        had_transient = False
        for cfg in ordered:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            # A rung is one ACCOUNT with an ordered model list. A 429 spends the
            # SHARED budget and ends the rung; a 404 retires one model id only and
            # falls to the next. Folding those together (before 2026-08-10) walled
            # a live account because a single id had gone stale.
            variants = prov.model_ids(cfg)
            stop_rung, gone_count = False, 0
            for mid in variants:
                for attempt in range(3):
                    result = await prov.call(cfg, messages,
                                             max_tokens=max_tokens, model=mid)

                    if result["error"] is None:
                        if cfg["key"] in exhausted_keys:
                            print(f"[keychain] {cfg['key']} window REOPENED "
                                  f"(probe of a believed-exhausted provider "
                                  f"succeeded)")
                        self.last_used = cfg["key"]
                        self.last_model = mid
                        # Truncation metadata for the caller. complete() still
                        # returns a plain str -- ten call sites depend on that --
                        # so the flags ride on the instance beside last_used. A
                        # caller that cares (the think loop, the batch judge)
                        # reads them; the rest are unaffected.
                        self.last_finish_reason = result.get("finish_reason") or ""
                        self.last_truncated = bool(result.get("truncated"))
                        if self.last_truncated:
                            print(f"[keychain] {cfg['key']} reply hit the "
                                  f"{max_tokens}-token ceiling "
                                  f"(finish_reason=length)")
                        qs.record_success(self.state, cfg["key"])
                        return result["text"]

                    err = str(result["error"])
                    kind = classify_error(err)

                    if kind == "gone":
                        # This model id left the shelf; the account is fine.
                        gone_count += 1
                        if len(variants) > 1:
                            print(f"[keychain] {cfg['key']}: {mid} is gone from "
                                  f"the shelf -- falling to the next model")
                        break  # next MODEL, same rung

                    if kind in ("too_large", "quota"):
                        qs.record_exhaustion(self.state, cfg["key"])
                        stop_rung = True
                        break  # the ACCOUNT is spent -- next provider

                    if kind == "flaky":
                        had_transient = True
                        print(f"[keychain] {cfg['key']} flaky ({err[:70]}) "
                              f"-- next provider")
                        stop_rung = True
                        break  # degenerate response; another window may serve it

                    if kind == "retryable":
                        had_transient = True
                        if attempt < 2:
                            await asyncio.sleep(3 * (2 ** attempt))  # 3s, 6s
                            continue
                        stop_rung = True
                        break  # move to next provider

                    # Hard error
                    raise RuntimeError(f"Provider {cfg['key']} error: {err}")

                if stop_rung:
                    break
            if not stop_rung and gone_count == len(variants):
                # EVERY declared model has left the shelf: wall the rung so we
                # stop paying a round trip per dead id every cycle. Preserves the
                # 2026-07-19 purge behaviour, which must never hard-raise. Counted
                # rather than inferred from the last model's verdict -- a gone id
                # followed by a flaky one would otherwise wall a healthy account.
                qs.record_exhaustion(self.state, cfg["key"])

        if had_transient:
            raise RuntimeError("All providers temporarily unavailable.")
        raise RuntimeError("All providers exhausted.")

    def any_available(self) -> bool:
        enabled = [p for p in self.providers if p.get("enabled", True)]
        return any(not qs.is_exhausted(self.state, p["key"]) for p in enabled)
