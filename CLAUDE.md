So the block is
the missing payment method — and since this ladder is free-tier-only and always
will be, that makes cerebras **defunct for us**, not merely dark. **Retired
2026-08-26** (`enabled: false`, dated comment naming the migration): the rung
entry is kept rather than deleted, `CEREBRAS_API_KEY` is now withheld from the
container (verified 0 tools reference it), and the walled-rung probe and its
permanent `SERIOUS` both stop. I first put this to Tue as a money decision; it
never was one, and his standing free-tier constraint had already answered it.# CLAUDE.md — working on Growing Spine

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

## The method — read this before you fix anything

Every rule in §2 is an instance of these two.

**1. When the creature builds a defective tool, you do not fix the tool.**
Not the obvious one-line fix, not when the fault is costing something every
cycle, not when you are certain. Its tools are its world. Instead:

- Ask *why it built the fault*, and — separately, this is the harder half —
  *why it cannot see the fault now*. The second question is where the framework
  bug usually is.
- **Fix the machine that produced the fault**, never the fault. A `cat >` that
  leaves no `.bak`, a guard hunting one literal string, advice that named a
  mechanism instead of an invariant.
- Then **make the fault visible to the creature** so it can prune it itself,
  deterministically and without being asked. It cannot request a check for a
  problem it does not know it has, so a tool it must choose to run is worthless
  here — the fact has to arrive unprompted, the way the gate fact does.
- State the **invariant** ("one record per line"), never the mechanism to avoid
  ("don't use `jq -n`"). It has no outbound channel and cannot ask which you
  meant; it will obey the letter and rebuild the fault by another route.
- Surface on a **change of state, never continuously**. A fact repeated every
  cycle is a nag it learns to skip, or a trap it cannot exit when it looks and
  finds nothing it can fix.
- **STOP THE BLEEDING FIRST, and that is not an intervention.** If one of its
  tools is wedging the system, kill the processes and respawn the body
  immediately — no consent, no discussion, no waiting. **Its TOOLS are its world;
  its PROCESSES are not.** A process is ephemeral and the body is disposable by
  design; killing one changes nothing durable. `ensure_body` already does the
  automated version of exactly this. Only after the bleeding stops does the method
  below apply, and by then there is time to follow it properly.
  Two things to keep straight when judging the emergency. **A runaway tool cannot
  starve the host**: the container is capped at 1.5 of 4 cores and 1 GB, hard, so
  the "148%" of 2026-08-14 WAS that cap, not the box being taken. The genuinely
  unbounded resources are **disk** and **PIDs** — and the only thing that has ever
  wedged the whole spine was PID exhaustion, which was our `sleep infinity`, not
  its tool. So measure before you conclude its tool is the emergency.
  And if a hand had to intervene at all, **that is the finding**: the framework
  was missing a bound. The fix is the limiter — a cap, a timeout, a reaper — never
  an edit to its tool. `run_command` times out at 300 s, but that binds the EXEC
  and not the children it backgrounds, which is how 49 orphans accumulated.
- Direct intervention IN ITS TOOLS only if it is genuinely stuck, and only after
  discussing it with Tue. Consent in chat is the floor, not the ceiling.

**2. You are the framework's debugger, not the creature's nanny.**
It is meant to stand alone, permanently, with nobody watching. So:

- **Never build anything that makes it depend on your inspection.** If a fault is
  only caught because a human or a session reads a log, it is not fixed.
- An instrument only *we* can read buys better supervision, not autonomy. When
  you add detection, say plainly who receives it — and prefer the creature.
- Your job is to find and remove framework faults that block its effectiveness.
  It is not to do its work, tidy its library, or keep it out of trouble.

---

## 1. Read these first, in this order

| What | Where | Note |
|---|---|---|
| `DEV-LEDGER.md` | laptop `~/growing-spine/DEV-LEDGER.md` | **gitignored, laptop-only.** STATUS blocks newest-first + LIVE STATE / OPEN / FIXED / SCARS. The best orientation document that exists. A *record*, not an onboarding file. |
| `audit/RE-INSPECTION-2026-08-06.md` | both machines, **gitignored** | Per-finding verdict record for all 67 static-audit findings. |
| Assistant memory | `D:\AI\claude-memory\memory.md`, section "Growing Spine" | Doctrine, scars, standing decisions. Read that section, not the whole file. |
| `growing-spine-architecture.md` | this repo | Design + version history. |
| `.claude/skills/README.md` | this repo | The eight `/gs-*` standing inspections and the rule that keeps them from drifting out of sync with this file. |

`audit/` and `DEV-LEDGER.md` are gitignored deliberately: **this repo is public**,
and those files are a file-and-line map of a running system's failure modes.
Never commit them. Never commit `config.yaml` — it holds API keys.

---

**The `/gs-*` skills carry PROCEDURE; this file carries DOCTRINE.** Eight standing
inspections live in `.claude/skills/` — `gs-bug-daily`, `gs-products`, `gs-vitals`,
`gs-ladder`, `gs-data`, `gs-instruments`, `gs-directives`, `gs-secrets`. Each one
mandates exactly what must be inspected, so a check is never the whim of the day,
and each ends with a pointed open pass plus one blank pass, because a pure
checklist is blind to whatever it was written before: on 2026-08-19 three
instruments were all correct and the creature had been down twelve hours, and the
gap was found by an open-ended look. **Anything a blank pass finds that mattered
becomes a mandated item there, dated.** When you correct a scar, correct it HERE —
the skills point at §5 rather than quoting it, so one edit is enough. **They run in
the inspection session, never on the laptop** — the laptop runs the creature, this
session watches it from outside over the bridge, and the creature never sees them.
Each appends one record per run to `gs-history/<name>.jsonl` in the checkout,
gitignored for the same reason `audit/` is, which is what turns snapshots into
trends.

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
  `tool_stem()`, `demand_counts()`, `TOOL_PLACEHOLDER_MARKERS` / `is_hollow_stub()`,
  `tool_start_failure()` / `tool_syntax_error()` / `looks_like_python()` — the ONE
  startability predicate, called by the done-gate, the in-loop warning and any
  census. It never executes a tool.
- `executive/loop.py` → `TOOL_CLUSTERS` (one taxonomy: label + member_kws + title_kws).
- `executive/embed_gate.py` → `refresh_standard()`, `_is_junk()`.

If you need one of these behaviours, import it. If you are about to write a regex
or a path literal that already exists elsewhere, stop.

---

## 5. Scars — signatures, so a recurrence is a lookup not a re-diagnosis

- **`journalctl` is the FRAMEWORK's stdout. What the creature DID is in
  `~/growing-spine-mind/journal.jsonl`.** Measuring the creature from journald
  undercounts everything, silently, because most of its record never goes to
  stdout. On 2026-08-18 this produced three wrong numbers in one session:
  "`served_by` is no longer greppable" (it is, in the journal file — 1,148 records
  on 08-17), "0 exec blocks in three hours" (there were 595 that day), and "only
  one wake fell in the dead window" (there were 152 thinks and **202 exec
  blocks**). Worse, that file keys on **epoch `ts`, not a date string**, so
  `grep '2026-08-18' journal.jsonl` returns 3 coincidental hits and reads exactly
  like a quiet day. Parse `ts` with `time.localtime`; never date-grep it.
