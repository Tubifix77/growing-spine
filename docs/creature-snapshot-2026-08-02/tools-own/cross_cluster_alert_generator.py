#!/usr/bin/env python3
# tool: CrossClusterAlertGenerator
# call: CrossClusterAlertGenerator <keyword>
# does: Monitors real‑time feeds (wake_catchup_fetcher) for a user‑defined keyword,
#       cross‑references historic incidents (keyword‑archive‑search),
#       crafts an alert narrative via subagent_ask_helper,
#       and stores the alert in the keyword‑archive (keyword‑archive‑store).

import json, subprocess, sys, os, shlex, textwrap

def run_cmd(cmd, capture_output=True):
    """Run a shell command safely and return stdout (str)."""
    result = subprocess.run(
        cmd, shell=True, check=False,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nSTDERR: {result.stderr.strip()}")
    return result.stdout.strip()

def fetch_fresh_items():
    """Invoke wake_catchup_fetcher and return a list of dicts."""
    out = run_cmd("wake_catchup_fetcher")
    try:
        items = json.loads(out)
        if not isinstance(items, list):
            raise ValueError
        return items
    except Exception:
        raise RuntimeError("Failed to parse JSON from wake_catchup_fetcher")

def search_historic(keyword, limit=3):
    """Run keyword‑archive‑search and return a list of notes (strings)."""
    out = run_cmd(f"keyword-archive-search {shlex.quote(keyword)}")
    try:
        # The command returns a JSONL of notes; each line is a JSON object.
        notes = []
        for line in out.splitlines():
            obj = json.loads(line)
            notes.append(obj.get("note", ""))
            if len(notes) >= limit:
                break
        return notes
    except Exception:
        # If no notes exist, just return empty list
        return []

def craft_alert(fresh_item, historic_notes):
    """Ask the sub‑agent to synthesize a concise alert."""
    title = fresh_item.get("title", "")
    url   = fresh_item.get("url", "")
    # Build a prompt
    prompt = f"""You are an alert‑generation assistant.

Fresh news item:
Title: {title}
URL: {url}

Relevant historic incidents for the same topic (if any):
{chr(10).join(historic_notes) if historic_notes else "None"}

Produce a short (1‑2 sentence) alert describing why this fresh item is noteworthy,
referencing past incidents when useful. Do NOT include any markup, just plain text."""
    # Call the sub‑agent
    answer = run_cmd(f"subagent_ask_helper {shlex.quote(prompt)}")
    return answer.strip()

def store_alert(keyword, alert):
    """Persist the alert into the keyword‑archive."""
    # Use keyword‑archive‑store: <keyword> <note> [--tags tags]
    # Tags will help later filtering.
    tags = "alert"
    cmd = f"keyword-archive-store {shlex.quote(keyword)} {shlex.quote(alert)} --tags {tags}"
    run_cmd(cmd, capture_output=False)

def main():
    if len(sys.argv) != 2:
        print("Usage: CrossClusterAlertGenerator <keyword>", file=sys.stderr)
        sys.exit(1)

    keyword = sys.argv[1].lower()
    # 1️⃣ Pull fresh items
    try:
        fresh_items = fetch_fresh_items()
    except Exception as e:
        print(f"Error fetching fresh items: {e}", file=sys.stderr)
        sys.exit(1)

    # 2️⃣ Filter items that mention the keyword (case‑insensitive)
    matched = [it for it in fresh_items
               if keyword in it.get("title", "").lower()
               or any(keyword in t.lower() for t in it.get("tags", []))]

    if not matched:
        print(f"No fresh items matched keyword '{keyword}'.")
        sys.exit(0)

    # 3️⃣ For each matched item: historic search → alert → store
    for item in matched:
        historic = search_historic(keyword)
        alert = craft_alert(item, historic)
        store_alert(keyword, alert)
        # Show the alert so the caller sees something useful
        print(f"ALERT STORED: {alert}")

if __name__ == "__main__":
    main()
