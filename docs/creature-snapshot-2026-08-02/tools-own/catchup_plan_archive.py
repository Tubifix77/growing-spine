import subprocess
import sys
import json
import os

def run_tool(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running {cmd}: {e.stderr}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: catchup_plan_archive <topic>")
        sys.exit(1)

    topic = sys.argv[1]
    print(f"[*] Starting catchup research plan for: {topic}")

    # 1. Fetch fresh news items using wake_catchup_fetcher
    print("[*] Fetching fresh items...")
    fetch_output = run_tool(f"wake_catchup_fetcher {topic}")
    if not fetch_output:
        print("[-] No fresh items found or fetcher failed.")
        sys.exit(0)

    try:
        items = json.loads(fetch_output)
    except json.JSONDecodeError:
        print("[-] Failed to parse fetcher output as JSON.")
        sys.exit(1)

    if not items:
        print("[-] No new items to process.")
        sys.exit(0)

    print(f"[*] Found {len(items)} new items. Synthesizing research goals...")

    # 2. Synthesize a high-level research question based on these items
    # We use subagent_ask_helper to turn the headlines/URLs into a targeted research goal.
    items_summary = "\n".join([f"- {item.get('title', 'No Title')} ({item.get('url', 'No URL')})" for item in items])
    prompt = (
        f"Based on the following fresh news items about {topic}, formulate a single, comprehensive "
        f"research question that would allow an AI to fully understand the current state of affairs and "
        f"identify the most critical missing information. Only return the question.\n\n"
        f"Items:\n{items_summary}"
    )
    
    research_question = run_tool(f"subagent_ask_helper \"{prompt}\"")
    if not research_question:
        print("[-] Failed to synthesize research question.")
        sys.exit(1)
    
    print(f"[*] Synthesized Research Question: {research_question}")

    # 3. Use plan_from_question to create a multi-step plan (Compounding Capability)
    # This increases dependency depth by chaining fetch -> synthesis -> planner tool -> tracker tool.
    print("[*] Generating detailed research plan via plan_from_question...")
    # Note: plan_from_question creates a plan and returns a plan ID or summary.
    # It internally uses step-planner-tracker.
    plan_result = run_tool(f"plan_from_question \"{research_question}\"")
    
    if plan_result:
        print("[+] Successfully created a research plan based on fresh data.")
        print(f"Plan Output: {plan_result}")
        
        # Log the session summary to the archive
        summary = f"Catchup Research Plan for {topic}\nQuestion: {research_question}\nPlan Result: {plan_result}\nItems processed: {len(items)}"
        run_tool(f"keyword-archive-store {topic} \"{summary}\" --tags catchup,research_plan")
    else:
        print("[-] Failed to generate plan.")

if __name__ == "__main__":
    main()
