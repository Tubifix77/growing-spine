# Quarantined tests

These four files have been red since shortly after they were written. None
of them is imported or run by anything (only `tests/test_loop_v2.py` is ever
machine-run — see `executive/self_restart.py`'s deploy-self gate). Per
audit finding P3-D2 (`audit/PASS-3-DEAD.md`), they test APIs the codebase no
longer has. Quarantined here rather than deleted, per audit note P3 §3.7:
delete them before anyone widens the deploy-self validator's scope to
`tests/` generally, or a widened validator would brick every restart on
these.

Each file's assertions were orphaned by a real refactor, not a bug:

- **test_keychain.py** — orphaned by `93d3548` ("v0.9.3: strip token
  machinery from quota system — two timestamps only", 2026-06-27). Asserts
  `state["provider_a"]["used"]`; that commit removed the `used` counter
  from the quota schema in favor of two timestamps.

- **test_loop.py** — orphaned by `2c00e09` ("refactor: protected-prompt.md
  + editable-prompt.md replace the-prompt.md", 2026-06-04). Asserts
  `loop.PROTECTED_BLOCK`; that refactor removed the in-module constant in
  favor of the external `protected-prompt.md` file.

- **test_runtime.py** — orphaned by `cd7c108` ("feat: probe-based reset
  detection — sleep 1h then retry real prompt", 2026-06-05). Asserts a
  `reset_at`-per-provider sleep calculation (min of provider reset times,
  floored at 60s); that commit replaced it with a fixed 3600s probe
  (later refined further by `d1d776a` into the current
  `discovered_reset_interval`-based calculation), so the `reset_at` field
  the test builds no longer feeds `sleep_duration_seconds` at all.

- **test_volume.py** — orphaned by `39c1997` ("remove: skills/ stub from
  volume init — unused, dead directory", 2026-06-05). Asserts
  `init_volume` creates a `skills/` directory; that commit deliberately
  removed it as dead.
