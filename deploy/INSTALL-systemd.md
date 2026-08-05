# Installing the systemd supervisor (the immortal-brain layer)

The executive (brain) is kept alive by a systemd **user** service. If it dies it
is auto-restarted; it also starts on boot. This is the layer that makes
self-restart (deploy-self) safe.

## Install (on the laptop, as the creature's user)
```bash
mkdir -p ~/.config/systemd/user
cp deploy/growing-spine.service ~/.config/systemd/user/
loginctl enable-linger "$USER"          # run even when not logged in / at boot
systemctl --user daemon-reload
systemctl --user enable --now growing-spine.service
```

## Verify
```bash
systemctl --user status growing-spine.service     # active (running)
# prove resurrection:
kill -9 $(systemctl --user show growing-spine.service -p MainPID --value)
sleep 8 && systemctl --user is-active growing-spine.service   # active again
```

## Notes
- Do NOT also launch `python3 main.py` by hand or via the old desktop entry — that
  creates an unsupervised second brain. Use `./restart.sh` (delegates to systemd).
- The unit logs to the systemd journal. Read it with `journalctl --user -u growing-spine`, and scope by time with `--since "6 hours ago"` or by the current boot with `-b`. (Before 2026-07-05 it appended to `~/growing-spine.log`, which stripped per-line timestamps; that file is now frozen history.)

## Daily health probe (spine-health.timer)

`scripts/spine_health.py` runs a daily behavioral-invariant probe + stub
janitor (sensor-mock regression check, stale-fallback census, age-out of
placeholder stubs >3d to the attic). Install as a user timer:

```bash
mkdir -p ~/.config/systemd/user
cp deploy/spine-health.service ~/.config/systemd/user/
cp deploy/spine-health.timer   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now spine-health.timer
systemctl --user list-timers spine-health.timer   # verify next run
```

Output is appended to `~/spine-health.log` (one line per run). The launcher
`start-growing-spine.sh` also arms this timer, so a fresh install that has run
the icon once will have it active.

## Hourly flatline tripwire (spine-flatline.timer)

The one unit that would have caught the 55-hour google_gemma outage of
2026-08-02. Runs `check_flatline()` only, every hour at :07. **Install this on
any fresh clone** — until 2026-08-06 these units existed by hand on one laptop
only, so a fresh install had no tripwire at all.

```
cp deploy/spine-flatline.service ~/.config/systemd/user/
cp deploy/spine-flatline.timer   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now spine-flatline.timer
systemctl --user list-timers spine-flatline.timer
```

Both this and the daily probe **exit non-zero when a traffic-carrying rung has
gone silent**, so the unit shows up in `systemctl --user --failed` rather than
the finding sitting unread in `~/spine-health.log`. A quiet *low* rung (the
OpenRouter floor, unreached because the rungs above it are serving) is expected
and exits 0. Check either with:

```
systemctl --user --failed
grep SERIOUS ~/spine-health.log
```

## Weekly OpenRouter tier diff (openrouter-tier.timer)

The free shelf rotates; this flags a configured rung whose model id has vanished
(it caught the 2026-07-19 purge). Reports only — never edits config.

```
cp deploy/openrouter-tier.service ~/.config/systemd/user/
cp deploy/openrouter-tier.timer   ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now openrouter-tier.timer
```

## Observer dashboard (spine-observer.service)

The GUI dashboard runs as a user service too -- hand-launching it (setsid/
nohup) proved fragile (it died when the launching shell returned) and
sometimes left an unmapped window. As a service it survives SSH teardown and
reboots and restarts on crash.

```bash
cp deploy/spine-observer.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user start spine-observer.service      # start now
# optional: systemctl --user enable spine-observer.service  # also at login
```

Needs `DISPLAY=:0` (set in the unit). The launcher `start-growing-spine.sh`
starts this service. Restart the GUI after an observer.py change with:
`systemctl --user restart spine-observer.service`.

## Embedding gate dependency (v0.12)

The idea gate's semantic layer needs Model2Vec (numpy-only static
embeddings, ~30MB model, no torch):

```bash
pip3 install --user --break-system-packages model2vec
```

The model (`minishlab/potion-base-8M`) downloads from HuggingFace on first
use and is cached in `~/.cache/huggingface`. If the package or model is
unavailable, the gate degrades automatically to the lexical fallback and
prints one `[embed-gate] UNAVAILABLE` notice -- nothing breaks.
