#!/usr/bin/env python3
"""
amiga_title_collector.py

Collects classic Amiga game titles:
  • Searches the keyword‑archive for the keyword "Amiga"
  • Extracts any URLs stored with those notes
  • Downloads each URL (via web-fetch)
  • Adds a step to the persistent planner so the next run is scheduled

Usage:
  python amiga_title_collector.py [--category CATEGORY]

If --category is provided the tool also tags the planner entry with that category.
"""

import json
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd: list[str]) -> str:
    """Run a command, raise on failure, return stdout stripped."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()

def search_amiga_urls() -> list[str]:
    """Search the keyword‑archive for “Amiga” and return a list of URLs."""
    # keyword-archive-search returns JSON lines, each line is a note.
    out = run_cmd(["keyword-archive-search", "Amiga"])
    urls = []
    for line in out.splitlines():
        try:
            note = json.loads(line)
            # We store URLs under the key "url" (the archive tools use any JSON fields)
            if isinstance(note, dict) and "url" in note:
                urls.append(note["url"])
        except json.JSONDecodeError:
            continue
    return urls

def fetch_url(url: str) -> bool:
    """Fetch the URL with web-fetch; return True on success."""
    try:
        run_cmd(["web-fetch", url])
        return True
    except subprocess.CalledProcessError:
        return False

def add_planner_step(category: str | None, url: str):
    """Create a planner entry that records the fetch and schedules the next run."""
    # step-planner-tracker expects: add <goal> <description>
    # We create a goal called "Amiga Title Collection" and a step that mentions the URL.
    goal = "Amiga Title Collection"
    description = f"Fetched {url}"
    if category:
        description += f" (category={category})"
    # The tool `step-planner-tracker` uses sub‑commands; we call the "add" action.
    subprocess.run(
        ["step-planner-tracker", "add", goal, description],
        check=False,
    )

def main():
    # Parse optional --category flag
    category = None
    args = sys.argv[1:]
    if "--category" in args:
        idx = args.index("--category")
        if idx + 1 < len(args):
            category = args[idx + 1]
            # Remove them so any future parsing sees only positional args
            del args[idx:idx + 2]

    # 1️⃣ Search archive
    urls = search_amiga_urls()
    if not urls:
        print("No Amiga URLs found in the keyword‑archive.")
        sys.exit(0)

    # 2️⃣ Fetch each URL
    fetched = []
    for u in urls:
        ok = fetch_url(u)
        if ok:
            fetched.append(u)
            print(f"✅ Fetched: {u}")
        else:
            print(f"⚠️ Failed to fetch: {u}")

    # 3️⃣ Record steps in the planner
    for u in fetched:
        add_planner_step(category, u)

    # 4️⃣ Schedule the next run (the planner can handle recurring steps)
    # We add a generic “run again in 7 days” step.
    recurrence_desc = "Run AmigaTitleCollector again (weekly)."
    if category:
        recurrence_desc += f" (category={category})"
    subprocess.run(
        ["step-planner-tracker", "add", "Amiga Title Collection", recurrence_desc],
        check=False,
    )
    print("🗓️ Planner updated – next collection scheduled.")
    
if __name__ == "__main__":
    main()
