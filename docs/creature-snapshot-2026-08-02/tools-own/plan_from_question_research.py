#!/usr/bin/env python3
"""
tool: plan_from_question_research
does: Generate a research plan from a question, then run knowledge_gap_filler on each step
       to enrich it with missing knowledge. Returns the plan ID and any identified gaps.
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime

# Helper to run a tool and capture its stdout (as text)
def run_tool(command: list, input_data: str = None) -> str:
    result = subprocess.run(
        command,
        input=input_data.encode() if input_data is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # Propagate error with context
        sys.stderr.write(
            f"Error running {' '.join(command)} (rc={result.returncode}): {result.stderr}\\n"
        )
        sys.exit(1)
    return result.stdout.strip()

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: plan_from_question_research <question>\\n")
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    # 1️⃣ Create a research plan using the existing `plan_from_question` tool.
    # The tool prints the new plan ID on stdout.
    plan_id = run_tool(["plan_from_question", question])
    if not plan_id:
        sys.stderr.write("Failed to obtain a plan ID from plan_from_question.\\n")
        sys.exit(1)

    # 2️⃣ Retrieve the steps for this plan using `step-planner-tracker`.
    # We ask the tracker for the full plan JSON.
    plan_json_str = run_tool(["step-planner-tracker", "get-plan", "--plan-id", plan_id])
    try:
        plan = json.loads(plan_json_str)
    except json.JSONDecodeError:
        sys.stderr.write(f"Failed to parse plan JSON: {plan_json_str}\\n")
        sys.exit(1)

    steps = plan.get("steps", [])
    gaps = []  # collect any knowledge gaps identified per step

    # 3️⃣ For each step, run knowledge_gap_filler.
    # knowledge_gap_filler expects a JSON wake-up item on stdin.
    for idx, step in enumerate(steps):
        # Prepare a minimal wake‑up item containing the step text.
        wake_item = {
            "title": f"Research step {idx+1}",
            "description": step.get("description", step.get("text", "")),
            "tags": ["research", "auto-generated"],
        }
        wake_json = json.dumps(wake_item)

        # Run the filler; it returns a JSON object with a `gap` field when a gap is found.
        filler_output = run_tool(["knowledge_gap_filler"], input_data=wake_json)

        try:
            filler_res = json.loads(filler_output)
        except json.JSONDecodeError:
            # If filler didn't return JSON, just ignore (treat as no gap)
            continue

        if filler_res.get("gap"):
            gaps.append({
                "step_index": idx,
                "step_text": step.get("description", step.get("text", "")),
                "gap": filler_res["gap"]
            })

    # 4️⃣ Update the plan metadata with identified gaps (optional but useful for later tools).
    if gaps:
        # Store gaps as a JSON string under a special `metadata` field.
        metadata = plan.get("metadata", {})
        metadata["knowledge_gaps"] = gaps
        # Write back the updated plan via the tracker.
        run_tool([
            "step-planner-tracker",
            "update-plan",
            "--plan-id", plan_id,
            "--metadata", json.dumps(metadata)
        ])

    # 5️⃣ Output a concise JSON for the cousin: plan ID and any gaps.
    result = {
        "plan_id": plan_id,
        "gaps": gaps
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
