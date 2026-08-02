# Ideation Engine — build brief (Growing Spine)

> **READ THIS FIRST. You are modifying a LIVE creature running on a shared Debian laptop.**
> A half-applied change or a double-launched process can break a 16-day experiment. Test on a
> copy before you touch the running process. The gotchas in §6 already cost multiple days — respect them.

## 0. The result this is built on (why we're doing this)
The creature is mechanically healthy (durable memory works, `remember`/tools work, it has web access,
the done-gate + spin-trap + retro + self-concept-reset + novelty-gate all fire correctly). It is **not**
limited by memory, network, or enforcement. It is limited by **drive/imagination**: it objective-hill-climbs
inside ONE basin ("ingest data → sentiment/insight → dashboard/report") and, when blocked from a duplicate,
it *relabels* rather than *reinvents* — block "Dashboard" and it makes a "Sentiment Alerting System"; give it
the open web and it fetches news to summarize. Every project it has ever set is the same KIND. Lifetime
PROGRESSING ≈ 0; ~28 completions are all report/dashboard/analytics variants.

The existing Gate A (novelty gate) is **negative** — it only says *don't repeat*, which buys minimal evasion,
not exploration. This build replaces that with a **positive novelty *driver*** at project selection. Lineage:
novelty search (Lehman & Stanley) + quality-diversity / MAP-Elites (Mouret, Clune). Make *distance from
everything already done* the driver, and force coverage of an explicit space of project KINDS.

## 1. Project law (do not violate)
**Build the room, not the worker.** Everything here is executive/host-side, in `executive/loop.py` + one
new state file. Do **not** edit the creature's prompt-obedience or its container. You shape its inputs and
gate/steer its project selection; the creature still does the building.

## 2. The mechanism — an "ideation engine" at project-start (4 parts)
Replace the current `_enforce_novelty_gate` (Gate A v2) with `_run_ideation(executed, keychain)`. Keep the
same TRIGGER (fires when a NEW project title is set — `PROJECT_SET_RE` matched in this cycle's `executed`;
the module var `_last_gated` skips mere refinements of the same title). Behaviour changes from
"judge duplicate → block" to:

### Part 1 — KIND coverage (MAP-Elites; the PRIMARY lever)
- `KINDS = ["game","simulation","solver_or_algorithm","generative_art","cipher_or_crypto",
  "puzzle_generator","parser_or_interpreter","math_toy","creative_writing_generator","bot_or_agent"]`
  (tune freely). **Explicitly EXCLUDE the basin** — no "dashboard/report/analytics/insight/sentiment/
  pipeline/monitoring" kind is allowed.
- Persist `kinds_built` (a `{kind: count}` map) in `~/growing-spine-mind/ideation_state.json`
  (same pattern as `retrospective_state.json`). A kind only counts as built when a project of that kind
  GENUINELY completes (see the completion hook in §3).
- At ideation, compute `untried = KINDS − {kinds with count>0}` (or least-built). The engine REQUIRES the
  next project to be from an untried/least-covered kind. This flips the gate from "don't repeat" (negative)
  to "build a *game* now" (positive pull into the empty cells of the space).

### Part 2 — random orthogonal seed (bisociation: creativity from yoking two unrelated frames)
- The executive (host) HAS internet. Each ideation, fetch a random concept HOST-SIDE (Python stdlib urllib;
  do NOT depend on the creature's tools):
  `GET https://en.wikipedia.org/api/rest_v1/page/random/summary` → take `title` + first sentence of `extract`.
- The proposal MUST incorporate that seed concept. Fallback to a hardcoded seed-word list if the fetch
  fails (fail-open — never block the creature because Wikipedia was slow).

### Part 3 — diverge hot, pick far, execute cold
- ONE brainstorm `keychain.complete(...)` call: ask for **N=8 deliberately different** project ideas, each
  tagged with its KIND, each forced to (a) be an untried kind and (b) use the seed concept.
  - Temperature: `complete(prompt, max_tokens=...)` is known to work (verified). CHECK `keychain/keychain.py`
    to see if `complete` forwards a `temperature`/params arg to the provider call. If yes → pass
    `temperature≈1.0` for THIS call only. If not → **do not add temperature plumbing** (don't risk the shared
    keychain); instead get diversity from the PROMPT ("make these 8 wildly different from each other AND from
    the past-work list below"). Prompt-driven diversity is the safe default.
- Score the 8 by distance from past work (use the completed-log overview from `_summarize_completed` +
  `kinds_built`); pick the farthest candidate that is ALSO an untried kind.
- Then enforce + steer (see §2 Part-enforcement below). The creature executes its build normally (cold).

### Part 4 — anchor-starve + role mask (at the brainstorm call ONLY)
- The creature relabels because every cycle it marinates in its own history (completed-log + self-concept in
  layer1), so its next goal is the nearest neighbour of the last. For the **brainstorm call's prompt only**,
  do NOT include the creature's self-concept/recent history. Include only: the KIND coverage map, the seed
  concept, and a RANDOMLY chosen role ("You are a game designer" / "a mathematician" / "a prankster inventor"
  / "a naturalist" / "a demoscene coder" …). Fresh, stateless, separate from the creature's main loop.

### Enforcement (how the chosen idea actually lands)
Evolve the existing block machinery rather than dictating:
- If the creature's just-set project is a duplicate of completed-log **OR** a kind already covered → CLEAR it
  (reuse `_clear_project_state()`) and write a POSITIVE block-notice to `PROJECT_BLOCK_PATH` (the existing
  read-and-delete injection surfaced by `_build_project_block()` in `_build_context`). The notice now CARRIES
  the positive content: "Your pick rebuilds the report/data family. Build a **<required untried kind>** instead.
  Use this seed concept: **<title — extract>**. Starter ideas (pick one or better): 1)… 2)… (the 8)."
