#!/bin/bash
# Start the Growing Spine creature + observer GUI together.
# The creature (main.py) runs forever, sleeping through quota windows and
# respawning its container as needed. Safe to run repeatedly: it restarts
# whatever is already running.
# Deployed on the laptop at ~/start-growing-spine.sh (launched by the desktop
# entry ~/Skrivebord/growing-spine.desktop). This repo copy is for reference.
cd /home/boas/growing-spine || exit 1

# --- Creature (executive loop) ---
pkill -f "python3 -u main.py" 2>/dev/null
sleep 2
nohup python3 -u main.py >> /home/boas/growing-spine.log 2>&1 &
echo $! > /home/boas/creature.pid

# --- Observer GUI (needs the X display) ---
pkill -f "observer.py" 2>/dev/null
sleep 1
DISPLAY=:0 nohup python3 observer.py >> /home/boas/observer.log 2>&1 &
echo $! > /home/boas/observer.pid

echo "Growing Spine started -- creature PID $(cat /home/boas/creature.pid 2>/dev/null), observer PID $(cat /home/boas/observer.pid 2>/dev/null)"
