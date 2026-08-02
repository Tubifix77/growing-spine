#!/usr/bin/env python3
"""
tool: dynamic_faq_from_web
call: dynamic_faq_from_web <url>
does: Fetch a web page, generate FAQ (Q&A) pairs via LLM, and store each pair in the keyword‑archive.
"""

import sys
import json
import subprocess
import shlex
import os
import tempfile

def run_cmd(cmd, input_data=None):
    """Run a shell command, capture stdout, raise on error."""
    result = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
        shell=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(f"Command failed: {cmd}\\n")
        sys.stderr.write(result.stderr)
        sys.exit(1)
    return result.stdout.strip()

def fetch_page(url):
    """Use existing web-fetch tool to retrieve the page body."""
    return run_cmd(f"web-fetch {shlex.quote(url)}")

def generate_faq(content, url):
    """
    Ask the LLM (via subagent_ask_helper) to produce FAQ pairs.
    The prompt asks for JSON output: [{\"question\":..., \"answer\":...}, ...]
    """
    prompt = f"""You are given the HTML content of a web page (URL: {url}).

Extract from this page a concise Frequently Asked Questions list that a newcomer might ask.
Provide **exactly** a JSON array of objects, each with two string fields:
  "question": the FAQ question,
  "answer": a short answer (1‑3 sentences) drawn from the page content.

Do NOT include any extra text, explanations, or markdown. Return only the JSON."""
    # subagent_ask_helper reads the prompt from stdin and prints the answer
    return run_cmd("subagent_ask_helper", input_data=prompt)

def parse_faq(json_text):
    """Parse the JSON output from the LLM; if parsing fails, abort."""
    try:
        data = json.loads(json_text)
        if not isinstance(data, list):
            raise ValueError("FAQ output is not a list")
        # Ensure each entry has required keys
        for entry in data:
            if not isinstance(entry, dict) or "question" not in entry or "answer" not in entry:
                raise ValueError("Malformed FAQ entry")
        return data
    except Exception as e:
        sys.stderr.write(f"Failed to parse FAQ JSON: {e}\\n")
        sys.stderr.write(f"Raw output was: {json_text}\\n")
        sys.exit(1)

def store_faq(faq_list, url):
    """Store each FAQ entry in the keyword‑archive."""
    base_keyword = f"FAQ:{url}"
    for idx, entry in enumerate(faq_list, start=1):
        # Build a descriptive note
        note = {
            "question": entry["question"],
            "answer": entry["answer"],
            "source_url": url,
            "index": idx
        }
        note_json = json.dumps(note, ensure_ascii=False)
        # Use keyword-archive-store: keyword‑archive-store <keyword> <note>
        # Add tags to make it searchable
        tags = "faq,web"
        cmd = f'keyword-archive-store "{shlex.quote(base_keyword)}" \'{note_json}\' --tags {tags}'
        run_cmd(cmd)

def main():
    if len(sys.argv) != 2:
        sys.stderr.write("Usage: dynamic_faq_from_web <url>\\n")
        sys.exit(1)
    url = sys.argv[1]

    # Step 1: fetch page
    page_content = fetch_page(url)
    if not page_content:
        sys.stderr.write("Failed to fetch page content.\\n")
        sys.exit(1)

    # Step 2: generate FAQ via LLM
    faq_raw = generate_faq(page_content, url)

    # Step 3: parse output
    faq_items = parse_faq(faq_raw)

    # Step 4: store each FAQ entry
    store_faq(faq_items, url)

    print(f"Stored {len(faq_items)} FAQ entries for {url}")
    
if __name__ == "__main__":
    main()