- If the creature's OWN pick is already a genuinely-new kind + novel → **let it stand** (never override good
  behaviour — that's the whole point).
- Keep a safety cap (the existing `NOVELTY_BLOCK_CAP=4`): never permanently lock the creature out of acting;
  after N consecutive blocks let one through and journal "Cap reached" (this is also a signal to read — if it
  fires repeatedly the creature can't execute the required kinds = a *capability* wall, see §7).
- STRONGER ALTERNATIVE if blocking+steering proves too weak (it ignored the steer like it ignores soft asks):
  pre-seed `current-project`/`current_focus` with the chosen idea via `memory.forget` + `store` so layer1 LEADS
  with the new direction (coordinate with `_reset_self_concept`, see §5). Try blocking+steer first; escalate to
  pre-seeding only if it relabels around the steer.

## 3. Exact integration points (`executive/loop.py`)
- `_enforce_novelty_gate(executed, keychain)` is hooked in `run_cycle` immediately after
  `_enforce_done_gate(executed)` (~line 853–854, before `_stamp_gage` + `return True`). REPLACE with
  `await _run_ideation(executed, keychain)`.
- `_build_context` injects `_build_project_block()` (read-and-delete one-shot) and
  `_build_active_project_block()` (which shows the completed-log overview via `_summarize_completed`). **Add the
  KIND-coverage map to the active-project block** so the creature SEES "kinds built: …; untried: …" every cycle.
- **Completion → kind classification hook:** in `_enforce_done_gate`'s GENUINE-completion path (where the real
  completion is recorded / `completed-log` is appended), add ONE cheap stateless classify call ("which KIND is
  this finished project? answer one word from the list, or 'other'") and increment `kinds_built[kind]` in
  `ideation_state.json`. This is what fills the MAP-Elites cells with *real* (finished) work, not attempts.
- New state file `~/growing-spine-mind/ideation_state.json`:
  `{"kinds_built": {kind:count}, "last_seed": "...", "last_ideated_title": "...", "block_streak": 0}`.
- Reuse existing helpers: `_clear_project_state()`, `_summarize_completed(entries)`, `PROJECT_SET_RE`,
  `_last_gated`, `PROJECT_BLOCK_PATH`, `memory.forget` (exists), `memory.retrieve/store`.

## 4. keychain
- `keychain.complete(prompt, max_tokens=...)` works (verified). Each engine call is ONE stateless completion
  (cheap; the roster is Groq llama-3.3-70b + Cerebras gpt-oss-120b + Gemini 2.5 Flash — all handle this).
- **Fail-open EVERYWHERE**: any keychain error / quota RuntimeError / seed-fetch failure / malformed brainstorm
  → let the creature's own pick stand. NEVER trap or crash the loop. (This mirrors the existing gate's
  fail-open, which is load-bearing under heavy quota throttling.)

