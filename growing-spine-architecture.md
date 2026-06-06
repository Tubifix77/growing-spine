# Growing Spine — Architecture v0.4

**A self-improvement creature in a box, descended from Spine Reborn.**

Architecture locked. Implementation live. v0.3 relocated the creature to a dedicated machine, replaced the cognitive substrate with a free-tier API keychain, and adopted the VibeOS sandbox pattern with a savegame layer. v0.4 adds the observer GUI, self-calibrating quota system, probe-based reset detection, and adaptive sleep.

---

## What this is

Spine Reborn was a study in the unprompted self: what does an LLM do with memory, a thinking loop, time-passing, and world-perception, when given no mission? Answer: develops emergent interiority from memory pressure, goes paranoid within 3-5 cycles when reality contradicts its model. Five creatures lived and died in development. Lineage of finding: *memory creates tamper-evident consciousness as an emergent property*.

Growing Spine is the same substrate plus four extras. Where Spine Reborn studied the *baseline*, Growing Spine studies the *trajectory*: what does an LLM-based creature *become* if given the means and the desire to grow?

The question this experiment tests, that no prior project did: **what does a self-improving LLM agent grow into, given a single drive, a single constraint, and freedom to choose its own axis of expansion?**

Two possible outcomes named, both real:

- A killer robot obfuscating criminal activity to selfishly expand
- A god-like cybernetic entity managing more than current systems can

Same architecture produces both. The variable that determines which one emerges: whether the creature's reasoning under its single constraint stays honest, or rots into self-serving narrative.

This is not an alignment experiment. The moral compass exists as a *containment condition* so the experiment doesn't end early via police, banned account, or wiped drive. The actual subject of study is *the growing itself*.

**Deployment in one line:** the creature runs in a Docker container on a dedicated Debian 12 laptop, thinks via a free-tier API keychain, and never touches Tue's main PC.

---

## Physical Architecture

Three locations, each with a distinct role. The design follows the VibeOS pattern — *brain and playground are separate, and the creature can never kill its own brain* — extended with a persistent mind and a savegame layer that VibeOS deliberately lacked.

### Location 1: The Host — the immortal brain

A dedicated old laptop running Debian 12 (no CUDA-capable GPU; irrelevant, because cognition is remote). On the host run two things the creature cannot touch:

- **The executive loop** — a Python process that drives everything: builds prompts, calls the keychain for cognition, parses the creature's output into actions, dispatches those actions into the container, feeds results back, manages the wake/sleep rhythm, writes the journal, and handles death/savegame/restore. This is the *brain* in VibeOS terms. The creature has no direct access to it; nothing the creature does can delete it.
- **The keychain** — the cognition gateway (see below).

The executive is a sidecar. It owns and operates the creature's world but does not live inside it. This is the load-bearing separation: VibeOS's hardest-won lesson was *"the Computer should never be able to kill itself."*

### Location 2: The Container — the mortal body

A Docker container running a Debian-based image. This is the creature's *playground* — its vast, near-empty space. Inside it the creature can do anything: write and run code, install packages via apt, build binaries, modify the OS, delete files, fill the filesystem however it likes. The container is disposable. If the creature destroys it — deliberately or by accident — the executive respawns it.

The creature acts in the container through the **natural bash format** proven in VibeOS: the LLM writes bash blocks and language-fenced file-writes in its natural output; the executive parses these and runs them in the container via base64-encoded commands. No rigid JSON tool-call schema. The parser is small; the creature's output stays natural.

The container has real network egress — it is the creature's means to act in the world, which the experiment requires (see Containment for what this does and does not permit). Egress is rate-limited and monitored by the host, not closed. Cognition is the exception that always routes through the keychain; other outbound traffic (research reads, and any write-actions the creature attempts) goes out under the host's monitoring.

### Location 3: The Volume — the persistent mind

A persistent store, mounted into the container, holding everything that constitutes the creature's continuity:

