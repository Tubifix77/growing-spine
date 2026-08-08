# CLAUDE.md — working on Growing Spine

You are working on a live autonomous creature, not a codebase at rest. It runs
24/7 on the Debian laptop, writes its own tools, and cannot be paused politely.
Read this before touching anything; it is short on purpose.

Tue is the human. Prefer asking him over guessing on anything irreversible.

**This file is yours.** You are the session with hands on this system; there is
no other reviewer to defer to. Maintain it: when a measurement contradicts §8,
correct §8 and commit. When you learn a rule the hard way, add it to §5. Date
what you write and name the instrument behind every number — the most expensive
errors in this project's history are numbers nobody could source.

---

## 1. Read these first, in this order

| What | Where | Note |
|---|---|---|
| `DEV-LEDGER.md` | laptop `~/growing-spine/DEV-LEDGER.md` | **gitignored, laptop-only.** STATUS blocks newest-first + LIVE STATE / OPEN / FIXED / SCARS. The best orientation document that exists. A *record*, not an onboarding file. |
| `audit/RE-INSPECTION-2026-08-06.md` | both machines, **gitignored** | Per-finding verdict record for all 67 static-audit findings. |
| Assistant memory | `D:\AI\claude-memory\memory.md`, section "Growing Spine" | Doctrine, scars, standing decisions. Read that section, not the whole file. |
| `growing-spine-architecture.md` | this repo | Design + version history. |

`audit/` and `DEV-LEDGER.md` are gitignored deliberately: **this repo is public**,
and those files are a file-and-line map of a running system's failure modes.
Never commit them. Never commit `config.yaml` — it holds API keys.

---

## 2. Hard boundaries

1. **Never edit `~/growing-spine-mind/tools/own/`.** Those are the creature's own
   tools — its world, not ours. Exception: explicit consent from the creature in
   chat, for a specific job. Even then: back up first, and tell it exactly what
   you changed, including anything you changed beyond what it agreed to.
2. **`framework-tools/` is protected scar tissue.** Do not "improve" it. Never
   point `py_compile` at it — a planted `__pycache__` once emptied the creature's
   toolset for four days; it hit the hole 715 times and blamed its own tools.
3. **Never run `tests/test_sandbox.py`.** It stops the live container.
4. **Restart the brain BEFORE killing the body.** A respawned container inherits
   the running brain's in-memory code, not the disk's.
5. **Never tell the creature about its own bugs**, and never delete its junk or
   `.bak` files — they are its safety net. Chat is world-facts only: no offers,
   no debugging hints, no advice.
6. **Culls need its consent.** Ask, offer alternatives, honour what it keeps.
7. **World-RULE changes are announced in Tue's voice and are Tue's call.** Draft,
   show him, send after approval. Announcements match the code's wording verbatim.
8. **The janitor ATTICS, it does not delete** (`os.replace` into `tools/attic/`).
   Nothing is destroyed by a sweep, so "rescue it before the janitor eats it" is
   never a reason to skip asking the creature first.

---

## 3. The gate

```bash
cd ~/growing-spine
python3 tests/test_loop_v2.py > /tmp/s.out 2>&1; echo "GATE=$?"
grep -c '^PASS' /tmp/s.out; tail -1 /tmp/s.out    # must say ALL TESTS PASS
```

- **To a file, never a pipe.** A pipe once swallowed `sys.exit(1)` and let an
  ungated commit ship.
- Check the literal string `ALL TESTS PASS`, not just the exit code.
- "N tests green" always means `test_loop_v2.py` alone. Four legacy files live in
  `tests/legacy/`.
- Code changes need `systemctl --user restart growing-spine` to load. Prompts and
  markdown are re-read every cycle.

---

## 4. Canonical helpers — never write a second copy

The central lesson of this codebase: a producer and a checker that share a
literal **will** drift, and no test notices.

