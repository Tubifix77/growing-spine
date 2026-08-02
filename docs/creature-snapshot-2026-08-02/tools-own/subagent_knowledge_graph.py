#!/usr/bin/env python3
"""
Tool: subagent_knowledge_graph
Call: subagent_knowledge_graph <keyword>
Does: Generate new knowledge about a keyword using subagent_ask_helper,
      then archive the result in the keyword archive.
"""
import sys
import json
import subprocess

def subagent_ask(prompt):
    # Use the built‑in subagent_ask_helper tool via subprocess
    result = subprocess.run(
        ["subagent_ask_helper", prompt],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

def main():
    if len(sys.argv) < 2:
        print("Usage: subagent_knowledge_graph <keyword>")
        sys.exit(1)
    keyword = sys.argv[1]
    # Generate knowledge
    answer = subagent_ask(f"Give a concise overview of {keyword}")
    # Archive the answer
    archiving_cmd = [
        "keyword-archive-store",
        "--keyword", keyword,
        "--tags", "generated,knowledge-graph",
        "--value", answer
    ]
    subprocess.run(archiving_cmd, check=True)
    print(f"Generated and stored knowledge for '{keyword}'")

if __name__ == "__main__":
    main()
