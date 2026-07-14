#!/bin/bash
# Growing Spine launcher (desktop icon target).
# Starts everything needed, idempotently, without ever creating a second brain.
#
# The brain (main.py) is a systemd user service -- we defer to it, never
# launch main.py directly (that caused a two-brain bug: different command
# strings, pkill couldn't match the systemd one).
cd /home/boas/growing-spine || exit 1

# --- 1. Brain: systemd, idempotent ---
if systemctl --user is-active --quiet growing-spine; then
    echo "Brain already running (systemd)."
else
    echo "Brain not running -- starting via systemd."
    systemctl --user start growing-spine
fi

# --- 2. Daily health probe timer (sensor/staleness/stub-janitor) ---
systemctl --user start spine-health.timer 2>/dev/null && echo "Health timer armed."

# --- 3. Observer GUI: systemd user service ---
# The dashboard is a service (like the brain) so it survives SSH-session
# teardown and reboots, and restarts on crash. Hand-launching with
# setsid/nohup proved fragile (died when the launching shell returned).
systemctl --user start spine-observer.service 2>/dev/null && echo "Observer service started."
sleep 2

# --- 4. Report ---
BRAIN=$(pgrep -f "/home/boas/growing-spine/main.py" | grep -v pgrep | head -1)
OBS=$(pgrep -f "observer.py" | grep -v pgrep | head -1)
echo "Growing Spine ready -- brain PID ${BRAIN:-none} (systemd), observer PID ${OBS:-none}"
if [ -z "$OBS" ]; then
    echo "WARNING: observer did not come up -- check /home/boas/observer.log"
fi
