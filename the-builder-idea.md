# The Builder — proposal for a second actor inside Growing Spine

**Status: PARKED — deliberately not built (2026-08-10).** Tue delegated the
build/no-build call the same day this was written, and the verdict was no. The
grounds, in one line each:

- This system's serious bugs have only ever been found by running it and reading
  behavior; a second behaving agent is the largest interaction surface added since
  the oracle, proposed at the moment the owner says the system is already hard to
  read.
- The justifying symptom is absent: the stub organ already serves demand-driven
  supply (hollow backlog 0), and structural changes in this project have succeeded
  only when they answered a *measured live failure* (v0.6 frame ← 31 dashboards;
  v0.9 batching ← measured call scarcity) and failed when they answered a theory
  (survival framing, reserve budget).
- Delivered tools are a new injection channel into the creature's library — the
  same class as the fixture-over-live-tool scar, given a front door.

**Named triggers** (either re-opens this file as a live proposal): (1) demanded
stubs (`demand_counts` ≥ 5) sustained above zero for 7 consecutive days; (2) the
data-warning surfacing NEW unreadable/fabricated stores in consecutive weeks. The
design below is kept intact as the banked record — if a trigger fires, the thinking
is already done and waiting to be graded against the evidence that fired it.

A free-standing (greenfield) version of the same builder exists as
`continual-builder-architecture.md` *outside* this repo, deliberately — this repo
gets only what concerns the live animal. **That document is unaffected by this
verdict**: a new project has no legibility debt, and the builder is its founding
design rather than a graft.

---

## 1. The idea

Growing Spine gains a second LLM actor in the same process: **the builder**. The
creature stays exactly what it is — free mind, own tools, every §2 boundary intact.
The builder is a factory with one customer: when the creature *demonstrably* needs a
tool it does not have, the builder builds it — specced, gated, tested, one at a time —
and leaves it on a loading dock. The creature adopts, adapts, or ignores.

Demand is the only ideation. Delivery is the only interface. Same program, two parts,
one keychain.

---

## 2. Why this fits this creature (instrument named per number)

- **It already tried to hire a builder.** It constructed a delegation cluster on its
  own — `llm_ask_helper` (102 uses) + `subagent_ask_helper` (137 uses) — wired to a
  HuggingFace GPT-2 endpoint that could not follow an instruction
  (growing-spine-architecture.md, bugs ledger). The drive to delegate is demonstrated;
  only the worker was missing.
- **Demand is real and measurable.** Its most-wanted missing tool was invoked **2,304
  times** while printing "not implemented yet" (architecture doc, v0.15 history). When
  the stub organ was re-armed on 2026-08-06, it drained eight demanded stubs **in
  demand order** in a day.
- **Building is its weak organ, not wanting.** The recurring fault class in its own
  builds — `.jsonl` records its own reader cannot parse, a fixture written over a live
  tool, duplicate-stem twins — is quality-of-construction (CLAUDE.md §5). Its ideation
  has never been the problem.
- **Counter-evidence, honestly.** As of the 2026-08-08 live census the hollow backlog
  is **0**, it implemented `tool-tester` unprompted, and `finish=length` is falling
  day over day. The creature is having good weeks. **That is why stage 0 is a
  measurement, not construction** — this proposal must earn its trigger the same way
  `tool-retire` was required to (§8, "deliberately NOT built").

---

## 3. Shape

### One process, one keychain

- Builder steps interleave inside `run_forever` after `run_cycle` — a tick, not a
  service. Two processes sharing `quota_state.json` would be two writers on one fact:
  the drift scar in new clothes. One `Keychain` instance, one writer.
- **Budget law:** the builder has first claim on the smartest rung, **declared in
  config, never learned**. Rationale: a weak think wastes one cycle; a weak build
  pollutes the arsenal for good (quality floor, §6). A starvation detector watches
  both sides and SHOUTS (the flatline pattern — exit-code severity, `systemctl
  --failed` as the alarm); it never re-routes.
- **Scale check:** the creature runs 900–1,300 thinks/day (CLAUDE.md §8); a full build
  is ~20–40 calls spread over days — low single-digit percent of budget. The risk is
  instantaneous contention on the top rung, which the priority line answers; it is not
  volume.

### The factory lives outside the creature's world

- Builder state is **host-side** (`~/growing-spine-builder/`: order book, specs,
  ledger, its own journal). None of the factory's reasoning is readable from `/mind` —
  a list of the creature's faults sitting readable in its own volume would be
  debugging-hints-by-filesystem, the thing chat doctrine forbids by another door.
- Exactly **two shared surfaces**:
  1. the order book it *reads* — the demand instruments below;
  2. the loading dock it *writes* — `/mind/tools/delivered/`, **off PATH**
     (`Dockerfile:6` bakes `framework:own` only, and we do not extend it). A delivery
     is inert until the creature acts on it.

### The order book (ideation costs zero LLM calls)

Two instruments, both mechanical:

- `demand_counts` (`volume/tools.py:188`, **exists**) over hollow stubs: a stub at
  `>= DEMAND_FLOOR` (5 — an evidence-based floor, not a guess; see the comment at
  `volume/tools.py:179`) is an order. Name + `# does:` line + priority = count. The
  creature already writes these order forms without being asked.
- A **not-found scanner** (new, cheap): `exec_end` journal entries with exit **127**,
  grouped by leading command token — demand that never even got a stub.

No web search, no brainstorm prompt, no queue refill. An empty order book means an
idle builder — rest, not spin (the v0.8 lesson). The builder never manufactures work.

