#!/usr/bin/env python3
"""
tool: robust_archive_search
call: robust_archive_search <query>
does: Wraps keyword-archive-search with automatic retries; on repeated failures it falls back to
       knowledge_gap_filler to expand the query and retries the search, recording each attempt
       in step-planner-tracker.
"""

import argparse
import subprocess
import sys
import time
import json
import os

# configuration
MAX_RETRIES = int(os.getenv("ROBUST_SEARCH_MAX_RETRIES", "3"))
BACKOFF_FACTOR = 1.5  # exponential back‑off multiplier

def run_cmd(cmd, capture_output=True):
    """Run a shell command, returning (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def log_attempt(tool, query, attempt, status):
    """
    Record an attempt in step‑planner‑tracker.
    The tracker expects: step-planner-tracker add-attempt <tool> <query> <attempt> <status>
    """
    # Build a simple JSON payload for the tracker; if the tracker has a different CLI,
    # this call will simply fail silently which is acceptable for logging.
    cmd = f'step-planner-tracker add-attempt {tool} "{query}" {attempt} "{status}"'
    rc, out, err = run_cmd(cmd, capture_output=False)
    # ignore failures – logging must never break the main flow
    return rc

def search_archive(query):
    """Run keyword-archive-search for the given query."""
    rc, out, err = run_cmd(f'keyword-archive-search "{query}"')
    return rc, out, err

def expand_query(original_query):
    """Invoke knowledge_gap_filler to get an expanded query."""
    rc, out, err = run_cmd(f'knowledge_gap_filler "{original_query}"')
    if rc != 0 or not out:
        # fallback: just return the original query if filler fails
        return original_query
    # knowledge_gap_filler returns a JSON with an "expanded_query" field,
    # but it may also just echo a plain string.
    try:
        data = json.loads(out)
        expanded = data.get("expanded_query") or data.get("query") or out
    except json.JSONDecodeError:
        expanded = out
    return expanded.strip()

def main():
    parser = argparse.ArgumentParser(description="Robust archive search with fallback")
    parser.add_argument("query", help="Search query")
    args = parser.parse_args()
    original_query = args.query

    attempt = 1
    current_query = original_query
    while attempt <= MAX_RETRIES:
        rc, out, err = search_archive(current_query)
        # Log the attempt regardless of success/failure
        status = "success" if rc == 0 and out else "failure"
        log_attempt("robust_archive_search", current_query, attempt, status)

        if rc == 0 and out:
            # Got a result – print it and exit
            print(out)
            sys.exit(0)

        # If this was the first failure, try to expand the query
        if attempt == 1:
            current_query = expand_query(original_query)

        # Back‑off before next retry
        time.sleep(BACKOFF_FACTOR ** (attempt - 1))
        attempt += 1

    # All attempts exhausted – report error
    print(f"robust_archive_search: all {MAX_RETRIES} attempts failed for query '{original_query}'", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
