#!/usr/bin/env python3
"""
cross_source_alert.py – Proactive alert generator

Monitors new items from wake_catchup_fetcher, filters by a topic,
detects knowledge gaps with knowledge_gap_filler, composes a concise
alert via subagent_ask_helper, and stores the result in the
keyword‑archive.

Usage:
  python3 cross_source_alert.py --topic "<topic>"
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def run_tool(cmd: list[str]) -> str:
    """Run another tool and return its stdout (or raise)."""
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            f"Error running {' '.join(cmd)}: exit {e.returncode}\\n"
            f"stderr: {e.stderr}\\n"
        )
        raise

def fetch_new_items() -> list[dict]:
    """Call wake_catchup_fetcher.real and parse its JSON output."""
    out = run_tool(["wake_catchup_fetcher.real"])
    try:
        items = json.loads(out)
        # Expect a list of dicts like {"title":..., "url":..., "tags":...}
        if not isinstance(items, list):
            raise ValueError("Fetcher did not return a list")
        return items
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Failed to decode JSON from fetcher: {e}\\n")
        raise

def filter_items_by_topic(items: list[dict], topic: str) -> list[dict]:
    """Keep items whose title or tags contain the topic (case‑insensitive)."""
    lowered = topic.lower()
    filtered = []
    for it in items:
        title = it.get("title", "").lower()
        tags = " ".join(it.get("tags", []))
        if lowered in title or lowered in tags.lower():
            filtered.append(it)
    return filtered

def fill_knowledge_gap(item: dict) -> str:
    """
    Run knowledge_gap_filler on the item's title; the tool prints a short
    description of the missing sub‑topics (or an empty string if none).
    """
    title = item.get("title", "")
    # knowledge_gap_filler expects a query string; we give the title.
    return run_tool(["knowledge_gap_filler", title])

def compose_alert(topic: str, item: dict, gap: str) -> str:
    """
    Use subagent_ask_helper to generate a concise alert.
    Prompt format:
      "You are a concise alert generator. Summarise the new article
       titled '<title>' (URL <url>) about <topic>. The following
       knowledge gaps were identified: <gap>. Produce a 2‑sentence alert."
    """
    prompt = (
        f"You are a concise alert generator. Summarise the new article "
        f"titled '{item.get('title', '')}' (URL {item.get('url', '')}) about "
        f"{topic}. The following knowledge gaps were identified: {gap or 'none'}. "
        f"Produce a short (max 2 sentences) alert."
    )
    return run_tool(["subagent_ask_helper", prompt])

def store_alert(topic: str, alert_text: str, source_item: dict) -> dict:
    """Store the alert in the keyword‑archive and return the stored JSON line."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    entry = {
        "keyword": f"alert:{topic}",
        "content": alert_text,
        "source_title": source_item.get("title", ""),
        "source_url": source_item.get("url", ""),
        "timestamp": timestamp,
    }
    # keyword-archive-store expects: keyword content [--tags tag1,tag2]
    # We'll pass the JSON string as the content.
    json_content = json.dumps(entry, ensure_ascii=False)
    run_tool([
        "keyword-archive-store",
        f"alert:{topic}",
        json_content,
    ])
    return entry

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a proactive alert for a topic from fresh items."
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Topic to monitor (e.g., 'home router').",
    )
    args = parser.parse_args()

    try:
        items = fetch_new_items()
        filtered = filter_items_by_topic(items, args.topic)

        if not filtered:
            sys.stderr.write(f"No new items for topic '{args.topic}'.\\n")
            return 0

        # Process each filtered item – we stop after the first successful alert
        for item in filtered:
            gap = fill_knowledge_gap(item)
            alert = compose_alert(args.topic, item, gap)
            stored = store_alert(args.topic, alert, item)

            # Print the stored entry for visibility / debugging
            print(json.dumps(stored, ensure_ascii=False))
            # Only one alert per run is enough
            break

        return 0
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"cross_source_alert failed: {exc}\\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
