"""provider.py — single OpenAI-compatible provider call."""
import asyncio, json, re
import urllib.request, urllib.error


def _extract_text_tokens(data: dict):
    """None-safe extraction. Reasoning models (gpt-oss via OpenRouter) can
    return content=null -- and even reasoning=null -- e.g. when
    finish_reason=length lands mid-reasoning; usage can be null too.
    dict.get's default is evaluated EAGERLY, so len(text)//4 as a .get
    default raised len(None) and killed the cycle (2026-07-17 02:00).

    Returns (text, tokens, finish_reason, reasoning_only).

    2026-08-05: finish_reason used to be mentioned only in this docstring and
    read nowhere, so a reply cut off at max_tokens was indistinguishable from a
    complete one and EVERY fail-open parser downstream turned truncation into
    its most permissive verdict in silence. Measured cost: of the last 60
    exec_skip cycles, 21 ended on an unclosed ``` fence -- commands were
    proposed and destroyed by the budget, and the journal said the model
    "proposed no commands".

    reasoning_only marks the other half: content empty while reasoning is not.
    That is deliberation returned AS the answer, which position-anchored parsers
    reject and scanning parsers can mistake for a verdict. It is not an answer,
    so the caller treats it as a degenerate response rather than as text."""
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    finish_reason = choice.get("finish_reason") or ""
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning") or ""
    text = content or reasoning
    reasoning_only = bool(reasoning) and not content
    usage = data.get("usage") or {}
    tokens = usage.get("total_tokens")
    if tokens is None:
        tokens = len(text) // 4
    return text, tokens, finish_reason, reasoning_only


def model_ids(cfg: dict) -> list:
    """The model ids this rung may use, in preference order. CANONICAL.

    A rung is one upstream ACCOUNT, not one model. OpenRouter bills its free tier
    at 50 requests/day against the account, shared by every `:free` model, so
    three config entries each declaring `limit: 50` described a budget that does
    not exist. Measured 2026-08-10 from `served_by`: `openrouter_super` took all
    50 every day (51/51/50/50) while `north` and `nemotron` starved -- and both
    were then reported dead for 185h by FLATLINE and the dashboard, which is a
    false alarm about a healthy reserve rather than a fault.

    `model_id` therefore accepts a list. A plain string still works and is still
    the right shape for a single-model account like Groq or Cerebras.
    """
    m = cfg.get("model_id")
    return list(m) if isinstance(m, (list, tuple)) else [m]


# How much of a provider's error body to keep. Chosen by MEASUREMENT, not
# taste: the real Google 429 body is 1,382 chars and puts its machine-readable
# half at the END -- `limit: 16000` at offset 400, `RESOURCE_EXHAUSTED` at 482,
# `quotaMetric` at 903, `quotaValue` at 1212 and `retryDelay` at 1342. The old
# cap of 200 kept NONE of them, so for the life of the project every provider
# told us exactly when to come back and we threw the sentence away and guessed.
# Widening only became safe on 2026-09-23, once classify_error stopped matching
# bare digits against body text (a Cloudflare UUID containing 404 was retiring
# live models); until then a longer body meant more chances to misclassify.
PROVIDER_ERROR_BODY_CHARS = 1500

_RETRY_PATTERNS = (
    # Google: "retryDelay": "41.111907086s"  (and the prose form beside it)
    re.compile(r'"retryDelay"\s*:\s*"?(\d+(?:\.\d+)?)s'),
    re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.I),
    re.compile(r"try again in (\d+(?:\.\d+)?)\s*s", re.I),
)


def retry_after_seconds(headers=None, body=""):
    """When the provider TELLS us to come back, in seconds, or None.

    Read the header first -- Retry-After is the protocol's own field and needs
    no parsing of prose -- then the body, because Google puts the number only
    in the JSON. Never invented: if nothing says when, this returns None and
    the caller keeps its own conservative default.
    """
    try:
        if headers is not None:
            raw = headers.get("Retry-After")
            if raw and str(raw).strip().isdigit():
                return float(str(raw).strip())
    except Exception:
        pass
    for pat in _RETRY_PATTERNS:
        m = pat.search(body or "")
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


async def call(cfg: dict, messages: list, max_tokens: int = 2048,
               model: str = None) -> dict:
    """
    POST to an OpenAI-compatible endpoint.
    Returns dict with keys: text, tokens_used, finish_reason, truncated,
    error (or None).

    `model` overrides the rung's default; the keychain passes it when walking a
    multi-model rung. Omitted, the first declared model is used.
    """
    payload = json.dumps({
        "model": model or model_ids(cfg)[0],
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
        text, tokens, finish, reasoning_only = _extract_text_tokens(data)
        truncated = finish == "length"
        base = {"tokens_used": tokens, "finish_reason": finish,
                "truncated": truncated}
        if not text:
            return dict(base, text="",
                        error="empty completion (content and reasoning both null)")
        if reasoning_only:
            # Deliberation is not an answer. "empty completion" keeps it in the
            # existing flaky class, so the keychain hops to the next window
            # instead of handing musings to a parser that will scan them.
            return dict(base, text="",
                        error="empty completion (reasoning-only, answer truncated)")
        return dict(base, text=text, error=None)
    except urllib.error.HTTPError as e:
        # Reading the error BODY is itself a network operation and can
        # fail. Until 2026-09-15 this line was bare, and an exception
        # raised INSIDE an except clause is never offered to the sibling
        # `except Exception` below it -- so a socket timeout here escaped
        # prov.call entirely, escaped the keychain (no classify_error, no
        # record_exhaustion, no fall-through to the next rung) and landed
        # in the loop's generic handler as "UNEXPECTED: The read
        # operation timed out" plus a 30 s sleep. Four cycles lost that
        # way on 09-12 and 09-13, and the creature then read our
        # infrastructure error out of its own activity log and blamed its
        # own tool for it ("crossclusterdigestscheduler tool failed
        # during canonicalization with an UNEXPECTED...", 09-12 16:52).
        #
        # Invariant: PROV.CALL NEVER RAISES. Every failure leaves by the
        # return path carrying text the classifier can read, because the
        # ladder's whole fail-open design (c1b93a5) depends on the error
        # reaching classify_error at all. The STATUS CODE matters more
        # than the body and is available even when the body is not, so it
        # is always reported.
        try:
            body = e.read().decode(errors="replace")
        except Exception as body_err:
            body = "<error body unreadable: %s>" % body_err
        return {"text": "", "tokens_used": 0, "finish_reason": "", "truncated": False,
                "retry_after_s": retry_after_seconds(getattr(e, "headers", None), body),
                "error": f"HTTP {e.code}: {body[:PROVIDER_ERROR_BODY_CHARS]}"}
    except Exception as e:
        return {"text": "", "tokens_used": 0, "finish_reason": "", "truncated": False,
                "error": str(e)}