## 5. Memory-layer interaction (don't fight it)
`layer1` working memory = the 5 most-recent non-control memories shown in full each cycle (volume/memory.py),
pure recency. The self-concept reset (commit 3dbf968) forgets self-concept keys on a STUCK retro and seeds a
fresh `current_focus` at the TOP of layer1. If you pre-seed an ideation direction (the §2 stronger path), use
`memory.forget` on stale focus keys + `store` the new direction so it LEADS layer1 — otherwise the old basin's
persistent memories outweigh a transient directive (that's exactly why soft directives lose). Coordinate with
`_reset_self_concept` so the two don't stomp each other.

## 6. Dev flow (MANDATORY — live creature, shared laptop)
- Edit on the **laptop** first (`~/growing-spine`) — it is the live test surface. **LF line endings only.**
  (CRLF in a shebang/executed script is fatal — it's what silently broke `remember` for days. `.py` imports
  tolerate CRLF, but keep LF anyway. `.gitattributes` already pins `framework-tools/* eol=lf`.)
- **TEST on the laptop with a `/tmp` mock-keychain harness against a COPY of the live `memory.db` BEFORE you
  touch the running creature.** Established pattern:
  ```
  import sys; sys.path.insert(0,'/home/boas/growing-spine')
  import keychain.quota_state as qs; qs.save_state=lambda *a,**k:None   # never write live quota state
  from executive import loop
  loop.VOLUME_MOUNT='/tmp/ideatest'; loop.IDEATION_STATE_PATH='/tmp/ideatest/ideation_state.json'
  loop.PROJECT_BLOCK_PATH='/tmp/ideatest/project_block.txt'
  # cp /home/boas/growing-spine-mind/memory.db* /tmp/ideatest/ ; stub keychain.complete with a fake
  # drive _run_ideation through: duplicate pick→blocked+kind-steer; novel-new-kind pick→allowed;
  #   untried-kind selection correct; seed-fetch-fail→fallback; keychain raises→fail-open(creature pick stands);
  #   cap reached→let through+journal; completion-classify updates kinds_built.
  ```
  Aim for full branch coverage (the harness has caught every regression in this project).
- Sync the SAME edit to the repo `D:\Projects\growing-spine`; verify byte-identical LF-normalized
  (laptop `tr -d '\r' | md5sum` vs repo). Commit + push **from Windows** — the laptop has NO push creds; the
  flow is always Windows → GitHub → laptop `git pull`.
- **RESTART to load code (no hot-reload).** RESTART GOTCHA (this has burned us repeatedly): do NOT combine
  kill+launch in one command. FOUR SEPARATE steps:
  1. `pkill -9 -f "[p]ython3 -u main.py"`
  2. verify `pgrep -cf "[p]ython3 -u main.py"` == 0
  3. `cd ~/growing-spine && setsid bash -c 'exec python3 -u main.py' >> ~/growing-spine.log 2>&1 < /dev/null & disown`
  4. verify `pgrep -cf "[p]ython3 -u main.py"` == 1   (the `[p]` bracket stops pgrep matching itself)
  Then write the pid to `~/creature.pid`. A one-shot `nohup … &` over SSH gets torn down when the channel
  closes — `setsid …& disown` is what survives. (prompt/markdown files are re-read each cycle — no restart for
  those; only code needs a restart.)

## 7. Success metric & what to watch
- **Success = `kinds_built` grows beyond the data/report cell** — i.e., the creature GENUINELY COMPLETES a
  game OR simulation OR solver OR generative-art (etc.) project, and a retro finally comes back PROGRESSING.
- **Two distinct walls, distinguish them in the writeup:**
  - DRIVE wall (what we've seen): it won't *propose* a different kind on its own. The engine forces this.
  - CAPABILITY wall (new, possible): forced into "build a maze generator", does it actually *finish* a working
    one, or fail to execute the unfamiliar kind (repeated done-gate blocks / "Cap reached")? Either outcome is
    a real, publishable result.
- Keep disk healthy (`df`; the pruner at commit 203d258 is active). Don't let the brainstorm output or the
  random-Wikipedia fetch balloon anything. Laptop hovers ~88% / ~14G free — stay clear of 100%.

## 8. Files you'll touch
- `executive/loop.py` — the engine + hooks (the main change).
- `volume/memory.py` — only if you need a new helper (`forget()` already exists; probably nothing needed).
- new (runtime, created by code): `~/growing-spine-mind/ideation_state.json`.
- this brief: `IDEATION-ENGINE-SPEC.md` (repo root + `~/growing-spine/` on the laptop).
- Companion context: `GROWTH-FLYWHEEL-SPEC.md` (the earlier design lineage) is in the repo — read it for background.

## 9. One-paragraph summary for the impatient
At project-start, instead of only blocking duplicates: pull a random Wikipedia concept (host-side), pick a
project KIND the creature hasn't built yet (from an explicit list that excludes the dashboard/report basin),
brainstorm 8 deliberately-divergent ideas in that kind using that seed under a random creative-role mask with
NO self-history in the prompt, pick the one farthest from past work, and steer the creature into it via the
existing block-injection (escalate to pre-seeding layer1 if it relabels around the steer). Classify each
genuine completion into a kind to fill the coverage map. Fail-open on everything. Test on a copy, then do the
4-step restart. Success = it finishes a genuinely different KIND; if it's forced to a new kind and still can't
finish, that's the capability wall and also a real result.
