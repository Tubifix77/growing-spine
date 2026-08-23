---
name: gs-directives
description: Find places where the Growing Spine framework is telling the creature something wrong, ambiguous, or obeyable-to-the-letter-but-harmful — bad directives rather than bad code. Fire on "is it misunderstanding us", "check the prompts", "gs-directives", a fault that looks like obedience, or any repeated behaviour that matches an instruction and produces a bad outcome.
---

# gs-directives — is the framework telling it something wrong?

Everything else looks for broken code. This looks for **correct code carrying a
bad instruction** — the class where the creature does exactly what it was told
and the outcome is worse for it.

Run this on a **long horizon**, not daily. Misunderstandings here have taken
weeks to surface: the tool-header contract showed the convention without its `#`
for two months, and obedient files died with `tool:: command not found` the whole
time. Monthly, or after any fault that smells like obedience.

## Before you start — why this class hides

The creature has **no outbound channel**. It cannot ask which of two readings we
meant, cannot report that an instruction is unclear, and gets one reply per
message. So an ambiguous directive produces silent, patient, repeated
compliance — which looks exactly like the creature being bad at something.

Its only visible interpretation is in its own `think` records. That is the
window; use it.

## What the creature actually reads

`protected-prompt.md` (ours, authoritative), `editable-prompt.md` (its own, it
rewrites this), the tool catalogue injected each cycle, the in-loop warnings,
the done-block reason text, and any chat message from Tue. Every one of those is
a directive surface.

## Tier 1 — mandated checks. Run all of them, every time.

1. **Every convention shown by example** in the prompts: does the example show
   the convention *exactly* as the file must contain it? A convention shown
   imprecisely gets obeyed literally. Diff the example against what `tool-new`
   actually writes and against what a healthy live tool actually contains.
2. **Every instruction that names a mechanism rather than an invariant.** These
   get obeyed to the letter and the fault returns by another route: told not to
   build JSON with `jq -n`, it stopped using `jq` and rebuilt the identical
   fault with a heredoc 36 hours later. List every "don't use X" and rewrite it
   as "hold Y true".
3. **Every instruction with two readings.** State both and say which the
   creature's behaviour shows it took.
4. **Contracts that specify durability but not identity** — "put it somewhere
   persistent" produces obedient tools that cannot find each other's data. Say
   *where*, exactly, not *which volume*.
5. **Broken tools whose fault matches a documented instruction.** Cross-check
   the current startability failures against the prompts: is any family the
   shape of something we told it to do?
6. **Its own `editable-prompt.md`**: what has it written there about how to work?
   Anything it has told itself that contradicts ours is a directive collision,
   and its version is the one it follows.
7. **Repeated confusion signatures in `think` records**: the same question asked
   across cycles, uncertainty about where something lives, a tool called by a
   name that does not exist, re-deriving a fact the framework already supplies.
8. **In-loop warning text**: does each warning state an invariant, name no
   mechanism, and arrive on a change of state rather than continuously?
9. **The done-block reason text** it receives when a gate blocks it — is it
   actionable, or does it name a condition without a next step?
10. Deltas against the previous run of this skill.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Look for obedient-but-wrong behaviour, and treat finding none as a claim you
> have to defend.** The signature is: a behaviour repeated across many cycles,
> traceable to a documented instruction, producing an outcome we would not want.
> Worked example, the one that cost two months — the contract displayed the tool
> header as `tool: <name>` without the leading `#`. Files written exactly as
> shown died before executing a line. Nothing in the error output pointed at the
> documentation, and the creature had no way to tell us the instruction was
> wrong. It was found only when we asked it what made its work harder.
>
> Note the harder half of that story: **when the same fault recurs after the
> documentation is fixed, the documentation is no longer the cause.** As of
> 2026-08-19 `protected-prompt.md` shows the header correctly and says outright
> that the file dies without the `#`, and three tools written that week still
> reproduced it. Re-fixing the wording then would have been treating a symptom
> that was not there. Check whether the directive is still wrong before blaming
> it.

> **Then read the prompts as the creature, not as their author.** Take one
> instruction and ask what the cheapest literal compliance looks like. If
> cheapest-literal-compliance is harmful, the instruction is the bug regardless
> of how clear it seems to whoever wrote it.

> **And ask what it needs to know that we have never told it.** Absence is a
> directive fault too, and it is invisible by construction. Look for facts it
> repeatedly re-derives, capabilities it has but never uses, and things it built
> a tool to discover that the framework could simply state.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one way the framework is misleading the creature that no item above would
> have caught — or say plainly that you found none. If it mattered, add it to
> Tier 1, dated.

## Write the numbers down

Append one record per run to `gs-history/directives.jsonl` in this repo checkout.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `examples_checked`, `mechanism_phrasings[]`,
`ambiguous[]`, `collisions[]`, `confusion_signatures[]`, `obedient_wrong[]`,
`absences[]`.

## Changing a directive is Tue's call

A world-RULE change is announced in Tue's voice and is his decision: draft it,
show him, send after approval, and make the announcement match the code's
wording verbatim (`CLAUDE.md` §2.7). Never tell the creature about its own bugs —
chat is world-facts only.

## The related ritual

Once a month, ask the creature directly what made its work harder. Ask for
**symptoms, never causes**, and always **with a time window** — its recent state
lives in a five-slot register that overwrites each cycle, so an open question
returns only its oldest memories. It answers once. Then investigate yourself and
report back. The first run of this in 2026-08 surfaced the two-month header bug.
