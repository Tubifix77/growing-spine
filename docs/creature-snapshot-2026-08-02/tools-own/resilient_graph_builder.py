#!/usr/bin/env python3
"""
tool: resilient_graph_builder
does: Build a knowledge‑graph for a topic, falling back to archive search + LLM inference
      when the primary knowledge_graph_fetcher fails (timeout or error).
"""

import argparse
import json
import os
import subprocess
import sys
import shlex
import time

# ------------------------------------------------------------
# Helper: run a tool with a timeout, capture stdout/stderr
# ------------------------------------------------------------
def run_tool(cmd, timeout=15):
    """Run a command (list) with a timeout, return (code, stdout, stderr)."""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            return -1, stdout, f"Timeout after {timeout}s"
        return proc.returncode, stdout, stderr
    except Exception as e:
        return -1, "", f"Exception while running {' '.join(cmd)}: {e}"

# ------------------------------------------------------------
# Fallback: use archive snippets + sub‑agent LLM to synthesize a graph
# ------------------------------------------------------------
def fallback_graph(topic):
    # 1. Retrieve up to 5 relevant archived notes
    archive_cmd = ["keyword-archive-search", topic, "--limit", "5"]
    code, out, err = run_tool(archive_cmd, timeout=10)
    if code != 0:
        # If archive also fails, just return an empty graph
        return {"nodes": [], "edges": []}
    snippets = out.strip()

    # 2. Prompt the sub‑agent to extract relationships.
    prompt = (
        f"You are given several text snippets about the topic '{topic}'. "
        "Extract entities and their relationships in JSON format with two arrays: "
        "'nodes' (each with an 'id' and optional 'label') and 'edges' "
        "(each with 'source', 'target', and 'type'). "
        "If you cannot find any relationship, return empty arrays.\n\n"
        "Snippets:\n"
        f"{snippets}\n\n"
        "JSON:"
    )
    # The sub‑agent tool expects a single argument query.
    subagent_cmd = ["subagent_ask_helper", prompt]
    code, llm_out, llm_err = run_tool(subagent_cmd, timeout=30)
    if code != 0:
        return {"nodes": [], "edges": []}

    # 3. Parse the LLM output – it may contain surrounding text; extract the first JSON block.
    try:
        # Find the first '{' and the matching '}'
        start = llm_out.find("{")
        end = llm_out.rfind("}")
        json_text = llm_out[start : end + 1] if start != -1 else "{}"
        graph = json.loads(json_text)
        # Ensure the required keys exist
        graph.setdefault("nodes", [])
        graph.setdefault("edges", [])
        return graph
    except Exception:
        return {"nodes": [], "edges": []}

# ------------------------------------------------------------
# Main: orchestrate primary fetcher with fallback
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Resilient Graph Builder")
    parser.add_argument("--topic", required=True, help="Topic / keyword for the graph")
    args = parser.parse_args()
    topic = args.topic

    # 1. Try the primary knowledge_graph_fetcher
    primary_cmd = ["knowledge_graph_fetcher", topic]
    code, out, err = run_tool(primary_cmd, timeout=20)

    if code == 0 and out.strip():
        # Assume the primary tool returns a JSON graph on stdout
        try:
            graph = json.loads(out)
        except Exception:
            # If parsing fails, fall back
            graph = fallback_graph(topic)
    else:
        # Primary failed – use fallback
        graph = fallback_graph(topic)

    # 2. Write the graph to a persistent file in /workspace
    filename = f"{topic.lower().replace(' ', '_')}_knowledge_graph.json"
    out_path = os.path.join("/workspace", filename)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to write graph file: {e}", file=sys.stderr)
        sys.exit(1)

    print(out_path)  # tool contract: print the path of the created file
    sys.exit(0)

if __name__ == "__main__":
    main()
