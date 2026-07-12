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

# --- 3. Observer GUI: single instance, reliable detach + window mapping ---
# Bare 'nohup ... &' left an unmapped 10x10 window under xfwm4 once; the
# reliable form is setsid + stdin from /dev/null + disown (observer.py itself
# handles the deferred showMaximized since d8a131a).
pkill -f "observer.py" 2>/dev/null
sleep 1
DISPLAY=:0 setsid python3 observer.py >> /home/boas/observer.log 2>&1 < /dev/null &
disown 2>/dev/null
echo $! > /home/boas/observer.pid
sleep 3

# --- 4. Report ---
BRAIN=$(pgrep -f "/home/boas/growing-spine/main.py" | grep -v pgrep | head -1)
OBS=$(pgrep -f "python3 observer.py" | grep -v pgrep | head -1)
echo "Growing Spine ready -- brain PID ${BRAIN:-none} (systemd), observer PID ${OBS:-none}"
if [ -z "$OBS" ]; then
    echo "WARNING: observer did not come up -- check /home/boas/observer.log"
fi
