#!/usr/bin/env python3
# ------------------------------------------------------------
# Tool: archive_enrichment_loop
# Call: archive_enrichment_loop.py "<query>"
# Does: For a given query, gathers existing archive notes,
#       fills knowledge gaps, fetches fresh related items,
#       and stores the enriched content back to the keyword‑archive.
# ------------------------------------------------------------
import subprocess
import sys
import json
import shlex

def run_tool(*cmd):
    """Run a shell tool, capture stdout, ignore non‑zero exit (return empty)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except Exception as e:
        return ""

def main():
    if len(sys.argv) < 2:
        print("Usage: archive_enrichment_loop.py \"<query>\"")
        sys.exit(1)
    query = sys.argv[1]

    # 1. Get existing archive notes
    existing = run_tool("keyword-archive-search", query)
    if not existing:
        existing = "(no existing notes found)"

    # 2. Fill any knowledge gaps for the query
    gap_filled = run_tool("knowledge_gap_filler", query)
    if not gap_filled:
        gap_filled = "(no gaps identified or filler failed)"

    # 3. Pull fresh related items (using the generic wake catcher)
    fresh_items = run_tool("wake_catchup_fetcher")
    if not fresh_items:
        fresh_items = "(no fresh items retrieved)"

    # 4. Compose enriched content
    enriched = (
        "=== ORIGINAL ARCHIVE NOTES ===\\n" + existing + "\\n\\n"
        "=== KNOWLEDGE GAP FILL ===\\n" + gap_filled + "\\n\\n"
        "=== FRESH FETCHED ITEMS ===\\n" + fresh_items
    )

    # 5. Store back to the keyword‑archive with an “enriched” tag
    # keyword-archive-store expects: <keyword> -c "<content>" [-t <tags>]
    store_cmd = ["keyword-archive-store", query, "-c", enriched, "-t", "enriched"]
    store_result = run_tool(*store_cmd)

    # 6. Report outcome
    print("=== ARCHIVE ENRICHMENT COMPLETE ===")
    print(store_result if store_result else "Stored enriched entry.")
    # Optionally, print a short preview
    print("\\n--- Preview of enriched entry (first 300 chars) ---")
    print(enriched[:300] + ("..." if len(enriched) > 300 else ""))

if __name__ == "__main__":
    main()
