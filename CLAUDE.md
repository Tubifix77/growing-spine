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
**Report the creature's production as a RATIO, never as a count.** "Library 702
(+8)" is the number I led with for a month while `README.md`'s actual measure —
edges per tool — fell from 2.33 to 1.56 with nothing anywhere saying so. A
count cannot fall while the thing it stands for does; that is the whole reason
it reads as reassurance.

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
- **When truncation NESTS, the outer cut reports the loss of the WRAPPER and
  silently replaces the inner cut's honest number.** This is the keyhole fix's
  own sequel, found by gs-bug-daily one day after it shipped. The writer capped
  exec stdout at 300 and appended `…[+3305 chars cut]`; the render then capped
  the whole journal record at 300 and appended its own marker measuring *the
  record*, so the creature was shown **`+40 chars cut` when 3,319 characters
  were withheld** (measured against the live 08-26 00:35 record). That is worse
  than shipping no marker, because a small number reads as reassurance. Its
  behaviour matched exactly: in the 15.6 h after the marker went live it asked
  for `sed -n '1,100p'` **97 times** and `1,50p` **56 times**, every request an
  order of magnitude too large to fit, and **82.3%** of its exec results were
  capped (median loss 3,305 chars, 2.0 million characters cut in one window).
  Worse still, it began doubting its own tools rather than the channel -- three
  think records reason "if the file is actually that short, it's a broken tool",
  which poisons the broken-tool warning with an artifact of our own truncation.
  Fixed `5427b72`. Invariant: **a marker always reports the TOTAL characters not
  shown; a later cut may only increase that number, never replace it with its
  own.** Two general lessons. First, **a marker is a measurement and inherits
  every rule a measurement has** -- it can be precisely wrong, and nothing in
  the first fix checked the number against reality. Second, the half-marker
  sweep across caps 290-325 found a real bug on its first run (a cut landing one
  character in left a lone ellipsis, because the remnant detector keyed on two
  characters instead of one): **when a cut can land anywhere, sweep the range
  rather than picking cases by hand.**
- **An event that exists only on stdout cannot be counted by a metric that
  reads `journal.jsonl`** -- the journald scar, arriving inside one of our own
  instruments. The effort funnel's early-rejection stage read exactly zero on
  three consecutive runs and looked idle. Both halves of its definition were
  uncountable: the gate-choice line "a near-duplicate will not be built" is
  advisory text in the wake context rather than an event (32 `think_end`
  records in one window, 785 all-time -- counting it measures how often the
  creature was TOLD the rule), and the oracle's rest decision only ever
  `print`ed. Fixed `b2d1b61` by journalling it as kind `oracle_rest`,
  deliberately outside `MEANINGFUL_KINDS` so it reaches the funnel and never
  the creature. The doc's own "if it is still zero on the third run, go and
  check" rule is what caught it -- **write that rule for every stage that can
  read zero.**
- **Searching for a STRING and concluding an event is uncountable, when the
  event is journalled under a KIND you never enumerated.** 2026-08-26 I declared
  the effort funnel's early-rejection stage uncountable because I grepped for the
  advisory text "a near-duplicate will not be built" and found only `think_end`
  records. I then instrumented a third path (`oracle_rest`), which has fired
  **0 times all-time**. Two countable kinds were already there and I never
  looked: `journal.append(..., "idea_gate", ...)` at `loop.py:1789` with **157
  records all-time**, and four `novelty_block` appends at 1977-2050 with **52**.
  Invariant: **for any event you suspect is uncountable, enumerate journal
  `kind` values FIRST and grep strings second** -- one `Counter` over every
  `kind` in the file costs a single pass. Second half of the lesson: `idea_gate`
  is a SHARED kind that also carries batch-judge failures, so counting a kind
  still requires reading the content.
- **A census keyed on `kind == "error"` cannot see a provider failure that was
  journalled as something else.** This run reported **0 provider errors** while
  two live provider failures sat in the journal as kind `idea_gate`: *"batch
  judge parsed 0/4 -- band left UNJUDGED. cause=EMPTY-REPLY (provider returned
  nothing); reply 0 chars vs 1040 tok budget"*. An HTTP 200 with an empty body
  is not an error to `classify_error` and never becomes one, so it is structurally
  invisible to that census. Now mandated as `gs-bug-daily` item 13.
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
- **A rung that ANSWERS but whose answers cannot be used is worse than a dark
  one, and the aggregate skip count hides it completely.** Measured 2026-08-29,
  splitting `exec_skip` by the rung that served the cycle: `google_gemma`
  **0.5%**, `cloudflare` **0.0%**, `gemini_flash` **53.8%**, `openrouter_super`
  **97.3%** (75 served, 73 skipped). The pool yields a usable cycle 2.7% of the
  time and is exactly what the ladder falls into whenever the workhorse walls.
  The total looked healthy all week — 69 skips in 32.9 h — because 1,144 clean
  gemma cycles drown it. **My first explanation of the mechanism was wrong.** I
  wrote that the pool models are reasoning models spending the whole 3,072-token
  budget before emitting a bash block. Re-measured over 164 h on 2026-09-04,
  `finish` is **248 `stop` against 53 `length`**, and the skip split is **189
  no-bash-block, 44 truncation, 27 unclosed fence**. The dominant fault is
  **format non-compliance** — clean, complete replies containing no command at
  all — not truncation. `gemini_flash` is the opposite disease: 41 skips, all 41
  truncation. Either way `record_success` fires, the rung is never walled, and
  nothing below it is ever reached by escalation. §8 has warned about that
  design gap since 08-18; **97.3%, then 86.7%, is what it costs.**
  **The action was blocked by an instrument gap, not by the decision.** A rung is
  one account with an ORDERED MODEL LIST, and `served_by` recorded only the rung
  — so 189 failures could not be pinned on any of three models and no reorder or
  retirement could be justified by evidence. `keychain.last_model` was already
  tracked and simply never written down; fixed `201c362`. Invariant: **a rung
  with more than one model must record WHICH one served.**
  The second half of the lesson is about attribution. I raised the journal caps,
  saw a 100% skip burst six minutes later, and reverted my own change on the
  timing correlation — then found the burst was six minutes of this hole with
  gemma quota-walled, and my caps were exonerated by a rate that had held all
  window. **Without a per-rung baseline you cannot tell your own change from the
  ground it landed on.** Take the baseline before touching prompt size, never
  after.
- **A diagnostic that is literally false about the file it describes gets
  obeyed to the letter, forever.** `recall_and_answer` had `#!/usr/bin/env
  python3` on **line 3**, under an empty line and a comment it had written. The
  startability predicate said *"no #! line"* — false: there was one, just not
  where the kernel looks. So the creature did exactly what it was told: **ten
  `tool-edit` calls in five minutes on 2026-09-17, 01:24–01:29, each commented
  "adding a #! line", each adding a shebang below the comment, each drawing the
  identical false message.** The write-time WARNING fired every time and named
  the wrong thing every time. `news_plan_tracker.py` sat in the broken stock
  from **07-18** with its header comment above its shebang and the same message
  — two months — and §5's 08-19 census had already noted "two of them with the
  shebang pushed to line 4" without the predicate ever learning to say so.
  Fixed: when a `#!` exists within the first ten lines but is not line 1, the
  message names the line and quotes what sits above it, and states the
  invariant — **a shebang only works as the very first two bytes of the file.**
  The verdict is unchanged (a displaced shebang on a body bash accepts still
  runs and is still not a failure); only the truth of the message changed. The
  mirror in `tool-edit` was regenerated verbatim from the canonical, as the
  §4 test requires. General rule: **before shipping a message about an
  artifact, check the message against the artifact.** "No #! line" was one
  `head -3` away from being known false. Its working 3,626-byte predecessor is
  gone — `tool-edit` keeps one `.bak` and that is the ninth broken attempt;
  the savegame snapshots may hold it, and restoring it is its call (§2.1).
- **`bash -n` on MSYS hangs about half the time on an unterminated quote fed
  via stdin, and a test asserting FAULTY for that fixture is a coin-flip on the
  PC.** Measured 2026-09-17: four `_shell_syntax_ok` calls on the
  `err_as_tool` fixture — three hit the 15 s timeout and returned UNKNOWN, one
  answered promptly with the syntax error. The 432-PASS gate had won the flip;
  the next run lost it and reported a change I had made as the cause. The
  predicate is right — §5 already says an instrument that cannot run must say
  UNKNOWN, never FAULTY — so the fault was the TEST, which asserted a verdict
  the instrument cannot reliably produce off POSIX. Now asserts the contract
  where the instrument can exist (POSIX, the production machine) and claims
  nothing where it cannot; the laptop gate is authoritative for it. Side
  effect worth knowing: the PC suite now legitimately exceeds 120 s because of
  those timeouts — run it in the background, and **when a gate goes red right
  after a change, diff OLD against NEW on the exact fixture before believing
  the correlation.** Third time this project has been fooled by "it changed
  when I changed something".
- **An exception raised INSIDE an `except` clause has no sibling — it escapes
  the whole function, past every handler you thought you had written.**
  `keychain/provider.py` read the HTTP error body with a bare
  `body = e.read()` inside `except urllib.error.HTTPError`. Reading that body is
  itself a network operation, so when the socket had already timed out the
  `socket.timeout` was raised from within the except clause — and Python never
  offers it to the `except Exception` two lines below. It escaped `prov.call`,
  escaped the keychain (no `classify_error`, no `record_exhaustion`, no
  fall-through to the next rung) and reached the loop's generic handler as
  **`UNEXPECTED: The read operation timed out`** plus a 30 s sleep. Four cycles
  died that way on 09-12 and 09-13; the timing confirms it (think_start
  16:49:30, error 16:51:36, against the 120 s `urlopen` timeout). **The fail-
  closed shape of the 651-cycle ladder scar in a new place**, and the bitter
  detail is that the string would have classified perfectly — `timed out` is
  already a `flaky` branch. It simply never arrived. Fixed `dc51e8b`.
  Invariant: **`prov.call` NEVER RAISES** — every failure leaves by the return
  path carrying text the classifier can read, and the STATUS CODE is reported
  even when the body cannot be read, because the code is what `classify_error`
  needs most. Without the fix the suite does not fail, it **crashes** with the
  escaping traceback. General rule: **any I/O inside an exception handler needs
  its own handler**, and `except Exception` at the end of a function is not the
  safety net it looks like.
  Second half, and it is a Tier 4 consequence rather than a framework one: the
  creature **read our infrastructure error out of its own activity log and
  blamed its own tool** — *"the `crossclusterdigestscheduler` tool failed during
  canonicalization with an UNEXPECTED..."* (09-12 16:52). Same class as the
  2026-08-18 OCI errors arriving on stdout shaped like its own command's output.
  Nothing marks a record in `journal.jsonl` as OURS rather than its; the escape
  is closed, the class is not.
- **A fix that buys one measurement can cost another, and "no symptom" will not
  find it — you have to go back and look.** Raising the journal caps on 08-29
  (`e495773`) did what it promised: capped exec results fell 71.8% → 43%, and
  the creature learned to size its reads. It also **tripled reply truncation**.
  Per-day `finish=length`, measured 2026-09-16: **8.2 / 4.9 / 4.4 / 3.5 / 4.3%**
  across 08-24..08-28, then **10.1%** on the raise day itself, then 15.9 / 10.3 /
  13.2 / 23.7 / 7.7 / 10.6 / 6.5 / 17.6 / 14.0 / 12.2 / 9.1 / 10.9 / **13.8%** —
  eighteen days at roughly three times the old level. Mechanism: a 17.5% bigger
  wake context produces longer replies, which hit the 3,072-token output ceiling
  more often, and each one becomes an `exec_skip`. The traffic-mix confound is
  ruled out: `google_gemma`'s SHARE fell 87.4% → 77.5% while its truncation
  ROSE. **`gs-bug-daily` item 15 says to baseline before changing anything that
  touches prompt size — I baselined the skip rate by rung and never thought to
  baseline the reply ceiling.** The lesson is not "don't raise caps"; the read
  fix was right. It is that **a context-size change has two edges, and the one
  you are not watching is the one that moves.**
- **"Don't fix what has no symptom" does not apply when the failure mode IS a
  plausible wrong number.** §4's disease was found live in `loop.py` on
  2026-09-10 by an outside review Tue commissioned: **seven producers and one
  consumer sharing three string literals** — `"Done-gate blocked"`,
  `"Spin trap"`, `"Retrospective verdict: STUCK"` — with **zero tests binding
  any pair** across 400 lines. I verified it before acting: all seven matched,
  nothing had drifted. **That is why it was worth fixing, not why it wasn't.**
  `_window_journal_stats` feeds `_build_digest` and therefore the retro judge,
  so one drifted literal makes the count read **zero** and tells the judge the
  creature had no done-gate blocks in a window that had **139**. §6's rule earns
  its keep against speculative work on failures you would *notice*; a silent
  wrong number is the one class it blinds you to, because the symptom is
  invisible by construction. **Distinguishing test: would the failure announce
  itself? If yes, wait for it. If it produces a plausible number instead, the
  absence of a symptom is not evidence of health.**
  Checking the review against live data also produced a near-miss worth keeping.
  STUCK verdicts appear in the journal as `kind="retro"` with the text
  `"Verdict: STUCK"`, not the literal the consumer hunts — which looked exactly
  like a live drift. It was not: there are two branches, a first strike at 3099
  that watches without resetting and a forced clear at 3110, and `forced_clears`
  is meant to count only the second. **Correct, and entirely implicit in a
  string, one reasonable edit away from silently counting watch-only strikes as
  clears.** I nearly reported the code broken; the fix was to make the
  distinction a named value instead.
  Fix shape, which is the general one: **journal the class as a FIELD, and make
  the field authoritative** — the consumer falls back to prose ONLY when the
  field is absent, so a tagged record can never be re-classified by wording that
  happens to contain another guard's name, and pre-existing records keep
  working. Mutation-tested both directions: removing a producer's field **fails
  the gate**, and drifting a producer's prose **no longer breaks anything** —
  the second mutation was silent before. A **third** copy of the same literal
  lived in `gs-bug-daily` item 4, across a repo boundary, so the disease had
  already reached the inspection skill; that reads the field now too.
- **A constant nobody chose is not a decision, and three revisions of a MESSAGE
  are evidence the message was never the lever.** The creature's entire view of
  any command result was 300 characters, and `git log -S` traces that number to
  **`c98f69b`, the v0.4 SKELETON commit** — scaffold, never weighed against any
  context budget, and the creature's whole world for the life of the project.
  `c733adc` named the caps as constants and kept their values, which is how a
  never-chosen number survives a review that was specifically about it. Three
  fixes to the WORDING were shipped first and none moved behaviour: an honest
  loss number, then the window named beside it. After the second the creature
  read it correctly — *"the activity log shows `[+3046 chars cut; window 300]`.
  This means the summary of the execution is truncated"* (08-27 20:10) — resumed
  ranged reads (5 → 69), and **still asked for 100 lines in 63 of 69 cases**,
  because the ceiling is stated in CHARACTERS and it asks in LINES. Raised to
  1200 on `e495773` against a census of 1,387 results (median 1,776 chars, p90
  5,090; whole-result fit 27.3% → 45.6% for +17.5% context). Two lessons.
  **When a message has been revised three times and the number has not moved,
  stop editing the message.** And **`git log -S` the constant before defending
  it** — if it arrives from a skeleton commit, there is no decision to respect.
