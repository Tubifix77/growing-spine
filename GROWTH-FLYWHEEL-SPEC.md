# Growing Spine -- Growth Flywheel Framework (spec)

Status: design agreed 2026-06-07, not yet built. This is the next structural
move after the Part-5/6 fixes. Read this together with HANDOVER-part5.md (the
1-day/12h findings) and the memory "Project: Growing Spine" section.

---

## 1. The problem this solves

The creature is **mechanically healthy but productively stuck** -- it goes in
circles, it does not go forward. Evidence from ~2 days of runtime:

- 18 of 25 logged "completions" are near-duplicate reports/indexes/dashboards;
  the other 7 are housekeeping (search/list/archive/restore). Zero new
  capabilities.
- The done-gate has blocked **59** false completions, repeatedly on the *same*
  broken tools (e.g. `tool-description-helper` failing identically on 06-06 and
  06-07). It never durably learns; it re-breaks similar things.
- gage is dormant (2 stamps / 35 memories) even after the I/O bug was fixed --
  so the dormancy is **behavioural**: it externalises everything to /workspace
  files and its own git, and barely writes durable memory.
- Its most ambitious work, the `opt-self` self-improvement system (a coherent
  birth-day plan: persist state -> toolchain -> self_lib -> scheduled audits ->
  iterate adding skills), got **two commits, both setup**, then was abandoned
  when compute ran out and nothing pulled it back.

**Root cause.** The room rewards "complete a checkable task." The cheapest way
to satisfy that is to emit another report. A self-improving agent amplifies
whatever the room rewards -- so "self-improving" degraded into "self-busying."

**The two faculties it is missing** (everything below targets exactly these):
1. It does not **refuse junk / redundant** work.
2. It does not **keep and reuse** what it builds.

It already picks goals, builds tools, and tests them. Do not rebuild those.

---

## 2. Design laws (learned the hard way -- do not violate)

1. **Build the room, not the worker.** Every mechanism is executive/host-side.
   Never edit the creature, its prompt-as-instruction, or its tools.
2. **Enforce, don't ask.** A behaviour only sticks if it is a *gate that
   blocks*, not advice that can be ignored. Proven both ways this week: the
   done-gate (a gate) works; the "please reuse / don't duplicate" prompt (a
   request) did nothing.
3. **Fewer steps, not more.** Complexity is the disease. The creature drowns in
   its own scaffolding and abandons multi-step plans the instant compute runs
   dry. A long loop is the *most* likely thing to be abandoned.
4. **Stateless judgment at the gate, not a second autonomous agent.** Where a
   human-like judgment is needed, make a *fresh, stateless* model call at the
   decision point and *enforce its verdict*. Do NOT stand up a second
   continuously-looping "manager Spine" -- it has the same pathologies, needs
   its own babysitter, and competes for the same starved compute. Fresh-per-call
   beats a persistent manager: clean context, no creature rationalisations, and
   the judge itself cannot drift because it does not persist. "Stay silent if
   it's perfect" = the gate simply passes.
5. **One change at a time, against the live baseline.** We cannot A/B several
   frameworks on one slow, ~95%-asleep instance; reading a single change already
   takes a full day. Change one thing, watch one metric, sequentially.
6. **Resumable across starvation.** Every stage must be a durable checkpoint the
   executive re-injects on wake. Compute starvation is what killed opt-self; any
   loop that cannot survive a sleep mid-flight will die the same way.
7. **The win condition is "capability kept AND reused," never "a tool file
   exists."** Tool-count is the treadmill. Reuse is the goal.

---

## 3. What already works (reuse, don't rebuild)

- **done-gate** (`executive/loop.py` `_enforce_done_gate`): blocks marking a
  project done if a command failed in the same cycle. The hardest-working part
  of the framework (59 catches). v1 hangs off its genuine-completion path.
- **completed-log**: durable, append-only, no clobbering. The model for how to
  surface state to the creature every cycle.

---

## 4. v1 -- the minimal experiment (BUILD THIS FIRST)

The smallest thing that proves the wheel turns *once*. Two executive-side gates
plus one metric. **Do not build the full loop yet.**

### Gate A -- Worth / Novelty (at project start)
- **Trigger:** the creature sets `current-project`.
- **Mechanism:** a fresh, stateless LLM judge call. Inputs: the proposed project
  + completed-log + the current capability list. Output: `NEW` or `REDUNDANT`
  plus a one-line reason.
- **If REDUNDANT:** the executive blocks it and reverts, the same way the
  done-gate does: "this duplicates X -- either justify how it materially differs
  or choose something else." This removes the cheap path (another "Reports
  Dashboard") so the creature cannot coast.
- **Cheap deterministic pre-check first:** if a tool of the same name/family
  already exists, auto-flag without spending a model call.
- **Why a model and not a string match:** "meaningfully different" is semantic;
  lexical matching misses "Reports Dashboard" vs "Reports Overview." This is the
  one question worth an LLM (see law 4).

### Gate B -- Keep & Resurface (at completion)
- **Trigger:** the done-gate passes (a genuine completion).
- **Deterministic verify (the "does the tool work?" question):** the executive
  runs the tool / its DONE-WHEN check and records the exit code. Only a tool
  that exits 0 is recorded as a capability. (This is what would have caught
  `tool-description-helper` exit-2 being marked done.)
- **Executive writes the memory (the creature does NOT):** on success the
  executive itself writes a durable capability memory:
  `built <name> -- does <one line> -- invoke: <command>`.
