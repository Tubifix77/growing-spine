#!/usr/bin/env bash
# restart.sh -- canonical (re)start of the Growing Spine creature.
#
# As of v0.7 the executive (brain) is supervised by a systemd USER service
# (~/.config/systemd/user/growing-spine.service, Restart=always). systemd is the
# immortal-brain layer: if main.py dies it is auto-restarted; it also starts on
# boot (linger enabled). So a "restart" is just asking systemd to restart it --
# which is atomic and cannot leave a double-brain or an orphan.
#
# Do NOT launch `python3 main.py` by hand anymore; that creates an unsupervised
# process alongside the systemd one. Use this script (or `systemctl --user
# restart growing-spine`).
#
# Usage:  ./restart.sh

set -u
SVC="growing-spine.service"

if systemctl --user list-unit-files "$SVC" >/dev/null 2>&1 && \
   systemctl --user cat "$SVC" >/dev/null 2>&1; then
  echo "[restart] restarting via systemd user service..."
  systemctl --user restart "$SVC"
  sleep 4
  state="$(systemctl --user is-active "$SVC")"
  pid="$(systemctl --user show "$SVC" -p MainPID --value)"
  if [ "$state" = "active" ] && [ -n "$pid" ] && [ "$pid" != "0" ]; then
    echo "[restart] RESTART OK (pid $pid, systemd-supervised)"
    journalctl --user -u growing-spine -n 3 --no-pager -o short-iso 2>/dev/null | sed 's/^/    /'
    exit 0
  fi
  echo "[restart] ABORT: service not active after restart (state=$state). status:"
  systemctl --user status "$SVC" --no-pager 2>&1 | head -12
  exit 1
else
  echo "[restart] systemd service not installed; cannot supervise."
  echo "[restart] install it with:"
  echo "    systemctl --user enable --now growing-spine.service"
  echo "[restart] (unit lives at ~/.config/systemd/user/growing-spine.service)"
  exit 1
fi
