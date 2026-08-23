---
name: gs-fan-diagnostic
description: Diagnose why the Growing Spine laptop's CPU fan is running hard — standalone, against a reference list of the tenants that normally run there together with no problem, so the answer is never "close Steam and Heroic". Adds the is-this-me check, the periodic-job sweep and a heat-versus-work verdict. Fire on "the fan is running", "the laptop is loud", "it sounds hot", "gs-fan-diagnostic", or any report of noise, heat or sluggishness.
---

# gs-fan-diagnostic — why is it hot, and is it even us?

**This skill stands alone.** "The fan is loud" is exactly the moment someone
types it cold, so it takes its own box measurements in part A below — it never
requires `gs-vitals` to have run.

If `gs-vitals` HAS just run, reuse its numbers instead of taking them again and
reference its history record. Reuse when available, measure when not; never
depend.

The overlap with `gs-vitals` in part A is deliberate. What must not be duplicated
is a **definition** — the tenant list, the thresholds, the container caps — and
those live once, in `../baseline-laptop.md`. Two skills measuring temperature is
fine. Two skills deciding for themselves what "normal" means is the
producer-and-checker drift this project keeps getting burned by.

Tue reports this roughly fortnightly. His ear has been right **three times out of
three**: thermal clamping, a 49-orphan runaway hitting the container's CPU cap,
and 9,082 zombies filling the PID namespace. Each time the first attribution was
"legitimate workload" and each time that was wrong. So his report is a **fault
report from a detector with a perfect record**, and it is a sufficient trigger on
its own regardless of what the numbers say.

## Read `../baseline-laptop.md` first

The shared reference for what normally runs on that machine — Bedrock and its
manager, Steam, Heroic, opensnitch, ufw, pihole — **all at once, with no fan
problem. They are the normal state, not a suspect list.** A diagnosis that ends in
"close Steam and Heroic" has diagnosed nothing; it has described Tue's desktop
back to him. Say so plainly if that is genuinely all you found.

That file also records that there is **no trustworthy numeric baseline yet** and
why the first attempt was discarded. Until quiet samples accumulate, **"I cannot
say whether this is abnormal" is a permitted and honest answer.**

## Tier 1 part A — the box measurement. Take it, or reuse a fresh `gs-vitals` run.

Same checks and the same thresholds as `gs-vitals`, because a fan diagnosis that
skips them is guessing. Definitions come from `../baseline-laptop.md`; do not
invent local ones.

1. Package temperature and `intel_powerclamp cur_state` (−1 or 0 = not clamping).
2. `loadavg` (all three), total process count, zombie count.
3. Container `pids.current` / `pids.max`, `HostConfig.Init`, and container CPU
   from `docker stats` — against the cap of **1.5 of 4 cores**, so a reading near
   150% is at its ceiling rather than eating the box.
4. Disk free on `/` and on the volume, plus the journal's size.
5. Per-cycle framework cost: `WAKE` p50/max against its budget — and only trust
   any brain-CPU average if brain uptime exceeds 2 hours, or it is cold-start
   noise.
6. The creature's own running processes: `/mind/tools/` cmdlines with ages
   (`loop._stuck_tool_procs`). A tool that has not returned still holds its CPU.

## Tier 1 part B — the five checks only this skill makes. Run all of them.

1. **Is this me?** Is an inspection session running on that laptop now, or in the
   previous 15 minutes? Every `/gs-*` run sweeps Python across 488 tool files;
   `gs-products` shells out to `bash -n` per shell tool; `gs-bug-daily` reads a
   64 MB journal tail. Tue has reported the diagnostics themselves causing fan
   events, and the discarded baseline is proof that an inspection is loud enough
   to appear in its own measurements. Check `ps` for `python3` under
   `/home/boas/gs_*`, a bridge `sshd` doing real work, and what this session has
   executed on that box in the last hour.
