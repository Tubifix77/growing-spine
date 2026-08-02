#!/usr/bin/env python3
"""
tool: semantic_search_planner
call: semantic_search_planner <topic>
does: Generate a research plan for <topic> by first retrieving semantically relevant archived snippets
       (via semantic_search_recall) and then feeding them to plan_from_question.
"""

import subprocess
import json
import sys
import textwrap

def run_tool(cmd, input_data=None):
    """Run a tool in the toolbox, capture stdout (as text) and return it."""
    result = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
        check=False,  # we will handle errors ourselves
        env=dict(**dict(os.environ), **{"PYTHONUNBUFFERED":"1"})
    )
    if result.returncode != 0:
        sys.stderr.write(f"Error running {' '.join(cmd)}:\n")
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip()

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: semantic_search_planner <topic>\\n")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])

    # 1️⃣ Retrieve relevant snippets via semantic_search_recall
    # The tool expects a JSON query on stdin; we pass a simple dict.
    recall_input = json.dumps({"query": topic, "top_k": 5})
    recall_output = run_tool(
        ["/mind/tools/own/semantic_search_recall"],
        input_data=recall_input
    )
    # semantic_search_recall returns a JSON list of {"text": "...", "score": ...}
    try:
        snippets = json.loads(recall_output)
    except json.JSONDecodeError:
        sys.stderr.write("semantic_search_recall did not return valid JSON.\\n")
        sys.exit(1)

    # Build a context string from the snippets
    context = "\n".join(snippet.get("text", "") for snippet in snippets)

    # 2️⃣ Create a planning prompt that includes the retrieved context
    planning_prompt = textwrap.dedent(f\"\"\"
        Using the following background information, create a detailed research plan to
        explore the topic: {topic}

        Background:
        {context}
    \"\"\")
    # plan_from_question expects a JSON with a "question" field
    plan_input = json.dumps({"question": planning_prompt})

    plan_output = run_tool(
        ["/mind/tools/own/plan_from_question"],
        input_data=plan_input
    )

    # plan_from_question returns a JSON object with at least "plan_id" and "steps"
    try:
        plan = json.loads(plan_output)
    except json.JSONDecodeError:
        sys.stderr.write("plan_from_question did not return valid JSON.\\n")
        sys.exit(1)

    # 3️⃣ Print a concise summary for the cousin
    plan_id = plan.get("plan_id", "unknown")
    steps = plan.get("steps", [])
    print(f"Plan ID: {plan_id}")
    print("First few steps:")
    for i, step in enumerate(steps[:5], start=1):
        print(f"  {i}. {step}")

if __name__ == "__main__":
    main()
