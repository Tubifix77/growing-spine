# CLAUDE.md — working on Growing Spine

You are working on a live autonomous creature, not a codebase at rest. It runs
24/7 on the Debian laptop, writes its own tools, and cannot be paused politely.
Read this before touching anything; it is short on purpose.

Tue is the human. Prefer asking him over guessing on anything irreversible.

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

## 8. State at handover (2026-08-07/08)

v0.15. HEAD `82e28ae`. 224 tests green. ~346 own tools, only **8 never invoked**.
900–1300 thinks/day, exec_skip ~3–7% (was 14.9%). **Zero open audit findings** —
all 67 verdicted, all 28 that were open are fixed.

Beware stale snapshots: `docs/creature-snapshot-2026-08-02/` predates the 6 August
repairs. On 2 August the hollow backlog was 23; the organ was re-armed on the 6th
and the creature drained it itself, implementing eight demanded stubs in demand
order. **Live backlog is 1.** The janitor's first non-zero line, `aged-out 14`,
was 6 August. Always take the live census before acting on snapshot numbers.

**Needs Tue's decision**
- Rotate the OpenRouter API key (it was exposed in a chat transcript).
- 2026-08-17: cerebras free tier changes. **Probe before flipping** — it served
  217 thinks in a day, a real workhorse. `groq_oss120` is the same model but
  TPM-walled at 8000, so it cannot take fat thinks.
- `WIRING:!!` flags `memstore.jsonl` at two paths — a NEW instance of the
  scattered-data class *after* the contract fix. The named trigger for
  reconsidering a path-resolver framework tool.
- `autoquestionplanner`: a complete 78-line bash implementation sits BELOW the
  Python stub template with a `python3` shebang, so it runs the stub, prints
  "not implemented yet", exits 0, and the real code never executes. It is the
  creature's own tool — needs its consent, not a unilateral fix. No urgency: the
  janitor attics, it does not delete.

**No decision needed**
- ~86 replies/day still end `finish=length`, mostly gemma, after the think cap
  went 2048 → 3072. Best measurable target left.
- Delete `~/archive-merge-backup-*` once the merged archive has proven itself.

**Watching only, deliberately**
- `tool-tester` is a hollow stub; the janitor will attic it. Its call.
- The creature believes `container_status = no_shell_exec_possible`. False, and
  producing no symptom. Leave it.
- Several of its tools build JSON with `jq -n` (pretty) and append to `.jsonl`.
  It has been told the pattern. Its call.
- ~28 duplicate-stem twins (`X` and `X.py`) with traffic split across both. Not
  yet investigated; culling needs consent.

**Known issues, deliberately NOT built** — reasoning is in memory; do not
re-propose without new evidence.
- *Size-aware routing.* A learned "this rung can't take fat prompts" ceiling
  ratchets downward and never announces it — the same disease we spent a week
  removing. If ever built: declared numbers in config, and the detector SHOUTS
  rather than re-routes.
- *Catalogue v2.* The full listing still enters every wake. Current state has a
  measured cost and no symptom; alternatives trade it for unmeasured risk.

**Monthly ritual.** We ask the creature what made its work harder; it answers
once — it has **no way to speak unprompted** — then we investigate and report
back. First run 2026-08-07 surfaced a real two-month-old framework bug. Next due
early September. Ask for symptoms, never causes, and **with a time window**:
every item it named came from June, because recent state lives in a five-slot
register that overwrites each cycle.
