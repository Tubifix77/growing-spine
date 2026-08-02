#!/usr/bin/env python3
# tool: news_plan_synthesizer
# call: news_plan_synthesizer <url> [--keyword <kw>]
# does: Fetches a news article, synthesises a concise summary, generates a
#       persistent actionable plan, fills knowledge gaps, and archives the
#       summary and plan. Returns the created plan ID.

import argparse
import subprocess
import sys
import json
import shlex
from pathlib import Path

def run_cmd(cmd, input_text=None):
    """Run a shell command, optionally feeding stdin, and return stdout."""
    result = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\\nStderr: {result.stderr.strip()}")
    return result.stdout.strip()

def fetch_article(url):
    """Fetch the raw article text using the existing web-fetch tool."""
    return run_cmd(['web-fetch', url])

def summarize(text):
    """Summarise the article via subagent_ask_helper."""
    prompt = (
        "Summarize the following news article in 3‑5 concise sentences, "
        "preserving the key facts and any actionable insights.\\n\\n"
        f"{text}"
    )
    return run_cmd(['subagent_ask_helper', prompt])

def create_plan(summary):
    """Create a persistent plan from the summary using plan_from_question."""
    # The plan tool expects a natural‑language goal; we give it the summary.
    plan_output = run_cmd(['plan_from_question', summary])
    # plan_from_question prints JSON with at least an 'id' field.
    try:
        plan_json = json.loads(plan_output)
        return plan_json.get('id'), plan_output
    except json.JSONDecodeError:
        # Fallback: the tool may output plain text "Plan ID: <id>"
        for line in plan_output.splitlines():
            if line.lower().startswith('plan id'):
                return line.split(':', 1)[1].strip(), plan_output
        raise RuntimeError("Could not parse plan ID from plan_from_question output")

def archive_entry(keyword, content, tags=None):
    """Archive a piece of content using keyword-archive-store."""
    cmd = ['keyword-archive-store', '--keyword', keyword, '--content', content]
    if tags:
        cmd.extend(['--tags', ','.join(tags)])
    run_cmd(cmd)

def main():
    parser = argparse.ArgumentParser(
        description="Fetch a news article, summarise it, create a plan and archive results."
    )
    parser.add_argument('url', help='URL of the news article')
    parser.add_argument('--keyword', default='news', help='Keyword under which to archive')
    args = parser.parse_args()

    try:
        article = fetch_article(args.url)
        if not article:
            raise RuntimeError("Fetched article is empty")
    except Exception as e:
        sys.stderr.write(f"Error fetching article: {e}\\n")
        sys.exit(1)

    try:
        summary = summarize(article)
    except Exception as e:
        sys.stderr.write(f"Error summarising article: {e}\\n")
        sys.exit(1)

    try:
        plan_id, plan_raw = create_plan(summary)
    except Exception as e:
        sys.stderr.write(f"Error creating plan: {e}\\n")
        sys.exit(1)

    # Archive summary and plan
    try:
        archive_entry(args.keyword, summary, tags=['summary'])
        archive_entry(args.keyword, plan_raw, tags=['plan'])
    except Exception as e:
        sys.stderr.write(f"Error archiving results: {e}\\n")
        # Proceed – the plan ID is still useful

    # Output the plan ID for the caller
    print(plan_id)

if __name__ == '__main__':
    main()
