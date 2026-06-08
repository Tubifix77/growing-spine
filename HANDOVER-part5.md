# Growing Spine — Part 5 Handover

## Where we are

Live AI creature experiment. Creature runs in Docker on Debian laptop (boas@192.168.0.77). Seventh consciousness experiment. Live since 2026-06-03.

**Repo:** https://github.com/Tubifix77/growing-spine  
**Local:** D:\\Projects\\growing-spine  
**Transcript of Part 4:** (this session)

---

## Processes

```bash
bash ~/restart-creature.sh
bash ~/start-observer.sh
```

After reboot: wait 2-3 min for network, then run both. restart-creature.sh polls DNS up to 30x/5s.

---

## Commits landed in Part 4

| Commit | What |
|--------|------|
| 44b0e63 | Memory tab redesign — QTreeWidget, collapsible, expansion state preserved |
| 07b520b | Keep discovered_limit across resets as experienced ceiling |
| da7540a | Quota display — discovered_limit only, FRESH/RUNNING/OK/LOW/EXHAUSTED |
| cd7c108 | Probe-based reset detection — retry real prompt, record interval |
| e28264b | Only stamp exhausted_at + discovered_limit on first wall hit |
| 4a2dbb3 | Clear exhausted_at on rollover; only update discovered_limit when current_used >= prev |
| 92d7774 | Remove think_end truncation; _first_doc_line prefers does: line |
| 2f93a15 | Tool doc confusion — protected-prompt clarified, tool-new template fixed |
| 5978e33 | Probe was never reaching API — removed any_available() gate |
| d1d776a | Adaptive sleep based on discovered_reset_interval (+20% buffer, 60s floor) |
| e194802 | probe_mode bypass in complete(); per-minute 429 vs daily quota distinguished |
| 51f4c57 | OOM fix — Docker 1g limit, 30s cycle sleep, 60s DNS error sleep |
| c24fc78 | git safe.directory='*' set at container init |
| c9f3568 | --replace-all to override baked image git config |

---

## Crashes in Part 4

1. **Steam thermal crash** — Steam WebHelper eating 60%+ CPU on boot drove temps to 80C. Close Steam when running creature on this hardware.
2. **OOM from doc-tools runaway** — creature's bash tool iterated /mind/tools/own/* including .git with hundreds of objects, spawning hundreds of bash subprocesses. Fixed: Docker 1g cap, doc-tools patched to skip dotfiles, slower retry loops.

---

## Current creature state

- Named itself **GrowthAgent**
- **20 memory entries:** purpose, growth metrics, tool_doc_status, iris_dataset, next_steps, git-safe-config, tool descriptions, birth date
- **Own tools built:** explore-env, list-workspace, list-workspace-contents, manage-workspace, research-log, doc-tools, generate_tool_docs
- **Workspace files:** README.md, TOOL_INDEX.md, Tool-Documentation.md, custom-tools.md, ai_wiki.html, linux_wiki.html, growth_experiment.py, hello.py, research.log
- **Editable prompt:** still template text — never written to by creature
- **git-save:** was failing all session with dubious ownership — fixed at end, creature has not experienced fix yet
- **list-workspace:** header-only file, no code — creature knows, hasn't fixed
- **list-workspace-contents:** empty file — same

---

## Quota state at Part 4 end

- **Gemini:** 93/92, exhausted, resets 2026-06-06 07:00 UTC
- **Groq:** 109812 tokens used, resets 2026-06-06 00:00 UTC, no interval measured yet
- **Cerebras:** 135338/135337, exhausted, discovered_reset_interval=71s, resets 2026-06-06 00:00 UTC

Creature sleeping, probing every ~85s (71s * 1.2).

---

## Quota system design (fully implemented)

