#!/usr/bin/env python3
"""
does: Evaluate an incoming alert, ask a sub‑agent if it is relevant,
      optionally fetch supporting data, and create or update a high‑priority
      task in step‑planner‑tracker.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import shlex
import tempfile

def run_cmd(cmd, input_data=None):
    """Run a shell command, capture stdout, raise on error."""
    result = subprocess.run(
        cmd, input=input_data, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed: {result.stderr.strip()}")
    return result.stdout.strip()

def ask_subagent(alert: str) -> dict:
    """
    Use subagent_ask_helper to decide relevance.
    The sub‑agent is prompted to output a JSON object with fields:
        relevant (bool)
        needs_fetch (bool)
        fetch_url (str, optional)
        task_title (str)
        task_detail (str)
    """
    prompt = (
        "You are a security‑oriented analyst. Given the alert below, decide if it is "
        "relevant for immediate investigation. Respond ONLY with a JSON object "
        "containing the following keys:\n"
        "- relevant (true/false)\n"
        "- needs_fetch (true/false)\n"
        "- fetch_url (string, optional, only if needs_fetch is true)\n"
        "- task_title (short title for a planner task)\n"
        "- task_detail (detailed description of the task)\n"
        "\nAlert:\n"
        f"{alert}\n"
    )
    # subagent_ask_helper expects the prompt on STDIN and returns only the answer.
    out = run_cmd(["subagent_ask_helper"], input_data=prompt)
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Sub‑agent did not return valid JSON: {out}") from e

def fetch_support(url: str) -> str:
    """Fetch supporting data (HTML/text) for the given URL using wake_catchup_fetcher."""
    # wake_catchup_fetcher normally returns an array of items; we can reuse its
    # lower‑level fetcher: fetch_url.
    out = run_cmd(["fetch_url", url])
    return out

def create_high_priority_task(title: str, detail: str) -> str:
    """Create a high‑priority task via step‑planner‑tracker and return the plan ID."""
    cmd = [
        "step-planner-tracker",
        "add",
        "--priority", "high",
        "--title", title,
        "--detail", detail
    ]
    out = run_cmd(cmd)
    # The tracker typically prints the new plan ID on the last line.
    plan_id = out.splitlines()[-1].strip()
    return plan_id

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m cross_cluster_signal_router \"<alert>\"")
        sys.exit(1)

    alert = " ".join(sys.argv[1:])

    # 1. Ask the sub‑agent whether the alert matters
    answer = ask_subagent(alert)

    if not answer.get("relevant", False):
        result = {
            "alert": alert,
            "relevant": False,
            "task_created": None,
            "plan_id": None,
            "note": "Sub‑agent judged alert not relevant"
        }
        print(json.dumps(result))
        return

    # 2. If extra context is required, fetch it
    fetched_data = ""
    if answer.get("needs_fetch", False):
        fetch_url = answer.get("fetch_url")
        if fetch_url:
            fetched_data = fetch_support(fetch_url)

    # 3. Build the task description (append fetched data if any)
    title = answer.get("task_title", "Untitled Alert Task")
    detail = answer.get("task_detail", "")
    if fetched_data:
        # Truncate to a reasonable size to avoid giant planner entries
        snippet = fetched_data[:2000]
        detail = f"{detail}\n\n--- Fetched Context ({fetch_url}) ---\n{snippet}"

    # 4. Create the planner task
    plan_id = create_high_priority_task(title, detail)

    # 5. Return a JSON summary
    result = {
        "alert": alert,
        "relevant": True,
        "task_created": True,
        "plan_id": plan_id,
        "title": title,
        "detail_snippet": detail[:300] + ("..." if len(detail) > 300 else "")
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