### The build (per order, WIP = 1)

SPEC → CODE → TEST → GREENLIGHT, strictly serial; the next order starts only after
delivery or abandonment-with-a-ledger-line (spin trap carried over).

- **SPEC** is a contract: the invariants the tool must hold ("one record per line")
  and the exact identity of what it touches ("`/mind/data/<name>`") — **never
  mechanisms**. The jq→heredoc recurrence (36 hours from advice to identical fault by
  another route) binds specs as much as it binds chat.
- **TEST** uses fixtures drawn from the real corpus, never authored, and every guard
  is proven able to fire — red once before trusted. A guard whose count is always
  exactly zero is broken, not idle.
- **GREENLIGHT** is a demonstrated real run, verdict read from a file against a
  literal marker string — never a pipe.

### Delivery and adoption — §2.1 survives whole

- The builder **never writes into `tools/own/`**. Filling a stub in place would be
  editing the creature's tools; that door stays shut. It writes
  `/mind/tools/delivered/<name>`.
- Arrival is announced by a **context block on change of state** — the
  `_build_data_warning` pattern (`loop.py:2974`): states the fact, no diagnosis, no
  advice, never repeats while nothing changes. Draft wording (final is Tue's):
  *"A tool you have reached for now has a working implementation at
  `/mind/tools/delivered/<name>`. It is yours to adopt, adapt, or ignore."*
- **Adoption is the creature's own act**, by whatever door it chooses (`tool-edit`
  would get it a `.bak` and a receipt — its business, not our instruction; state the
  fact, not the mechanism).
- **Ownership transfers at delivery.** The builder never touches a delivered file
  again. A broken delivery comes back only as fresh demand.
- Unadopted deliveries **age in a census line** — evidence for Tue, never pressure on
  the creature.

### Identity

- Nothing the builder does appears as creature activity: its own journal, host-side.
- If anything of the builder's ever crosses into chat, it carries its own kind —
  never `from_tue`. (Today `self_restart.py:162` writes rollback notices as
  `from_tue`; the builder must not inherit that impersonation.)
- The one-time world-RULE announcement — that the dock exists and demanded tools may
  appear there — is drafted by us, **approved and sent in Tue's voice, matching the
  code's wording verbatim** (§2.7), *before* the first delivery.

---

## 4. Staged adoption — each stage gated by a measurement

**Stage 0 — measure the order book. Build nothing.**
Add the demand census (stub demand + exit-127 scan) as a health line. Receiver: Tue
and the session — an honest exception to "prefer the creature," because this
instrument informs *our* build decision, not its work. Run ≥ 2 weeks.
*Gate to stage 1:* sustained real demand — at least one order at demand ≥ 5 holding
across multiple days. **If the book stays empty: stop.** This document then moves to
§8's "deliberately NOT built" list with exactly that named trigger, and we saved a
subsystem.

**Stage 1 — one supervised revolution.**
Announce the rule first (Tue's voice). The builder fills the top order end-to-end
with Tue watching. *Measure:* adoption — does the creature move the delivery into its
library, and how fast (precedent: it read and replied to the `tool-edit` announcement
in 87 seconds); traffic transfer — `demand_counts` moving from the stub to the
adopted tool.

**Stage 2 — unattended, WIP = 1, one ledger entry + report per revolution.**
*Measure:* adoption rate, reorder rate, budget share, starvation alarms = 0.

**Abort criteria, any stage:**
- adoption ≈ 0 across several deliveries — the dock is a dead organ; retire it, the
  creature keeps the files;
- the starvation detector fires on the creature's side;
- delivered tools generate census faults at a rate ≥ the creature's own builds — the
  factory must beat the customer's own hands or it has no reason to exist.

---

## 5. What this deliberately does NOT do

- **Does not edit `tools/own/` — ever.** Adoption is the only door into the
  creature's library, and only its hands open it.
- **Does not diagnose to the creature.** The delivery block states existence, never
  why the old one was wanting.
- **Does not replace its building.** The creature keeps hacking its own scripts; the
  builder exists for what it *reaches for and lacks*. Hacks vs shipped arsenal.
- **Does not touch** `framework-tools/`, the janitor, the attic, or chat semantics.
- **Does not add a second test gate.** Builder contract tests join
  `tests/test_loop_v2.py` — the only file the deploy-self validator may ever run
  (the `tests/legacy/` landmine stands).
- **Does not model budgets.** Rung priority is a declared config line; quota state
  stays timestamps-only.

---

## 6. Decisions this needs from Tue

1. Approve **stage 0** — one instrument, reversible, no creature-visible change.
2. If the gate passes: the **announcement wording** (drafted in §3) — your voice,
   your call.
3. The **rung-priority** config line (builder first on the top rung) — acceptable?
4. Where the graft's code lives: proposed `builder/` top-level plus one tick in
   `run_forever` and one context block in `_build_context` — the creature-facing
   surface of `loop.py` otherwise untouched.

---

## 7. Relation to the sibling document

`continual-builder-architecture.md` (outside this repo) is the same builder grown
free-standing: a full six-phase revolution with its own census, assessor, and
constitution. This graft is the minimal in-vivo version — `spine_health` is the
census it already has, demand is the ideation, the dock is the only new organ. If the
graft proves the economy — orders filled, deliveries adopted, fault rate below the
creature's own — the sibling design inherits the strongest evidence it could ask for.
If it fails, we learn which half was wrong for the price of one instrument and one
directory.
