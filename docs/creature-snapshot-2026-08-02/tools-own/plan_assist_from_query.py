#!/usr/bin/env python3
"""
tool: plan_assist_from_query
call: plan_assist_from_query <question>
does: Takes a natural‑language question, uses `plan_from_question` (which calls
      subagent_ask_helper and registers steps with step‑planner‑tracker) to
      generate a persistent multi‑step plan, and prints the resulting plan ID.
"""

import sys
import subprocess
import shlex

def main():
    if len(sys.argv) < 2:
        print("Usage: plan_assist_from_query <question>")
        sys.exit(1)

    # Combine all arguments into a single question string
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print("Error: empty question")
        sys.exit(1)

    # Call the existing plan_from_question tool
    # We use shlex.split to safely pass the whole question as one argument
    cmd = ["plan_from_question"] + shlex.split(question)
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running plan_from_question:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)

    # The plan_from_question tool prints a JSON line with the plan ID.
    # Typical output: {"plan_id": "1234567890"}   (but we accept any text)
    output = result.stdout.strip()
    # Try to extract a plan_id if JSON; otherwise just echo the whole output
    plan_id = None
    try:
        import json
        data = json.loads(output)
        plan_id = data.get("plan_id")
    except Exception:
        # Not JSON – fall back to raw text
        plan_id = output

    if plan_id:
        print(plan_id)
    else:
        # If we couldn't parse, still echo whatever we got
        print(output)

if __name__ == "__main__":
    main()