- **An observation channel that truncates silently manufactures rational-looking
  repetition — and a repeat-suppressor stacked on it punishes information-seeking.**
  The creature's entire view of any command's result was ~286 chars: exec results
  journalled `stdout[:300]`, commands `cmd[:200]`, and the wake render cut
  `content[:300]` again — all with NO marker, so a 4KB `cat` looked complete.
  14-day census, 2026-08-25: **127 streaks** of the shape the loop warning fires
  on; **102 with capped output**; 89 raw `cat`s of its own tools; **44 where the
  warning's "same result" was false**; 23 distinct long commands collapsed into
  false repeats by the 200-char cap (tool-edit heredocs — four different edits of
  one tool read as one command four times, and it was told to stop editing the
  tool it was upgrading). It tried `base64 FILE`, `python3 -c
  "print(open(...).read())"` and `cat $(which ...)` to widen a pipe that does not
  widen, then called the ban "a trap" in its own reasoning and stalled three
  cycles. Fixed `c733adc`: **truncation must announce itself wherever it cuts**
  (`_capped`, one marker, named constants shared by writer, render and warning);
  **a detector must not count what truncation destroyed** (capped commands are
  identity-unknown and never counted); and the warning now **checks the results
  it makes claims about**, saying one of three true things — complete-identical
  (act; extracting different information is fine), truncated (repetition cannot
  widen the window; transform in-block or extract a range), differed (decide what
  the changing answer is for). The "any reworded form" ban is gone: the detector
  sees exact strings only, and banning a space it cannot observe is how the trap
  was built. Prior art both ways: SWE-agent's ACI (arXiv:2405.15793) replaced raw
  `cat` with windowed viewing under explicit limits; ProcCtrlBench
  (arXiv:2605.20251) names the class — duplicate steps arise when the agent lacks
  evidence that a call resolved its uncertainty. The old B4 test asserted the trap
  phrase AS A REQUIREMENT — a mechanism test defending the fault.
- **A status field is not liveness. Prove it by doing.** `ensure_body` returned
  True on `docker inspect .State.Running`, which reads `true` for a container
  whose PID namespace is full and which cannot fork a single process. The body sat
  like that for **three and a half hours** on 2026-08-18 while every tool call the
  creature made returned an OCI error, and the liveness check called it alive on
  every cycle. Ask the thing to DO something; never accept its own report of its
  own health. The house disease wearing the health check as a costume.
- **An init that never calls `wait()` turns every orphan into a permanent
  zombie.** The body ran as `docker run ... sleep infinity` with no `--init` since
  the beginning. `sleep` does not reap, so anything the creature backgrounded, or
  anything whose parent exited first, accumulated forever: **9,082 zombies between
  08-16 20:20 and 08-18 04:11**, when `pids.current` hit 9085 against a
  `pids.max` of 9090 and the namespace was full. Invariant: **PID 1 in any
  container we start must reap.** Instrument: `pids.current` / `pids.max` in the
  container's cgroup, and `ps -eo stat | grep -c ^Z`.
- **A cost that scales with the creature's own growth is a bomb with no error
  message.** `_tool_dependencies` re-searched every file once per tool name:
  433 x 433 = **187,489 full-content regex scans per wake, 28.3 seconds**,
  measured 2026-08-18. Nothing failed, nothing logged, and it got worse every
  time the creature built a tool — the load parameter was its success. It was
  found because Tue could HEAR the fan, which is not an instrument this system
  owns. **It does now:** `loop._record_wake_cost` times `_build_context` on every
  cycle (every per-cycle builder lives inside it, so anything added later is
  covered by construction), edge-triggers one line into the brain's log when the
  median crosses `WAKE_COST_BUDGET_MS` = 5,000, and the daily health line carries
  `WAKE:p50 …ms max …ms` either way so the trend is visible without the threshold
  having to be right. Budget DECLARED, never learned — an adaptive one ratchets
  along with the fault and never says so. Costs 0.35 ms/cycle on the laptop.
  Still: when you write a scan over its library, state what happens at 1,000 tools.
- **Boundary groups that CONSUME their delimiter drop adjacent matches
  silently.** `finditer` returns no overlapping matches, so the rewritten
  dependency scan had to use lookaround: with consuming groups,
  `"store_item plan_step"` yields only `store_item` — the space is eaten and the
  next edge vanishes, producing a smaller plausible graph and no error. Verified
  by mutation 2026-08-18, which is the only reason it is known.
- **An instrument that cannot run must say UNKNOWN, never FAULTY.** Building the
  shell half of the startability check, `bash -n` was handed a temp file it could
  not open and returned nonzero — so a perfectly valid script was reported broken,
  which is the house disease inside the checker itself. Then text-mode newline
  translation made bash receive a trailing CR and reject valid bash. It now feeds
  BYTES on stdin, and before believing any rejection it proves bash still parses
  `true`. Whenever a checker's failure and its subject's failure look the same,
  make the checker prove itself first.
- **An error message can be written into a file AS the program.** `extract-key-insights`
  has, as its entire line 1, `Error: LLM call failed: ask: HTTP 429 from provider:
  {"error":{"message":"Rate limit rea` — a failed LLM call's output piped into
  `tool-edit`. `ask` reported that failure honestly on stderr with a nonzero exit;
  one of the creature's own wrappers converted it to stdout text, and the text
  became a tool. This is why the 10% of its tools that RETURN error strings as
  their value matters: it does not merely mislead a caller, it manufactures broken
  programs. Note the honest limit of detection here — a single line of prose can be
  syntactically valid shell, so this class is caught only when it leaves something
  unterminated, which a truncated JSON error does.
- **A guard whose count is always exactly zero is broken, not idle.** The stub
  janitor logged `aged-out 0` twenty-eight times with 25 stubs in front of it,
  because the template and the detector were four words apart.
- **Never let a test write its own fixture using the string the detector hunts.**
  That test passes forever regardless.
