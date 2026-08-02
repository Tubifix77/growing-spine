#!/usr/bin/env python3
"""
AutoNewsDigest – a compositional tool that:
  • Fetches an RSS feed,
  • Extracts item titles,
  • Summarizes each title via the LLM sub‑agent,
  • Writes a JSON digest file named `news_digest_<date>.json`,
  • Archives each summary in the keyword‑archive under a daily keyword.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List

def run_cmd(cmd: List[str], input_text: str = None) -> str:
    """Run a command, capture stdout, raise on error."""
    result = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(f"Command {' '.join(cmd)} failed (code {result.returncode})\n")
        sys.stderr.write(result.stderr)
        sys.exit(result.returncode)
    return result.stdout.strip()

def fetch_rss(feed_url: str) -> Path:
    """Use the existing `fetch_rss_feed` tool; returns path to downloaded XML."""
    out = run_cmd(["fetch_rss_feed", feed_url])
    return Path(out)

def extract_titles(rss_path: Path) -> List[str]:
    """Extract titles via the `extract_rss_titles` tool."""
    with rss_path.open("rb") as f:
        out = run_cmd(["extract_rss_titles"], input_text=f.read())
    # each title is on its own line
    return [line.strip() for line in out.splitlines() if line.strip()]

def summarize_title(title: str) -> str:
    """Ask the LLM sub‑agent to produce a short one‑sentence summary."""
    prompt = f"Summarize the following news headline in one concise sentence:\n{title}"
    # subagent_ask_helper reads from stdin and prints the answer
    summary = run_cmd(["subagent_ask_helper"], input_text=prompt)
    return summary

def archive_entry(keyword: str, title: str, summary: str):
    """Store a note in the keyword‑archive via `keyword-archive-store`."""
    # The store tool expects: keyword, note JSON (as a string)
    note = json.dumps({"title": title, "summary": summary})
    run_cmd(["keyword-archive-store", keyword, note])

def main():
    parser = argparse.ArgumentParser(description="Create a JSON news digest from an RSS feed.")
    parser.add_argument(
        "--source",
        required=True,
        help="URL of the RSS feed to process",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the digest JSON file will be written",
    )
    args = parser.parse_args()

    # 1️⃣ Fetch the feed
    rss_path = fetch_rss(args.source)

    # 2️⃣ Extract titles
    titles = extract_titles(rss_path)
    if not titles:
        sys.stderr.write("No titles extracted – aborting.\n")
        sys.exit(1)

    # 3️⃣ Summarize each title and optionally archive
    today_key = f"news_digest_{datetime.date.today().isoformat()}"
    digest = []
    for title in titles:
        summary = summarize_title(title)
        digest.append({"title": title, "summary": summary})
        archive_entry(today_key, title, summary)

    # 4️⃣ Write JSON digest
    out_path = Path(args.output_dir) / f"news_digest_{datetime.date.today().isoformat()}.json"
    out_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2))
    print(f"Digest written to {out_path}")

if __name__ == "__main__":
    main()