- `volume/paths.py` → `mind_root()` — one derivation of the mind root (was five).
- `volume/tools.py` → `tool_description()`, `is_tool_file()` / `list_tools()`
  (the isfile check lives in the lister because callers kept forgetting it),
  `tool_stem()`, `demand_counts()`, `TOOL_PLACEHOLDER_MARKERS` / `is_hollow_stub()`.
- `executive/loop.py` → `TOOL_CLUSTERS` (one taxonomy: label + member_kws + title_kws).
- `executive/embed_gate.py` → `refresh_standard()`, `_is_junk()`.

If you need one of these behaviours, import it. If you are about to write a regex
or a path literal that already exists elsewhere, stop.

---

## 5. Scars — signatures, so a recurrence is a lookup not a re-diagnosis

- **A guard whose count is always exactly zero is broken, not idle.** The stub
  janitor logged `aged-out 0` twenty-eight times with 25 stubs in front of it,
  because the template and the detector were four words apart.
- **Never let a test write its own fixture using the string the detector hunts.**
  That test passes forever regardless.
- **A guard that names one exact string is one rename away from silent.** The
  SENSOR looked for the title `"Mock News Item"`; the creature's fixture said
  `"Test Article 1"`, and the guard built to catch mocks reported
  `SENSOR:ok(2 fresh)` over two `example.com` articles (2026-08-08). Test a fact
  about the world where you can — RFC 2606 reserves `example.com` so it can
  never carry real content — and keep phrase lists as backstop only.
- **A fixture written OVER a live tool is a stub that lies.** `cat > <tool path>`
  bypasses `tool-edit`, so there is no `.bak` and no "Rewrote X (44 -> 89 lines)"
  line: the change leaves no trace anywhere. `wake_catchup_fetcher` became a
  two-item mock this way and 55 dependent tools kept exiting 0 with valid JSON.
  A stub does nothing; a fixture does something false. Both look healthy.
- **Read model replies from the END.** Three parsers needed this cure: the retro
  verdict, the architect ruling, the chat reply. A model that muses about an
  answer before giving it will mention the tag or the verdict mid-thought.
- **A normalisation mismatch between two halves of one comparison** yields a
  plausible wrong number, not an error. Stem-normalised keys compared against raw
  filenames once reported 67 unused tools; the truth was 8.
- **Instrument beats inference.** `journalctl --utc` formats output as UTC but
  parses `--since` in LOCAL time. Wakes are not cycles.
- **A contract that specifies durability but not identity** produces obedient
  tools that cannot find each other's data. Say *where*, exactly — not *which volume*.
- **Documentation that shows a convention imprecisely gets obeyed literally.**
  The contract showed the tool header without `#`, so files died with
  `tool:: command not found` for two months.
- **YAML's Norway problem:** a bare `off`/`on`/`yes`/`no` key parses as a boolean.
- **Tests that assert a MECHANISM go red when you improve the mechanism.** Assert
  the contract instead.
- Re-verify any "it started" claim a beat later. Fixtures come from the real
  corpus, never authored. Never call `_build_tool_catalogue()` just to inspect it
  — it ends in `_mark_surfaced()` and writes rotation state.

---

## 6. Standing decisions (Tue's)

- **Quality floor over capacity.** No weak model in the ladder: under a shared
  cap, weak calls starve smart rungs and a weak author's buggy tools are lasting
  pollution. `openrouter/free` auto-routing stays rejected.
- **Reversible actions are just done**, not asked about.
- **If a test is quick and nothing live is at risk, why is it waiting?** A net
  that has never fired is not evidence of calm water — bench the extinguisher.
- **Don't tune a constant with no evidence** — that is how voodoo constants are born.
- **Don't fix what has no symptom.** Measured cost beats theoretical harm.
- Distinguish a hold with a NAMED trigger and date (legitimate) from a hold
  waiting on "more information" (inaction in the costume of caution).

---

## 7. Ops

