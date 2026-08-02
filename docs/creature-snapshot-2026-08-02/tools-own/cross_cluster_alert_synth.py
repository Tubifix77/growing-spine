#!/usr/bin/env python3
"""
cross_cluster_alert_synth.py

Chains:
  knowledge_gap_filler (research) → subagent_ask_helper (risk synthesis) → step-planner-tracker (task insertion)

Usage:
  python3 cross_cluster_alert_synth.py "<topic>"
Example:
  python3 cross_cluster_alert_synth.py "AI ethics"
"""

import json
import subprocess
import sys
import shlex

def run_cmd(cmd, input_data=None):
    """Run a shell command, optionally feeding it stdin, and return its stdout."""
    result = subprocess.run(
        cmd, input=input_data, capture_output=True, text=True, shell=True, check=False
    )
    if result.returncode != 0:
        sys.stderr.write(f"Command failed: {cmd}\\n{result.stderr}\\n")
        return None
    return result.stdout.strip()

def fetch_wake_items(topic):
    """Fetch fresh wake items and filter by the topic (case‑insensitive)."""
    # wake_catchup_fetcher returns a JSON array of items.
    raw = run_cmd("wake_catchup_fetcher.real")
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    filtered = [it for it in items if topic.lower() in it.get("title", "").lower()]
    return filtered

def fill_gaps(item):
    """Run knowledge_gap_filler on a single JSON item."""
    inp = json.dumps(item)
    out = run_cmd("knowledge_gap_filler", input_data=inp)
    return out

def synthesize_risk(item_json):
    """Ask the sub‑agent to highlight emerging risk in the supplied JSON."""
    # Build a prompt that asks the model to list risks in one short sentence.
    prompt = (
        "You are a risk analyst. Given the following research item, "
        "identify any emerging risk or ethical concern in one concise phrase. "
        "If none, output \"No risk\".\n\n"
        f"{item_json}"
    )
    # subagent_ask_helper expects the prompt on stdin.
    out = run_cmd("subagent_ask_helper", input_data=prompt)
    return out

def create_task(risk_phrase, source_title):
    """Insert a new high‑priority task in the persistent planner."""
    # Build a human‑readable task description.
    task_desc = f"Investigate {risk_phrase} (source: {source_title})"
    # step-planner-tracker add "high" "<description>"
    cmd = f'step-planner-tracker add "high" "{task_desc}"'
    _ = run_cmd(cmd)
    return

def main():
    if len(sys.argv) < 2:
        print("Usage: cross_cluster_alert_synth.py \"<topic>\"")
        sys.exit(1)

    topic = sys.argv[1]
    items = fetch_wake_items(topic)

    if not items:
        print(f"No fresh items found for topic '{topic}'.")
        sys.exit(0)

    for item in items:
        # 1) Fill knowledge gaps
        gap_filled = fill_gaps(item)
        if not gap_filled:
            continue

        # 2) Synthesize risk
        risk = synthesize_risk(gap_filled)
        if not risk or risk.lower() == "no risk":
            continue

        # 3) Create task
        create_task(risk, item.get("title", "unknown"))
        print(f"Created task: Investigate {risk}")

if __name__ == "__main__":
    main()
