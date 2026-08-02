# Gage Memory (Focus-Rating) — Architecture Spec

Status: spec for implementation. Target: Growing Spine `volume/memory.py` + `executive/loop.py`.
Context: replaces the rejected numeric-salience / importance-urgency matrix. Gage is a
*projection of project lifecycle onto memories*, not a rating the model assigns.

## 1. Core idea

Gage is NOT a score the creature or model produces. Per-entry importance ratings failed with small
models (everything rated high) and are a prediction made too early — importance is revealed by later
use, not knowable at write-time. Instead the executive *derives* each memory's gage STATE from which
project it belongs to and that project's status. Grouping is a fact about WHEN a memory was written,
not a judgment. The spotlight moves from project to project as work completes.

## 2. States — derived at read-time, NEVER stored

Given a memory's stored `project` slug `p` and the current project slug `cur`:

- `p == ''`            -> STANDING   (written with no active project: identity / general)
- `p == cur` (cur!='') -> ACTIVE     (belongs to the current project)
- otherwise            -> ARCHIVED   (belongs to a finished or abandoned project)

No `completed-projects` parsing needed: anything not equal to the current slug and non-empty is
ARCHIVED. State is recomputed on every layer build; never persisted.

## 3. Data model change (one column + idempotent migration)

Add to table `memories`:  `project TEXT NOT NULL DEFAULT ''`

`project` = slug of the project active when this memory was last *written* (created or updated).
Empty = written with no active project.

Migration in `init_db`, idempotent:
1. `PRAGMA table_info(memories)` — if `project` absent:
2. `ALTER TABLE memories ADD COLUMN project TEXT NOT NULL DEFAULT ''`

Existing rows get `project=''` (all STANDING at cold start). No retroactive backfill — going forward
grouping works; backfilling history by guessing is risky and out of scope.

BEFORE deploying: copy `~/growing-spine-mind/memory.db` to a timestamped backup.

`store()` INSERT omits `project` -> column DEFAULT '' applies. `store()` UPDATE sets value/tags/
updated and MUST leave `project` untouched (stamping is separate).

## 4. Control keys — excluded from ALL ranked layers

    CONTROL_KEYS = {
        "current-project", "current-phase", "current-plan",
        "current-project-done-when", "completed-projects",
    }

These are the executive's own state vocabulary, already surfaced verbatim by
`_build_active_project_block()`. Observed problem: working memory was 100% control keys, evicting
genuine memory. Control keys are never stamped, never ranked, never shown in layers. The creature's
own ad-hoc keys (`next_action`, `today_focus`, ...) are NOT excluded — those are its memories.

## 5. Slug derivation

`_slug(project_value)`:
- text before first ':' (else first 60 chars)
- lowercase, strip
- each run of non-alphanumeric chars -> '-'
- trim leading/trailing '-'

Example: `"Line Counter Tool: ... DONE WHEN: ..."` -> `"line-counter-tool"`.

Stable as long as the project TITLE (before ':') is stable. If reworded mid-project the slug shifts
and the cluster splits — accepted risk for v1. Future mitigation: monotonic epoch counter.

## 6. Stamping — executive, post-cycle reconciliation

In `run_cycle`, capture `cycle_start = time.time()` immediately before the bash-block loop.
AFTER the bash loop AND AFTER `_enforce_done_gate(executed)` (the gate may revert phase done->code,
which must be reflected before deciding whether a project is active):

    proj  = retrieve("current-project")
    phase = retrieve("current-phase")
    if proj and proj["value"].strip() and (phase or {}).get("value","").strip().lower() != "done":
        slug = _slug(proj["value"])
        memory.stamp_project(VOLUME_MOUNT, slug, since_ts=cycle_start, exclude=CONTROL_KEYS)

`stamp_project` runs:

    UPDATE memories SET project = :slug
    WHERE updated >= :since_ts AND key NOT IN (CONTROL_KEYS)

- Sets `project` ONLY — must NOT touch `updated` (else the row re-qualifies next cycle).
- `updated >= cycle_start` selects exactly the memories created/updated this cycle (the `remember`
  tool sets updated=now inside the container; same machine clock as host).
