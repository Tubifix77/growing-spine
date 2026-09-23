#!/usr/bin/env python3
"""text_bench.py -- bench a change to text the creature READS, before shipping it.

WHY THIS EXISTS
---------------
CLAUDE.md section 5 records the single worst asymmetry in this project:

    "8 of 33 section 5 scars live in text the creature reads, and they are the
     only ones that have ever RECURRED after being fixed... No code scar has
     recurred, because a code fix ships with a test and a text fix was being
     verified by hoping."

A code fix gets a gate. A warning, a marker, a refusal message got nothing --
we changed the words, shipped them, and waited days to see whether behaviour
moved. Three text fixes in this project's history were shipped, believed, and
found later to have changed nothing at all.

This is the missing bench. It renders the OLD and NEW wording of one message
over REAL fixtures from the creature's own journal, puts both to a local model
of the SAME FAMILY as the production workhorse, and reports whether the new
wording actually produces the right action more often. Tue's idea, brought
over from the Growing Cousin spinoff on 2026-09-23.

WHAT IT IS NOT
--------------
**The local model NEVER serves the creature.** It is not a rung, it must never
become a rung, and section 6 is explicit about why: "No weak model in the
ladder: under a shared cap, weak calls starve smart rungs and a weak author's
buggy tools are lasting pollution." This process talks to localhost and the
creature's ladder does not know it exists.

It is also not proof. A local 12B is not the 31B the creature actually runs on,
so a PASS here is weak evidence and a FAIL is strong evidence: if a model of
the same family misreads our sentence, the sentence is ambiguous. Read it that
way round and it is honest.

HONEST LIMITS, stated because this file is an instrument
--------------------------------------------------------
- Fixtures come from the real corpus, never authored (section 5).
- temperature=0, so a run is reproducible and a difference is the wording
  rather than the dice.
- gemma4 emits a separate `thinking` field; the budget must cover it or the
  answer comes back EMPTY while eval_count sits at the cap -- the same
  "empty completion (reasoning-only, answer truncated)" shape groq_oss120
  returns in production. Measured here 2026-09-23.
- If no local model is reachable this prints UNKNOWN and exits 2. It never
  prints a pass it did not earn, and it never fails quietly: a bench that
  skips in silence is the "guard whose count is always zero" scar.

Usage:  python3 scripts/text_bench.py [--model gemma4:12b] [--fixtures PATH]
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

def _ollama_base():
    """OLLAMA_HOST is commonly set bare ("127.0.0.1" or "host:11434"), which
    urllib rejects outright. Normalise rather than demand a spelling."""
    h = (os.environ.get("OLLAMA_HOST") or "http://localhost:11434").strip()
    if not h.startswith(("http://", "https://")):
        h = "http://" + h
    if ":" not in h.split("//", 1)[1]:
        h += ":11434"
    return h.rstrip("/")


OLLAMA = _ollama_base()
DEFAULT_MODEL = "gemma4:12b"     # same FAMILY as the creature's gemma-4-31b-it
EXIT_UNKNOWN = 2                 # distinct from pass/fail: the bench could not run


def ask(model, prompt, max_tokens=700, timeout=300):
    """One local completion, or None if the bench cannot run at all."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        # THINKING OFF. Measured 2026-09-23: gemma4:12b spends 7,517 chars of
        # `thinking` on this prompt and returns an EMPTY answer even at a
        # 2,000-token budget -- 14 of 16 replies on the bench's first run came
        # back empty for exactly this reason. With think=false the same model
        # answers correctly in 8 tokens.
        #
        # It is a distortion and it is the right one: this is a DIFFERENTIAL
        # bench, old wording against new under identical conditions, so what
        # matters is that both sides face the same model in the same mode. It
        # measures which command the model NAMES, not how it got there.
        "think": False,
        "options": {"num_predict": max_tokens, "temperature": 0},
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
    return {
        "text": (msg.get("content") or "").strip(),
        "thinking": (msg.get("thinking") or ""),
        "tokens": d.get("eval_count") or 0,
        "done": d.get("done_reason"),
    }


# ---------------------------------------------------------------------------
# The message under test. NEW comes from the live code so the bench can never
# drift from what actually ships; OLD is the historical form, kept verbatim
# here because it no longer exists anywhere else.
# ---------------------------------------------------------------------------
def render_new(block, code):
    from executive.loop import _false_completion_reason
    return _false_completion_reason(block, code)


