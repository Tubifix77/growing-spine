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

    def available_providers(self) -> list:
        return [p for p in self.providers if qs.is_available(self.state, p["key"], p)]

    async def complete(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        """
        Send prompt through the highest-priority available provider.
        Returns response text. Raises RuntimeError if all quota exhausted.
        Distinguishes transient failures (retry) from real exhaustion (sleep).
        """
        available = self.available_providers()
        if not available:
            raise RuntimeError("All providers exhausted. Sleeping.")

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
                    return result["text"]

                err = str(result["error"])
                # Check quota exhaustion first — a "quota exceeded" 429
                # must not be misclassified as a transient per-minute limit.
                is_quota = (
                    "quota" in err.lower() or
                    "rate_limit_exceeded" in err.lower() or
                    "exceeded" in err.lower() or
                    "billing" in err.lower()
                )
                if is_quota:
                    # Record actual call count at exhaustion as discovered limit
                    current_used = self.state[cfg["key"]].get("used", 0)
                    self.state[cfg["key"]]["discovered_limit"] = current_used
                    self.state[cfg["key"]]["used"] = current_used + 1  # mark exhausted
                    qs.save_state(self.state)
                    break  # move to next provider

                # Transient: retry same provider with backoff
                is_transient = (
                    "429" in err or
                    "too_many_requests" in err.lower() or
                    "high traffic" in err.lower() or
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

    def any_available(self) -> bool:
        return bool(self.available_providers())