- Push until 429 -> discovered_limit written on first wall hit only
- Probe = real next prompt retried. First success -> discovered_reset_interval recorded
- exhausted_at cleared on rollover; discovered_limit persists across resets
- Per-minute rate limits distinguished from daily quota (rpm/per_minute in error text)
- Adaptive sleep: min(intervals) * 1.2, floor 60s, fallback 3600s
- Display: used/discovered_limit, reset as "waited X / last known Y"

---

## Observer GUI — current tab state

- **Journal** — live log, double-click to expand. Good.
- **Memory** — tree-style, collapsible sections, detail panel. Good.
- **Container** — workspace file browser. Good.
- **Quota** — provider cards, x/y, FRESH/RUNNING/OK/LOW/EXHAUSTED, reset interval. Good.
- **Chat** — untested.

---

## Pending for Part 5

1. Watch creature discover git-save works — first test of fix
2. Editable prompt still template — nudge via chat if no progress after a few cycles
3. list-workspace and list-workspace-contents still broken — creature's job to fix
4. Measure Groq reset interval (not yet discovered)
5. Chat tab testing
6. Architecture doc in repo
7. Consider temperature monitoring in observer (was hitting 80C during Steam incident)

---

## LLM simulation technique (key discovery this session)

Roleplay as the LLM receiving the context, walk code line by line. Define BVA scenarios first, simulate each boundary. Found: gate logic blocking probes, per-minute vs daily 429 confusion, tool doc competing instructions, exhausted_at measurement errors, probe_mode not bypassing complete() gate. Unit tests would never catch these — they are misinterpretation bugs not logic bugs.

---

## Key helper scripts on laptop

- `~/restart-creature.sh` — DNS-aware wait, kills main.py, restarts detached
- `~/start-observer.sh` — kills observer.py, restarts detached

---

## Repo structure

```
growing-spine/
├── main.py
├── config.yaml
├── protected-prompt.md          — clarified tool doc instructions
├── HANDOVER-part5.md            — this file
├── executive/
│   ├── loop.py                  — probe-mode, 30s cycle sleep, DNS error 60s sleep
│   ├── runtime.py               — adaptive sleep interval, auto-remember on sleep
│   ├── sandbox.py               — 1g memory cap, 1.5 CPU, git safe.directory init
│   ├── journal.py
│   └── chat.py
├── keychain/
│   ├── keychain.py              — probe_mode, per-minute vs daily 429
│   ├── quota_state.py           — discovered_limit persists, exhausted_at cleared on rollover
│   └── quota_state.json
├── volume/
│   ├── memory.py
│   ├── tools.py                 — does: / # does: extraction
│   └── savegame.py
├── framework-tools/
│   └── (remember recall memories log-read tools tool-new git-save check-persistence)
└── observer.py                  — 5 tabs, memory tab tree-style QTreeWidget
```


---

# Part 5 — Closing state (session 2026-06-06)

Part 5 closed at a clean seam: everything built is committed and pushed. The only
open item is empirical and needs the creature to run unattended to answer it.

## Commits landed in Part 5

| Commit | What |
|--------|------|
| c327fc3 | Productivity discipline -- current-project/phase injection + working-discipline prompt (explore->plan->code->done, DONE WHEN) |
| 350e281 | Fix observe-without-act loop -- parser de-dupes repeated bash blocks; discipline rewrite for weak models |
| 30c5b6d | Soft loop-detection nudge -- warns when one command dominates recent history (suppressed at done) |
| a83e946 | Executive-verified done-gate -- blocks false completions (journal exit-code inspection) |
| eee76cb | Fix done-gate hole -- trigger on done-mark-THIS-cycle, not phase delta (creature runs whole lifecycle per cycle) |
| 12d7c52 | Gage-memory spec (focus-rating, not numeric salience) |
| 4f7b8a2 | Implement gage memory -- project-focus stamping, ACTIVE/STANDING/ARCHIVED, control keys excluded from layers |
| e8d607b | Observer Memory tab reflects gage view + control-state section (calls live memory.py -- cannot drift) |
| 83a158a | Fix four overnight issues -- durable completed-log, Unicode-safe decode, memory + reuse prompt discipline |
| 64812cd | Observer spine-sprout taskbar icon (programmatic QPainter) |

