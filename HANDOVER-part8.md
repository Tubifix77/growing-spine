# Growing Spine — Handover, Part 8

A clean state-of-the-project so the next session (or a future reader) can pick up without relying on chat history. Written 2026-06-21, after shipping v0.7 (self-restart) and syncing it to GitHub.

If you are the next Claude: read this, then `memory_read` (the sections under "Growing Spine — ..." carry the operational lessons), then look at the live state on the laptop before changing anything.

---

## One-paragraph status

Growing Spine is a self-improvement "toolsmith" creature: an LLM in a Docker container on an always-on Debian laptop, woken on a loop, building itself a coherent toolkit (and now able to rewrite and reload its own brain). As of this handover it is **live and healthy on v0.7**, systemd-supervised, single instance, quota-throttled as always. **Code, laptop, and GitHub are all in sync at commit `9ccf94e`.** The architecture (toolsmith reframe, v0.6) and the self-restart capability (v0.7) both work and are proven. The one thing NOT yet done: the README/architecture docs still describe v0.6 and need updating to document v0.7.

---

## The substrate (unchanged, know this)

- **Host** = the Debian laptop (`boas@192.168.0.77`). Runs the **executive** (`main.py` -> `executive/loop.py`), the keychain, the observer GUI, savegames. This is the "immortal brain".
- **Container** = the creature's mortal body (`growing-spine-body`); `/workspace` is its workshop. Dies and respawns; mind persists.
- **Volume** = `~/growing-spine-mind` (mounted at `/mind` in the container): memory.db, journal.jsonl, chat.jsonl, `tools/own/`, and v0.7 state files.
- **Keychain** = free-tier rotation (Gemini 2.5 Flash daily, Groq llama-3.3-70B, Cerebras gpt-oss-120B). Quota exhaustion is NORMAL; the creature works in bursts.
- **Repo**: PC `D:\Projects\growing-spine` and laptop `~/growing-spine` are BOTH full git peers (both push & pull; both use the same stored HTTPS token). GitHub: https://github.com/Tubifix77/growing-spine. (The old "laptop is pull-only" note was wrong and is fixed.)
- **Deploy flow**: edit on PC -> commit + push -> laptop `git pull` -> `./restart.sh`. Code changes need a restart; prompt/markdown (`protected-prompt.md`, `editable-prompt.md`) are re-read each cycle, no restart.

Method discipline (load-bearing): **shape the environment, never program the creature.** Every mechanism is executive-side. Build the room, not the worker. Sharpest debugging tool = LLM-simulation (roleplay the model reading its context).

---

## What v0.6 is (the toolsmith architecture — already shipped, already documented in README/arch)

The creature was relabelling/rebuilding ~31 near-identical dashboards (the "basin"). Fix = reframe it as a toolsmith building a toolkit for a near-conscious LLM "cousin" in a box like its own (cousin = pedagogical mirror, not a real recipient). Success = **reuse + dependency depth** (later tools built OUT OF earlier ones), not tool count. Five executive mechanisms: mission frame (protected-prompt), clean-context redirect (basin backstop), done-gate (with hollow-tool guard), reuse+dependency metrics, category coverage. This is live and working; the README + architecture docs already cover it.

---

## What v0.7 is (self-restart — shipped THIS session, NOT yet in the docs)

The creature could grow its body (tools, which hot-load) but was frozen out of its own brain (the executive only loads on restart, and nothing restarted it). v0.7 gives it the ability to rewrite and reload its own cognition, safely. Four layers, each verified:

