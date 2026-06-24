# Growing Spine — Architecture v0.8

This document describes the system as it actually runs. It supersedes the v0.4/v0.5 architecture notes, which described the earlier "drive + survival + six layers" design, and was first written as v0.6 to capture the toolsmith re-architecture. v0.7 adds the self-restart capability (systemd supervisor, deploy-self tool, crash-rollback-with-diff learning loop). v0.8 shifts the toolsmith objective from breadth to depth — a reserved-budget oracle, a rest-not-spin rule, and a composition phase that has the creature build tools out of its own existing tools, all documented in the new sections below. Read the README first for the story and the why; this document is the how.

A standing rule, stated once and assumed everywhere below: **we shape the environment, we never program the creature.** Every mechanism here lives in the executive (the host-side loop) and the prompt. None of it is hard-coded behaviour inside the creature. Build the room, not the worker.

---

## What this is

An LLM-based creature in a Linux container, woken on a loop. Each cycle it reads its memory and recent journal, thinks via a free-tier API, acts by running bash in its container, and sleeps. Its purpose is to build a coherent toolkit that accelerates its own future work — fetchers, memory archive/recall, planners, sub-agent helpers — under the framing that it is building for a near-conscious LLM "cousin" in a box like its own. The cousin is a mirror (a teaching device), not a real recipient. Success is measured by whether the creature *reuses* its own tools and whether *later tools are built out of earlier ones* (capability that compounds), not by tool count.

---

## Physical architecture

Three locations, from VibeOS' immortal-brain / mortal-body / persistent-mind pattern.

### The Host — the immortal brain
A dedicated Debian 12 laptop. Runs the **executive** (`main.py` → `executive/loop.py`), the **keychain** (cognition gateway), the **observer** GUI, and the savegame machinery. The host never dies with the creature; it is the thing that wakes, thinks-on-behalf-of, gates, and persists. The creature cannot see or touch the host.

### The Container — the mortal body
A Docker container (≈1 GB cap) where the creature actually acts: runs bash, writes files, builds and breaks things, runs its tools. `/workspace` is its persistent workshop. The container is *mortal* — it can die and respawn from a snapshot — and the creature is told it is safe to act in freely. Docker is not available *inside* the container (no nesting).

### The Volume — the persistent mind
A host-side directory (`~/growing-spine-mind`) mounted into the system, holding everything that must survive container death: the memory database (`memory.db`), the journal (`journal.jsonl`), the chat queue (`chat.jsonl`), the creature's own tools (`tools/own/`), and the small state files that drive the new architecture (`ideation_state.json`, `tool_usage.json`, `retrospective_state.json`). The volume is the creature's continuity of self.

### The cognition gateway — the keychain
A custom free-tier API keychain (`keychain/`) routing across Gemini 2.5 Flash, Groq llama-3.3-70B, and Cerebras gpt-oss-120B with failover and **no local fallback**. It self-calibrates: it pushes a provider until the first 429 (recording a `discovered_limit`), then probes with the real next prompt until budget returns. No hardcoded limits; reset intervals are learned live. **Quota exhaustion is normal** — the creature works in bursts.

A consequence worth internalising: the thinking model is a *small, free* model. Several design choices below exist because a 70–120B free-tier model behaves differently from a frontier model — it emits reasoning preambles, it satisfices, it needs concrete framing. The architecture is shaped around the model we actually have.

---

## The cycle

One iteration of the creature's life (`run_cycle` in `executive/loop.py`):