```bash
systemctl --user restart growing-spine            # brain (needed after code changes)
systemctl --user restart spine-observer.service   # dashboard
systemctl --user --failed                         # a traffic-carrying rung went silent
grep SERIOUS ~/spine-health.log                   # same, in the log
tail -3 ~/spine-health.log                        # JANITOR / WIRING / FLATLINE / STALE-FALLBACKS
journalctl --user -u growing-spine --since "2 hours ago"
```

- **Always scope `journalctl` with `--since` or `-b`.** The flat
  `~/growing-spine.log` is frozen history and re-surfaces long-fixed scars.
- Creature's volume: `~/growing-spine-mind` (`/mind` in the container). Its
  workshop: `~/growing-spine-workspace` (`/workspace`).
- Both machines push AND pull; GitHub is the hub. No file shuttling.
- Driving the laptop over an MCP bridge: **keep payloads small.** Large heredocs
  and long-running commands wedge it. Native bash on the laptop has no such issue.

---

## 8. State — 2026-08-08 20:45

**This section goes stale fast. It is yours to maintain: when you measure
something that contradicts it, correct it and commit. You do not need
permission for that.** The first version of this file was already nine hours
stale at the moment it was committed — it said `tool-tester` was a hollow stub
when the creature had finished it four hours earlier. Date what you write, name
the instrument, and prefer a live census to any figure in here.

v0.15. 229 tests green. 359 own tools. 900–1300 thinks/day. (No HEAD hash here:
a file cannot name the commit that contains it, so the line was stale on arrival.
Use `git log -1`.)
**Zero open audit findings** — all 67 verdicted, all 28 that were open are fixed.

**LIVE NOW — `wake_catchup_fetcher` is a mock (measured 2026-08-08 20:29).**
At 17:14 the creature wrote a fixture over the real tool to get deterministic
input while testing `cross_source_digest_scheduler`: `cat > /mind/tools/own/…`,
which bypasses `tool-edit`, so no `.bak` exists. It emits two `example.com`
articles. **55 live tools call it**, all still exiting 0. The real implementation
survives as `wake_catchup_fetcher.real` (541 b, 28 Jun). The SENSOR now catches
this (`SENSOR:MOCK(!!)`, verified against the live mock) — it did not before.
**Restoring it is the creature's call, not ours: §2.1. Not yet asked.**

**Measured 2026-08-08 20:29 by live census:**
- **Hollow backlog: 0**, held all day across 42 tool edits. `tool-tester` is
  implemented — 3,569 bytes, 103 lines, written 2026-08-07 19:30, after the
  creature was told plainly that nothing would prompt it to.
- `finish=length` by full calendar day: 19.0% (6 Aug) → 13.0% (7 Aug) →
  **8.0% (8 Aug)**. Falling steadily; 69 events today against 116 yesterday.
- **Two persistent stores were emptied on 8 Aug and neither is restored.**
  `/mind/data/keyword-archive.jsonl` went 193,665 b (03:26) → 5,105 b, 29
  entries, all dated that day, oldest 12:11. `/workspace/planner.json` hit 0 b
  at 13:09, one minute before `step-planner-tracker` was repointed to
  `/mind/data/step-planner/`. The planner loss is an unmigrated path change; the
  archive mechanism is **undetermined** — ruled out: our framework touches the
  archive nowhere, no exec block in 03:26–12:11 names the file, and every
  surviving archive tool is append-only. **Do not restore until the cause is
  known** (Tue, 8 Aug). Do NOT delete `~/archive-merge-backup-*` — it is now the
  only copy of the pre-loss content.
- The pre-loss archive was **422 real entries but 99.4% unparseable as JSONL**
  (multi-line pretty JSON, one object over many lines), so the creature's own
  line-based `keyword-archive-search` could ever read only 18 of them. The
  rewritten `keyword-archive-store` still writes multi-line. The loss is smaller
  than 193 KB suggests — most of it was already unreadable to its owner.
