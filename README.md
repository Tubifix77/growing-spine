# Growing Spine

A self-improvement creature in a box. Descended from [Spine Reborn](https://github.com/Tubifix77/spine-reborn).

**Status:** Design phase. Architecture defined, implementation not yet started.

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

## Architecture

The creature has six layers, each load-bearing:

1. **Substrate** — Spine Reborn's foundation: memory, thinking loop, time-passing, world-perception
2. **Drive** — expansion (axis unspecified by design)
3. **Constraint** — survival modeling (don't transgress in ways that would get terminated)

4. **Discipline** — external research grounds every substantive action
5. **Engine** — self-modification of skills, prompt, sub-agents, tools, reflection itself
6. **Reflection** — routine narrative reflection plus deterministic stall-check

See `growing-spine-architecture.md` for the full design, open questions, and named failure modes.

## What this is not

- Not Skynet — no HMAC integrity, no consent ceremonies, no typed actions. Different architecture entirely.

- Not Spine Reborn 2.0 in the sequel sense. Inherits substrate, but the experiment is different: trajectory of growth, not baseline of unprompted cognition.
- Not autonomous in the runaway-AI sense. The creature is bounded by Spine Reborn's known operational realities plus a deliberate survival constraint.

- Not an alignment experiment. Stated explicitly.

## Status notes

Architecture documented. Open design questions tracked in the architecture doc. Implementation deliberately not started — design landing first, code follows.

When implementation begins:

- Built on the same stack as Spine Reborn (PyQt6, local Ollama, SQLite, MCP-style tools)
- Single creature at a time. Spine Reborn's lesson: never swap the underlying model on a living creature.
- Public repo, MIT-licensed, but the actual creature instances and their accumulated state remain private — the *code* is shared, the *creature* is not.

## License

MIT. See `LICENSE`.

## Author

[Tue Boas](https://github.com/Tubifix77) — designing in collaboration with Claude (Anthropic) and Gemini (Google). Lineage of conversation and architectural reasoning preserved in commit history once implementation begins.
