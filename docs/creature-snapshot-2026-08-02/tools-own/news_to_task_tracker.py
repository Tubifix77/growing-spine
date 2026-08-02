#!/usr/bin/env python3
"""
news_to_task_tracker
does: Pull latest news via wake_catchup_fetcher, extract actionable items with subagent_ask_helper,
      and create tracked tasks in step-planner-tracker.
"""

import argparse
import json
import subprocess
import sys
from shlex import quote

def run_cmd(cmd, capture_output=True):
    """Run a shell command, raise on error, return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture_output, text=True, check=False
    )
    if result.returncode != 0:
        sys.stderr.write(f"Error running command: {cmd}\\n")
        sys.stderr.write(result.stderr or "")
        sys.exit(result.returncode)
    return result.stdout.strip()

def fetch_news(topic: str, limit: int):
    """Fetch fresh news items using wake_catchup_fetcher.real."""
    cmd = f"wake_catchup_fetcher.real --topic {quote(topic)} --limit {limit}"
    out = run_cmd(cmd)
    # The fetcher returns a JSON list, each item has at least 'title' and 'url'
    try:
        items = json.loads(out)
        if not isinstance(items, list):
            raise ValueError
        return items
    except Exception:
        sys.stderr.write("Failed to parse news JSON. Output was:\\n")
        sys.stderr.write(out + "\\n")
        sys.exit(1)

def extract_task(title: str):
    """Ask subagent_ask_helper to turn a headline into an actionable task."""
    # The subagent_ask_helper expects a prompt on stdin and prints the answer.
    prompt = (
        f"Given the news headline below, produce ONE short actionable task description "
        f"(imperative mood, no extra commentary).\\n\\nHeadline: {title}\\n\\nTask:"
    )
    cmd = "subagent_ask_helper"
    result = subprocess.run(
        cmd, input=prompt, shell=True, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        sys.stderr.write("subagent_ask_helper failed.\\n")
        sys.stderr.write(result.stderr + "\\n")
        sys.exit(result.returncode)
    return result.stdout.strip()

def create_plan(task_desc: str, source_title: str, source_url: str):
    """Create a new plan with step-planner-tracker."""
    # Build a JSON payload for the planner: name and steps list
    plan_name = f"NewsTask:{source_title[:50].replace(':','').strip()}"
    payload = json.dumps({"name": plan_name, "steps": [task_desc]})
    # step-planner-tracker expects a JSON string via STDIN and outputs the plan ID
    cmd = "step-planner-tracker add"
    result = subprocess.run(
        cmd,
        input=payload,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write("step-planner-tracker add failed.\\n")
        sys.stderr.write(result.stderr + "\\n")
        sys.exit(result.returncode)
    plan_id = result.stdout.strip()
    # Store a reference to the source URL in the plan metadata (optional)
    # The planner supports a "metadata" field; we use a separate command if needed.
    # For simplicity, we just print the association.
    return plan_id

def main():
    parser = argparse.ArgumentParser(description="Create tasks from news headlines.")
    parser.add_argument("--topic", required=True, help="News topic to fetch (e.g., tech)")
    parser.add_argument(
        "--limit", type=int, default=5, help="Maximum number of news items to process"
    )
    args = parser.parse_args()

    news_items = fetch_news(args.topic, args.limit)
    if not news_items:
        print("No new items found.")
        return

    created = []
    for item in news_items:
        title = item.get("title")
        url = item.get("url", "")
        if not title:
            continue
        task = extract_task(title)
        plan_id = create_plan(task, title, url)
        created.append((plan_id, title))

    # Output summary
    for pid, t in created:
        print(f"Created plan {pid} for headline: {t}")

if __name__ == "__main__":
    main()
