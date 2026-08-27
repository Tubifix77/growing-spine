# The effort funnel — one definition, computed by two skills

`gs-bug-daily` computes this per window; `gs-products` computes it over its own
horizon. Neither owns it. Overlap in measurement is fine; a second definition is
not.

Tue's idea, 2026-08-24. The point: **error buckets say what went wrong and never
what fraction of intent becomes a working tool.** Both are needed.

## The stages — report every one, including the ones that read zero

| stage | how to get it |
|---|---|
| distinct tools worked on | union of names across all three doors |
| authoring actions | `tool-new` + `tool-edit` + redirect/`tee` invocations |
| **rounds per tool** | actions ÷ distinct tools |
| early rejected | journal kinds `idea_gate` + `novelty_block` + `oracle_rest` |
| done-marks attempted | `remember current-phase done` in the window |
| **late rejected** | done-gate blocks by kind: false-completion / hollow / upgrade-no-change / cannot-start |
| done accepted | attempted − refused |
| passed but cannot start | of the tools accepted in the window, how many fail `tool_start_failure` |

## The rule that keeps this honest

**Rounds must be paired with the outcome, or the metric scolds honest iteration.**

First reading, 2026-08-24: 50 edits across 11 tools — 4.5 each — and two tools
took 29 of the 50. `SystemicEventAnalyzer` 15 edits in a single hour;
`plan_gap_store` 14 over 7.3 h with five done-marks inside the span, meaning the
gate bounced it and it went back. **Both ended green and start fine.** That is
intense converting work, not thrash.

So report **rounds-to-green separately from rounds-then-abandoned**, and never
present a high round count as a fault on its own. The tool that took fifteen
attempts and works is a success story; the one that took three and was abandoned
is the finding.

## The stage to distrust

**Early rejection read zero on its first three readings, and it was blind, not
idle** -- exactly what this section was written to catch. Diagnosed 2026-08-26:
the stage was defined as two things, and NEITHER was countable. The gate-choice
line "a near-duplicate will not be built" is advisory text in the wake context,
not a rejection event -- it appears in 32 `think_end` records in a single window
and 785 all-time, so counting it measures how often the creature was TOLD the
rule. And the oracle's rest decision only ever `print`ed to stdout, which lands
in journald while this metric reads `journal.jsonl`. A stage that always reads
exactly zero is broken rather than idle -- the stub janitor logged `aged-out 0`
twenty-eight times with 25 stubs in front of it.

Fixed by journalling the rest decision as kind `oracle_rest`, deliberately
outside `MEANINGFUL_KINDS` so it reaches this metric and never the creature.
**The stage is therefore newly instrumented from 2026-08-26: treat its first
non-zero reading as a baseline, not as a change.**

**Corrected 2026-08-27, and the correction is the more useful lesson.** The
2026-08-26 diagnosis was half wrong. The gate-choice half was right -- that
string really is advisory text. But the claim that the stage had NO countable
event was false: `journal.append(..., "idea_gate", ...)` at `loop.py:1789` and
four `novelty_block` appends at 1977-2050 were already there, **157 and 52
records all-time**. I found nothing because I searched for the advisory STRING
instead of enumerating journal KINDS, then added a third path (`oracle_rest`)
which has since fired **0 times all-time**. Method rule: **for any event you
suspect is uncountable, enumerate `kind` values first and grep strings second.**
A `collections.Counter` over every `kind` in the file costs one pass and would
have answered it immediately.

Note also that `idea_gate` is a SHARED kind -- it also carries batch-judge
failures -- so counting it requires reading the content, not just the kind.

## History keys

`funnel{tools_worked, actions{new,edit,redirect}, rounds_per_tool,
early_rejected, done_attempted, late_rejected{by_kind}, done_accepted,
accepted_cannot_start, rounds_to_green[], rounds_abandoned[]}`