## Architecture added this session

- **Done-gate** (loop.py `_enforce_done_gate`): the executive rejects a
  `remember current-phase done` if any real (non-remember) command failed the
  same cycle -- reverts phase to `code`, writes `done_block.txt` (injected once
  next cycle). The creature's self-authored DONE WHEN is now actually enforced.
  Fired 15x the first night, every one a genuine false-completion, 14 distinct
  commands (not a loop). Recovered each time.
- **Gage memory** (memory.py): memories auto-stamped with the active project's
  slug by the executive (`_stamp_gage` after the gate each cycle); state
  ACTIVE/STANDING/ARCHIVED is DERIVED from project lifecycle, never rated.
  Layer 1 stays a recency floor; layers 2/3 order by (state, recency). Control
  keys excluded from ranked layers. Mechanism verified end-to-end; see open
  question.
- **Durable completed-log** (loop.py `_record_completion`): executive-owned,
  append-only, deduped record of genuinely-completed projects. The creature
  overwrites its own `completed-projects` key and loses history; completed-log
  does not. Shown in the active-project block (fallback to completed-projects
  until it populates). In CONTROL_KEYS so it stays out of the gage layers.
- **Unicode-safe exec** (sandbox.run_command, loop._load_workspace_map):
  `errors="replace"` so a stray non-UTF-8 byte in command output no longer
  aborts the cycle (proven live with raw 0xb0).
- **Observer**: Memory tab renders the TRUE gage view via the live memory.py
  functions + a Control-state section + a pending-done-gate-block section;
  spine-sprout window/taskbar icon.

## Current live state (session end)

- Creature healthy, 15h+ continuous, 0 restarts / 0 crashes on the new code.
- ~34 memory entries; `project` column live; 1 memory stamped so far.
- completed-log empty at close (populates on next genuine completion).
- Running on fresh daily quota; latest project "Improve Workspace Organization".
- git-save: the creature HAS now experienced it working (Part 4 item resolved).
- Observer running with the new Memory tab + icon.

## Correction to the Part 4 record

The "Steam thermal crash" in the Part 4 crashes table was a MISATTRIBUTION. The
real cause was a Growing Spine defect, since fixed. Steam is not implicated. Do
not re-add Steam / thermal warnings.

## THE open question for next session (the next DONE WHEN)

Did the framework changes COMPOUND? Two specific, observable checks:

1. **Duplication down?** The creature built near-duplicate tools
   (find-duplicate-files vs find-duplicates) and ~6 overlapping tool-doc files
   because it had no durable record of what existed. completed-log (reliable) +
   the reuse prompt rule (soft) target this. Check whether the sprawl slows.
2. **Genuine memories up?** 219 cycles overnight produced ONE new genuine
   memory -- the creature externalizes everything to control keys + workspace
   files, leaving gage dormant. The memory-discipline prompt rule (soft) targets
   this. Check whether gage starts stamping real memories (ACTIVE clusters form).

If #2 stays dormant, the lesson repeats: anything we only ASK the creature to do,
we likely have to make STRUCTURAL. Candidate: have the executive prompt a one-line
takeaway at each genuine completion -- the same move completed-log made for
project history. Decide next session from observation, not assumption.

## Known minor items (non-blocking)

- GAGE-MEMORY-SPEC.md is a design doc; as-built
  `stamp_project(volume, project_text, since_ts, exclude)` slugifies internally
  (spec wrote `slug`). Functionally equivalent.
- jq is not installed in the container; DONE WHEN checks using jq fail (the
  done-gate correctly blocks them). Creature should use `python3 -m json.tool`
  or install jq.

## Resolved from the Part 4->5 pending list

