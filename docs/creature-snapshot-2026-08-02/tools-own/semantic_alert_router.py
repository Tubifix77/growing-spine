#!/usr/bin/env python3
"""
tool: semantic_alert_router
call: python /mind/tools/own/semantic_alert_router.py --source <url>
does: Fetch alerts, enrich each with keyword‑archive context, and create a high‑priority task in step‑planner‑tracker.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

# ----------------------------------------------------------------------
# Helper utilities – wrappers around existing tools
# ----------------------------------------------------------------------
def run_tool(tool_cmd: List[str]) -> str:
    """Run a tool and return its stdout (decoded). Abort on error."""
    result = subprocess.run(tool_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(f"Error running {' '.join(tool_cmd)}:\n{result.stderr}\n")
        sys.exit(1)
    return result.stdout.strip()

def fetch_feed(url: str) -> List[Dict[str, Any]]:
    """Retrieve a JSON feed of alerts using the built‑in web-fetch tool."""
    out = run_tool(["web-fetch", url])
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        sys.stderr.write(f"Failed to parse JSON from {url}\n")
        sys.exit(1)
    if not isinstance(data, list):
        sys.stderr.write("Expected a JSON array of alerts.\n")
        sys.exit(1)
    return data

def search_archive(query: str, top_n: int = 3) -> List[Dict[str, Any]]:
    """Search the keyword‑archive and return the top‑n notes."""
    out = run_tool(["keyword-archive-search", "--top", str(top_n), query])
    try:
        notes = json.loads(out)
    except json.JSONDecodeError:
        # some tools output raw text; fallback to empty list
        notes = []
    return notes

def fetch_wikipedia_summary(term: str) -> str:
    """Fetch a Wikipedia summary via web-fetch (fallback when archive empty)."""
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{term.replace(' ', '_')}"
    out = run_tool(["web-fetch", wiki_url])
    try:
        data = json.loads(out)
        return data.get("extract", "")
    except json.JSONDecodeError:
        return ""

def create_task(alert: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
    """Create a high‑priority task in the planner and return its ID."""
    task_payload = {
        "title": alert.get("title", "Untitled alert"),
        "source_url": alert.get("url", ""),
        "description": alert.get("description", ""),
        "priority": "high",
        "context": context,
    }
    # step‑planner‑tracker expects a JSON on stdin for `add-task`
    proc = subprocess.run(
        ["step-planner-tracker", "add-task", "--json"],
        input=json.dumps(task_payload),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(f"Failed to add task: {proc.stderr}\n")
        sys.exit(1)
    # The tool prints the created task ID
    return proc.stdout.strip()

# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic Alert Router")
    parser.add_argument("--source", required=True, help="URL of the JSON alerts feed")
    args = parser.parse_args()

    alerts = fetch_feed(args.source)

    created_ids = []
    for alert in alerts:
        title = alert.get("title") or alert.get("summary") or ""
        if not title:
            continue  # skip malformed alerts

        # 1️⃣ Enrich via archive search
        archive_hits = search_archive(title)

        # 2️⃣ If archive is empty, fetch a Wikipedia summary as fallback
        if not archive_hits:
            wiki_summary = fetch_wikipedia_summary(title)
            if wiki_summary:
                archive_hits = [{"source": "wikipedia", "content": wiki_summary}]

        # 3️⃣ Create a high‑priority task
        task_id = create_task(alert, archive_hits)
        created_ids.append(task_id)

    # Output created task IDs for visibility
    print(json.dumps({"created_task_ids": created_ids}, indent=2))

if __name__ == "__main__":
    main()
