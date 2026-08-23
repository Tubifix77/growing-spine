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
10. **Deltas against the previous run of this skill**, from the history file.

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

> **For every instrument that fired this window, ask whether it fired for the
> right reason** — a correct alarm raised by the wrong cause is a coincidence
> that will not repeat.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing in this window that no item above would have caught — or state
> plainly that you found none. If you found one and it mattered, add it to
> Tier 1 in this file, dated. That is how this list grows from experience rather
> than from imagination.

## Write the numbers down

Append one record per run to `~/gs-history/bug-daily.jsonl` on the laptop —
host home, so it is outside the creature's volume and outside this public repo.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `window_h`, `span_h`, `thinks`, `exec`, `skips`, `errors`,
`err_guardrail`, `err_provider`, `err_unclassified`, `err_other`,
`truncation_pct`, `cannot_start`, `fixes_verified`, `fixes_unverified`.

## Output shape

The four error buckets and the rate table first, then Tier 2 findings as prose,
then the blank-pass answer. Anything that changes standing understanding goes
into `CLAUDE.md` §8 — there, and nowhere else.