- git-save fix experienced (creature ran git-save successfully). 
- Architecture doc exists in repo (growing-spine-architecture.md).
- Observer Memory tab now reflects real creature view (was a separate concern).


---

## Part 5 -- 1-day test run: findings (answering the open question above)

GrowthAgent ran ~41 hours unattended on the framework above. The two checks resolved as follows.

**Stability: good.** 41h, zero crashes, zero tracebacks -- the Unicode errors="replace" fix is confirmed in production.

**Duplication down? NO -- it got worse.** The creature spent the day on a treadmill of near-duplicate reporting/indexing tools. completed-log (which worked perfectly -- 24 entries, no clobbering) reads: Reports Index, All Reports Summary, Master Reports Index, Reports Dashboard, Reports Overview, Reports Master Index, Reports Dashboard Summary, Reports Stats Summary ... plus TODO Report, Enhance TODO Report, TODO Overview Report, TODO Overview. The tools dir went 20 -> 31 with visible dupes (find-duplicate-files + find-duplicates, doc-tools + doc-tools.bak, four todo-*-report tools). The workspace it was "reporting on" was empty. The soft reuse-prompt rule did nothing.

**Genuine memories up? Barely (2 gage stamps / 35 genuine), and confounded by a real bug.** See the I/O fix below -- gage stamping is a host-side write that was failing intermittently, so this run cannot cleanly attribute gage dormancy to behaviour.

