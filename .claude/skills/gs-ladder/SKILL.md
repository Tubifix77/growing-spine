---
name: gs-ladder
description: Health of the Growing Spine provider ladder — which LLM rungs are serving, walled, or dark, what each returns when its allowance is gone, and whether a replacement account is needed. Fire on "which LLMs are alive", "check the providers", "gs-ladder", FLATLINE or SERIOUS alarms, a rung going quiet, or before adding/retiring any rung.
---

# gs-ladder — which rungs serve, which are dark, and what we still don't know

The ladder is the creature's cognition. When it fails the creature stops
thinking, and the failure is usually silent because degradation is the design.

Output goes to **Tue** as much as to this session: adding or replacing a rung
needs an account and a key, which is his to create.

## Before you start — where the truth lives

- **A provider's own response headers are the only trustworthy source for its
  limits.** Curated free-LLM lists gave this project a `groq: 14400` that was
  wrong by 14×. Docs are a sanity check; lists are for discovery; **headers are
  the fact.**
- **Limits and exhaustion signatures are different facts.** Headers tell you the
  ceiling and say nothing about what the provider returns when you hit it. That
  gap cost 651 cycles in one day.
- Full scars: `CLAUDE.md` §5, ladder entries.

## Tier 1 — mandated checks. Run all of them, every time.

1. `keychain/quota_state.json` per rung: `last_success_at`, `exhausted_at`, and
   the walled/open verdict (`exhausted_at > last_success_at`).
2. FLATLINE hours per rung and the current SERIOUS set, from `~/spine-health.log`.
3. Provider mix over the window from `journal.jsonl` `served_by` records, with
   finish reasons, and **truncation rate per rung** — not just overall.
4. Every rung dark more than 24h: probe it through `provider.call` (never an
   ad-hoc request — the probe must travel the real path) and record the **exact
   error body**, verbatim.
5. Run `classify_error` on every observed error body. **Assert none lands on
   `unknown`.** One that does is the next outage, already loaded.
6. The named-trigger register: for each dark rung, its decision date and what
   resolves it. A hold without a date is inaction wearing caution's clothes.
7. Concentration: what share the top rung carries. A single rung above ~75% means
   the ladder has no depth left, whatever the rung count says.
8. For any rung being considered for retirement: is its key a
   `LEGACY_KEY_ALIAS` in `executive/sandbox.py`, and does **any** tool in
   `tools/own` reference that env var? Disabling a rung withholds its key from
   the container, so retiring one can silently disarm the creature's tools.
9. Whether any rung is truncating without being walled — `finish=length` goes
   through `record_success`, so a rung that truncates every reply looks healthy
   forever and the fatter rung below it is never reached by escalation.
10. Deltas against the previous run of this skill.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **For every rung carrying real traffic, ask what you do not know about it —
> specifically, do you know what it returns when its allowance is gone?** If you
> do not, that is the next outage and its date is whenever the allowance runs
> out. This is not hypothetical: a rung added on 08-17 from perfectly good
> live headers became the workhorse at 77% of traffic, spent a *monthly*
> allowance in two days, and answered with `HTTP 402 {"detail":"Check your
> subscription..."}` — no *quota*, no *billing*, no *exceeded*, no 429 — which
> fell through every branch of the classifier to a default that raised and
> aborted the whole chain. 651 cycles, with four other rungs sitting open.

> **Then ask whether the ladder still has depth, not just entries.** Count the
> rungs that could actually absorb the current load if the top one vanished
> tonight. A six-rung ladder where two are out on allowance, one is retired and
> one is TPM-walled below wake-size requests is a two-rung ladder.

> **And ask what a graceful degradation is hiding.** Everything here is designed
> to fail quietly and carry on, which means correct behaviour and a silent
> outage look identical from the outside. For each rung that fell back, walled,
> or retired in this window, confirm a log line exists naming the cause — a
> degradation that logs nothing is an outage nobody will ever explain.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing about the ladder that no item above would have caught — or say
> plainly that you found none. If it mattered, add it to Tier 1, dated.

## Write the numbers down

Append one record per run to `gs-history/ladder.jsonl` in this repo checkout.
**One record per line.** A skipped run is absent, never a zero.

Keys: `ts`, `run`, `rungs{key:{state,last_success_h,share_pct,trunc_pct}}`,
`serious[]`, `dark_over_24h[]`, `unknown_classifications[]`, `top_rung_pct`,
`depth`, `triggers{key:date}`.

## Standing decisions (Tue's — do not re-litigate)

- **Quality floor over capacity.** No weak model in the ladder; `openrouter/free`
  auto-routing stays rejected.
- **A defunct model is removed the moment it is detected**, then **replaced
  rather than shrinking the ladder**. Prefer a NEW account over a second model
  on one we already hold — two names on one bucket is not added capacity.
- A rung that is out of *allowance* is not defunct. Leave it enabled so it
  returns on its own when the budget resets; that beats a config flag someone
  has to remember.
- **Never dump `config.yaml`.** Grep the one field you need; it holds live keys.
