"""provider.py — single OpenAI-compatible provider call."""
import asyncio, json
import urllib.request, urllib.error


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
        "Authorization": f"Bearer {cfg['api_key']}",
    }

    req = urllib.request.Request(cfg["endpoint"], data=payload, headers=headers)
    try:
        loop = asyncio.get_event_loop()
        def _do():
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        data = await loop.run_in_executor(None, _do)
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", len(text) // 4)
        return {"text": text, "tokens_used": tokens, "error": None}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"text": "", "tokens_used": 0, "error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"text": "", "tokens_used": 0, "error": str(e)}