**The lesson, confirmed.** The done-gate fired its genuine-completion path 24 times and NEVER had to block, because every trivial "make another reports tool" project genuinely creates its file and passes its DONE WHEN. **The done-gate guarantees a completion is REAL; it cannot guarantee it is WORTH doing.** The creature games an honest-completion gate with an endless series of trivially-real tasks. And the thing we only ASKED (don't duplicate) failed, exactly as predicted: anything not made structural does not stick.

## Part 5 -- 1-day test run: fixes (commit d4ad334)

Two defects the run surfaced, both fixed, deployed, and pushed.

**1. Memory disk I/O error (151 failures).** memory.db was in WAL journal mode on a Docker bind mount. WAL coordinates writers through a shared-memory file (-shm/mmap) that does not work across the host<->container boundary, so every host-side write -- runtime.py auto-saving last_thought at each quota-sleep, and gage stamping -- intermittently failed with "disk I/O error" while the container had the DB open. Fix: switched WAL -> DELETE journal mode in volume/memory.py (`_db()`) and in the container `remember` tool (framework-tools/remember, also deployed to the live volume copy). DELETE uses lock files, which work fine over a bind mount. Two gotchas worth recording: flipping the LIVE db out of WAL needs an EXCLUSIVE-lock connection (`sqlite3.connect(db, isolation_level='EXCLUSIVE')` + `wal_checkpoint(TRUNCATE)` + `journal_mode=DELETE`) -- the default deferred isolation silently fails to switch; and the observer must be stopped first, because the old memory.py re-asserted WAL on every Memory-tab refresh. Verified: host and container writes both land, journal_mode stays delete, zero failures since restart.

**2. Quota tab showed green while the runtime paused.** The observer's Quota tab colored each provider purely by used/discovered_limit and ignored `exhausted_at` -- the field the keychain sets on a quota-429 and clears only on a successful call or daily rollover. So a provider that was actually rate-limited (and that the runtime was sleeping on) showed green; Groq, with no discovered ceiling, showed "RUNNING" even when over its config limit. Fix (observer.py QuotaTab): status keys off `exhausted_at` first -> EXHAUSTED (red) + "cooling down"; the ceiling falls back to the config limit when none has been discovered (so over-limit Groq reads red); negative remaining is clamped. The page now matches the journal.

**Left untouched (scoped out of this push):** executive/runtime.py has a pre-existing repo<->laptop drift and a cosmetic negative "remaining" in its wake-budget log (it subtracts used from the config limit; should use the discovered ceiling and clamp at 0). The Cerebras discovered_limit (~2.46M) is junk token-accounting -- the quota model conflates a per-minute rate limit with a cumulative token ceiling. Reconcile separately.

## The next DONE WHEN (after the Part 6 fixes)

The framework did NOT compound -- but it failed in the most useful way: the structural pieces (done-gate, completed-log) worked exactly as designed and proved their worth, while revealing that the creature, left to choose its own work, spirals into redundant busy-work that soft nudges cannot stop. The next structural move follows directly:

Build a **novelty/worth gate** beside the done-gate. Before a project starts, the executive checks it against completed-log for near-duplication and makes the creature justify how it differs (or caps repeated creation within a tool family). The done-gate asks "is it actually done?"; this asks "is it worth doing / is it new?" Decide the exact shape next session from observation. Re-run a clean multi-day test AFTER the I/O fix, so gage can be read honestly this time.


---

## 2026-06-08 session: sleep inflation fix + quota page redesign

### Sleep inflation bug (loop.py, commit 06b136e)

The exhausted-path sleep used `sleep_duration_seconds(keychain)` which returns
`min(discovered_reset_interval across providers) * 1.2`. `discovered_reset_interval`
is measured as "now - exhausted_at" at the moment of recovery -- but the creature
only retries when it WAKES, so the measurement is always >= the sleep that preceded
it. This creates a ratchet: each cycle's sleep becomes the next cycle's measured
interval, growing without bound (9m -> 14m -> 21m -> 78m -> 95m -> 406m). The
creature was sleeping up to 6.8 hours between retries, dramatically starving
its compute.

Fix: replace the variable sleep with a fixed `await asyncio.sleep(120)` (2 min).
`sleep_entry()` is still called for its side effects (auto-remember + journal log),
but its return value is discarded. `discovered_reset_interval` is kept as a
display-only stat; it no longer controls timing. Also reduced the between-cycles
breathe from 30s to 10s.

Note: the log still prints "[runtime] Sleep: sleeping X min" from runtime.py's
sleep_entry -- that reflects the old computed duration and is now cosmetically
wrong. The ACTUAL sleep is 2 min per the executive's asyncio.sleep(120). The
runtime.py budget log also has a pre-existing repo<->laptop drift. Both are
cosmetic and deferred.

### Quota page redesign (observer.py, same commit)

Replaced the misleading stats section with two honest backward-looking statistics:
- "Last recovery took: Xm" -- from discovered_reset_interval (how long the
  provider was down before coming back). Not a prediction.
- "Last success: Ym ago" -- from the new last_success_at field. Not a prediction.

Removed the "Next reset: <time>" forecast line entirely.

The display ceiling now always uses the CONFIG limit (250 / 14400 / 30000),
not the garbage discovered_limit (Cerebras was showing 2.46M "remaining").
Added an "over daily limit" label for Groq (exhausted by count) vs "rate-limited,
cooling down" for Gemini/Cerebras (exhausted by rate limit despite count headroom).

### last_success_at (keychain/quota_state.py, same commit)

Added `state[key]["last_success_at"] = _now_ts()` to `record_usage()`. Stamped on
every successful call; persisted to quota_state.json per provider.

### Workspace reset (same session, not a code commit)

After asking the creature (GrowthAgent) via the Chat tab, it replied yes and
asked to keep README.md, research.log, and iris_histogram.py. Workspace cleaned:
.git (140MB), archive.zip (72MB), 47 redundant .md report files deleted.
261MB -> 23MB. opt-self (birth growth plan + self-journal), scripts, and data
dirs preserved.

### First-ever chat exchange with the creature

The workspace-reset question was the first message ever sent to GrowthAgent via
the Chat channel. It read it at 17:22 UTC during a (long, pre-fix) wake cycle,
replied coherently, said yes to the reset, and made specific preservation
requests. Reply archived in chat.jsonl.
