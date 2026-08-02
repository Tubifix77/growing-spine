tool: keyword_planner
call: keyword_planner <keyword>
does: Generate a plan from relevant keyword‑archive notes for a given search term
#!/usr/bin/env python3
"""
keyword_planner.py – Bridge the keyword archive and the step planner.

Usage:
    python keyword_planner.py "<keyword>"

The script:
    1. Searches the keyword‑archive for the given keyword (via the existing
       `keyword-archive-search` tool) and retrieves the top N matching notes.
    2. Turns each note into a short task description.
    3. Creates a persistent plan using `step-planner-tracker add` with those
       tasks as ordered steps.
    4. Prints the plan ID and the generated steps so the caller can see the
       result immediately.
"""

import sys
import json
import subprocess
from pathlib import Path

def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a command, capture stdout/stderr, raise on error."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command {' '.join(cmd)} failed (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return result

def search_archive(keyword: str, top_n: int = 3) -> list[dict]:
    """
    Use the existing `keyword-archive-search` tool to fetch matching notes.
    The tool returns JSON lines – each line is a note dict.
    """
    cmd = ["keyword-archive-search", keyword, str(top_n)]
    result = run_cmd(cmd)
    notes = []
    for line in result.stdout.strip().splitlines():
        try:
            notes.append(json.loads(line))
        except json.JSONDecodeError:
            # Skip malformed lines – they are not critical for plan creation
            continue
    return notes

def build_tasks_from_notes(notes: list[dict]) -> list[str]:
    """
    Convert archive notes into concise task strings.
    Preference order for description:
        1. `title` field if present.
        2. `summary` field.
        3. Full note as JSON (fallback).
    """
    tasks = []
    for note in notes:
        if "title" in note:
            task = note["title"]
        elif "summary" in note:
            task = note["summary"]
        else:
            task = json.dumps(note)
        # Trim whitespace and limit length for readability
        task = " ".join(task.split())
        if len(task) > 200:
            task = task[:197] + "..."
        tasks.append(task)
    return tasks

def create_plan(keyword: str, tasks: list[str]) -> str:
    """
    Call the step‑planner‑tracker to create a new plan.
    The planner expects a JSON payload:
        {"goal": "<keyword>", "steps": ["...","..."]}

    It returns the plan ID on stdout.
    """
    plan_payload = {
        "goal": f"Research & act on “{keyword}”",
        "steps": tasks,
    }
    # Write payload to a temporary file because step-planner-tracker reads from stdin
    tmp_file = Path("/tmp/keyword_plan_payload.json")
    tmp_file.write_text(json.dumps(plan_payload))

    cmd = ["step-planner-tracker", "add", "--input", str(tmp_file)]
    result = run_cmd(cmd)
    plan_id = result.stdout.strip()
    return plan_id

def main():
    if len(sys.argv) != 2:
        print("Usage: python keyword_planner.py \"<keyword>\"", file=sys.stderr)
        sys.exit(1)

    keyword = sys.argv[1]

    # 1️⃣ Search the archive
    notes = search_archive(keyword)

    if not notes:
        print(f"No matching notes found for keyword: {keyword}", file=sys.stderr)
        sys.exit(1)

    # 2️⃣ Build task list
    tasks = build_tasks_from_notes(notes)

    # 3️⃣ Create the plan
    plan_id = create_plan(keyword, tasks)

    # 4️⃣ Show result
    print(f"Plan ID: {plan_id}")
    print("Generated steps:")
    for i, step in enumerate(tasks, start=1):
        print(f"  {i}. {step}")

if __name__ == "__main__":
    main()
