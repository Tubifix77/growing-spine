#!/usr/bin/env python3
"""
News Driven Research

This tool composes existing utilities to turn a fresh news item into a
research plan.

Steps:
  1. Run `wake_catchup_fetcher.real` → fetches fresh Hacker News items as JSON.
  2. Pick the first item (title + URL) and turn its title into a research question.
  3. Call `plan_from_question "<question>"` → creates a persistent plan and prints its ID.
  4. Print the plan ID together with the source title/URL.
"""

import json
import subprocess
import sys
import os
import random

def run_cmd(cmd, capture_stdout=True):
    """Run a shell command, raise on error, return stdout if requested."""
    result = subprocess.run(
        cmd,
        shell=True,
        check=True,
        stdout=subprocess.PIPE if capture_stdout else None,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip() if capture_stdout else ""

def fetch_news():
    """Fetch fresh Hacker News items via the real fetcher."""
    # The fetcher writes a JSON array to stdout.
    output = run_cmd("wake_catchup_fetcher.real")
    try:
        items = json.loads(output)
    except json.JSONDecodeError:
        sys.exit("Failed to parse JSON from wake_catchup_fetcher.real")
    if not isinstance(items, list) or len(items) == 0:
        sys.exit("No news items returned by wake_catchup_fetcher")
    return items

def pick_item(items):
    """Pick a news item. Currently we use the first item (most recent)."""
    # Could be randomized: random.choice(items)
    return items[0]

def create_plan(question):
    """Create a persistent plan via plan_from_question."""
    # plan_from_question prints the plan id on stdout.
    plan_id = run_cmd(f'plan_from_question "{question}"')
    return plan_id

def main():
    # 1️⃣ Fetch fresh news
    items = fetch_news()
    item = pick_item(items)

    title = item.get("title", "").strip()
    url = item.get("url", "").strip()
    if not title:
        sys.exit("Selected news item has no title")

    # 2️⃣ Form a research question from the title
    question = f"Research the topic: {title}"
    # Optionally include the URL for context
    if url:
        question += f" (source: {url})"

    # 3️⃣ Generate the plan
    plan_id = create_plan(question)

    # 4️⃣ Output result
    print(f"Created plan ID: {plan_id}")
    print(f"Source title: {title}")
    if url:
        print(f"Source URL: {url}")

if __name__ == "__main__":
    main()
