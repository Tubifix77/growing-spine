#!/usr/bin/env python3
"""
tool: knowledge_graph_fetcher
does: Fill knowledge‑graph gaps for a keyword by searching the keyword‑archive,
      fetching a Wikipedia summary if missing, and storing the result back
      into the archive (keyword‑archive-store). Designed to be run as:
   
  python knowledge_graph_fetcher.py [--force] <keyword>
"""

import argparse
import json
import os
import sys
import urllib.request
from subprocess import run, PIPE

# Helper to execute subtools as commands
def run_tool(tool_name, *args):
    """Run a tool installed in /mind/tools/own and capture its JSON output."""
    cmd = ["python", f"/mind/tools/own/{tool_name}.py"] + list(args)
    result = run(cmd, stdout=PIPE, stderr=PIPE, text=True)
    if result.returncode != 0:
        print(f"Error running {tool_name}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # Some tools (e.g., fetch) just print plain text; return raw string
        return result.stdout.strip()

def keyword_exists_in_archive(keyword):
    """Check if a note for the keyword already exists in the archive."""
    # Use keyword-archive-search; it returns list of matching notes
    matches = run_tool("keyword-archive-search", keyword)
    return len(matches) > 0

def fetch_wikipedia_summary(keyword):
    """Fetch the summary of the Wikipedia page for the given keyword."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{keyword.replace(' ', '_')}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
            return data.get("summary", "")
    except Exception as e:
        print(f"Failed to fetch Wikipedia summary for {keyword}: {e}", file=sys.stderr)
        return ""

def store_in_archive(keyword, content):
    """Store the given content under the keyword in the keyword archive."""
    # keyword-archive-store expects a note; we can provide tags maybe
    # Using run_tool which expects JSON output; but store tool likely takes args via CLI?
    # Suppose keyword-archive-store.py is a script that takes arguments: keyword, content, maybe tags?
    # We'll construct a simple JSON and pipe? Instead, we can call python -c to write directly?
    # However there is a tool `keyword-archive-store` defined; might accept arguments.
    # For simplicity, use run_tool with arguments.
    # The store tool may expect JSON via stdin; Let's try passing note as argument "content"
    # We'll use run_tool with extra param "content" which may be interpreted accordingly.
    # To avoid complexity, we can directly invoke the store script with needed args.
    store_cmd = ["python", "/mind/tools/own/keyword-archive-store.py", keyword, content]
    result = run(store_cmd, stdout=PIPE, stderr=PIPE, text=True)
    if result.returncode != 0:
        print(f"Error storing archive for {keyword}: {result.stderr}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", help="Keyword to fill knowledge graph for")
    parser.add_argument("--force", action="store_true", help="Force fetch even if present")
    args = parser.parse_args()

    kw = args.keyword
    force = args.force

    if not force and keyword_exists_in_archive(kw):
        print(f"Knowledge already present for '{kw}'. Exiting.")
        return

    # Ensure we have a placeholder note; could create empty first
    # Fetch Wikipedia summary
    summary = fetch_wikipedia_summary(kw)
    if not summary:
        print(f"Could not retrieve summary for '{kw}'.", file=sys.stderr)
        sys.exit(1)

    # Store the summary in the archive
    store_in_archive(kw, summary)
    print(f"Stored Wikipedia summary for '{kw}' in the knowledge archive.")

if __name__ == "__main__":
    main()
