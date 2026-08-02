#!/usr/bin/env python3
"""
tool: QueueScalingAdvisor
call: QueueScalingAdvisor
does: Fetches latest Postgres queue scaling info, fills gaps, and synthesises a concise advisory.
"""

import subprocess
import json
import sys

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running {cmd}: {e.stderr}"

def main():
    topic = "Postgres queue scaling"
    print(f"Step 1: Fetching latest articles on {topic}...")
    
    # Fetch fresh items
    fetch_out = run_cmd(f"wake_catchup_fetcher \"{topic}\"")
    
    context = ""
    try:
        items = json.loads(fetch_out)
        if items:
            context = "\n".join([f"Title: {i.get('title')}\nURL: {i.get('url')}" for i in items])
            print(f"Found {len(items)} new items.")
        else:
            print("No new items found in the feed. Using general research fallback.")
    except json.JSONDecodeError:
        print("Could not parse fetcher output. Using general research fallback.")

    print("Step 2: Running knowledge_gap_filler to extract best-practice patterns...")
    # If we have items, we fill gaps based on them. Otherwise, we fill gaps on the topic.
    gap_query = f"What are the latest best practices for {topic}?"
    if context:
        gap_query += f"\nContext from fresh articles:\n{context}"
    
    gap_out = run_cmd(f"knowledge_gap_filler \"{gap_query}\"")
    
    print("Step 3: Synthesising final advisory via deep_answer_synth...")
    # We feed the gap-filled knowledge into the deep synthesizer
    synth_query = (
        f"Provide a concise, evidence-backed advisory on scaling Postgres queues. "
        f"Incorporate these specific findings: {gap_out if gap_out else 'General best practices'}. "
        f"Focus on performance, pitfalls, and recommended architectural patterns."
    )
    
    final_advisory = run_cmd(f"deep_answer_synth \"{synth_query}\"")
    
    print("\n--- POSTGRES QUEUE SCALING ADVISORY ---\n")
    print(final_advisory)
    print("\n---------------------------------------")

if __name__ == "__main__":
    main()