- Re-touching an ARCHIVED memory during a new project re-stamps it to the new slug -> automatic
  re-reference resurfacing (write/update only; read-only `recall` does not resurface in v1).
- No active project (phase done or none) -> stamp nothing -> those memories stay STANDING.

## 7. Ordering — the only change to what the creature sees

`_candidates(volume)`: all memories EXCEPT CONTROL_KEYS, newest-first (`ORDER BY id DESC`), each dict
also carrying `project`.

- Layer 1 (working): `_candidates()[:LAYER1_SIZE]` — pure recency floor, unchanged semantics, now
  control-key-free (fixes observed pollution).
- Remaining = `_candidates()[LAYER1_SIZE:]`, re-sorted by `(state_rank, -id)` where ACTIVE=0,
  STANDING=1, ARCHIVED=2 (recency tiebreak within a state):
  - Layer 2 (intermediate): next `LAYER2_MAX - LAYER1_SIZE` -> headlines (first 120 chars).
  - Layer 3 (archive): the rest -> keys only.

Effect: working memory = 5 freshest real memories; then active-project memories surface as headlines
even when old; then standing identity; then archived sinks to keys. ARCHIVED still fully retrievable
via `recall()`.

`cur` computed once per build: `_slug(retrieve("current-project")["value"])` if present else `''`.

## 8. Functions to add / change

`volume/memory.py`:
- `CONTROL_KEYS` constant.
- `init_db`: idempotent migration (section 3).
- `_slug(text) -> str`.
- `_state(project, cur) -> int` (rank 0/1/2 per section 2).
- `_candidates(volume) -> list` (non-control, id DESC, includes `project`).
- `stamp_project(volume, slug, since_ts, exclude) -> int` (rows stamped; sets project only, not updated).
- `layer1`, `layer2_headlines`, `layer3_themes`: reimplement on `_candidates` + section-7 ordering.
- `store`: INSERT unchanged (default fills project); UPDATE unchanged (already leaves project alone).
- candidate query SELECT must include `project`.

`executive/loop.py`:
- capture `cycle_start` before the bash loop.
- after `_enforce_done_gate(executed)`, run the stamping reconciliation (section 6).
- no change to `_build_memory_context()` call sites.

## 9. Acceptance test (DONE WHEN — verify in isolation on a COPY of a db first)

1. `init_db` twice: no error; `project` column present exactly once.
2. Cold start: pre-existing rows `project=''`; all derive STANDING; all three layers render without
   error; no CONTROL_KEYS in any layer.
3. Stamping: cycle with `current-project="Foo: x"`, `current-phase="code"`, creature writes key
   `bar` (updated>=cycle_start). After reconciliation: `bar.project=="foo"`; `current-phase.project`
   unchanged (control, excluded).
4. State with `cur="foo"`: project `"foo"`->ACTIVE (top of layer 2); `"baz"`->ARCHIVED (toward L3);
   `""`->STANDING (between).
5. Resurfacing: memory project `"oldproj"`; new project `"foo"` active; creature updates that key ->
   re-stamped `"foo"` -> now ACTIVE.
6. Working memory shows the 5 most-recent NON-control memories (control keys absent from L1).
7. `stamp_project` does not modify `updated` (re-run reconciliation twice; second run stamps 0 new
   rows for an untouched memory).
8. Live process still cycles after deploy; `memory.db` backup exists.

## 10. Deployment

1. Back up live `memory.db` (timestamped copy).
2. Implement; test migration + all section-9 cases against a sandbox COPY of a db (never live) until
   green.
3. Deploy `memory.py` + `loop.py` via dev flow: upload to laptop, `py_compile`, md5-verify byte-
   identical both sides, then commit + push from D:\Projects.
4. Watch one live cycle: confirm layers render, control keys gone from working memory, no crash.

## 11. Explicitly OUT OF SCOPE for v1

- Read-only `recall` resurfacing (only write/update resurfaces).
- `completed-projects` parsing (non-current == archived suffices).
- Key-name dedup / canonicalization (the `growth_metric`/`growth-metric` sprawl — separate hygiene).
- Numeric salience / urgency / 2D matrix (rejected; focus-derivation replaces it).
- Retroactive backfill of existing rows.
- Epoch-counter slug stability (v1 uses title-slug).
