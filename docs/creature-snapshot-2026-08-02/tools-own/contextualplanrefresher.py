#!/usr/bin/env python3
import subprocess
import argparse
import sys
import os
import json

"""
tool: contextualplanrefresher
call: contextualplanrefresher --topic <topic>
does: Pulls previous related plans from memstore, runs knowledge_gap_filler to discover new constraints or data, and rewrites the plan using step‑planner‑tracker.
"""

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running {cmd}: {e.stderr}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="The topic to refresh the plan for")
    args = parser.parse_args()

    topic = args.topic
    print(f"Refreshing plan for topic: {topic}...")

    # 1. Pull previous related plans/knowledge from memstore
    print("Recalling existing knowledge and plans...")
    # Search memstore for any entries related to the topic
    memory_context = run_cmd(f"recall {topic}")
    
    # 2. Run knowledge_gap_filler to discover new constraints or data
    print("Filling knowledge gaps...")
    gap_info = run_cmd(f"knowledge_gap_filler {topic}")

    # 3. Synthesize updated plan using subagent_ask_helper
    print("Synthesizing updated plan...")
    prompt = (
        f"I have an existing plan/knowledge for '{topic}':\n{memory_context}\n\n"
        f"I have discovered the following new constraints or knowledge gaps:\n{gap_info}\n\n"
        f"Please rewrite the plan for '{topic}' as a clear, ordered list of steps. "
        f"Ensure it incorporates the new data and fixes any stale assumptions. "
        f"Return ONLY the list of steps, one per line, without numbering or preamble."
    )
    
    # We wrap the prompt in quotes for the shell command
    updated_steps = run_cmd(f"subagent_ask_helper '{prompt}'")

    if not updated_steps or "Error" in updated_steps:
        print("Failed to synthesize an updated plan.")
        sys.exit(1)

    # 4. Rewrite the plan using step-planner-tracker
    print("Persisting updated plan...")
    goal = f"Updated plan for {topic}"
    # The step-planner-tracker add command: step-planner-tracker add "goal" "step1\nstep2..."
    # We need to be careful with quotes for the steps string.
    cmd_add_plan = f'step-planner-tracker add "{goal}" "{updated_steps}"'
    result_plan = run_cmd(cmd_add_plan)

    print(f"Plan successfully refreshed. Result:\n{result_plan}")
    print(f"\nUpdated Steps:\n{updated_steps}")

if __name__ == "__main__":
    main()
