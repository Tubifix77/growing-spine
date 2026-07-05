# DEV LEDGER — the dev/assistant working reference (NOT for the creature)

Read this FIRST each session, before any log forensics. It is the fast
operational map: what's live vs stale, what's open, what's fixed (with dates),
and known scars. It lives in the repo on the host — outside the creature's
container mounts (`/mind`, `/workspace`) — so the creature never sees it.

Deep lessons and design narrative live in `growing-spine-architecture.md`.
This file is the index + status, kept to one-liners.

**Discipline**
- Every issue gets a discovered-date; when resolved, a fixed-date + commit.
- **SCARS** = fixed issues whose symptoms can recur. Keep the signature so a
  reappearance is a 5-second lookup, not a re-diagnosis.
- The **LIVE STATE** section must be REGENERATED from the running system each
  session — never trusted from memory or old logs. Reading stale data as
  current is the exact failure this file exists to prevent.

---

## LIVE STATE  (regenerate from the system — as of 2026-07-05 ~10:47 UTC)

- Running: HEAD `9a6ab7e`, v0.10.1; single brain; systemd active; container up.
- Disk 83% (~19 GB free). Tools ~256 (grows as it builds). Hollow backlog ~6
  (tolerance 3), draining from a peak of 41.
- Logs: systemd **journal** (timestamped). Read with
  `journalctl --user -u growing-spine --since "6 hours ago"` or `-b`.
  The flat `~/growing-spine.log` is FROZEN history — do not grep it whole.
- **LIVE memory/state** (written continuously): `memory.db` (core working
  memory), `journal.jsonl` (append log, ~37 MB), `tool_usage.json`,
  `ideation_state.json`, `retrospective_state.json`.
- **STALE / VESTIGIAL — do NOT treat as current memory:**
  - `keyword_archive.jsonl` (/mind): 221 real notes, but FROZEN since 2026-06-26.
  - `memstore.db`: fixed + working, but EMPTY and unused by the creature.
  - `memarch/`: June test files only. `memstore.json`: one June test key.
  - `/workspace/keyword_archive.jsonl`: ~15 test notes (search's old sandbox).

> Baked-in lesson: on 2026-07-05 the assistant spent hours on the keyword_archive
> subsystem and called a fix "highest-value" while the creature's ACTUAL live
> memory (`memory.db`) sat unexamined. This section exists so that never repeats.

---

## OPEN — found, not yet fixed

- **[2026-07-05] Archive consolidation.** 3-way path fragmentation
  (keyword_archive /mind, memarch, memstore) + keyword_archive writes quiet
  since ~06-26. Design call: pick a canonical store, retire the vestigial ones.
  LOW urgency — core `memory.db` is healthy.
- **[2026-07-05] Is the creature still WRITING new knowledge since ~06-26?**
  Write-side mirror of the search fix — check whether archiving still lands or
  the habit lapsed. Verify against LIVE STATE, not old data.
- **[2026-07-05] No guard for "silent wrongness."** Tools that run but do the
  wrong thing (path mismatches, mock data) are invisible to the done-gate and
  hollow-gate. Candidate: periodic behavior-probe of the most-used tools.
- **[2026-07-05] `wake_catchup_fetcher` is a static MOCK** (fake "Mock News
  Item"), 312 uses. Real fetcher possible (container has network). Creature-
  design call.

---

## FIXED — discovered -> fixed (commit)

- **keyword-archive-search read the wrong file.** Disc 2026-07-04, fixed
  2026-07-05 (`9a6ab7e`): repointed /workspace test sandbox -> /mind (221 real
  notes). NOTE: peripheral/stale subsystem (frozen 06-26); real value LOW —
  was oversold at the time.
- **memstore ephemeral path.** Disc 2026-07-04, fixed 2026-07-04: /var/memory
  -> /mind + mkdir + stripped corruption. Root cause (persistence-knowledge
  gap) fixed in `protected-prompt.md` (`fc54ad1`). NOTE: memstore still unused.
- **Logs not timestamped.** Fixed 2026-07-05 (`459060a`): flat file ->
  systemd journal.
- **v0.10.1 yank ban-ordering.** Fixed 2026-07-04 (`802c0fa`): ban armed only
  after the redirect lands, so a failed yank leaves no silent ban.

---

## SCARS — fixed, but watch for recurrence (signature + when)

- **`AttributeError: 'Keychain' object has no attribute 'available_providers'`**
  in `runtime.py` `wake_entry`. Crash-loop ~late June (journal region
  ~lines 39962-40228), fixed in the v0.9.3 quota rewrite (caller updated to
  inline `qs.is_exhausted`). Recurrence = caller/keychain method drift.
  4700+ clean wakes since.
- **v0.10 rut detector "never fires" is NOT a bug.** The basin never enters
  through the creature's judged picks, so the streak stays 0. Do not "fix" the
  keying — wrong layer. Recorded so it isn't re-investigated as broken.