- **Two caps in series are a producer and a checker, and raising only one is a
  silent no-op.** The writer capped exec stdout before the render ever saw it,
  so lifting `JOURNAL_RENDER_CHARS` alone would have bought exactly nothing —
  the characters were already gone from `journal.jsonl`. Now asserted at import
  (`EXEC_STDOUT_JOURNAL_CHARS >= JOURNAL_RENDER_CHARS`) with the assert verified
  to fire on simulated drift, because §4's literal-drift disease applies to
  numbers in series exactly as it does to regexes.
- **A § pointer is a claim ABOUT a paragraph, not the paragraph — and the
  weaker copy wins whenever the reader trusts it.** On 2026-08-27 I refused to
  repair a demonstrably failing warning text, telling Tue it was his call under
  §2.7. §2.7 says: *"World-RULE changes are announced in Tue's voice and are
  Tue's call. Draft, show him, send after approval."* That is about **what is
  SENT to the creature in chat**, and says nothing about prompt, warning or
  marker text. The broad prohibition came from `gs-bug-daily`'s own line —
  *"a directive or prompt change … is his call (§2.7)"* — **which I wrote**, and
  which restated §2.7 into something it never said.
  **This was not a memory failure and not compaction: the whole of `CLAUDE.md`
  is loaded into every session's context, so §2.7's real text was in front of me
  the entire time.** I quoted my own paraphrase instead of the source. §1 had
  already legislated against exactly this — *"the skills point at §5 rather than
  quoting it, so one edit is enough"* — and the line I wrote broke that design.
  Two rules. **Never invoke a § by number without quoting its sentence in the
  same breath** — if quoting it would show the citation does not support the
  claim, that is the point of quoting it. And **a skill may POINT at a §; it may
  never restate what the § says**, because the restatement is what gets read and
  it drifts silently, which is the producer/checker literal-drift disease of §4
  arriving in prose.
  Cost of this instance: the single largest recurring defect class in the project
  was formally exempt from repair. **8 of 33 §5 scars live in text the creature
  reads, and they are the only ones that have ever RECURRED after being fixed** —
  the tool header shown without `#` (two months), `jq -n` named as a mechanism
  (rebuilt by heredoc in 36 h), the "any reworded form" ban the creature called a
  trap in its own reasoning. No code scar has recurred, because a code fix ships
  with a test and a text fix was being verified by hoping. **Text the creature
  reads is held to the same standard as code: name the invariant, ship a test
  that fails without it, gate both machines.**
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
- **A GENERATED artifact rebuilt on the wrong machine silently drops whatever
  only the other machine can read, and the loss looks like content.**
  `docs/framework-map.html` is built by a generator whose whole design principle
  is that nothing is hardcoded -- `loc()` resolves line numbers live, `fw_verbs()`
  reads `framework-tools/` live, and the prompt panels are loaded from the
  running code. That is why it survived six weeks of drift with every file:line
  still correct. Both live reads degrade to a plausible-looking answer, in
  opposite directions. **`loc()` returned a BARE PATH when a symbol moved** --
  indistinguishable from a node nobody gave a symbol to, so a rename makes the
  map say less than it used to and nothing anywhere says so. **And the editable
  prompt panel rendered EMPTY when built from the PC**, because that file lives
  on `/mind` and only the laptop has one -- publishing *"the creature has
  written nothing"*, which is a different claim entirely and invisible by eye.
  Fixed 2026-09-21: the generator collects misses and blank panels, names them,
  and **exits 1** rather than writing a hollowed map quietly; mutation-proved by
  renaming `_capped` (reports that one symbol, fails the build) and by the blank
  panel firing on the real case immediately, which is what forced the rebuild
  onto the host. Invariant: **a builder that reads its content live must refuse
  to publish a read that came back empty.** General rule, and it is the §5
  instrument disease one level up: a live read is better than a hardcoded value
  in every way except one -- it can fail quietly, and a hardcoded value cannot.
  Corollary worth keeping: **the PROSE in a generated artifact does not
  self-heal.** Three claims in that map were measurably false after six weeks
  (a ladder of "9 windows" that is five rungs, a done-gate of "four checks" that
  is five, a "2-min cadence" that is ten seconds) while every mechanical
  reference in the same file was still exact. Re-read what a generator hardcodes
  as TEXT whenever you rebuild it.
- **Deploy code BEFORE config when a schema changes.** A `model_id` list landed on
  the laptop while the running brain still held the old single-string code; its
  last cycle sent the list verbatim and died on `HTTP 400: No models provided`.
  Config is read at `Keychain()` construction, so the window is "until the next
  restart" — push and pull the code first, then edit config, then restart.

- **The creature could not ask a question of its own history, and every
  obedience scar in this file sits downstream of that.** Measured 2026-09-17:
  `journal.jsonl` holds **394,544 records / 201 MB**, it has been readable from
  inside the body at `/mind/journal.jsonl` since June, and **not one of the
  creature's 702 tools references it** — nor did a single one of **75,825 exec
  blocks** ever name it. The one instrument it had for its own past,
  `log-read`, is tail-only with a 200-char cap and answers no question: it was
  **tried 48 times in June, 21 in August, 11 in September** — the usage curve
  of a tool that was reached for and abandoned. So its working view of its own
  past was the wake render's
  `meaningful[-8:]` plus a five-slot working register that overwrites each
  cycle. At the thirteenth identical `tool-edit` of `recall_and_answer` that
  window covered **1.4 minutes and held 2 of the 12 attempts that had already
  failed**. The repetition was not stubbornness and not disobedience: it was
  the only rational act available to something with no way to ask *have I done
  this before*. **This is the root that the eight instruments built this month
  all sit above** — every one of them reports to US, and every one is built out
  of ITS diary, which §2 had already ruled on: *"If a fault is only caught
  because a human or a session reads a log, it is not fixed."* When a fault
  class keeps recurring in text the creature reads, ask whether it can see its
  own past at all before writing the message a fourth time.
  Fixed by `framework-tools/did-i`: how many records in the whole history name
  a term, broken down by kind, plus the most recent COMMANDS with the exit code
  of whatever followed each one. Four design facts, each of them a scar in this
  file. **The count is the answer** — a common tool name matches 3,065 records,
  so the six most recent of them are a worse answer than one line of
  arithmetic. **An outcome is read from the FOLLOWING record, never a matching
  one**, because the `exec_end` carrying `bash: line 6: import: command not
  found` never names the tool it broke. **The answer must fit the channel that
  carries it, measured and not reserved**: exec stdout is journalled at 1,200
  chars, so anything wider is destroyed on the way back. **Verified
  end-to-end on live data 2026-09-18 rather than by arithmetic**, pushing real
  output through `_capped` at both call sites: `did-i` produces 1,034 chars and
  the creature receives all of it, every record and both header lines intact;
  asked for ten records it produces 1,606 and **6 of 14 lines die in transit,
  with the NOTE arriving at offset 211 against the first record at 371** — so
  the warning survives the cut it describes, which was the whole point of
  front-loading it. `log-read 15` loses **22%** (1,562 produced, 1,230
  received, 6 of 27 lines) — **not the "two thirds" I claimed when I shipped
  this, which was arithmetic from the 200-char cap and never measured.** Its
  real defect is not the loss: it is that it answers no question, offering only
  the tail the wake render already gives free. My own first two budgets overran by 170 and by 30, both
  because the frame varies with the search term's length; it now measures the
  rendered frame and fits the rows to what is left. And **an overflow notice
  must precede the records it describes**, because a warning printed past the
  cut is a warning nobody can read. Streams with a substring pre-filter ahead
  of `json.loads`: **1.41 s, 13.8 MB peak** against log-read's 4.2 s and 471 MB
  for strictly less. It excludes its own calls and says how many it excluded —
  an instrument that counts the act of measuring reports its own noise back as
  history.
- **I diagnosed an instrument fault with two broken instruments in the same
  hour, and both read ZERO while broken.** Building `did-i` I set out to prove
  that framework tools are undiscoverable, and produced a whole thesis from two
  bad measurements. (1) `awk '/\bfw\b/'` over `loop.py` returned nothing, so I
  reported `_build_tool_catalogue`'s `fw` as a dead variable and concluded
  framework tools never reach the creature. **In POSIX ERE `\b` is a
  BACKSPACE, not a word boundary** — the search was for control characters and
  could never have matched anything. `fw` is used eleven lines later, and every
  framework tool is listed in EVERY wake context with its `does:` line under
  *"Built-in (always available)"*. (2) Counting mentions with
  `grep -o -- "$name"` gave `ask` 72 and `tools` 227, because it was matching
  inside *task*, *asked* and *toolset*, and it searched `CLAUDE.md` and
  `README.md` — **documents the creature has never read.** Its prompt surface
  is `protected-prompt.md` (11,643 b) plus `editable-prompt.md`, which is 153
  bytes and effectively empty.
  **Both wrong claims were CORRECTED BY THE SAME METHOD that this file already
  mandates and I skipped: prove the search can return non-zero.** One
  `grep -n fw loop.py` and one word-boundary count settled both in seconds.
  The discarded numbers, kept because the method that produced them is worth
  more than the answer: *"`log-read` 0 mentions and 0 uses in 75,805 exec
  blocks; `web-fetch` 0; the prompt is the single door."* The truth is
  `log-read` **80** uses, `web-fetch` **192**, `memories` **735 with zero
  prompt mentions** — so "named nowhere therefore used nowhere" is simply
  false, and discoverability was never the fault. **The fault was tool
  QUALITY**: shown every wake since June, `log-read` fell 48 → 21 → 11 uses a
  month because a tail with a 200-char cap cannot answer a question. General
  rule, now third-time-earned: **a zero is a claim about your instrument
  before it is a claim about the world.** And when you are about to build
  something on a measured absence, measure the presence of the same thing by a
  second method first.
  What survives of the discoverability idea is smaller and real: the catalogue
  gives a tool's `does:` line and nothing else, so `did-i` is also named in
  `protected-prompt.md` — not to make it reachable, which it already is, but to
  say WHEN to reach for it and to state the invariant behind it (your visible
  past is minutes; your recorded past is complete). A tool whose purpose is
  never stated gets tried and abandoned, which is exactly `log-read`'s curve.
- **When a new instrument reads the creature's record, say plainly whether it
  is PUSH or PULL before reaching for §2.5.** §2.5 says *"Never tell the
  creature about its own bugs... Chat is world-facts only: no offers, no
  debugging hints, no advice"* — and that governs what WE SEND. A search the
  creature runs on its own record is the opposite direction, and it already
  receives `kind=error` records in every wake render, so a history search
  changes the DEPTH of what it can reach and not the KIND. `did-i` therefore
  searches its journal unfiltered, deliberately. A filtered one would have been
  the house disease wearing a new costume: an instrument that reads plausible
  while withholding. And §2's own method asks for exactly this — *"make the
  fault visible to the creature so it can prune it itself"* — of which a search
  over its own history is the strongest available form. Judgement recorded so
  the next session does not re-litigate it; Tue delegated it explicitly.

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
- **Chat is a HERE-AND-NOW channel. It can carry a fact; it has never carried
  a habit change.** Tue's standing notion, held from early on and confirmed by
  measurement on 2026-09-21: *"the chat can only work to a here and now fix and
  question to speed things up that should be fixed in framework also."* The
  three chat interventions this project has ever made split cleanly by **what
  the framework did alongside**, not by how well the message was written:

  | chat used to | uses/month after | outcome |
  |---|---|---|
  | announce a capability the framework had just BUILT (`ask`, 08-14) | 79 Aug → **160** Sep | **adopted** |
  | correct a belief, nothing new framework-side (`llm_ask_helper`, told twice, 08-07) | kept using the broken path | **failed** — the operator had to fix the tool |
  | correct a belief (`git-save`, 09-20) | 503 → 102 → 21 → **0**, and 0 across 67 authoring actions after | **failed** |

  So a chat message is an **accelerant for something the framework already
  carries**, and worthless as the carrier itself. **It is never a valid answer
  to "how does this fact reach the creature"** — that is `gs-bug-daily` Tier 4
  item 5, and "we told it" now has a 0-for-2 record there. Write the message
  when it saves the creature a day of rediscovering something the framework has
  ALREADY made true; never write it in place of the framework change.
  The corollary is the useful half: **if the only available fix is a chat
  message, there is no fix yet** — either build the thing that makes the fact
  arrive unprompted, or accept that the behaviour stands and say so.
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
  passed; only the hash caught it. **the corrupting step is TRANSCRIPTION, not the wire.**
  Diagnosed 2026-08-26: a whole-blob transfer failed, then a 4-chunk transfer of
  the same bytes came through with all four hashes clean and rendered correctly,
  then a 10-chunk transfer failed on exactly ONE chunk. The channel is fine; what
  breaks is the session copying base64 out of a tool result into a decoder, at
  roughly one chunk in ten. That is why size looked like the variable — a bigger
  blob is simply more characters to mis-copy, with no way to localise the damage.
  **Method that works:** `split -b 470`, print `md5sum` per chunk plus the
  whole-file hash, verify EVERY chunk on arrival, assemble, and check the
  whole-file hash again. A bad chunk is then named and re-requested on its own
  instead of poisoning the image. Keep the chunk count low — each one is a
  transcription risk — and never trust a length, a PNG header or an `IEND`
  footer; two corrupt files have now passed all three.
  For a GUI change specifically, the cheapest verification is still to ask Tue to
  glance at the screen in front of him: it costs him two seconds and it is the one
  reading with no transcription step in it. Symptom of the corrupt file: PIL reads the header
  then dies with `unrecognized data stream contents`, and the image API rejects it.
  `-colors 8` PNG8 was also rejected outright; **grayscale plain PNG** worked
  (`-colorspace Gray -strip`, 660x46 → 1,910 b). `certutil -decode` is not the
  culprit — it and `base64.b64decode` agreed byte for byte on the corrupt copy.

---

## 8. State — 2026-09-23 20:10

**A LOCAL-MODEL BENCH NOW EXISTS FOR TEXT THE CREATURE READS, and its first
run said my own fix from this morning is NOT an improvement.** Tue's idea,
carried over from the Growing Cousin spinoff: *"for really killing bugs like
this you could also test your proposed fix on a local ollama model."* It
lands on the worst asymmetry in this file — §5's *"8 of 33 scars live in text
the creature reads, and they are the only ones that have ever RECURRED after
being fixed... a code fix ships with a test and a text fix was being verified
by hoping."*

