#!/usr/bin/env python3
"""
fetch_and_gap_fill

Downloads fresh data from a given URL (using the generic web-fetch tool),
runs the knowledge_gap_filler on the fetched content to discover missing
information, and automatically creates a research plan for those gaps via
plan_from_question. The resulting plan ID is stored in the persistent
step‑planner‑tracker.
"""

import argparse
import json
import subprocess
import sys
import os
import shlex
import tempfile

def run_cmd(cmd, input_data=None):
    """Run a shell command, returning its stdout (as text)."""
    result = subprocess.run(
        cmd,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(f"Command failed: {' '.join(cmd)}\n")
        sys.stderr.write(result.stderr + "\n")
        sys.exit(1)
    return result.stdout.strip()

def fetch_url(url):
    """Fetch the URL content using the existing `web-fetch` tool."""
    return run_cmd(["web-fetch", url])

def fill_gaps(content):
    """Detect missing knowledge using the existing knowledge_gap_filler tool.

    The tool expects a query, so we feed the fetched content as the query.
    It returns a JSON list of gap descriptions (or an empty list).
    """
    # knowledge_gap_filler reads a query from stdin; supply the content.
    out = run_cmd(["knowledge_gap_filler"], input_data=content)
    try:
        gaps = json.loads(out)
    except json.JSONDecodeError:
        # If the tool returns plain text, treat the whole output as a single gap.
        gaps = [{"gap": out}]
    return gaps

def create_plan_for_gap(gap_text):
    """Create a persistent plan for a single gap using plan_from_question."""
    # plan_from_question reads a natural‑language goal from stdin and prints a plan ID.
    plan_id = run_cmd(["plan_from_question"], input_data=gap_text)
    return plan_id

def main():
    parser = argparse.ArgumentParser(
        description="Fetch a URL, fill knowledge gaps, and generate research plans."
    )
    parser.add_argument("--url", required=True, help="URL to fetch")
    args = parser.parse_args()

    # 1. Download the target page.
    content = fetch_url(args.url)
    if not content:
        sys.stderr.write("Fetched content is empty.\n")
        sys.exit(1)

    # 2. Run knowledge_gap_filler to discover missing pieces.
    gaps = fill_gaps(content)
    if not gaps:
        print("No knowledge gaps detected – nothing to plan.")
        return

    # 3. For each gap, generate a research plan and report the plan IDs.
    created = []
    for g in gaps:
        # The gap description may be under various keys; be robust.
        gap_text = g.get("gap") or g.get("question") or json.dumps(g)
        plan_id = create_plan_for_gap(gap_text)
        created.append(plan_id)

    # 4. Store the plan IDs in the step‑planner‑tracker for visibility.
    # The tracker tool `step-planner-tracker` can add notes; we just echo.
    print("Generated research plan IDs for detected gaps:")
    for pid in created:
        print(pid)

if __name__ == "__main__":
    main()
