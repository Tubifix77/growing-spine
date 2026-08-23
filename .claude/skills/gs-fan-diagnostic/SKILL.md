---
name: gs-fan-diagnostic
description: Diagnose why the Growing Spine laptop's CPU fan is running hard — against a reference list of the tenants that normally run there together with no problem, so the answer is never "close Steam and Heroic". Fire on "the fan is running", "the laptop is loud", "it sounds hot", "gs-fan-diagnostic", or any report of noise, heat or a spinning fan.
---

# gs-fan-diagnostic — why is the fan running, and is it even us?

Tue reports this roughly fortnightly. His ear has been right **three times out of
three**: thermal clamping, a 49-orphan runaway hitting the container's CPU cap,
and 9,082 zombies filling the PID namespace. Every time the first attribution was
"legitimate workload" and every time that was wrong.

So the report is a **fault report from a detector with a perfect record**, not a
hypothesis to assess. Measure the whole box before forming any explanation.

## Read `baseline.md` in this directory FIRST

It lists the tenants that normally run on that laptop together — Bedrock server
and its manager, Steam, Heroic, opensnitch, ufw, pihole, and Growing Spine — all
at once, with no fan problem. **They are the normal state, not a suspect list.**

A diagnosis that ends in "close Steam and Heroic" has diagnosed nothing; it has
described Tue's desktop back to him. Say so if that is genuinely all you found.

`baseline.md` also records that there is **no trustworthy numeric baseline yet**,
and why the first attempt was discarded. Until quiet samples accumulate,
**"I cannot say whether this is abnormal" is a permitted and honest answer.**

## Tier 1 — mandated checks, in this order. Run all of them.

1. **Is this me?** Is an inspection session running on that laptop now, or in the
   previous 15 minutes? Every `/gs-*` run sweeps Python over 488 tool files;
   `gs-products` shells out to `bash -n` per shell tool; `gs-bug-daily` reads a
   64 MB journal tail. Tue has reported the diagnostics themselves causing fan
   events. Check `ps` for `python3` under `/home/boas/gs_*` or a bridge `sshd`
   doing real work, and check when this session last ran anything.
2. **Whole-box aggregate, before any component.** Package temperature,
   `intel_powerclamp cur_state`, `loadavg` (all three), total process count,
   zombie count.
3. **Every process above 0.4%, with BOTH numbers**: its lifetime average and a
   sampled instantaneous reading. They differ by an order of magnitude for bursty
   tenants — `bedrock_server` averages single digits and samples at 120%.
4. **Diff against the tenant list**: which baseline tenants are present, which are
   absent, and **what is running that is not on the list at all**. The last group
   is the finding; the first two are context.
5. **Periodic jobs.** What fired in the last hour and what is due:
   `systemctl list-timers --all`, plus `cron.daily` / `weekly` / `monthly` and
   `anacron`. The symptom is periodic, so a periodic cause is the first
   hypothesis. Note especially that `update-system` and `fstrim` both land Monday
   night.
6. **Is it CPU at all?** `iowait` from `vmstat`, disk utilisation, and free space.
   A fan spins for heat, and heat comes from I/O and from a full or trimming disk
   as readily as from compute. Disk was 85% full on 2026-08-23.
7. **The container**: actual container CPU from `docker stats`, `pids.current` vs
   `pids.max`, zombie count, `HostConfig.Init`. Remember the cap — 1.5 of 4 cores
   — so a container reading near 150% is at its ceiling, not eating the box.
8. **The creature's own processes**: `/mind/tools/` cmdlines with ages
   (`loop._stuck_tool_procs`). A tool that has not returned still holds its CPU.
9. **Framework per-cycle cost**: `WAKE` p50/max against its budget, and the
   brain's own CPU — but only if brain uptime exceeds 2 hours, or the average is
   cold-start noise rather than steady state.
10. **Thermal history**: is the clamp engaged now, and how long has it been? A
    clamped box is already being protected, which is a different situation from a
    hot one.
11. Deltas against the previous run, and whether this sample qualifies as `quiet`
    for baseline purposes.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Establish whether the cadence is real before explaining it.** Tue reports this
> about every 14 days, and **nothing on that box runs on a 14-day timer**. So one
> of three things is true: two weekly jobs coincide (`update-system` and `fstrim`
> share a Monday night), something cumulative is crossing a threshold, or the
> interval is not really 14 days. A cumulative cause is the interesting one and
> the one this project has form for — the quadratic dependency scan got worse
> every time the creature built a tool, and its load parameter was its own
> success. Check the history file for previous fan events and their dates before
> reaching for a cause.
>
> **Deliver:** The dates of prior fan events from the history file with the
> intervals between them, or the literal words "no prior events recorded" — plus
> which of the three explanations the evidence supports, or that it supports none.

> **Ask whether it is heat or work.** A fan can run hard at an ordinary workload:
> a dusty vent, a warm room, the laptop on a soft surface, a failing fan bearing,
> thermal paste past its life. If temperature is high while load, iowait and
> container CPU are all normal, **the answer is physical and no amount of software
> diagnosis will find it** — and saying that plainly is the correct outcome, not a
> failure to diagnose. This machine idles at 60–70 °C.
>
> **Deliver:** Temperature paired with loadavg, iowait and container CPU, and an
> explicit verdict: work-caused, heat-caused, or cannot distinguish.

> **Account for our own additions honestly, whatever the answer.** Time every
> per-cycle builder the framework runs and state the total, and state what the
> inspection session itself cost on this laptop today. On 2026-08-18 the honest
> answer was 15 ms combined against a 45-second fault that predated the session,
> and saying so was worth more than being blamed or exonerated.
>
> **Deliver:** Total milliseconds of our per-cycle work, plus what this session
> has executed on that laptop in the last hour.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing that could make this laptop hot that no item above would have
> caught — or say plainly that you found none. If it mattered, add it to Tier 1,
> dated, and to `baseline.md` if it changes what "normal" means.

## Tier 4 — if the cause is one of the creature's tools

Two things apply, in this order.

**Stop the bleeding first, and that is not an intervention.** Kill the runaway
processes and respawn the body immediately — no consent, no waiting. Its tools are
its world; its processes are not, and the body is disposable by design.

**Then the response protocol**, which lives in `gs-products` Tier 4 and is not
restated here: the class rather than the instance, the machine that allowed it,
why the creature cannot see it, the detector, the channel that reaches it
unprompted, and confirmation that no tool of its own was edited. In this case
item 2 has a specific answer — **the framework was missing a bound** — and the
detector is a limiter: a cap, a timeout, a reaper. Never an edit to its tool.

Note what is already bounded, so the limiter you propose is one that is missing:
container CPU 1.5 cores, memory 1 GB, `run_command` timeout 300 s — but that
timeout binds the **exec**, not the children it backgrounds, which is how 49
orphans accumulated.

## Write the numbers down

Append one record per run to `gs-history/fan.jsonl` in this repo checkout.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `reported_by_human`, `temp_c`, `powerclamp`, `loadavg1`,
`procs`, `zombies`, `iowait_pct`, `disk_free_gb`, `container_cpu_pct`,
`pids_current`, `brain_up_h`, `brain_cpu_pct`, `wake_p50_ms`,
`processes_over_0_4[{name,avg,inst,in_baseline}]`, `not_in_baseline[]`,
`timers_fired_last_hour[]`, `verdict` (work | heat | inspection | cannot-tell),
`inspection_active`, `quiet` (true only if no inspection ran within 15 min and
brain uptime > 2 h — only quiet samples may form the baseline).
