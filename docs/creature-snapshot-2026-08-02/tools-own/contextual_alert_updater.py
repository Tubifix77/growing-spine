#!/usr/bin/env python3
# tool: contextual_alert_updater
# call: contextual_alert_updater <topic>
# does: Generate concise contextual alerts for a given topic from fresh Hacker News items and store them in the keyword‑archive.

import sys
import json
import subprocess
import datetime
import shlex

def run_cmd(cmd, input_data=None):
    """Run a shell command, optionally feeding stdin, and return stdout (str)."""
    result = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
        shell=True,
        executable="/bin/bash"
    )
    return result.stdout.strip()

def fetch_fresh_items():
    """Fetch fresh Hacker News items using the real wake_catchup_fetcher."""
    # The real fetcher writes JSON to stdout.
    return json.loads(run_cmd("wake_catchup_fetcher.real"))

def filter_items_by_topic(items, topic, max_items=5):
    """Return up to max_items items whose title contains the topic (case‑insensitive)."""
    topic_lc = topic.lower()
    matched = [it for it in items if topic_lc in it.get("title", "").lower()]
    return matched[:max_items]

def generate_alert(item, topic):
    """Ask the sub‑agent to produce a 2‑sentence alert for the given item."""
    prompt = (
        f"Summarize the following news item in two short sentences, focusing on why it matters for \"{topic}\":\n"
        f"Title: {item.get('title','')}\n"
        f"URL: {item.get('url','')}\n"
    )
    # subagent_ask_helper reads the prompt from stdin and outputs the answer.
    answer = run_cmd("subagent_ask_helper", input_data=prompt)
    return answer.strip()

def store_alert(topic, item, alert_text):
    """Store the alert JSON in the keyword‑archive under the keyword 'alert-<topic>'."""
    now_iso = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    alert_record = {
        "topic": topic,
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "alert": alert_text,
        "fetched_at": now_iso
    }
    # Use keyword-archive-store: keyword-archive-store <keyword> <json>
    keyword = f"alert-{topic.replace(' ', '-').lower()}"
    json_blob = json.dumps(alert_record, ensure_ascii=False)
    # Escape the JSON so the shell sees it as a single argument
    escaped_json = shlex.quote(json_blob)
    run_cmd(f"keyword-archive-store {shlex.quote(keyword)} {escaped_json}")
    return keyword

def main():
    if len(sys.argv) < 2:
        print("Usage: contextual_alert_updater <topic>", file=sys.stderr)
        sys.exit(1)

    topic = " ".join(sys.argv[1:]).strip()
    try:
        items = fetch_fresh_items()
    except subprocess.CalledProcessError as e:
        print(f"Failed to fetch fresh items: {e}", file=sys.stderr)
        sys.exit(1)

    matches = filter_items_by_topic(items, topic)
    if not matches:
        print(f"No fresh Hacker News items matched topic '{topic}'.")
        sys.exit(0)

    created = []
    for itm in matches:
        try:
            alert = generate_alert(itm, topic)
            kw = store_alert(topic, itm, alert)
            created.append((kw, itm.get("title", ""), itm.get("url", "")))
        except subprocess.CalledProcessError as e:
            print(f"Error processing item '{itm.get('title','')}' – {e}", file=sys.stderr)
            continue

    # Report what was stored
    print(f"Created {len(created)} alert(s) for topic '{topic}':")
    for idx, (kw, title, url) in enumerate(created, 1):
        print(f"{idx}. [{kw}] {title} – {url}")

if __name__ == "__main__":
    main()