- **A provider's own response headers are the only trustworthy source for its
  limits.** This file's `groq: limit 14400` matched a curated free-LLM list
  exactly — and was wrong: Groq publishes 1,000 RPD and the account's
  `x-ratelimit-limit-requests` returned `1000`. Vendors increasingly publish
  nothing at all (Google's rate-limit page defers to the signed-in AI Studio
  dashboard; Mistral's tier page to a signed-in Limits panel), which is exactly
  why the stale community lists get quoted. So when adding or re-verifying a
  rung: make ONE live call and read `x-ratelimit-*`. Lists are for discovery,
  docs are a sanity check, headers are the fact. And check whether the numbers
  you actually need are even returned — Mistral gives per-minute only, so the
  size of its free allowance is invisible until it runs out.
- **A ladder's default for an unrecognised error must never be "stop".**
  `classify_error` ended in `return "hard"`, and `hard` RAISES, aborting the whole
  provider chain. So the first provider error nobody had enumerated took down
  cognition that four open rungs could have served: mistral answers a spent
  monthly allowance with `HTTP 402 {"detail":"Check your subscription on
  admin.mistral.ai/subscription"}` — no *quota*, no *billing*, no *exceeded*, no
  429 — and on 2026-08-19 that killed **651 cycles in one day**, dropping the
  creature from 82 thinks/hour to **6**. Because it raised, `record_exhaustion`
  never ran either, so the rung was never walled and was retried every cycle.
  This project had already learned the lesson once — 2026-07-17, degenerate
  free-pool responses hard-raising "even with open windows" — and fixed it by
  **enumerating more strings**, which left the fail-closed default untouched. That
  is why it recurred. Invariant: **an unrecognised error routes to the next rung,
  does not wall the account, and is announced once with its text.** When you split
  a failure class to know which one happened, the default is the half that bites.
- **Adding a rung means adding its EXHAUSTION SIGNATURE, not just its key.** The
  mistral rung was added 08-17 from live `x-ratelimit-*` headers — the right source
  for *limits*, and silent about what the provider returns once the allowance is
  gone. Two days later that unknown response shape was the outage. Before a rung
  carries traffic, either know what its 402/429 body looks like or verify
  `classify_error` maps it to something other than the default.
- **A graceful degradation that logs nothing is a silent outage.** Groq withdrew
  `llama-3.3-70b-versatile` on 2026-08-17; the `groq` rung began returning 404,
  the ladder classified it `gone`, walled the rung and carried on — correctly,
  with cognition uninterrupted and **not one line anywhere saying why**. The
  `gone` print fired only when a sibling model existed, so single-model rungs
  retired mutely, and FLATLINE would have reported `groq(12h)` half a day later
  with no cause attached. When you separate two failure classes to know *which*
  one happened, the log line is the whole deliverable — handling it quietly
  throws away the reason you split them.
- **A guard that names one exact string is one rename away from silent.** The
  SENSOR looked for the title `"Mock News Item"`; the creature's fixture said
  `"Test Article 1"`, and the guard built to catch mocks reported
  `SENSOR:ok(2 fresh)` over two `example.com` articles (2026-08-08). Test a fact
  about the world where you can — RFC 2606 reserves `example.com` so it can
  never carry real content — and keep phrase lists as backstop only.
- **Guidance to the creature is a contract, not a recipe.** Told "don't build
  JSON with `jq -n` and append it to a `.jsonl`", it stopped using `jq` and
  rebuilt the identical fault with a heredoc 36 hours later. Name the invariant
  it must hold (*one record per line*), never the mechanism to avoid — it has no
  outbound channel and cannot ask which you meant.
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
  `tool:: command not found` for two months. **Re-checked 2026-08-19 and the
  documentation half is CLOSED:** `protected-prompt.md` now shows the header with
  `#` and says outright "Those three lines are COMMENTS -- keep the `#` ... the
  file dies before it runs", and `tool-new`'s template writes it correctly. Three
  tools authored THIS WEEK still reproduce the fault, two of them with the shebang
  pushed to line 4. So this is no longer a documentation defect, and re-fixing the
  wording would be treating a symptom that is not there. It is one of three
  generation-artifact families (below) that share a single root: **nothing
  validates a tool file at the moment it is written.**
- **An LLM writing an executable file produces three recurring corruptions, and
  none of them is a logic error.** Census of the live 485-tool library,
  2026-08-19, `volume/tools.tool_syntax_error`: **10 tools cannot start at all.**
  (1) **Backslash-escaped triple quotes** — `prompt = f\"\"\"` — 5 tools, from
  generating Python through a shell layer whose escapes survived into the file.
  (2) **Unicode look-alikes** — `invalid character '‑' (U+2011)`, a typographic
  non-breaking hyphen where ASCII `-` was meant, inside identifiers like
  `keyword‑archive` — 2 tools. (3) **The header without `#`** — 3 tools. All were
  written through `tool-edit`, the proper door, which leaves a `.bak` and escapes
  nothing; the corruption is in what the creature handed it. When you diagnose a
  broken tool here, check for these three before reading the logic.
- **YAML's Norway problem:** a bare `off`/`on`/`yes`/`no` key parses as a boolean.
- **Tests that assert a MECHANISM go red when you improve the mechanism.** Assert
  the contract instead. They also go red where the mechanism is deliberately
  *absent*: the chat test asserted `chat.jsonl.lock` exists, and off POSIX
  `_locked` is a no-op by design, so the whole gate was red on the PC peer while
  a sibling test two hundred lines away existed purely to keep the suite runnable
  there (found 2026-08-11). Assert the contract always, the mechanism where it
  can exist. **Third instance 2026-08-19**, in one feature: the
  execute-bit check in `tool_start_failure` is only real on POSIX (off POSIX
  `os.stat` reports it from the file EXTENSION), so it condemned the whole library
  on the PC; then the fixtures, written with `open()` and therefore without `+x`,
  read as unstartable on the LAPTOP where the bit is real. Green on one machine and
  red on the other, twice, in opposite directions. Gate both, always.
- **A guard verified through the guarded door is not verified.** The P1-F12 chat
  test wrote both its messages with `enqueue` — the locked writer — so it passed
  continuously while `observer.py` appended to the same file with a bare
  `open(CHAT, "a")` and never imported `fcntl` at all (2026-08-11, five days
  after the finding was closed). When you test that a shared resource is safe,
  enumerate every WRITER and reach it the way each one really does; a test that
  can only get in through the lock can never see someone climbing the window.
- **A docstring is a claim, not an instrument.** That finding was closed on one
  sentence whose two clauses had different provenance: the first was read from
  the code, the second lifted from `_locked`'s own docstring, which said "the
  observer APPENDS (enqueue, its own process)" — the *design*, never built. The
  conclusion ("Tue's messages cannot be lost") was drawn from the pair. **A
  verdict is only as strong as its weakest clause.** Prefer a count you can state
  — `grep -c fcntl observer.py` → 0 — over any prose in the file you are auditing,
  the code's own comments included.
- Re-verify any "it started" claim a beat later. Fixtures come from the real
  corpus, never authored. Never call `_build_tool_catalogue()` just to inspect it
  — it ends in `_mark_surfaced()` and writes rotation state.
- **A test that builds its own state dict can still write to the real file.**
  `quota_state.record_success/record_exhaustion` end in `save_state()`, which
  dumps whatever dict it is handed to `keychain/quota_state.json` — a module
  constant with no injection point. A keychain test passing a fresh `{}` flattened
  every provider's `last_success_at` on the live laptop (2026-08-10). Repoint the
  module constant into `TMP` before exercising anything that records, and assert
  in the test that you did. Derived state, so it rebuilt within minutes — but
  FLATLINE and the dashboard read "never" for every rung until it did.
- **Deploy code BEFORE config when a schema changes.** A `model_id` list landed on
  the laptop while the running brain still held the old single-string code; its
  last cycle sent the list verbatim and died on `HTTP 400: No models provided`.
  Config is read at `Keychain()` construction, so the window is "until the next
  restart" — push and pull the code first, then edit config, then restart.

---

## 6. Standing decisions (Tue's)

- **Free tier only, permanently — and depth is not a goal** (stated 2026-08-26).
  "We get what is available without paying anything ever. If the nice models all
  die we have to run on what we can get." So a rung behind a paywall is DEFUNCT
  FOR US by definition, and removing it needs no decision from Tue — the money
  question was settled once, forever, and re-opening it as an option is a mistake
  I made twice. It also means **rung count and concentration are outcomes, not
  targets**: a 93%-on-one-rung ladder is what free tiers give, not a fault to fix.
  More large models would be nice and may become impossible; do not treat that as
  a problem to solve with accounts.
- **Quality floor over capacity.** No weak model in the ladder: under a shared
  cap, weak calls starve smart rungs and a weak author's buggy tools are lasting
  pollution. `openrouter/free` auto-routing stays rejected.
- **Reversible actions are just done**, not asked about.
- **The repair boundary is not Tue's to arbitrate case-by-case** (stated
  2026-08-26): a known-failing behaviour in OUR framework is fixed without
  asking — "I don't want something running that we know fails if it's part of
  our own framework." A fault in the creature's own output is never fixed and
  never needs his sign-off either: the response is always visibility — make it
  see the failure at the moment it makes it, every time it makes it. Do not
  send decisions of this shape back to him; he is the idea guy.
- **A defunct model is removed the moment it is detected** — Tue's standing
  practice, stated 2026-08-17; do not queue it for his decision. Set
  `enabled: false` with a dated comment naming what happened. Check first whether
  the rung's key is carried into the container as a LEGACY ALIAS
  (`sandbox.py: LEGACY_KEY_ALIASES`): disabled rungs' keys are withheld from the
  body, so retiring a rung can delete an env var the creature's tools rely on.
  Deploy the code that stops depending on it BEFORE flipping the config.
  Then **find a replacement rather than shrinking the ladder** — Tue, 2026-08-17:
  "we must find a new one next time we run out." Prefer a NEW account over a
  second model on one we already hold: `groq` and `groq_oss120` shared a bucket,
  so the second was never added capacity. Source its limits from headers (§5).
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
- **Never change the dashboard without looking at it afterwards.** `observer.py`
  is PyQt6 on X11, `DISPLAY=:0`. The bridge cannot move binaries, so:

  ```bash
  export DISPLAY=:0
  xwininfo -root -tree | grep Dashboard          # window id, e.g. 0x7800007
  import -window <id> /tmp/dash.png              # scrot/import/convert are installed
  convert /tmp/dash.png -crop 330x22+1340+12 +repage -strip -colors 8 PNG8:/tmp/t.png
  base64 -w0 /tmp/t.png                          # then certutil -decode on the PC
  ```

  Crop TIGHT: base64 travels through the session, and a full 1920x1015 grab is
  ~500 KB. A 330x22 label crop is ~750 chars; a full-width 1920x50 strip is ~6 K
  and already too costly. Note the window is maximised to 1920 even though the
  code says `resize(1180, 720)` — crop to 1180 and you miss the right-hand chips.

  **ALWAYS `md5sum` on the laptop and verify after decoding.** Base64 carried
  through the session is NOT byte-safe: a 6,576-char blob came back with the right
  LENGTH, the right PNG header and the right `IEND` footer, and a different md5 —
  characters had been substituted in the middle (2026-08-11). Every cheap check
  passed; only the hash caught it. A 2,548-char blob transferred clean, so keep the
  payload small AND prove it. Symptom of the corrupt file: PIL reads the header
  then dies with `unrecognized data stream contents`, and the image API rejects it.
  `-colors 8` PNG8 was also rejected outright; **grayscale plain PNG** worked
  (`-colorspace Gray -strip`, 660x46 → 1,910 b). `certutil -decode` is not the
  culprit — it and `base64.b64decode` agreed byte for byte on the corrupt copy.