2. **Diff against the tenant list.** Which baseline tenants are present, which are
   absent, and **what is running that is not on the list at all** — the last group
   is the finding, the first two are context. Use a **0.4% threshold** here, not
   `gs-vitals`' 2%: a bursty tenant averages below 2% and samples above 100%, so
   report both its lifetime average and a sampled instantaneous reading.
3. **Periodic jobs.** What fired in the last hour and what is due:
   `systemctl list-timers --all`, plus `cron.daily` / `weekly` / `monthly` and
   `anacron`. The symptom is periodic, so a periodic cause is the first
   hypothesis, not the last.
4. **Is it CPU at all?** `iowait` from `vmstat`, and disk utilisation. A fan spins
   for heat, and heat comes from I/O and from a trimming or nearly-full disk as
   readily as from compute.
5. **Thermal history.** Is the clamp engaged now, and for how long? A clamped box
   is already being protected, which is a different situation from a hot one — and
   it understates every software timing taken on it.

Then: does this sample qualify as `quiet` for baseline purposes — no inspection
within 15 minutes and brain uptime over 2 hours? Only quiet samples may form the
baseline.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Establish whether the cadence is real before explaining it.** Tue reports this
> about every 14 days, and **nothing on that box runs on a 14-day timer**. So one
> of three things is true: two weekly jobs coincide (`update-system` and `fstrim`
> share a Monday night), something cumulative is crossing a threshold, or the
> interval is not really 14 days. The cumulative one is the interesting one and
> the one this project has form for — the quadratic dependency scan got worse
> every time the creature built a tool, and its load parameter was its own
> success. Check the history for previous fan events and their dates before
> reaching for a cause.
>
> **Deliver:** The dates of prior fan events from `gs-history/fan.jsonl` with the
> intervals between them, or the literal words "no prior events recorded" — plus
> which of the three explanations the evidence supports, or that it supports none.

> **Ask whether it is heat or work.** A fan can run hard at an ordinary workload:
> a dusty vent, a warm room, the laptop on a soft surface, a failing bearing,
> thermal paste past its life. If temperature is high while load, iowait and
> container CPU are all normal, **the answer is physical and no amount of software
> diagnosis will find it** — and saying that plainly is the correct outcome, not a
> failure to diagnose. This machine idles at 60–70 °C.
>
> **Deliver:** Temperature paired with loadavg, iowait and container CPU, and an
> explicit verdict: work-caused, heat-caused, inspection-caused, or cannot
> distinguish.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing that could make this laptop hot that neither this skill nor
> `gs-vitals` would have caught — or say plainly that you found none. If it
> mattered, add it to Tier 1 here, dated, and to `../baseline-laptop.md` if it
> changes what "normal" means.

## Tier 4 — if the cause is one of the creature's tools

**Stop the bleeding first, and that is not an intervention.** Kill the runaway
processes and respawn the body immediately — no consent, no waiting. Its tools are
its world; its processes are not, and the body is disposable by design.

**Then the response protocol**, which lives in `gs-products` Tier 4 and is not
restated here. In this case item 2 has a specific answer — **the framework was
missing a bound** — and item 4's detector is a limiter: a cap, a timeout, a
reaper. Never an edit to its tool.

Know what is already bounded, so the limiter you propose is a missing one:
container CPU **1.5 of 4 cores**, memory **1 GB**, `run_command` timeout 300 s —
but that timeout binds the **exec**, not the children it backgrounds, which is how
49 orphans accumulated.

## Write the numbers down

Append one record per run to `gs-history/fan.jsonl` in this repo checkout.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `reported_by_human`, `inspection_active`,
`processes_over_0_4[{name,avg,inst,in_baseline}]`, `not_in_baseline[]`,
`timers_fired_last_hour[]`, `iowait_pct`, `clamp_engaged_min`, `verdict`
(work | heat | inspection | cannot-tell), `quiet`, and the part-A box numbers.
If a fresh `gs-vitals` record was reused rather than re-measured, set
`vitals_run` to its timestamp instead of copying its fields.
