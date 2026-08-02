#!/usr/bin/env python3
"""
plan_from_question_fixer.py
Wraps knowledge_gap_filler around plan_from_question, ensuring missing context is filled.
Does: Generates a persistent plan for a question, fills knowledge gaps for each step,
      and returns the final plan ID.
"""

import sys
import json
import subprocess
from pathlib import Path

def run_cmd(cmd: list) -> str:
    """Run a command, raise on error, return stdout stripped."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout.strip()

def plan_from_question(question: str) -> str:
    """Call the existing plan_from_question tool and return the plan ID."""
    out = run_cmd(["plan_from_question", question])
    # The tool prints the plan ID (or JSON with it); we accept either.
    try:
        data = json.loads(out)
        return data.get("plan_id") or out
    except json.JSONDecodeError:
        return out

def knowledge_gap_filler(step_json: str) -> bool:
    """
    Run knowledge_gap_filler on a single step (JSON string).
    Returns True if a gap was filled (i.e., a new note was added to the archive).
    """
    # knowledge_gap_filler reads a JSON object from stdin.
    result = subprocess.run(
        ["knowledge_gap_filler"],
        input=step_json,
        capture_output=True,
        text=True,
    )
    # The filler prints a JSON with a `filled` boolean flag.
    try:
        resp = json.loads(result.stdout)
        return resp.get("filled", False)
    except json.JSONDecodeError:
        return False

def get_plan_steps(plan_id: str) -> list:
    """Retrieve ordered steps for a plan via step-planner-tracker."""
    out = run_cmd(["step-planner-tracker", "list", "--plan", plan_id, "--json"])
    data = json.loads(out)
    # Expect {"steps": [{...}, ...]}
    return data.get("steps", [])

def main():
    if len(sys.argv) != 2:
        print("Usage: plan_from_question_fixer.py <question>", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # 1️⃣ Generate an initial plan
    plan_id = plan_from_question(question)
    if not plan_id:
        print("Failed to create initial plan.", file=sys.stderr)
        sys.exit(1)

    # 2️⃣ Examine each step for knowledge gaps
    steps = get_plan_steps(plan_id)
    any_filled = False
    for step in steps:
        # step is a dict; we need to feed JSON to the filler.
        step_json = json.dumps(step)
        if knowledge_gap_filler(step_json):
            any_filled = True

    # 3️⃣ If we filled any gaps, regenerate the plan so new context is used.
    if any_filled:
        # Re‑run plan_from_question – the tool will create a *new* plan that
        # can reference the freshly‑added archive notes.
        plan_id = plan_from_question(question)

    # 4️⃣ Output the final persistent plan ID (plain text)
    print(plan_id)

if __name__ == "__main__":
    main()
