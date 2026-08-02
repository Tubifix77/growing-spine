#!/usr/bin/env python3
"""
tool: catchup_memory_archiver
call: catchup_memory_archiver
does: Fetch fresh news items via wake_catchup_fetcher and archive each into the keyword-archive under the keyword "news".
"""

import subprocess
import json
import sys

def run_tool(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running {cmd}: {e.stderr}", file=sys.stderr)
        return None

def main():
    print("Fetching fresh news items...")
    # Use wake_catchup_fetcher.real to ensure we get new items
    news_json = run_tool(["wake_catchup_fetcher.real"])
    
    if not news_json:
        print("No new news items found or error fetching.")
        return

    try:
        items = json.loads(news_json)
    except json.JSONDecodeError:
        print("Failed to decode news JSON.")
        return

    if not items:
        print("No new items to archive.")
        return

    print(f"Found {len(items)} new items. Archiving...")
    
    count = 0
    for item in items:
        title = item.get('title', 'No Title')
        url = item.get('url', 'No URL')
        
        # Format the content for the archive
        content = f"Title: {title}\nURL: {url}"
        
        # Store in keyword-archive under 'news'
        # Usage: keyword-archive-store <keyword> <text> [tags...]
        # We use a list for the command to handle spaces in titles
        store_cmd = ["keyword-archive-store", "news", content, "catchup", "automated"]
        
        if run_tool(store_cmd):
            count += 1

    print(f"Successfully archived {count} items to the 'news' category.")

if __name__ == "__main__":
    main()