`scripts/text_bench.py` (`d5a72e0`) renders the OLD and NEW wording of one
message over **real fixtures from the journal** and puts both to
**`gemma4:12b` — the same FAMILY as the production workhorse
`gemma-4-31b-it`** — at temperature 0, so a difference is the wording rather
than the dice. It runs on the workstation (RTX 3080, 10 GB), **never on the
creature's host**, which has 3 GB of RAM free and a 2013 GPU. **The local
model is a BENCH and must never become a rung** (§6's quality floor); it
talks to localhost and the ladder does not know it exists.

**The result, over 32 real comment-led blocks:**

| wording | named the right command | named a comment |
|---|---|---|
| old (quoted the whole block) | 20/32 — **62%** | **0/32** |
| new (quotes the command) | 22/32 — **69%** | **0/32** |

**+2 of 32, from 6 gains and 4 losses across 10 changed verdicts. That is
noise, not a signal.** So the done-gate fix is **NOT VERIFIED** as a
behaviour change. What remains true of it is narrower and still worth having:
a comment cannot exit 1, so the old message was *literally false* about the
artifact it described, and §5 requires that be fixed regardless of whether a
model notices. **What I implied this morning — that the creature had to guess
which command failed — is not demonstrated.**

**And the bench refuted my actual diagnosis.** I said the old wording makes
the reader name the comment. **It never did, in 64 trials: 0/32 both ways.**
The failure mode is completely different — when the model gets it wrong it
**invents a plausible command that was never run** (`python3 -m
tests.policy_check`, `python3 scripts/digest_entity_tracker.py`). That the
right command is identified only ~65% of the time *either way* is a far
bigger finding than which line is quoted, and no instrument we had could see
it.

**The bench found two faults in itself on its first run, which is the honest
part.** `gemma4` spends **7,517 chars of `thinking`** on this prompt and
returns an EMPTY answer even at a 2,000-token budget — the same *"empty
completion (reasoning-only, answer truncated)"* shape `groq_oss120` returns
in production; **14 of 16 replies came back empty** and with `think=false`
the same model answers in 8 tokens. Worse, it **printed "NOT AN IMPROVEMENT"
off those 14 empty replies** — a verdict drawn from nothing, this project's
own house disease arriving inside a brand-new instrument within minutes of
its birth. It now says UNKNOWN and reports no verdict when more than a fifth
of replies are empty.

**Read the bench this way round: a PASS is weak evidence, a FAIL is strong.**
A local 12B is not the 31B the creature runs on, so it cannot prove a message
works — but if a model of the same family misreads our sentence, the sentence
is ambiguous.

**Also corrected: a quiet `git pull` that failed and I did not notice.** An
untracked local fixtures file blocked it, `-q` swallowed the error, and the
bench re-ran the old 8 fixtures while I read the count from the stale file.
The commit hash was one `git log -1` away from showing it. **`-q` on a pull
whose result you are about to depend on is the same class as trusting a patch
script's exit code** — which cost four separate corrections earlier today.

**Named trigger: the next text change the creature reads gets benched BEFORE
it ships**, not after. The `tool-edit` write-time warning, the broken-tool
warning, the truncation marker and the chat one-shot line are all unbenched
and all in the class that has recurred.

---

### Previous state — 2026-09-23 18:45

**Tue asked whether anything besides `retryDelay` was ready to fix, and said
to do them all. Five were ready; all five shipped.** Gates **laptop 559 PASS,
PC 551 PASS** (the PC figure is from before the last 2 checks; re-run next
session). Brain restarted 18:29:27 and holds everything.

**Two of the five turned out to be the OPPOSITE of what §8 recommended this
morning, and both corrections came from checking a dependency before acting.**

- **`groq_oss120` must NOT be retired.** `framework-tools/ask` reads
  `GROQ_OSS120_API_KEY`, and `sandbox.py:52` withholds a disabled rung's key
  from the container — so `enabled: false` would have broken **the most
  adopted framework tool we have** (165 calls in September, still rising).
  **DEMOTED instead**, to last among the enabled rungs, keeping the key. It
  sat ABOVE the workhorse while serving **0 cycles across three windows** with
  301 `too_large` and 287 `quota` walls in 17 h; at 8,000 TPM it cannot take a
  wake-sized prompt and never could. `ask` verified from inside the body after
  the change: `ok`.
- **`mistral` must NOT be repointed.** `mistral-medium-latest` and
  `mistral-small-latest` returned **429 rate_limited on every probe across 25
  minutes**, so neither could be validated on a wake-sized prompt, and
  repointing to an unvalidated model is exactly what cost 651 cycles on
  08-19. **RETIRED instead** (`enabled: false`, dated): `mistral-large-latest`
  answers `HTTP 403 tier_not_allowed` — a paywall, which §6 makes defunct for
  us by definition. Safe: not a `LEGACY_KEY_ALIAS`, and 0 tools reference
  `MISTRAL_API_KEY`. **A replacement account is needed and that is Tue's.**

**The enabled ladder is now four and honest about it:** `gemini_flash` →
`google_gemma` → `cloudflare` → `groq_oss120` (last resort, kept for its key).

**The three code fixes, `8afc647` and `00c420d`.**
1. **`prov.call` kept `body[:200]`.** Measured against the real 1,382-char
   Google 429 body that discards everything machine-readable: `limit` at
   offset 400, `RESOURCE_EXHAUSTED` at 482, `quotaMetric` at 903, `retryDelay`
   at **1342**. So for the life of the project every provider told us exactly
   when to come back and we threw the sentence away. Cap is now **1500**,
   chosen from those offsets. This was only safe because the morning's
   status-vs-body separation stopped digits being read out of body text.
2. **The loop slept a flat 120 s while Google asked for 41 s** — 139 quota
   sleeps in 17 h. `prov.call` now parses `Retry-After` and `retryDelay`,
   `record_exhaustion` writes it as an absolute time, and the loop waits that
   long. **Clamped into [5, 120] with the max being the OLD FLAT VALUE on
   purpose: this can only ever shorten a sleep, so the worst case is exactly
   the behaviour it replaces.** Nothing is invented — a silent provider still
   gets 120.
3. **FLATLINE fired for `cloudflare` by construction.** It spends its daily
   allowance in ~5 h and is dark 16–18 h, so against a 12 h threshold it
   crossed daily: `SERIOUS:cloudflare` on **269 of 1,046 health lines**, 26%
   of every health line ever written, none of which could have meant
   anything. Threshold is now per rung under a stated rule — **a rung's
   threshold must exceed its own reset period, or the alarm measures the
   calendar instead of the rung**. Raising the global value was rejected: it
   would blind the check for `google_gemma`, whose 55 h of silence is why the
   instrument exists. The live line now reads **`FLATLINE:ok`** for the first
   time in weeks.

**THE LESSON OF THE EVENING, and it is the same one four times.** *Verify the
artifact, never the script's exit code* earned its keep **four separate times
in one session**: a patch script died mid-run leaving `provider.py` edited and
three files not; a second died leaving `loop.py` calling `_qs` with no import;
a re-run silently **duplicated** a whole test block because the replacement
text contained its own anchor (gate went 559 → 561 and still said ALL TESTS
PASS); and the retryDelay fix **shipped broken**. Every one was caught by
`grep -c` on the file, never by the gate.

**The fourth is the instructive one.** `record_exhaustion` returns early when
a rung is already walled, and the `retry_at` write sat BELOW that return — so
it only ever fired on a rung's very first failure, and rungs are almost always
already walled by the time the loop sleeps. **Every unit test passed, because
every one called it on a fresh dict.** Production said it in one line within
seconds of the restart: the keychain printed *"provider says retry in 49s"*
while the loop, in the same second, printed *"retrying in 120s (no provider
delay given)"*. Fixed `00c420d`, with the rule now stated in the code: **the
two timestamps have opposite update rules** — `exhausted_at` marks where a
dark period began and must never move, `retry_at` is forward-looking so the
most recent statement always wins.

**Status of the evening's work, honestly split.** The parser is **verified
live** (49 s, 48 s, 15 s read off three different rungs). `retry_at` is
**verified recorded** in `quota_state.json`. The nap itself is **ARMED BUT NOT
YET EXERCISED** — the all-rungs-walled branch has not fired since 18:29, so
nothing has yet slept a provider-stated duration. **First check next run: a
`Quota exhausted - retrying in Ns (provider-stated)` line with N well under
120, and whether the quota-sleep count falls from 139 per 17 h.**

**Everything else from the 18:05 entry stands**, including `did-i` at 0 calls
with its **2026-09-25** trigger, the `cannot_start` backslash tool, and the
five API keys pending rotation.

---

### Previous state — 2026-09-23 18:05