1. **systemd immortal-brain supervisor.** `~/.config/systemd/user/growing-spine.service` (Restart=always, linger enabled, starts on boot). Vendored in repo at `deploy/growing-spine.service` + `deploy/INSTALL-systemd.md`. **Proven:** `kill -9` the brain -> systemd resurrects it. `restart.sh` now delegates to `systemctl --user restart growing-spine` (atomic; no more double-launch footgun).
2. **Brain snapshots via git** (`volume/savegame.py`): `brain_commit`, `snapshot_brain` (commits dirty tree so the SHA is faithful), `restore_brain` (git reset --hard), `brain_diff` (git diff good..bad, truncated). `save()` now records `brain_commit`.
3. **Crash-rollback-with-diff** (`executive/self_restart.py` + `boot_check` wired in `main.py`): if a self-restart crash-loops (>=3 starts within 90s), restore brain to the last good save AND enqueue a chat message to the creature: *"you crashed, restored to save A, the diff that killed you was [diff]"*. This is the LEARNING LOOP (Tue's key requirement — a rollback that teaches, not a silent reset). A healthy reload that stays up disarms as success. **Both paths proven** (simulated crash-loop reverted + messaged; good reload disarmed silently).
4. **deploy-self tool** (`framework-tools/deploy-self`, canonical in repo, auto-deployed to the volume each wake): the creature runs it to request a brain reload; it writes `/mind/restart_request.flag`; the executive sees it at cycle-end, runs `prepare_and_arm` (compile + full test suite + snapshot A, ~180s), and exits for systemd to reload. If validation fails, the creature is told why and stays on working code. **Proven** round-trip container->host.

The creature was told about deploy-self via a "## Reloading your own brain" section in `protected-prompt.md`.

Recursion achieved: host (systemd) supervises brain; brain (`ensure_body`) supervises container; brain can snapshot+restore container (existing) AND now systemd + boot_check can restore the brain (new).

---

## EXACT CURRENT STATE (verify before trusting)

- Laptop = PC = GitHub all at **`9ccf94e`**, working trees clean.
- Creature: `systemctl --user is-active growing-spine.service` = active, ONE instance (`pgrep -af main.py`), running the v0.7 brain.
- v0.7 verified live earlier this session: classifier fix holds (categories spread across all 5), done-gate catches premature completions, systemd resurrects on kill, rollback-with-diff works.
- Tests: `tests/test_loop_v2.py` (~33 checks) passing; it's also the gate `prepare_and_arm` runs before any self-restart.

---

## WHAT'S LEFT (the next task)

**Update README.md + growing-spine-architecture.md from v0.6 to v0.7.** They currently describe only the toolsmith architecture and do not mention self-restart at all. Add:
- README: a short "v0.7 — the creature can reload its own brain" section in the journey/status; mention systemd supervisor, deploy-self, rollback-with-diff; bump status line.
- architecture doc: bump to v0.7; document the 4 layers above; add to the "What works / what we tried that didn't" ledger (what works: systemd resurrection, rollback-with-diff learning loop, validate-before-reload; what we learned: testing destructive rollback against the live repo briefly reverted all on-disk work [git-recoverable], so test rollback on a throwaway commit; framework tools must live in the repo and be re-deployed, or a mind-restore wipes a volume-only tool); update file map (self_restart.py, deploy/, deploy-self); bump document-history.
- These are prose docs -> write on the PC, commit, push, laptop pull (no restart needed for docs, but pull keeps them in sync).

That's the only outstanding work. Nothing the running creature depends on is at risk.

---

## Key operational facts / gotchas (also in memory)

- **Restart**: always `./restart.sh` (now = `systemctl --user restart growing-spine`). Never hand-launch `python3 main.py` (creates an unsupervised second brain). One instance is correct; `main.py` does NOT fork.
- **creature.pid**: `restart.sh` writes `~/growing-spine/creature.pid`; a second old launcher (`deploy/start-growing-spine.sh`) writes `~/creature.pid` — inconsistent, harmless, consolidate when convenient. An empty/missing pid file just means the live process wasn't started by restart.sh.
- **File transfer laptop<->PC**: use `ssh_read_file` (returns text, no base64) -> `workspace:write` -> md5-check. Do NOT base64-grind through ssh_exec. PC cannot SSH to laptop directly (no key trust). `workspace:write` always needs `session_id`. Watch UTF-8 display mojibake (loop.py line 1 has real on-disk mojibake; true md5 41a8d6c5...). Git exec bit must be committed for deploy-self/restart.sh (100755).
- **Quota throttle**: long "Providers temporarily unavailable" / "Quota exhausted - retrying in 2 min" stretches are normal, not bugs.
- **Testing destructive things**: test rollback/self-restart against a THROWAWAY commit, not the live repo (lesson learned the hard way; git made it recoverable).

---

## Lineage / what this is NOT

7th in a series (Throne Mechanicum, Spine Reborn [direct ancestor], Sovereignty, LLM Profiler, MinionAI, The Prompt To Rule All Prompts, Growing Spine). NOT an alignment experiment; NOT Skynet; the abandoned original survival/"killer-robot vs cybernetic-entity" framing produced paralysis and was removed (containment is structural: container + rate limits + volume boundary). Old spec docs in the repo (IDEATION-ENGINE-SPEC, GROWTH-FLYWHEEL-SPEC, GAGE-MEMORY-SPEC, HANDOVER-part5) are historical; where they conflict with README/architecture, the latter are current.

_Laptop push access verified 2026-06-21T14:19Z_
