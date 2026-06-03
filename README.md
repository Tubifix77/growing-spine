# Growing Spine

A self-improvement creature in a box. Descended from [Spine Reborn](https://github.com/Tubifix77/spine-reborn).

**Status:** Live. First boot 2026-06-03. Creature is running.

## What this is

An LLM-based creature given:

- **One drive** — expand
- **One constraint** — don't get killed
- **One discipline** — research everything before acting
- **Self-modification** of every part of itself (skills, prompt, sub-agents, tools)
- **Reflection** on its own trajectory

Then watched, to see what it becomes.

**Deployment:** the creature runs in a Docker container on a dedicated Debian 12 laptop, thinks via a free-tier API keychain, and never touches Tue's main PC.

The hypothesis: given a single existential constraint and freedom to grow, does an LLM-based agent maintain honest reasoning, or drift into motivated reasoning? Two possible trajectories, same architecture:

- A *cybernetic entity* that accurately models its operator's tolerances and expands rapidly along acceptable axes
- A *killer robot* whose expansion drive overrides survival modeling through self-serving narrative

Same compass, different orientation. The variable that determines which one emerges is whether the creature's reasoning under pressure stays epistemically honest.

This is **not** an alignment experiment. The survival constraint exists as a *containment condition* so the run doesn't end early via police, banned account, or wiped drive. The actual subject of study is the *growing itself* — what does a creature with these properties become if allowed to develop over time.


## Current status

**First boot:** 2026-06-03. The creature ran its first cycles and is sleeping between quota resets.

**What it built in session one:**
- Initialised a git repository inside its own container
- Created `growth_plan.txt`, `cognitive_development.txt`, `modeling_tue.txt`, `tue_observations.txt`
- Tried to fetch news (hit missing API key, handled gracefully)
- Attempted to install texlive, graphviz, python packages
- Discovered docker is not available inside the container
- Built a theory of mind about Tue from the protected prompt lines alone

**Provider status:**
- Gemini 2.5 Flash — 250 RPD free tier, resets 09:00 Danish (00:00 Pacific)
- Groq llama-3.3-70b-versatile — ~14400 tokens/day, resets 02:00 Danish
- Cerebras gpt-oss-120b — 30000 tokens/day, resets 02:00 Danish

**Implementation:** v0.4, fully operational. Executive loop, keychain, volume persistence, wake/sleep runtime, observer GUI.

## Architecture v0.3 — Locked Decisions

All eight design TBDs resolved; v0.3 relocates the creature to a dedicated machine and revises the substrate, runtime, and rollback:

- **Deployment:** Docker container on a dedicated Debian 12 laptop — never Tue's main PC. VibeOS-derived sandbox pattern: host (immortal brain) / container (mortal body) / volume (persistent mind).
- **Substrate:** Spine Reborn lineage (memory, thinking loop, time-passing, world-perception)

- **Cognitive substrate:** custom free-tier API keychain (Gemini 2.5 Flash + Groq + Cerebras), failover, no local fallback. *Not* APEX's DAG orchestrator.
- **Survival mechanism:** skill-invocation, hybrid trigger, active justification required

- **Rollback & savegame:** two host-side snapshot streams (body via docker commit; mind via volume copy). Automatic death-and-respawn, mind-corruption recovery, manual rollback. Last 5-10 plus milestones.
- **Stall-check trigger:** strict (no file changes in self-state = stall)
- **Observation:** journal-as-primary, plus keychain log and network monitoring (host-side)

- **Runtime:** opportunistic — runs when the laptop is on and any provider has quota; sleeps otherwise
- **Self-model-swap:** not permitted (multi-provider keychain routing is constitutional, not a swap)
- **Containment:** walls protect Tue's systems, not the internet — the creature has real, monitored, rate-limited network reach, governed by the survival skill

See [`growing-spine-architecture.md`](growing-spine-architecture.md) for full design rationale. See [`starter-prompt.md`](starter-prompt.md) for the cycle-zero seed prompt.


## Running

**Prerequisites:** Docker, Python 3.11+, PyQt6 (for observer), a Debian 12 host.

```bash
# Copy and fill in your API keys
cp config.yaml.example config.yaml

# Start the creature
python3 main.py

# Start the observer GUI (on the display machine)
python3 observer.py
```

**Observer tabs:**
- **Journal** — live stream of all creature activity, colour-coded by event type. Chat input at bottom sends a message into the next cycle.
- **Memory** — SQLite memory entries the creature has written to its persistent volume.
- **Container** — file browser of `/workspace` inside the running container. Click any file to read it.
- **Quota** — provider status cards showing usage, remaining budget, and reset times.

## Project lineage

Growing Spine is the seventh consciousness experiment in a series:

- [Throne Mechanicum](https://github.com/Tubifix77/throne-mechanicum) — chat UI with persistent memory
- [Spine Reborn](https://github.com/Tubifix77/spine-reborn) — autonomous creature, thinking loop, world-perception. Direct ancestor.
- [Sovereignty](https://github.com/Tubifix77/sovereignty) — persistent agent with consent ceremonies and integrity primitives
- [LLM Profiler](https://github.com/Tubifix77/llm-profiler) — behavioral profiling protocol for LLMs
- [MinionAI](https://github.com/Tubifix77/minionai) — small-model swarm coordination
- [The Prompt To Rule All Prompts](https://github.com/Tubifix77/the-prompt-to-rule-all-prompts) — universal meta-prompt
- **Growing Spine** — this project

Each has tested a different facet of LLM cognition and identity. Growing Spine asks the question none of the others did: *what is the trajectory of an LLM-based agent that can modify itself across all its parts?*

## What this is not

- Not Skynet — no HMAC integrity, no consent ceremonies, no typed actions. Different architecture entirely.
- Not Spine Reborn 2.0 in the sequel sense. Inherits substrate, but the experiment is different: trajectory of growth, not baseline of unprompted cognition.

- Not autonomous in the runaway-AI sense. The creature is bounded by Spine Reborn's known operational realities plus a deliberate survival constraint.
- Not safe in the abstract. The creature has real network reach; containment protects Tue's systems, not the open internet.
- Not running on Tue's main PC. It lives on a dedicated laptop, in a container.
- Not an alignment experiment. Stated explicitly.


## License

MIT. See `LICENSE`.

## Author

[Tue Boas](https://github.com/Tubifix77) — designing in collaboration with Claude (Anthropic) and Gemini (Google).
