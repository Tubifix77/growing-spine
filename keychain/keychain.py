"""keychain.py — one function: give it a prompt, get a response."""
import asyncio, os, yaml
from . import quota_state as qs
from . import provider as prov


def _load_config() -> list:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)["providers"]


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
        ordered = (
            [p for p in enabled if not qs.is_exhausted(self.state, p["key"])] +
            [p for p in enabled if qs.is_exhausted(self.state, p["key"])]
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
                    qs.record_success(self.state, cfg["key"])
                    return result["text"]

                err = str(result["error"])
                err_l = err.lower()

                # STRUCTURAL: request too big for this provider (e.g. Groq 413
                # "Request too large ... TPM Limit 12000"). Retrying the identical
                # oversized request always fails; the message says "per minute" so
                # it must be caught BEFORE the per-minute check. Mark & move on.
                is_too_large = (
                    "413" in err or
                    "request too large" in err_l or
                    "request_too_large" in err_l or
                    "too large for model" in err_l or
                    "context length" in err_l or
                    "maximum context" in err_l or
                    "reduce the length" in err_l
                )

                # Per-minute rate limit — transient, retry with backoff
                is_per_minute = (not is_too_large) and (
                    ("rate_limit" in err_l or "too_many_requests" in err_l) and
                    ("per minute" in err_l or "per-minute" in err_l or
                     "per_minute" in err_l or "rpm" in err_l)
                )

                # Quota exhaustion — mark provider and move on
                is_quota = (not is_per_minute) and (not is_too_large) and (
                    "quota" in err_l or
                    "rate_limit_exceeded" in err_l or
                    "exceeded" in err_l or
                    "billing" in err_l or
                    "429" in err
                )

                if is_too_large or is_quota:
                    qs.record_exhaustion(self.state, cfg["key"])
                    break  # try next provider — retrying won't help

                if is_per_minute or "500" in err or "502" in err or                         "503" in err or "504" in err or                         "high traffic" in err_l:
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
