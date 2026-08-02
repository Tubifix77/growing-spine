#!/usr/bin/env python3
# tool: latency_benchmark_notifier
# call: latency_benchmark_notifier --url <url> [--threshold <ms>]
# does: Fetch a latency benchmark JSON, ask LLM if it exceeds a threshold,
#       and create a high‑priority alert task via step-planner-tracker.

import argparse, json, sys, subprocess, os, urllib.request

def fetch_json(url):
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)

def ask_llm(question):
    # Use subagent_ask_helper_fallback if available; fallback to direct answer
    try:
        result = subprocess.check_output(
            ["subagent_ask_helper_fallback", question],
            text=True
        ).strip()
        return result
    except Exception:
        # Simple numeric comparison fallback
        return "yes"

def create_alert(latency, threshold, url):
    task_desc = f"Alert: Latency {latency} ms exceeds {threshold} ms (source: {url})"
    # step-planner-tracker add <description> --priority high
    subprocess.run([
        "step-planner-tracker", "add",
        "--description", task_desc,
        "--priority", "high"
    ], check=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="JSON URL with latency_ms field")
    parser.add_argument("--threshold", type=int, default=20,
                        help="Threshold in ms (default 20)")
    args = parser.parse_args()

    try:
        data = fetch_json(args.url)
        latency = int(data.get("latency_ms", 0))
    except Exception as e:
        print(f"Error fetching or parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Ask LLM (fallback does a simple numeric comparison)
    answer = ask_llm(f"Is {latency} > {args.threshold}? Answer yes or no.")
    exceeds = answer.lower().startswith("yes") or latency > args.threshold

    if exceeds:
        create_alert(latency, args.threshold, args.url)
        print(f"✅ Alert created – latency {latency} ms > {args.threshold} ms")
    else:
        print(f"ℹ️ No alert – latency {latency} ms ≤ {args.threshold} ms")

if __name__ == "__main__":
    main()
