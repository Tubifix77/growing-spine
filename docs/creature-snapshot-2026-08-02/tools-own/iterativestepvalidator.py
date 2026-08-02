#!/usr/bin/env python3
# tool: IterativeStepValidator
# call: iterativestepvalidator.py --plan-id <id>
# does: Verifies the most recent completed step of a plan using a subagent and logs the result in memstore.

import argparse
import json
import subprocess
import sys
import os

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {cmd}: {e.stderr}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-id", required=True, help="The ID of the plan to validate")
    args = parser.parse_args()

    plan_id = args.plan_id
    print(f"Validating most recent completed step for plan {plan_id}...")

    # 1. Get the plan steps
    # step-planner-tracker list usually lists all plans or a specific one if supported.
    # Based on common usage, let's list and filter.
    plan_data_raw = run_cmd("step-planner-tracker list")
    if not plan_data_raw:
        print("Could not retrieve plan list.")
        sys.exit(1)

    # We need to find the steps for plan_id and the last one marked 'done'.
    # Assuming output format: [Plan ID] Goal: ... \n  1. Step text [DONE] \n  2. Step text [PENDING]
    lines = plan_data_raw.splitlines()
    target_plan_found = False
    last_done_step = None
    step_index = 0

    for line in lines:
        if f"[{plan_id}]" in line or plan_id == line.strip():
            target_plan_found = True
            continue
        
        if target_plan_found:
            # Check if we've hit another plan
            if line.startswith("[") and "]" in line:
                break
            
            # Look for completed steps. Assuming format "X. Description [DONE]" or similar.
            if "[DONE]" in line.upper() or "completed" in line.lower():
                last_done_step = line.strip()
                step_index += 1 # Simple counter for the step number in the validation log
            elif line.strip() == "":
                continue
            else:
                # This is a pending step or other text
                pass

    if not target_plan_found:
        print(f"Plan ID {plan_id} not found in tracker.")
        sys.exit(1)

    if not last_done_step:
        print(f"No completed steps found for plan {plan_id} to validate.")
        sys.exit(0)

    print(f"Last completed step found: {last_done_step}")

    # 2. Verify with subagent
    # We ask the subagent to judge if the step was truly successful based on context.
    # Since we don't have a "current state" dump, we ask the subagent to reflect 
    # on the step description and check if there is any evidence of failure in the recent log/memory.
    
    # Get recent memories for context
    memories = run_cmd("memories") or ""
    
    prompt = (
        f"Plan ID: {plan_id}\n"
        f"Step to verify: {last_done_step}\n"
        f"Recent memories/context:\n{memories[-2000:]}\n\n"
        f"Based on the context provided, was this step successfully completed? "
        f"Answer with 'PASS: [reason]' or 'FAIL: [reason]'. Be concise."
    )

    # Call subagent_ask_helper
    # Using a shell wrapper to pass the prompt safely
    verification_result = run_cmd(f"subagent_ask_helper \"{prompt}\"")
    if not verification_result:
        print("Subagent failed to provide a verification result.")
        sys.exit(1)

    print(f"Verification result: {verification_result}")

    # 3. Log to memstore
    # Key: validation:<plan_id>:<step_snippet>
    # Value: Result
    step_key = last_done_step[:30].replace(" ", "_").replace("[", "").replace("]", "")
    mem_key = f"validation:{plan_id}:{step_key}"
    
    # Use memstore tool to save the result
    run_cmd(f"memstore set {mem_key} \"{verification_result}\"")
    
    print(f"Validation result logged to memstore under key: {mem_key}")

if __name__ == "__main__":
    main()
