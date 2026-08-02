#!/usr/bin/env python3
"""
Tool: critical_path_alert
does: Detect breaking news for a topic, fill missing knowledge, synthesize a concise alert via LLM, and archive the alert.
Usage: critical_path_alert.py --topic <topic>
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime

# Helper to run a sub‑tool and capture its stdout (or raise)
def run_tool(tool_cmd: list) -> str:
    result = subprocess.run(tool_cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(f"Error running {' '.join(tool_cmd)}:\n{result.stderr}\n")
        raise RuntimeError(f"Tool failed: {' '.join(tool_cmd)}")
    return result.stdout.strip()

def fetch_breaking_news(topic: str):
    """Use wake_catchup_fetcher to fetch fresh items filtered by the topic."""
    # wake_catchup_fetcher returns a JSON array of items {title,url,tags}
    raw = run_tool(['wake_catchup_fetcher', '--topic', topic])
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        sys.stderr.write(f"Failed to parse JSON from wake_catchup_fetcher: {raw}\n")
        items = []
    return items

def fill_gaps(item):
    """Run knowledge_gap_filler on the article URL, returning any gap description."""
    # knowledge_gap_filler expects a URL argument and prints a JSON description of gaps
    raw = run_tool(['knowledge_gap_filler', '--url', item['url']])
    try:
        gaps = json.loads(raw)
    except json.JSONDecodeError:
        gaps = {}
    return gaps

def synthesize_alert(topic: str, item, gaps):
    """Ask subagent_ask_helper to craft a concise alert."""
    prompt = (
        f"Topic: {topic}\n"
        f"Title: {item['title']}\n"
        f"URL: {item['url']}\n"
        f"Gaps (if any): {json.dumps(gaps)}\n"
        "Create a short (≤2 sentences) alert describing why this is breaking news for the given topic. "
        "If no gaps were found, just summarise the news item briefly."
    )
    # subagent_ask_helper reads the prompt from stdin and outputs only the answer
    result = subprocess.run(
        ['subagent_ask_helper'],
        input=prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(f"subagent_ask_helper failed: {result.stderr}\n")
        raise RuntimeError("LLM generation failed")
    return result.stdout.strip()

def archive_alert(topic: str, alert_text: str, source_item):
    """Persist the alert in the keyword archive."""
    # Use a deterministic keyword so alerts are discoverable
    keyword = f"critical-alert-{topic}"
    # Build a JSON line for the archive
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "topic": topic,
        "title": source_item['title'],
        "url": source_item['url'],
        "alert": alert_text,
    }
    # Store via keyword-archive-store
    json_line = json.dumps(entry)
    run_tool([
        'keyword-archive-store',
        '--keyword', keyword,
        '--json', json_line,
        '--tags', f"alert,{topic}"
    ])

def main():
    parser = argparse.ArgumentParser(description="Create an alert for breaking news.")
    parser.add_argument('--topic', required=True, help='Topic to monitor, e.g. "cybersecurity"')
    args = parser.parse_args()

    items = fetch_breaking_news(args.topic)
    if not items:
        print(f"No fresh items for topic '{args.topic}'.")
        return

    for item in items:
        gaps = fill_gaps(item)
        alert = synthesize_alert(args.topic, item, gaps)
        archive_alert(args.topic, alert, item)
        print(f"Archived alert for: {item['title']}")

if __name__ == "__main__":
    main()
