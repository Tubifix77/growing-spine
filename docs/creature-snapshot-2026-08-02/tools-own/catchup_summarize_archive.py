#!/usr/bin/env python3
"""
tool: catchup_summarize_archive
call: catchup_summarize_archive [optional_topic]
does: Fetch fresh Hacker News items, summarize each via subagent_ask_helper,
      store the summary in the keyword archive, and output a JSON report.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
import shlex

def run_cmd(cmd, input_data=None):
    """Run a shell command, capture stdout, raise on error."""
    result = subprocess.run(
        cmd, input=input_data, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nStderr: {result.stderr}")
    return result.stdout.strip()

def fetch_catchup_items():
    """Return list of items from wake_catchup_fetcher.real as dicts."""
    # wake_catchup_fetcher.real prints a JSON array of items
    cmd = "wake_catchup_fetcher.real"
    out = run_cmd(cmd)
    try:
        items = json.loads(out)
        if not isinstance(items, list):
            raise ValueError("Fetcher did not return a list")
        return items
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from wake_catchup_fetcher.real: {e}")

def summarize_item(item):
    """Summarize a single item using subagent_ask_helper."""
    title = item.get("title", "")
    url = item.get("url", "")
    # Build prompt - ask LLM to summarize the article; if URL is missing, summarize title.
    if url:
        prompt = f"Summarize the following article in 2-3 concise sentences. Provide the main point and any notable detail.\nURL: {url}"
    else:
        prompt = f"Summarize the following headline in 2-3 concise sentences:\n{title}"
    # Use subagent_ask_helper to get the answer
    cmd = f'subagent_ask_helper {shlex.quote(prompt)}'
    try:
        summary = run_cmd(cmd)
    except Exception as e:
        # Fallback: just return the title
        summary = f"(fallback) {title}"
    return summary

def store_summary(keyword, title, url, summary):
    """Store the summary in the keyword archive."""
    # Build a note payload – we'll store title, url, and summary as JSON text
    note = json.dumps({
        "title": title,
        "url": url,
        "summary": summary
    })
    # Use keyword-archive-store
    cmd = f'keyword-archive-store {shlex.quote(keyword)} {shlex.quote(note)} --tags catchup'
    run_cmd(cmd)
    return True

def main():
    # Optional topic argument – we currently ignore it, but keep signature
    topic = sys.argv[1] if len(sys.argv) > 1 else None

    items = fetch_catchup_items()
    if not items:
        print(json.dumps([]))
        return

    reports = []
    for itm in items:
        title = itm.get("title", "Untitled")
        url = itm.get("url", "")
        summary = summarize_item(itm)
        # Store under keyword "catchup" (could be refined with topic)
        store_summary("catchup", title, url, summary)
        reports.append({
            "title": title,
            "url": url,
            "summary": summary
        })

    # Output JSON report for verification
    print(json.dumps(reports, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
