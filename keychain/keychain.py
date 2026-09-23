"""keychain.py — one function: give it a prompt, get a response."""
import asyncio
import time, os, re, yaml
from . import quota_state as qs
from . import provider as prov


def _load_config() -> list:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(cfg_path) as f:
        return yaml.safe_load(f)["providers"]


# A saturated upstream usually clears in minutes; 10 min balances "retry
# the smart rung soon" against burning RPM on probes. Each failed upward
# probe refreshes exhausted_at, self-throttling to one attempt per window.
# A reply that hit the token ceiling is NOT a usable answer: the loop finds
# no closed bash block and skips the cycle. Before 2026-09-16 it was still
# recorded as a plain success and returned, so the cycle was simply lost
# and the rungs below were never reached -- the design gap section 8 has
# named since 2026-08-18. Measured cost over 265 h: 405 truncations, and
# gemini_flash alone truncated 41.3% of everything it served.
#
# So truncation now ESCALATES: the same prompt goes to the next rung. Two
# properties make this cheap. It pays only on the failures (~12% of
# cycles) rather than taxing every call the way a bigger ceiling would,
# and google_gemma has enormous headroom -- 2,619 calls used of 14,400/day
# -- so absorbing the escalations is nearly free.
#
# DECLARED, never learned, and bounded: throughput is the binding problem
# right now (12-13 thinks/h against a 15/h floor), so at most this many
# extra rungs are tried before the longest truncated reply is returned
# anyway. Degrading to the pre-2026-09-16 behaviour always beats raising.
TRUNCATION_ESCALATE_MAX = 2

UPWARD_REPROBE_SECS = 600

# Distinct unrecognised provider errors already announced in this process. Bounds
# the log to one line per novel failure mode rather than one per cycle. A brain
# restart re-announces, which is correct: a new process has not reported it yet.
_REPORTED_UNKNOWN = set()


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


def _diag(err, width=160):
    """One line of an error, for a human reading the log.

    Collapses whitespace so a pretty-printed JSON body does not spread one
    failure over thirty lines, and says when it cut. A diagnostic that hides
    its own truncation is the keyhole scar wearing a new hat (CLAUDE.md
    section 5); a marker always reports the total NOT shown.
    """
    flat = " ".join(str(err).split())
    if len(flat) <= width:
        return flat
    return "%s...[+%d chars]" % (flat[:width], len(flat) - width)


_HTTP_STATUS_RE = re.compile(r"^\s*HTTP\s+(\d{3})\b")


def http_status(err: str):
    """The status code a provider actually returned, or None.

    prov.call formats every HTTP failure as "HTTP {code}: {body}", so the
    status is the FIRST thing in the string and is the only trustworthy
    place to read a number from. Everything after it is provider prose that
    we do not control.
    """
    m = _HTTP_STATUS_RE.match(err or "")
    return m.group(1) if m else None


