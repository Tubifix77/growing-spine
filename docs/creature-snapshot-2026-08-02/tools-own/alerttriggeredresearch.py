tool: alerttriggeredresearch
call: alerttriggeredresearch --watch <keyword>
does: Continuously monitors feeds via wake_catchup_fetcher; on detecting a configured keyword, it launches knowledge_gap_filler to fetch missing details and stores the insights with keyword-archive-store.
#!/usr/bin/env python3
import argparse
import subprocess
import json
import sys
import time

def run_cmd(cmd):
    """Runs a shell command and returns stdout."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {cmd}: {e.stderr}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Monitor feeds for keywords and trigger research.")
    parser.add_argument("--watch", required=True, help="Keyword to monitor")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    args = parser.parse_args()

    keyword = args.watch
    print(f"Monitoring feeds for: {keyword}...")

    try:
        while True:
            # 1. Fetch fresh items
            # wake_catchup_fetcher returns a JSON array of {title, url, tags}
            fetch_out = run_cmd("wake_catchup_fetcher")
            if not fetch_out:
                time.sleep(args.interval)
                continue

            try:
                items = json.loads(fetch_out)
            except json.JSONDecodeError:
                print("Failed to parse fetcher output as JSON", file=sys.stderr)
                items = []

            for item in items:
                title = item.get("title", "").lower()
                url = item.get("url", "")
                
                if keyword.lower() in title:
                    print(f"MATCH FOUND: {item.get('title')}")
                    
                    # 2. Launch knowledge_gap_filler to fetch missing details
                    # knowledge_gap_filler usually takes a query
                    query = f"Detailed information about {keyword} from this source: {url}"
                    print(f"Filling knowledge gaps for: {keyword}...")
                    research_out = run_cmd(f"knowledge_gap_filler '{query}'")
                    
                    if research_out:
                        # 3. Store insights with keyword-archive-store
                        # Usage: keyword-archive-store <keyword> <content>
                        # We wrap the content in a shell-safe string.
                        store_cmd = f"keyword-archive-store '{keyword}' '{research_out}'"
                        run_cmd(store_cmd)
                        print(f"Successfully archived research for {keyword}.")
                    else:
                        print(f"No research output generated for {keyword}.")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopping monitor...")

if __name__ == "__main__":
    main()