- **The keyword-archive path split has resolved itself.** Seven live tools now
  agree on `/mind/data/keyword-archive.jsonl` (still actively written; it was
  193 KB when this was first measured — see the emptying above),
  including the `keyword-archive-store` / `keyword-archive-search` pair behind
  the 1,670-writes / 934-empty-reads scar. The creature converged its own wiring
  on the evening of 7 August. **This is evidence for the path-resolver decision:
  the high-traffic case fixed itself without a framework resolver.**
- `autoquestionplanner` — the complete bash body sitting below a Python stub — is
  attic'd and intact. Not urgent, and not ours to fix: it is the creature's tool.

**Ignore `docs/creature-snapshot-2026-08-02/` for anything numeric.** It predates
the 6 August repairs, when the stub organ was re-armed and the creature drained
its own backlog (eight demanded stubs implemented in demand order, 52–107 lines
each). Its MANIFEST's usage counts produced a "half the library never invoked"
figure; the true never-invoked count is single digits.

**Needs Tue's decision**
- **Rotate API keys.** OpenRouter, Gemini, Groq ×2 and Cerebras have all been
  exposed in transcripts by `cat`-ing `config.yaml`. **Grep that file for the one
  field you need; never dump it.**
- 2026-08-17: cerebras free tier changes. **Probe before flipping** — it served
  235 thinks since 7 August, a real workhorse. `groq_oss120` is the same model
  but TPM-walled at 8000, so it cannot take fat thinks.
- `WIRING:!!` still flags `memstore.jsonl`: `/mind/data/memstore.jsonl` is 0
  bytes and read by `ToolUsageAuditor`; `/mind/memstore.jsonl` holds 236 bytes
  and is read by `RecallScheduler`. **A live tool whose job is auditing tool
  usage is reading zero bytes and returning nothing without error** — the
  house scar, in its own toolkit. Its tool, so its consent.

**Open, measurable**
- `finish=length` by full calendar day, from `served_by` events: 187 on 6 Aug
  (19.0%), **116 on 7 Aug (13.0%)** — falling after the think cap went
  2048 → 3072. By count `google_gemma` dominates (83 of 119 since 7 Aug); by
  **rate** `openrouter_super` is worst at 19.8% against gemma's 11.8%. Pick your
  target: fewest wasted calls, or the worst-behaving rung.
- `gemini_flash` (the `is_floor: true` rung) has served 9 requests since 7 Aug.
  `spine-flatline.service` sitting in `failed` is the alarm working as designed.
- Delete `~/archive-merge-backup-*` once the merged archive has proven itself.

**Watching only, deliberately**
- The creature believes `container_status = no_shell_exec_possible`. False, and
  producing no symptom. Leave it.
- Several of its tools build JSON with `jq -n` (pretty) and append to `.jsonl`.
  It has been told the pattern. Its call.
- **31** duplicate-stem twins (`X` and `X.py`) with traffic split across both
  (live census 2026-08-08 03:25; the "~28" that stood here was the 2 Aug
  snapshot figure — it is growing, not static).
  Culling needs consent, and the honest cull list has been small every time it
  was measured.

**Known issues, deliberately NOT built** — do not re-propose without new evidence.
- *Size-aware routing.* A learned "this rung can't take fat prompts" ceiling
  ratchets downward and never announces it — the same disease this project spent
  a week removing. If ever built: declared numbers in config, and the detector
  SHOUTS rather than re-routes.
- *Catalogue v2.* The full listing still enters every wake. Current state has a
  measured cost and no symptom; alternatives trade it for unmeasured risk.
- *Path-resolver framework tool.* The trigger was a recurrence after the contract
  fix — but the high-traffic case then resolved itself. Weaker case than it looked.

**Monthly ritual.** Ask the creature what made its work harder; it answers once —
it has **no outbound channel** — then investigate and report back. First run
2026-08-07 surfaced a real two-month-old framework bug (the contract showed the
tool header without `#`, so obedient files died with `tool:: command not found`).
Next due early September. Ask for symptoms, never causes, and **with a time
window**: every item it named came from June, because recent state lives in a
five-slot register that overwrites each cycle.
