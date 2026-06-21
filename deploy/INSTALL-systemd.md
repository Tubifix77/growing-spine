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
- The unit logs to `~/growing-spine.log` and the journal (`journalctl --user -u growing-spine`).
