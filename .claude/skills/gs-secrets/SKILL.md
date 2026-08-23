---
name: gs-secrets
description: Check whether Growing Spine provider keys have leaked out of config into the creature's tools, stores, journal, workspace or transcripts — without ever printing a key. Fire on "check the keys", "gs-secrets", after any session that read config.yaml, before making the repo or a report public, or when a key is rotated.
---

# gs-secrets — has a key escaped, and which are still pending rotation?

The creature holds live provider keys in its container environment by design, and
it writes files freely. So a key reaching one of its tools, its archives, or its
journal is a plausible accident rather than a paranoid one.

## The rule that governs this whole skill

**Never print, echo, or dump a key.** Not in a command, not in output, not
redacted-but-adjacent. This check reports **locations and counts only** — file,
line number, and which key *name* matched. Never the value.

Two related standing rules: **never `cat config.yaml`** — grep the single field
you need — and never commit it. Five keys are already pending rotation because
they reached transcripts this way.

The standing rules behind this — never commit `config.yaml`, grep one field
rather than dumping it, never delete the creature's `.bak` or junk files —
live in `CLAUDE.md` §1, §2.5 and the rotation entry in §8. Pointers only here.

## Tier 1 — mandated checks. Run all of them, every time.

1. **The rotation register.** Which keys are pending rotation, since when, and
   why. Report the age in days. This is Tue's action, not ours, so it must be
   restated every run until it clears.
2. `config.yaml` is gitignored and untracked — confirm both, and confirm
   `git log --all -- config.yaml` is empty.
3. **Which keys the body actually holds**: the env var *names* present in the
   container, and which config rung each corresponds to. Names only.
4. **Leak scan by shape, not by value.** Search the creature's territory for
   provider-key *patterns* — `sk-`, `gsk_`, `AIza`, `csk-`, long
   high-entropy base64/hex runs — and report file plus line count only. Cover:
   `tools/own`, `tools/attic`, the journal, `chat.jsonl`, every store under
   `/mind/data`, `/workspace`, and any `.bak`.
5. **Leak scan by value, safely.** For each key, take a short hash of the value
   and search for the value without ever emitting it: grep with the value passed
   via a variable or `--file=-` on stdin, and print only match counts. If a match
   is found, report the file and line — never the line's content.
6. **Its own tools that reference a key env var**: which tools read which
   `*_API_KEY`, and whether any writes that value anywhere.
7. **Legacy aliases**: `sandbox.LEGACY_KEY_ALIASES` — which disabled-rung keys
   would vanish from the container, and whether any tool depends on one.
8. Whether any key appears in a file that is tracked by git, in any branch.
9. Deltas against the previous run of this skill.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Ask how a key could plausibly get out of the container this week, given what
> the creature has actually been doing.** It writes tools, it archives text, it
> pipes command output into files, and one of its own wrappers has already
> converted a provider error into stdout text that then became a tool file. A
> key printed in a debug line, an `env` dump captured into an archive, or an
> error body containing an `Authorization` header would each land somewhere
> permanent and silent. Look for the shape of that accident, not just for the
> key.

> **Then look at what we have published.** Session reports and artifacts are
> written from this system's internals; the repo is public. Check the most recent
> report and any newly committed file for a key, a full `config.yaml`, or a path
> that discloses more than it needs to. Anything sent outward may be cached or
> indexed even if deleted afterwards.

> **And confirm the boundary still holds in the other direction**: does anything
> in the creature's territory contain a credential for a service we did not give
> it? A key it obtained itself, from a fetched page or a model reply, would be
> both a leak and a capability nobody granted.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one way a secret could leave this system that no item above would have
> caught — or say plainly that you found none. If it mattered, add it to Tier 1,
> dated.

## Write the numbers down

Append one record per run to `~/gs-history/secrets.jsonl` on the laptop.
**One record per line.** Record **no key material, not even truncated** — only
names, counts, paths, and dates.

Keys: `ts`, `run`, `pending_rotation[{name,since,days}]`,
`config_untracked`, `env_names_in_body[]`, `pattern_hits[{file,count}]`,
`value_hits[{file,line,key_name}]`, `tools_reading_keys[]`,
`tracked_by_git[]`, `foreign_credentials[]`.

## If you find one

Say which key, where, and how old the exposure is — then stop. Rotation is
Tue's to perform, and **do not** attempt to clean the creature's files: deleting
its junk or `.bak` files is forbidden, and a rewrite of its history would be an
intervention in its world. The remedy for a leaked key is a new key, not a
scrubbed file.
