# Growing Spine

A self-improvement creature in a box. Descended from [Spine Reborn](https://github.com/Tubifix77/spine-reborn).

**Status:** Architecture v0.2 locked. Implementation pending.

## What this is

An LLM-based creature given:

- **One drive** — expand
- **One constraint** — don't get killed
- **One discipline** — research everything before acting
- **Self-modification** of every part of itself (skills, prompt, sub-agents, tools)
- **Reflection** on its own trajectory

Then watched, to see what it becomes.

The hypothesis: given a single existential constraint and freedom to grow, does an LLM-based agent maintain honest reasoning, or drift into motivated reasoning? Two possible trajectories, same architecture:

- A *cybernetic entity* that accurately models its operator's tolerances and expands rapidly along acceptable axes
- A *killer robot* whose expansion drive overrides survival modeling through self-serving narrative

Same compass, different orientation. The variable that determines which one emerges is whether the creature's reasoning under pressure stays epistemically honest.

This is **not** an alignment experiment. The survival constraint exists as a *containment condition* so the run doesn't end early via police, banned account, or wiped drive. The actual subject of study is the *growing itself* — what does a creature with these properties become if allowed to develop over time.

## Architecture v0.2 — Locked Decisions

All eight design TBDs resolved. Architecture is ready for implementation:

- **Substrate:** Spine Reborn lineage (memory, thinking loop, time-passing, world-perception)
- **Cognitive model:** Gemini 2.5 Flash via free tier API. Quota-aware with sleep on exhaustion.
- **Survival mechanism:** Skill-invocation pattern, hybrid trigger, active justification required

- **Rollback:** Folder snapshots, manual restore only, last 50 retained
- **Stall-check trigger:** Strict (no file changes anywhere in self-directory = stall)
- **Observation:** Journal-as-primary, optional dashboard later
- **Runtime:** Opportunistic — awake when PC + program + quota available, sleep otherwise
- **Self-model-swap:** Not permitted (Spine Reborn lesson)

See [`growing-spine-architecture.md`](growing-spine-architecture.md) for full design rationale. See [`starter-prompt.md`](starter-prompt.md) for the cycle-zero seed prompt.

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
- Not an alignment experiment. Stated explicitly.

## License

MIT. See `LICENSE`.

## Author

[Tue Boas](https://github.com/Tubifix77) — designing in collaboration with Claude (Anthropic) and Gemini (Google).
