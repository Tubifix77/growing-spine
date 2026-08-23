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
10. **The composition of the wake context**: how many characters are static
    contract versus live state. Added 2026-08-23 by the blank pass — the
    contract is 84 lines / 10,730 chars injected every cycle and nothing
    measures what share of its attention budget goes to text that never
    changes. Do NOT call `_build_context` to find out: it ends in
    `_mark_surfaced()` and writes rotation state.
11. Deltas against the previous run of this skill.

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
>
> **Deliver:** Each candidate as a triple — instruction, behaviour, bad outcome — or the number of instructions you checked and why none matched.

> **Then read the prompts as the creature, not as their author.** Take one
> instruction and ask what the cheapest literal compliance looks like. If
> cheapest-literal-compliance is harmful, the instruction is the bug regardless
> of how clear it seems to whoever wrote it.
>
> **Deliver:** One instruction quoted, its cheapest literal compliance spelled out, and whether that compliance is harmful.

> **And ask what it needs to know that we have never told it.** Absence is a
> directive fault too, and it is invisible by construction. Look for facts it
> repeatedly re-derives, capabilities it has but never uses, and things it built
> a tool to discover that the framework could simply state.
>
> **Deliver:** At least one named absence, or the list of re-derived facts and unused capabilities you checked before concluding there is none.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one way the framework is misleading the creature that no item above would
> have caught — or say plainly that you found none. If it mattered, add it to
> Tier 1, dated.

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

Append one record per run to `gs-history/directives.jsonl` in this repo checkout.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `examples_checked`, `mechanism_phrasings[]`,
`ambiguous[]`, `collisions[]`, `confusion_signatures[]`, `obedient_wrong[]`,
`absences[]`.

Plus, for Tier 4: `faults[]` with `class`, `machine`, `blindness`, `detector`, `channel`, and `no_tool_edited: true` on each. A fault recorded without a `detector` and a `channel` is stored as `incomplete: true`, so the gap is countable later rather than forgotten.

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
