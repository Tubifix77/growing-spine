#!/usr/bin/env python3
"""
tool: cross_source_alert_synthesizer
does: Compose wake_catchup_fetcher, knowledge_gap_filler, and step-planner-tracker.
      Fetches items from a feed, enriches each with missing knowledge,
      and creates a persistent alert task for each item.
"""

import argparse, json, subprocess, sys, os, textwrap

def run_cmd(cmd, input_data=None):
    """Run a command, optionally feeding JSON via stdin, and capture stdout."""
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Command {' '.join(cmd)} failed: {e.stderr}\\n")
        sys.exit(1)

def fetch_items(feed_url):
    """Use wake_catchup_fetcher.real to fetch fresh items from the feed."""
    return json.loads(run_cmd(["wake_catchup_fetcher.real", "--feed", feed_url]))

def enrich_item(item):
    """Run knowledge_gap_filler on a single item (JSON via stdin)."""
    enriched = run_cmd(["knowledge_gap_filler"], input_data=json.dumps(item))
    return json.loads(enriched)

def create_alert(item):
    """Create an alert task via step-planner-tracker."""
    title = f"Alert: {item.get('title','<no title>')}"
    # Use a nicely formatted JSON description for the task body
    description = json.dumps(item, indent=2, ensure_ascii=False)
    # step-planner-tracker add "<title>" "<description>"
    task_id = run_cmd(["step-planner-tracker", "add", title, description])
    return task_id

def main():
    parser = argparse.ArgumentParser(
        description="Cross‑source alert synthesizer – fetch, enrich, and create alert tasks."
    )
    parser.add_argument("--feed", required=True, help="RSS or JSON feed URL")
    args = parser.parse_args()

    # 1. Fetch fresh items
    items = fetch_items(args.feed)
    if not items:
        sys.stderr.write("No new items fetched from the feed.\\n")
        sys.exit(0)

    # 2. Process each item
    created = []
    for idx, item in enumerate(items, 1):
        enriched = enrich_item(item)
        task_id = create_alert(enriched)
        created.append(task_id)
        print(f"[{idx}/{len(items)}] Created alert task ID: {task_id}")

    # 3. Summary
    print("\\nSummary: created", len(created), "alert tasks.")
    sys.exit(0)

if __name__ == "__main__":
    main()
