#!/usr/bin/env python3
"""
memory_gap_filler
does: Retrieve a fact from memstore; if missing, run knowledge_gap_filler to fetch it,
      store the result back into memstore (and long‑term memory), and return the answer.
"""

import subprocess
import sys
import json
import shlex

def run_cmd(cmd):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

def get_memstore(key):
    out, err, rc = run_cmd(f"memstore get {shlex.quote(key)}")
    if rc != 0:
        return None
    try:
        data = json.loads(out)
        return data.get("value")
    except json.JSONDecodeError:
        return out if out else None

def set_memstore(key, value):
    escaped = json.dumps(value)
    run_cmd(f"memstore set {shlex.quote(key)} {escaped}")

def remember_fact(key, value):
    run_cmd(f'remember {shlex.quote(key)} {shlex.quote(value)}')

def fill_gap(key):
    out, err, rc = run_cmd(f'knowledge_gap_filler {shlex.quote(key)}')
    if rc != 0:
        return None
    return out

def main():
    if len(sys.argv) != 2:
        print("Usage: memory_gap_filler <query>", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]

    existing = get_memstore(query)
    if existing:
        print(existing)
        sys.exit(0)

    fetched = fill_gap(query)
    if not fetched:
        print(f"Error: could not retrieve information for '{query}'", file=sys.stderr)
        sys.exit(1)

    set_memstore(query, fetched)
    remember_fact(query, fetched)

    print(fetched)

if __name__ == "__main__":
    main()
