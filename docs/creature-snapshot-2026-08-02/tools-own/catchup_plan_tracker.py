#!/usr/bin/env python3
"""
catchup_plan_tracker
====================

Does: Fetch fresh news items for a given topic using `wake_catchup_fetcher`,
      then turn each item into a persistent plan via `step-planner-tracker`.
"""

import json
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd: list[str]) -> str:
    """Run a command, raise on error, and return its stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()

def fetch_news(topic: str) -> list[dict]:
    """
    Use the existing fetcher to get fresh items.
    The fetcher writes a JSON array to stdout:
        [{ "title": "...", "url": "...", "tags": [...] }, ...]
    """
    # The fetcher can filter by topic via an env‑var or argument; we expose it.
    # The real fetcher accepts a positional argument `topic`.
    out = run_cmd(["wake_catchup_fetcher.real", topic])
    try:
        items = json.loads(out)
        if not isinstance(items, list):
            raise ValueError("Fetcher did not return a list")
        return items
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse fetcher output: {e}")

def create_plan(item: dict) -> str:
    """
    Create a plan for a single news item.
    The planner (`step-planner-tracker`) accepts:
        step-planner-tracker add "<goal>"
    and returns the new plan id on stdout.
    """
    title = item.get("title", "Untitled")
    url   = item.get("url", "")
    # Build a short, actionable goal for the planner.
    goal = f"Investigate news: {title}. Source: {url}"
    plan_id = run_cmd(["step-planner-tracker", "add", goal])
    return plan_id

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: catchup_plan_tracker.py <topic>")
        sys.exit(1)

    topic = sys.argv[1]
    try:
        news_items = fetch_news(topic)
    except Exception as e:
        print(f"[catchup_plan_tracker] Error fetching news for '{topic}': {e}")
        sys.exit(1)

    if not news_items:
        print(f"[catchup_plan_tracker] No new items for topic '{topic}'.")
        sys.exit(0)

    created = []
    for item in news_items:
        try:
            plan_id = create_plan(item)
            created.append((plan_id, item.get("title", "")))
        except Exception as e:
            print(f"[catchup_plan_tracker] Failed to create plan for item '{item.get('title','?')}': {e}")

    # Summarise the result for the cousin
    print("=== Catchup Plan Tracker Result ===")
    for pid, title in created:
        print(f"Plan ID: {pid}  |  News: {title}")

    # Remember the list of created plan IDs for later cycles (optional)
    if created:
        ids = [pid for pid, _ in created]
        # Store under a predictable key so the cousin can retrieve later.
        remember_key = f"catchup_plans:{topic}"
        # `remember` is a built‑in command; we call it via subprocess.
        subprocess.run(["remember", remember_key, json.dumps(ids)], check=True)

if __name__ == "__main__":
    main()
