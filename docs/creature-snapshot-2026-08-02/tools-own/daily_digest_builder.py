#!/usr/bin/env python3
"""
daily_digest_builder.py
Build a daily digest by fetching fresh Hacker News items for the given date,
summarising each via subagent_ask_helper, and archiving the result.

Usage:
    python3 daily_digest_builder.py [--date DATE]

DATE can be:
    - "today" (default)
    - "yesterday"
    - an explicit YYYY-MM-DD string
The script will:
    1. Call wake_catchup_fetcher (real) to retrieve items for that date.
    2. Summarise each item's title (and optionally its URL) using subagent_ask_helper.
    3. Assemble a JSON digest containing:
        { "date": "YYYY-MM-DD", "items": [ {"title":..., "url":..., "summary":...}, ... ] }
    4. Store the digest in the keyword‑archive under key
       "daily-digest-YYYY-MM-DD" using keyword-archive-store.
    5. Print the archive key for verification.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

# ---- Helper utilities -------------------------------------------------

def run_cmd(cmd: list) -> str:
    """Run a subprocess command, capture stdout, raise on error."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()

def fetch_items(date_str: str):
    """
    Use the real wake_catchup_fetcher to fetch items for the requested date.
    The fetcher returns a JSON array of objects with at least `title` and `url`.
    """
    # The fetcher expects a date argument; we pass it via environment variable.
    env = os.environ.copy()
    env["WAKE_FETCH_DATE"] = date_str
    # The fetcher script prints a JSON array on stdout.
    out = run_cmd(["python3", "/mind/tools/own/wake_catchup_fetcher.real"])
    try:
        items = json.loads(out)
        if not isinstance(items, list):
            raise ValueError("Fetcher did not return a list")
        return items
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to decode fetcher output: {e}")

def summarize_item(title: str, url: str) -> str:
    """
    Ask subagent_ask_helper to produce a concise 1‑2 sentence summary.
    The prompt is crafted to keep the answer short.
    """
    prompt = (
        f"Summarise the following news item in one short sentence. "
        f"Title: \"{title}\" URL: {url}"
    )
    # subagent_ask_helper prints only the answer.
    out = run_cmd(["subagent_ask_helper", prompt])
    return out.strip()

def store_digest(date_str: str, digest: dict):
    """
    Store the digest JSON in the keyword‑archive using keyword-archive-store.
    The key format is `daily-digest-YYYY-MM-DD`.
    """
    key = f"daily-digest-{date_str}"
    # Write digest to a temporary file first.
    tmp_path = f"/tmp/digest-{date_str}.json"
    with open(tmp_path, "w") as f:
        json.dump(digest, f, indent=2)
    # Call the archiver: keyword-archive-store <key> <file>
    run_cmd(["keyword-archive-store", key, tmp_path])
    # Clean up temp file.
    os.remove(tmp_path)
    return key

def resolve_date(arg_date: str) -> str:
    """Convert various date specifications to YYYY‑MM‑DD."""
    if not arg_date or arg_date == "today":
        return datetime.utcnow().strftime("%Y-%m-%d")
    if arg_date == "yesterday":
        return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    # Assume user gave a proper ISO date; validate quickly.
    try:
        datetime.strptime(arg_date, "%Y-%m-%d")
        return arg_date
    except ValueError:
        raise argparse.ArgumentTypeError("Date must be YYYY-MM-DD, 'today' or 'yesterday'.")

# ---- Main workflow -----------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build a daily Hacker News digest.")
    parser.add_argument("--date", default="today", help="Date for the digest (today|yesterday|YYYY-MM-DD)")
    args = parser.parse_args()

    date_str = resolve_date(args.date)
    print(f"[daily_digest_builder] Building digest for {date_str} ...", file=sys.stderr)

    # 1. Fetch fresh items for the date.
    try:
        items = fetch_items(date_str)
    except Exception as e:
        print(f"[daily_digest_builder] ERROR fetching items: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Summarise each item.
    digest_items = []
    for itm in items:
        title = itm.get("title", "")
        url = itm.get("url", "")
        if not title:
            continue
        try:
            summary = summarize_item(title, url)
        except Exception as e:
            summary = f"(failed to summarize: {e})"
        digest_items.append({"title": title, "url": url, "summary": summary})

    # 3. Assemble the digest.
    digest = {"date": date_str, "items": digest_items}

    # 4. Store in the archive.
    try:
        key = store_digest(date_str, digest)
        print(f"[daily_digest_builder] Digest stored under key: {key}")
    except Exception as e:
        print(f"[daily_digest_builder] ERROR storing digest: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
