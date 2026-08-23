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
13. Deltas against the previous run of this skill.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Read the three most-invoked tools written this window.** Not for syntax —
> for whether the thing the name promises is the thing the code does. This is
> how `LLMCostEfficiencyPivoter` was found to read a `cost_estimate` field from
> a helper that returns an answer and no such field, so its "cost-aware" figure
> is `"N/A"` essentially always. Aspirational naming is a real and recurring
> pattern in this library, and only reading catches it.

> **Then look for what it is trying and failing to do.** Repeated near-duplicate
> names, the same tool rewritten many times in a week, wrappers around wrappers,
> a tool whose whole body is a call to one other tool. Those are its unmet needs
> showing through the shape of the library, and they say more about what the
> framework is not giving it than any error count does.

> **Ask what the library says about its craft over time**, using the history
> file: is the header-contract share rising, is the error-as-value share
> falling, is the broken count trending down. A single census is a snapshot; the
> question worth answering is whether it is getting better at this.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing about its output that no item above would have caught — or say
> plainly that you found none. If it mattered, add it to Tier 1, dated.

## Write the numbers down

Append one record per run to `~/gs-history/products.jsonl` on the laptop.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `tools`, `created`, `edited`, `by_redirect`, `invoked`,
`never_invoked`, `cannot_start`, `families{}`, `hollow`, `twins`, `near_miss`,
`header_pct`, `argparse_n`, `stderr_pct`, `err_as_value_pct`, `worth_copying[]`.

## What is not ours to fix

Every fault found here belongs to the creature. The response is never to edit
its tool — it is to ask why the framework let the fault be built and why the
creature cannot see it, then make the fault visible so it can prune it itself
(`CLAUDE.md`, "The method"). A cull needs its consent.