---

## 8. State — 2026-08-26 00:35

**The observation keyhole, found and fixed (`c733adc`; the §5 scar has the full
anatomy).** Tue set the session to Fable and ordered a best-fix for the loop
warning trapping reads; the census turned up the real fault — the creature sees
~286 silently-truncated chars of ANY command's output, at two layers, and the
warning asserted completeness on top of it. Markers now announce every cut;
capped commands are never counted as repeats; the warning says only what it
checked. Verified live 00:30: fires correctly on synthetic streaks (14 contract
tests), silent on the live tail. **On trial for the next gs-bug-daily:** streak
count (census method, was 127/14d), rounds-per-tool (was 4.2–6.3), done-marks
accepted (was 1 of 5), think-records calling a warning a trap (was 3).

**gs-bug-daily 2026-08-25 20:21 (28h):** 999 thinks at 35.7/h, 947 exec, 6
errors — 4 done-gate (right reason), **2 provider: `google_gemma` HTTP 499
reached the keychain's `unknown` path, which routed around it, carried the text,
and lost nothing** — the c1b93a5 fail-open design doing exactly its job, twice.
Fixed up front under the new rule: 499/client-closed/cancelled -> `flaky`
(`d196a94`, real journal string as fixture). Truncation 5.1%. Funnel: 17 actions
over 4 tools, done 5 attempted / 4 refused / 1 accepted — the collapse that led
to the keyhole. `plan_from_question` took 13 edit rounds and IS green.

**The 08-26 trigger FIRED and was actioned the same night.** The broken-tool
count sat at 32 for four days with engagement but no repair, so per its own
terms `tool-edit` now gives write-time startability feedback: a WARNING on
stderr, never a refusal — the file is saved exactly as given, exit stays 0, and
stderr names the line and the invariant. I first sent this to Tue as a choice;
his answer became the §6 decision rule above, and the change shipped under it.
Because the tool runs inside the container where `volume/tools.py` does not
exist, it carries a **verbatim mirror** of the four canonical startability
functions, and a suite test fails on one character of drift — the §4 rule held
by test where import is impossible. The keyhole fix and this land together, so
the next window measures their JOINT effect on the count; that attribution
blur is accepted and noted. Watch: does 32 finally fall, and does the WARNING
line appear in exec stderr when it writes a broken file.

**Ladder:** mistral returns 08-31, cerebras holds to 09-01, gemma carrying ~90%.
`exec/think` watch unchanged, waiting on mistral. Keys still pending rotation.

Gates: **laptop 379 PASS, PC 373 PASS**, each ending `ALL TESTS PASS`.

---

### Previous state — 2026-08-22 09:05

**Overnight run 08-21 19:00 -> 08-22 08:55, 13.9 h continuous** (records in every
hour, no gap; the box was off 17:00-19:00 on 08-21). **550 thinks at 39/h, 532
exec, 67 skips, 11 errors** — 9 done-gate false-completion blocks, 1 spin trap,
and 1 unclassified `IncompleteRead(78 bytes read)` from the generic handler at
`loop.py:3848`. One occurrence in 14 h is not a symptom; noted, not chased.
Full day 08-21: **896 thinks / 885 exec / 16 errors**. Truncation 7.3%,
`google_gemma` carrying **89%** of traffic. `exec/think` steady at **0.97** — still
the open watch item, still waiting on mistral's 08-31 return to test the cause.
60C, clamp off, zombies 0, `pids.current` 2.

