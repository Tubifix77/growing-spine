---
name: gs-bug-daily
description: Inspect the Growing Spine FRAMEWORK for faults over a recent window (default 20h, typically last session's fixes to today's run) — error classification, bad directives the creature is obeying, and whether the last session's fixes actually worked. Fire on "what happened since yesterday", "check for bugs", "gs-bug-daily", or any request to review recent framework health.
---

# gs-bug-daily — what went wrong in the framework, and did the last fix work?

Scope is the **framework**, not the creature's own tools (that is `gs-products`).
The question is: did our code, our prompts, or our providers fail it, and did
what we changed last time do what we said it would.

Output goes to **Tue and this session**. Nothing here enters the wake context.

## Before you start — three ways this check lies

- **Read `~/growing-spine-mind/journal.jsonl`, never `journalctl`.** journald
  carries the framework's stdout; most of what the creature DID never reaches it.
- **That file keys on epoch `ts`.** `grep '2026-08-22'` returns a handful of
  coincidental hits and reads exactly like a quiet day. Parse `ts`.
- **A guard-rail firing is not a fault.** On 2026-08-22, 11 of 11 "errors" were
  the done-gate and a spin trap working correctly.

Full scar list: `CLAUDE.md` §5. Do not restate it here — point at it.

## Tier 1 — mandated checks. Run all of them, every time.

1. **Window validity first.** Per-hour record counts across the whole window.
   Report gaps as gaps; a box that was off is not a collapse. Reconcile against
   what the human believes the runtime was, and say when they disagree.
2. Totals: `served_by`, `exec_start`, `exec_skip`, `error`, plus rate per hour
   **over the span that produced records**, not wall clock.
3. Every distinct error string with a count. No sampling.
4. Classify every error into four buckets and report them **separately**:
   guard-rail-fired (done-gate false-completion / hollow / upgrade / backlog,
   spin trap, startability block), provider error, **unclassified**
   (`UNEXPECTED:` prefix from the generic handler), other.
5. Provider errors: any that reached the keychain's `unknown` path ("does not
   recognise"), and any hard-raise. Either is a rung whose failure mode we had
   not enumerated.
6. `exec_skip` reasons split three ways: no bash block / truncation / unclosed.
7. Truncation share of thinks **and which rung produced it**.
8. Tools created in the window that cannot start — count and names
   (`volume.tools.tool_start_failure`).
9. `git log` since the previous run: what landed, on both machines, and whether
   the running brain actually holds it.
10. **Which authoring door it used** — `tool-new` / `tool-edit` / redirect-or-tee
    into `tools/own`. Added 2026-08-23 by the blank pass: the redirect is the door
    that leaves no `.bak` and no execute bit, and nothing else asks. First
    reading: tool-edit 7, redirect 1, tool-new 0.
11. **Is the broken-tool warning actually reaching the wake context?** Count
    records mentioning it in the window, not just whether the state file exists.
    Added 2026-08-23: the state file said 32 and looked healthy while the fact had
    not been said once in 28 hours.
12. **Did engagement convert to action?** Count the cycles in which the
    creature *engaged* with a standing warning (quoted it, reasoned about it,
    named a tool from it) against the number of items it actually repaired.
    Added 2026-08-24 by the blank pass: on this run it engaged in four
    separate cycles and the count stayed at 32, and no item above asks that.
    A count is a lagging indicator; engagement is the leading one.
13. **Provider failures journalled under a kind OTHER than `error`.** Added
    2026-08-27 by the blank pass. The error census reads `kind == "error"` and
    on this run reported **0 provider errors** while two live provider failures
    sat in the journal as kind `idea_gate`: *"batch judge parsed 0/4 -- band
    left UNJUDGED. cause=EMPTY-REPLY (provider returned nothing); reply 0 chars
    vs 1040 tok budget"* at 03:58 and 04:00. A 200 with an empty body is not an
    `error` to `classify_error` and never becomes one, so it is invisible to a
    census keyed on that kind. Sweep every kind for provider-shaped failures:
    `EMPTY-REPLY`, `provider returned nothing`, `UNJUDGED`, `0 chars`, HTTP
    codes. Report them beside the four buckets, not inside them.
14. **The early-rejection stage: count journal KINDS, not advisory text.** Added
    2026-08-27, correcting my own 2026-08-26 conclusion. I searched for the
    gate-choice string *"a near-duplicate will not be built"*, found only
    `think_end` records, declared the stage uncountable and instrumented a third
    path (`oracle_rest`) that has fired **0 times all-time**. Two countable
    kinds already existed and I never looked: **`idea_gate` (157 all-time)** and
    **`novelty_block` (52 all-time)**. Search by `kind`, then by string --
    never the reverse.