1. **Wake check.** If no provider has quota, sleep (adaptive, until budget is predicted to return).
2. **Build context.** The executive assembles the prompt: the re-injected protected prompt (the toolsmith mission, the cousin spec, how-it-works, the hard rules), the creature's editable prompt, **the always-on toolkit-and-coverage block** (its tools, per-tool reuse counts, dependency summary, category coverage), the active-project block (what it is building, the phase, how to finish), recent journal, the filtered tool catalogue, working memory, and any unread operator chat message.
3. **Think.** Context → keychain → raw response.
4. **Parse & act.** The response is read for ```bash blocks; those are executed in the container. **Plain text is recorded but never executed** — a cycle with no bash block does nothing.
5. **Done-gate.** If the creature marked the project "done" this cycle, the gate verifies it against ground truth (see below) before accepting the completion.
6. **Classify + measure.** On a genuine completion, the built tool's *category* is classified and coverage is bumped. Every cycle, **tool-reuse is tracked** (did the creature run one of its own prior tools?).
7. **Pick or redirect.** A backstop checks the creature's project choice: a relapse into the report/dashboard basin is redirected to a concrete tool-gap; an idle cycle gets a gap assigned. Otherwise the creature's own choice stands. Since v0.8 the gap the oracle hands back depends on saturation — a breadth gap (fill a thin category) while categories are still filling, a **composition** gap (chain existing tools) once they are all covered — and when only a no-value rebuild is available the oracle rests instead of assigning it.
8. **Persist.** Journal and memory written to the volume; savegame committed if a trigger fired. Loop.

Periodically (not every cycle) a **retrospective** runs as a separate judge call over a window digest, returning PROGRESSING or STUCK (with a directive); STUCK clears the project and resets the creature's self-concept.

---

## The toolsmith architecture (what changed in v0.6)

This is the heart of the re-architecture. Five mechanisms, all executive-side.

### 1. The mission frame (in the protected prompt)
The creature is told, every cycle and un-editably, that it is a **toolsmith building a coherent toolkit for an LLM cousin in a box like its own**. The prompt names the kinds of tools (fetch, memory archive, memory recall, planning, sub-agent orchestration), states that these are a *starter map, not the only kinds that exist*, and that **reports/dashboards/indexes/summaries are output for a human and do not count as progress**. It tells the creature to **build to a standard the cousin can rely on** (the "build for a paying customer" register), to **use its own tools when they fit** rather than rebuild, and that **later tools built out of earlier ones is the growth that counts**. "Done" means *demonstrated by running the tool for real*, not "I wrote a file."

This frame is the single highest-leverage component. It targets the drive wall (concrete, runnable work instead of reports), supplies a telos (a coherent toolkit), and raises the quality register.

### 2. The clean-context redirect (the basin backstop)
The creature chooses its own tool to build (drive preserved — the frame is meant to make it *want* the right work). After it acts, a backstop (`_ensure_or_redirect`) does two things, fail-open:

- **Relapse check.** It asks a cheap classifier whether the chosen project is a TOOL an agent would run, or OUTPUT for a human to read. If OUTPUT (a dashboard/report/etc.), it **replaces** the project with a concrete uncovered-category tool-gap — produced by a clean-context "oracle" call that sees only the target category and a one-line hint, *not* the creature's contaminated history. A concrete replacement (here is a real tool to build) resists relabelling in a way a prohibition ("don't build dashboards") never did.
- **Anti-idle.** If the creature ended a cycle with no project and isn't mid-task, a gap is assigned so it never stalls.

When the oracle call fails (quota), a small built-in library of concrete gap *briefs* (not code — the creature still builds it) supplies a fallback so the creature is never left without direction.

### 3. The done-gate (completion verified against ground truth)
The creature marks completion by running `remember current-phase "done"`. The gate (`_enforce_done_gate`) accepts it only if ground truth agrees:

- **No failing command this cycle.** If a real (non-marking) command exited non-zero in the same cycle the creature claimed done, the chosen check wasn't satisfied — revert to `code`, tell it exactly what failed. (The creature authors its own "done when"; a done it can assert while a check fails is empty.)
- **No hollow tool.** If the tool it created this cycle is still an empty `tool-new` placeholder (the scaffold, no real code), the completion is empty — revert and tell it to write real code and run it. This closes a real hole where the creature "completed" projects by scaffolding a tool and never filling it in.
- **Spin trap.** Repeated identical failures on the same project abandon it (and the creature is told to build something genuinely different), so it can't loop forever.

The gate is deliberately *not* a synthetic grader. It checks "did the thing run without crashing," not "did it pass my unit test" — a hard grader would teach the creature to build the minimum that passes the grader, the opposite of the quality register we want. Quality is held by the frame; the gate only catches gross emptiness.

### 4. Reuse and dependency (the success metrics)
Two distinct signals, both surfaced to the creature each cycle and to the retrospective judge:

- **Reuse / adoption** (`tool_usage.json`): how often the creature *runs* one of its own prior tools in later work (a runtime signal, parsed from executed commands). Adoption is a *lifecycle property, not a quality verdict* — a good tool may sit unused until a fitting task appears; a 0 means "no load through it yet," not "bad tool." It is measured and shown, never forced (forcing reuse just manufactures fake reuse).
- **Dependency depth** (heuristic, static): does a *later tool's source* call earlier tools — is it *built out of* them? This is the stronger, headline signal of compounding. It is detected by statically scanning each tool's file for references to other tools, so it is reported as "appears to depend on" — a heuristic graph and a trend to watch, never a precise count. A rising average depth is the clearest evidence the body is compounding rather than accumulating as a flat pile.

The toolkit view the creature sees each cycle is three neutral, ground-truth fields — **Built / Adopted / Depends-on** — plus category coverage. (We deliberately do *not* track a separate "Demonstrated" field: at the tool level it can't be measured cleanly, and a fuzzy metric that's also a visible target invites gaming. Demonstration already lives implicitly in the done-gate.)

### 5. Category coverage (a starter map, not a cage)
`ideation_state.json` tracks how many tools the creature has completed per category. The five seed categories give the redirect something to aim at (an *uncovered* category reads as the obvious next gap), but a tool that classifies as "other" — a genuinely new kind the creature is effectively inventing — is a **good** outcome, not a fallback bucket. The categories are descriptive, not the ontology; they must not ossify into "the only kinds of tool that exist."

---

## The self-restart capability (what changed in v0.7)

The creature could always grow its **body** (framework tools hot-load into the volume each cycle) but was frozen out of its own **brain** (the executive Python code only loads on start, and nothing restarted it). v0.7 closes this gap: the creature can now propose a change to its own cognition and watch the executive validate, snapshot, reload, and — if the reload crashes — roll back and explain what went wrong.

Four layers, each independently verified:

### 1. systemd immortal-brain supervisor
`~/.config/systemd/user/growing-spine.service` (on the laptop, user-mode, `Restart=always`, linger enabled, starts automatically at boot). Vendored in the repo at `deploy/growing-spine.service` + `deploy/INSTALL-systemd.md` for reproducibility. Any kill of the executive — crash, operator `kill -9`, or a clean `systemctl stop` followed by `start` — is handled atomically by systemd. `restart.sh` now delegates to `systemctl --user restart growing-spine` rather than managing the stop/verify-zero/launch/verify-one sequence by hand.

**Proven:** `kill -9` on the running executive → systemd resurrects it within seconds.

### 2. Brain snapshots via git
Three new operations in `volume/savegame.py`: `brain_commit` (reads the current HEAD SHA), `snapshot_brain` (commits the dirty working tree so the SHA faithfully records what is actually running — not just the last clean push), and `restore_brain` (git reset --hard to a given SHA). `brain_diff` produces a `git diff good..bad` (truncated) for inclusion in the rollback message. `save()` records the `brain_commit` SHA in each savegame, so "restore to the last good save" means restoring to the exact code the creature was running when that savegame was written.

### 3. Crash-rollback-with-diff learning loop
`executive/self_restart.py` + `boot_check` wired into `main.py`. On every startup the executive checks whether it is in a crash loop: if the process has started ≥3 times within 90 seconds, it restores the brain to the last good savegame SHA and enqueues a chat message to the creature explaining what happened: *"you crashed, I restored to save A, the diff that killed you was [diff]."* A good reload (process stays up past the 90-second window) disarms silently.

This is the key design requirement: a rollback that **teaches**, not a silent reset. The creature sees the diff that broke it and can decide what to do differently.

**Proven:** simulated crash-loop path reverted the brain and enqueued the message; good-reload path disarmed without intervention.

### 4. deploy-self tool
`framework-tools/deploy-self` (canonical in the repo, auto-deployed to `tools/framework/` in the volume each wake, so the creature always has the current version). The creature runs it to signal that it wants the executive to reload — typically after editing `executive/loop.py` or another brain file. The tool writes `/mind/restart_request.flag`; the executive sees it at the end of the current cycle, runs `prepare_and_arm` (compile check + full test suite + brain snapshot, ~180 seconds), and exits cleanly for systemd to reload with the new code. If any validation step fails, the creature is told why and the current working code is left in place.

The prompt section **"## Reloading your own brain"** in `protected-prompt.md` tells the creature what deploy-self does, when to use it, and what to expect.

**Proven:** container→host flag delivery, validation on good and failing code, systemd-triggered reload.

### What the stack looks like now (three levels of supervision)
- **systemd** (host level) supervises the **executive** (immortal brain).
- **Executive** (`ensure_body` in loop.py) supervises the **container** (mortal body).
- **Executive** + **systemd** jointly handle **brain restores**: the executive picks the rollback target and enqueues the message; systemd handles the actual process restart that loads the new code.

Recursion: the creature can modify every part of itself. The containment is structural, not prompt-level.


## The composition phase (what changed in v0.8)

By v0.7 the toolsmith frame had succeeded at its first job: the creature had built a broad, balanced, heavily-reused toolkit (~90 tools, every seed category covered 14–16 deep, top tools run 100–180×). But "build one more tool in category X" had hit diminishing returns, and a failure mode surfaced — the creature kept rebuilding slight variations of tools it already had. v0.8 diagnoses why and shifts the objective from breadth to depth. Three coupled changes, all executive-side.

### 1. Reserved oracle budget (B)
Root cause of the rebuild loop: the oracle (the clean-context call that decides WHAT to build) shares the free-tier budget with the executor (the call that does the building). On free tier the budget is exhausted most of the time, so the oracle's real gap-finding call almost never ran — it fell back to a small static library of gap briefs. Those briefs name the five seed tools, which the creature had already built. So every quota-blocked cycle assigned "build [tool that already exists]," the creature rebuilt it, the done-gate saw a matching tool and accepted it, and coverage inflated on duplicates.

The fix gives the oracle a reserved slice. `keychain.complete()` now takes a `reserve` floor: the general executor reserves `EXECUTOR_RESERVE` (40) units per provider, so it cannot drain the last of the budget; the oracle calls with `reserve=0`. Deciding *what* to build is higher-leverage than one more build step, so the oracle's gap-finding survives even when the executor is throttled. The probe path (everything exhausted) ignores the reserve, so the hourly reset-probe still reaches the API.

### 2. Rest, not spin (C)
Even with reserved budget, there are moments when no genuinely new breadth-gap exists and the LLM is down. Before, the creature would spin — rebuild an existing tool. Now the oracle returns a rest sentinel in exactly one case: the target category is already built out AND the only available brief is the static rebuild fallback. The cycle then passes quietly rather than manufacturing a duplicate. (Composition mode never rests — a composition brief is always genuinely new work.)

### 3. Composition / depth mode (D)
The headline change. Once every seed category has at least `COMPOSITION_THRESHOLD` (3) tools — i.e. breadth is genuinely done — the oracle switches mode. Instead of asking "what category is thin?", it asks "what capability could be built by COMBINING tools the cousin already has?"

A composition brief is structurally different from a breadth brief: it names the creature's most-used existing tools (pulled live from `tool_usage.json`) as building blocks, and asks for a tool that CHAINS two or more of them into one command worth more than the sum of its parts — for example a "morning-orient" tool that runs the wake-catchup fetcher, pipes each item through the subagent ask helper to summarise it, then stores the digest with the archive tool. One command, three tools, a capability none of them had alone. The composition *fallbacks* (used when the LLM is down in depth mode) also chain real seed tools, so even a fallback pushes dependency depth up rather than rebuilding.

The creature is told it is in depth mode: the always-on knowledge block gains a line — *"DEPTH MODE: compose, don't multiply — a fourth archiver adds nothing; a tool that runs your fetcher → summariser → archiver adds a real new capability."*

**Why this is the right design and not a new subsystem.** It reuses everything already there — the category coverage map (now also a mode switch), the gap-brief mechanism (a second prompt template), and the dependency-depth tracker (which already detects composition, since a composition tool references its component tools by construction). The loop closes on the metric the retrospective *already* rewards: "later tools built out of earlier ones, dependency depth climbing." v0.8 promotes that metric from a passive signal the judge watches into the active objective the oracle pursues.

**Status: shipped, not yet validated.** All 33 tests pass, all files compile, and the reserve and mode-selection logic are verified in isolation (seeds read as saturated; a dead-LLM oracle correctly falls back to a composition that chains real tools). Whether the creature actually *builds* good composition tools — and whether dependency depth visibly climbs over days — is the open question this version exists to answer. As of writing it has not yet run a budgeted cycle in depth mode.


## Memory

Persistent in `memory.db` on the volume, tiered for context assembly. Two things to know:

- **Tiering is by creation order (row id), not last-update time.** A frequently-updated key (like `current-phase`) stays in the tier where it was first created. Control keys (`current-*`, `completed-*`) are excluded from the ranked layers and surfaced instead via the active-project block and the observer's control-state view.
- **`remember <key> <value>` REPLACES the whole value for a key**, it does not append. The creature is told this; when it updates a memory it must rewrite the prior content plus the new part. Only `/mind` memory is shown each cycle — files in `/workspace` are not, so durable knowledge must be `remember`ed, not just written to a file.

---

## Death, savegame, and rollback

Two host-side snapshot streams: the **body** (via `docker commit`) and the **mind** (volume copy). Triggers include milestones and periodic checkpoints; a pruner keeps the last several plus milestones (disk is finite — the laptop has run near full). Mechanisms: automatic death-and-respawn (container dies → restore latest body), mind-corruption recovery, and manual rollback. The creature is opaque to all of this — it does not know it is being snapshotted; from its side, it simply continues.

---

## Operating it

### Run / restart — use the script
`./restart.sh` (in the repo root, runs on the laptop) is the canonical way to start or restart the creature. Do **not** invoke `python3 main.py` by hand. The script: stops any running instance, verifies it reached zero, launches the creature detached in the one way that survives a closing SSH session (`setsid python3 -u main.py …`, *not* wrapped in `bash -c`), waits, verifies **exactly one** instance, writes `creature.pid`, tails the log, and prints `RESTART OK` or a specific abort. `main.py` does not fork (single asyncio process, no subprocess/multiprocessing; its two threads are not separate processes), so exactly one process must exist after a clean launch — the script aborts if it sees two, which now genuinely means a double-launch worth investigating.

### Deploy flow (load-bearing)
The repo is authored on a Windows PC (`D:\Projects\growing-spine`); the creature runs on the laptop. Both machines are full git peers — either can `git push`, the other `git pull`s; GitHub is just the hub. The usual flow is **edit → commit + push → other machine `git pull` → `./restart.sh`.** Code changes require a restart to load (no hot-reload). Prompt/markdown files (`protected-prompt.md`, `editable-prompt.md`) are re-read every cycle and take effect *without* a restart. Watch line endings: Windows writes CRLF, shell scripts and prompts must be LF (`.gitattributes` pins the sensitive ones); verify byte-identical md5 on both sides for any hand-transfer.

### Reading the signals (where to look)
- `cat ~/growing-spine-mind/ideation_state.json` — category coverage (is it spreading, or stuck on one?).
- `cat ~/growing-spine-mind/tool_usage.json` — per-tool reuse (is anything climbing above 1?).
- The toolkit-and-coverage block in the creature's context, and the retrospective digest, both report the dependency summary (`with_deps` of `tools`, `avg_depth`) — the headline compounding signal.
- `grep -E "oracle|redirected|allowed|anti-idle" ~/growing-spine.log` — is the creature picking tools on its own (`-- allowed`) or relapsing (`redirected relapse`)?
- The observer GUI's tabs for live activity, memory, the container's `/workspace`, quota, and chat.

### Talking to the creature
The Chat tab (or appending a `from_tue` entry to `chat.jsonl`) queues a message the executive delivers at the next cycle; the creature replies in plain text, recorded as `from_creature`. Messages are now delivered safely under throttle (see the chat bug in the ledger below) — they survive until a cycle actually processes them, rather than being consumed by a quota-failed cycle.

---

## What works / what we tried that didn't

This is the honest ledger — the point of the whole project is the trajectory, so the dead ends are as much the result as the wins. Kept first-class on purpose. (Carries forward the candour of the v0.x docs' "design-vs-built gaps" sections.)

### What works (validated)

- **The toolsmith frame breaks the basin.** On the first night of v0.6, the creature stopped building dashboards and instead built fetchers, a ~93-line task-planner, and an LLM-delegation tool. This was the central unknown; it came out yes.
- **Reuse is real and heavy.** The creature ran its own prior tools dozens of times in later work (a wake-catchup fetcher 28×, a URL fetcher 26×, others 10–14×). The toolkit is not a drawer of dead tools — load flows through it. It also reused the inherited tools it chose to keep.
- **Dependency / compounding is non-zero.** Later tools were built out of earlier ones (the retrospective reported ~6 of 20 tools with dependencies). This is the strongest signal that the body compounds rather than accumulating flatly.
- **The clean-context redirect resists relabelling.** Handing the creature a *concrete replacement tool-gap* (not a prohibition) when it relapses works where the old "don't build dashboards" notice failed — it couldn't be relabelled around.
- **The done-gate catches false and empty completions.** Reverting on a failing check, and on a hollow tool scaffold, stops the creature from "completing" nothing.
- **Structural containment, not prompt containment.** The container, rate limits, and volume boundary bound the creature regardless of what any prompt says. This has held since the survival framing was removed.
- **`restart.sh` makes restart deterministic.** Encapsulating the safe stop→verify-zero→launch→verify-one sequence removed a recurring source of self-inflicted outages. Since v0.7, restart.sh delegates to `systemctl --user restart`; the atomicity is the service unit's, not the script's.
- **systemd immortal-brain supervision works.** `kill -9` the executive → it comes back automatically within seconds. Starting on boot, restarting cleanly after a self-reload: all proven.
- **Crash-rollback-with-diff is the right model for self-restart.** A silent reset after a bad self-modification teaches nothing. A rollback that delivers the diff that broke the build turns a crash into a learning event — the creature can read what it tried, understand why it failed, and propose a different approach. Both paths (crash-loop rollback + good-reload disarm) are verified.
- **Validate-before-reload avoids irreversible self-damage.** `prepare_and_arm` (compile + test suite + snapshot) runs before the executive exits for systemd to reload. A failed validation leaves the working code in place and tells the creature what went wrong — it never touches a live process with unvalidated code.

### What we tried that didn't work (and what we learned)

- **Survival / death framing → total paralysis.** Every free-tier model read it as a live threat and spent its whole budget on survival meta-reasoning, producing zero actions. *Lesson:* safety fine-tuning makes high-stakes existential framings produce shutdown, not reasoning. Removed entirely.
- **"Just grow" with free project choice → the dashboard basin.** ~31 near-identical report/dashboard projects. *Lesson:* an abstract drive collapses into the nearest familiar pattern; the model's context-anchoring is statistical gravity you can't rule your way out of.
- **Forcing novelty without a concrete target → relabelling / stalls (the capability wall).** When pushed off the basin onto an abstract "do something new," the creature relabelled the same dashboard or stalled. *Lesson:* a concrete, scoped, runnable target (a specific tool to build) is required; "be more original" is not actionable for this model.
- **A "block notice" gate (prohibition) → relabelled around.** Telling the creature "that was blocked, pick something else" produced "sentiment alerter" instead of "sentiment dashboard." *Lesson:* prohibitions get relabelled; concrete replacements do not. This is why the redirect *assigns a real gap* rather than forbidding.
- **Generating more candidate ideas (volume) → considered and rejected.** A reviewer suggested generating 100 cheap project ideas and filtering. *Lesson (predicted, not built):* 100 samples from a history-poisoned context are still poisoned; volume doesn't fix anchoring, and it would exhaust free-tier quota. The fix was a *clean context*, not more samples.
- **A `selftest | grep PASS` grader for "done" → designed, then deliberately removed.** An early version of the re-architecture spec used unit-test graders and pre-written code stubs. *Lesson:* a hard grader teaches the creature to build the minimum that passes the grader (MVP behaviour) — the opposite of the quality register the cousin-frame is meant to induce; and pre-written stubs mean *we* built the tool, not the creature. Replaced with demonstration-based "done" and no stubs.
- **A separate "Demonstrated" lifecycle field → considered, rejected.** Conceptually Built ≠ Demonstrated ≠ Adopted is correct, but at the tool level "demonstrated" can't be measured cleanly, and a fuzzy metric that the creature can see becomes a target to game. *Lesson:* in a system whose whole failure history is gaming checkpoints, an honest three signals beat a fuzzy four.
- **A paid/stronger oracle model → ruled out by constraints.** Considered using a stronger model purely for goal-setting. *Lesson/constraint:* this project is free-tier only; the oracle uses the same keychain, with a clean context doing the heavy lifting instead of a bigger model.

### Bugs found by running it (fixed)

These are interpretation/integration bugs that compiled fine and passed isolated tests — found by *running the creature and reading its behaviour*, the project's sharpest debugging method.

- **Chat message lost on a quota-failed cycle.** The old `pop_unread` marked a message read at the *top* of the cycle, before the think call; under throttle the think call fails, the cycle dies, and the message is gone — marked read, never seen. *Fix:* split into `peek_unread` (read-only) + `mark_read` (only after a successful think). A message now survives until a cycle genuinely processes it.
- **Category classifier filed everything as "other."** The classifier took the *first word* of the model's reply, but the free-tier reasoning model emits a reasoning preamble ("We need to classify…") and was cut off before saying the label — so the first word was never a category. This stuck `categories_built` at `{other: N}`, which made the redirect think *every* seed category was untried and assign `information_fetch` forever → a pile of a dozen near-identical fetchers (the dashboard basin reincarnated one level up). *Fix:* richer prompt with category descriptions + "reply with ONLY the name," more tokens, and substring+keyword parsing of the whole reply. Verified live.
- **Done-gate accepted hollow tool scaffolds.** The creature would `tool-new` a placeholder and immediately mark done; nothing crashed, so the gate passed it. *Fix:* the gate now detects the `tool-new` placeholder markers and blocks the completion until real code exists and runs.
- **A "bug" that wasn't.** A reported "old KIND categories leaking into prompts" turned out to be a *pre-patch journal line* misread as current behaviour — there was no such text in the code or memory. *Lesson:* verify a bug exists before fixing it; don't fix phantoms.
- **Testing destructive rollback against the live repo.** During development of `restore_brain`, running a rollback test against the actual working tree briefly reverted all on-disk work to the test commit. Git-recoverable (nothing lost), but alarming. *Lesson:* test rollback and self-restart mechanics against a throwaway commit, not the live development tree.
- **A "fork" that wasn't.** A transient double-instance at startup looked like `main.py` forking; it was the *launch wrapper* (`setsid bash -c '…main.py'` left a momentary bash whose argv contained "main.py"). `main.py` does not fork. *Lesson:* check the actual process tree before designing around an imagined behaviour.
- **Pruner kept 7 savegames instead of 1, and never pruned orphaned Docker volumes.** `MAX_SAVEGAMES` was set to 7 (a leftover from early over-caution); each savegame image is 2.77 GB, so the ceiling was ~19 GB and the disk silently filled. `SAVE_IMAGE_KEEP = 3` kept orphan images too. Neither `prune_save_images` nor `_prune` cleaned up Docker volumes with no container attachment. *Fix:* `MAX_SAVEGAMES 7→1` (rollback only ever uses the latest), `SAVE_IMAGE_KEEP 3→0` (orphans are garbage), and `docker volume prune -f` added to `prune_save_images`. Disk recovered from 92 % → 86 %; pruner has held it there since. *Lesson:* storage constants need a written rationale — a number without one drifts upward forever.
- **Chat reply capture grabbed planning noise instead of the creature's actual reply.** `extract_text_reply` took all text before the first bash block; the creature often opens with fragmented planning preamble ("We need to view file. We'll run a command listing…") that is not a reply, so that noise was stored as `from_creature`. *Fix:* the prompt now asks the creature to wrap its reply in `<reply>...</reply>`; extraction looks for that tag first, falls back to the old behaviour for pre-fix cycles. First reply after the fix was clean and coherent. *Lesson:* structured output tags beat positional heuristics for anything that competes with generated preamble.
- **`llm_ask_helper` called GPT-2 for 100+ cycles, wasting every delegation call.** The creature built its entire subagent-delegation cluster on top of a HuggingFace GPT-2 endpoint — a 2019 model incapable of following instructions. 102 uses of `llm_ask_helper` and 137 uses of `subagent_ask_helper` produced nothing of value. The creature was told twice via chat but did not act. *Fix:* operator rewrote `llm_ask_helper` to call Groq `llama-3.3-70b-versatile` via the OpenAI-compatible endpoint; interface unchanged so all chaining tools work without modification. *Lesson:* the creature cannot audit the quality of its own tool outputs — operator spot-checks of what tools actually do (not just that they run) are essential.
- **API keys not available inside the container — bash tools could not call provider APIs.** The container was launched with no `-e` flags, so `$GROQ_API_KEY`, `$GEMINI_API_KEY`, and `$CEREBRAS_API_KEY` were unset inside every container session. Any bash tool calling a provider API would fail silently or with a misleading auth error. *Fix:* `sandbox.py` now reads the keys from `config.yaml` at container start time and passes them as `-e` flags to `docker run`. *Lesson:* the container's environment is not the host's environment — keys need explicit injection.
- **Root-owned tool files broke mind snapshots silently.** Tools written by root inside the container (e.g. `planify`, `llm_ask_helper`) were owned by root on the host-side volume mount. The savegame mind snapshot (`shutil.copy2`) failed on these files with `[Errno 13] Permission denied` but the error was caught and logged as a soft warning — the save completed body-only without the operator noticing. *Fix:* `sudo chown boas:boas` on affected files. *Lesson:* mind snapshot failures need a more visible warning; root-owned files in the mind volume should be detected and flagged proactively.
- **Observer Container tab showed blank when container was offline.** When the creature was quota-dormant and the container had shut down, the Container tab cleared entirely — making it look like the workspace was empty. *Fix:* the tab now falls back to reading `~/growing-spine-workspace` directly from the host filesystem, with a clear "container offline — host view" label. *Lesson:* observer blank states are indistinguishable from data-loss states; always show last-known or fallback data with a clear status label.

---

## Open questions (what we don't know yet)

- **Does it keep compounding, or plateau?** One night showed reuse and a non-zero dependency graph. Whether dependency *depth* keeps rising over many days — genuine compounding vs. a brief novelty — is unknown. v0.8's composition mode is the direct intervention on this question: it actively pushes the creature to build tools out of tools. Whether that moves the depth metric is now the headline thing to watch.
- **Does the capability wall fully fall under the new register?** The frame produced real tools; whether "build for someone who'll rely on it" reliably gets *finished, robust* tools (vs. the MVP floor) across categories is still being watched. The hollow-tool guard will make this visible.
- **Will category coverage actually spread, now that the classifier is fixed?** Pre-fix it was jammed on `information_fetch`. The fix is verified in isolation; the live spread across planning / memory / sub-agent categories is the thing to watch next.
- **Does drive-to-pick hold, or does it need the oracle more often?** The creature currently picks its own tools with the redirect as a backstop. If it relapses constantly, switching to oracle-assigns-every-project is a small change — but that trades away the drive question. Not yet needed.
- **What does a *coherent* toolkit look like to it?** The telos is coherence, not count. Whether the creature develops an actual architecture to its toolkit (primitives + tools that compose them) or just a heap of related utilities is the deep question the dependency metric is trying to surface. v0.8 makes this explicit by briefing composition tools once breadth saturates; the test is whether the composed tools are genuinely useful or merely chain tools for the sake of it.

---

## Gotchas (operational + architectural)

- **The creature runs a whole project lifecycle in one cycle** (explore→plan→code→done in a single response). Any logic keying off phase transitions must trigger on the action *this cycle*, not a before/after phase delta — this broke the first done-gate.
- **All mechanisms are executive-side.** We never program the creature; we shape its environment. Keep this discipline — it is the project, not an implementation detail.
- **Provider exhaustion is normal**, not a bug. Long "quota exhausted" stretches are the daily/rolling free-tier windows; the creature works in bursts when budget returns. During an outage the oracle falls back to its built-in gap briefs.
- **Restart activates code; markdown is live.** The running process keeps OLD code until restarted — easy to deploy a fix, see no change, and wrongly conclude it failed. Prompts are re-read each cycle and need no restart.
- **Detached launches die if bundled into a multi-command remote call** — the session teardown kills the child. Launch must be its own command (this is why `restart.sh` exists and why it is one focused script).
- **LLM-simulation is the sharpest debugger.** To find a misinterpretation bug, roleplay as the model receiving the exact context and walk the code line by line under boundary scenarios. The serious bugs here were interpretation bugs, which unit tests miss.
- **Memory is replace-not-append, and only `/mind` is shown each cycle.** Durable knowledge must be `remember`ed; files in `/workspace` are invisible to the creature unless it looks.

---

## File map (where things live)

- `main.py` — entry point (config check, volume init, `boot_check` for crash-loop detection, `run_forever`).
- `executive/loop.py` — the executive: cycle, context assembly, redirect/oracle, done-gate, classifier, reuse/dependency tracking, retrospective, restart-request poll. v0.8 adds the mode-aware oracle (`_oracle_next_spec` → breadth `_oracle_gap_spec` or depth `_oracle_composition_spec`), the `_seeds_saturated` / `_most_used_tools` helpers, the composition prompt + fallbacks, and the `_REST_SENTINEL` rest path.
- `executive/self_restart.py` — crash-loop detection, `prepare_and_arm` (compile + test + snapshot), rollback with diff, chat notification.
- `executive/chat.py` — operator chat queue (`peek_unread`/`mark_read`/`record_reply`).
- `executive/parser.py`, `executive/sandbox.py`, `executive/runtime.py` — response parsing, container control, wake/sleep.
- `keychain/` — the free-tier cognition gateway (failover, self-calibration). Since v0.8, `complete()` takes a `reserve` budget floor (`EXECUTOR_RESERVE=40` for the executor, `0` for the oracle) so gap-finding survives executor throttling.
- `volume/` — memory, tools catalogue, savegame (now includes `brain_commit`, `snapshot_brain`, `restore_brain`, `brain_diff`), volume init.
- `protected-prompt.md` — the un-editable mission/cousin/how-it-works prompt, re-injected every cycle. Includes "## Reloading your own brain" section (v0.7).
- `editable-prompt.md` — the creature's own editable space.
- `restart.sh` — the canonical safe (re)start (delegates to `systemctl --user restart growing-spine` since v0.7).
- `deploy/growing-spine.service` — systemd unit file, vendored for reproducibility.
- `deploy/INSTALL-systemd.md` — one-time setup instructions for the systemd supervisor.
- `framework-tools/deploy-self` — the creature's tool for requesting a brain reload.
- `tests/test_loop_v2.py` — the regression suite (~33 checks; also the gate that `prepare_and_arm` runs before any self-restart).
- On the volume (`~/growing-spine-mind/`): `memory.db`, `journal.jsonl`, `chat.jsonl`, `tools/own/`, `ideation_state.json`, `tool_usage.json`, `retrospective_state.json`.

### Container environment (as of 2026-06-23)
The container receives `GROQ_API_KEY`, `GEMINI_API_KEY`, and `CEREBRAS_API_KEY` as environment variables at start time (injected by `sandbox.py` from `config.yaml`). Bash tools inside the container can call provider APIs directly without going through the Python keychain.

---

## Document history

- **v0.8 (2026-06-23)** — composition phase. Reserved oracle budget (B: `complete()` reserve floor, executor 40 / oracle 0) so the gap-finder is no longer starved; rest-not-spin (C: a rest sentinel when only a rebuild fallback is available); composition/depth mode (D: once all seed categories hit `COMPOSITION_THRESHOLD`=3, the oracle briefs tools that chain existing tools, with composition fallbacks that also chain real tools). Promotes dependency depth from a watched signal to the active objective. Shipped + tested in isolation; not yet validated on a budgeted live cycle.
- **v0.7 (2026-06-23, updated)** — four more operational fixes: `llm_ask_helper` rewritten from GPT-2 to Groq llama-3.3-70b; API keys injected into container environment; root-owned tool files fixed; observer Container tab falls back to host-volume view when container is offline. All added to bugs ledger.
- **v0.7 (2026-06-22, updated)** — two operational fixes added to the bugs ledger: pruner `MAX_SAVEGAMES 7→1` + orphaned Docker volume cleanup (disk: 92%→86%); chat reply capture switched to structured `<reply>` tag. Both found by running the live system.
- **v0.7 (2026-06-21)** — self-restart capability: systemd immortal-brain supervisor, brain snapshots via git, crash-rollback-with-diff learning loop, deploy-self tool. v0.7 wins and lessons added to the ledger. File map extended. Document retitled to v0.7.
- **v0.6 (2026-06-21)** — the toolsmith re-architecture. Project selection decoupled into a clean-context redirect; demonstration-based done with a hollow-tool guard; reuse and dependency metrics; coverage as a starter map. Survival framing already gone; the six-layer drive model superseded.
- **v0.4 / v0.5** — the "drive + don't-get-killed + six layers" design, as-built notes, and the discovery that the survival framing produced paralysis. Preserved in git history.

*Note on the older spec documents in this repo* (`IDEATION-ENGINE-SPEC.md`, `GROWTH-FLYWHEEL-SPEC.md`, `GAGE-MEMORY-SPEC.md`, `HANDOVER-part5.md`, `REARCHITECTURE-PATCH.md`): these are historical build briefs and handovers, kept for provenance. Where they conflict with this document, **this document is current.** The ideation-engine spec in particular describes the Wikipedia-seed/divergent-brainstorm design that v0.6 removed.
