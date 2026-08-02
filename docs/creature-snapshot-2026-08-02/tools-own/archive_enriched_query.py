#!/usr/bin/env python3
"""
does: Enrich a raw search term via subagent_ask_helper and perform a keyword‑archive‑search.
       The tool prints the refined query and the top matching archive entries.
"""

import sys
import subprocess
import shlex
import json

def run_subagent(prompt: str) -> str:
    """Ask subagent_ask_helper for a refined query. Return empty string on failure."""
    try:
        # subagent_ask_helper expects the prompt as a single argument
        result = subprocess.run(
            ["subagent_ask_helper", prompt],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return result.stdout.strip()
    except Exception as e:
        # If the sub‑agent fails, fall back to empty string
        return ""

def run_archive_search(query: str) -> str:
    """Run keyword-archive-search on the given query and return its stdout."""
    try:
        result = subprocess.run(
            ["keyword-archive-search", query],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[archive search error: {e}]"

def main():
    if len(sys.argv) < 2:
        print("Usage: archive_enriched_query.py <raw-search-term>")
        sys.exit(1)

    raw_query = " ".join(sys.argv[1:]).strip()
    # Prompt the sub‑agent to produce a richer phrase
    prompt = (
        f"Refine the following search term into a concise, descriptive phrase that "
        f"captures likely relevant context for an archive search. Return only the refined phrase. "
        f"Original term: \"{raw_query}\""
    )
    refined = run_subagent(prompt)

    if not refined:
        # Sub‑agent failed – fall back to the raw query
        refined = raw_query
        fallback = True
    else:
        fallback = False

    # Perform archive search on the refined term
    search_output = run_archive_search(refined)

    # Display results
    print(f"Raw query:    {raw_query}")
    print(f"Refined query:{' (fallback)' if fallback else ''} {refined}")
    print("\n--- Archive Search Results ---")
    if search_output:
        print(search_output)
    else:
        print("[no results]")

if __name__ == "__main__":
    main()