15. **`exec_skip` rate BY RUNG — not just the total.** Added 2026-08-29 by the
    blank pass, and it is the single most valuable number this skill has ever
    produced. The aggregate skip count looked fine all week (69 in 32.9 h).
    Split by the rung that served the cycle it reads:

    | rung | served | skips | skip rate |
    |---|---|---|---|
    | `google_gemma` | 1144 | 6 | **0.5%** |
    | `cloudflare` | 88 | 0 | **0.0%** |
    | `gemini_flash` | 26 | 14 | **53.8%** |
    | `openrouter_super` | 75 | 73 | **97.3%** |

    A rung that answers but whose answers cannot be used is worse than a dark
    one: it consumes the cycle and reports success, so `record_success` keeps
    it open forever and nothing below it is ever reached. Without this split
    the whole loss hides inside a healthy-looking total.
    **It is also the control you need for any context-size change.** On this
    run I raised the journal caps, saw a 100% skip burst six minutes later, and
    reverted my own change — the burst was six minutes of the 97.3% hole with
    the workhorse walled, and I could not tell the difference because no
    per-rung baseline existed. Measure this BEFORE changing anything that
    touches prompt size.
16. **The effort funnel for this window**, as defined in `../effort-funnel.md`.
    The error buckets say what went wrong; the funnel says what fraction of what
    it set out to build became a working tool. Report every stage including the
    zeroes, and keep rounds-to-green separate from rounds-then-abandoned — a tool
    that took fifteen attempts and works is a success story, not a fault.
17. **Deltas against the previous run of this skill**, from the history file.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Every fix landed in the previous session is on trial.** For each one: name
> what it was supposed to change, find the specific number that would show it,
> and say whether that number moved. A fix whose effect you cannot locate has
> not been verified — say so plainly rather than assuming it worked. Two
> self-inflicted faults in one week would have been caught here: a rung added on
> 08-17 was carrying 77% of traffic by 08-18 and nobody asked what it returns
> when its allowance runs out; a predicate split on 08-19 left the warning
> reporting 9 while the gate checked 32, and the creature found the hole three
> days before we would have.
>
> **Deliver:** One line per fix: what it should have changed, the number that shows it, and moved / did not move / could not locate. "Could not locate" is a permitted answer and counts as unverified.

> **Then look for obedient-but-wrong behaviour — the hardest and most valuable
> item here.** Something the creature did repeatedly, correctly following a
> framework instruction, that produced a bad outcome. This is the class that
> cost two months when the tool-header contract showed the convention without
> its `#` and obedient files died with `tool:: command not found`. Read its own
> `think` records for how it *interprets* our instructions — that is the only
> window we have into misunderstanding, because it has no outbound channel and
> cannot tell us. Look for: a documented instruction followed to the letter with
> a bad result; the same wrong shape rebuilt by a different mechanism after we
> named a mechanism instead of an invariant; repeated confusion about where
> something lives or what a tool is called.
>
> **Deliver:** At least three `think` records quoted with timestamps, or the number of records you read and what you concluded from them. Reading none is not an answer.

> **For every instrument that fired this window, ask whether it fired for the
> right reason** — a correct alarm raised by the wrong cause is a coincidence
> that will not repeat.
>
> **Deliver:** One line per instrument that fired: right reason / wrong reason / cannot tell.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing in this window that no item above would have caught — or state
> plainly that you found none. If you found one and it mattered, add it to
> Tier 1 in this file, dated. That is how this list grows from experience rather
> than from imagination.

## Fix the obvious, up front, and say what you fixed

**This skill does repair — but only our own code, and only when the fix is
obvious.** Do it before writing the report, and list every one in the executive
summary so nothing is repaired silently.

Obvious means **all** of these:

- the fault is in **framework code** — `executive/`, `keychain/`, `volume/`,
  `scripts/`. Never a tool of the creature's: those go to Tier 4 and are never
  fixed by us, whatever the temptation.
- the fix is small enough to hold in your head, and you can name the invariant it
  restores;
- it ships with a test that **fails without it**;
- the gate passes on **both machines** afterwards.

Never "obvious", regardless of how clear it looks:

- a **chat message to the creature**, or a change to a **world RULE** it must
  obey — `CLAUDE.md` §2.7. That paragraph covers what is *sent* to the creature
  in Tue's voice, and adding or removing an obligation. **It does not cover
  prompt, warning or marker TEXT, and this line used to claim it did** —
  corrected 2026-08-27 after Tue pointed out that the exemption protected the
  one thing that most needs repairing.
  The test: **does the change add a constraint, or make an existing fact
  legible?** Adding a constraint is design — show him. Making a fact legible is
  repair — it is yours, and §6 requires it: "a known-failing behaviour in OUR
  framework is fixed without asking".
  Text the creature reads is held to the **same** standard as code, not a
  weaker one and not an exempt one: name the invariant, ship a test that fails
  without it, gate both machines. That is the standard it was missing, and why
  three text scars have recurred after being "fixed" while no code scar has —
  the tool header shown without `#` (two months), `jq -n` named as a mechanism
  (rebuilt by heredoc in 36 h), and the "reworded form" ban the creature called
  a trap;
- a **config or provider change** — that follows the ladder discipline, code
  before config, and a rung's exhaustion signature must be known first;
- anything in `framework-tools/` — protected scar tissue;
- anything you would have to argue for. If it needs an argument it is a finding
  with a named trigger and a date, not a fix.

An emergency is different again and comes first: see "When the fault is an
emergency" below. Stop the bleeding, then report all six items anyway.