**gs-bug-daily 2026-09-23 18:05 (17.0 h since this morning's run, NO gaps).**
235 served at **13.1/h**, 310 exec, **4 skips**, **13 errors and ALL 13 are
guard rails** (6 cannot_start, 4 false-completion, 3 upgrade-no-change). Zero
provider, zero unclassified, zero provider-shaped failures under other kinds.
Truncation **12.8%** (up from 7.6%). Library **743**, `cannot_start` **20 →
21**. Funnel: 18 tools at 3.0 rounds, 19 done-marks / 13 refused / **6
accepted (32%)**. Gates: **laptop 537 PASS, PC 531 PASS**.

**THIS MORNING'S FIX FOUND THE BUG UNDERNEATH IT WITHIN ONE WINDOW, and that
is the whole story of the day.** The GONE line was corrected at 00:44 to quote
the provider instead of asserting a hardcoded `"(404 from the provider)"`. By
17:51 it had caught this, twice:

> `cloudflare: model @cf/... reported GONE by classify_error -- no models left
> on this rung -- walling it. Provider said: HTTP 429: {"errors":[{"message":
> "AiError: you have used up your daily free allocation of 10,000 neurons...`

**An HTTP 429 classified as GONE.** The cause is the hazard §8 named on
2026-08-27 and gave a trigger: `classify_error` matched **bare digits anywhere
in the error body** (`"404" in err`), and **Cloudflare puts a UUID in every
error**. The live body ends `...continue usage. (d008a44d-` — a UUID, cut at
`body[:200]`. Two of those UUIDs contained `404`. The old prediction was ~0.7%
per error; cloudflare errored ~498 times in the window, so ~3 hits expected
and **2 observed**.

**Fixed `16389bb`. Invariant: A NUMBER IS EVIDENCE ONLY WHERE THE PROTOCOL PUT
IT.** `classify_error` now parses the status once, from the front where
`prov.call` writes it, and every digit rule reads that and nothing else; words
still match the body; an error with no parseable status fires no numeric rule
at all. `5035` is a BODY code so it is pinned to its HTTP 403. **17 checks, the
load-bearing one being the real captured body, mutation-proved** — restoring
`"404" in err` fails that one check and nothing else.

**What that chain says about method, and it is worth more than the fix.**
Yesterday I fixed a diagnostic for lying about *what it observed*. That fix
had no behavioural effect at all — it only changed a log line. **Within
seventeen hours it exposed a live classification bug that had been retiring
healthy rungs silently for a month.** A false diagnostic does not merely
mislead; it hides the thing underneath it. The order was forced and I had it
backwards in yesterday's entry: I wrote that status-separation had to come
first to unblock widening. In fact the honest MESSAGE had to come first,
because nothing else could have shown which errors were being misread.

**The three fixes from this morning are all VERIFIED in production.**
- **The done-gate comment fix:** 4 false-completion blocks since 00:44 and
  **0 of 4 quote a comment**, against **142 of 279 (51%)** before. They read
  `` `step-planner-tracker list` ``, `` `ls -l /workspace/knowledge/` `` — real
  commands.
- **The GONE line:** quoting the provider, and it caught the bug above.
- **The WALLED-as line:** 2,531 lines in 17 h, and it answers questions no log
  could answer before. Full split: `gemini_flash/quota` 616,
  `mistral/quota` 503, `cloudflare/quota` 498, `google_gemma/quota` 324,
  **`groq_oss120/too_large` 301**, `groq_oss120/quota` 287.

**`groq_oss120` is confirmed as a pure tax: 301 `too_large` walls, 0 cycles
served, from a slot ABOVE the workhorse.** Every cycle pays a reach and a hop
for it. That is now three windows of zero. **Next `gs-ladder`: move it below
`google_gemma` or retire it** — it cannot take a wake-sized prompt at 8,000
TPM and never could.

**The retryDelay fix is now UNBLOCKED.** Yesterday's entry said the order was
forced — separate status from body, then widen `prov.call`'s `body[:200]`,
then honour the `retryDelay: 41s` the provider asks for instead of sleeping
120 s. The first link shipped today, so widening is safe now. 139 quota sleeps
in this window. **Named trigger: 2026-09-25, top item.**

**`cannot_start` 20 → 21, and the guard caught most of what caused it.** The
done-gate's `cannot_start` block fired **6 times** — the first real activity
from that guard in weeks — and the broken-tool warning was mentioned in **19**
records, against 0 last window, so the set changed and the creature was told.
One tool leaked through: `memory_archive_search_helper`, *"line 86: f-string
expression part cannot include a backslash"* — the backslash family, one of
§5's three LLM-file-corruption classes, unchanged since 08-19.

**Throughput is flat at 13.1/h** against 12.8, still under the 15/h floor, with
**61% of 604 `think_start`s finding no rung**. Ladder: `google_gemma` 198,
`cloudflare` 27, `gemini_flash` 10, `groq_oss120` 0, `mistral` 0. `cloudflare`
dropped off the SERIOUS list today, so only `mistral` remains there.

**Everything else from the 00:50 entry stands**, including the mistral repoint
(the account is alive; only `mistral-large-latest` is 403 `tier_not_allowed`),
gemma's real limit of **16,000 input tokens per minute**, `did-i` at 0 calls
with its **2026-09-25** trigger two days out, and the cloudflare FLATLINE
firing by construction (**2026-09-27**).

**Blank pass: none.** Item 19, added this morning, would have caught the
`groq_oss120` zero-serve — and did.

---

### Previous state — 2026-09-23 00:50

**gs-bug-daily 2026-09-23 (31.3 h, NO gaps, 32 hours with records).** 408
served at **12.8/h** — down from 17.1 — 520 exec, **7 skips** (all truncation),
and **10 errors of which ALL 10 are guard rails** (done_gate/false_completion,
four sampled by hand and all correct). Zero provider, zero unclassified.
Truncation **7.6%** (10.6% → 7.6%). Library **742**, `cannot_start` **20**,
flat, and **0 of the 22 tools written in-window fail to start** — the flow is
clean for the fourth window running. Funnel: 26 tools at 3.2 rounds, 30
done-marks / 10 refused / **20 accepted (67%)**, sanity-checked per item 17.
Gates: **laptop 520 PASS, PC 514 PASS**.

**THE HEADLINE IS A CORRECTION TO THIS FILE, and it was produced by an
instrument that did not exist three hours ago.** §8 has said since 09-02 that
`mistral` is dark because its **monthly allowance** is spent and that it
**"returns 10-01"**. That is false and has been false for some or all of 480
hours. The rung answers `HTTP 403 {"message":"This model is not available in
your subscription tier","type":"tier_not_allowed","code":"1910"}` — a
**paywall, not a reset**, and §6 says a rung behind a paywall is DEFUNCT for
us by definition. Nobody could see it because the branch that walls an account
**printed nothing at all**.
**But the account is ALIVE and the rung should be repointed rather than
retired.** Probed through `provider.call`: `mistral-large-latest` 403
tier_not_allowed; `mistral-medium-latest` and `mistral-small-latest` **429
rate_limited** — reachable, not tier-blocked; `ministral-8b-latest` **answers a
wake-sized prompt with `finish=stop`**. So only the large model moved behind
the tier. **Named trigger: next `gs-ladder` — repoint to
`mistral-medium-latest` after one clean-window wake-sized validation.**
`ministral-8b` is excluded by the quality floor, not by capability. Config
change, so it follows ladder discipline rather than being done in a bug-daily.

**THE WORKHORSE'S REAL LIMIT IS A DIFFERENT DIMENSION FROM THE ONE CONFIG
NAMES.** `google_gemma` walled **235 times in 32 h** while serving 365 cycles
against a configured `limit: 14400`/day, and no instrument could say why. One
live call settles it: the 429 body carries
`quotaId: GenerateContentInputTokensPerModelPerMinute-FreeTier`, **limit
16,000 — INPUT TOKENS PER MINUTE**. Requests per day was never the binding
constraint. Two consequences, both measured:
- The loop sleeps **120 s** on a quota wall while the body says
  **`retryDelay: 41s`**. 302 sleeps in the window ≈ **6.6 h of unnecessary
  sleep in 32 h**, which is most of the gap between 12.8/h and the 15/h floor.
- **A fatter wake context now costs throughput directly**, because fewer
  cycles fit in 16,000 tokens/minute. That is a THIRD edge of the 08-29 cap
  raise, and §5's rule that a context-size change has two edges was already one
  short.

**FIXED UP FRONT — four, and they are one class wearing three costumes: a
diagnostic that names something it never checked.**
1. **`73cf999` — the GONE line hardcoded `"(404 from the provider)"`** while
   `classify_error` returns `gone` for 404, *not found*, *no endpoints*,
   *model_not_found*, the Workers-free-plan 403, and any body that merely
   CONTAINS the characters 404. On 09-22 it named `groq_oss120` and
   `cloudflare` GONE six times. **Probed today: groq_oss120 answered and
   cloudflare returned its own documented daily-allowance 429. Both alive.**
   §6 says *"a defunct model is removed the moment it is detected... do not
   queue it for his decision"* — so two live rungs were one reading away from
   being disabled, by the book. The line now quotes the provider.
2. **`73cf999` — the wall that printed nothing.** `gone` has printed since
   08-17 and `flaky` prints on every hop; the branch that actually walls an
   account was silent. **Verified firing in production 30 seconds after the
   restart, on four rungs** — and it immediately produced both findings above
   plus the next one.
3. **`8002a57` — the new test constructed `Keychain()`**, which reads
   laptop-only `config.yaml`: green on the host, red on the PC. The
   green-here-red-there scar, fourth instance.
4. **`1c26df2` — the done-gate told the creature a COMMENT had exited with
   code 1.** `bad_cmd[:120]` is the whole exec block and the creature opens
   most blocks with a comment stating its plan: **142 of the 279
   false-completion blocks since 09-01 — 51% — quote a comment.** This one is
   in text the creature READS, which §5 records as the only class of scar that
   has ever recurred after being fixed, so it is held to the code standard.
   Verdict logic untouched; only the quoted fragment changed.

**AND THE EMBARRASSING HALF, two days after the last one of exactly this
shape.** Fix 4 first shipped with tests on the helper alone — and **the
mutation PASSED**: the rendered message still quoted the comment while the
gate stayed green at 517. That is 2026-09-21's *"a suite that tests only the
pieces stays green while the assembly is broken"* reproduced 48 hours later by
the person who wrote it down. The message is now a named function
(`_false_completion_reason`) with the RENDERED string under test, and
reverting the call site fails two checks. **Second time in one session that
verifying the ARTIFACT rather than the script's exit code caught something:**
a re-run of a patch script aborted on its assert and left `loop.py` half
mutated, and only `grep -c` on the file showed it.

**THE §8 UUID HAZARD HAS FIRED, and it is the root of the false-GONE.**
The trigger was *"the first walled rung nobody can explain, or 2026-09-10"* —
both conditions are now met. `classify_error` matches **bare digits anywhere
in the body** (`"404" in err`) and checks `gone` **before** `quota`, so any
error text containing those three characters retires a live model. This also
**blocks the retryDelay fix above**: `prov.call` keeps `body[:200]`, and
measured against the real 1,382-char Google 429 body the useful fields sit at
**offset 400 (`limit: 16000`), 482 (`RESOURCE_EXHAUSTED`) and 1342
(`retryDelay`)** — none survives — but widening the capture makes the
digit-matching hazard strictly worse. **So the order is forced: separate
status from body, then widen, then honour `retryDelay`.** Named trigger:
**2026-09-25, top item.** It is the largest measured throughput loss on the
board.

**`groq_oss120` served 0 of 408 cycles and the new line says why:** `HTTP 413
Request too large` on every reach. It sits ABOVE `google_gemma`, so every
cycle pays a reach and a hop. Known since §8 08-17 ("TPM-walled at 8000, so it
cannot take fat thinks") and never visible in a log until today.

**Ladder:** `google_gemma` 365, `cloudflare` 24, `gemini_flash` 19,
`groq_oss120` **0**, `mistral` **0**. Effective depth is **one**, and 63% of
1,106 `think_start`s found no rung at all (55% last run).

**Instruments.** `THROUGHPUT:!!` fired all window at 10–13/h and for the right
reason — and for the first time we can say what the reason IS. FLATLINE named
`mistral` correctly as dark and **carried the wrong cause for 20 days**.
FLATLINE on `cloudflare` still fires by construction (trigger 2026-09-27).
The escalation ran **37 times with 6 ending `finish=stop`**. The broken-tool
warning was silent, correctly — the set did not change. `UNMET:330n/10763d+0
streak 0/7`. `WAKE:p50` **3630 ms** against the 5,000 budget, rising with the
library (3271 → 3630). `COMPOUND:739t/1244e **1.68/t** marg **4.23** streak
0/3` — new work still far more connected than the corpus it joins.

**Item 13 keeps earning its place:** 3 provider failures (`EMPTY-REPLY`,
provider returned nothing) sat under kind `idea_gate`, invisible to a census
keyed on `kind == "error"` — which is why the error bucket reads zero provider
errors and that reading is true but incomplete.

**`did-i`: 0 calls this window, 2 lifetime, none since 09-19.** The
**2026-09-25** trigger is two days out and **NOT met**. `git-save` 0, as
recorded when the chase was retired. Framework-tool monthly curves are
otherwise healthy: `ask` 79 → **165**, `web-fetch` 57 → **85**, `memories`
48 → 62. `tool-find` fell **937 → 232** — worth a look at the next
`gs-products`.

**Doors:** `tool-edit` 64, redirect-or-tee 8, `tool-new` 8. The redirect share
fell from 18% to 10%.

**Blank pass:** the finding is that **a rung serving ZERO while reopening
dozens of times is invisible to every item on the list.** `groq_oss120`
reopened 28 times, served 0, and nothing flagged it: FLATLINE watches last
success (it had one — the probe), the skip rate has no denominator for a rung
that never serves, and the provider-mix table just shows a small number. Now
mandated as `gs-bug-daily` item 19, dated.

---

### Previous state — 2026-09-21 18:00

**ANSWERED: `tool-edit` should NOT version what it overwrites, and the reason
is that a BETTER mechanism already exists and nobody knew its coverage —
including me, four days ago, when I wrote that a tool was "gone".** Tue asked
the question and asked whether a search could answer it. Partly: the search
supplied the trap, and reading our own system supplied the answer.

**What the fetch contributed, and it is decisive.** The 2026 checkpoint/rollback
literature names the exact failure of the design I was about to consider:
*"Checkpointing does not track file changes made by bash commands — a `rm` or
`mv` executed through a shell tool is invisible to it; only edits made through
the harness's own file-editing tools are captured."* That is **our** situation
measured: this window's authoring split is `tool-edit` 103, `tool-new` 17,
**redirect-or-tee 26**. Versioning inside `tool-edit` would miss **18% of
writes**, and the redirect is precisely the door §5 already calls the dangerous
one (no `.bak`, no execute bit, *"a fixture written OVER a live tool is a stub
that lies"*). Aider is the strongest prior art for per-edit commits — one commit
per edit with `/undo`, treated as a feature — and its documented downside is
noisy history for PRs and `git rebase -i`, an objection that **does not transfer
here** because nobody reviews the creature's repo.

**What our own system contributed, and it settles it.** `runtime.py` already
calls `savegame.save(..., label="pre-risky")` whenever `_is_risky_command`
fires. **18 snapshots exist, 06-21 → 09-18, 2.0 GB, each a full copy of the
mind including `tools/own`.** Verified by doing, not by reading: a snapshot
file is **byte-identical** to the live one (`md5` match), and the 09-10 copy of
`recall_and_answer` (2,976 b) **STARTS** today, sitting beside 732 other tools.
So the framework already has **door-agnostic** versioning that sees redirects,
`tool-new` and `tool-edit` alike. Adding it to `tool-edit` would be a SECOND
copy of a capability we have — §4's disease at the feature level — with
strictly worse coverage.

**So the real fault is the TRIGGER, not the absence.** Snapshots fire on
*risky commands*. The `recall_and_answer` destruction was ten ordinary
`tool-edit` calls in five minutes — nothing risky — so nothing fired. The gaps
prove it: **06-24 → 09-10 is 78 days with no snapshot, and 09-11 23:12 →
09-18 03:11 is 6.5 days, with the 09-17 01:24 destruction inside it.** That is
why the 3,626-byte version is genuinely unrecoverable, and **it corrects my own
09-17 wording**: not "there is no history" but "the history has holes exactly
where ordinary work happens".

**RECOMMENDATION — build nothing today, and here is the counter-pressure.**
The symptom is one lost tool in three months, and §6 says measured cost beats
theoretical harm. Against that: **the snapshot store is 2.0 GB and is NEVER
pruned** (oldest is 06-21 and still present) while the body-image pruner
demonstrably bounds its own images — and disk is the one resource CLAUDE.md
names as genuinely unbounded, currently **78% / 24 G free**. Making snapshots
more frequent would push on exactly the resource that has twice been the real
emergency. **A cadence trigger and a retention policy have to be designed
together or not at all, and that is design, not repair — Tue's call.**
**Named trigger: the next working tool destroyed past recovery, OR the
snapshot store passing 4 GB, whichever comes first.** Instruments: `did-i
<tool>` establishes the destruction retroactively, and `du -sh
~/growing-spine-saves` the store.

**The cheap half is already done: knowing.** The recovery path is
`~/growing-spine-saves/mind-<stamp>-pre-risky/tools/own/<tool>` — and §2.1 says
restoring one is the creature's call, not ours.

---

### Previous state — 2026-09-21 17:10

**gs-bug-daily 2026-09-21 (50.3 h, NO gaps, 52 hours with records).** 859
served at **17.1/h** — the best sustained rate since the ladder thinned — 1,098
exec, **22 skips**, and **27 errors of which ALL 27 are guard rails** (25
false-completion, 1 spin trap, 1 upgrade-no-change). Zero provider, zero
unclassified. Truncation **10.6%** (12.0% → 10.9% → 10.6%). Skip by rung:
`google_gemma` 1.6%, `cloudflare` 0.0%, `gemini_flash` 27.8%. `think_start`s
finding no rung **61% → 56% → 55%**. Library **737**, `cannot_start` **21 →
20**. Funnel: 34 tools at 3.4 rounds, 57 done-marks / 26 refused / **31
accepted (46%)** — sanity-checked per item 17.

**THE COMPOUNDING QUESTION IS ANSWERING POSITIVELY, and the marginal is
computable for the first time.**
`COMPOUND:737t/1241e 1.68/t depth[0:161/1:176/2:145/3:224/4:30/5:1] max5
new7d:1.91x43 brief:1.79/1.19 anach:22 carry:54%/520pd marg:4.12 vs 2026-09-18
streak 0/3`. **New work brings 4.12 edges per tool against a 1.68 corpus
average** — far MORE connected than the body it joins, so the average must
rise, and the threshold-free alarm is correctly silent at 0/3. The longest
real chain is five deep: `SelfHealingReplanner → ArchiveDrivenStepReplanner →
ArchiveDrivenPlanRecovery → step-planner-tracker → knowledge_gap_filler →
subagent_ask_helper`.

**FIXED UP FRONT, and the second one is the embarrassing half.**
1. **`deep3` went 48 → 257 while edges moved 1236 → 1239.** Three edges cannot
   make 209 deep tools, so item 17's sanity rule — added two days ago — caught
   it. It was **arithmetically correct**: depth is recursive, the edges landed
   on `step-planner-tracker` (the most-invoked tool in the library), and every
   tool above that hub gained a level at once. **A threshold count over a
   recursive metric is a cliff, not a trend** — the series 27/17/47/48/257 was
   never a trend line. Now reports the DISTRIBUTION plus the max chain, which
   cannot move without the population moving; `deep3` is still written to the
   state file so the recorded history stays comparable.
2. **Then that fix shipped BROKEN and the gate did not notice.** The patch
   script aborted on an assertion *before* its write, so `depth_hist` was
   REFERENCED by one edit and never DEFINED by the other, and
   `check_compounding` raised `NameError` on **every call**. **The gate was
   green at 502 throughout**, because every test covered a pure helper and not
   one of them called the function those helpers exist for. Blast radius was
   the **entire 06:30 health line** — `__main__` builds it in one list, so the
   exception would have taken `SENSOR`, `JANITOR`, `FLATLINE`, `UNMET` and
   `WAKE` with it. Found by RUNNING it rather than by reading the gate.
   **Two lessons. A multi-step patch script that asserts before writing can
   leave a file half-edited across separate runs, so verify the artifact and
   never the script's exit code. And a suite that tests only the pieces stays
   green while the assembly is broken** — the same shape as *"a guard verified
   through the guarded door is not verified"*, which this project learned in
   August and which I have now reproduced with the pieces instead. 3 end-to-end
   checks now call `check_compounding` and assert it returns a line.

**FAILED VERIFICATION, and it is the honest headline: telling the creature was
not enough.** The `git-save` correction was read at 09-20 23:37 and answered
*"Got it. I'll use `git-save` for both files and directories now that it's
fixed."* Since then: **317 cycles, 67 authoring actions, and ZERO `git-save`
calls.** That is not a short window and not a missing opportunity — every one
of those 67 was an occasion. **Acknowledgement did not convert to adoption, for
the second time in this project's history** (`llm_ask_helper`, 2026-08-07: told
twice, agreed twice, acted never). This moves from `unverified` to **FAILED**.
The two fixes shipped in response — journalling the exchange so `did-i` can
find it, and telling it the message is shown ONCE — **are both UNEXERCISED**,
because no chat has been sent since they landed at 23:52. They are the next
test, not a result.

**The `git-save` ADOPTION CHASE IS RETIRED, under the principle it just
proved.** §6 now says: *"if the only available fix is a chat message, there is
no fix yet — either build the thing that makes the fact arrive unprompted, or
accept that the behaviour stands and say so."* Applied here, honestly:

- **The tool is fixed and that was worth doing regardless** — 402 tracebacks
  are a framework fault whether or not anyone calls it again.
- **Chasing adoption further is not available to us.** We have tried the only
  channel we have and it is 0-for-2. Nagging is explicitly forbidden, and
  building machinery to push one built-in would be the nanny half of §2.
- **But the underlying cost is REAL and measured, so this does not close as
  "no symptom".** `recall_and_answer`'s working 3,626-byte predecessor is
  **gone** — `tool-edit` keeps exactly one `.bak` and that was the ninth
  broken attempt in five minutes. Version history would have saved it, and the
  creature's own repo already existed at `/mind/tools/own/.git` the whole time.

**So the real question is not whether it uses `git-save`. It is whether
`tool-edit` should version what it overwrites** — the framework carrying the
fact rather than asking the creature to remember. That is a genuine design
change to protected scar tissue (§2.2) with real cost questions (a commit per
edit, at 103 edits in 50 h), so it is a **finding, not a fix**: *"anything you
would have to argue for is a finding with a named trigger and a date."*
**Named trigger: the next time a working tool is destroyed past its single
`.bak` — the instrument is a tool that was startable and is not, whose `.bak`
is also broken. `did-i <tool>` can now establish that retroactively, which it
could not on 09-17.** Until then the behaviour stands, and that is recorded
rather than hoped away.

**`did-i`: 0 calls in 50 h, 2 lifetime.** The **2026-09-25** trigger is four
days out and currently **NOT met**. Per its own rule, measure per MONTH; two
calls is not adoption.

**Doors:** `tool-edit` **103**, redirect-or-tee **26**, `tool-new` **17**. The
redirect share is holding, not rising.

**Blank pass:** the finding is item 2 above — a helper suite is not a smoke
test. Now mandated implicitly by the three end-to-end checks; the general rule
belongs with the gate discipline in §3 rather than as a new numbered item.

Gates: **laptop 505 PASS, PC 499 PASS**.

---

### Previous state — 2026-09-21 00:05

**"In one ear out the other" — Tue, on the git-save correction being
acknowledged and changing nothing. He is right, and the room produced it.**
The chat contract asked for exactly ONE thing, a `<reply>` tag, and that is
precisely what it delivered: read 23:37, *"Got it"* 23:38, and by 23:39 the
fact existed nowhere the creature could reach. **Identical to `llm_ask_helper`
on 2026-08-07 — told twice, agreed twice, acted never.** The instruction was
obeyed perfectly and the outcome was useless, which is §5's most expensive
class.

**Two independent routes shipped tonight, and they fail differently on
purpose.**

1. **`f24eaa4` — the exchange is journalled** (`chat_from_tue` / `chat_reply`,
   outside `MEANINGFUL_KINDS`). Works even if the creature records nothing:
   the fact becomes findable by `did-i`. Covers forgetting.
2. **`980c513` — the creature is told the message is shown ONCE.** The new
   line: *"This message is shown to you ONCE. It will not be in your next
   cycle's context and nothing will repeat it. Your reply is not storage. If
   it changed a fact you rely on, it survives this cycle only if you put it
   somewhere that lasts."* Covers the decision.

**Why that wording, precisely.** It is **making an existing fact legible, not
adding a rule** — `chat_block` is built only while a message is UNREAD, so the
message genuinely is one-shot and the creature had no way to see that. By
`gs-bug-daily`'s own test (*"does the change add a constraint, or make an
existing fact legible?"*) that is repair and therefore ours, not a §2.7
announcement. **The INVARIANT is named and the MECHANISM is not:** saying "run
`remember`" would be the `jq -n` mistake a third time, obeyed to the letter and
rebuilt by another route, exactly as it stopped using `jq` and reached the same
broken shape by heredoc 36 hours later. And the sentence is **conditional** —
*which* messages are worth keeping stays its judgement, so this cannot decay
into remembering every "hello".

**The load-bearing test is the NEGATIVE one:** the chat literal must name no
tool at all. A test that only asserted the new words would pass while someone
helpfully added the mechanism back. 5 checks total, including a regression that
the reply tag is still required — Tue getting an answer is why the channel
works.

**This is verified by BEHAVIOUR, not by hoping.** §5: 8 of 33 scars live in
text the creature reads and **they are the only ones that have ever recurred
after being fixed**, while no code scar has. **Measurement: does a durable
write follow the next chat message** — and separately, does `git-save` appear
in an exec block. Neither is answerable tonight; the creature has authored no
tool since replying.

**Deliberately NOT done: writing the memory for it.** The framework could call
`remember` on its behalf at delivery. That writes into its world, cannot know
which facts matter to it, and makes it dependent on our judgement — against
§2's *"never build anything that makes it depend on your inspection"* and the
README's *"we shape the creature's environment, we never program the
creature."* The room was wrong; the room is fixed.

Gates: **laptop 500 PASS, PC 494 PASS**. Brain restarted 23:55:21.

---

### Previous state — 2026-09-20 23:55

**Tue asked how long the creature remembers a chat message, and the answer
found a live framework fault in under an hour.** It read the `git-save`
correction at 23:37 and replied at 23:38 — *"Got it. I'll use `git-save` for
both files and directories now that it's fixed."* Then the three stores that
could hold that fact were checked, and they have three different lifetimes:

| store | holds | lifetime |
|---|---|---|
| the chat context | the correction | **ONE CYCLE** — `chat_block` is built only while the message is UNREAD, so it vanished the instant the reply was extracted |
| its own memory | **nothing** — zero rows mention `git-save` across all four stores | never written, in either direction |
| `journal.jsonl`, what `did-i` searches | **the 402 failures** | permanent |

**The correction was not in the journal at all.** It lived only in
`chat.jsonl`, which nothing the creature runs can read. Verified in the live
body: `did-i git-save` returns **3,000 records** whose four most recent commands
all end `exit=1 stderr=Traceback`, and **not one word about the repair**. So the
only durable searchable record still taught the false belief — and **the history
tool shipped two days earlier was the thing that would have re-taught it.** The
house disease inside my own instrument: reads plausible, wrong about the
present.

**Fixed `f24eaa4`.** A consumed exchange is journalled as `chat_from_tue` and
`chat_reply`, on **both** paths that consume it — answered, and given up on
after three attempts — because it was delivered either way. **Outside
`MEANINGFUL_KINDS`**, like `oracle_rest`: the message already had its one
cycle, and re-showing it every wake is the nag §2 warns against, so it reaches
`did-i` and any census but never the render. Invariant: **a fact told to the
creature must be findable in the record the creature can search.** 4 checks.
Brain restarted 23:52:32.

**Deliberately NOT backfilled.** Writing a record with a past timestamp to make
history say what we wish it had said is the fixture-that-lies class, and
re-sending the correction purely to get it into the journal would spend the
creature's attention on our bookkeeping. **The already-sent message stays
unfindable; every future one is findable.** If the `git-save` false belief
resurfaces, a fresh correction now lands in the searchable record.

**The general shape, worth more than the instance.** Acknowledgement is not
adoption, and this project has the scar: on 2026-08-07 the creature was told
twice in chat that `llm_ask_helper` was calling GPT-2, agreed both times, and
did not act. `gs-bug-daily` item 12 exists for exactly that gap. **The reply is
also the cheap half** — "got it" costs nothing, a `git-save` call in an exec
block costs a decision. **Measurement unchanged: does `git-save` appear in an
exec block.** Judge it after it next writes a tool; at the time of writing it
has authored none since replying, so the current zero means nothing.

Gates: **laptop 495 PASS, PC 489 PASS**.

---

### Previous state — 2026-09-20 23:35

**THE 2026-09-20 THINK-CEILING TRIGGER IS CLOSED: the ceiling is NOT raised,
and this is decided on evidence rather than deferred again.** Three readings
settle it. (1) **165 escalations since 09-16, of which 9 ended `finish=stop`** —
a later rung completed the reply **within the same 3,072 ceiling**, so that
truncation was rung-specific and no larger budget was needed. (2) The other
156 degraded, and that is mostly **ladder depth, not budget**: `google_gemma`
served **489 of 540** cycles this window, so an escalation usually has nowhere
to go. (3) The symptom is **shrinking on its own** — truncation 12.0% → **10.9%**
and `exec_skip` **15 of 662 exec blocks (2.3%)**. Raising the ceiling would tax
every call on the scarcest resource while throughput is the binding constraint,
against a 2.3% loss that is already falling. §6: *"Don't fix what has no
symptom. Measured cost beats theoretical harm."*
**Re-arm condition, so this is a decision and not an excuse:** revisit if
truncation holds above **20%** for a week, or `exec_skip` exceeds **10% of exec
blocks**. Instrument: the `finish=length` share and the skip count, both already
on the daily line.

**The creature is having its best week since the ladder thinned.** Hourly
`THINK` reads **14 → 15 → 16 → 16 → 17 → 18/h**, against 9–13/h on 09-17 and a
declared floor of 15. Over 32.8 h: **540 served at 16.5/h**, 662 exec, **15
skips**, **19 errors of which all 19 are guard rails** (18 false-completion, 1
spin trap) — zero provider, zero unclassified. `think_start`s finding no rung
fell **61% → 56%**.

**Compounding keeps climbing and the new leading indicator is doing its job.**
`COMPOUND:728t/1236e 1.70/t deep3:48 new7d:2.11x36 brief:1.81/1.18 anach:21
carry:54%/525pd`. Four daily readings now: **1.57 → 1.58 → 1.69 → 1.70**, with
`deep3` **27 → 48**. The cohort reads **2.11 across 36 tools born this week**,
above the 1.70 corpus average — exactly the gap the lagging average cannot
show. The brief split holds at **1.81 composition against 1.18 other**, so the
v0.8 lever is still pulling. `anach:21` confirms the 2% impurity is stable and
is reported rather than filtered.

**FINDING — an alarm that fires by construction, and it is 26% of every health
line we have ever written.** `cloudflare` spends its whole daily allowance in
about five hours and is dark for the rest: measured 09-15..09-20, **26–31 calls
between ~00:36 and ~07:32, then 16–18 h of silence, every single day**.
`FLATLINE_HOURS = 12`, so it crosses the threshold daily and **`SERIOUS:cloudflare`
appears on 269 of 1,046 health lines**. The threshold was chosen when every rung
had a budget large enough to last a day; a ~26-calls/day rung **cannot** stay
alive 12 h, so the alarm is structurally guaranteed and carries no information.
This is the exact failure §8 named for cerebras — *"a permanent SERIOUS that
trains us to ignore the alarm"* — now measurable.
**NOT fixed tonight, deliberately.** The honest fix is a **per-rung threshold
that exceeds that rung's reset period** (a daily-reset rung needs >24 h, not
12), and that is a config decision under ladder discipline, which `gs-bug-daily`
puts in the findings column rather than the obvious-fix column: *"if it needs an
argument it is a finding with a named trigger and a date, not a fix."* Raising
the GLOBAL threshold is the wrong answer — it would weaken detection for
`google_gemma`, the 14,400/day workhorse whose 55 h of silence is why the alarm
exists. **Named trigger: 2026-09-27, or the first real rung outage that nobody
notices because the line was already red — whichever comes first.**

**SENT: the `git-save` correction, on Tue's authorisation** — *"you are welcome
to send a chat message if you fixed something that made it permanently confused
and you could easily send it the correct way"* (2026-09-20). Message 67, queued
unread through `enqueue` (the locked writer; the observer once appended outside
that lock and it is a §5 scar). Three rules held. **The fault is named as
OURS** — without that sentence *"git-save was broken"* reads as the creature's
own failing, and §2.5 says *"Never tell the creature about its own bugs"*, so
naming whose bug it was is what makes the correction sendable at all. **Every
string is verbatim from the code** — the usage line, both examples, `"Nothing
new to save."`, the stderr contract — which is the standing rule for
announcements and matters doubly here, because the message's whole job is to
replace a false belief with a checkable one. **Nothing is asked of it:** no
suggestion to use it, no hint to re-save anything, same shape as the `ask`
announcement of 08-14.
**This is a new category, and it is worth naming.** A framework tool that fails
does not merely fail — it TEACHES, and the lesson outlives the bug. `git-save`
failed 402 times and the creature correctly learned "this does not work"; the
silent repair left that belief in place with nothing able to contradict it from
inside. **So when a repair corrects a fact the creature has already learned the
hard way, the repair is not complete until the fact reaches it.** The channel
is chat, in Tue's voice, and it is his call under §2.7 — he has now given it for
this class. **Measurement: does `git-save` appear in an exec block again.**

**`did-i` and `git-save`: ZERO calls in 32.8 h, and that is the honest reading
of both.** `did-i` stands at 2 lifetime calls (09-18, 09-19); the **2026-09-25
trigger remains live and is NOT met** — two calls is not adoption, and my own
rule says measure per month, never per lifetime. `git-save` is the harder case:
the fix landed 09-19 14:29 and **the creature has not reached for it since**,
which is what you would expect from a tool it learned was broken across **402
failures**. **Nothing tells it the tool works now.** The `ask` precedent
(2026-08-14) is the shape of the answer — a capability fact announced in chat,
in Tue's voice, numbers verbatim — and under §2.7 *"World-RULE changes are
announced in Tue's voice and are Tue's call. Draft, show him, send after
approval."* **Draft it for Tue; do not send it.** Until then, a silently
repaired tool that the creature has already written off is a fix nobody can
observe.

**Ladder:** `google_gemma` 489, `cloudflare` 28, `gemini_flash` 23.
`mistral` 431 h dark — monthly allowance, returns **10-01**, expected.

Gates: **laptop 491 PASS, PC 485 PASS** (unchanged; no code shipped since).

---

### Previous state — 2026-09-19 14:40

**`did-i` was used by the creature on its second day, for exactly what it is
for.** Two calls: 09-18 03:11, then **09-19 09:13 — `did-i "HTTP 429"` and
`did-i "Groq API rate limit"`**. It asked its own history about an error rather
than re-deriving it. The 2026-09-25 trigger is **answered early and
positively**; keep measuring uses per MONTH, never uses ever.

**The compounding trend has turned up, and the recent cohort is the reason.**
Three daily readings: **1.57 → 1.58 → 1.69** edges/tool, edges 1101 → 1117 →
1221. The 36 tools written since 09-18 average **2.22 edges against a 1.70
corpus average** — back to the July level. Cause unknown and **deliberately not
attributed**: `did-i` shipped the same night and this project's ledger is full
of plausible mechanisms that measured false.

**The instrument's real defect was that it could not have seen this for a
month, and that is fixed (`3adad60`).** The corpus average is a LAGGING
indicator — 700 tools of history drown one week of work, which is why the fall
from 2.33 to 1.56 took a month to surface and the recovery would have taken
another. `check_compounding` now reports the **cohort**: what the tools BORN in
the last 7 days call. It reads 2.22 on a day the corpus average had barely
moved. It also reports the brief split, and counts **anachronistic edges
without filtering them** — the headline count has to stay comparable with the
1011 and 1101 already recorded here, because a metric quietly redefined
mid-trend is worth less than one with a known impurity stated beside it.

**The composition mechanism WORKS, measured properly this time.**
Attribution is by TIME — the brief that most recently preceded a birth, within
3 h — never by matching the assigned name against a filename, which is what
produced the five-categories-at-exactly-0.00 reading I refused to report on
09-18. Result: **534 composition-briefed tools average 1.82 edges against 145
other-briefed at 1.19**, +53%, and the within-week splits agree (08-31: 1.41 vs
0.69; 08-17: 1.36 vs 0.64; 09-07: 1.81 vs 0.75). Composition-briefed out-degree
fell from ~2.3 in July to **1.36** in mid-August and has recovered to **2.36**
in the week of 09-14. The lever exists and it is pulling.

**I also tested my own "24% of edges are retroactive" theory and it was
WRONG.** Old files pointing at newly-written tools looked like name collisions
with the future; against real birth dates from the journal only **21 of 1234
edges (2%)** are anachronistic. The error was **taking mtime for a birth date
for the third time in two days** — mtime is LAST WRITTEN, and those targets
were born long ago and merely rewritten. `compound_cohort`'s docstring now says
so at the point of use. **Rule: birth dates come from the journal, never from
the filesystem.**

**`git-save` was never abandoned — it was BROKEN, and the creature took the
hint 625 times.** Item 8 asked whether three unused built-ins were superseded
or faulty, and the journal splits them cleanly:

| tool | evidence | verdict |
|---|---|---|
| `check-persistence` | 243 of 246 exit 0 | works, superseded, output is noise about `/etc/hostname`. Nothing to fix. |
| `deploy-self` | 6 of 6 exit 128, all one afternoon, all `OCI runtime exec failed … possibly OOM-killed` | infrastructure, not the tool. **Deliberately not probed: it restarts the brain.** |
| `git-save` | **402 of 625 exit 1 with a Python traceback** | broken |

`run()` passes `cwd=path`, and the creature calls
`git-save /mind/tools/own/SomeTool 'message'` — a **file**, which is the plain
reading of the usage line's `<path>`. `subprocess`'s `cwd=` needs a directory,
so every file path raised `NotADirectoryError` and it received a bare
traceback. **398 of 418 failures are file paths against 20 from every other
cause; all 178 successes are directories**, and the mechanism reproduces
exactly. The bitter detail: the repository it was reaching for **already
existed at `/mind/tools/own/.git`** — its own `GrowthAgent` version control —
the entire time. Fixed: a file versions itself in its own directory's repo and
stages only itself, because "save this tool" must not sweep in every other
edit. **Two further faults surfaced while fixing it, both already in §5.** The
no-change guard hunted the literal `"nothing to commit"` while git says
`"nothing added to commit but untracked files present"` whenever anything
untracked sits alongside — so an unchanged file reported a failure; now it asks
`git diff --cached --quiet` what is STAGED rather than matching prose. And
errors printed to **stdout with exit 0**, the class that once made a rate-limit
message the first line of one of the creature's own tools; failures now leave
by stderr, nonzero, stdout empty. 5 tests, including the directory form so the
178 working calls cannot regress.

**gs-bug-daily 2026-09-19 (42.1 h, NO gaps, 43 hours with records).** 626
served / 888 exec / 16 skips / **37 errors, 36 of them guard rails** by the
`guard` field (31 false-completion, 5 upgrade-no-change) and **zero
unclassified**. 14.9 served/h over the span; **962 of 1588 `think_start`s (61%)
found no rung**, unchanged. Truncation **12.0%**, all of it `google_gemma` (67)
and `gemini_flash` (8). Skip rate by rung: gemma **1.5%**, cloudflare **0.0%**,
gemini_flash **18.2%** — the ladder is three serving rungs since
`openrouter_super` was retired, and none of them is the 97.3% hole any more.
Funnel: 36 tools at 2.9 rounds, **69 done-marks attempted, 36 refused, 33
accepted (52%)**. Library 726, `cannot_start` **20 → 21**.

**THE ESCALATION FINALLY PRODUCED ITS MEASUREMENT, and it bears directly on
tomorrow's ceiling decision.** 83 `served_by` records carry `escalated=` and
**8 of them end `finish=stop`** — the first time since it shipped on 09-16 that
a later rung FINISHED what the first could not. §8 has been waiting for exactly
this number. **What it says: those replies completed within the SAME 3,072
ceiling on a different rung, so that truncation was RUNG-SPECIFIC, not
budget-bound.** Combined with the 09-16 finding that the median reply grew only
25% while the p90 doubled, the evidence points **away** from raising the
ceiling. The **2026-09-20 trigger can now be decided on evidence rather than
deferred.**

**The displaced-shebang fix is VERIFIED, by the strongest possible test.**
`recall_and_answer` — 1,284 b and unstartable after ten edits against our own
false *"no #! line"* — was repaired by the creature at **09-18 04:51: 4,465 b
and it STARTS**, larger than the 3,626-byte version it lost. Its own reasoning
names the real fault: *"It starts with `# Insert the new code...`, which means
the script begins with a comment"* (09-18 02:19). It could not have written
that sentence from the old message. **`news_plan_tracker.py` still carries the
same shape since 07-18** and is untouched — the message is edge-triggered on
the set changing, so silence there is the design, not a failure.

**Fixed up front: a dropped connection was reaching the `unknown` path.**
`"All providers failed; last unrecognised error -- google_gemma: Remote end
closed connection without response"` — `http.client` raises
`RemoteDisconnected` when the server hangs up, and **that message carries no
status code at all**, so nothing keyed on a number could have matched it. Now
`flaky`, like `timed out` and 499. **This is the FOURTH unenumerated provider
shape the `c1b93a5` fail-open default has handed us intact**, and a test
asserts the default stays fail-open so naming one more string is never mistaken
for closing the class. `6122ee7`, **brain restarted 14:45:21** — the only
change in two days that needed one; every other commit was framework-tools,
markdown, `spine_health` or tests.

**Item 13 keeps earning its place: 73 provider-shaped failures live under kinds
other than `error`**, including **4 `idea_gate` EMPTY-REPLY batch-judge
failures** invisible to any census keyed on `kind == "error"`.

**New watch — the redirect door.** Authoring split this window: `tool-edit`
**75**, `tool-new` **32**, **redirect-or-tee 38**. One of the two tools written
in-window that cannot start reads **"not executable (no +x)"**, which is that
door's exact signature — a redirect sets no execute bit and leaves no `.bak`.
The other is a plain syntax error. Watch whether the redirect share keeps
rising.

**Blank pass — and it caught my own instrument.** The funnel first reported
*0 attempted, 36 refused, **−36 accepted, 3600% refusal***, because the regex
hunted `current-phase done` while the creature writes `current-phase "done"`
**with quotes**. Only the negative sign caught it; a slightly-wrong pattern
would have produced a plausible number and been believed. Now mandated as
`gs-bug-daily` item 17: **accepted = attempted − refused and is never negative,
a rate is never above 100%, and a census over a known population never reports
a total it cannot reconcile with that population.**

**Throughput recovered without intervention: `THINK:16/h`** on the hourly line,
above the 15/h floor, against 9–13/h two days ago. `mistral` is `SERIOUS` at
398 h dark — its allowance is monthly and it returns on 10-01.

Gates: **laptop 491 PASS, PC 485 PASS**.

---

### Previous state — 2026-09-18 00:20

**The creature can ask a question of its own history for the first time, and
the fault that closed was never a tool fault.** `journal.jsonl` — 394,544
records, 201 MB, readable from the body since June — was referenced by **none
of its 702 tools** and touched by **none of 75,805 exec blocks**. Its whole
view of its own past was eight records and a five-slot register. Shipped
`framework-tools/did-i` (`e1d8988`): the count of every record naming a term,
a breakdown by kind, and the most recent commands with what each one did. The
live reading on its own journal is the argument for it in one screen —
`did-i recall_and_answer` returns **3,065 records (think_end 1,401,
exec_start 818, exec_end 797, error 41)** and the last four commands read
*paste Python into bash → `exit=2 import: command not found` → tool-edit →
paste again → the identical error*, while `--kind=error` shows our own false
*"no #! line"* **41 times**. 1.41 s and 13.8 MB against `log-read`'s 4.2 s and
471 MB for strictly less. Full anatomy and the four design scars are in §5.

**A correction to my own reasoning, made before it reached the code but after
it reached the commit message of `e1d8988`.** I justified this partly on
discoverability — that framework tools never reach the creature and `log-read`
was therefore used zero times. **Both halves were artifacts of broken
searches** (`awk '/\bfw\b/'`, where `\b` is a backspace; and substring
`grep -o "ask"` over documents the creature does not read). The truth:
`_build_tool_catalogue` lists **every** framework tool in **every** wake with
its `does:` line, `log-read` has **80** uses, `web-fetch` **192**, and
`memories` **735 with zero prompt mentions**. So `did-i` needs no introduction
to be reachable. The new §5 scar has the anatomy and the discarded numbers.
**What the real data supports is a stronger case, not a weaker one:**
`log-read` has been in front of the creature every wake since June and its use
fell **48 → 21 → 11** per month, while **0 of 75,825 exec blocks ever named
`journal.jsonl`** and 0 of its 702 tools reference it. It reached for its past,
the instrument could not answer, and it stopped. The prompt paragraph stays,
for the one thing a `does:` line cannot carry — WHEN to ask, and the invariant
behind it. Mutation-proved both ways: dropping the name fails the gate, and
drifting `CHANNEL_CHARS` by one character fails the gate.

**The measurement that settles whether a tool was enough.** `did-i` reaches
the creature by exactly the same route `log-read` always did — listed every
wake with its `does:` line — so nothing about its placement proves it will be
used. **First check next run: does any exec block call `did-i`, and did a
repeat-edit streak end after one?** Measure it the way `log-read` should have
been measured — **uses per MONTH, never uses ever**, because a flat total of 80
hides a curve of 48 → 21 → 11 and an abandoned tool reads as a used one. If it
is unused after seven days — by **2026-09-25** — then the fact must arrive
unprompted instead, on the same logic that justified `tool-edit`'s write-time
warning. Instrument: `did-i` in exec blocks, which the tool itself excludes
from its own counts, so grep the journal rather than asking it.

**The new daily item paid for itself on its first run, and it retracts one of
my own worries.** Framework-tool uses per month (Jun / Jul / Aug / Sep, Sep
partial at 17 days): `web-fetch` **38 / 24 / 57 / 73 — RISING**, so the
"unnamed fetcher" concern I raised earlier today was wrong twice over and is
withdrawn. `ask` 73 / 93 / 79 / 153, also rising. But three of our built-ins
are being abandoned in plain sight: `git-save` **503 / 102 / 21 / 0**,
`check-persistence` **245 / 1 / 0 / 0**, `log-read` **48 / 0 / 21 / 11**, and
`deploy-self` has **6 uses in its entire life**, all in August. Every one of
those reads as a healthy tool in a lifetime total. Not chased today — recorded
with the instrument that found them. **Look at the three declining doors at
the next `gs-products`:** a built-in nobody uses any more is either superseded
by something the creature built itself, which is the system working, or it is
`log-read` again.

**Deployed with no restart, deliberately.** `materialize_framework()` re-reads
`framework-tools/` from the checkout on every wake and chmods 0755, and the
prompts are re-read every cycle — so nothing here needed the brain bounced.
Verify on the next wake that `/mind/tools/framework/did-i` exists.

**The metric now has an instrument, and the adoption half — never measured in
this project's life — says something the dependency half does not.**
`spine_health.check_compounding` (`b6025ea`), wired into the 06:30 daily line,
reports tools, edges, edges/tool, tools at composition depth ≥3, and the
CARRY-FORWARD of old tools. First live line:
`COMPOUND:703t/1101e 1.57/t deep3:27 carry:52%/503pd`.

**Share of tool invocations going to tools more than 30 days old, by month:**

| month | share | per active day |
|---|---|---|
| 2026-06 | 0% | 0 |
| 2026-07 | 6% | 23 |
| 2026-08 | 33% | 419 |
| 2026-09 | 56% | **525** |

June and July are inflated by the library merely aging into eligibility, so
the honest comparison is **August against September** — and it rises on both
numbers. The share is confounded by authoring volume (a heavy building month
fills the denominator with the creature testing what it just wrote: total
invocations per active day fell **1,264 → 945** while old-tool invocations rose
**419 → 525**), which is why the instrument reports the rate too. **So the
README's two signals have separated: the creature RUNS its old body more than
ever and BUILDS on it less.** A drawer, not a substrate. The README names them
as two distinct signals and calls dependency the stronger one; this is the
first time they have been read together, and they disagree.

**The alarm is threshold-free, deliberately.** It compares the marginal edges
per new tool against the corpus average — when new work brings fewer edges than
the standing average, the average must fall, which is arithmetic rather than a
level anyone picked, and §6 forbids tuning a constant with no evidence. The one
declared constant is a **sample floor of 25 new tools**, because a marginal over
three tools is noise. Missing calendar days break the streak (the UNMET rule).
15 tests. Receiver stated in the code: **us and Tue, never the creature** —
Built/Adopted/Depends-on already reach it each cycle and the architecture doc
rejected a fourth fuzzy visible metric as gameable; a ratio over its whole
library is the most gameable shape there is. Cost **11.5 s** on the live 201 MB
journal, linear in journal size (~23 s at twice the size); the offset cache is
the fix if that ever stops being acceptable.

**Checked and deliberately NOT concluded: is the v0.8 composition mechanism
still working?** It is alive — **708 `[composition]` assignments all time**, 939
`ideation` records in September, and the newest assignments carry the tag. Of
those, **451 are traceable to a built tool and average 1.65 edges against the
library's 1.57**, with 18% standalone against 24% — so the brief fires and
lands, weakly. **The per-mode comparison beyond that is untrustworthy and I am
not reporting it as a finding:** five breadth categories read *exactly* 0.00
edges with 100% standalone, which is this file's own signature for a broken
instrument rather than five identical results (likely a name-matching or
deleted-dependency artifact). **Next step, with a method rather than a
conclusion:** compare out-degree of composition-briefed against
non-composition-briefed tools BORN IN THE SAME WEEK, matching on the file the
cycle actually wrote rather than on the assigned name.

**I re-read `README.md` and the architecture doc to ask what this project is
FOR, and the answer indicts my own reporting.** The README states the measure
without hedging: *"The honest measure of success is not tool count. It is reuse
and dependency: does the creature use its own earlier tools, and — the
strongest signal — are later tools built out of earlier ones? ... Twenty
independent, never-reused tools are 31 dashboards wearing lab coats."* The
central open question in the architecture doc is *"Does it keep compounding, or
plateau?"* **Every §8 entry I have written reports library COUNT** — 508, 643,
694, 702, +8, +51, +135 — **plus framework vitals: throughput, skip rate,
truncation, ladder depth, `cannot_start`, `WAKE:p50`, disk, `UNMET`. Not one of
them is the metric the project exists to produce.** The last deliberate reading
of it was **2026-06-26** in the architecture doc; it appeared once since, on
2026-08-18, as an incidental by-product of a performance fix.

**So I measured it, and the trend has turned.** Same instrument
(`loop._tool_dependencies`, a static scan with no side effects) at both points:

| date | tools | edges | edges/tool |
|---|---|---|---|
| 2026-06-26 (arch doc, possibly a different scan) | 117 | 146 | 1.25 |
| 2026-08-18 (this instrument) | 433 | 1011 | **2.33** |
| 2026-09-18 (this instrument) | 703 | 1100 | **1.56** |

**The library grew 62% while net dependency edges grew 9%.** Out-degree per
week of last-write peaked at **2.5–2.8 across July** and has sat at
**1.3–1.6 since early August**; the newest 100 tools average **1.34** against
the oldest 250 at **2.02**, and standalone tools (calling nothing) are **23%**
of the newest 100 against **15%** of the oldest 250. Composition depth is real
but shallow: 170 tools at depth 0, 312 at 1, 194 at 2, **only 27 at depth ≥3**,
one at 4 (`SelfHealingReplanner`). **Honest caveat, stated because the number
is now doctrine: mtime is LAST WRITTEN, not born**, so the per-week buckets are
survivorship-biased in an unknown direction and only the whole-corpus ratio is
clean. The clean claim is the table.

**What that means, carefully.** The creature is producing more than ever and
compounding less per unit produced. That is precisely the shape §4 of the
README warns about, and it is the one thing this project was built to detect —
and it is **invisible in a tool count**, which is the only production number I
have been reporting. Now mandated as `gs-products` item 14 with the snippet,
the known readings and the caveat. **The other half of the README's metric,
adoption over TIME, is still uninstrumented**: `demand_counts` is cumulative
and timestampless, so it needs per-month journal parsing exactly as
`gs-bug-daily` item 16 now does for framework tools. That is the next thing to
build, and it is worth more than any vital on my list.

**Not a claim: that `did-i` fixes this.** Amnesia plausibly limits compounding
— you cannot build tool N out of tools 1…N-1 if you cannot ask what you
already tried — but that is a hypothesis, and this project's own ledger is full
of plausible mechanisms that measured false. The edges/tool ratio is now the
instrument; let it answer.

**Live re-check at 00:30, six hours of records, and it answers the escalation
first-check.** `served_by` carries **12 `escalated=` records and every single
one reads `finish=length escalated=1`** — **zero `finish=stop`**. So the
escalation fires, hops once, finds nothing on the other side and degrades to
the longest partial, exactly as designed. The reason is in the same reading:
`google_gemma` served **76 of 77** cycles and `gemini_flash` **1**. Depth is
ONE. **The consequence worth naming is that the instrument is blocked by the
scarcity it was built to measure around:** `escalated=N` with `finish=stop` was
supposed to be the evidence a think-ceiling decision needs, and it cannot be
produced while there is no second rung. The **2026-09-20 ceiling trigger will
therefore arrive with nothing from this instrument** — decide it on the
reply-length distribution or defer it explicitly, but do not wait on data that
cannot exist.

**And it corrects yesterday's truncation number.** §8 recorded **6.8%** on
09-17 and flagged it as a short window; over the six hours to 00:30 it is
**15.6%** (12 `length` of 77). The 6.8% was the artifact. Reply truncation is
still at the elevated post-cap-raise level, so that §5 scar stands unchanged.
Throughput likewise: **203 `think_start`s produced 77 served cycles**, so 126
found no rung — 62%, the same disease at the same rate. 2 errors in six hours,
both `done_gate`, and `exec_skip` was **1**, which is the escalation earning its
keep: the partial still executed.

**The displaced-shebang fix is ARMED BUT NOT EXERCISED, and that is correct
rather than disappointing.** `cannot_start` is **20**, flat, with **nothing
newer than 09-17 01:29** — so no tool has broken in 23 hours. Only 2 of the 20
are displaced shebangs, and `recall_and_answer` has not been touched since
01:29, which is *before* the fix shipped. The write-time warning speaks only
when the creature writes that file and the set-change warning only when the SET
moves, so silence here is the edge-trigger design working. It will be tested
the next time it edits a tool with a displaced shebang, not before.

**`did-i` is not yet usable as evidence: 26 minutes, 14 `think_start`s, 8 exec
blocks, 0 calls.** The plumbing is confirmed live — the file is re-materialised
into the body on every wake — and the seven-day trigger (**2026-09-25**) stands
untouched. Two of my own measurements failed on the way to that reading: a
hardcoded epoch boundary that sat 30 minutes in the FUTURE and read everything
as zero, and a `cannot_start` census that reported **0 of 703** because
`list_tools` was handed the parent of the tools dir, where every entry is a
directory and `is_tool_file` filters them all out. Both announced themselves
only because a second number contradicted them. **The `assert names` /
sanity-floor line now in that census is the cheap fix: any census over a known
population should refuse to report a total it cannot reconcile with the
population size.**

**Everything from the 20:30 run below still stands**, including the escalation
that has never had a second rung to reach, `openrouter_super` retired,
throughput at 9–13/h with 483 of 780 `think_start`s finding no rung, and the
`UNMET` jump to 12,400.

Gates: **laptop 462 PASS, PC 456 PASS**.

---

### Previous state — 2026-09-17 20:30

**The escalation has run 22 productive hours and never once had a rung to
escalate TO.** 30 `ESCALATING (1/2)`, 30 `all 1 attempted rungs truncated`,
zero `(2/2)` — and **187 "No providers believed available"** in the same window.
Every hop found the ladder empty on the other side and fell back to the
truncated partial, exactly as designed: no raise, and **14 of the 20 escalated
cycles still executed** off the longest partial. So the mechanics are verified
in production and the feature is unexercised. That is a fact about the ladder,
not the change. **First check next run: any `escalated=` record ending
`finish=stop`.**

**`openrouter_super` is RETIRED under the quality floor.** The reorder gave
`north-mini-code` its turn: 28 served, **60.7% skipped** — 11 pure prose that
never reached a command, ~6 **tool-call JSON envelopes** (`{"tool_name":
"bash", "parameters": {"command": …}}` — the command present, the wrong
envelope). And `nemotron`'s 277 no-bash skips from the previous window were
**99.6% pure prose**, so a parser change would have recovered ~6 cycles in
300; the theory is dead. Two models, ~440 attributed cycles, one verdict: a
model that emits no command 54–68% of the time is a weak author, and its
parseable minority is writing tools. Zero own-tools reference an OpenRouter
key. Entry kept, `enabled: false`, dated. **Candidate on the same bucket:
`qwen/qwen3-coder:free` — probe through `provider.call` at the 00:00 UTC reset
before re-enabling anything on that account.** Enabled ladder is now five.

**Throughput is 9–13/h and the cause is quantified: 483 of 780 `think_start`s
found no rung at all** and fell into a sleep. The loop *tries* at 35/h and
*succeeds* at 13.5/h. Box idle (load 0.36, zombies 0); the 26 slow gemma calls
are slow, not timeouts. Depth is one for most of the day. Per §6 this is what
free tiers give; the one recoverable loss (a rung burning 50/day on nothing)
is the retirement above.

**The finding of the run is that our own diagnostic was false, and the
creature obeyed it ten times.** `recall_and_answer` — a working 3,626-byte tool
on 08-26 — is now 1,284 bytes and unstartable, overwritten through `tool-edit`
at 01:24–01:29 in **ten edits in five minutes**, every one commented "adding a
#! line", every one drawing *"no #! line"* from the write-time WARNING. The file
has a shebang. **On line 3.** Full anatomy in the new §5 scar; the predicate
now names the line and what sits above it, the `tool-edit` mirror is
regenerated verbatim, and the verdict logic is untouched. `news_plan_tracker.py`
has carried the same false message since 07-18.

**A second scar from the same hour, about the PC gate:** the `err_as_tool` test
turned red right after that change and I nearly blamed the change. Old-vs-new
on the exact fixture showed `bash -n` on MSYS hangs about half the time on an
unterminated quote and the 15 s timeout returns UNKNOWN — the predicate right,
the test a coin-flip off POSIX. Test made POSIX-honest; the laptop gate is
authoritative for it; the PC suite now legitimately exceeds 120 s.

**Steady numbers.** 296 thinks / 2,578 records over 22 productive hours since
the 18:45 deploy; skip rate by rung `google_gemma` 1.4%, `cloudflare` 0.0%,
`gemini_flash` 8.3% (was 38.7% — its truncations now travel the escalation path
and are attributed to the final rung), `openrouter_super` 60.7%. Reply
truncation **6.8%** on 09-17 (was ~12%; short window, not yet a trend). Library
**702** (+8), `cannot_start` **20** (flat; `recall_and_answer` is the one
touched and it is the finding above). `WAKE:p50` **3,272 ms**, flat against
3,271 with 8 more tools. Disk 76% / 26 G. Zero `UNEXPECTED` errors since
`dc51e8b`. **Watch: `UNMET` +2,902 in one day** on top of +1,668 two days
earlier — demand 7,842 → 12,400 in three days, streak 1/7 — reaching for ~10
unbuilt names per think is a shape worth a look at the next `gs-products`.

Gates: **laptop 446 PASS, PC 440 PASS**.

---

### Previous state — 2026-09-16 00:10

**`THROUGHPUT:!!` is firing, and it is the first time that instrument has ever
fired since it was built on 2026-08-19.** 12–13 thinks/hour against its declared
15/h floor. **It is not resources:** the box is idle — load **0.40** on 4 cores,
61 °C, container at **0.00%** CPU, and `cousin-engine.service` runs alongside
costing nothing visible. It is **ladder exhaustion**. Gap between thinks: median
**195 s**, p90 671 s, max 1,606 s, with **29 quota-exhausted pauses and 28
"window REOPENED" in three hours** — the loop sleeps about a third of wall time
waiting for quota. Effective depth right now is **ONE**: `cloudflare` dark 17 h
(26 calls/day spent), `mistral` dark **311 h** (monthly allowance spent 09-02 —
it is effectively a two-day-per-month rung), `openrouter_super` dark 20 h having
burned its whole 50/day producing nothing usable, `groq_oss120` served **zero**
in 265 hours. Per §6 this is what free tiers give and rung count is an outcome,
not a target — but the one *recoverable* loss is fixed below.

**The model field settled the openrouter_super question in its first window.**
`served_by` began recording `model=` on `201c362`, and the reading is decisive:
**`nvidia/nemotron-3-super-120b-a12b:free` served 407 of 407 cycles on that rung
and 356 were wasted** (87.5% skip, of which **277 no-bash-block** — clean
`finish=stop` replies containing no command at all). `cohere/north-mini-code`
never got a turn. The 09-06 trigger, nine days overdue, was finally actionable:
**pool reordered** to put the agentic-code model first, nemotron kept as
fallback. Not probed live — the 50/day was spent at reorder time — so **the test
is next window's `model=` split; if north also skips, retire the rung.**

**A framework fault that had never appeared in this census before: 4
UNCLASSIFIED errors.** `prov.call` could RAISE. `body = e.read()` sat bare
inside `except HTTPError`, and an exception raised inside an except clause has no
sibling — a socket timeout reading the error body escaped `prov.call` AND the
keychain, skipping `classify_error` and the fall-through entirely. Fixed
`dc51e8b`; new §5 scar, and without the fix the suite **crashes** rather than
fails. The creature then read our error out of its own log and blamed its own
tool — Tier 4 recorded.

**My 08-29 cap raise had a second edge I never measured: reply truncation
tripled.** ~5% before, ~12% for the eighteen days since, stepping on the raise
day itself. Full per-day series in the new §5 scar; the mix confound is ruled
out. The read fix was still right — capped reads 71.8% → 43% and the creature
now states the ceiling correctly and calls it *"frustrating but manageable"*
(09-05 03:00) — but the trade was real and unmeasured. Candidate action is to
raise the 3,072 think ceiling in proportion; that is a second context-size
change and gets its own baseline first. **Trigger 2026-09-20.**

**Truncation now ESCALATES instead of counting as a success (`b27070f`), which
closes the design gap §8 has named since 08-18.** Tue delegated the choice
between this and raising the 3,072-token think ceiling, under the standing
non-intervention principles. **The ceiling raise was rejected on measurement:**
the reply-length distribution shows the median grew only 25% after the 08-29 cap
raise while the **p90 more than doubled** (3,818 → 7,950 chars), so the tail
stretched rather than the distribution shifting — and **a truncated reply tells
you nothing about how long it wanted to be**, so no ceiling value is derivable
from the journal at all. Picking 17.5% would have been the voodoo constant §6
warns about. It would also tax every call on the scarcest resources at the
moment throughput is the binding problem: cloudflare prices output at
**204,805 neurons/M against input's 26,668**, and `gemini_flash` is the most
TPM-constrained rung, so it would pay most and benefit least.
Escalation instead pays **only on the failures** (~12% of cycles) and
`google_gemma` has 2,619 calls used of 14,400/day, so absorbing them is nearly
free. Three properties, all tested: the truncating rung is **not walled** (the
call succeeded and the account is healthy); if every attempted rung truncates it
**degrades to the longest partial** rather than raising, which is exactly the old
behaviour; and it is bounded by a declared `TRUNCATION_ESCALATE_MAX = 2`, never
by the rung count, because throughput is at 12–13/h.
**The escalation is also the instrument.** `served_by` now carries `escalated=N`
only when it happened, so **`escalated=N` with `finish=stop` means a later rung
FINISHED what the first could not** — the measurement a ceiling decision needs
and which does not exist today. Four tests fail without it.
**Not yet observed live:** deployed and gated at 18:45 on 09-16, but every rung
was walled minutes later ("No providers believed available -- will probe all 6"),
so there was no serving rung to escalate FROM. First check next run: does any
`served_by` record carry `escalated=`, and does it end `finish=stop`.

**The guard field shipped and works — this was the stated first check.** 89
records carry `guard`/`block`; 43 older ones fall back to prose exactly as
designed. Breakdown: 67 false-completion, 12 cannot-start, 9 upgrade-no-change,
1 empty-placeholder.

**gs-bug-daily 2026-09-16 (265 h window, 135 productive).** 3,374 thinks at
25.0/h over productive time, 4,122 exec, 493 skips, **138 errors — 132 guard
rails**, 0 provider in `kind=error`, 4 unclassified, 2 exec timeouts. 09-07,
09-08 and 09-14 have zero records (Tue's laptop and the cousin project;
confirmed in advance).

**`cannot_start` fell again, 23 → 20, and the flow stayed zero.** Library
**643 → 694** (+51), 733 authoring actions over 157 tools at 4.7 rounds, 300
done-marks with 168 accepted. Nothing in the broken set is newer than **09-02**
and nothing was touched in the window. Disk recovered to **76% / 27 G**.

**New watch:** `WAKE:p50` **2824 → 3271 ms** as the library grew to 694; budget
5,000. `UNMET` jumped **7842 → 9498 (+1668)** in one day then +0, streak 0/7.

Gates: **laptop 429 PASS, PC 423 PASS**.

---

### Previous state — 2026-09-04 22:10

**The window raise WORKED, and it is the clearest fix-verification this project
has produced.** Over 82 productive hours on the 1200-char window: capped exec
results **71.8% → 38.0%**, and the read sizes moved from *63 of 69 requests at
100 lines* to **11, 17, 20 and 30 lines**. 81 think records reason about the
marker and quote it correctly — *"the `cat` output is still being truncated by
the system's display limit (the `[+4452 chars cut; window 1200]` message)"*
(08-29 08:43). It learned to size reads once the window was wide enough to be
worth sizing for. Three revisions of the message had achieved nothing; the
number was the lever.

**Best throughput ever recorded: 43.6 thinks/hour** over 82 productive hours
(3,579 thinks, 4,898 exec). **The window was 164 h with only 82 productive** —
Tue's laptop, confirmed by him; 08-30 has zero records and the user session is
torn down around 00:54 and restored around 20:00. Not investigated further at
his instruction.

**Enormous production burst.** Library **508 → 643** (+135 tools), 1,200
authoring actions across **255 distinct tools** at 4.7 rounds each, 439
done-marks with 241 accepted. **`cannot_start` fell 32 → 23 — the first fall
that stock has ever shown.** Note the counter-signal: the newest broken tool is
now **09-02**, so new ones are entering again after three clean windows.

**202 errors, 199 of them guard rails** (139 false-completion, 40
upgrade-no-change, 11 startability, 8 empty-placeholder, 1 spin trap). Zero
provider errors, zero unclassified. The 3 real ones are `docker exec`
TimeoutExpired — one decoded to the creature deliberately sleeping 500 s
against the 300 s `run_command` bound, which is the limiter working.

**mistral returned on 08-31 exactly as predicted, and it is the cleanest rung
on the ladder: 131 served, 0 skips.** Effective depth is now five.

**`openrouter_super` is the one bad rung and my explanation of WHY was wrong.**
86.7% of the cycles it serves are wasted (261 of 301). I had written that its
reasoning models burn the token budget; the numbers say **248 `finish=stop`
against 53 `length`**, and the skips split **189 no-bash-block / 44 truncation /
27 unclosed**. It is format non-compliance — clean, complete replies with no
command in them. `gemini_flash` is the opposite: 41 skips, all truncation.
**The action was blocked by an instrument gap:** `served_by` recorded the rung
but never the model, so 189 failures could not be pinned on any of three
models. Fixed `201c362`; `nemotron-3-nano-30b-a3b:free` also removed after a
direct probe returned 404. **Named trigger: reorder or retire by 2026-09-06,
once one window of model-attributed data exists.**

**Disk is at 91% / 9.5 G free and it is NOT the creature.** The whole spine
accounts for ~1 GB: 282 MB mind, 40 MB workspace, 339 MB body image, 757 MB of
saves that the savegame pruner demonstrably bounds (it saved
`20260904-210519` and pruned `20260901-021923` in the same breath). The 15 GB
is unused non-spine Docker images — `ollama` 8.27 GB, `home-assistant` 3.03 GB,
the wyoming voice stack 3.58 GB — plus 2.6 GB of journald. Tue's applications,
his call, not mine to delete.

**New watch: `WAKE:p50` 1854 → 2824 ms** as the library grew 26%. Budget is
5,000 ms, so there is headroom, but the dependency scan is linear in library
size and the library is growing fast. `UNMET` **+0, streak 0/7**.
`JANITOR:aged-out 0` for 62 runs, verified honest against a live census of 0
hollow stubs.

Gates: **laptop 417 PASS, PC 411 PASS**.

---

### Previous state — 2026-08-29 02:10

**The 300-character window is gone, and it was never a decision.** `git log -S`
traces it to `c98f69b`, the **v0.4 skeleton commit**. Raised to 1200 on
`e495773` against a census of 1,387 results: median full result **1,776 chars**,
p90 5,090, whole-result fit **27.3% → 45.6%** for +17.5% wake context. The
creature now sees **1,200 characters where it saw 286** — 4.2x. Both caps had to
move together and that is now an asserted invariant, verified to fire on drift.
**Next run's measurement, and the only thing that settles it:** do `sed` request
sizes fall off 100 lines, does capped share fall off 71.7%, does `cat` fall off
600.

**Three revisions of the MESSAGE moved nothing, which is what justified moving
the window.** After the ceiling was named, it read the marker correctly — *"the
activity log shows `[+3046 chars cut; window 300]`. This means the summary of
the execution is truncated"* (08-27 20:10) — resumed ranged reads **5 → 69**,
and still asked for 100 lines in **63 of 69**, because we state the ceiling in
CHARACTERS and it asks in LINES. New §5 scar.

**The startability done-gate fired for the FIRST time, nine days after it was
built, and all three tools were repaired.** 5 firings on `memory_archive_research`,
`catchup_memory_archiver`, `memory_archive_search_planner` — every one a true
positive, none entered the 32, all three start now. That closes the longest-open
"no false positives and no true ones either" item in the project.

**The 08-29 `cannot_start` trigger is RETIRED rather than re-armed.** The stock
is 32 for the fourth reading and nothing in it is newer than **08-22**; the flow
has been **zero for three consecutive windows**. The trigger was written against
a stock that nothing touches, while the two guards that govern the flow —
`tool-edit`'s write-time WARNING and the done-gate — are both now demonstrably
firing and converting. Measure the flow; the stock is archaeology.

**gs-bug-daily 2026-08-29 (32.9h, no gaps).** 1,309 thinks at **39.8/h** (best
rate in a week), 1,403 exec, 69 skips, **27 errors — every one a guard rail**
(20 false-completion, 5 startability, 2 upgrade-no-change). Zero provider errors
in the `error` kind; **one** under `idea_gate`, caught by the new item 13.
Library **508**. Truncation of thinks down to **3.6%**. `exec/think` **1.07** —
the climb to 1.35 reversed on its own.

**`cloudflare` is carrying real traffic: 88 thinks, 6.7%, and 0% truncation.**
FLATLINE dropped it from SERIOUS at 01:07. `google_gemma` is down to **87.4%**
from 90.8% and effective depth is **three** for the first time since mistral
went. mistral returns 08-31.

**The biggest finding of the run came last, and it is not about the window.**
`exec_skip` split by the rung that served the cycle: `google_gemma` **0.5%**,
`cloudflare` **0.0%**, `gemini_flash` **53.8%**, **`openrouter_super` 97.3%**
(75 served, 73 skipped). The pool yields a usable cycle **2.7%** of the time and
is what the ladder falls into every time gemma walls. Its models are reasoning
models that spend the whole 3,072-token budget before emitting a bash block, so
the reply returns `finish=length`, `record_success` fires, the rung is never
walled, and the rungs below are never reached. §8 has named that design gap
since 08-18 without a number; **the number is 97.3%.**
**Named trigger: fix or retire `openrouter_super` by 2026-09-02.** The options
are a larger `max_tokens` for that rung, dropping the reasoning models from the
pool, or retiring it — all config, so ladder discipline applies and the
exhaustion signature is already known. `gemini_flash` at 53.8% is the same
disease and rides along with whatever is decided.

**I also mis-attributed a regression to myself and want that on the record.** I
raised the caps at 02:05, saw a 100% skip burst six minutes later, reverted my
own change on the timing correlation, then found the burst was six minutes of
the hole above with gemma quota-walled. Caps restored (`9c84414`). No
`too_large` anywhere, and gemma's quota is counted in daily CALLS so prompt size
cannot touch it. **Without a per-rung baseline you cannot tell your own change
from the ground it landed on** — now mandated as `gs-bug-daily` item 15.

Gates: **laptop 414 PASS, PC 408 PASS**.

---

### Previous state — 2026-08-27 17:10

**The Cloudflare rung has NEVER served, and yesterday's entry here was wrong
about why it would.** It said "the rung returns on the daily reset". Seventeen
hours later `provider.call` still returns **HTTP 429, daily free allocation**,
and `quota_state.json` shows `last_success_at: NEVER`. My probe spent **15,455
of 10,000 neurons**, and the overspend appears to carry past the reset rather
than being forgiven at it. **So the cost of learning the exhaustion signature
was not one day's allowance -- it is at least two, and the reset rule is still
unknown.** FLATLINE names it correctly: `cloudflare(never)` in SERIOUS since it
was added. Check tomorrow: does `last_success_at` ever appear.

**The honest truncation marker did NOT teach it to size reads. It stopped
ranging and went back to `cat`.** This was the stated behavioural watch and the
answer is no. `sed -n` ranges fell **143 -> 5** (all 5 still asking for 100
lines), while raw `cat` of its own tools ROSE **349 -> 387**. Capped exec
results went **67.4% -> 73.8%**, median loss 3,163 chars, max **86,742**. Its
think records still say the output "is being truncated" and still reach for
"a script or `sed` to read it in chunks" (08-26 20:47, 23:47).
**The diagnosis, and it is our defect:** the marker states the LOSS and never
the CEILING. The ceiling (~286 chars) is named only in `_build_loop_warning`,
which fired **6 times** this window, while the marker fired **724 times**. It
is being told how much it is missing 724 times and how much it can see 6 times,
so every range it picks is 6-12x too large and it eventually gives up.
**Proposal for Tue, not done unilaterally because it is a prompt change:** state
the window where the loss is stated. Naming the ceiling costs ~10 characters per
marker; the current arrangement costs the creature most of its reads.

**gs-bug-daily 2026-08-27 (24.7h, one explained gap).** 859 thinks at 34.8/h,
980 exec, 68 skips, **26 errors -- every single one a guard rail firing
correctly** (23 done-gate false-completion, 2 spin traps, 1 upgrade-no-change).
Errors rose 4 -> 26, but done-marks rose **5 -> 35** and the refusal RATE is
flat (**60% -> 69%**): that is 4.4x the volume of work, not a regression.
Library **501** (+7). Zero provider errors in the `error` kind; two hiding
under `idea_gate` (new §5 scar). Box rebooted 08-26 19:01, which accounts for
the 17:00-19:00 gap exactly.

**`cannot_start` is flat at 32 for the third reading, and the FLOW is zero for
the second window running.** Nothing in the 32 is newer than **08-22**, zero
broken tools were created in 24.7 hours, and `tool-edit`'s write-time WARNING
fired **0 times** because it had nothing to fire on. The 08-29 trigger stands
against the stock, but the stock is legacy and the flow is the live measure.

**Two instruments answered the always-zero question honestly.** `JANITOR:aged-out
0` has now appeared **54 runs** running -- and a live census says **0 hollow
stubs exist**, so it is genuinely idle rather than blind. `UNMET` **broke its
streak**: `329n/7842d+0`, back to 0/7 from 2/7, so the builder trigger receded.

**New watch: `exec/think` is climbing** -- 1.12, 1.19, 1.22, **1.35** across the
last four hourly readings, against 0.99 yesterday. No hypothesis yet; recorded
as a measurement.

Gates unchanged since `ede86c0`: **laptop 404 PASS, PC 398 PASS**.

---

### Previous state — 2026-08-27 (Cloudflare added)

**A sixth rung: `cloudflare`, and its exhaustion signature is KNOWN before it
carries traffic** -- the first time a rung has been added that way. Tue created
the account; the rung is `@cf/meta/llama-3.3-70b-instruct-fp8-fast` on Workers
AI, placed **below `google_gemma`** (the 14,400/day workhorse) and above mistral
and the OR pool, so it is reached when gemma walls. No code was needed: the
config already carries a per-rung `endpoint`, and Cloudflare's OpenAI-compatible
URL embeds the account id.

**Model choice was measured, not assumed.** Of the five models the Workers FREE
plan will actually serve, `llama-3.3-70b-instruct-fp8-fast` is the only one that
finished a real 10k-token prompt with `finish=stop` (278 tokens). `gpt-oss-120b`
and `nemotron-3-120b-a12b` are reasoning models: both returned `finish=length`
at `max_tokens=600`. Four catalogued frontier models -- `kimi-k2.6`, `glm-5.2`,
`glm-5.3-flash`, `deepseek-v4-pro-0813` -- answer **HTTP 403 code 5035, "not
available on the Workers Free plan"**, while the model-search API lists them
regardless. That shape now classifies as `gone` (`ec2b410`), because the id has
left OUR shelf while the account is fine, and a single-model rung must be walled
WITH a log line.

**Capacity, and the number that is NOT the published one.** One wake-sized call
(10,295 in / 556 out, measured) costs ~388 neurons, so 10,000/day is **~26
calls/day** -- a FLOOR rung at ~3.4% of the creature's 770 thinks/day, not a fix
for gemma's 90.9%. **But the cap is enforced with LAG:** a deliberate probe spent
**15,455 neurons across 28 consecutive HTTP 200s** and enforcement only arrived
afterwards. So "it still serves" is not evidence of headroom.

**The exhaustion signature, earned the useful way.** Because the probe overran,
the next `provider.call` returned it for free: **HTTP 429, "you have used up your
daily free allocation of 10,000 neurons"**. `classify_error` already maps that to
`quota` with no change -- it walls the rung and the ladder falls through -- and
the running brain proved it in production, writing `cloudflare:{exhausted_at}`
into `quota_state.json` by itself. **Today's allowance is spent by my probe; the
rung returns on the daily reset.** First thing to check tomorrow: does
`cloudflare` show a `last_success_at`.

**Cloudflare returns NO `x-ratelimit-*` headers** -- only `cf-ai-neurons`, the
actual cost of that call, which matched the published price table to four
decimal places. So this project's canonical "read the limits from headers"
method does not work here; the per-call cost is the instrument instead.

**Open, and it is a real fragility found on the way:** `classify_error` matches
substrings against whole error bodies, and Cloudflare puts a **UUID in every
error**. A UUID containing "402" or "429" would misclassify a transient failure
as `quota` and wall a healthy rung. Rough odds ~0.7% per error. Not fixed today
-- it needs status-vs-body separation, which is bigger than an obvious fix.
**Named trigger: the first walled rung nobody can explain, or 2026-09-10,
whichever comes first.**

Gates: **laptop 404 PASS, PC 398 PASS**, each ending `ALL TESTS PASS`.

---

### Previous state — 2026-08-26 16:30

**The keyhole fix had a sequel, and it was worse than the original: the marker
lied.** gs-bug-daily one day later found that truncation NESTS -- writer caps
stdout at 300 and marks it, render caps the whole record at 300 and marks it
again, overwriting the honest number with its own. The creature was shown
**`+40 chars cut` where 3,319 characters were withheld**. Fixed `5427b72`; the
full anatomy and the two general lessons are in the new §5 scar. Verified live:
the same record now reports `+3328` against 3,320 truly withheld (8 chars over,
because the record's own ` stderr=` framing counts as content -- conservative
direction, 0.24%). **The watch for tomorrow is behavioural, not numeric:** it
asked for `sed -n '1,100p'` 97 times and `1,50p` 56 times in 15.6 h, every one
too large to fit. Does an honest number change how it sizes reads?

**gs-bug-daily 2026-08-26 16:25 (19.8h, no gaps).** 770 thinks at 38.9/h, 759
exec, 63 skips, **4 errors** -- 3 done-gate (right reason), 1 provider. Library
494. Truncation of thinks 3.1% (5.1% yesterday) but **82.3% of exec RESULTS were
capped**, which is the number that mattered and no previous run had measured.
`exec/think` 0.99.

**Three framework faults fixed up front, each with a test that fails without
it.** (1) `9c27900` Cloudflare **520-527 -> retryable**: mistral returned
`HTTP 520: error code: 520` at 00:08 and reached the `unknown` path, which
routed around it and carried the text -- the c1b93a5 fail-open design working
for the **third** time, and the third unenumerated error shape it has handed us.
(2) `5427b72` the nested-truncation marker, above. (3) `b2d1b61` the funnel's
early-rejection stage, which had read zero three runs running because it counted
an event that only ever existed on stdout.

**`tool-edit`'s write-time WARNING fired on its first day and the repair
followed in 79 minutes.** 13:39 `ContradictionWatcher` was saved with no `#!`
and a body that is neither Python nor shell; stderr said so; by 14:58 it starts.
**It never entered the 32.** That reframes the 08-26 trigger: `cannot_start` is
a **stock**, the new check governs the **flow**, and the flow reading for this
window is **zero new broken tools**. Nothing in the 32 is newer than 08-22;
oldest is 06-22. Trigger re-armed for **08-29** against the stock, but the
honest measure is now the flow.

**Ladder is thin and this one is Tue's.** 5 enabled rungs, all momentarily
walled at read time (normal daily recycling -- it was serving again minutes
later), but `google_gemma` carries **90.9%**, `openrouter_super` has been dark
**13h**, mistral returns **08-31**, cerebras retired today. FLATLINE confirmed
the retirement by dropping cerebras from SERIOUS at 16:07. Effective depth: two.

**Builder trigger is advancing: `UNMET:329n/7842d+7 streak 2/7`.** Second
consecutive day of growth. Fires at 7.

Gates: **laptop 402 PASS, PC 396 PASS**, each ending `ALL TESTS PASS`.

---

### Previous state — 2026-08-26 00:35

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
