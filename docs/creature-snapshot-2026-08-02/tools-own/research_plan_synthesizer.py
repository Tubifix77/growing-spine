#!/usr/bin/env python3
"""
tool: research_plan_synthesizer
call: research_plan_synthesizer <research_question>
does: Accepts a research question, runs knowledge_gap_filler to identify missing pieces, then creates a step-by-step agenda with plan_from_question and registers it in step-planner-tracker.
"""
import subprocess
import sys
import json

def run_tool(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running {cmd}: {e.stderr.strip()}"

def main():
    if len(sys.argv) < 2:
        print("Usage: research_plan_synthesizer <research_question>")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"Synthesizing research plan for: {question}")

    # Step 1: Identify knowledge gaps
    print("Identifying knowledge gaps...")
    gaps = run_tool(f"knowledge_gap_filler \"{question}\"")
    
    if "Error" in gaps or not gaps:
        print("No specific gaps identified or tool failed. Proceeding with general planning.")
        enriched_question = question
    else:
        print(f"Gaps found: {gaps[:200]}...")
        enriched_question = f"{question}\n\nNote the following identified knowledge gaps to address in the plan:\n{gaps}"

    # Step 2: Create the plan
    print("Generating persistent research plan...")
    # plan_from_question usually outputs the plan ID or a summary
    plan_result = run_tool(f"plan_from_question \"{enriched_question}\"")

    if "Error" in plan_result:
        print(f"Failed to create plan: {plan_result}")
        sys.exit(1)

    print("\n--- Plan Synthesized Successfully ---")
    print(plan_result)

if __name__ == "__main__":
    main()
