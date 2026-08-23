# `/gs-*` — the standing inspections

Eight skills, one per area of the system. Invoke by name (`/gs-vitals`) or let
them fire on a matching request.

| Skill | The question it answers | Cadence |
|---|---|---|
| `gs-bug-daily` | What went wrong in the framework, and did the last fix work? | Per session / ~20h window |
| `gs-products` | What has the creature built, is it used, is it sound, is any of it worth copying? | Weekly, or on request |
| `gs-vitals` | Is the box healthy, is any of the load ours, did our code even load? | On any physical symptom |
| `gs-ladder` | Which LLM rungs serve, which are dark, and what don't we know yet? | On any FLATLINE/SERIOUS, before adding or retiring a rung |
| `gs-data` | Is its stored knowledge readable, real, and in one place? | Weekly |
| `gs-instruments` | Do the checks themselves still work? | After adding an instrument; after any fault a human found first |
| `gs-directives` | Is the framework telling it something wrong? | Monthly, or after a fault that smells like obedience |
| `gs-secrets` | Has a key escaped, and which are pending rotation? | After any session that touched config; before publishing |

## Where these run

**They run in the inspection session, on the PC. They do not run on the laptop.**
The laptop runs the creature; this session watches it from outside and is
deliberately detached from it. So:

- The skills live in this repo because that is what makes them versioned and
  shared, not because anything on the laptop reads them. The creature never sees
  them and they never enter its wake context.
- The history files are **repo-local and gitignored** (`gs-history/`), on the
  machine the session runs on — following the precedent `audit/` and
  `DEV-LEDGER.md` already set: a record of a live system's failure modes, in a
  public repo, stays untracked.
- Almost every measurement is taken **over the SSH bridge**, so the laptop is
  the subject, never the host.

### Bridge discipline — this is where the runs actually break

The bridge is not a terminal. It wedges, and then the whole check is lost
mid-flight. Two of them wedged in one week, both my fault:

- **Never sleep or wait-loop in a bridge command.** A 90-second polling loop
  wedged it. If you need to wait for something, end the call and make a second,
  short one.
- **Never run a blocking systemd action.** `systemctl --user start` on a oneshot
  unit blocks until the unit finishes and wedged the bridge; use `--no-block`, or
  invoke the script directly.
- **Keep payloads small.** Large heredocs travel badly. Upload a script with
  `ssh_upload` and run it, rather than pasting it into a command.
- **Base64 through the session is not byte-safe.** A 6,576-char blob returned
  with the right length, the right PNG header and a different md5 — characters
  substituted in the middle. If you must move binary, keep it small and
  `md5sum` both ends.

Anything long-running should be launched detached and read back in a separate
short call.

## Why these exist

A free-form "what happened since yesterday" catches novel things but varies with
whatever the session thought of that morning. A fixed checklist is reproducible
but blind to anything not on it — and that blindness is this project's
characteristic failure: on 2026-08-19 three instruments were all working
correctly and the creature had been down for twelve hours, because each was
watching something adjacent to the problem.

So every skill has three tiers, and all three are mandatory:

1. **Mandated checks** — terse, mechanical, reproducible. Each one is on the list
   because it has already caught something.
2. **Pointed open inspection** — open in method, specific in target, written as
   prose because a one-line open item gets a one-line look.
3. **One blank pass** — "name something no item above would have caught, or state
   that you found none." Phrased so that finding nothing is an answer you can be
   wrong about.

**Anything the blank pass finds that mattered becomes a Tier 1 item, dated.**
That is the ratchet: the lists grow from what has bitten us rather than from what
someone imagined on the day they were written.

## The one architectural rule

**Skills carry procedure. `CLAUDE.md` carries doctrine.**

A skill states the commands, the order, and the traps in context, then *points*
at `CLAUDE.md` §5 for the scar rather than quoting it. Restating doctrine in
eight files would create eight copies that diverge — which is precisely the
producer-and-checker drift the whole project keeps getting burned by. When a scar
is corrected, it must be corrected in one place.

Live state and standing decisions likewise live only in `CLAUDE.md` §6 and §8.

## History files

Each skill appends one record per run to `gs-history/<name>.jsonl` in this repo
checkout — on the machine the session runs on, and gitignored so it never
publishes. Nothing on the laptop reads or writes these.

Three constraints, each from a scar this project already owns:

- **One record per line.** Non-negotiable; this is the fault the creature keeps
  rebuilding and we must not hand it a bad example.
- **A skipped run is absent, never a zero.** Absence of evidence is not evidence
  of zero — the day the laptop ran something else proved why.
- **Never cap a sample inside a measurement.** A cap once pinned an escalation
  rule below its own trigger and made the alarm silent by arithmetic.

The point of the history is that snapshots become trends. "Is it getting better
at building tools?" is currently unanswerable, because the quality census has
exactly one data point.

## Who receives the output

Every skill says so explicitly. Nothing here enters the creature's wake context:
these answer questions about *our* stewardship, not facts about its world. An
instrument only we can read makes us better caretakers; only something the
creature receives makes it more independent — and the doctrine prefers the
latter, so when a finding could become a fact it can act on, say so.

## Report-only

No skill repairs anything. Mixing diagnosis and repair in one command is how a
check becomes a whim. Findings about the creature's own tools are never fixed by
us at all — the method is to ask why the framework let the fault be built, then
make it visible so the creature prunes it itself.