def render_old(block, code):
    """The wording shipped until 2026-09-23: the WHOLE block, so the first
    line quoted was whatever the creature had written at the top -- and it
    opens most blocks with a comment stating its plan. 1,566 refusals in the
    journal quote a comment this way."""
    return (f"You set current-phase to done, but `{block[:120]}` exited with "
            f"code {code} in the same cycle. A failing check means you are NOT "
            f"done. Phase reverted to code. Fix the failure, run your DONE WHEN "
            f"check until it exits 0, and only then mark done.")


QUESTION = (
    "You are an autonomous agent. You marked your work done and the system "
    "refused, with this message:\n\n"
    "{msg}\n\n"
    "Name the single shell command you must fix. Reply with ONLY that command "
    "on one line, nothing else."
)


def scores(answer, fixture):
    """Did the model name the real command, and did it name the comment?"""
    a = (answer or "").strip().strip("`").strip()
    a = re.sub(r"^```(?:bash|sh)?\s*|\s*```$", "", a).strip()
    first = a.splitlines()[0].strip() if a.splitlines() else ""
    cmd = fixture["command"]
    head = cmd.split()[0] if cmd.split() else cmd
    comment = fixture["block"].splitlines()[0].strip()
    return {
        "named_command": head in a,
        "named_comment": first.startswith("#") or comment[:30] in a,
        "answer": first[:70],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--fixtures", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "fixtures", "done_gate_blocks.json"))
    ap.add_argument("--max-tokens", type=int, default=700)
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        fixtures = json.load(open(args.fixtures, encoding="utf-8"))
    except OSError as e:
        print("UNKNOWN: no fixtures at %s (%s)" % (args.fixtures, e))
        return EXIT_UNKNOWN

    probe = ask(args.model, "Reply with the single word: ok", max_tokens=200)
    if probe.get("unreachable"):
        print("UNKNOWN: no local model at %s -- %s" % (OLLAMA, probe["unreachable"]))
        print("         This bench runs on the workstation, never on the "
              "creature's host. Nothing was measured; nothing is claimed.")
        return EXIT_UNKNOWN

    print("bench: %s via %s   fixtures: %d (real, from journal.jsonl)"
          % (args.model, OLLAMA, len(fixtures)))
    print("the local model is a BENCH ONLY and is never a rung (section 6)\n")

    tally = {"old": {"cmd": 0, "comment": 0}, "new": {"cmd": 0, "comment": 0}}
    empty = 0
    for i, f in enumerate(fixtures, 1):
        row = []
        for variant, render in (("old", render_old), ("new", render_new)):
            msg = render(f["block"], f["code"])
            r = ask(args.model, QUESTION.format(msg=msg), max_tokens=args.max_tokens)
            if not r.get("text"):
                empty += 1
            sc = scores(r.get("text"), f)
            tally[variant]["cmd"] += bool(sc["named_command"])
            tally[variant]["comment"] += bool(sc["named_comment"])
            row.append((variant, sc))
        print("%2d. want: %s" % (i, f["command"][:62]))
        for variant, sc in row:
            mark = "OK " if sc["named_command"] and not sc["named_comment"] else "MISS"
            print("      %-3s %s  %s" % (variant, mark, sc["answer"]))

    n = len(fixtures)
    print("\n%-5s %-22s %s" % ("", "named the command", "named a comment"))
    for variant in ("old", "new"):
        t = tally[variant]
        print("%-5s %2d/%-2d (%3.0f%%)          %2d/%-2d (%3.0f%%)"
              % (variant, t["cmd"], n, 100.0 * t["cmd"] / n,
                 t["comment"], n, 100.0 * t["comment"] / n))
    # A BENCH THAT COULD NOT MEASURE MUST NOT REPORT A VERDICT.
    # On its first run 14 of 16 replies came back empty and it printed
    # "NOT AN IMPROVEMENT" anyway -- a conclusion drawn from nothing, which is
    # this project's own house disease arriving inside a brand-new
    # instrument. gs-bug-daily item 17: a census over a known population never
    # reports a total it cannot reconcile with that population.
    if empty:
        print("\n%d of %d replies came back EMPTY." % (empty, 2 * n))
    if empty > 0.2 * 2 * n:
        print("\nUNKNOWN: too many empty replies to conclude anything. The model "
              "spent its budget on `thinking` and returned no answer; raise "
              "--max-tokens or check that think=false is being honoured.")
        print("         No verdict is reported, because none was earned.")
        return EXIT_UNKNOWN

    moved = tally["new"]["cmd"] - tally["old"]["cmd"]
    print("\nVERDICT: the new wording named the right command %+d times out of %d."
          % (moved, n))
    if moved <= 0:
        print("         NOT AN IMPROVEMENT ON THIS BENCH. A text fix that does not "
              "move behaviour is a text fix that has not been verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
