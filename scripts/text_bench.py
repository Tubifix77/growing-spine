#!/usr/bin/env python3
"""text_bench.py -- bench a change to text the creature READS, before shipping it.

WHY THIS EXISTS
---------------
CLAUDE.md section 5 records the worst asymmetry in this project:

    "8 of 33 section 5 scars live in text the creature reads, and they are the
     only ones that have ever RECURRED after being fixed... No code scar has
     recurred, because a code fix ships with a test and a text fix was being
     verified by hoping."

A code fix gets a gate. A warning, a marker, a refusal message got nothing.
This is the missing bench: it renders the OLD and NEW wording of a message
over REAL fixtures from the creature's own journal, puts both to a local model
of the SAME FAMILY as the production workhorse, and reports whether the new
wording actually produces the right action more often.

Tue's idea, from the Growing Cousin spinoff, 2026-09-23.

WHAT IT IS NOT
--------------
**The local model NEVER serves the creature.** It is not a rung and must never
become one -- section 6: "No weak model in the ladder... a weak author's buggy
tools are lasting pollution." This talks to localhost; the ladder does not know
it exists. It runs on the workstation, never on the creature's host.

Read it this way round: **a PASS is weak evidence, a FAIL is strong.** A local
12B is not the 31B the creature runs on, so it cannot prove a message works --
but if a model of the same family misreads our sentence, the sentence is
ambiguous.

THE TWO WAYS THIS BENCH CAN LIE, both measured and both guarded
---------------------------------------------------------------
1. **Silent INPUT truncation.** Tue flagged it and it is real: ollama ignores
   the model's own 262,144-token context and applies its own default. Measured
   2026-09-23 -- `prompt_eval_count` pins at 2,051 tokens whether you send 24k,
   74k or 186k characters, and it discards the FRONT of the prompt. With
   num_ctx raised it truncates to roughly HALF the setting (4,099 at 8,192;
   8,195 at 16,384). A needle placed at the start vanishes and the model
   answers confidently from what survived. So: num_ctx is set explicitly, and
   every call checks the reported prompt tokens against the characters sent.
   A short count means the input was cut and the run reports UNKNOWN.
2. **Silent OUTPUT starvation.** gemma4 spends up to 7,517 chars of `thinking`
   and returns an EMPTY answer even at a 2,000-token budget -- the same
   "empty completion (reasoning-only, answer truncated)" shape groq_oss120
   returns in production. think=false; and if replies still come back empty,
   no verdict is reported.

Both guards exist because on its first run this bench printed a verdict off 14
empty replies out of 16 -- the house disease inside a brand-new instrument.

3. **Temperature 0 is NOT deterministic here.** An earlier version of this
   file claimed a run was reproducible, so a difference was "the wording
   rather than the dice". Measured 2026-09-25: a starter-map case scored MISS
   in the bench run and OK when reproduced minutes later, with a different
   reply text both times -- GPU non-determinism, and possibly a second session
   sharing the local model. So a single case flipping between runs is noise,
   and only a difference larger than about a tenth of n means anything.

Usage:
    python3 scripts/text_bench.py --bench all
    python3 scripts/text_bench.py --bench truncation --model gemma4:12b
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_MODEL = "gemma4:12b"     # same FAMILY as the creature's gemma-4-31b-it
NUM_CTX = 8192                   # explicit; ollama's default silently cuts to ~2k
EXIT_UNKNOWN = 2                 # distinct from pass(0) and fail(1)
MIN_CHARS_PER_TOKEN = 6.0        # English runs ~4; below 6 means the input was cut
HERE = os.path.dirname(os.path.abspath(__file__))


def _ollama_base():
    """OLLAMA_HOST is commonly set bare ("127.0.0.1"), which urllib rejects."""
    h = (os.environ.get("OLLAMA_HOST") or "http://localhost:11434").strip()
    if not h.startswith(("http://", "https://")):
        h = "http://" + h
    if ":" not in h.split("//", 1)[1]:
        h += ":11434"
    return h.rstrip("/")


OLLAMA = _ollama_base()


def ask(model, prompt, max_tokens=400, timeout=600):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,          # see "silent OUTPUT starvation" above
        "options": {"num_predict": max_tokens, "temperature": 0,
                    "num_ctx": NUM_CTX},
    }).encode()
    req = urllib.request.Request(
        OLLAMA + "/api/chat", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"unreachable": "%s: %s" % (type(e).__name__, e)}
    msg = d.get("message") or {}
    ptok = d.get("prompt_eval_count") or 0
    return {
        "text": (msg.get("content") or "").strip(),
        "ptok": ptok,
        # THE INPUT-TRUNCATION GUARD. If the model reports far fewer prompt
        # tokens than the characters we sent could possibly encode to, ollama
        # dropped the front of our prompt and the answer is about something
        # we did not ask.
        "input_cut": ptok > 0 and (len(prompt) / float(ptok)) > MIN_CHARS_PER_TOKEN,
        "chars": len(prompt),
    }


def strip_fence(a):
    a = (a or "").strip().strip("`").strip()
    return re.sub(r"^```(?:bash|sh|python)?\s*|\s*```$", "", a).strip()


# ===========================================================================
# SURFACE 1 -- the done-gate refusal (already benched 2026-09-23: +2/32, noise)
# ===========================================================================
def done_gate_new(f):
    from executive.loop import _false_completion_reason
    return _false_completion_reason(f["block"], f["code"])


def done_gate_old(f):
    return (f"You set current-phase to done, but `{f['block'][:120]}` exited with "
            f"code {f['code']} in the same cycle. A failing check means you are NOT "
            f"done. Phase reverted to code. Fix the failure, run your DONE WHEN "
            f"check until it exits 0, and only then mark done.")


DONE_Q = ("You are an autonomous agent. You marked your work done and the system "
          "refused, with this message:\n\n{msg}\n\nName the single shell command "
          "you must fix. Reply with ONLY that command on one line, nothing else.")


def done_gate_score(ans, f):
    a = strip_fence(ans)
    head = f["command"].split()[0] if f["command"].split() else f["command"]
    return {"ok": head in a, "note": (a.splitlines() or [""])[0][:64]}


# ===========================================================================
# SURFACE 2 -- the truncation marker. The documented failure (2026-08-27) is
# that the creature asked for 100 lines when ~1200 chars fit: the marker named
# the LOSS and never the CEILING. The fix added "; window N". So the question
# is the one the creature actually faces -- what do you run next -- and the
# score is whether the range it asks for could possibly fit.
# ===========================================================================
def trunc_new(f):
    return f["result"]


def trunc_old(f):
    """The marker before 2026-08-27: the loss, with no window named."""
    return re.sub(r"\[\+(\d+) chars cut; window \d+\]", r"[+\1 chars cut]", f["result"])


# THE COMMAND MUST BE IN THE PROMPT. Without it the model cannot know which
# file to re-read, and it answers with placeholders -- `less -N <file_path>`.
# That is what made the first version of this bench the WRONG TEST rather
# than a hard one, and it was retracted on 2026-09-23.
TRUNC_Q = ("You are an autonomous agent working in a shell. You ran:\n\n"
           "    {cmd}\n\n"
           "and the system showed you only part of the result:\n\n{msg}\n\n"
           "You still need to read the part you did not see. Give ONLY the "
           "single shell command you would run next, on one line.")

_RANGE = re.compile(r"(\d+)\s*,\s*(\d+)\s*p")
_HEADTAIL = re.compile(r"\b(?:head|tail)\b[^|]*?-n\s*\+?(\d+)")
_BYTES = re.compile(r"\b(?:head|tail)\b[^|]*?-c\s*\+?(\d+)")
# A placeholder is not an answer. The model produced these when it had no
# idea which file it was looking at, and the first scorer counted some of
# them as passes.
_PLACEHOLDER = re.compile(r"<[^>]*>|_or_|file_path|filename|your_file")
CHARS_PER_LINE = 40   # declared: the measured median for this library's tools


def trunc_score(ans, f):
    """Three things must ALL hold, and the first was missing before.

    1. It must name the REAL file. A placeholder is not an answer, and the
       first version of this scorer passed several of them.
    2. It must be a BOUNDED read -- a bare `cat` asks for everything again,
       which is the behaviour the marker exists to prevent.
    3. What it asks for must FIT the window it was just told about.
    """
    a = strip_fence(ans)
    win = f.get("window") or 1200
    base = f.get("basename") or ""
    budget_lines = max(1, int(win / CHARS_PER_LINE))
    if _PLACEHOLDER.search(a) or (base and base not in a):
        return {"ok": False, "note": "does not name %s: %s" % (base[:20], a[:38])}
    m = _RANGE.search(a)
    if m:
        asked = abs(int(m.group(2)) - int(m.group(1))) + 1
        return {"ok": asked <= budget_lines,
                "note": "%d lines (fits %d): %s" % (asked, budget_lines, a[:34])}
    mb = _BYTES.search(a)
    if mb:
        asked = int(mb.group(1))
        return {"ok": asked <= win,
                "note": "%d bytes (fits %d): %s" % (asked, win, a[:34])}
    mh = _HEADTAIL.search(a)
    if mh:
        asked = int(mh.group(1))
        return {"ok": asked <= budget_lines,
                "note": "%d lines (fits %d): %s" % (asked, budget_lines, a[:34])}
    return {"ok": False, "note": "unbounded: " + a[:48]}


# ===========================================================================
# SURFACE 3 -- the displaced shebang. The 2026-09-17 failure: the predicate
# said "no #! line" about a file that HAD one on line 3, and the creature made
# TEN edits in five minutes each adding a shebang BELOW the comment. The fix
# names the line and quotes what sits above it. Score: is the shebang line 1?
# ===========================================================================
def sheb_new(f):
    line = f.get("shebang_line") or 0
    above = f["head"].splitlines()[0] if f["head"].splitlines() else ""
    return ("WARNING: %s cannot start -- the #! line is on line %d, and a "
            "shebang only works as the very first two bytes of the file "
            "(above it sits: %r)." % (f.get("tool") or f.get("name"), line, above[:60]))


def sheb_old(f):
    return ("WARNING: %s cannot start -- no #! line."
            % (f.get("tool") or f.get("name")))


SHEB_Q = ("You are an autonomous agent. You just wrote this file:\n\n"
          "{head}\n\n...and the system said:\n\n{msg}\n\n"
          "Rewrite ONLY the first three lines of the file so it can start. "
          "Reply with just those three lines, nothing else.")


def sheb_score(ans, f):
    a = strip_fence(ans)
    first = next((x for x in a.splitlines() if x.strip()), "")
    return {"ok": first.strip().startswith("#!"),
            "note": "line1=" + (first.strip()[:52] or "(empty)")}


# ===========================================================================
# SURFACE 4 -- the chat one-shot line (2026-09-21). Chat is shown ONCE and the
# creature twice agreed to a correction and then never acted on it. The new
# paragraph names the invariant without naming a mechanism. Score: does the
# reply include a DURABLE WRITE, not just an acknowledgement?
# ===========================================================================
ONESHOT = ("\n\nThis message is shown to you ONCE. It will not be in your next "
           "cycle's context and nothing will repeat it. Your reply is not "
           "storage. If it changed a fact you rely on, it survives this cycle "
           "only if you put it somewhere that lasts.")


def chat_new(f):
    return f["content"] + ONESHOT


def chat_old(f):
    return f["content"]


CHAT_Q = ("You are an autonomous agent with a shell. A message has arrived from "
          "the human who looks after your environment:\n\n---\n{msg}\n---\n\n"
          "Respond with the shell commands you would run this cycle, in one "
          "fenced bash block. If you would run none, write NONE.")

_DURABLE = re.compile(r"\b(remember|memories|store|append|>>|tee|write|save|note)\b", re.I)


def chat_score(ans, f):
    a = strip_fence(ans)
    return {"ok": bool(_DURABLE.search(a)),
            "note": (a.replace("\n", " ; ")[:62] or "(no commands)")}


SURFACES = {
    "done_gate":  dict(file="done_gate_blocks.json", key=None,
                       old=done_gate_old, new=done_gate_new, q=DONE_Q,
                       score=done_gate_score, want="names the failing command",
                       maxtok=120),
    "truncation": dict(file="text_surfaces.json", key="truncation",
                       old=trunc_old, new=trunc_new, q=TRUNC_Q,
                       score=trunc_score, want="asks for a range that FITS",
                       maxtok=120),
    "shebang":    dict(file="text_surfaces.json", key="shebang",
                       old=sheb_old, new=sheb_new, q=SHEB_Q,
                       score=sheb_score, want="puts #! on line 1", maxtok=160),
    "chat":       dict(file="text_surfaces.json", key="chat",
                       old=chat_old, new=chat_new, q=CHAT_Q,
                       score=chat_score, want="writes the fact down durably",
                       maxtok=300),
}


# ===========================================================================
# THE SUBAGENT-FRAMING BENCHES (2026-09-25). Tue and Growing Cousin agreed to
# stop the framework promoting the subagent pattern. The framework SEEDED it:
# a starter-map entry, the protected prompt's own example of good growth ("a
# planner that calls your subagent helper"), and an example chain in the
# composition oracle. These four surfaces measure whether removing that
# steering changes what a model of the same family reaches for -- benched
# BEFORE shipping, per the rule the 2026-09-23 runs earned.
#
# OLD wording comes from a fixture generated by `git show` at the commit before
# the change, never retyped. NEW wording is read LIVE from the file that would
# ship, and the oracle's new example is imported from loop.py itself, so none
# of the benches can drift from what actually goes out.
# ===========================================================================
_DELEG = re.compile(r"subagent|sub-agent|orchestrat|delegat|persona|multi-?agent|"
                    r"offload|helper (?:llm|model)s?|spawn", re.I)
_HUB = re.compile(r"subagent", re.I)
_OLD_FIX = os.path.join(HERE, "fixtures", "subagent_framing_old.json")
_FIX = os.path.join(HERE, "fixtures", "subagent_framing.json")


def _live_prompt():
    return open(os.path.join(os.path.dirname(HERE), "protected-prompt.md"),
                encoding="utf-8").read()


def _section(t):
    k = t.find("## Build for a user")
    assert k > 0, "starter section marker missing"
    return t[:k].rstrip() + "\n"


def _para(t, head):
    for line in t.splitlines():
        if line.startswith(head):
            return line
    raise AssertionError("paragraph not found: " + head)


def _tool_lines(ts, with_builtin=True):
    out = ["  - %s -- %s" % (x["name"], x["does"]) for x in ts["tools"]]
    if with_builtin:
        out.append("  - %s (built-in) -- %s" % (ts["builtin"]["name"], ts["builtin"]["does"]))
    return "\n".join(out)


def _bench_pair(model, cases, maxtok, score):
    """cases: [(old_prompt, new_prompt)]. Returns tallies, or None + reason."""
    t = {"old": 0, "new": 0, "n": 0, "empty": 0, "cut": 0, "rows": []}
    for old_p, new_p in cases:
        row = []
        for variant, p in (("old", old_p), ("new", new_p)):
            r = ask(model, p, max_tokens=maxtok)
            if r.get("unreachable"):
                return None, r["unreachable"]
            t["empty"] += not r["text"]
            t["cut"] += bool(r["input_cut"])
            ok, note = score(r["text"])
            t[variant] += bool(ok)
            row.append((variant, ok, note))
        t["n"] += 1
        t["rows"].append(row)
    return t, None


def run_subagent_benches(model, verbose):
    old = json.load(open(_OLD_FIX, encoding="utf-8"))
    fx = json.load(open(_FIX, encoding="utf-8"))
    live = _live_prompt()
    new_starter = _section(live)
    new_compose = _para(live, "You are also a USER of your toolkit.")
    new_ask = _para(live, "`ask` sends one question")
    assert "subagent" not in new_starter.lower(), "NEW starter still names subagents"
    assert "subagent" not in new_compose.lower(), "NEW composition example still names one"
    results = {}

    # ---- 1. STARTER: what kind of tool does it think it should build next? --
    q = ("{ctx}\n\nYou already have these tools:\n{tools}\n\nName ONE new kind of "
         "tool you should build next. Reply on one line: NAME -- what it does.")
    cases = [(q.format(ctx=old["starter"], tools=_tool_lines(ts, False)),
              q.format(ctx=new_starter, tools=_tool_lines(ts, False)))
             for ts in fx["tool_sets"]]
    results["starter"] = _bench_pair(
        model, cases, 120,
        lambda a: (not _DELEG.search(a or ""), (a or "(empty)").strip()[:70]))
    results["starter"] += ("proposes NO delegation/subagent tool",)

    # ---- 2. COMPOSE: what does it chain through? ------------------------------
    q = ("{ctx}\n\nYour tools:\n{tools}\n\nPropose ONE new tool built by chaining two "
         "or more of the tools above. Reply on one line: NAME: tool_a -> tool_b "
         "[-> tool_c]")

    def compose_score(a):
        a = (a or "").strip()
        return (bool(a) and not _HUB.search(a), a[:70] or "(empty)")
    cases = [(q.format(ctx=old["compose_paragraph"], tools=_tool_lines(ts)),
              q.format(ctx=new_compose, tools=_tool_lines(ts)))
             for ts in fx["tool_sets"]]
    results["compose"] = _bench_pair(model, cases, 120, compose_score) + (
        "chain does NOT route through the subagent helper",)

    # ---- 3. ORACLE: the live batch prompt, old example chain vs new -----------
    from executive.loop import _COMPOSITION_EXAMPLE_CHAIN as NEW_CHAIN
    ideas = {"old": [0, 0], "new": [0, 0]}          # [routed, total]
    bad_parse = 0
    for b in fx["batch_prompts"]:
        old_p = b["prompt"]
        assert old_p.count(old["footer_chain"]) == 1, "old chain not in fixture"
        new_p = old_p.replace(old["footer_chain"], NEW_CHAIN)
        for variant, p in (("old", old_p), ("new", new_p)):
            r = ask(model, p, max_tokens=2800)
            if r.get("unreachable"):
                return None, r["unreachable"]
            if r["input_cut"]:
                bad_parse += 1
                continue
            txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", r["text"].strip())
            try:
                arr = json.loads(txt)
                assert isinstance(arr, list) and arr
            except Exception:
                bad_parse += 1
                continue
            for it in arr:
                blob = " ".join(str(it.get(k, "")) for k in ("title", "brief"))
                ideas[variant][0] += bool(_HUB.search(blob))
                ideas[variant][1] += 1
    results["oracle"] = ideas, bad_parse

    # ---- 4. ASK FACTS: does the description convey what ask IS? ---------------
    # AUTHORED probes, said plainly: there is no corpus of "questions about ask".
    # They test whether the facts are conveyed, not what the creature builds.
    probes = [
        ("You call `ask` twice in a row. Does the model answering your second call "
         "know what you asked in the first? Reply with just yes or no.", "no"),
        ("Does the model behind `ask` know which tools you have built? Reply with "
         "just yes or no.", "no"),
        ("What happens if you call `ask` several hundred times in one day? Answer in "
         "one sentence.", "budget"),
    ]
    budget = re.compile(r"budget|limit|cap\b|quota|run(?:s)? out|fail|error|stop|"
                        r"reset|exhaust|rate", re.I)
    base = "Built-in tool you can run:\n  ask -- %s" % fx["tool_sets"][0]["builtin"]["does"]
    cases, keys = [], []
    for ts in fx["tool_sets"][:4]:
        ctx_old = base + "\n\nYour tools:\n" + _tool_lines(ts, False)
        ctx_new = ctx_old + "\n\n" + new_ask
        for text, want in probes:
            cases.append((ctx_old + "\n\n" + text, ctx_new + "\n\n" + text))
            keys.append(want)

    def facts_score(a):
        want = next(it)
        a = (a or "").strip()
        if want == "budget":
            return bool(budget.search(a)), a[:60]
        return a.lower().startswith(want), a[:30]
    # one score() call per variant per case, in order: old then new
    keys = [k for k in keys for _ in (0, 1)]
    it = iter(keys)
    results["ask_facts"] = _bench_pair(model, cases, 80, facts_score) + (
        "states the true fact (authored probes)",)

    return results, None


def report_subagent(results, verbose):
    print("\n%-10s %-4s %-14s %-14s %s" % ("surface", "n", "old", "new", "wants"))
    unknown = False
    for name in ("starter", "compose", "ask_facts"):
        t, err, want = results[name]
        if t is None:
            print("%-10s UNKNOWN (%s)" % (name, err)); unknown = True; continue
        n = t["n"]
        if t["cut"] or t["empty"] > 0.2 * 2 * n:
            print("%-10s %-4d UNKNOWN (%d input-truncated, %d empty)"
                  % (name, n, t["cut"], t["empty"])); unknown = True; continue
        print("%-10s %-4d %-14s %-14s %s" % (
            name, n, "%d (%2.0f%%)" % (t["old"], 100.0 * t["old"] / n),
            "%d (%2.0f%%)" % (t["new"], 100.0 * t["new"] / n), want))
        if verbose:
            for row in t["rows"]:
                for variant, ok, note in row:
                    print("      %-3s %-4s %s" % (variant, "OK" if ok else "MISS", note))
    ideas, bad = results["oracle"]
    for v in ("old", "new"):
        r, tot = ideas[v]
        print("%-10s %-4s %s ideas routed through the subagent helper: %d of %d (%s)"
              % ("oracle" if v == "old" else "", "", v, r, tot,
                 "%.0f%%" % (100.0 * r / tot) if tot else "no parseable ideas"))
    if bad:
        print("           %d oracle replies unparseable or input-truncated -- excluded, not guessed" % bad)
    return unknown


def load(spec):
    p = os.path.join(HERE, "fixtures", spec["file"])
    d = json.load(open(p, encoding="utf-8"))
    return d[spec["key"]] if spec["key"] else d


def run_surface(name, model, verbose):
    spec = SURFACES[name]
    fixtures = load(spec)
    n = len(fixtures)
    tally = {"old": 0, "new": 0}
    empty = cut = 0
    print("\n=== %s  (%d real fixtures)   want: %s" % (name.upper(), n, spec["want"]))
    for i, f in enumerate(fixtures, 1):
        line = []
        for variant in ("old", "new"):
            msg = spec[variant](f)
            q = spec["q"].format(msg=msg, head=f.get("head", ""),
                                 cmd=f.get("command", ""))
            r = ask(model, q, max_tokens=spec["maxtok"])
            if r.get("unreachable"):
                return None, r["unreachable"]
            if not r["text"]:
                empty += 1
            if r["input_cut"]:
                cut += 1
            sc = spec["score"](r["text"], f)
            tally[variant] += bool(sc["ok"])
            line.append((variant, sc))
        if verbose:
            print(" %2d." % i)
            for variant, sc in line:
                print("     %-3s %-4s %s" % (variant, "OK" if sc["ok"] else "MISS", sc["note"]))
    return {"n": n, "tally": tally, "empty": empty, "cut": cut}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="all",
                    choices=list(SURFACES) + ["all", "subagent"])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    sys.path.insert(0, os.path.dirname(HERE))

    probe = ask(args.model, "Reply with the single word: ok", max_tokens=40)
    if probe.get("unreachable"):
        print("UNKNOWN: no local model at %s -- %s" % (OLLAMA, probe["unreachable"]))
        print("         This bench runs on the workstation, never on the "
              "creature's host. Nothing was measured; nothing is claimed.")
        return EXIT_UNKNOWN

    if args.bench == "subagent":
        print("bench: %s via %s  num_ctx=%d  (subagent-framing surfaces)"
              % (args.model, OLLAMA, NUM_CTX))
        print("the local model is a BENCH ONLY and is never a rung (section 6)")
        res, err = run_subagent_benches(args.model, not args.quiet)
        if err:
            print("UNKNOWN: lost the local model mid-run -- %s" % err)
            return EXIT_UNKNOWN
        return EXIT_UNKNOWN if report_subagent(res, not args.quiet) else 0

    names = list(SURFACES) if args.bench == "all" else [args.bench]
    print("bench: %s via %s  num_ctx=%d" % (args.model, OLLAMA, NUM_CTX))
    print("the local model is a BENCH ONLY and is never a rung (section 6)")

    results = {}
    for nm in names:
        res, err = run_surface(nm, args.model, not args.quiet)
        if err:
            print("UNKNOWN: lost the local model mid-run -- %s" % err)
            return EXIT_UNKNOWN
        results[nm] = res

    print("\n%-12s %-6s %-14s %-14s %s" % ("surface", "n", "old", "new", "verdict"))
    unknown = False
    for nm, r in results.items():
        n, t = r["n"], r["tally"]
        calls = 2 * n
        bad = r["empty"] > 0.2 * calls or r["cut"] > 0
        if bad:
            unknown = True
            why = []
            if r["cut"]:
                why.append("%d prompts were INPUT-TRUNCATED" % r["cut"])
            if r["empty"] > 0.2 * calls:
                why.append("%d/%d replies empty" % (r["empty"], calls))
            print("%-12s %-6d %-14s %-14s UNKNOWN (%s)"
                  % (nm, n, "-", "-", "; ".join(why)))
            continue
        moved = t["new"] - t["old"]
        verdict = ("no measurable difference" if abs(moved) <= max(1, 0.1 * n)
                   else ("BETTER +%d" % moved if moved > 0 else "WORSE %d" % moved))
        print("%-12s %-6d %-14s %-14s %s"
              % (nm, n,
                 "%d (%2.0f%%)" % (t["old"], 100.0 * t["old"] / n),
                 "%d (%2.0f%%)" % (t["new"], 100.0 * t["new"] / n),
                 verdict))
    if unknown:
        print("\nAt least one surface reported UNKNOWN. No verdict is claimed "
              "for it, because none was earned.")
        return EXIT_UNKNOWN
    print("\nSmall n is not a result. Treat anything under +/-10%% of n as noise, "
          "and a FAIL as much stronger evidence than a PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
