# The laptop's known-good tenants

**These are NOT suspects. They are the normal state of this machine.** All of them
run together with Growing Spine, continuously, with no fan problem. A diagnosis
that concludes "close Steam and Heroic" has not diagnosed anything — it has
described Tue's desktop back to him.

Tue owns this file. Correct it whenever the normal set changes; a baseline nobody
maintains becomes a source of false findings.

## The tenants — the LIST is reliable, the NUMBERS are not yet

| Process | What it is | Whose |
|---|---|---|
| `bedrock_server` | Minecraft Bedrock server | Tue's |
| Bedrock server *manager* | Tue's manager program | Tue's |
| `steam`, `steamwebhelper` | Steam client | Tue's |
| `heroic` | Heroic games launcher | Tue's |
| `opensnitch-ui` / daemon | Application firewall | Tue's |
| `ufw` | Firewall (not a busy daemon) | Tue's |
| `main.py` | Growing Spine brain | ours |
| `observer.py` | Growing Spine dashboard | ours |
| `growing-spine-body` | the creature's container | ours |
| `pihole` container | DNS | Tue's |

`bedrock_server` is **bursty**, and this is the single most important
non-finding on the machine: it has been sampled at **88% and 120%** in short
windows and has twice been the loudest process on the box. A high instantaneous
reading from it is normal.

## There is NO trustworthy CPU baseline yet — and that is the honest state

A first attempt was measured on 2026-08-23 at 13:52 and **discarded as
contaminated**, on Tue's challenge. The contamination was visible in the figures
themselves:

- `sshd` read **22.7%** — that was the inspection session's own bridge.
- `main.py` read 4.7% averaged over an `etimes` of **0.5 h**, because the brain
  had been restarted at 13:22. That average is mostly cold start: embed model
  load, cold parse caches, a 2.8 s first context build.
- The whole sample was taken minutes after Python sweeps across 488 tool files.

A number taken while the measurer is working describes the measurer. Recording
this rather than quietly replacing it, because the discarded method is worth more
than the discarded number.

### How a real baseline must be taken

1. **No inspection session active**, and none in the previous 15 minutes.
2. **Brain uptime over 2 hours**, so lifetime averages are steady-state rather
   than cold-start.
3. **At least 5 samples on different days**, at different times of day, with the
   normal tenant set running.
4. Record per sample: package temp, `intel_powerclamp cur_state`, `loadavg`,
   total process count, and every process above 0.4% with **both** its lifetime
   average and a sampled instantaneous reading — those two differ by an order of
   magnitude for bursty tenants.
5. The baseline is then the **median of the quiet samples**, with the spread
   stated. Not one reading, and not a reading taken during an incident.

Until that exists, the skill reports observations against the tenant *list* and
says plainly that it has no numeric baseline to compare against. **"I cannot say
whether this is abnormal" is a permitted and honest answer** — and far better than
a comparison against a number that describes an inspection.

Samples accumulate in `gs-history/fan.jsonl`, tagged `quiet: true|false`. Only
quiet samples may form the baseline.

## Our own ceiling — hard facts, not contaminated

Read from the cgroup, so these are unaffected by who was measuring:

- Container `cpu.max = 150000 100000` — **1.5 of 4 cores**, hard.
- Container `memory = 1 GB`, hard.
- **A runaway tool of the creature's cannot starve the host.** The "148%" of
  2026-08-14 *was* that cap being hit, not the box being taken.
- Unbounded, and therefore the real risks: **disk** (85% full, 17 GB free on
  2026-08-23) and **PIDs** (`pids.max` 9090; filled once, by our own
  `sleep infinity`, not by a tool of its own).

## Periodic jobs — check these before blaming software that is always running

The reported symptom recurs roughly fortnightly, and **nothing on this box runs on
a 14-day timer.** So either two weeklies coincide, or something cumulative is
crossing a threshold, or the cadence is not really 14 days. Establish which; do
not assume.

| Unit | Cadence | Seen |
|---|---|---|
| `update-system.timer` | weekly, Mon ~00:11 | 08-17 → 08-24 |
| `fstrim.timer` | weekly, Mon ~01:20 | 08-17 → 08-24 |
| `e2scrub_all.timer` | weekly, Sun ~03:10 | 08-23 → 08-30 |
| `apt-daily` / `apt-daily-upgrade` | daily | ~06:07 / ~06:33 |
| `man-db.timer` | daily | ~00:29 |
| `logrotate`, `dpkg-db-backup` | daily, 00:00 | — |
| `systemd-tmpfiles-clean` | daily, ~23:51 | — |
| `anacron.timer` | hourly | — |
| `cron.daily` | `0anacron apt-compat dpkg logrotate man-db popularity-contest` | — |
| `cron.weekly` | `0anacron man-db` | — |

**Two weeklies land on the same Monday night** — `update-system` and `fstrim`.
That is the closest thing on this machine to a fortnightly pattern, and it is the
first hypothesis to test rather than the last.

## The tenant that is easiest to forget

**The inspection session itself.** Every `/gs-*` run executes Python across 488
tool files on this laptop; `gs-products` shells out to `bash -n` once per shell
tool; `gs-bug-daily` reads a 64 MB journal tail. A full startability sweep is
~350 ms cold, and a `gs-products` run is seconds of sustained Python plus dozens
of subprocesses.

Tue has explicitly reported that the diagnostic tools have caused fan events, and
the discarded baseline above is proof that an inspection is loud enough to show up
in its own measurements. So **"is this me?" is the first question of the skill,
not an afterthought** — a fan event caused by an inspection looks identical to one
caused by the creature.
