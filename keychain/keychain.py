"""keychain.py — one function: give it a prompt, get a response."""
import asyncio, os, yaml
from . import quota_state as qs
from . import provider as prov


def _load_config() -> list:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)["providers"]


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

    async def complete(self, prompt: str, system: str = "",
                       max_tokens: int = 2048, **_kwargs) -> str:
        """Send prompt through the first available provider.

        Tries non-exhausted providers first, then exhausted ones as a probe
        (a 429 from an exhausted provider means "not yet"; a success means
        the window reopened). Raises RuntimeError if all providers fail.

        **_kwargs swallows any legacy keyword arguments — ignored.
        """
        enabled = [p for p in self.providers if p.get("enabled", True)]
        # Put non-exhausted providers first; exhausted ones at the end as probes
        exhausted_keys = {p["key"] for p in enabled
                          if qs.is_exhausted(self.state, p["key"])}
        ordered = (
            [p for p in enabled if p["key"] not in exhausted_keys] +
            [p for p in enabled if p["key"] in exhausted_keys]
        )

        had_transient = False
        for cfg in ordered:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            for attempt in range(3):
                result = await prov.call(cfg, messages, max_tokens=max_tokens)

                if result["error"] is None:
                    if cfg["key"] in exhausted_keys:
                        print(f"[keychain] {cfg['key']} window REOPENED "
                              f"(probe of a believed-exhausted provider succeeded)")
                    self.last_used = cfg["key"]
                    qs.record_success(self.state, cfg["key"])
                    return result["text"]

                err = str(result["error"])
                kind = classify_error(err)

                if kind in ("too_large", "quota"):
                    qs.record_exhaustion(self.state, cfg["key"])
                    break  # try next provider -- retrying won't help

                if kind == "flaky":
                    had_transient = True
                    print(f"[keychain] {cfg['key']} flaky ({err[:70]}) -- next provider")
                    break  # degenerate response; another window may serve it

                if kind == "retryable":
                    had_transient = True
                    if attempt < 2:
                        await asyncio.sleep(3 * (2 ** attempt))  # 3s, 6s
                        continue
                    break  # move to next provider

                # Hard error
                raise RuntimeError(f"Provider {cfg['key']} error: {err}")

        if had_transient:
            raise RuntimeError("All providers temporarily unavailable.")
        raise RuntimeError("All providers exhausted.")

    def any_available(self) -> bool:
        enabled = [p for p in self.providers if p.get("enabled", True)]
        return any(not qs.is_exhausted(self.state, p["key"]) for p in enabled)