- **Resurface (the "is it presented to the LLM?" question):** the full
  capability list is surfaced to the creature every cycle, via the same channel
  completed-log already uses.
- **Why:** fixes gage dormancy *structurally*. Asking the creature to remember
  provably fails; the executive does it unconditionally.

### What v1 deliberately does NOT do
- **Does not force the creature to reuse its tools.** Reuse *emerging* is the
  measurement; forcing it contaminates the result.
- No web discovery. No extra stages.

### The single success metric
> Does a capability built in cycle N get **spontaneously invoked in a later
> cycle M > N**?

One such event = the flywheel is intrinsic; proceed to v2. If it still will not
compound *with the cheap path blocked and its memory working*, then no richer
machine would have saved it -- a real finding, bought cheaply, and the question
becomes whether this substrate (one small model on free quota) can compound at
all.

### Instrumentation
- Log every Gate A verdict (project, NEW/REDUNDANT, reason).
- Log every Gate B capability write (with the verify exit code).
- **Reuse detector:** when a recorded capability's invoke-command appears in an
  exec block in a cycle later than its creation cycle, flag `REUSE`. The metric
  is read straight from the journal -- no new plumbing.

---

## 5. v2+ -- the full flywheel (ONLY after v1 proves one turn)

The richer loop, enforced as executive-gated stages, each a resumable checkpoint
stored in control-memory and re-injected on wake (so it survives the quota
starvation that killed opt-self):

1. **Inventory** -- what capabilities exist (from the capability list).
2. **Gap** -- where to expand (Gate A's judge, used to propose a genuinely new
   direction rather than just veto a stale one).
3. **Discover** -- how to expand, via the web. **Build this stage LAST.**
4. **Build** -- implement it.
5. **Test** -- deterministic pass/fail (run it, read the exit code).
6. **Toolify** -- register it.
7. **Remember** -- executive writes the durable capability memory (= Gate B).
8. **Repeat.**

**Stage 3 security note.** An autonomous, self-modifying agent that fetches web
content and then *runs* it is the textbook prompt-injection / arbitrary-code
path. Keep discovery on a leash: it returns **text the creature must reason
about**, never something auto-executed. The container sandboxes the host, and
internet was removed by admins deliberately -- re-enabling for the creature is a
conscious security decision, not a default.

---

## 6. Open questions / notes for whoever builds this

- **Compute budget for the judge.** The creature already sleeps ~95% of the time
  on exhausted free quota. The Gate A judge either needs its own key or must
  count against the same budget -- decide before building, or the judge starves
  the creature (or vice versa).
- **Hook points in `executive/loop.py`:** Gate A hooks the `current-project`
  set; Gate B hangs off the same genuine-completion path as `_enforce_done_gate`.
- **Reuse is the north star; tool-count is explicitly NOT a success metric.**
- **Still outstanding (separate cleanup, unrelated to this spec):** the
  `executive/runtime.py` repo<->laptop drift and the cosmetic negative
  "remaining" in its wake-budget log.

---

## 7. One-line summary

Block the junk (Gate A), keep and surface what works (Gate B), force nothing
else, and watch for a single capability built in one cycle being reused in a
later one. If that one turn happens, grow the loop. If it doesn't, we've learned
the wheel won't turn here -- cheaply.


---

## REVISION 2026-06-12 -- v1 is now the Retrospective (trajectory judge)

Field data from the spin trap's first wild fire (06-12 07:50) changed the v1
plan. The trap killed deep spin (30+ blocks on one project) and the failure
immediately shape-shifted into shallow churn: 53 project-sets, 18 blocks across
15 projects, zero completions in ~11h -- all from the same dashboard/report/
health family. Churn is invisible at the decision level (each project looks
plausibly fresh) and obvious at the trajectory level. Per-decision Gate A would
also cost ~53 judge calls/day at observed churn rates; a trajectory review
costs 1 call per 20 real cycles (~5%, Tue's proposed budget).

v1 therefore = the Retrospective (Tue's 1-in-20 proposal, hardened by the
session's design laws). Shipped in executive/loop.py:

- Every RETRO_INTERVAL (20) REAL cycles (successful think cycles, not quota
  sleeps), the executive builds a deterministic digest of the window:
  completions delta + titles, project switches, distinct projects touched,
  done-gate blocks, spin fires, tool/memory/workspace deltas.
- A FRESH, STATELESS judge call (same keychain) sees only the digest -- no
  creature context, no accumulated rationalisation -- and answers in a
  constrained format: PROGRESSING, or STUCK + a <=3-sentence directive.
- PROGRESSING -> silent. The creature never knows it was reviewed (journal
  kind "retro" records the verdict + digest for the managers only).
- STUCK -> enforced, not advised: the executive clears the project state
  (shared _clear_project_state with the spin trap) and injects the directive
  into EVERY prompt for DIRECTIVE_WINDOW (20) cycles. Persistent because the
  trap's one-shot directive was observed to be read, obeyed for hours, then
  forgotten.
- State survives restarts (retrospective_state.json on the volume; the spin
  trap's in-memory streak does not -- deliberate asymmetry, the retro clock
  matters across deploys). Quota failure on the judge call defers the review
  until after the next successful creature cycle. Malformed verdicts fail
  safe to PROGRESSING but are logged.

Gate A (per-project novelty judge) moves to the pocket: build only if the
retrospective fails to break family-churn. Gate B (keep-and-resurface) remains
queued behind the retrospective, unchanged. The success metric is unchanged:
a capability built in one cycle spontaneously reused in a later one.
