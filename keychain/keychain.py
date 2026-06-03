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
        """
        available = self.available_providers()
        if not available:
            raise RuntimeError("All providers exhausted. Sleeping.")

        for cfg in available:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            result = await prov.call(cfg, messages, max_tokens=max_tokens)

            if result["error"] is None:
                # track calls (1) for daily_calls quota, tokens otherwise
                usage = 1 if cfg["quota"].get("type") == "daily_calls" else result["tokens_used"]
                qs.record_usage(self.state, cfg["key"], usage)
                return result["text"]

            err = str(result["error"])
            # transient rate limit — skip this provider this cycle, don't mark exhausted
            is_transient = "429" in err or "too_many_requests" in err.lower() or "high traffic" in err.lower()
            if is_transient:
                await asyncio.sleep(2)
                continue

            # true quota exhaustion — mark dead until reset
            is_quota = "quota" in err.lower() or "rate_limit_exceeded" in err.lower() or "exceeded" in err.lower()
            if is_quota:
                self.state[cfg["key"]]["used"] = cfg["quota"].get("limit", 999999)
                qs.save_state(self.state)
                continue

            # hard error — raise
            raise RuntimeError(f"Provider {cfg['key']} error: {result['error']}")

        raise RuntimeError("All providers failed or exhausted.")

    def any_available(self) -> bool:
        return bool(self.available_providers())
