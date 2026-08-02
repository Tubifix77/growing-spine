#!/usr/bin/env python3
"""
tool: knowledge_gap_resolver
call: knowledge_gap_resolver "<natural‑language query>"
does: Resolve a knowledge gap by searching the keyword‑archive, fetching a Wikipedia summary if missing,
      summarising it via a sub‑agent, and archiving the brief.
"""

import sys, subprocess, json, shlex, urllib.parse, os, textwrap

def run_cmd(cmd, input_data=None):
    """Run a shell command, capture stdout, raise on error."""
    result = subprocess.run(cmd, input=input_data, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\\nstderr: {result.stderr}")
    return result.stdout.strip()

def search_archive(query):
    """Return list of matching archive entries (as JSON strings)."""
    cmd = f'keyword-archive-search "{shlex.quote(query)}"'
    out = run_cmd(cmd)
    return [line for line in out.splitlines() if line.strip()]

def fetch_wikipedia(query):
    """Fetch Wikipedia summary JSON for the query."""
    encoded = urllib.parse.quote(query)
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    # web-fetch prints the body; we need raw JSON
    out = run_cmd(f'web-fetch "{url}"')
    try:
        data = json.loads(out)
        # Prefer the plain-text extract; fall back to description
        return data.get('extract') or data.get('description') or ''
    except json.JSONDecodeError:
        return ''

def synthesize_brief(topic, raw_text):
    """Ask the sub‑agent to produce a concise brief."""
    prompt = textwrap.dedent(f'''
        You are a chemistry assistant. Write a concise (≈2‑3 sentences) explanation of the topic below.
        Topic: {topic}
        Information: {raw_text}
        ''').strip()
    # subagent_ask_helper reads the prompt from stdin and outputs only the answer
    out = run_cmd('subagent_ask_helper', input_data=prompt)
    return out

def archive_brief(keyword, brief):
    """Store the brief in the keyword‑archive."""
    # keyword‑archive-store expects a JSON line; we give { "text": "..."} format
    payload = json.dumps({"text": brief})
    cmd = f'keyword-archive-store "{shlex.quote(keyword)}" \'{payload}\''
    run_cmd(cmd)   # we ignore its output; success means it was stored

def main():
    if len(sys.argv) != 2:
        print("Usage: knowledge_gap_resolver \"<query>\"")
        sys.exit(1)
    query = sys.argv[1].strip()

    # 1. Search the archive
    entries = search_archive(query)
    if entries:
        # Return the first matching entry (already brief enough)
        print(entries[0])
        return

    # 2. Fetch fresh Wikipedia info
    wiki_text = fetch_wikipedia(query)
    if not wiki_text:
        print(f"[knowledge_gap_resolver] No Wikipedia info found for: {query}")
        sys.exit(1)

    # 3. Synthesize a brief via sub‑agent
    brief = synthesize_brief(query, wiki_text)

    # 4. Archive the brief
    archive_brief(query, brief)

    # 5. Output the brief for the caller
    print(brief)

if __name__ == "__main__":
    main()
