#!/usr/bin/env python3
"""
task_backlog_revival
does: Revive stale tasks from memstore by re‑evaluating relevance (via subagent_ask_helper),
      pulling fresh context (via wake_catchup_fetcher), and updating their status in
      step-planner-tracker.  Returns a short report of actions taken.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

MEMSTORE_PATH = "/mind/memstore"          # JSON‑lines file with stored entries
FETCHER_CMD = "wake_catchup_fetcher"      # Existing fetcher tool
SUBAGENT_CMD = "subagent_ask_helper"      # Existing sub‑agent helper
PLANNER_CMD = "step-planner-tracker"      # Existing persistent planner


def load_memstore():
    """Yield each JSON object from the memstore file."""
    if not os.path.isfile(MEMSTORE_PATH):
        return
    with open(MEMSTORE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def is_task(entry):
    """Identify task entries – we consider any key that starts with 'task:'."""
    return isinstance(entry.get("key", ""), str) and entry["key"].startswith("task:")


def task_age_days(entry):
    """Return age of the entry in days (fallback to 0 if timestamp missing)."""
    ts = entry.get("timestamp")
    if isinstance(ts, (int, float)):
        entry_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(ts, str):
        try:
            entry_dt = datetime.fromisoformat(ts.rstrip("Z")).replace(tzinfo=timezone.utc)
        except ValueError:
            return 0
    else:
        return 0
    return (datetime.now(timezone.utc) - entry_dt).days


def reeval_task(task_json):
    """Ask the sub‑agent whether the task is still relevant."""
    prompt = (
        "You are a task‑relevancy reviewer. Answer with a single word "
        "'yes' or 'no'. Is the following task still relevant?\n\n"
        f"Task ID: {task_json['key']}\n"
        f"Description: {task_json.get('value','')}."
    )
    result = subprocess.run(
        [SUBAGENT_CMD, prompt],
        capture_output=True,
        text=True,
        timeout=30,
    )
    answer = result.stdout.strip().lower()
    return answer.startswith("yes")


def fetch_latest_context():
    """Run the existing wake_catchup_fetcher and return its JSON output."""
    result = subprocess.run(
        [FETCHER_CMD],
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        return json.loads(result.stdout)
    except Exception:
        return []  # Gracefully ignore fetch failures


def update_planner(task_id, new_status):
    """Tell step‑planner‑tracker to set the task’s status."""
    subprocess.run(
        [PLANNER_CMD, "update", task_id, f"status={new_status}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    parser = argparse.ArgumentParser(description="Revive stale tasks.")
    parser.add_argument("--age", type=int, default=30,
                        help="Consider tasks older than this many days as stale.")
    args = parser.parse_args()

    stale_tasks = []
    for entry in load_memstore():
        if not is_task(entry):
            continue
        if task_age_days(entry) > args.age:
            stale_tasks.append(entry)

    if not stale_tasks:
        print("✅ No stale tasks found (age > {} days).".format(args.age))
        return

    # Pull fresh context once – it may be useful for many tasks
    fresh_context = fetch_latest_context()

    revived, expired = 0, 0
    for task in stale_tasks:
        task_id = task["key"]
        if reeval_task(task):
            # Keep the task alive – optionally enrich with fresh context
            # (Here we just note that we fetched it; real enrichment can be added later.)
            update_planner(task_id, "pending")
            revived += 1
        else:
            update_planner(task_id, "expired")
            expired += 1

    print(f"🔄 Processed {len(stale_tasks)} stale tasks:")
    print(f"   – revived : {revived}")
    print(f"   – expired : {expired}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(f"❌ task_backlog_revival failed: {e}\\n")
        sys.exit(1)
