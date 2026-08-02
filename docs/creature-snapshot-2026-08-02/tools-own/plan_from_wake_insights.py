#!/usr/bin/env python3
"""
tool: plan_from_wake_insights
call: plan_from_wake_insights <topic>
does: Turn fresh “wake” items about <topic> into a tracked plan.
   1. Fetch fresh items with wake_catchup_fetcher.
   2. Download each article body.
   3. Ask a sub‑agent (subagent_ask_helper) for an actionable insight.
   4. Combine insights into a single prompt.
   5. Generate a persistent plan with plan_from_question.
   6. Register the plan in step‑planner‑tracker and output the plan ID.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Helper to run a shell command and capture output
def run_cmd(cmd: list) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed: {result.stderr.strip()}")
    return result.stdout.strip()

def fetch_wake_items(topic: str):
    """Return list of dicts {title, url, tags} from wake_catchup_fetcher."""
    out = run_cmd(["wake_catchup_fetcher", "--topic", topic, "--json"])
    try:
        items = json.loads(out)
    except json.JSONDecodeError:
        raise RuntimeError("wake_catchup_fetcher did not return valid JSON")
    return items

def fetch_article(url: str) -> str:
    """Download article body (text) – fallback to curl -> wget -> python urllib."""
    # Use existing tool `fetch_url` which writes to stdout
    return run_cmd(["fetch_url", url])

def get_insight(article_text: str) -> str:
    """Ask subagent_ask_helper for a single actionable insight."""
    # The sub‑agent expects a prompt; we give a short instruction.
    prompt = (
        "Summarise the most actionable insight from the following text. "
        "Answer in one concise sentence suitable for a to‑do item."
    )
    # subagent_ask_helper reads the prompt from stdin
    result = subprocess.run(
        ["subagent_ask_helper"],
        input=prompt + "\n---\n" + article_text,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"subagent_ask_helper failed: {result.stderr.strip()}")
    return result.stdout.strip()

def build_plan(insights: list) -> str:
    """Create a persistent plan using plan_from_question."""
    # Combine insights into a single question for the planner.
    combined = " | ".join(insights)
    question = f"Create a step‑by‑step plan to act on these insights: {combined}"
    plan_id = run_cmd(["plan_from_question_onecall", question])
    return plan_id

def register_plan(plan_id: str):
    """Add the plan to step‑planner‑tracker (high‑priority task)."""
    # The tracker expects: add <plan_id> <description>
    description = f"Plan derived from wake insights (ID {plan_id})"
    run_cmd(["step-planner-tracker", "add", plan_id, description])

def main():
    if len(sys.argv) != 2:
        print("Usage: plan_from_wake_insights <topic>")
        sys.exit(1)
    topic = sys.argv[1]

    # 1️⃣ fetch wake items
    items = fetch_wake_items(topic)
    if not items:
        print(f"No fresh items found for topic: {topic}")
        sys.exit(0)

    insights = []
    for it in items[:5]:  # limit to first few to keep cost low
        try:
            article = fetch_article(it["url"])
            insight = get_insight(article)
            insights.append(insight)
        except Exception as e:
            # Log but continue with other items
            print(f"[WARN] Skipping {it.get('url')}: {e}", file=sys.stderr)

    if not insights:
        print("No insights could be generated.", file=sys.stderr)
        sys.exit(1)

    # 2️⃣ build & register plan
    plan_id = build_plan(insights)
    register_plan(plan_id)

    print(f"Created plan ID: {plan_id}")

if __name__ == "__main__":
    main()
