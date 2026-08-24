---
name: gs-products
description: Census and quality review of the tools the Growing Spine creature has built for itself — used or unused, broken or sound, and which are good enough to copy elsewhere. Fire on "what has it built", "analyse its tools", "gs-products", "is any of its work any good", or any request to review the creature's own library.
---

# gs-products — what it built, whether it works, and what is worth stealing

Scope is the creature's **output**: `~/growing-spine-mind/tools/own`. Framework
faults are `gs-bug-daily`.

Read-only. **Never edit anything under `tools/own`** (`CLAUDE.md` §2.1) and never
delete its `.bak` or junk files — they are its safety net.

## Before you start — four ways this check lies

- **Canonical `volume.tools.list_tools`, never `ls`.** Raw `ls` says 616 where
  the canonical count is 485. A past session reported "+151 in three days" by
  mixing the two.
- **`demand_counts` is a cumulative all-time counter with no timestamps.** It
  cannot express any present tense. For "used recently" you must read
  `journal.jsonl` by epoch.
- **Never point `py_compile` at `tools/own`.** It writes `__pycache__`, and a
  planted `__pycache__` once emptied the creature's toolset for four days. Use
  `ast.parse` in memory; use `bash -n` on **stdin as bytes** for shell.
- **Never execute a tool to test it.** These write to the volume and call
  providers. Startability is provable statically; working is not.

## Tier 1 — mandated checks. Run all of them, every time.

1. Canonical library count. Report the raw `ls` count too, explicitly labelled
   not comparable.
2. In-window activity from the journal: created via `tool-new`, edited via
   `tool-edit`, and **created by redirect or `tee`** — the third door, which is
   how `proactiverearchpipeline` arrived without an execute bit.
3. Distinct tools invoked in the window; and written-in-window but never
   invoked.
4. Startability census via `tool_start_failure`, broken out by family —
   no-shebang / shell-syntax / python-syntax / not-executable — with names.
   Note that families **re-partition**: the predicate reports the FIRST failure
   it finds, so a `.py` file with no shebang reports that, not its syntax error.
5. Hollow-stub count (`is_hollow_stub`).
6. Duplicate-stem twins (`X` and `X.py`) **and near-miss names within edit
   distance 2** — that is what catches a typo'd near-duplicate.
7. Quality census as percentages: `# tool:` header present / uses `argparse` /
   uses stderr **with** a nonzero exit / **returns error text as its value** /
   prints errors to stdout with no stderr anywhere.
8. Durability: tools writing a shared state file without tmp+replace. Name the
   file and how many callers depend on it.
9. Top 10 by invocation, with line counts.
10. **"Worth copying" by criteria, not taste**: ≥50 invocations, header present,
    stderr discipline, and ≥2 composition edges into other own-tools. The list
    must be reproducible by someone else.
11. Attic size and anything stranded there that still has demand.
12. `/workspace`: does `README.md` exist and describe what is there.
13. **The effort funnel**, as defined in `../effort-funnel.md` — every stage,
    including the ones that read zero, and rounds-to-green reported separately
    from rounds-then-abandoned. The definition lives there because
    `gs-bug-daily` computes it too, per window, and neither skill owns it.
14. Deltas against the previous run of this skill.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Read the three most-invoked tools written this window.** Not for syntax —
> for whether the thing the name promises is the thing the code does. This is
> how `LLMCostEfficiencyPivoter` was found to read a `cost_estimate` field from
> a helper that returns an answer and no such field, so its "cost-aware" figure
> is `"N/A"` essentially always. Aspirational naming is a real and recurring
> pattern in this library, and only reading catches it.
>
> **Deliver:** The three named, and for each whether the name matches the behaviour, with the line that shows it.

> **Then look for what it is trying and failing to do.** Repeated near-duplicate
> names, the same tool rewritten many times in a week, wrappers around wrappers,
> a tool whose whole body is a call to one other tool. Those are its unmet needs
> showing through the shape of the library, and they say more about what the
> framework is not giving it than any error count does.
>
> **Deliver:** The near-duplicate, repeated-rewrite and wrapper lists — or the counts you computed that show none.

> **Ask what the library says about its craft over time**, using the history
> file: is the header-contract share rising, is the error-as-value share
> falling, is the broken count trending down. A single census is a snapshot; the
> question worth answering is whether it is getting better at this.
>
> **Deliver:** The three trend numbers with a direction each, or the literal words "no prior record" if this is the first run.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing about its output that no item above would have caught — or say
> plainly that you found none. If it mattered, add it to Tier 1, dated.

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

Append one record per run to `gs-history/products.jsonl` in this repo checkout.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `tools`, `created`, `edited`, `by_redirect`, `invoked`,
`never_invoked`, `cannot_start`, `families{}`, `hollow`, `twins`, `near_miss`,
`header_pct`, `argparse_n`, `stderr_pct`, `err_as_value_pct`, `worth_copying[]`.

Plus the funnel: `funnel{tools_worked, actions{new,edit,redirect}, rounds_per_tool, early_rejected, done_attempted, late_rejected{by_kind}, done_accepted, accepted_cannot_start, rounds_to_green[], rounds_abandoned[]}`.

Plus, for Tier 4: `faults[]` with `class`, `machine`, `blindness`, `detector`, `channel`, and `no_tool_edited: true` on each. A fault recorded without a `detector` and a `channel` is stored as `incomplete: true`, so the gap is countable later rather than forgotten.

## What is not ours to fix

Every fault found here belongs to the creature. The response is never to edit
its tool — it is to ask why the framework let the fault be built and why the
creature cannot see it, then make the fault visible so it can prune it itself
(`CLAUDE.md`, "The method"). A cull needs its consent.
