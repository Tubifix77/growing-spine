tool: dynamic_faq_updater_from_news
does: Fetch recent news for a topic, generate FAQ pairs, and store them in the keyword‑archive.
#!/usr/bin/env python3
"""
dynamic_faq_updater_from_news
--------------------------------
Fetch recent news for a given topic, generate FAQ Q&A pairs via the existing
dynamic_faq_updater tool, and store each pair in the keyword‑archive.

Arguments:
    <topic>   The search term to fetch news for (e.g. "Kimi K3").

Workflow:
1. Call `wake_catchup_fetcher <topic>` – returns a JSON array of news items.
2. For each item, download its URL (via `fetch_url`) and pipe the content to
   `dynamic_faq_updater` which writes FAQ entries (one JSON per line) to stdout.
3. For every generated FAQ entry, invoke `keyword-archive-store` with the
   keyword "faq-<topic>" and the JSON payload, adding a tag for the source URL.
4. Print a short summary of how many entries were created.

Output:
    Prints "Added N FAQ entries for <topic>" on success.
"""

import json
import os
import sys
import subprocess
import tempfile

def run_cmd(cmd, **kwargs):
    """Run a shell command, capture stdout, raise on error."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\\nstderr: {result.stderr.strip()}")
    return result.stdout.strip()

def main():
    if len(sys.argv) != 2:
        print("Usage: dynamic_faq_updater_from_news <topic>", file=sys.stderr)
        sys.exit(1)

    topic = sys.argv[1]

    # 1. Fetch recent news items for the topic
    try:
        raw_news = run_cmd(f"wake_catchup_fetcher {topic}")
        news_items = json.loads(raw_news)
    except Exception as e:
        print(f"Failed to fetch news for '{topic}': {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(news_items, list) or not news_items:
        print(f"No news items returned for '{topic}'.", file=sys.stderr)
        sys.exit(1)

    total_faq = 0

    for item in news_items:
        url = item.get("url")
        title = item.get("title", "")
        if not url:
            continue

        # 2. Download article content
        try:
            article_text = run_cmd(f"fetch_url {url}")
        except Exception as e:
            print(f"Skipping URL {url}: {e}", file=sys.stderr)
            continue

        # 3. Write article to a temporary file for dynamic_faq_updater
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp.write(article_text)
            tmp_path = tmp.name

        # 4. Run dynamic_faq_updater on the article file
        try:
            # dynamic_faq_updater expects a file path argument
            faq_output = run_cmd(f"dynamic_faq_updater {tmp_path}")
        except Exception as e:
            os.unlink(tmp_path)
            print(f"FAQ generation failed for {url}: {e}", file=sys.stderr)
            continue
        finally:
            os.unlink(tmp_path)   # clean up temp file

        # 5. Each line is a JSON FAQ entry
        for line in faq_output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                print(f"Invalid FAQ JSON from {url}: {line}", file=sys.stderr)
                continue

            # Add source tag for traceability
            entry.setdefault("tags", [])
            entry["tags"].append(url)

            # Store in archive under a topic‑specific keyword
            faq_keyword = f"faq-{topic}"
            entry_json = json.dumps(entry, ensure_ascii=False)

            try:
                run_cmd(f'keyword-archive-store "{faq_keyword}" \'{entry_json}\'')
                total_faq += 1
            except Exception as e:
                print(f"Failed to store FAQ entry for {url}: {e}", file=sys.stderr)

    print(f"Added {total_faq} FAQ entries for {topic}")

if __name__ == "__main__":
    main()
