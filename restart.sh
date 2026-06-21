#!/usr/bin/env bash
# restart.sh -- the canonical, safe way to (re)start the Growing Spine creature.
#
# WHY THIS EXISTS: restarting by hand repeatedly went wrong this way --
#   * launching via `setsid bash -c 'exec python3 ... main.py'` leaves a
#     transient bash whose argv CONTAINS "main.py", so pgrep briefly counts two;
#   * detached launches died when bundled into a multi-command SSH call;
#   * checking the instance count too fast caught that transient as a "race".
# main.py does NOT fork (verified: single asyncio process, no subprocess/
# multiprocessing/threads-as-procs), so after a clean launch there must be
# EXACTLY ONE matching process. This script enforces that and aborts loudly
# otherwise. Run it instead of invoking python3 main.py by hand.
#
# Usage:  cd ~/growing-spine && ./restart.sh

set -u
REPO="$HOME/growing-spine"
LOG="$HOME/growing-spine.log"
PIDFILE="$REPO/creature.pid"
# match the running interpreter line, but NOT this script and NOT the grep
PAT='python3 -u main\.py'

count() { pgrep -f "$PAT" | grep -v "restart.sh" | wc -l | tr -d ' '; }

echo "[restart] stopping any running instance..."
pkill -9 -f "$PAT" 2>/dev/null
# wait up to ~6s for it to reach zero
for i in $(seq 1 12); do
  [ "$(count)" = "0" ] && break
  sleep 0.5
done
if [ "$(count)" != "0" ]; then
  echo "[restart] ABORT: could not stop existing instance(s): $(pgrep -f "$PAT" | tr '\n' ' ')"
  exit 1
fi
echo "[restart] stopped. launching detached..."

# Launch WITHOUT a bash -c wrapper (so no transient false-match), fully detached,
# stdin/out/err severed from this shell so it survives the session closing.
cd "$REPO" || { echo "[restart] ABORT: no repo at $REPO"; exit 1; }
setsid python3 -u main.py >> "$LOG" 2>&1 < /dev/null &
disown 2>/dev/null || true

# settle, then verify EXACTLY ONE (no fork, so this is deterministic)
sleep 4
n="$(count)"
if [ "$n" = "1" ]; then
  pid="$(pgrep -f "$PAT" | grep -v restart.sh | head -1)"
  echo "$pid" > "$PIDFILE"
  echo "[restart] RESTART OK (pid $pid)"
  echo "[restart] recent log:"
  tail -3 "$LOG" | sed 's/^/    /'
  exit 0
elif [ "$n" = "0" ]; then
  echo "[restart] ABORT: process did not start. last log:"
  tail -8 "$LOG" | sed 's/^/    /'
  exit 1
else
  echo "[restart] ABORT: $n instances after launch (expected 1) -- a real double-launch:"
  pgrep -f "$PAT" | grep -v restart.sh | tr '\n' ' '
  echo; echo "[restart] killing all and bailing so you can investigate."
  pkill -9 -f "$PAT" 2>/dev/null
  exit 1
fi
