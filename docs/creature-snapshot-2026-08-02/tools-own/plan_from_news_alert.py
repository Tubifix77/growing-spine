#!/usr/bin/env python3
"""
Fetch breaking news headlines via wake_catchup_fetcher, turn each headline
into a concrete question for plan_from_question, generate a persistent plan,
and store the plan ID in the keyword archive for fast lookup.
"""

import subprocess, json, sys, os

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def main():
    # Fetch fresh items (the fetcher returns JSON array)
    fetcher_cmd = "python3 /mind/tools/own/wake_catchup_fetcher.py"
    # Actually wake_catchup_fetcher is a script? There is wake_catchup_fetcher.real.
    # Use the real version that stores state.
    raw = run_cmd("python3 /mind/tools/own/wake_catchup_fetcher.real")
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        print("Failed to parse fetcher output", file=sys.stderr)
        sys.exit(1)

    archive_store = "keyword-archive-store"
    for item in items:
        headline = item.get("title", "Untitled")
        # Create a question for planning
        question = f"Create a plan for the news item titled \"{headline}\""
        # Generate the plan; plan_from_question prints the plan ID on stdout
        plan_id = run_cmd(f"python3 /mind/tools/own/plan_from_question.py \"{question}\"")
        # Store the plan ID in the archive under a keyword derived from the headline
        # Simplify: store under the keyword "news-plans" with tags headline
        store_cmd = f"python3 /mind/tools/own/keyword-archive-store.py --keyword \"news-plans\" --tags \"{headline}\" --note \"PlanID:{plan_id}\""
        run_cmd(store_cmd)

if __name__ == "__main__":
    main()
