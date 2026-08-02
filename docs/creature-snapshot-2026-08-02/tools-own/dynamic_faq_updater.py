#!/usr/bin/env python3
"""
dynamic_faq_updater.py
Usage:   python3 -m dynamic_faq_updater "<query>"
Does:    Refreshes an FAQ entry by searching the keyword archive,
         filling knowledge gaps, synthesising a fresh answer,
         and persisting the updated FAQ.
"""

import sys
import json
import subprocess
import shlex
from pathlib import Path

def run_tool(name: str, *args) -> str:
    """Run a tool from /mind/tools/own and capture its stdout."""
    cmd = ["python3", f"/mind/tools/own/{name}"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"[ERROR] Tool {name} failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()

def search_faq(query: str) -> dict:
    """Search the keyword archive for an FAQ entry matching the query."""
    # Use keyword-archive-search – it returns JSON lines of notes.
    out = run_tool("keyword-archive-search", query, "--limit", "5")
    # The tool returns JSONL; take the first matching note whose tags include 'faq'
    for line in out.splitlines():
        try:
            note = json.loads(line)
            tags = note.get("tags", [])
            if "faq" in tags:
                return note
        except json.JSONDecodeError:
            continue
    return {}

def store_faq(query: str, answer: str, source: str = "generated"):
    """Persist the refreshed FAQ entry."""
    # Use keyword-archive-store
    # Ensure a consistent key: `faq:<query>`
    key = f"faq:{query}"
    tags = ["faq"]
    # Store as a JSON object with fields we might need later
    note = json.dumps({
        "question": query,
        "answer": answer,
        "source": source
    })
    run_tool("keyword-archive-store", key, note, "--tags", ",".join(tags))

def fill_gaps(note: dict) -> dict:
    """Pass the note through knowledge_gap_filler to ensure up‑to‑date info."""
    # knowledge_gap_filler expects JSON on stdin describing a single item.
    # We'll feed it the note JSON and capture any enriched output.
    proc = subprocess.run(
        ["python3", "/mind/tools/own/knowledge_gap_filler"],
        input=json.dumps(note),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        # If the filler fails, just return the original note.
        return note
    # The filler may output the same note or an enriched version.
    try:
        enriched = json.loads(proc.stdout.strip())
        return enriched
    except json.JSONDecodeError:
        return note

def synthesize_answer(query: str, context: str) -> str:
    """Run deep_answer_synth to get a fresh answer."""
    # deep_answer_synth expects the question as argument; we pass context via env.
    env = dict(os.environ)
    env["DEEP_ANSWER_CONTEXT"] = context
    result = subprocess.run(
        ["python3", "/mind/tools/own/deep_answer_synth", query],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        print(f"[ERROR] deep_answer_synth failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 -m dynamic_faq_updater \"<query>\"", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1].strip()

    # 1. Look for an existing FAQ entry.
    existing = search_faq(query)

    if existing:
        # 2. Enrich it via knowledge_gap_filler.
        enriched = fill_gaps(existing)
        # 3. Build a context string for synthesis (existing answer + any new data).
        context = enriched.get("answer", "")
        # 4. Generate a fresh answer.
        answer = synthesize_answer(query, context)
    else:
        # No prior entry – start from scratch.
        # Use deep_answer_synth with an empty context.
        answer = synthesize_answer(query, "")

    # 5. Store the refreshed FAQ.
    store_faq(query, answer)

    # 6. Output the refreshed answer for the caller.
    print(answer)

if __name__ == "__main__":
    main()
