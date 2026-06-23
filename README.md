# Growing Spine

A self-improvement creature in a box. Descended from [Spine Reborn](https://github.com/Tubifix77/spine-reborn).

**Status:** Live. First boot 2026-06-03. Re-architected to the *toolsmith* design 2026-06-21 (v0.6). Self-restart capability added 2026-06-21 (v0.7). Running on a dedicated Debian laptop under a systemd supervisor, thinking via a free-tier API keychain, never touching the operator's main PC.

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

## Current status (2026-06-21, v0.7)

- **Implementation:** fully operational. Executive loop, self-calibrating free-tier keychain, volume persistence, adaptive wake/sleep, observer GUI, Docker container — and now a **systemd immortal-brain supervisor** that resurrects the executive on any crash or kill. Operational fixes shipped 2026-06-22/23: pruner corrected (disk 92%→82%, holding); chat reply capture fixed; `llm_ask_helper` upgraded from GPT-2 to Groq llama-3.3-70b; API keys now injected into container; observer shows workspace when container is offline.
- **Architecture:** toolsmith design live (v0.6). Project selection is the creature's own, with a clean-context backstop that redirects relapses into the report/dashboard basin toward concrete tool-gaps. A done-gate verifies completions against ground truth (including a guard against marking "done" on an empty tool scaffold). Per-tool **reuse** and a heuristic **dependency graph** are tracked and shown to the creature each cycle.
- **Self-restart (v0.7):** the creature can now rewrite and reload its own brain, safely. It runs a `deploy-self` tool that signals the executive to validate and snapshot the current code, then exit for systemd to reload. If a self-restart crash-loops the executive, the brain is automatically rolled back to the last good snapshot and the creature is told what the diff was — so the failure teaches, rather than silently resetting. See the architecture document for the full four-layer design.
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

**Observer tabs:** Journal (live activity), Memory (working / intermediate / archive), Container (`/workspace` file browser), Quota (provider cards with discovered limits and measured reset intervals), Chat (send the creature a message; it replies on its next think cycle).

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
