#!/usr/bin/env python3
"""
CrossClusterSignalRouter
Integrates:
  - subagent_ask_helper (LLM relevance check)
  - wake_catchup_fetcher (fetch latest context)
  - step-planner-tracker (create high‑priority task)

Usage:
  python -m cross_cluster_signal_router "<alert text>"
"""

import sys, json, subprocess, shlex, os, tempfile

def run_cmd(cmd, input_data=None):
    """Run a shell command, capture stdout, raise on error."""
    result = subprocess.run(
        cmd, input=input_data, capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nSTDERR:{result.stderr}")
    return result.stdout.strip()

def ask_llm(question):
    """Ask the sub‑agent LLM via subagent_ask_helper."""
    # subagent_ask_helper expects the question on STDIN
    return run_cmd("subagent_ask_helper", input_data=question)

def fetch_latest_items():
    """Fetch fresh Hacker News items via wake_catchup_fetcher."""
    out = run_cmd("wake_catchup_fetcher")
    # The fetcher returns a JSON array; parse it
    try:
        items = json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse wake_catchup_fetcher output")
    return items

def summarise_items(items):
    """Summarise a list of items via the LLM."""
    # Build a simple bullet list string
    txt = "\n".join(f"- {i.get('title','')} ({i.get('url','')})" for i in items)
    prompt = (
        "Summarise the following Hacker News items in a short paragraph:\n"
        + txt
    )
    return ask_llm(prompt)

def create_task(alert, summary):
    """Create a high‑priority task via step‑planner‑tracker."""
    goal = f"Investigate alert: {alert}"
    # First step is the summary; further steps can be added later by the cousin
    steps = f"Summary: {summary}"
    # Use the planner CLI: step-planner-tracker add <goal> <steps>
    cmd = f"step-planner-tracker add {shlex.quote(goal)} {shlex.quote(steps)}"
    out = run_cmd(cmd)
    # The planner prints the new plan ID; just return the output
    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m cross_cluster_signal_router \"<alert>\"")
        sys.exit(1)
    alert = sys.argv[1]

    # 1. Relevance check
    relevance_prompt = (
        f"Is the following alert relevant and worth creating a high‑priority task?\n"
        f"Alert: {alert}\n"
        f"Answer with exactly YES or NO."
    )
    relevance = ask_llm(relevance_prompt).strip().upper()
    if relevance != "YES":
        print("Alert deemed not relevant; no task created.")
        sys.exit(0)

    # 2. Fetch context
    items = fetch_latest_items()
    if not items:
        print("No fresh items fetched; creating task without extra context.")
        summary = "No additional context available."
    else:
        # 3. Summarise
        summary = summarise_items(items)

    # 4. Create task
    result = create_task(alert, summary)
    print(f"Task created. Planner output:\n{result}")

if __name__ == "__main__":
    main()
