---
name: gs-data
description: Whether the Growing Spine creature's stored knowledge is readable, real, and singular — jsonl parse rates, fabricated feeds, split paths, and the chat channel. Fire on "check its data", "are its notes readable", "gs-data", a JSONL or WIRING alarm, or any suspicion that it is storing or reading non-information.
---

# gs-data — is what it stores readable, real, and in one place?

The creature accumulates knowledge and then reads it back. Three things break
that, and all three are quiet: a writer whose records its own reader cannot
parse, a store full of fabricated content, and the same logical store living at
two paths where each half is invisible to the other.

## Before you start — the two ways this check lies

- **Never cap the sample inside the measurement.** A `_DATA_SAMPLE_LINES = 2000`
  once reported "2000 lines" for a 16,862-line file and pinned the escalation
  rule below its own trigger, making the alarm silent by arithmetic. Whole file,
  every time.
- **Test a fact about the world, not a phrase list.** The mock sensor was caught
  by RFC 2606 (`example.com` can never carry real content), not by hunting the
  title `"Mock News Item"` — a guard that names one exact string is one rename
  away from silent.

Every trap named above is an instance of a scar in `CLAUDE.md` §5 — the
sample cap, the one-exact-string guard, the mechanism-vs-invariant rule, and
the lock that only one writer used. Read them there; they are not restated
here, so a correction there corrects this.

## Tier 1 — mandated checks. Run all of them, every time.

1. Every `.jsonl` under `/mind/data` and `/mind`: line count and parse rate via
   `volume.tools.jsonl_parse_rate`. No sampling.
2. Every store below 100%: name, ratio, **and the tool that writes it**. A parse
   rate is a symptom; the writer is the fault.
3. Fabricated-feed check on the sensor's output — reserved hosts first
   (`is_fabricated_feed`), phrase list only as backstop.
4. WIRING: same-stem files at two or more paths, with sizes and the count of
   tools reading each. Name which half is being written and which is being read.
5. Zero-byte files that something reads.
6. Records that are error text rather than content — the 10% of its tools that
   return an error string as their value feed straight into stores, and an
   archive full of `Error: ...` lines still parses perfectly.
7. **The chat channel**: does `chat.jsonl` show Tue's recent messages, did the
   creature reply, and is every writer reaching it through the lock? Enumerate
   the writers and reach each the way it really does — a test that can only get
   in through the lock can never see someone climbing the window.
8. Size delta per store against the previous run, and total volume growth.
9. Deltas against the previous run of this skill.

## Tier 2 — pointed open inspection. Prose, and it cannot be skipped.

> **Trace one record end to end.** Pick a store, find the tool that wrote its
> most recent record, read that tool's write path, then read the tool that
> consumes it and confirm it can actually parse what was written. Parse rates
> tell you a store is broken; only tracing tells you why. `keyword-archive.jsonl`
> has sat at 0 of 2,618 lines readable by its own writer's reader, across weeks,
> because nobody followed one record through.
>
> **Deliver:** The store named, its writer tool, its reader tool, and whether the reader parses what the writer actually wrote.

> **Then ask what the creature believes is in there.** Read its `think` records
> for claims about its own memory — "I recall", "the archive says", "as noted
> earlier". If it is reasoning from a store that reads back empty or garbled, it
> is building on nothing, and that is far worse than a parse-rate number
> suggests. This is the closest thing we have to measuring whether its knowledge
> actually compounds.
>
> **Deliver:** Three `think` records quoted, each with whether the store backs the claim it makes — or the number of records read and why none made such a claim.

> **And ask whether a store that looks healthy is real.** A file can be
> perfectly parseable and entirely fabricated. Sample actual record content, not
> just its shape: reserved hosts, placeholder answers, records that merely
> restate their input, timestamps that are all from one minute.
>
> **Deliver:** Five sampled records with a real / fabricated verdict on each.

## Tier 3 — the blank pass. Mandatory, and it must be answerable as "none".

> Name one thing about its data that no item above would have caught — or say
> plainly that you found none. If it mattered, add it to Tier 1, dated.

## Write the numbers down

Append one record per run to `gs-history/data.jsonl` in this repo checkout.
**One record per line** — this is the exact fault the creature keeps rebuilding
and we must not hand it a bad example.

Keys: `ts`, `run`, `stores{name:{lines,parse_pct,bytes,writer}}`,
`unreadable[]`, `fabricated[]`, `split_paths[]`, `zero_byte_read[]`,
`chat_last_in`, `chat_last_reply`, `volume_mb`.

## What is not ours to fix

The writers are the creature's tools. Do not edit them. Name the **invariant**
it must hold — *one record per line* — never the mechanism to avoid: told not to
use `jq -n`, it stopped using `jq` and rebuilt the identical fault with a heredoc
36 hours later. And do not restore an emptied store until the cause is known;
a store the creature cleaned deliberately is not a data loss.
