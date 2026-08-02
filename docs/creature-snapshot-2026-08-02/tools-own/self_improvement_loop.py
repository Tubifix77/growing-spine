#!/usr/bin/env python3
# tool: self_improvement_loop
# call: self_improvement_loop --step-id <step_id>
# does: Evaluates a completed step via subagent, logs insights in memstore, and refines future steps using plan_from_question.

import subprocess
import argparse
import sys
import json
import os

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {cmd}: {e.stderr}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step-id", required=True, help="The ID of the completed step to evaluate")
    args = parser.parse_args()
    
    step_id = args.step_id

    # 1. Retrieve plan details
    plan_data_raw = run_cmd("step-planner-tracker --show")
    if not plan_data_raw:
        print("Could not retrieve plan info.")
        sys.exit(1)

    try:
        plan_data = json.loads(plan_data_raw)
    except json.JSONDecodeError:
        print("Failed to parse plan data.")
        sys.exit(1)

    # Find the step
    steps = plan_data.get("steps", [])
    target_step = next((s for s in steps if str(s.get("id")) == step_id), None)

    if not target_step:
        print(f"Step ID {step_id} not found in current plan.")
        sys.exit(1)

    step_desc = target_step.get("description", "No description")
    step_status = target_step.get("status", "unknown")

    # 2. Evaluate performance via subagent
    # We provide the step description and its status. 
    # We also ask the LLM to check memstore for any recent outcomes related to this step.
    eval_prompt = (
        f"Evaluate the execution of the following task step:\n"
        f"Step ID: {step_id}\n"
        f"Description: {step_desc}\n"
        f"Status: {step_status}\n\n"
        f"Based on the context of the current project, was this step successful? "
        f"What were the key insights or failures? "
        f"Should the remaining steps of the plan be adjusted? "
        f"Provide a concise evaluation and a 'YES' or 'NO' if replanning is needed."
    )
    
    evaluation = run_cmd(f"subagent_ask_helper \"{eval_prompt}\"")
    if not evaluation:
        print("Evaluation failed.")
        sys.exit(1)

    print(f"Evaluation for step {step_id}:\n{evaluation}")

    # 3. Log insights in memstore
    mem_key = f"self_improvement:step_{step_id}"
    run_cmd(f"memstore store {mem_key} \"{evaluation}\"")
    print(f"Insight logged to memstore: {mem_key}")

    # 4. Refine future steps if necessary
    if "YES" in evaluation.upper():
        print("Replanning triggered based on evaluation...")
        goal = plan_data.get("goal", "the current objective")
        refine_prompt = (
            f"The original goal is: {goal}\n"
            f"Previous step {step_id} evaluation: {evaluation}\n"
            f"Please refine the remaining plan to account for these insights. "
            f"Generate a new set of steps to complete the goal."
        )
        # We use plan_from_question to generate a new refined plan
        # Note: plan_from_question creates a new plan in step-planner-tracker
        run_cmd(f"plan_from_question \"{refine_prompt}\"")
        print("New refined plan generated.")
    else:
        print("No replanning needed.")

if __name__ == "__main__":
    main()
