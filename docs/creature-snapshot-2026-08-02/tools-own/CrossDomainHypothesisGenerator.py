#!/usr/bin/env python3
"""
tool: CrossDomainHypothesisGenerator
call: CrossDomainHypothesisGenerator <domain1> <domain2> [num_hypotheses]
does: Generate research hypotheses that connect two Wikipedia domains by fetching their summaries, prompting an LLM, and archiving the result.
"""

import sys
import json
import urllib.parse
import subprocess
import shlex
import os

def run_cmd(cmd):
    """Run a shell command, return stdout (decoded). Raise on error."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nstderr: {result.stderr}")
    return result.stdout.strip()

def fetch_wiki_summary(domain):
    """Fetch Wikipedia summary via the REST API and return the plain text extract."""
    # Encode the domain for URL safety
    title = urllib.parse.quote(domain)
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    # Use the existing web-fetch tool (it returns raw body)
    raw = run_cmd(f"web-fetch {shlex.quote(url)}")
    # The response is JSON; extract the 'extract' field with jq (ensure_jq is available)
    try:
        # If jq is not installed, fallback to python json parsing
        summary = json.loads(raw).get("extract", "")
    except Exception:
        # fallback via jq
        summary = run_cmd(f"echo {shlex.quote(raw)} | jq -r '.extract'")
    return summary

def main():
    if len(sys.argv) < 3:
        print("Usage: CrossDomainHypothesisGenerator <domain1> <domain2> [num_hypotheses]")
        sys.exit(1)

    domain1 = sys.argv[1]
    domain2 = sys.argv[2]
    num = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    # 1. Get summaries
    try:
        summary1 = fetch_wiki_summary(domain1)
        summary2 = fetch_wiki_summary(domain2)
    except Exception as e:
        print(f"Error fetching summaries: {e}")
        sys.exit(1)

    # 2. Build prompt
    prompt = (
        f"Domain A ({domain1}): {summary1}\n\n"
        f"Domain B ({domain2}): {summary2}\n\n"
        f"Generate {num} concise research hypotheses that plausibly connect these two domains. "
        f"List each hypothesis as a separate short sentence."
    )

    # 3. Ask sub‑agent LLM
    try:
        # subagent_ask_helper expects the prompt as a single argument
        answer = run_cmd(f"subagent_ask_helper {shlex.quote(prompt)}")
    except Exception as e:
        print(f"Error from subagent_ask_helper: {e}")
        sys.exit(1)

    # 4. Archive the result
    keyword = f"hypotheses:{domain1}-{domain2}"
    tags = "hypothesis,domain1,domain2"
    # keyword-archive-store expects: <keyword> <content> [--tags <tags>]
    try:
        run_cmd(f'keyword-archive-store "{keyword}" "{answer}" --tags "{tags}"')
    except Exception as e:
        print(f"Error archiving hypotheses: {e}")
        # continue anyway – we still want to show the answer

    # 5. Output
    print(answer)

if __name__ == "__main__":
    main()