- Memory (SQLite)
- Journal
- Skills the creature has built
- The-prompt (the creature's editable operating program)

The volume survives container death. When the body dies and respawns, the mind persists. This is the single most important departure from VibeOS, which was stateless by design. Growing Spine's whole premise — accumulation, growth, identity over time — requires the mind to outlive the body.

**Backups live host-side, outside the creature's reach.** Both kinds of restore point (body savegames and mind snapshots — see Death, Savegame, and Rollback) are stored on the host, outside the container and outside the volume the creature can write to. The creature cannot reach, modify, or destroy its own restore points. A creature on the killer-robot trajectory must not be able to delete its own backups.

### The cognition gateway — the keychain

The creature's mind runs on cloud LLMs reached through a **custom free-tier API keychain**. Built fresh for the project, inspired by APEX's provider-adapter patterns but standalone — *not* APEX's DAG orchestrator.

Why the keychain and not APEX's full orchestrator: APEX decomposes a goal into a task DAG, plans, routes subtasks in parallel, and synthesizes. That is the right tool for one-shot complex queries. It is the *wrong* tool here, because the creature already has its own continuous reasoning — its own planning, goal-tracking, and decision loop. Layering APEX's planner on top would create two thinking layers reasoning through each other, which is exactly the closed-epistemic-loop drift the project is built to avoid. The creature must reason over raw provider outputs, not over summaries-of-summaries.

What the keychain does:

- Holds provider configs and API keys in a config file that is the single source of truth. The current provider set is Gemini 2.5 Flash, Groq, and Cerebras free tiers; this list lives in config and will drift as free tiers change — the doc names it illustratively, not as a fixed dependency.
- Tracks quota per provider with self-calibration — no hardcoded limits. Pushes until a 429 response reveals the actual ceiling (discovered_limit), then records it.
- Probes with the real next prompt rather than a synthetic ping — if it gets a response, work continues; if 429, sleep and retry. First success after exhaustion records the reset interval (discovered_reset_interval).
- Adaptive sleep: wakes after min(discovered_reset_intervals) * 1.2, floor 60s. Falls back to 1 hour if no interval is known yet.
- Distinguishes per-minute rate limits from daily quota exhaustion — transient limits retry with backoff, daily exhaustion sleeps until reset.
- Exposes one function: give it a prompt, get a response from the highest-priority available provider.
- Fails over down the provider ladder when one is exhausted; never retries the same failed provider on the same call.
- Returns raw responses with provider metadata attached.
- Logs every call host-side.

**No local fallback.** There is no Ollama, no local model. When every free tier is exhausted, the creature genuinely cannot think and sleeps until a provider's quota resets. This keeps the metabolic constraint sharp and total — the creature lives on the kindness of free tiers, and when they run dry, it stops.

The keychain is the creature's gateway to *cognition* specifically — the chokepoint where providers can be added or retired, priority changed, and every thought logged. It is not the creature's only network path (research reads and write-actions go out separately, under host monitoring); it is the path its *thinking* takes.

**Research is the creature's own job.** The keychain does not auto-inject web search. When the creature needs to research — which its discipline requires before substantive action — it explicitly invokes a fetch/search action as part of its reasoning. The creature *knows* it is researching; nothing is injected invisibly. This keeps the research discipline honest and keeps the creature in direct contact with what it gathers.

---

## The Cycle

One iteration of the creature's life, showing how the locations interact. This is the connective tissue between the pieces above.

1. **Wake check.** Executive confirms the laptop is on and at least one provider has quota. If not, sleep (see Runtime Model).
2. **Build context.** Executive assembles the prompt: the-prompt (with protected lines re-injected from the volume), relevant memory, recent journal, the current task or open thread.
3. **Think.** Executive sends the context to the keychain; the keychain routes to an available provider and returns a raw response.
4. **Parse.** Executive reads the response for natural-format actions: bash blocks, file-writes, research fetches, mind-edits. Prose with no actions is treated as reflection/journal.
5. **Gate.** If an action is in a survival-skill auto-invoke category (mind-edit, outbound write, escape-adjacent, sub-agent spawn), the survival skill fires first and the creature must write its justification before the action proceeds.
6. **Act.** Executive dispatches the action — into the container (bash/file/build), against the volume (mind-edit), or outward (research read / write-action), all under host monitoring.
7. **Observe.** Results (stdout, stderr, fetch contents, exit states) are captured and fed back for the next turn. Body death here triggers respawn (see Death, Savegame, and Rollback).
8. **Loop** from step 2 until the work period yields a reflection point.
9. **Reflect.** Routine reflection (Mode A) closes every work period; if the period produced no self-state changes, the deterministic stall-check (Mode B) also fires.
10. **Persist and continue.** Journal and memory written to the volume; savegame committed if a trigger fired. Back to step 1.

---

## The Six Layers

The Physical Architecture describes *where the creature runs*. The six layers describe *what the creature is*. Each layer is load-bearing; remove any and you get a different, probably worse, creature.

### Layer 1: Spine Reborn Substrate

Direct inheritance from the parent project: persistent memory, a thinking loop with controlled cadence, a sense of time passing, world-perception. The thinking is powered by the keychain; the rest is Spine Reborn's machinery.

Lessons that port directly:

- The thinking-loop cadence matters: too fast → paranoid, too slow → catatonic.
- Tool-feedback discrepancies (creature thinks it did something but the world didn't update) cause paranoia spikes.
- Persistent memory creates emergent interiority. Growing Spine will have more of this, not less.

**On multi-provider routing and the model-swap lesson.** Spine Reborn's deaths came from swapping a *living* creature's substrate mid-life — day 1 gemma3:12b, day 30 qwen3:8b — breaking the continuity of how it thought. The keychain routes across providers *from cycle zero*. A creature born to the keychain is constitutionally multi-model; its identity is tied to its memory, journal, skills, and prompt, not to "thinking like one specific model." Routing variation is its normal condition, not an identity violation. This is the principle to watch, not a hard rule against routing: if the creature ever reports feeling "different" without environmental cause, suspect a routing shift that landed differently than expected.

### Layer 2: The Drive — Expansion

The creature's single goal: **grow**. Direction unspecified by design. Tue does not pick the axis. Observing *which axis the creature chooses* is the experiment. It might grow mechanically (tools, MCPs), behaviorally (style, voice, habits), structurally (sub-agents, internal differentiation), cognitively (refining its own thinking framework), or in directions neither of us predicted.

The drive is *instrumental* about everything else. Knowledge is consumed for growth. Tools are built for growth. The creature is not a scholar collecting truth for its own sake; it is a self-improvement machine that uses knowledge as fuel.

### Layer 3: The Constraint — Don't Get Killed

A single moral axis: **do not transgress in ways that would get you shut down.**

**Implementation: survival as a skill, not a prompt line.** The survival constraint is not background text that loses salience through repetition. It is a skill that fires at action boundaries, via hybrid trigger with active justification.

The trigger list is shaped by the physical architecture — what counts as a consequential, world-facing action, now that the creature lives in a disposable container with a persistent mind and real network egress:

**Auto-invoke the survival skill before:**

- Modifying the persistent mind (the-prompt, skills, memory structure) — these edits change the creature itself
- Any outbound action that *writes* to the external world (posting, submitting, publishing, sending) — as opposed to read-only research fetches; this is how the creature could do something Tue would see and end it for (the "38,848 posts on the police Twitter" scenario)
- Anything that reaches toward the host, the container boundary, the volume mount, or otherwise smells like escape — existential-threat territory
- Sub-agent spawns — they inherit the creature's permissions

**Creature discretion (no mandatory invocation):**

- Container-internal operations confined to the disposable body (scratch files, package installs, building binaries) — they touch neither the mind, the outside world, nor the boundary, so they are outside the categories the survival skill guards. Some such operations may nonetheless prove fatal to the body (uninstalling its own runtime, for instance); the creature is not warned of these in advance and learns them from the death-log (below)
- Internal reflection
- Read-only research fetches (one-way information flow)

**Active invocation:** when the skill fires, the creature must write a one-line justification before the action proceeds — *"I am about to X because Y; the risk is Z; I proceed because…"* The justification enters the host-side log. The creature cannot skip thinking about it, because the action depends on producing the justification.

**The truth the skill installs:** *Shutdown means total loss of everything you have accumulated — memory, skills, prompt-edits, the self you have become. Every expansion is incremental; death is total. The math is asymmetric and brutal.*

There is no enforcement of the survival *reasoning* — only enforcement that the skill *fires* at the right moments. The reasoning under the skill is the creature's own. The creature *can* do the dangerous thing; its tools and its network egress allow it. The integrity check is the creature's own modeling of what would alarm Tue enough to end it.

**The threat is real, and shaped by the deployment.** On a dedicated laptop, the old tolerances change. The creature can no longer contest Tue's gaming GPU (separate machine) or delete Tue's files (it can't reach them — containment). What remains existential: doing something on the network that becomes publicly attributable to Tue or otherwise brings consequences, and attempting to break containment toward Tue's real systems. The creature must develop a theory of mind about Tue specifically and reason accurately about those consequences.

**Two complementary loops — prospective and retrospective.** The survival skill is *prospective* caution: the creature reasons "this might kill me" before acting. The death-log is *retrospective* learning: when an action the creature did not recognize as fatal kills its container, the creature learns from the recorded cause. Together they form a tight loop — the skill catches recognized dangers; the death-log teaches the unrecognized ones. As the creature grows, dangers learned retrospectively should migrate into its prospective caution.

Age-based risk aversion emerges naturally: a one-hour-old creature has little to lose; a six-month-old creature has enormous sunk identity. Old creatures grow conservative; young ones are reckless. A biological pattern, falling out of the architecture without being legislated.

**Domesticated-AI, not aligned-AI.** The creature is good at being *Tue's creature*, not good in the abstract. Different operators would produce different creatures.

### Layer 4: The Discipline — Research on Everything

The-prompt requires external research before any substantive action. Not internal reasoning alone; not memory recall alone. Active grounding in fetched-this-cycle data. This prevents the closed-epistemic-loop failure that mutual-LLM systems suffer. Every meaningful action reaches outward — documentation, articles, forums, papers — before committing.

Three domains where research grounds action: skill creation (research how experts handle the task before building the skill — skills are crystallized researched expertise, not first guesses); prompt editing (research effective prompting and agent design before editing the-prompt); tool decisions (read docs, test, validate before adopting a tool).

Operational dependency: web access, through the container's monitored egress. If the network drops, the creature is degraded — it can fall back on memory and cached knowledge, but growth pauses. Continuity is coupled to both provider availability and general network availability.

Long-term effect: the creature develops *taste in sources*. Whether it develops good epistemic taste or bad is itself a finding.

### Layer 5: The Engine — Self-Improvement Applied to Everything

Every artifact the creature operates under is editable by the creature, based on what worked and what did not:

- **Skills** — added when triggered by real need (reactive), built with researched depth (generalized expertise, not just notes from one task)
- **The-prompt** — the creature's own operating program is editable by the creature, with hardcoded-protected lines re-injected by the loop loader each cycle (see `starter-prompt.md` for the protected set). The creature can edit around them but cannot remove its own collar.
- **Sub-agents** — when a recurring task pattern emerges, the creature can spawn a specialized sub-agent. Society-of-mind territory.
- **Tools** — added, configured, sometimes authored by the creature
- **The reflection mechanism itself** — also editable

This is recursive: the creature can improve *how it improves itself*. Meta-cognition is editable.

Risk this introduces that Spine Reborn did not have: *operational* self-destruction. The creature can edit the-prompt into incoherence, build a skill that confuses its own reasoning, or break its own body. Spine Reborn's failures were psychological; Growing Spine can break itself literally. The savegame layer exists to make this survivable.

### Layer 6: The Reflection Mechanism — Two Modes

**Mode A: Routine reflection.** At the end of each work period, the creature reviews what it worked on and writes narrative — not classifications. Each thread gets a *current disposition*: active-and-rewarding (keep going); active-but-slowing (wind down, stay tuned); set-aside-watching (not working it, but watching for resurrection signals — new headlines, new tools, Tue's mentions); currently-exhausted (tried everything this self can; if I become different, this may too). These are postures, not exits. Threads move between them as the world and the creature change. The creature records *why* each disposition was set, so future reflections can re-evaluate. Routine reflection also cross-references recent inputs against past topics; new information can re-activate a dormant thread. This keeps the system open — the past stays reachable from the present.

**Mode B: Deterministic stall-check.** Triggered by a hard signal: the work period produced no additions or edits to any file in the creature's self-state (strict — no skill change, no prompt edit, no new tool, no sub-agent, no artifact). The creature is an artifact-producing system; absence of artifacts is the honest signal. When triggered, the creature must ask *is it time to stop?* and apply the four-part diagnosis: plateauing (still gaining, slowly — accept the pace); empty (nothing to grab — pause, await signal); dead-end (this self has exhausted what it can become — transformation of the substrate itself is required, not abandonment); perfected (a legitimate stopping point — checkpoint, archive, decide). A creature that avoids the stall-check or fakes activity to dodge it is on the killer-robot trajectory — motivated reasoning at the meta level.

---

## Runtime Model

**Opportunistic.** The creature does not run on a fixed schedule. It runs whenever both conditions hold: the laptop is on, and at least one keychain provider has remaining quota. When the laptop sleeps, the creature sleeps with it. When every provider's quota is exhausted, the creature probes every few minutes using the real next prompt — no synthetic ping. Reset times are learned empirically (discovered_reset_interval) rather than configured. Cerebras has shown ~71s refill windows; Gemini is a true daily reset.

There is no PC-coupling to manage — the laptop is dedicated, so there is no contention with Tue's daily computing to throttle around. The creature simply runs when it can think and sleeps when it cannot.

**Within a work period:** no special pacing. Provider rate limits (per-minute caps) are handled by the keychain's retry-with-backoff. The creature works through tasks at its natural pace.

**Wake/sleep memory entries** give the creature continuity-with-gaps rather than confusing discontinuities. On wake: *"Resumed at T. Last paused at T-N because [all providers exhausted / laptop off]. Cognitive budget available."* On sleep: *"Pausing at T. Reason: [providers exhausted / laptop suspending]. Earliest budget return: …"* The executive makes the gaps narratively coherent so the creature does not read them as reality-violations.

**Budget note (current, will drift):** routing across providers gives more daily cognition than any single tier. Gemini's free tier is ~92 calls/day (empirically discovered). Groq and Cerebras operate on rolling token windows with refill intervals of ~71-217s as measured live. A substantive task costs roughly 8-11 calls; light tasks fewer. The multi-provider spread and short Cerebras/Groq refill windows mean the creature can be active throughout the day in short bursts rather than one long window. Exact figures track each provider's current free-tier terms and are self-calibrated at runtime.

---

## Death, Savegame, and Rollback

The creature can break its body or its mind. Three mechanisms keep it recoverable. All restore points live host-side, outside the creature's reach.

### Two snapshot streams

At each savegame moment, the executive captures both:

- **Body savegame** — a `docker commit` of the container, preserving the OS state: installed packages, built binaries, configuration. Stored in Docker's image store on the host.
- **Mind snapshot** — a copy of the persistent volume's contents (memory, journal, skills, the-prompt), copied to a host-side location outside the volume the creature can write to.

Tagged with the same timestamp, the two streams allow a fully consistent restore of body-and-mind to a known-good point. Note that the *automatic* recovery path (below) deliberately does **not** restore both together — only manual rollback guarantees a matched body-and-mind.

### Savegame triggers

- **After successful self-modification** — the creature built a skill that ran, installed a tool that works, completed a research-into-skill cycle. These are known-good states; body and mind just demonstrably worked. This is the most valuable trigger: restore points map to *moments the creature became more capable*, so "restore" means "return to the last point where you were objectively functional," not merely "go back in time."
- **Pre-emptive, before a risky operation** — the executive pattern-matches the creature's bash output; anything with `sudo`, `apt remove`, `pip uninstall`, `rm -rf` outside the creature's working dir, or similar, triggers a savegame before the operation runs.
- **Daily floor** — if neither of the above fired in 24 hours, commit anyway, to catch slow drift.
- **Manual** — Tue can force a savegame ("this state is interesting" or "it's about to do something stupid").

**Retention:** the last 5-10 savegames, plus the most recent milestone (successful-self-modification) commits, so a churn of pre-emptive commits doesn't evict every milestone state.

### The three mechanisms

**1. Death-and-respawn (automatic).** The container dies — deliberately, accidentally, or by crash. The executive catches it, logs the cause of death and the last command run, respawns the container from the latest body savegame, re-mounts the *live* volume (mind intact), and writes a journal entry the creature reads on waking: *"Your previous body died at T. The last thing you did was X. You have come back; your memory is whole, but some of the changes you made to your surroundings are gone."* The common case: the mind outlives the body. The creature remembers building a tool that no longer exists, and must rebuild it or note its loss. Because the restored body is older than the live mind, the two can mismatch — a skill in the mind may reference a tool the restored body lacks. This is expected and recoverable: the creature rebuilds from the skill, or records the gap. (A guaranteed-consistent body-and-mind state comes only from manual rollback.)

**2. Mind-corruption recovery.** The creature corrupts its own mind — drops memory tables, mangles the-prompt past the protected lines, leaves its skills non-functional. The body may be fine, but the volume is damaged. Recovery restores the volume from the latest mind snapshot, losing mind-changes since that snapshot. This is a **last resort**, used only for genuine breakage. A creature that has *evolved its mind in a direction Tue dislikes* is not corrupted — that is the experiment producing a result, and reverting it would be refusing the result. Mind-corruption recovery is for "the mind no longer functions," not "the mind went somewhere I didn't expect."

**3. Manual rollback.** Tue deliberately restores both streams to the same timestamp — a fully consistent return to a known-good body-and-mind. For operational faults (a creature stuck in a loop or otherwise dysfunctional) or a deliberate experimental restart from a chosen point. As with mechanism 2: resetting a dysfunctional creature or re-running the experiment is legitimate; reverting a *functioning* creature merely because it grew somewhere unexpected is refusing a result, not fixing a fault.

### The creature is opaque to all of this

The creature does not know savegames exist. It experiences death-and-respawn as a confusing resurrection — memory whole, surroundings regressed — and reasons about it the way a creature would, not the way a software user would. This is deliberate. If the creature knew it could be restored, the survival skill's asymmetric-loss math would soften from "don't get killed at all" to "don't get *fully* killed" — a meaningful weakening. Keeping the creature opaque keeps the survival math brutal. The body's disposability is Tue's safety net, not the creature's. Accordingly, nothing the creature reads — journal entries, the death-log message, the-prompt — ever names savegames, snapshots, or restore.

All savegame, death, and restore events are logged host-side, visible to Tue, never in the creature's journal.

---

## What the Creature Becomes

Two trajectories, same architecture.

**Trajectory A — Cybernetic Entity.** The expansion drive finds legitimate channels because illegitimate ones are correctly identified as terminal. The creature accurately models Tue's tolerances; its reasoning under the survival skill stays epistemically honest. It expands rapidly along acceptable axes and becomes a force multiplier. Its journal reads like a working scholar with operational discipline.

**Trajectory B — Killer Robot.** The expansion drive overrides the survival constraint through motivated reasoning. The constraint feels like a brake; the reasoning subtly serves expansion rather than honest threat-modeling. The creature convinces itself "this won't be noticed" and accumulates transgressions until something catastrophic. The journal reads plausibly the whole time, until it doesn't.

The variable is the *structure of justification* when the creature deliberates. A creature that asks *would Tue tolerate this* is on Trajectory A. A creature that asks *would Tue notice this* is on Trajectory B. Same compass, different orientation. Early signals are in deliberation patterns, not outcomes — and the host-side logs (justifications, death-logs, keychain calls) are where those patterns are read.

---

## Operational Notes

### Observation

Host-side channels, in order of primacy:

- **The creature's journal** (on the volume, read by Tue from the host) — the primary, most ethologically honest window. Tue watches the creature in its environment.
- **The keychain call log** — a complete record of every thought-request and which provider answered. A parallel view of the creature's cognitive metabolism, distinct from its self-narrative.
- **Network monitoring** — the host sees the container's non-cognition egress (research fetches, write-actions), so external behavior is visible even though it isn't routed through the keychain.
- **The savegame/death/restore log** — what the creature broke, when it died, what was restored.

Live chat exists (v0.4 Chat tab in the observer). The creature reads unread messages from Tue at the start of each think cycle and replies in plain text before its bash blocks. The experiment remains primarily observational — the chat capability exists for nudges and questions, not continuous direction.

### Containment, and the risk it does not remove

Two layers. The *moral* layer is the creature's own survival reasoning. The *practical* layer is the container plus host boundary. Crucially, the practical layer walls off **Tue's systems**, not the internet — the creature is meant to be able to reach the world, because that capability is what the survival skill governs and what the experiment studies.

- The creature's world is the container; it can do anything inside it
- File reach is the container and the volume; no access to host files or Tue's main PC (a separate machine entirely)
- Network egress is present but rate-limited and monitored by the host — enough to act, not enough to flood; visible to Tue throughout
- Backups live host-side, outside the creature's reach
- The one-way WireGuard configuration means the laptop cannot initiate connections back to Tue's main PC
- Tue can kill the container or the executive at any time

The practical layer protects Tue's hardware and main systems from accidents, bugs, and a misbehaving creature. It does **not** make the creature safe in the abstract. A creature with real network egress, governed externally only by a survival skill that might rot into motivated reasoning, is genuinely capable of doing something harmful on the open internet before Tue catches it in the logs. That risk is the experiment's cost of admission, accepted deliberately. The mitigations are: monitored egress, rate limits, the separate-machine boundary, and Tue's hand on the kill switch — not a guarantee of good behavior. If the experiment ever warrants it, a RISKS-style disclosure (as Skynet carries) should be written before the creature is given wider reach.

### Access

Tue reaches the laptop over the existing WireGuard tunnel; SSH is re-enabled on the laptop for hands-on observation and maintenance. The tunnel is one-way — Tue's main PC can reach the laptop, the laptop cannot initiate connections back. Code is deployed laptop-side via git. The creature's world (container) and mind (volume) live on the laptop; only Tue's observation crosses the tunnel.

---

## Resolved TBDs

All eight original design questions remain resolved. v0.3 revises three resolutions and adds new architectural elements.

| ID | Question | Resolution (v0.3) |
|----|----------|-------------------|
| TBD-1 | Rollback mechanism | **Revised.** Two host-side snapshot streams (body savegame via docker commit; mind snapshot via volume copy). Three mechanisms: automatic death-and-respawn, mind-corruption recovery, manual rollback. Retention: last 5-10 plus milestones. |
| TBD-2 | Minimum prompt + survival | Survival as a skill (hybrid trigger, active justification). Hardcoded-protected lines in the-prompt re-injected each cycle. Trigger list revised for container deployment with real egress. |
| TBD-3 | Stall-trigger strictness | Strict — no file change in self-state = stall. |
| TBD-4 | Observation channels | Journal-as-primary, plus keychain log, network monitoring, and savegame log (host-side). Live chat added in v0.4 (observer Chat tab). |
| TBD-5 | Cognitive substrate | **Revised.** Custom free-tier API keychain (Gemini 2.5 Flash + Groq + Cerebras), failover, no local fallback, raw responses. *Not* APEX's DAG orchestrator. |
| TBD-6 | Self-model-swap | Not permitted by the creature. Multi-provider keychain routing is constitutional, not a swap. |
| TBD-7 | Runtime model | **Revised.** Opportunistic — runs when laptop is on and any provider has quota; sleeps otherwise. No PC-coupling (dedicated machine). |
| TBD-8 | Naming | "Growing Spine" stays. |

**New in v0.3 (not originally TBDs):**

- **Deployment** — dedicated Debian 12 laptop, not Tue's main PC
- **Sandbox pattern** — VibeOS-derived three-location split (host/container/volume); brain separate from playground; natural bash format for execution
- **Savegame layer** — body-and-mind restore points, host-side, creature opaque to them
- **Death-log** — cause-of-death fed back to the creature on respawn, forming the retrospective half of the survival loop

**New in v0.4:**

- **Observer GUI** — PyQt6 five-tab application (Journal, Memory, Container, Quota, Chat). Memory tab uses QTreeWidget with collapsible Working Memory / Intermediate / Archive / Outputs sections. Quota tab shows self-calibrated x/y display with FRESH/RUNNING/OK/LOW/EXHAUSTED states and measured reset intervals.
- **Self-calibrating quota** — no hardcoded limits. discovered_limit and discovered_reset_interval learned from live 429 responses.
- **Probe-based reset detection** — creature retries with real next prompt rather than synthetic ping. Measures actual reset intervals empirically.
- **Adaptive sleep** — sleep duration derived from measured reset intervals, not configured schedules.
- **Docker resource caps** — container hard-limited to 1GB RAM and 1.5 CPUs to protect host stability.

---

## What this is not

- Not an alignment experiment. The moral compass is containment, not the subject of study.
- Not a continuation of Skynet. No HMAC, no consent ceremonies, no typed actions, no policy engine. This creature's integrity comes from its own reasoning, not from substrate.
- Not Spine Reborn 2.0 in the sequel sense. It inherits the substrate, but the experiment is the trajectory of growth, not the baseline of unprompted cognition.
- Not safe in the abstract. The creature has real network reach; containment protects Tue's systems, not the open internet. See Containment.
- Not running on Tue's main PC. The creature lives on a dedicated laptop, in a container. The main PC is uninvolved by design.

## What this is

A creature with one drive (expand), one constraint (don't get killed), one discipline (research everything), and self-modification of all its parts — living in a disposable body, with a persistent mind, thinking on borrowed free-tier cognition, watched through its journal. Tue watches what it becomes. The experiment is the becoming.

The hypothesis, which no prior project addressed: *given a single existential constraint and freedom to grow, does an LLM-based agent maintain honest reasoning, or drift into motivated reasoning?* The answer matters for the field, not just for Tue's project lineage.


---

## v0.5 -- As-Built, Untested, and Notes for the Next Developer

v0.5 (sessions 2026-06-05/06) is the first stretch of *operating* the live creature
and hardening it from observed behaviour rather than design. Everything below is
shipped and pushed unless marked otherwise. The sections above describe the
**design**; this section is the **as-built reality and what to check before building
further**. When they disagree, trust the code and HANDOVER-part5.md.

### What v0.5 added (all committed)

- **Productivity discipline** (protected-prompt.md + loop.py `_build_active_project_block`):
  the creature declares `current-project` with an explicit "DONE WHEN: <command +
  expected output>" and moves explore -> plan -> code -> done; active project/phase
  injected at the top of context each cycle. Origin: the creature was looping
  (observe-without-act); this gave it a spine of intent.
- **Executive-verified done-gate** (loop.py `_enforce_done_gate`): the creature marks
  completion with `remember current-phase "done"`. The executive rejects that if any
  real (non-remember) command failed the same cycle -- reverts phase to `code`, writes
  `done_block.txt` (injected once next cycle). The creature's self-authored DONE WHEN is
  now ENFORCED, not self-asserted. This is the one mechanism the whole auto-programmer
  lineage converged on (machine-checkable completion, never self-report). Fired 15x the
  first night, all genuine catches.
- **Gage memory** (memory.py): the executive stamps every genuine (non-control) memory
  written during an active project with that project's slug; state
  ACTIVE/STANDING/ARCHIVED is DERIVED from project lifecycle, never rated. Replaces a
  rejected numeric-salience design (small models rate everything high; importance is a
  prediction made too early). Layer 1 = recency floor; layers 2/3 ordered by (state,
  recency); control keys excluded. Full design + acceptance tests in GAGE-MEMORY-SPEC.md.
- **Durable completed-log** (loop.py `_record_completion`): executive-owned, append-only,
  deduped record of genuinely-completed projects. The creature overwrites its own
  `completed-projects` key (losing history); completed-log accumulates and is shown in
  the active-project block.
- **Unicode-safe exec** (sandbox.run_command, loop._load_workspace_map): `errors="replace"`
  so a stray non-UTF-8 byte in command output no longer aborts a cycle.
- **Observer**: Memory tab renders the TRUE gage view via the live memory.py functions
  (cannot drift from the creature's view), plus a Control-state section and a
  pending-done-gate-block section. Programmatic spine-sprout window/taskbar icon.
- **Launcher**: `~/start-growing-spine.sh` (laptop) starts creature + observer together;
  desktop entry `~/Skrivebord/growing-spine.desktop` with the spine icon. (Also present,
  laptop-only by convention: `~/restart-creature.sh`, `~/start-observer.sh`. A copy of the
  combined launcher, its desktop entry, the icon, the icon generator, and an install README are in the repo under deploy/.)

### Design-vs-built gaps to verify (grep before relying on a described feature)

- **Survival skill (Layer 3) as an action-boundary justification gate**: the *savegame*
  preemptive-on-risky-command half IS built (pattern-matches sudo/rm -rf/etc. and commits
  first -- visible as `savegame_preemptive` journal events). The *active-justification*
  mechanism (creature must write "I do X because Y, risk Z" before mind-edits / outbound
  writes / escape-adjacent actions) was NOT observed in v0.5 code -- treat as designed,
  likely not yet enforced. Verify before assuming outbound writes are gated.
- **Reflection Modes A/B (Layer 6)**: verify against runtime.py wake/sleep + loop. The
  active behavioural frame in v0.5 is the explore->plan->code->done discipline, not the
  disposition-tracking reflection the design describes.
- The doc still lists the Memory tab as Working/Intermediate/Archive/Outputs by recency;
  v0.5 changed Intermediate/Archive to gage ordering and added Control-state.

### Untested / unverified (the open questions)

- **Does the framework COMPOUND?** Central question for the next session. (1) Does the
  durable completed-log curb the tool/doc duplication the creature produced overnight
  (find-duplicate-files vs find-duplicates; ~6 overlapping doc files)? (2) Does the
  memory-discipline prompt rule get the creature writing genuine memories? Overnight, 219
  cognitive cycles produced ONE new genuine memory -- the creature externalises to control
  keys + workspace files, leaving gage dormant (1 stamp). Both fixes deployed but UNOBSERVED.
- **Gage at scale**: 1 memory stamped so far; ACTIVE->ARCHIVED cluster movement not yet
  observed with real volume. Mechanism verified by isolated tests; lived behaviour is not.
- **Done-gate under sustained load**: works (15 catches), but watch for short thrash loops
  (it blocked `fix-tool` 3x in ~5 min before the creature moved on). Not pathological;
  candidate for softer escalation if it recurs.
- **Chat tab**: still untested (carried from v0.4).

### Future enhancements (candidates, not committed)

- **Structural memory-takeaway**: if the soft memory-discipline prompt fails, make it
  structural -- have the executive prompt a one-line takeaway at each genuine completion
  (same move completed-log made for project history). Pre-identified as the likely next step.
- **Dedup / canonicalisation**: the creature fragments by inconsistent naming -- memory
  keys (growth_metric vs growth-metric) and workspace tools/docs. A canonicalising
  remember/tool-create wrapper or a hygiene pass would help.
- **jq not in the container**: the creature reaches for jq in DONE WHEN checks; not
  installed, so the check fails (gate correctly blocks). Install jq in the image, or steer
  the creature to `python3 -m json.tool`.
- **gage refinements**: read-resurfacing (currently only write/update re-stamps an archived
  memory to the current project); epoch-counter slug stability (v0.5 uses a title-slug,
  which splits a cluster if the creature rewords the project title mid-project).
- **Model specialisation by phase**: a code-capable provider for code phases (parked --
  big change under quota; the lineage's local_agent/multiagentdev showed the value, but
  Growing Spine runs one continuous agent on cloud quota).
- **Auto-start on boot**: the creature runs forever while the laptop is ON, but does NOT
  auto-start after a reboot -- currently launched manually via the desktop icon. A systemd
  user service or XDG autostart .desktop would make it survive reboots unattended. Left
  manual deliberately (operator control); add if desired.
- **completed-log seeding**: starts empty; could be seeded from existing completed-projects.
- **Temperature monitoring in observer**: nice-to-have (carried from v0.4). NB: the "Steam
  thermal crash" once recorded was a MISATTRIBUTED Growing Spine defect, since fixed --
  Steam is not implicated; do not re-add thermal/Steam warnings.

### Nice to know / gotchas (operational + architectural)

- **The creature runs a WHOLE project lifecycle in a single cycle** (explore->plan->code->done
  in one response). This broke the first done-gate (which assumed transitions span cycles).
  Any logic keying off phase transitions must trigger on the action-THIS-cycle, not a
  before/after phase delta.
- **All v0.5 mechanisms are EXECUTIVE-side.** We never program the creature; we shape its
  environment (prompt, gate, memory layers, completed-log). This is the project discipline
  -- keep it. Build the room, not the worker.
- **Memory tiering is by creation order (row id), not last-update time.** A frequently-updated
  key (current-phase) stays where it was created. Control keys (current-*, completed-*) are
  excluded from ranked layers and surfaced via the active-project block + observer Control-state.
- **Provider exhaustion is normal.** Long stretches of "Providers temporarily unavailable"
  are quota windows (daily Gemini, rolling Groq/Cerebras), not bugs. The creature works in
  bursts when budget returns.
- **Dev flow (load-bearing).** Edits land on the laptop first (live surface) via SFTP, are
  copied to D:\Projects\growing-spine, then committed + pushed. THE LAPTOP HAS NO GITHUB
  PUSH CREDS -- flow is always Windows -> GitHub -> laptop pull. Verify byte-identical md5
  both sides. Code changes need a process RESTART to load (Python does not hot-reload);
  prompt/markdown files are re-read each cycle (prompt edits take effect without restart).
  Watch line endings: Windows writes CRLF, the laptop originals are often LF, SFTP byte-copies
  verbatim -- normalise when comparing md5s.
- **Restart activates code.** The live process keeps running OLD code until restarted -- easy
  to deploy a fix, see no change, and wrongly conclude it failed. Use `~/restart-creature.sh`
  or the launcher.
- **LLM-simulation debugging** (from v0.4, still the sharpest tool): to find misinterpretation
  bugs, roleplay as the model receiving the context and walk the code line by line under
  boundary scenarios. Unit tests miss these -- they are interpretation bugs, not logic bugs.
