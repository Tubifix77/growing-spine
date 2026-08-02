tool: ResearchArchiveSynthesizer
call: research_archive_synthesizer.py <query>
does: Pull prior archived notes for a query, fill any knowledge gaps via LLM, synthesize a full report, and archive the result.

import sys, json, subprocess, textwrap, shlex, os

def run_cmd(cmd, input_data=None):
    """Run a shell command, capture stdout (text) and return it."""
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
        sys.exit(result.returncode)
    return result.stdout.strip()

def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: research_archive_synthesizer.py <query>\\n")
        sys.exit(1)
    query = " ".join(sys.argv[1:])

    # 1️⃣ Search the keyword archive for existing notes
    search_cmd = f'keyword-archive-search {shlex.quote(query)}'
    existing_notes_raw = run_cmd(search_cmd)
    # The archive tool returns newline‑separated JSON objects; collect them.
    notes = []
    for line in existing_notes_raw.splitlines():
        line = line.strip()
        if line:
            try:
                notes.append(json.loads(line))
            except json.JSONDecodeError:
                # If the tool returns plain text, keep it as a string.
                notes.append({"raw": line})

    # 2️⃣ Build a prompt for the LLM:
    #    - Include the original query
    #    - Include any found notes (as bullet list)
    #    - Ask the LLM to produce a comprehensive report,
    #      and explicitly note any knowledge gaps it discovers.
    notes_text = ""
    for i, n in enumerate(notes, 1):
        # Prefer a "content" field, fall back to the whole dict.
        content = n.get("content") or n.get("text") or json.dumps(n)
        notes_text += f"{i}. {content}\\n"

    prompt = textwrap.dedent(f\"\"\"\
        You are asked to write a thorough research report on the topic:
        "{query}"

        Existing notes from the internal knowledge archive (if any):
        {notes_text if notes_text else "(none found)"}

        For this report:
        1. Summarise what is already known from the notes.
        2. Identify any missing information (knowledge gaps).
        3. Retrieve the missing information by briefly searching the web (you may assume you have a generic web‑search capability).
        4. Synthesize a complete answer that covers the topic, filling the gaps.
        5. End the report with a short "Knowledge gaps still unknown" section if any remain.

        Provide the full report in plain text (no JSON wrapper).\"\"\")
    
    # 3️⃣ Ask the LLM via subagent_ask_helper
    #    subagent_ask_helper expects the prompt as a single argument.
    #    We pass it through proper quoting.
    llm_cmd = f'subagent_ask_helper {shlex.quote(prompt)}'
    report = run_cmd(llm_cmd)

    # 4️⃣ Archive the final report
    #    Store under a keyword derived from the query (lower‑case, hyphenated).
    keyword = query.lower().replace(" ", "-")
    # The archive tool expects a JSON line: {"content":"...","tags":[...]}
    archive_entry = json.dumps({
        "content": report,
        "tags": ["research-report", "synthesized"]
    })
    store_cmd = f'keyword-archive-store {shlex.quote(keyword)} {shlex.quote(archive_entry)}'
    run_cmd(store_cmd)

    # 5️⃣ Print the report for the caller's visibility
    print(report)

if __name__ == "__main__":
    main()
