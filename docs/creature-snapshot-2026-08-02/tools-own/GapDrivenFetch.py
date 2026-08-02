#!/usr/bin/env python3
"""
does: Fill a knowledge gap for a query, fetch missing info (via web-fetch),
      and store it in the keyword‑archive.
"""

import json
import subprocess
import sys
import shlex
from pathlib import Path

def run_tool(name: str, *args, input_data: str = None):
    """Run a tool from /mind/tools/own and return its stdout as text."""
    cmd = [name] + list(args)
    result = subprocess.run(
        cmd,
        input=input_data.encode() if input_data is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Tool {name} failed (exit {result.returncode}). "
            f"stderr: {result.stderr.strip()}"
        )
    return result.stdout.strip()

def main():
    if len(sys.argv) != 2:
        print("Usage: GapDrivenFetch.py \"<query>\"")
        sys.exit(1)

    query = sys.argv[1].strip()
    # --------------------------------------------------------------
    # 1. Ask knowledge_gap_filler whether we already have info.
    # --------------------------------------------------------------
    # knowledge_gap_filler expects a JSON object on stdin.
    filler_input = json.dumps({"query": query})
    try:
        filler_output = run_tool(
            "/mind/tools/own/knowledge_gap_filler",
            input_data=filler_input,
        )
    except Exception as e:
        print(f"Error invoking knowledge_gap_filler: {e}", file=sys.stderr)
        sys.exit(1)

    # knowledge_gap_filler returns JSON like:
    # {"gap_found": true, "search_term": "John Tayler"}
    try:
        filler_json = json.loads(filler_output)
    except json.JSONDecodeError:
        print("Invalid JSON from knowledge_gap_filler", file=sys.stderr)
        sys.exit(1)

    if not filler_json.get("gap_found", False):
        # Nothing to fetch – the knowledge already exists.
        print(f"No knowledge gap for '{query}'. Nothing to do.")
        sys.exit(0)

    search_term = filler_json.get("search_term", query)

    # --------------------------------------------------------------
    # 2. Fetch fresh information (prefer Wikipedia)
    # --------------------------------------------------------------
    # Build a Wikipedia search URL; fallback to a generic web search if needed.
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{shlex.quote(search_term)}"
    try:
        fetched = run_tool("web-fetch", wiki_url)
    except Exception as e:
        # If Wikipedia fails, try a generic web search via duckduckgo.
        fallback_url = f"https://duckduckgo.com/html/?q={shlex.quote(search_term)}"
        try:
            fetched = run_tool("web-fetch", fallback_url)
        except Exception as e2:
            print(f"Both Wikipedia and fallback fetch failed: {e2}", file=sys.stderr)
            sys.exit(1)

    # --------------------------------------------------------------
    # 3. Store the fetched snippet in the keyword‑archive
    # --------------------------------------------------------------
    # Create a short excerpt (first 1000 chars) to keep the archive tidy.
    snippet = fetched[:1000]

    try:
        run_tool(
            "/mind/tools/own/keyword-archive-store",
            query,
            "--tags",
            "gap_filled",
            input_data=snippet,
        )
    except Exception as e:
        print(f"Failed to store in keyword‑archive: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Knowledge gap for '{query}' filled and stored (search term: {search_term}).")

if __name__ == "__main__":
    main()
