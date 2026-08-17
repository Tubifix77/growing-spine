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
- Direct intervention only if it is genuinely stuck, and only after discussing it
  with Tue. Consent in chat is the floor, not the ceiling.

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
  `tool:: command not found` for two months.
- **YAML's Norway problem:** a bare `off`/`on`/`yes`/`no` key parses as a boolean.
- **Tests that assert a MECHANISM go red when you improve the mechanism.** Assert
  the contract instead. They also go red where the mechanism is deliberately
  *absent*: the chat test asserted `chat.jsonl.lock` exists, and off POSIX
  `_locked` is a no-op by design, so the whole gate was red on the PC peer while
  a sibling test two hundred lines away existed purely to keep the suite runnable
  there (found 2026-08-11). Assert the contract always, the mechanism where it
  can exist.
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

- **Quality floor over capacity.** No weak model in the ladder: under a shared
  cap, weak calls starve smart rungs and a weak author's buggy tools are lasting
  pollution. `openrouter/free` auto-routing stays rejected.
- **Reversible actions are just done**, not asked about.
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

## 8. State — 2026-08-14 17:45

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
  file its wrong `groq: 14400`. **UNKNOWN: no daily or monthly header is returned,
  so the size of the free allowance is invisible.** If it runs out the rung
  402/429s and the keychain walls it honestly — watch for `mistral` appearing in
  FLATLINE. Key lives at `/home/boas/mistral.key` (chmod 600, outside the repo).
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
  (1) demanded stubs (`demand_counts` ≥ 5) sustained above zero for 7
  consecutive days — its own hands stopped keeping up; or (2) the data-warning
  surfacing NEW unreadable/fabricated stores in consecutive weeks — visibility
  proved insufficient and quality needs fixing at construction time. Until one
  fires, the graft answers a theory.

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
