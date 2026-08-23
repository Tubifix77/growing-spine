---
name: gs-vitals
description: Physical and process health of the Growing Spine laptop — heat, load, zombies, container PID headroom, disk, and whether the load is even ours. Fire on "is the laptop ok", "it sounds louder than usual", "check the box", "gs-vitals", any report of noise/heat/sluggishness, or before explaining any performance symptom.
---

# gs-vitals — is the box healthy, is any of it ours, and did our code even load?

## Before you start — the rule that matters most here

**A human's physical report is a fault report from a detector with a perfect
record.** Tue's ear has been right three times out of three: thermal clamping,
a 49-orphan runaway at 148% container CPU, and 9,082 zombies filling the PID
namespace. Every time, the first attribution was "legitimate workload" and every
time that was wrong. **Measure the whole box before forming a hypothesis**, and
include our own additions in the measurement.

**A status field is not liveness.** `docker inspect .State.Running` reads `true`
for a container that cannot fork a single process. That is how the body sat dead
for three and a half hours while every check called it healthy.

## Tier 1 — mandated checks. Run all of them, every time.

1. Date, `uptime`, brain `ActiveEnterTimestamp`, body `StartedAt`. **Flag
   disagreement with what the human believes the runtime was** — twice now the
   estimate has been roughly half the measured span, and hourly journal record
   counts are the stronger evidence.
2. `loadavg`, total process count, zombie count (`ps -eo stat | grep -c '^Z'`).
3. Container `pids.current` / `pids.max`, and `HostConfig.Init`. Init must be
   true: PID 1 in any container we start must reap.
4. Thermal zone temperature and `intel_powerclamp cur_state` (−1 or 0 = not
   clamping). A clamped box understates every software timing you take on it.
5. `docker stats --no-stream` for every container.
6. Every process above 2% CPU with its full cmdline, **each explicitly
   attributed ours / not ours** — against the tenant list in
   `../baseline-laptop.md`, which is the shared reference for what normally runs
   on that machine. Do not re-derive it and never conclude "close Steam and
   Heroic": those are the normal state.
7. **The creature's own running processes** — `/mind/tools/` cmdlines with ages
   (`loop._stuck_tool_procs`). Added 2026-08-23: a tool that has not returned
   still holds its CPU and memory, and this check was absent while a sibling
   skill had it.
8. **Body liveness by doing** — `sandbox.body_responds()`. Never a status field.
9. Failed systemd units, and for each: is it the designed alarm (`exit_code`
   returns nonzero when a traffic-carrying rung is silent) or a real failure?
10. Per-cycle framework cost: `WAKE` p50/max against `WAKE_COST_BUDGET_MS`.
11. **Disk headroom** on the volume and on `/`. `journal.jsonl` is append-only
    and already 130 MB; a full disk is a spectacular silent failure and nothing
    else watches it. Report free bytes and the journal's growth since last run.
12. **Did the deploy load?** Compare `git log -1` on the laptop against the code
    the running brain actually holds — import the module and check for the
    symbol the last change introduced. A restart is assumed, not proven,
    otherwise.
13. Deltas against the previous run of this skill.

### When to escalate to `gs-fan-diagnostic`

This skill is the routine breadth check. Hand off to `gs-fan-diagnostic` — which
owns the baseline diff, the periodic-job sweep and the heat-versus-work verdict —
when **any** of these is true:

- package temperature is high while `loadavg`, container CPU and iowait are all
  normal (that is the physical-cause shape: dust, a soft surface, thermal paste);
- `intel_powerclamp cur_state` is above 0, i.e. the kernel is already protecting
  the box;
- a process above the threshold is **not on the tenant list**;
- a human reported noise, heat or sluggishness — their ear has been right 3/3, and
  that is a trigger on its own regardless of what these numbers say.

Escalating means running the five checks that skill adds, not repeating these.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Before explaining anything, ask what changed on this box that is not ours.**
> `bedrock_server` — a Minecraft server — has been the single loudest process
> twice, at 88% and 120%. Steam, Heroic and a pihole container also live here.
> Attributing someone else's game to the creature is the easiest wrong answer
> available, and the opposite error is just as easy: on 2026-08-18 the fan noise
> was real, ours, and had been going for 32 hours.
>
> **Deliver:** Every process above 2% named and attributed ours / not ours. No process left unattributed.

> **Then account honestly for our own additions.** Time every per-cycle builder
> we have added and state the total, whether or not it is the cause. On
> 2026-08-18 the answer was 15 ms combined against a 45-second fault that
> predated the session — and saying so plainly was worth more than being either
> blamed or exonerated.
>
> **Deliver:** The total milliseconds of our per-cycle additions, whether or not they are the cause.

> **Ask what would have to be true for this box to be unhealthy in a way none of
> the numbers above would show.** Thermal throttling, PID exhaustion and zombie
> accumulation were each invisible until someone looked for them specifically.
>
> **Deliver:** One named blind spot, or the list of sensors you enumerated before concluding there is none.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing about this box that no item above would have caught — or say
> plainly that you found none. If it mattered, add it to Tier 1, dated.

## Write the numbers down

Append one record per run to `gs-history/vitals.jsonl` in this repo checkout.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `uptime_h`, `brain_up_h`, `loadavg1`, `procs`, `zombies`,
`pids_current`, `pids_max`, `init`, `temp_c`, `powerclamp`, `container_cpu_pct`,
`body_responds`, `failed_units[]`, `wake_p50_ms`, `disk_free_gb`,
`journal_mb`, `deploy_loaded`, `stuck_tools`.

## If something is wrong

A respawn of the body is normal ops and self-healing — `ensure_body` does it.
**Restart the brain BEFORE killing the body**: a respawned container inherits the
running brain's in-memory code, not the disk's (`CLAUDE.md` §2.4).