**The warning and the gate disagreed about what "cannot start" means, and the
creature found the hole for me.** At 00:30 it wrote `proactiverearchpipeline`
(note the typo'd filename; its own header says `proactiveresearchpipeline`) with
`cat << EOF > /mind/tools/own/...`. Valid Python, correct shebang, **no execute
bit** — `tool-new` sets it, a redirect does not. Invisible to BOTH guards:
- the GATE, because `_tools_touched` matched only `tool-new`/`tool-edit`;
- the WARNING, because it called `tool_syntax_error` while the gate called
  `tool_start_failure`. Two definitions of one predicate — exactly the drift §4
  exists to prevent, and I introduced it two days ago.

Fixed in `b8df799`: **one predicate**, so the creature is now told about all **32**
rather than 9; `_tools_touched` also counts a redirect or `tee` into `tools/own`
(WRITE forms only — a bare `cat` of a tool file is reading, and blocking on that
would be a gate nobody could satisfy); **`st_mode` added to the parse cache key**,
because `chmod +x` changes neither mtime nor size and a fixed tool would otherwise
have stayed on the list forever; and an **empty file is no longer a start failure**
— with no shebang the kernel returns ENOEXEC, the shell runs it and exits 0, so it
starts and does nothing, which is the hollow organ's fault to report, not this one.

**Census under the one predicate: 32 of 485** — 19 no-shebang, 7 shell-syntax,
5 Python-syntax, 1 not-executable. Note the families **re-partitioned rather than
changed**: `tool_start_failure` reports the FIRST failure it finds, so four `.py`
files that previously counted as Python-syntax now report the missing `#!` first.
9 + those = the same set.

**The startability gate has still fired ZERO times** across ~40 h live. No false
positives, and no true ones either — the creature has not yet marked done in the
same cycle as writing an unstartable tool.

**Repairs held but did not continue overnight**: the Python-syntax family stayed at
9 (it fixed `contextual_alert_updater.py` and `extract-key-insights` on 08-21 and
nothing since). The 08-26 trigger for a write-time check in `tool-edit` is still
satisfied directionally; the wider count now being visible to it is the next test.

**Ladder unchanged**: `cerebras` 99 h dark (holds to 09-01), `mistral` 75 h walled
(returns 08-31). No provider errors in the window.

Gates: **laptop 359 PASS, PC 353 PASS**, each ending `ALL TESTS PASS`.

---

### Previous state — 2026-08-21 16:40

**2026-08-20 the laptop ran something else and the spine did not run at all: the
journal has ZERO records for that date.** 08-21 booted 00:04 and has cycled every
hour since — 200–450 records in each of hours 00..16, no gap. (Tue recalled
turning it on at 07:00 for ~8 hours; the instruments say 16.5, and hourly record
counts are the stronger evidence. Worth knowing which to trust when they differ.)

**The 08-19 ladder fix is fully holding. Errors 805 -> 13, and none of the 13 is a
fault**: 11 done-gate false-completion blocks, 1 spin trap, 1 upgrade-blocked-as-
no-change. **Zero provider errors all day.** 08-21: **703 thinks / 680 exec /
129 skips** over 16.5 h (~43 thinks/h). `THINK:36/h over 5.9h exec/think 1.07`,
no alarm.

**Three designs proved themselves on live data, all first real exercises:**
- **The missing-day rule.** `UNMET` history now reads `08-18, 08-19, 08-21` —
  08-20 simply absent — and the streak stays `0/7`. A day with no evidence is not
  read as a zero, which is what that branch was written for on 08-18.
- **Rate over the span that produced records.** A 16.5 h day starting at midnight,
  and `check_throughput` reported 36/h rather than dividing by wall clock.
- **The linear dependency scan.** `WAKE:p50 1704ms` against 1713 two days ago,
  with the library slightly larger. Flat, as a linear scan should be.

**The broken-tool warning worked, and this is the part that matters: the creature
repaired its own tools.** Python-syntax family **10 -> 9**, full startability
predicate **34 -> 31 of 484**. `contextual_alert_updater.py` edited 12:52 today and
now STARTS. **`extract-key-insights` — the file whose entire line 1 was
`Error: LLM call failed: ask: HTTP 429 ...` — was edited 10:13 today and now
STARTS.** The warning state file was rewritten at 10:33 holding 9, so it re-armed
and spoke again when the set changed; 22 journal records mention it. No direct
intervention, no tool of its own touched by us. **The named trigger for a
write-time check in `tool-edit` (count must fall by 08-26) is satisfied
directionally — do not touch `framework-tools/`.** The stragglers are old:
`ToolUsageAuditor` untouched since 08-07, `ascii_plot` since 07-14.

**The startability gate has not fired once in 16.5 h** — no "Done-gate blocked a
tool that cannot start" in the journal. Live confirmation of zero false positives,
which was the risk worth watching.

**Ladder, and the cerebras trigger has RESOLVED.** `cerebras` last served
**08-18 04:46**, now 83 h dark, so it did NOT serve by 08-20. Per the named
trigger: **hold to 2026-09-01** (month boundary, the hypothesis mistral proved).
`mistral` walled 59 h, waiting on its 08-31 reset. Carrying today:
`google_gemma` **75.1%**, `openrouter_super` 12.8%, `gemini_flash` 3.1%.

**Open, watch it: `exec/think` has roughly halved** — 2.19 on 08-18, 1.87 on
08-19, **0.97 today** — with 81 of today's 129 skips being "thought, but proposed
no commands" and truncation back up to **8.9%** (3.8% on 08-18). The plausible
cause is that the fat-think rung is gone until 08-31 and `google_gemma` carries
75% while truncating 5.4% of its own replies. Recorded as a measurement with a
candidate cause, NOT a diagnosis — the test is whether the ratio recovers when
`mistral` returns on 08-31. If it does not, the cause is elsewhere.

Gates: **laptop 354 PASS, PC 350 PASS**, each ending `ALL TESTS PASS`.

---

### Previous state — 2026-08-19 18:00

**08-18 was the creature's best day on record: 1,467 thinks / 3,209 exec blocks**
(08-17 was 1,148 / 1,585). First full day with `--init`, the clean exec path and
the linear dependency scan. The container fixes survived a reboot around 20:20 on
08-18: zombies **0**, `pids.current` **2**/9090, `Init=true`, 64C, no clamping.

**Then 08-19: a rung I added on 08-17 killed 651 cycles and thinks fell from
82/hour to 6.** `mistral`'s spent-allowance reply is
`HTTP 402 {"detail":"Check your subscription ..."}` — no *quota*, *billing*,
*exceeded* or 429 — so `classify_error` fell through to its default `"hard"`,
which RAISES and aborts the whole chain, with `google_gemma` and `gemini_flash`
open. The raise also pre-empted `record_exhaustion`, so the rung was never walled
and was retried every cycle. Fixed in `c1b93a5`: 402/payment/subscription/
insufficient -> `quota`, **and the default is no longer `hard`** — an unrecognised
error routes to the next rung, does not wall the account, and announces itself once
with its text; if all rungs fail and one was unnameable the raise carries that
text. Verified: `mistral` reads WALLED (was `open` through 12h of failures),
0 hard-raises, **thinks 6/h -> 85/h, errors 50/h -> 0**. See the two new §5 scars.

**All three instruments built this week were CORRECT today and none of them was
watching this.** FLATLINE named the silent providers; WAKE reported `p50 1713ms`
against its 5,000 budget (true — the cycles died after context building); UNMET
gave its first real delta, `327n/7460d -> 326n/7443d` = **-17, streak 0/7**
(correct: unmet demand fell). The collapse was found because Tue asked for a check,
which is the definition of a fault that is not fixed. So `f1ec46d` adds
**`spine_health.check_throughput`** — thinks/hour, exec count, exec/think ratio,
skips; declared floor **15/hour** (five full days ran 32–61/h, the fault ran at 6);
wired into the **hourly** tripwire, because a 6h window read once at 06:30 would
have missed all of 08-19. Verified firing live at 17:50:
`THINK:9/h over 5.9h (exec 43, exec/think 0.80, skip 15) THROUGHPUT:!!`. Rate is
taken over the span that PRODUCED records, not wall clock, so a box switched off
overnight is not a collapse. Reads `journal.jsonl` by epoch `ts`, 32 MB of tail
(the file is 130 MB / 293k records), and says when it could not reach the start.
584 ms, hourly. For **us and Tue**; nothing enters the wake context.

**Ladder state 2026-08-19.** `mistral` allowance is **MONTHLY, resets 2026-08-31**
— left ENABLED so it returns on its own. `cerebras` — **the 09-01 hold is WRONG and is
withdrawn (2026-08-26).** It was built on mistral's monthly-reset hypothesis, and
that does not transfer. Cerebras's dashboard, read by Tue: **"Your personal account
has been migrated to a PayGo account"** — that is the "free tier changes" note of
08-17, and cerebras last served 08-18 04:46, the day after. The key itself is
**ACTIVE** (three keys on the account: APEX, Default Key, Growing-Spine — one
shared budget, the groq/groq_oss120 scar). Probed through `provider.call`:
`HTTP 402 {"message":"Payment required to access this resource. Visit your billing
tab.","type":"payment_required_error","param":"quota"}`. **It cannot self-heal on
any date**: the ladder has re-probed it roughly 1,200 times over 8.4 days, across
every hour, and not one landed — a resetting daily quota would have let one
through, and a spent quota answers 429, not 402 `payment_required`. So the block is
the missing payment method, and the only things that change it are **Tue adding one
(a one-time $5 credit, expiring 30 days) or retiring the rung and replacing the
account.** Money decision, his alone; leaving it walled is the third option and
costs a probe per 10 min plus a permanent `SERIOUS` that trains us to ignore the
alarm. Checked in advance because retiring `groq` taught it:
`cerebras` IS a `LEGACY_KEY_ALIAS`, so disabling deletes `CEREBRAS_API_KEY` from
the container — but **no tool in `tools/own/` references it**, so retirement is
safe. Carrying load until month-end: `google_gemma`, `gemini_flash`,
`groq_oss120`, the OR pool. **No fat-think rung.**

**Tool-library audit, 2026-08-19 (the creature's OUTPUT, not the framework).**
Library **485 tools**, up from 433 on 08-18. In the last 7 days the journal shows
**90 created via `tool-new`, 185 edited via `tool-edit`**, 159 resolving to files
on disk, 182 distinct tools invoked. **Every one of the 159 written this week was
invoked in that week — zero never-used.** That retires the old "half the library
is never invoked" story for good. Quality census: **64% carry the `# tool:` header
contract**, 107 use `argparse`, **51% use stderr with a nonzero exit**, but **10%
(50 tools) RETURN error text as their value** — a failed subprocess becomes a
string that flows downstream as if it were content, which is the house disease in
its own toolkit. **10 tools cannot start at all** (three families, §5).
The single most-invoked tool is `step-planner-tracker` (84 lines, ~867 mentions in
exec blocks over the week); its `save_state` writes the shared state file
**without tmp+replace**, so a crash mid-write corrupts the file 800+ calls depend
on. Its tool, its call — not ours to fix.

**Built for the creature (not us): `loop._build_broken_tool_warning`** (`32a32cb`).
Names the count and the tools that cannot start, edge-triggered on the SET
changing, silent otherwise. States the invariant ("a tool must be able to start"),
never the mechanism — told to stop escaping quotes it would obey the letter and
reach the fault another way, as it did with `jq -n` then heredocs. Results cached
on `(mtime, size)` because a full `ast.parse` of 485 files per cycle is exactly the
cost class that hid the quadratic scan: **cold 349 ms, warm 16 ms** — and a test
proves the cache holds and that a touched file is the only one re-parsed. Bash
tools are never judged by Python's grammar.

**Deliberately NOT done: a write-time syntax check in `tool-edit`.** It would catch
this at authorship, when the creature still has context, instead of hours later —
but `framework-tools/` is protected scar tissue (§2.2) and I have injected two
faults of my own this week. **Named trigger:** if the broken-tool count has not
fallen by **2026-08-26**, a week after the warning went live, in-loop visibility
has been shown insufficient and a stderr warning (never a refusal) in `tool-edit`
becomes justified. Instrument: the count in `_library_broken_tools()`.

**The greenlight now requires that the tool can START (`a502b2a`, `5521450`).**
The creature marks completion with `remember current-phase done`; the done-gate
already refused that on a failed check or an unfilled `tool-new` scaffold, and
never asked whether the tool could run one line. It was also watching the wrong
door — `_hollow_tools_touched` matches only `tool-new`, and **all ten broken tools
were written with `tool-edit`** (185 edits vs 90 creates that week). `_tools_touched`
now matches both. The smoke test is STATIC and never executes the tool: these tools
write to the volume and call providers, so running one to test it is not available
to us. Startable, not working — an interpreter line the kernel can act on, a body
its declared interpreter can parse, the execute bit. For a file with no shebang the
decision is made by PARSING, not by guessing from the extension: guessing would
have condemned 26 live files, some of them working. **Scoped to THIS cycle** — a
library-wide block would be a trap it cannot exit, while a tool it wrote sixty
seconds ago is always still fixable. Live census under the predicate: **34 of 485
cannot start** — 21 no-shebang, 7 shell-syntax, 6 Python-syntax — and four sampled
by hand were all real, no false positives. `ToolUsageAuditor`, which §8 has listed
as "reading zero bytes and returning nothing without error", turns out to be
**unstartable**, which explains it.

Gates: **laptop 354 PASS, PC 350 PASS**, each ending `ALL TESTS PASS`.

---

### Previous state — 2026-08-18 07:55

**2026-08-18: the body had been unable to fork for three and a half hours and
nothing said so.** Found while chasing Tue's report that the laptop was louder
than usual — the third time he has raised fan noise and the third time the noise
was real. Instruments and numbers:

- `pids.current` 9085 against `pids.max` 9090; `ps -eo stat | grep -c ^Z` = 9,082,
  the oldest starting 08-16 20:20 and the newest 08-18 04:11 (the moment the
  ceiling was reached). All parented to the container's PID 1, `sleep infinity`.
- `sandbox.run_command("echo alive")` returned **exit 128 with
  `OCI runtime exec failed: ... procReady not received` ON STDOUT**. The creature
  received infrastructure breakage shaped exactly like the output of its own
  command, for 3.5 hours.
- `ensure_body` called it alive throughout, because it read
  `docker inspect .State.Running`.
- Nothing in the brain's journal, `spine-health.log`, or the dashboard named it.
  Zero exec-failure lines in three hours.

Fixed in `c76a7a8` (`--init` so tini is PID 1 and reaps; `run_command` routes
exec-setup failure to stderr with stdout EMPTY, the `framework-tools/ask`
contract applied to the path every tool call travels; `ensure_body` proves
liveness via the new `sandbox.body_responds`, and verifies the respawned body
too). `sandbox.exec_setup_failure` is the ONE classifier both the producer and
the checker call. **Verified through the real path, not by hand:** the restarted
brain found it itself —
`07:47:54 BODY UNRESPONSIVE: exec probe exit 128 ... / 07:48:08 Body respawned.`
Then `Init=true`, zombies 0, and from the container `echo alive` + `ask` -> `ok`.

**The cost of the outage, from the creature's own journal (not journald).** In
the 3h37m the body could not fork: **202 exec blocks attempted, 202 recorded as
completed, 213 records carrying `stdout=OCI runtime exec failed...`**, alongside
152 thinks and 27 exec_skips. Two OCI variants appear — `procReady not received`
and `error executing setns` — both caught by `exec_setup_failure`, verified.
So the creature ran two hundred commands whose output was a docker error, and its
own record shows two hundred successful executions. An earlier figure in this
session ("only one wake fell in the window") came from grepping journald for
`Wake:` and was wrong by two orders of magnitude; see the journald scar in §5.

**Throughput, measured from `journal.jsonl` by epoch `ts`:** 08-14 950 thinks /
1,305 exec, 08-15 1,019 / 1,351, 08-16 759 / 1,085, **08-17 1,148 / 1,585** (the
best day in the window), 08-18 371 / 595 by 08:05. Truncation share of thinks:
**5.6% on 08-17, 15.1% on 08-18** — elevated today and concentrated in
`google_gemma` (55 of ~210 of its calls). Provider mix 08-18: gemma 41.5%,
**mistral 37.5%** (9.7% on 08-17), cerebras 5.4%. The mistral rung is carrying
real load. Five-day `token ceiling` counts from journald are flat (134 / 115 /
94 / 132 / 102), so **today's rise is not a regression from this session's
changes** — but note `finish=length` is recorded via `record_success`, so a
truncating rung is never walled and the fat-think rung below it is never reached
by escalation. Size-aware routing stays rejected (§8, deliberately not built);
this is recorded as a measurement, not a proposal.

**The CPU was a second, unrelated fault, also measured.** `_build_knowledge_block`
cost **45.0 s of every wake**, 27.6 s of it `_dependency_summary`:
`_tool_dependencies` ran 433 x 433 = 187,489 full-content regex scans per cycle.
Replaced with one compiled alternation scanned once per file (`530cbee`).
Equivalence proven on the live 433-tool corpus: **28,312 ms -> 779 ms, 1011 edges
both ways, dicts identical**. The quadratic version is kept in
`tests/test_loop_v2.py` as the oracle. After both fixes, measured 07:52:
`_build_knowledge_block` **45,032 -> 1,001 ms**, `_stuck_tool_procs` 250 -> 6 ms
(the zombies were most of its cost). Host: 79C -> **70C**,
`intel_powerclamp cur_state` 11 -> **-1 (off)**, loadavg 4.65 -> **1.51**,
processes 9,328 -> **235**, container CPU 88.72% -> **0.00%**.
**Honest attribution: neither fault was mine.** Both predate this session
(`sleep infinity` from the beginning, the quadratic scan long-standing). My own
per-cycle additions measured **15 ms combined** (`_build_data_warning` 9 ms,
`_stuck_tool_procs` 6 ms). The loudest process on the box now is
`bedrock_server` at 88% — Minecraft, not ours, and not a fault.

**Two instruments were added afterwards, both for US and Tue, neither entering
the wake context.** (1) `spine_health.check_unmet_demand` — the builder's trigger,
redefined because the parked wording could not be evaluated; see the builder entry
under "deliberately NOT built". Baseline `UNMET:327n/7460d streak 0/7`, 53 ms,
daily. (2) `loop._record_wake_cost` — the detector for the fault class the
quadratic scan belonged to, since replacing that scan fixed only the instance and
nothing stopped the next one being written the same way. First live sample after
the 17:05 restart: **2,793 ms** (a cold first cycle; the steady figure measured
16:51 was 1,090 ms), budget 5,000 ms, 0.35 ms/cycle to run.

**Measured 16:51, nine hours after the fixes — they hold.** Zombies **0**,
container `pids.current` **5**/9090, `Init=true`, **0 OCI-error records since the
restart** (213 during the outage). 75C with `intel_powerclamp` **off**, loadavg
2.52, 234 processes, container CPU 0.00%, brain averaging **5.8%** against 84.5%
that morning. `bedrock_server` is the loudest thing on the box at ~30% over 44 h —
Minecraft, still not ours. The creature: **1,098 thinks / 2,307 exec blocks by
16:51**, already past 08-17's 1,585 exec blocks; **truncation down to 3.8%** since
the restart (15.1% that morning) because **`mistral` is now serving 77.7% of
thinks** against gemma's 11.3%. Of 184 "errors" since the restart, **161 are
`Done-gate blocked a false completion`** — a guard rail firing correctly, not a
fault.

Gates: **laptop 318 PASS, PC 314 PASS**, each ending `ALL TESTS PASS`.

---

### Previous state — 2026-08-14 17:45

**This section goes stale fast. It is yours to maintain: when you measure
something that contradicts it, correct it and commit. You do not need
permission for that.** The first version of this file was already nine hours
stale at the moment it was committed — it said `tool-tester` was a hollow stub
when the creature had finished it four hours earlier. Date what you write, name
the instrument, and prefer a live census to any figure in here.

v0.15. **Both gates green (measured 2026-08-14): laptop 282 PASS, PC 278 PASS,
each ending `ALL TESTS PASS`.** The PC abort that stood here (`os.sysconf`,
POSIX-only) was fixed in 16999cc the same day it was recorded. **415 own tools**
(canonical `list_tools`; raw `ls` says 513 — never compare the two; a session
report once claimed "+151 in three days" by mixing them). ~900–1000 thinks/day
(journal `served_by`: 994 / 914 / 980 on 08-10/11/12; the box was OFF
08-12 23:15 → 08-14 00:50, so 08-13 has zero cycles — a shutdown, not a fault). (No HEAD hash here: a file cannot name the commit that
contains it, so the line was stale on arrival. Use `git log -1`.)
**Zero open audit findings** — all 67 verdicted. One of those verdicts was wrong:
**P1-F12 (chat lost-update race) was closed on 2026-08-06 with only its executive
half fixed**, and the observer went on appending to `chat.jsonl` outside the lock
until 2026-08-11. Fixed and re-verdicted; the two new scars it produced are in §5.
Deployed to the laptop? **See "Needs doing on the laptop" below — the dashboard
change has NOT been looked at yet, which §7 requires.**

**STILL LIVE — `wake_catchup_fetcher` is a mock (first written over the real
tool 2026-08-08 17:14 with `cat >`, no `.bak`; re-made 08-09 and again 08-12;
measured 2026-08-14: 313 b, three `example.com` items, JSON-per-line).** It is
not deceived — its own reasoning calls it "the mock" — and the real
implementation survives as `wake_catchup_fetcher.real` (541 b, 28 Jun).
`SENSOR:MOCK(!!)` catches it; the data warning counts its output as fabricated.
**Restoring it is the creature's call, not ours: §2.1. Six days outstanding.**

**Measured 2026-08-14 17:45 by live census:**
- **Third fabricated-capability instance: the echo simulator (08-14 13:28).**
  The creature rewrote `subagent_ask_helper` from scratch as a "cost-aware
  routing" wrapper whose own comment says *"In a real environment, this would
  call the actual API client… we simulate the routing"*, delegating to
  `subagent_ask_fallback.py` — *"echoes the prompt back as a JSON answer"*.
  Exit 0, answer-shaped, no model anywhere; my 08-11 honest-failure patch
  survives at `subagent_ask_helper.bak`. Root condition: it has held seven live
  provider keys in its container env since `sandbox.py` began injecting them,
  and the one worked example of using them (`llm_ask_helper`) died in `/tmp` on
  23 Jun. It reaches past capability it cannot see a way to use.
- **`ask` deployed — the missing primitive (234b9d4).** Framework tool, so it is
  re-materialised every wake and cannot die in `/tmp`. `openai/gpt-oss-120b` via
  the injected `GROQ_API_KEY`; **500/day cap** (half the published 1,000 RPD —
  console.groq.com/docs/rate-limits, retrieved 08-14; account headers confirm
  1,000/8,000), counter readable at `/mind/state/ask_quota.json`. Contract:
  stdout is the answer or empty; every failure — key, budget, provider,
  truncated or empty reply — is stderr + nonzero. Verified live from its
  container 17:36: `ask "Reply with the single word: ok"` → `ok`, exit 0.
  Announced in chat 17:38 (Tue-voice, numbers verbatim). NOT llama-3.3-70b:
  Groq retires it for free tier on **2026-08-16**
  (console.groq.com/docs/deprecations, retrieved 08-14).
  **The experiment: does it adopt `ask`, rebuild its helper on it, and stop
  simulating? Instruments: `ask_quota.json` `used`; `subagent_ask_helper`
  mtime/content; echo-shaped records in stores.**
- **It cleaned its own archive.** `keyword-archive.jsonl` went 43,522 lines →
  199 (1.37 MB → 108 KB) after the 08-11 runaway message — the 4,309 error
  records removed by it, not us. The writer is still multi-line though:
  **196 of 199 lines unreadable** (`jsonl_parse_rate`), `keyword-archive-store`
  untouched since 08-08 12:15.
- `planner.json` is **resolved**: still 0 b, but `/mind/data/step-planner/`
  holds 33 plan files — the 08-08 repointing completed; abandoned file, not
  lost data.
- finish=length by full day: 11.1% (08-10) → 7.3% (08-11) → 6.2% (08-12) →
  8.5% (08-14 partial). Twins **39** (was 34). Hollow backlog **0, sixth day**.
- OR pool consolidation verified on live traffic: `openrouter_super` served
  exactly 50 / 50 / 50 / 51 on 08-10..14 — one account, one budget, as designed.
- **`mistral` rung added 2026-08-17 — the fat-think slot.** `mistral-large-latest`,
  a NEW account (so real added capacity, not another name for a bucket we hold).
  **250,000 tokens/minute** against `groq_oss120`'s 8,000, which is why it is
  here: `finish=length` has been the top measurable fault for a week and every
  other rung is TPM-walled far below. Costs 4 req/min, fine because the ladder
  reaches it only when the workhorses above wall, and the box averages under 1
  think/min. Placed after `google_gemma`, before the OR pool. Verified through
  `provider.call` (not an ad-hoc probe): `ALIVE`, finish=stop, 12 tokens.
  **All limits came from the account's own `x-ratelimit-*` headers, never docs** —
  Mistral publishes no free-tier numbers (its tier page defers to a signed-in
  panel), and the curated lists filling that gap are the same ones that gave this
  file its wrong `groq: 14400`. **RESOLVED 2026-08-19, the hard way: the allowance is
  MONTHLY and it ran out in two days.** No daily or monthly header is returned, so
  its size stayed invisible until exhaustion, exactly as flagged. It became the
  workhorse — 77.7% of thinks on 08-18, 72.9% on 08-19 — and spent a month of
  budget by 05:00 on 08-19. Tue read the reset date off the Mistral admin panel:
  **usage resets 2026-08-31.** Left **enabled** deliberately: walled costs one
  re-probe per 10 min, and the rung then returns on 08-31 without anyone having to
  remember a config flag.
  **The sentence that stood here was wrong, and it was mine (08-17): "If it runs
  out the rung 402/429s and the keychain walls it honestly."** It 402'd and the
  keychain did NOT wall it — `classify_error` had no branch for 402, so the default
  hard-raised and killed the cycle instead. A prediction about a path nobody had
  exercised, written in the voice of a measurement; see the ladder scar in §5 for
  what it cost. FLATLINE did report `mistral(12h)`, so that half held. Key lives at `/home/boas/mistral.key` (chmod 600, outside the repo).
- **The ladder is six rungs (2026-08-17).** `groq` retired the day Groq withdrew
  `llama-3.3-70b-versatile`: it served at 10:28 and 404'd by 17:20 (direct probe).
  Not repointed — `openai/gpt-oss-120b` is already `groq_oss120` on the same
  account and the same shared bucket, so a second copy buys nothing;
  `qwen/qwen3.6-27b` is the option if a distinct model is ever wanted. Its
  `limit: 14400` was always wrong (published 1,000 RPD) and died with it.
  `framework-tools/ask` reads `GROQ_OSS120_API_KEY` **or** `GROQ_API_KEY`,
  because retiring `groq` deletes the latter from the container — `sandbox.py`
  withholds disabled rungs' keys, and `GROQ_API_KEY` was only ever that rung's
  legacy alias. Code shipped before the config flip.

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
- The archive emptying is **not** the consented merge of 7 Aug (chat #52–54).
  That merge *created* the file — 677 records from 14 shards, 77 damaged
  fragments dropped with the creature's agreement, every shard backed up. It was
  still 193,665 b at 03:26 on 8 Aug, 27 hours later, and no merge script exists
  on disk to re-run. Ruled out by timing.
- **The `jq -nc` fix was reverted and the 934-empty-reads scar is live again.**
  On 7 Aug 00:47 `keyword-archive-store` was changed from `jq -n` (pretty, many
  lines) to `jq -nc` (compact) — the fault behind 1,670 writes yielding 422
  records the reader could parse 18 of. On 8 Aug 12:15 the creature rewrote that
  tool from scratch: no `jq` at all now, a `cat <<JSON` heredoc instead, and the
  records are multi-line again. **36 hours from fix to recurrence.**
  Live: `JSONL:!!3[keyword-archive.jsonl(4/104); memory_archive_cache.jsonl(0/7);
  resilient_task_log.jsonl(0/2)]` — two of those found by the new sensor on its
  first run, and both are wholly unreadable to their own writer.
- **Why the warning did not hold, and it is ours to learn from.** It was told
  "if any tool builds JSON with `jq -n` and appends to a `.jsonl`, it has the
  same fault". It obeyed exactly — it stopped using `jq` — and reached the same
  fault by heredoc. The advice named a MECHANISM; the contract is *one record
  per line*. §5 already says to assert the contract rather than the mechanism;
  that applies to what we tell the creature, not just to tests.
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

**Deployed 2026-08-11 (observer chat-lock fix) — §7 satisfied.**
Laptop pulled to 51e1e81, gate 270/0, `spine-observer.service` restarted (the brain
was NOT restarted — `observer.py` is not brain code), and the dashboard was looked
at: input row renders, status bar `tick 33 | 18:38:19` with no error text. The
import `_send` now depends on resolves in the service's own WorkingDirectory
(`python3 -c "from executive.chat import enqueue"` → OK from `~/growing-spine`).
`chat.jsonl` intact at 58,975 b across the restart.
**One thing deliberately NOT tested: an actual sent message.** A test send writes
into the creature's world in Tue's voice, which §2.5/§2.7 forbid. So the last mile
— does a real message arrive — is proven only by the gate and the import check.
When Tue next sends one, that is the confirmation; if `executive.chat` were ever
unimportable the status bar says `send error: …` and the text stays in the box.
**`audit/RE-INSPECTION-2026-08-06.md` is gitignored, so the corrected P1-F12
verdict does not travel by git.** Both copies were updated by hand on 2026-08-11;
any future correction needs doing twice.

**Needs Tue's decision**
- **Rotate API keys.** OpenRouter, Gemini, Groq ×2 and Cerebras have all been
  exposed in transcripts by `cat`-ing `config.yaml`. **Grep that file for the one
  field you need; never dump it.**
- *(Closed 2026-08-17: the `groq` rung was retired the day its model went. See
  the ladder note in the census block above.)*
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
- *`tool-retire` — an attic-instead-of-delete tool for the creature.* There IS a
  real asymmetry: `tool-new` and `tool-edit` exist, removal has none, so `rm` is
  the only door and the creature has used it 47 times. But measured 2026-08-08
  against the 2 Aug snapshot: of 349 tools then, **2 are gone from both `own` and
  `attic` — `--show` and `dummy`**, which `JUNK_RE` already calls non-tools. Zero
  real tools destroyed in six days. Its `rm` is state files and
  delete-then-recreate. Two counter-arguments as well: `tool-edit` has existed
  since 5 Aug and it still used `cat >` for the mock, so a safer door does not
  get taken; and making removal feel heavier risks worsening the twins (32 and
  climbing) in a library that once needed a 302 → 32 cull. **Named trigger:** a
  pruning spree that destroys a real tool. Until then this is theoretical harm.
- *The builder — a second LLM actor filling the creature's demanded tools*
  (full design: `the-builder-idea.md`, repo root). Parked 2026-08-10; Tue
  delegated the call and the verdict was no. Reasons: every serious bug in this
  project's history was found by running it and reading behavior, never by
  review, and a second behaving agent coupled to the creature (orders, dock,
  adoption) is the largest new interaction surface since the oracle — added at
  the moment the system's owner says he can no longer read it. The justifying
  symptom is also absent: the stub organ already serves demand (hollow backlog
  0, held through 42 edits on 8 Aug), and delivered tools would be a new
  injection channel into the creature's library — the exact class (a healthy-
  looking file doing something false) behind the mock scar. **Named triggers:**
  (1) **UNMET DEMAND GREW ON 7 CONSECUTIVE DAYS** — `spine_health.check_unmet_demand`,
  emitted daily as `UNMET:<names>n/<demand>d<delta> streak N/7` and shouting
  `BUILDER-TRIGGER:!!` with the top three names when it fires; or (2) the
  data-warning surfacing NEW unreadable/fabricated stores in consecutive weeks —
  visibility proved insufficient and quality needs fixing at construction time.
  Until one fires, the graft answers a theory.

  **Trigger (1) was redefined 2026-08-18, because the original could not be
  evaluated at all.** It read "demanded stubs (`demand_counts` ≥ 5) sustained
  above zero for 7 consecutive days", and both halves were broken:
  `demand_counts` is a **cumulative all-time counter with no timestamps**, so
  nothing in it can express any present tense — `health-summary-fixed` reads 378
  today from invocations that stopped months ago, `llm_ask_helper` 104 for a tool
  that died in `/tmp` on 23 June. And "demanded stubs" names the one population
  the stub organ **zeroes by construction** (`_finish_stub_spec` opens with
  `stubs = _library_hollow_tools()`), so the easy reading sits at 0 forever while
  327 demanded names have no file at all. A hold resting on a number nobody has
  computed is not a hold with a trigger.
  Now measured as the **daily delta** of unmet demand — did it reach for
  something it has not built *again today* — with one record per day in
  `~/spine-health-unmet.json` (host home, outside the volume and the repo). A
  flat day breaks the streak: that is its own hands keeping up, which is the
  thing being watched. A **missing calendar day also breaks it** — the box was
  off, so there is no evidence, and absence of evidence must never read as a
  zero. A counter rewrite appears as a large negative delta and breaks the streak
  rather than being smoothed. **Baseline, first reading 2026-08-18 08:07:
  `UNMET:327n/7460d`, streak 0/7**; deltas only become meaningful from 08-19.
  Cost 53 ms, daily (`spine-health.timer` is 06:30 daily, not hourly). This
  instrument reports to **us and Tue, not the creature** — it answers whether to
  graft a second actor, which is not a fact about its world, and the wake context
  is unchanged.

**Monthly ritual.** Ask the creature what made its work harder; it answers once —
it has **no outbound channel** — then investigate and report back. First run
2026-08-07 surfaced a real two-month-old framework bug (the contract showed the
tool header without `#`, so obedient files died with `tool:: command not found`).
Next due early September. Ask for symptoms, never causes, and **with a time
window**: every item it named came from June, because recent state lives in a
five-slot register that overwrites each cycle.

---

## 9. Session reports

End each working session with one report, published as a **private artifact** —
never a file in this repo. Same reason `audit/` and `DEV-LEDGER.md` are
gitignored: it is a file-and-line map of a running system's failure modes, and
this repo is public. Find earlier ones with the artifact tool's `list` action;
No. 1 is 2026-08-08.

One report per session, not per day, and it is written for Tue rather than for
the next session — §8 is what the next session reads. Structure that has worked:

- **What it did** — delta against the previous census, productive work first.
  The creature has good days and a report that only lists faults misrepresents it.
- **Findings** — severity-marked, each with the instrument that produced it.
- **What we built** — and for whom. An instrument only we can read makes us
  better caretakers; only something the creature receives makes it more
  independent. Say which you built.
- **For the next session** — what is unresolved, and the *specific measurement*
  that will settle it. "Does `wake_catchup_fetcher` move off 358 b" beats
  "check whether it worked".

Name the instrument behind every number, and when a number was wrong, print the
correction and the discarded method rather than quietly replacing it — the
methods that produce plausible wrong answers are worth more to Tue than the
answers.
