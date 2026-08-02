# tool: news_plan_tracker
# call: python /mind/tools/own/news_plan_tracker.py <url>
# does: Fetch a news article, create a persistent plan from its content, and output the plan ID
#!/usr/bin/env python3
import sys, subprocess, json, os, shlex

def run_cmd(cmd, input_data=None):
    """Run a shell command, capture stdout, raise on error."""
    result = subprocess.run(
        cmd, input=input_data, capture_output=True, text=True, shell=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\\nstderr: {result.stderr.strip()}")
    return result.stdout.strip()

def main():
    if len(sys.argv) != 2:
        print("Usage: news_plan_tracker <article_url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]

    # 1️⃣ Fetch the article text using the existing `web-fetch` tool.
    # `web-fetch` prints the response body (plain text / HTML). We'll keep it raw.
    article_text = run_cmd(f"web-fetch {shlex.quote(url)}")

    # 2️⃣ Build a concise description for planning.
    # The planner expects a natural‑language goal. We'll prepend a short hint.
    goal = f"Create an actionable plan based on the following article content:\\n\\n{article_text}"

    # 3️⃣ Call the existing `plan_from_question` tool.
    # `plan_from_question` reads the goal from stdin and returns a JSON with the plan ID.
    # We'll feed the goal via stdin.
    plan_output = run_cmd("plan_from_question", input_data=goal)

    # 4️⃣ Extract the plan ID (most tools output the ID as the last line).
    # If the output is pure JSON we try to parse it; otherwise we fall back to raw text.
    plan_id = plan_output
    try:
        data = json.loads(plan_output)
        # common field name used by the planner
        if isinstance(data, dict) and "plan_id" in data:
            plan_id = data["plan_id"]
        elif isinstance(data, dict) and "id" in data:
            plan_id = data["id"]
    except Exception:
        # Not JSON – keep raw output.
        pass

    print(plan_id)

if __name__ == "__main__":
    main()
