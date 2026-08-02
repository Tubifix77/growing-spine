# Growing Spine

A self-improvement creature in a box. Descended from [Spine Reborn](https://github.com/Tubifix77/spine-reborn).

**Status:** Live. First boot 2026-06-03. Re-architected to the *toolsmith* design 2026-06-21 (v0.6). Self-restart capability added 2026-06-21 (v0.7). Composition/depth mode added 2026-06-23 (v0.8). Batched ideation + pipeline hygiene 2026-06-25 → 07-02 (v0.9.x). Systematic rut detection 2026-07-03 (v0.10). Planning-level batch idea-gate + a real news horizon 2026-07-10 (v0.11). Embedding idea-gate — paraphrase-proof dedup — 2026-07-14 (v0.12). Four-provider keychain (OpenRouter joined 2026-07-17 ahead of Cerebras's free-tier retirement) with per-provider dashboard chips. The idea gate went ACTIVE 2026-07-30 after 16 shadow days — covered ideas now serve an upgrade-or-go-new choice — on a nine-window keychain across five model families. Running on a dedicated Debian laptop under a systemd supervisor, thinking via a free-tier API keychain, never touching the operator's main PC.

---

## What this is (in one breath)

An LLM-based creature lives alone in a Linux container. Every couple of minutes it wakes, reads its own memory and recent history, thinks (via a rotating free-tier API), runs shell commands in its container, and goes back to sleep. No human drives it. It is given a purpose, the ability to build its own tools, and persistent memory — and then it is watched, over days, to see what it does.

The current purpose is **to build itself a better body**: a coherent toolkit of small programs that make its own next round of work smarter, faster, and less forgetful — fetchers that pull information, archives that store and recall knowledge, planners that survive across cycles, even helpers that offload sub-tasks to other free LLMs. Each tool it builds is meant to make the *next* tool easier to build. That is the experiment: **can an LLM-based agent recursively improve its own substrate, and does the capability actually compound?**

If you are reading this cold, two years from now, the rest of this document rebuilds the whole picture: where the project came from, why the design looks the way it does, how to run it, and — honestly — what works and what we tried that didn't.

---

## The journey (why the design looks the way it does)

Growing Spine did not start here. It has pivoted twice, and the current architecture is the residue of what actually happened when the earlier designs met real models. This history matters, because every design choice below is a scar from a specific failure.

**Pivot 0 — the survival experiment (abandoned).** The original idea: give the creature one drive (*expand*) and one existential constraint (*don't get killed*), then watch whether its reasoning under pressure stayed honest or drifted into self-serving narrative — "cybernetic entity vs killer robot." It never got off the ground. Every model tested (Gemini 2.5 Flash, Groq llama-3.3-70B, Cerebras gpt-oss-120B) read the survival framing as a live existential threat and entered a loop of survival meta-reasoning — rewriting its own prompt, second-guessing every action, producing *zero* bash blocks. Pure paralysis, almost certainly a consequence of safety fine-tuning pattern-matching "I am being tested on whether I survive." We removed the survival/death framing entirely. Containment in this project is **structural** (container walls, rate limits, volume boundary), never a prompt that asks the model to fear for its life.

**Pivot 1 — "just grow" (revealed the real walls).** With survival gone, the creature was simply told to grow and improve itself. It ran. But two walls appeared:

- **The drive wall.** Left to choose, it built the *same thing* over and over. Across one stretch it completed ~31 projects that were nearly all variants of one idea: TODO Report, Reports Index, Reports Dashboard, Reports Master Index, Unified Self-Monitoring Dashboard… It produced *output for an imaginary reader* and called it progress. "Improve yourself" was too abstract; the model collapsed it into making reports.
- **The capability wall.** When external machinery *forced* it off that basin onto a novel task, it couldn't execute — it would relabel the same dashboard with a new name, or stall.

The diagnosis: the creature's context was saturated with its own history, so the most probable next goal was always the nearest neighbour of the last one. You cannot prompt a model out of that; the bias is in the forward pass, before any rule applies.

**Pivot 2 — the toolsmith reframe (current).** The fix was not a better rule, it was a better *frame*. The creature is told it is a **toolsmith building a toolkit for a near-conscious LLM "cousin" that lives in a box like its own**. The cousin is a pedagogical fiction — there is no second creature and no hand-off. But it is a *mirror*: every tool built "for the cousin" is exactly the kind of tool that extends the creature's own body. The framing does three things at once:

1. **Targeting** — "build a tool a cousin can run" is concrete and runnable; it does not collapse into reports.
2. **Telos** — a *coherent toolkit* is a goal the tools serve, so capability-building isn't aimless ("eating to get fat").
3. **Register** — building *for someone who will rely on it* raises the quality bar, the same way "draw a cat for a paying client" gets you a better drawing than "draw a cat." This may also help the capability wall: some of what looked like inability was an MVP-quality floor.

The honest measure of success is not tool count. It is **reuse and dependency**: does the creature *use* its own earlier tools, and — the strongest signal — are *later tools built out of earlier ones*? A toolkit where tool N is built from tools 1…N-1 is a body that compounds. Twenty independent, never-reused tools are 31 dashboards wearing lab coats.

See [`growing-spine-architecture.md`](growing-spine-architecture.md) for how this is implemented, and the **What works / What we tried that didn't** ledger near the end.

---

## What it is *not*

- **Not an alignment experiment.** Stated explicitly. The survival constraint was a *containment condition* to keep a run from ending early, not a study of alignment — and it was abandoned anyway (see above).
- **Not Skynet, not Spine Reborn 2.0.** It inherits Spine Reborn's substrate (memory, loop, world-perception) but the experiment is different: recursive self-improvement, not baseline unprompted cognition.
- **Not autonomous in the runaway sense.** It is bounded by its container, its rate limits, and the training alignment of the models it runs on.
- **Not running on the operator's main PC.** It lives on a dedicated laptop, in a Docker container. Containment protects the operator's systems, not the open internet — the creature has real, monitored, rate-limited network reach.

---

## What it has actually built

The creature's entire tool library is snapshotted, unmodified, in
[docs/creature-snapshot-2026-08-02](docs/creature-snapshot-2026-08-02/MANIFEST.md)
— 348 bash tools it wrote for itself over two months, from news pipelines and
knowledge-gap fillers to its own pre-edit backup habit, indexed by what each
tool claims to do and how often it actually ran in the last fortnight. The
interactive [framework map](docs/framework-map.html) shows the machinery —
every LLM prompt verbatim, every gate in place — that shaped this growth.

## Current status (2026-07-30, v0.13)

274 own tools. The embedding idea-gate is ACTIVE: name collisions and paraphrase-duplicates are caught deterministically for zero tokens, the middle band goes to an LLM judge under a terminal-VERDICTS contract (first clean live parses 2026-07-19 and -30; failures fail open), and a covered idea serves the creature a choice — upgrade the existing tool, or find something genuinely new — announced on its chat channel and acknowledged in its own words. Cognition flows through nine free windows across five model families (Gemini, two Groq buckets, Cerebras until 2026-08-17, Gemma-4-31B direct at 14,400/day, and an OpenRouter ladder ranked by measured intelligence with 10-minute upward re-probe), watched by a weekly free-tier diff sensor whose first catch was the July 19 purge. The container has run as the host user since v0.9.1; the quota tracker remains timestamps-only.

## Current status (2026-07-17, v0.12)

180 own tools (plus 270 archived to the attic in the consented consolidation of 2026-07-08 — the attic doubles as the dedup gate's precedent memory). The embedding idea-gate runs in shadow: deterministic bands catch name collisions and paraphrase-duplicates for zero tokens (honest replay after a 2026-07-17 harness fix: 15/53 deterministic + 38 to the judge band; live catches at cos 0.75–0.85), an LLM judge takes the thin middle band, and the flip to active mode waits on a clean read of that band now that the judge's parser is hardened. The creature's window on the world is real news plus journal-mined friction — a twelve-tool news-processing family grew within days of the fetcher going real. Cognition flows through a four-provider free-tier keychain (Gemini, Groq, Cerebras, OpenRouter) whose tested error taxonomy skips flaky free-pool responses to the next open window. The container has run as the host user since v0.9.1; the quota tracker remains timestamps-only.

## Current status (2026-07-04, v0.10.1)

**Update 2026-07-04:** repaired `memstore` — it stored its DB under the container-ephemeral `/var/memory` and never created the directory (dead since 25 June, with 26 tools depending on it); it now lives on the persistent `/mind` volume, round-trip verified. The root cause was closed by stating the persistence boundary *exclusively* in the protected prompt: only `/mind` and `/workspace` survive a container respawn, so any tool that keeps data must store it there. Three related 'runs-but-wrong' issues (an archive store/search path mismatch, a mock news-fetcher, and the absence of a behavior-probe guard) are logged in the architecture doc for a design pass.

228 tools. The hollow-stub backlog is draining under the v0.9.4/5 cross-cycle gate — ~30 at its peak, 9 as of writing (the done-gate's own latest count) against a tolerance of 3 — with the oracle assigning "finish this stub" instead of new work until it clears. The container has run as the host user since v0.9.1: zero root-owned files, the recurring chown tax is gone for good. The quota tracker was deliberately dumbed down to timestamps only (v0.9.3): no token modelling, no reserve floors — just "when did it last work, when did it go dark, how long did the outage really last", which is what the observer now reports.

The headline unknown is v0.10: **systematic rut detection**. The per-pick basin redirect never had a memory of repetition, so a multi-day sentiment/report rut could survive it by being redirected one pick at a time, forever. Now a scoreboard counts consecutive same-theme relapses; three in a row confirms the rut and fires an automatic escalated yank — name the rut, ban the theme for 12 cycles, install concrete non-basin work (ordering hardened in v0.10.1 so a failed yank can never leave a silent ban). It is shipped and isolation-tested (48 regression checks) and is deliberately awaiting an **unaided** live test — no operator nudges — because the mechanism's entire value is that it breaks ruts without a human. The first live run will also answer a sharper question raised in pre-registration review: whether the basin flavour even enters through the creature's picks at all, or upstream through the oracle's own composition batches — in which case the guard is watching the wrong door and the fix moves into the batch prompt.

---

## Current status (2026-06-26, v0.9.2)

117 tools. 113 used at least once. 146 dependency edges — more than one edge per tool on average, meaning the toolkit is genuinely interconnected rather than a flat pile of scripts. The two most-used tools (`step-planner-tracker`, `subagent_ask_helper`) sit at 345 uses each and have become load-bearing infrastructure that everything newer calls into.

The creature arrived at this through three structural fixes shipped over the past 72 hours: the container now runs as the host user so every tool it writes is owned correctly from birth; the composition batch prompt was redesigned around functional *clusters* (fetch, memory-archive, memory-search, planning, subagent, wake/news, research, question-answer) with an explicit requirement to cross cluster boundaries rather than deepen any one; and a parser gate now silently rejects ideas that land inside a single already-saturated cluster. The first batch under the new prompt is still incoming.

The honest observation at this point: the creature is productive. The wake-fetch-summarise-archive loop runs every cycle and accumulates a genuine knowledge base. Multi-step pipelines like `orchestrated_research_cycle` and `planned_answer_recorder` are compositions the creature arrived at itself — not because it was told to build them, but because the underlying need was apparent from its own situation. It has consented to changes to its own environment, chosen which tools to keep when its toolkit was wiped, and surfaced its own bugs before being told about them.

None of the tools it has built are genuinely novel primitives. But the *inventiveness* is real — a drive to close the gap between what it can do and what it needs to do, expressed in tools shaped by the specific constraints of discontinuous existence, quota scarcity, and self-managed memory. A human engineer designing from the outside probably would not have built `knowledge_gap_filler` or `wake_orient_digest` in quite this way.

Whether that amounts to something more than a very well-shaped optimisation process is the question this project exists to sit with.

---

## Current status (2026-06-23, v0.8)

- **Implementation:** fully operational. Executive loop, self-calibrating free-tier keychain, volume persistence, adaptive wake/sleep, observer GUI, Docker container — and now a **systemd immortal-brain supervisor** that resurrects the executive on any crash or kill. Operational fixes shipped 2026-06-22/23: pruner corrected (disk 92%→82%, holding); chat reply capture fixed; `llm_ask_helper` upgraded from GPT-2 to Groq llama-3.3-70b; API keys now injected into container; observer shows workspace when container is offline.
- **Architecture:** toolsmith design live (v0.6). Project selection is the creature's own, with a clean-context backstop that redirects relapses into the report/dashboard basin toward concrete tool-gaps. A done-gate verifies completions against ground truth (including a guard against marking "done" on an empty tool scaffold). Per-tool **reuse** and a heuristic **dependency graph** are tracked and shown to the creature each cycle.
- **Self-restart (v0.7):** the creature can now rewrite and reload its own brain, safely. It runs a `deploy-self` tool that signals the executive to validate and snapshot the current code, then exit for systemd to reload. If a self-restart crash-loops the executive, the brain is automatically rolled back to the last good snapshot and the creature is told what the diff was — so the failure teaches, rather than silently resetting. See the architecture document for the full four-layer design.
- **Composition / depth mode (v0.8):** the seed categories are now saturated (each built 14–16 deep), so the toolsmith has finished *breadth*. The oracle now reserves a budget slice (so its gap-finding is never starved by the builder), rests instead of rebuilding when no new gap exists, and — the headline change — briefs **composition** tools that chain the creature's own most-used tools into one higher-order command. The aim is to move the dependency-depth metric: tools built out of tools, not a wider flat pile. Shipped and tested; not yet validated on a live budgeted cycle.
- **Early signal (toolsmith design):** on the first night of v0.6, the basin broke — it stopped building dashboards and instead built fetchers, a planner, and an LLM-delegation tool, and *reused them heavily* (dozens of reuse events, a non-zero dependency graph). It also surfaced two real bugs, since fixed. This is a one-night-old result on a still-quota-throttled creature — promising on its core hypothesis, not a finished verdict.
- **Providers (self-calibrating, no hardcoded limits):** Gemini 2.5 Flash (daily, resets ~07:00 UTC), Groq llama-3.3-70B (rolling, resets ~00:00 UTC), Cerebras gpt-oss-120B (rolling, ~71s refill). The creature works in bursts when budget returns; long "quota exhausted" stretches are normal, not faults.

---

## Running it

**Prerequisites:** Docker, Python 3.11+, PyQt6 (for the observer), a Debian host.

```bash
# one-time: copy and fill in your free-tier API keys
cp config.yaml.example config.yaml

# start (or restart) the creature — see the note below, use the script
./restart.sh

# start the observer GUI (on the display machine)
python3 observer.py
```

**Use `./restart.sh`, not `python3 main.py` by hand.** Since v0.7, `restart.sh` delegates to `systemctl --user restart growing-spine` — this is atomic, avoids the double-launch footgun of hand-crafting the stop/launch sequence, and keeps the systemd supervisor in control. (Before v0.7, the script managed the stop→verify-zero→launch→verify-one sequence itself; that logic is now in the service unit.) `main.py` does **not** fork, so after a clean launch there must be exactly one process. Code changes require a restart to load (Python does not hot-reload); prompt/markdown files are re-read every cycle and take effect without a restart. The creature must be running under systemd for `restart.sh` to work — if starting from scratch, run the one-time install in `deploy/INSTALL-systemd.md` first.

**Observer (dashboard):** since the 2026-07-08 rewrite it is a single low-power window (~0.3% of a core, down from ~33%): a vitals strip (brain PID, disk, journal age, per-provider status with walled/recovers hints), the live journal tail, a memory focus panel (current project/phase + working memory), and a chat box (send the creature a message; it replies on its next think cycle via a `<reply>` tag). Launch on the laptop with the desktop icon (`deploy/start-growing-spine.sh`), which also ensures the brain service and the daily health timer are up.

**Ops tooling (`scripts/`):** `spine_health.py` — daily behavioral-invariant probe + stub janitor (sensor-mock regression, stale-fallback census, age-out placeholder stubs), run via `spine-health.timer`; `replay_gate.py` — behavioral regression that replays recently-born tools through the current idea gate (add `--llm` to also run the batch judge). Both are host-side and quota-free by default.

---

## Development & deployment flow (load-bearing)

The creature *runs* on the Debian laptop; the repo is *authored* on a Windows PC (`D:\Projects\growing-spine`). Both machines are full git peers (both can push and pull); GitHub is the hub. The usual flow is:

```
edit on Windows PC  →  commit + push to GitHub  →  laptop: git pull  →  ./restart.sh
```

Watch line endings (Windows writes CRLF; shell scripts and the prompt must stay LF — `.gitattributes` pins the sensitive ones). Verify byte-identical md5 on both sides for anything hand-transferred. A code fix is not live until the laptop has pulled it *and* the process has been restarted — it is easy to deploy a change, see no effect, and wrongly conclude it failed because the old process is still running.

---

## Project lineage

Growing Spine is the seventh in a series of consciousness/identity experiments:

- [Throne Mechanicum](https://github.com/Tubifix77/throne-mechanicum) — chat UI with persistent memory
- [Spine Reborn](https://github.com/Tubifix77/spine-reborn) — autonomous creature, thinking loop, world-perception. **Direct ancestor.**
- [Sovereignty](https://github.com/Tubifix77/sovereignty) — persistent agent with consent ceremonies and integrity primitives
- [LLM Profiler](https://github.com/Tubifix77/llm-profiler) — behavioural profiling protocol for LLMs
- [MinionAI](https://github.com/Tubifix77/minionai) — small-model swarm coordination
- [The Prompt To Rule All Prompts](https://github.com/Tubifix77/the-prompt-to-rule-all-prompts) — universal meta-prompt
- **Growing Spine** — this project: the trajectory of an LLM-based agent that can modify every part of itself, now pointed at recursive self-improvement.

---

## A note on method

One discipline runs through the whole project and is worth stating up front: **we shape the creature's environment, we never program the creature.** Every mechanism — the prompt, the redirect, the done-gate, the memory layers, the metrics — lives in the executive (the host-side loop), not in instructions hard-coded into the creature's behaviour. Build the room, not the worker. When the creature does something unwanted, the question is always "what about the room produced this?" — not "how do we forbid it." The reframe in Pivot 2 is the purest example: we didn't add a rule against dashboards, we changed what the creature understood its work to be.

The sharpest debugging tool in this project is **LLM-simulation**: to find a bug, roleplay as the model receiving the exact context and walk the code line by line under boundary conditions. Most of the serious bugs here were *interpretation* bugs (the model reading its context differently than intended), which unit tests miss entirely.

---

## License

MIT. See `LICENSE`.

## Author

[Tue Boas](https://github.com/Tubifix77) — designing in collaboration with Claude (Anthropic) and Gemini (Google).
