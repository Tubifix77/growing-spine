---
name: gs-instruments
description: Audit the Growing Spine's own checks — has each instrument ever fired, has it been seen both firing and silent, and can you name the case where it stays quiet while the thing it watches is broken. Fire on "are the checks still working", "gs-instruments", a guard that reads zero, after adding any new instrument, or whenever a fault was found by a human rather than by the system.
---

# gs-instruments — do the checks themselves still work?

This is the skill aimed at the project's characteristic bug: **an instrument that
reads zero, or reads plausible, while broken.** Every serious incident here has
had a working instrument pointed slightly to one side of it.

Fire this whenever a fault was found by a human asking rather than by the system
saying. That is the definition of an instrument gap.

## Before you start — the governing rule

**A guard whose count is always exactly zero is broken, not idle.** The stub
janitor logged `aged-out 0` twenty-eight times with 25 stubs in front of it,
because the template and the detector were four words apart. Zero is a claim
that requires the same evidence as any other number.

Every failure mode this skill hunts is recorded in `CLAUDE.md` §5, with the
incident that produced it. Read it there rather than trusting the summaries
above — they are pointers, and §5 is the source.

## The instruments in scope

Enumerate all of them, every run. Currently: `SENSOR`, `JANITOR`, `JOURNAL`,
`WIRING`, `JSONL`, `FLATLINE`, `STALE-FALLBACKS`, `UNMET`, `WAKE`, `THINK` /
`THROUGHPUT`, the startability gate, the broken-tool warning, each done-gate
branch (failing-check, hollow-touched, unstartable-touched, gate-choice,
library-backlog, spin-trap), the stub organ, `body_responds`, and the loop
warnings (`_build_loop_warning`, `_build_data_warning`,
`_build_stuck_tool_warning`). Add new ones here as they are built.

## Tier 1 — mandated checks, for EACH instrument.

1. **Has it ever fired?** Give the date of its most recent firing, from the
   health log or the journal.
2. **Has it been observed both firing and silent?** An instrument seen in only
   one state is unproven in the other.
3. **Is its count always exactly zero?** If so, treat as broken until shown
   otherwise.
4. **When did its value last change?** A number frozen for weeks is either a
   stable system or a dead sensor, and the two look identical.
5. **Does a test exist that actually makes it fire?** Not that it can be called —
   that it goes red when the fault is present. Assert the contract, not the
   mechanism, and note where the mechanism is POSIX-only.
6. **Who receives it** — the creature, this session, or Tue? An instrument only
   we can read buys better supervision, not autonomy.
7. **Is it edge-triggered or continuous?** A fact repeated every cycle is a nag
   the creature learns to skip; a fact that never repeats can be missed once and
   lost.
8. **Does it share its predicate with whatever acts on it?** Two definitions of
   one question always drift. On 2026-08-19 the broken-tool warning used
   `tool_syntax_error` while the done-gate used `tool_start_failure`, so a tool
   that was valid Python with no execute bit was invisible to both — and the
   creature found the hole before we did.
9. Cost per invocation, and what it costs at 1,000 tools or a 1 GB journal.
10. Deltas against the previous run of this skill.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **For each instrument, try to state the circumstance in which it stays silent
> while the thing it watches is broken. If you cannot think of one, you have not
> understood it well enough to trust it.** This is the whole point of the skill.
> Worked example: on 2026-08-19 FLATLINE correctly named the silent providers,
> WAKE correctly reported that context building was cheap, and UNMET correctly
> reported demand — three instruments, all accurate, and the creature had been
> down for twelve hours because none of them watched whether it was thinking.
> The gap was found because Tue asked for a check.

> **Then audit the newest instruments hardest.** Anything added in the last week
> has the least evidence behind it and the most confidence attached to it. For
> each: has it fired for real yet, has its threshold ever been approached, and
> would you know the difference between "no false positives" and "wired to
> nothing"? The startability gate has fired zero times in forty hours and both
> readings remain open.

> **And ask which alarm you have started ignoring.** A unit that sits in
> `failed` as designed, a tag that is always `!!`, a warning whose count never
> moves — habituation is an instrument failure that lives in the reader, not the
> code. Name any signal that has become wallpaper.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing the system should be watching and is not — or say plainly that
> you found none. This is where new instruments come from; `check_throughput`
> exists because this question was asked once.

## Write the numbers down

Append one record per run to `~/gs-history/instruments.jsonl` on the laptop.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `instruments{name:{last_fired,ever_fired,both_states,
value,changed_at,tested,audience,edge_triggered,shared_predicate,cost_ms}}`,
`never_fired[]`, `frozen[]`, `unshared_predicates[]`, `gaps_named[]`.

## The bar for adding one

An instrument that only a human or a session can read does not make the creature
more independent — it makes us better caretakers. Both are legitimate; say which
you built. And **never build anything that makes the creature depend on our
inspection**: if a fault is caught only because someone read a log, it is not
fixed.