def classify_error(err: str) -> str:
    """Sort a provider error string into an action class.
    too_large / quota -> mark exhausted, next provider
    retryable         -> backoff-retry same provider (per-minute, 5xx, traffic)
    flaky             -> next provider immediately (degenerate free-pool
                         responses: empty completions, timeouts, conn resets --
                         2026-07-17: these used to hard-raise and abort the
                         WHOLE chain, losing the cycle even with open windows)
    unknown           -> next provider, announced once, account NOT walled.
                         The DEFAULT. Never abort a chain with open rungs.
    """
    err_l = err.lower()
    # THE STATUS IS READ ONCE, FROM THE FRONT, AND NO DIGIT RULE LOOKS
    # ANYWHERE ELSE. Until 2026-09-23 every numeric branch below was a bare
    # substring test against the WHOLE error -- `"404" in err` -- and
    # Cloudflare puts a UUID in every error body. Section 8 predicted that
    # hazard on 2026-08-27 at roughly 0.7% per error and named a trigger; on
    # 2026-09-23 the new GONE diagnostic caught it happening TWICE in 17 h,
    # both times on an HTTP 429 whose trailing UUID contained 404, both times
    # reporting a live model as permanently withdrawn. Cloudflare errored ~498
    # times in that window, so ~3 hits was the prediction and 2 was the count.
    # Under CLAUDE.md section 6 a defunct model is retired the moment it is
    # detected and without asking, which is what makes a false GONE expensive.
    #
    # Invariant: A NUMBER IS EVIDENCE ONLY WHERE THE PROTOCOL PUT IT. Digits
    # are matched against the status code; words are matched against the body.
    # An error with no parseable status fires no numeric rule at all -- those
    # errors (RemoteDisconnected, urlopen failures) are textual anyway, and
    # guessing a status out of their prose is the same mistake one level down.
    code = http_status(err)
    if (code == "413" or "request too large" in err_l or "request_too_large" in err_l
            or "too large for model" in err_l or "context length" in err_l
            or "maximum context" in err_l or "reduce the length" in err_l):
        return "too_large"
    if (("rate_limit" in err_l or "too_many_requests" in err_l)
            and ("per minute" in err_l or "per-minute" in err_l
                 or "per_minute" in err_l or "rpm" in err_l)):
        return "retryable"
    if (code == "404" or "not found" in err_l or "no endpoints" in err_l
            or "model_not_found" in err_l
            # Cloudflare Workers AI answers a model our PLAN cannot reach with
            # HTTP 403 code 5035: "AiError: Model @cf/... is not available on
            # the Workers Free plan. Upgrade to access this model". Measured
            # 2026-08-26 on four catalogued models (kimi-k2.6, glm-5.2,
            # glm-5.3-flash, deepseek-v4-pro) -- the model-search API lists them
            # and the free plan refuses them. That is precisely `gone`: the id
            # has left OUR shelf, the account is fine, and a single-model rung
            # must be walled WITH a log line saying why (the 2026-08-17 silent
            # groq retirement). It matched nothing before this, so it reached
            # the fail-open default and retired mutely.
            or "not available on the workers free plan" in err_l
            # 5035 is a BODY code, not a status: Cloudflare returns it under
            # HTTP 403. Pinned to that status so a UUID carrying those four
            # digits cannot retire a rung by coincidence either.
            or (code == "403" and "5035" in err)):
        # The model left the shelf (the 2026-07-19 openrouter purge, ling on
        # 2026-08-07). This is NOT the account being out of budget: a rung with
        # other models declared should fall to the next one. Returned as its own
        # class since 2026-08-10 -- it used to be folded into "quota", which
        # walled the whole account because one model id had gone stale. Callers
        # must still never hard-raise on it.
        return "gone"
    if ("quota" in err_l or "rate_limit_exceeded" in err_l or "exceeded" in err_l
            or "billing" in err_l or code == "429"
            # 402 Payment Required is how a spent free ALLOWANCE reads on a
            # provider whose budget is monthly rather than daily. Mistral answers
            # HTTP 402 with {"detail":"Check your subscription on
            # admin.mistral.ai/subscription"} -- no "quota", no "billing", no
            # "exceeded" anywhere in it, so before 2026-08-19 it fell through to
            # the default and HARD-RAISED, killing 651 cycles in one day that had
            # google_gemma and gemini_flash sitting open. The account is out of
            # budget; that is quota, and it must wall the rung so the ladder falls
            # through instead of dying.
            or code == "402" or "payment required" in err_l
            or "subscription" in err_l or "insufficient" in err_l):
        return "quota"
    if (code in ("500", "502", "503", "504")
            # Cloudflare's own edge codes, 520-527. A provider fronted by
            # Cloudflare answers an origin failure with one of these rather than
            # a bare 502, and none of them contains any string this function
            # matched: on 2026-08-26 00:08 mistral returned
            # "HTTP 520: error code: 520" and it reached the `unknown` path,
            # which routed around it correctly but cost the cycle its chain.
            # Invariant: an edge or origin transport failure is transient and
            # never evidence about the account, so it retries and never walls.
            or code in ("520", "521", "522", "523",
                        "524", "525", "526", "527")
            or "high traffic" in err_l):
        return "retryable"
    if ("empty completion" in err_l or "timed out" in err_l or "timeout" in err_l
            or "connection refused" in err_l or "connection reset" in err_l
            or "temporary failure" in err_l
            # 499 is "client closed request" -- a cancelled or timed-out call,
            # transport-level and transient. Surfaced 2026-08-25 by the `unknown`
            # path doing its job: google_gemma returned HTTP 499 twice, nothing
            # recognised it, and the raise carried the text so it could be
            # classified. Same family as "timed out", so the same class: route to
            # the next rung, never wall the account for a cancelled request.
            or code == "499" or "client closed request" in err_l
            or "request was cancelled" in err_l
            # The server hung up mid-request: http.client raises
            # RemoteDisconnected("Remote end closed connection without
            # response"), which carries no status code at all. Surfaced
            # 2026-09-19 by the `unknown` path doing its job for the FOURTH
            # time -- google_gemma dropped one connection, nothing recognised
            # the string, and the fail-open default routed around it and
            # carried the text so it could be named. Transport-level and
            # transient, so the same class as "timed out": next rung, and
            # never wall an account because a socket closed.
            or "remote end closed connection" in err_l
            or "remotedisconnected" in err_l):
        return "flaky"
    # UNRECOGNISED, and that is a class of its own rather than a reason to stop.
    #
    # This default used to be "hard", which raises and aborts the WHOLE chain. The
    # project learned that lesson once already -- on 2026-07-17 degenerate
    # free-pool responses were hard-raising and losing cycles "even with open
    # windows", and the fix was to enumerate them as flaky. Enumerating strings
    # leaves the fail-CLOSED default in place, so it recurred on 2026-08-19 with a
    # provider error nobody had seen yet: one rung 402 killed cognition that four
    # other rungs could have served.
    #
    # A ladder whose entire purpose is graceful degradation must not treat "I do
    # not recognise this" as "stop everything". Unknown errors move to the next
    # rung, WITHOUT walling the account -- we do not know it is out of budget --
    # and say so loudly exactly once per distinct error, because a graceful
    # degradation that logs nothing is a silent outage. If every rung fails and an
    # unknown was among them, complete() raises carrying that text, so the reason
    # still reaches the log instead of a generic "all providers exhausted".
    return "unknown"


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
        # How many rungs truncated before the reply that was
        # finally returned. The loop writes this into served_by,
        # which makes it the instrument for the question a bigger
        # think ceiling would be answering: escalated=N with
        # finish=stop means a later rung FINISHED what this one
        # could not, and escalated=N with finish=length means
        # even escalation did not help.
        self.last_escalations = 0

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
        unknown_err = ""
        truncated_tries = []  # (rung, model, text)
        self.last_escalations = 0
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
            for _mi, mid in enumerate(variants):
                for attempt in range(3):
                    result = await prov.call(cfg, messages,
                                             max_tokens=max_tokens, model=mid)

                    if result["error"] is None:
                        if cfg["key"] in exhausted_keys:
                            print(f"[keychain] {cfg['key']} window REOPENED "
                                  f"(probe of a believed-exhausted provider "
                                  f"succeeded)")
                        # The CALL succeeded and the account is healthy, so
                        # record success before deciding whether the ANSWER
                        # is usable. Walling a rung that truncates would
                        # remove a rung that serves short replies perfectly.
                        qs.record_success(self.state, cfg["key"])
                        if (result.get("truncated")
                                and len(truncated_tries)
                                < TRUNCATION_ESCALATE_MAX):
                            truncated_tries.append(
                                (cfg["key"], mid, result["text"] or ""))
                            print(f"[keychain] {cfg['key']}/{mid} hit the "
                                  f"{max_tokens}-token ceiling -- "
                                  f"ESCALATING to the next rung "
                                  f"({len(truncated_tries)}/"
                                  f"{TRUNCATION_ESCALATE_MAX})")
                            stop_rung = True
                            break  # same prompt, next PROVIDER
                        self.last_escalations = len(truncated_tries)
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
                        return result["text"]

                    err = str(result["error"])
                    kind = classify_error(err)

                    if kind == "gone":
                        # This model id left the shelf; the account is fine.
                        #
                        # ALWAYS logged. Until 2026-08-17 this printed only when
                        # the rung had a sibling model to fall to, so a
                        # SINGLE-model rung was retired in total silence: on that
                        # day Groq withdrew llama-3.3-70b-versatile, the `groq`
                        # rung began 404ing, the ladder walled it correctly,
                        # cognition never faltered -- and nothing anywhere said
                        # why. FLATLINE would have reported `groq(12h)` half a day
                        # later with no cause attached. A graceful degradation
                        # that logs nothing is a silent outage; the whole point of
                        # separating `gone` from `quota` was to know WHICH it was.
                        gone_count += 1
                        tail = ("falling to the next model"
                                if _mi + 1 < len(variants)
                                else "no models left on this rung -- walling it")
                        # QUOTE THE ERROR, never a status we did not read.
                        # This line said "(404 from the provider)" as a LITERAL
                        # while classify_error returns "gone" for 404, "not
                        # found", "no endpoints", "model_not_found", the
                        # Workers-free-plan 403, and any body that merely
                        # CONTAINS the characters 404. On 2026-09-22 it
                        # reported groq_oss120 and cloudflare as GONE six
                        # times; both models answered a live probe the next
                        # day. Under CLAUDE.md section 6 a defunct model is
                        # retired the moment it is detected and without asking
                        # Tue -- so a false retirement verdict is a line that
                        # gets ACTED on, and two live rungs were one reading
                        # away from being disabled.
                        print(f"[keychain] {cfg['key']}: model {mid} reported "
                              f"GONE by classify_error -- {tail}. "
                              f"Provider said: {_diag(err)}")
                        break  # next MODEL, same rung

                    if kind in ("too_large", "quota"):
                        # A WALL MUST NAME ITS CAUSE. `gone` has printed since
                        # 2026-08-17 and `flaky` prints on every hop, but the
                        # branch that actually walls an account printed
                        # NOTHING -- so the commonest degradation in the
                        # system was the one no log could explain. On
                        # 2026-09-22 google_gemma walled 235 times in 32 h
                        # against a configured 14,400/day and no instrument
                        # anywhere could say why; it took a live probe to find
                        # that the binding limit is 16,000 INPUT TOKENS PER
                        # MINUTE, a different dimension from the one config
                        # names. That question should have been answerable
                        # from the log.
                        qs.record_exhaustion(self.state, cfg["key"])
                        stop_rung = True
                        print(f"[keychain] {cfg['key']} WALLED as {kind} "
                              f"-- {_diag(err)}")
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

                    # Unrecognised. Route around it; never lose a cycle that
                    # still has open rungs. Announced once per distinct error so a
                    # new failure mode gets classified instead of accumulating in
                    # silence -- once, not per cycle, or it becomes a nag.
                    had_transient = True
                    unknown_err = f"{cfg['key']}: {err}"
                    sig = cfg["key"] + "|" + err[:120]
                    if sig not in _REPORTED_UNKNOWN:
                        _REPORTED_UNKNOWN.add(sig)
                        print(f"[keychain] {cfg['key']} returned an error this "
                              f"classifier does not recognise -- routing to the "
                              f"next rung and NOT walling the account. Classify "
                              f"it: {err[:200]}")
                    stop_rung = True
                    break  # next provider

                if stop_rung:
                    break
            if not stop_rung and gone_count == len(variants):
                # EVERY declared model has left the shelf: wall the rung so we
                # stop paying a round trip per dead id every cycle. Preserves the
                # 2026-07-19 purge behaviour, which must never hard-raise. Counted
                # rather than inferred from the last model's verdict -- a gone id
                # followed by a flaky one would otherwise wall a healthy account.
                qs.record_exhaustion(self.state, cfg["key"])

        if truncated_tries:
            # Every rung we were willing to try truncated. Return the
            # LONGEST reply rather than losing the cycle: that is exactly
            # the pre-2026-09-16 behaviour, and degrading to it beats
            # raising, which would abort a cycle that at least has text.
            key, mid, text = max(truncated_tries, key=lambda t: len(t[2]))
            self.last_used, self.last_model = key, mid
            self.last_finish_reason, self.last_truncated = "length", True
            self.last_escalations = len(truncated_tries)
            print(f"[keychain] all {len(truncated_tries)} attempted rungs "
                  f"truncated -- returning the longest ({len(text)} chars) "
                  f"from {key}/{mid}")
            return text
        if unknown_err:
            # Every rung failed AND one failed in a way we cannot name. Carry that
            # text: "all providers exhausted" would throw away the only copy of
            # the reason, which is how a silent outage gets built.
            raise RuntimeError(
                "All providers failed; last unrecognised error -- " + unknown_err)
        if had_transient:
            raise RuntimeError("All providers temporarily unavailable.")
        raise RuntimeError("All providers exhausted.")

    def any_available(self) -> bool:
        enabled = [p for p in self.providers if p.get("enabled", True)]
        return any(not qs.is_exhausted(self.state, p["key"]) for p in enabled)
