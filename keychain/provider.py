"""provider.py — single OpenAI-compatible provider call."""
import asyncio, json
import urllib.request, urllib.error


def _extract_text_tokens(data: dict):
    """None-safe extraction. Reasoning models (gpt-oss via OpenRouter) can
    return content=null -- and even reasoning=null -- e.g. when
    finish_reason=length lands mid-reasoning; usage can be null too.
    dict.get's default is evaluated EAGERLY, so len(text)//4 as a .get
    default raised len(None) and killed the cycle (2026-07-17 02:00)."""
    msg = (data.get("choices") or [{}])[0].get("message") or {}
    text = msg.get("content") or msg.get("reasoning") or ""
    usage = data.get("usage") or {}
    tokens = usage.get("total_tokens")
    if tokens is None:
        tokens = len(text) // 4
    return text, tokens


async def call(cfg: dict, messages: list, max_tokens: int = 2048) -> dict:
    """
    POST to an OpenAI-compatible endpoint.
    Returns dict with keys: text, tokens_used, error (or None).
    """
    payload = json.dumps({
        "model": cfg["model_id"],
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        # Cloudflare WAFs intermittently 403 the default Python-urllib UA
        # (groq, error 1010, seen 2026-07-30); a real UA passes.
        "User-Agent": "growing-spine/1.0",
        "Authorization": f"Bearer {cfg['api_key']}",
    }

    req = urllib.request.Request(cfg["endpoint"], data=payload, headers=headers)
    try:
        loop = asyncio.get_event_loop()
        def _do():
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        data = await loop.run_in_executor(None, _do)
        text, tokens = _extract_text_tokens(data)
        if not text:
            return {"text": "", "tokens_used": tokens,
                    "error": "empty completion (content and reasoning both null)"}
        return {"text": text, "tokens_used": tokens, "error": None}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"text": "", "tokens_used": 0, "error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"text": "", "tokens_used": 0, "error": str(e)}