## Tier 4 — the response protocol. Mandatory for every fault found in what the creature produced.

**A fault in its output is never fixed by fixing its tool.** The doctrine and the
reasons are in `CLAUDE.md`, "The method" — not restated here. What follows is the
required OUTPUT FORM, because a method stated as a philosophy gets agreed with and
skipped.

For **each** fault, produce all six:

1. **The class, not the instance.** Name the kind of fault, in words a detector
   could be written against. *"`extract-key-insights` contains a rate-limit error
   message"* is an instance; *"a failed command's stdout can be written into a
   file as a program"* is a class. Only the class can be defended against.
2. **The machine that produced it.** What in the framework allowed a file in this
   shape to exist at all? If the honest answer is "nothing prevents it", that is
   the finding, and it is a framework finding rather than a creature one.
3. **Why it cannot see it now.** The harder half, and where the framework bug
   usually turns out to be. A fault it is told about at every single invocation
   but cannot add up across cycles is invisible in the only sense that matters —
   that was the whole of the ten unstartable tools.
4. **The detector.** Does one exist that catches the NEXT instance of this class
   without anyone asking? Name it, or state plainly that building it is the
   deliverable. It must pass two tests: it would have caught **this** instance
   retroactively, and it fires on the next one **unprompted**.
5. **How the fact reaches the creature.** It cannot request a check for a problem
   it does not know it has, so a tool it must choose to run is worthless here —
   the fact has to arrive the way the gate fact arrives. Name the channel and its
   trigger. If the finding reaches only us, say so: that is a weaker outcome and
   must be labelled as one, not presented as a fix.
6. **Confirmation that no tool of its own was edited** and that none of its junk
   or `.bak` files was deleted.

> **Deliver:** All six, per fault. **A fault reported without items 4 and 5 is a
> complaint, not a finding.** If the honest answer to 4 is "no detector, and I am
> not building one now", give the reason and the named trigger with a date that
> would change that — a hold without a date is inaction wearing caution's clothes.

### When the fault is an emergency

If the fault you are reporting is *currently* wedging the system — a tool
spinning, a body that cannot fork, a disk filling — **stop the bleeding before
you write anything.** Kill the processes, respawn the body. That is not an
intervention in its world: its tools are its world, its processes are not, and
the body is disposable by design.

Then come back and produce all six items anyway, because the emergency is the
evidence rather than the exception. Item 2 has a specific answer in this case:
**the framework was missing a bound**, and item 4's detector is a limiter — a
cap, a timeout, a reaper — not an edit to its tool. Record what the intervention
was, so the next run can see whether the limiter made it unnecessary.

Judge the emergency on measurements, not on the reading that alarms most: the
container is capped at 1.5 cores and 1 GB, so a runaway tool of its own cannot
starve the host. Disk and PIDs are the unbounded ones.

## Write the numbers down

Append one record per run to `gs-history/bug-daily.jsonl` in this repo checkout.
Gitignored, so it never publishes.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `window_h`, `span_h`, `thinks`, `exec`, `skips`, `errors`,
`err_guardrail`, `err_provider`, `err_unclassified`, `err_other`,
`truncation_pct`, `cannot_start`, `fixes_verified`, `fixes_unverified`,
`fixes_failed`, `fixed_up_front[]`, `open_items[]`, and the `funnel{}` block from
`../effort-funnel.md`.

Plus, for Tier 4: `faults[]` with `class`, `machine`, `blindness`, `detector`, `channel`, and `no_tool_edited: true` on each. A fault recorded without a `detector` and a `channel` is stored as `incomplete: true`, so the gap is countable later rather than forgotten.

## The executive summary — last thing in the report, first thing read

Tue reads this to know in five seconds whether he needs to care. It is numbers
and plain statements, no hedging, and it **must state the clean case explicitly**:
"No issues found" is a required sentence when true, not an absence the reader has
to infer.

Three lines, always all three:

```
FIXED UP FRONT   n — one clause each, naming what was wrong
OPEN             n — one clause each, with the trigger and date that resolves it
NO ISSUES        (or the word NONE against a heading that would otherwise be empty)
```

Then the three-state accounting for everything under monitoring. **Every item
must land in exactly one column, and the columns must sum to the total** — an
item that is neither done, unverified, nor failed has been lost:

```
UNDER MONITORING  n total
  verified        n — the number moved and I can point at it
  unverified      n — could not locate the number, or not enough time has passed
  failed          n — the number moved the wrong way
```

Cover in that accounting: every fix from the previous session, every named
trigger with a date, every instrument that should have fired, and every open lead
carried forward. **"Unverified" is a first-class answer and must never be rounded
up to "verified"** — a fix whose effect you cannot locate has not been verified,
and saying so is the whole point of the column.

End with the one-line trend against the previous run: thinks/hour, errors,
`cannot_start`, and rounds-per-tool from the funnel.

## Output shape

The four error buckets and the rate table first, then Tier 2 findings as prose,
then the blank-pass answer. Anything that changes standing understanding goes
into `CLAUDE.md` §8 — there, and nowhere else.
