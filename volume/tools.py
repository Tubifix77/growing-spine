"""tools.py — framework tool materialization and catalogue building.

Framework tools are canonical on the host (framework-tools/). At each wake the
executive copies them onto the volume (tools/framework/), overwriting any
tampering — immutability by restoration, the same principle as the protected
prompt. The catalogue (names + one-line descriptions) is injected into context
each cycle so the creature always knows what it can do. Tool bodies are never
injected; the creature reads them on demand with cat.
"""
import json, os, shutil


def _repo_root() -> str:
    # volume/tools.py -> repo root is one level up
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# CANONICAL "is this file still a tool-new shell?" markers.
#
# 2026-08-05: this existed in two disagreeing copies (loop.py's 3-string tuple
# and spine_health.py's single string) and NEITHER matched what tool-new had
# actually been writing. The template says "Replace the body below"; the markers
# hunted "Replace this whole file". Off by four words, and the consequence was
# that SIX organs -- the per-cycle hollow-completion gate, the library-wide
# backlog gate, the daily janitor and their diagnostics -- silently matched
# nothing for their entire existence. Live census the day it was found: 25 hollow
# stubs in tools/own, 0 detected, and a janitor log whose every one of 28 entries
# read "aged-out 0".
#
# Keep the legacy strings: attic files from before the template changed still
# carry them, and a marker that matches nothing costs nothing.
TOOL_PLACEHOLDER_MARKERS = (
    # current template (framework-tools/tool-new)
    "Replace the body below with real executable code",
    "print('not implemented yet: ' + sys.argv[0])",
    "not implemented yet: ",
    # legacy templates, retained for old attic residents
    "DESCRIBE WHAT THIS TOOL DOES",
    "Replace this whole file with real executable code",
    "A file with no real code fails",
)


def is_hollow_stub(body: str) -> bool:
    """True if this file body is still an unfilled tool-new shell."""
    return any(mk in (body or "") for mk in TOOL_PLACEHOLDER_MARKERS)


# CANONICAL "is this feed fabricated?" test. The same disease as is_hollow_stub,
# one stage later: a stub reads healthy and does NOTHING; a fixture reads healthy
# and does something FAKE. Both exit 0.
#
# 2026-08-08 17:14. Testing cross_source_digest_scheduler, the creature wanted
# deterministic input and wrote the fixture OVER the real tool:
#     # Create a simple mock fetcher for testing
#     cat > /mind/tools/own/wake_catchup_fetcher <<'BASH'
# `cat >` bypasses tool-edit, so there was no .bak and no "Rewrote X (44 -> 89
# lines)" line. The upstream source for 55 live tools became two example.com
# stubs, every dependent kept exiting 0 with valid JSON, and nothing was written
# down anywhere.
#
# spine_health's SENSOR was built to catch precisely this, and missed it: it
# hunted the literal title "Mock News Item" while the fixture emitted "Test
# Article 1". Four words apart -- the hollow-stub scar recurring INSIDE the guard
# written against it. Measured before this fix, against the live mock:
# `SENSOR:ok(2 fresh)`. A green light on a fabricated feed.
#
# So the primary test is a fact about the world, not a guessed phrase: RFC 2606
# reserves example.com/.org/.net so they can never carry real content. The title
# list is a backstop; nothing depends on matching one exact string any more.
RESERVED_FEED_HOSTS = ("example.com", "example.org", "example.net",
                       "example.edu", "localhost", "127.0.0.1")
# A failure notice stored as knowledge will be recalled as if it were true.
# 2026-08-17, pre-registered trigger fired: with subagent_ask_helper finally
# failing honestly (nonzero, stderr), a CALLER caught the failure, converted it
# back into the string "Answer not available (fallback)." and archived it tagged
# gap_filled -- the answer-shaped-failure disease resurfacing one level up the
# stack. Phrase list, so backstop only (§5: one rename from silent); the primary
# defences stay the honest-failure contract and the parse-rate fact. Lowercase;
# matched case-insensitively against stored record content.
PLACEHOLDER_ANSWER_MARKERS = ("answer not available", "fallback response for",
                              "not implemented yet", "no fallback available")
FABRICATED_TITLE_MARKERS = ("mock news item", "mock item", "test article",
                            "sample article", "sample item", "test note",
                            "dummy item", "lorem ipsum")


def jsonl_parse_rate(path: str):
    """(parseable, total) non-blank lines of a .jsonl file. (None, None) if unreadable.

    The contract for .jsonl is one record per LINE. Nothing checked it, and the
    same breach has now happened twice under different mechanisms:

      2026-08-07 00:47  keyword-archive-store built records with `jq -n`, whose
        default output is pretty-printed across several lines. 1,670 writes had
        produced 422 records of which the reader could parse 18. Fixed to
        `jq -nc` with the creature's consent.
      2026-08-08 12:15  the creature rewrote that tool from scratch and undid it
        -- not with jq this time, but `json_entry=$(cat <<JSON ...)`, multi-line
        again. Within hours: 104 lines, 4 parseable. The advice it had been given
        named a MECHANISM ("don't use jq -n"), so it avoided jq and walked into
        the same wall by another route.

    Both times the write succeeded, the read came back empty, and neither side
    errored -- keyword-archive-search's contract is to return nothing rather than
    fail. A reader that cannot parse its own store is the house disease: healthy
    surface, no content. Measure the rate; never trust the extension.

    Scans the WHOLE file, no sampling. A complete JSON value on its own line must
    open and close with a matching bracket, and that test is free -- it rejects
    every continuation line of a multi-line record without calling json.loads. In
    the pathological case that is 3 of every 4 lines, so the full scan is cheaper
    than the capped sample it replaces (2026-08-11: a 16,862-line archive scanned
    in milliseconds).
    """
    try:
        parseable = total = 0
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                if not ((line[0] == "{" and line[-1] == "}")
                        or (line[0] == "[" and line[-1] == "]")):
                    continue          # cannot be a complete record; no parse
                try:
                    json.loads(line)
                    parseable += 1
                except ValueError:
                    pass
        return parseable, total
    except OSError:
        return None, None


def parse_feed_items(text):
    """A fetcher's stdout as a list of items -- JSON array OR one object per line.

    Returns [] for empty output and None when neither shape yields anything.

    2026-08-09. The SENSOR assumed a JSON array. The creature rewrote its fixture
    to emit one object per line; `json.loads(whole_output)` raised, the sensor
    reported `SENSOR:fail(JSONDecodeError)` -- indistinguishable from the network
    being down -- and is_fabricated_feed() was never reached. A guard that assumes
    one output SHAPE is the same fault as one that assumes one exact string, and
    it was written into this file the day before by the same hand. Accept both
    shapes; decide fabrication separately.
    """
    text = (text or "").strip()
    if not text:
        return []
    try:
        v = json.loads(text)
        return v if isinstance(v, list) else [v]
    except ValueError:
        pass
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except ValueError:
            continue
    return items or None


def is_fabricated_feed(items) -> bool:
    """True if a parsed feed is fixture data rather than really-fetched content."""
    if not isinstance(items, list):
        return False
    for it in items:
        if not isinstance(it, dict):
            continue
        url = str(it.get("url") or it.get("link") or "").lower()
        if any(h in url for h in RESERVED_FEED_HOSTS):
            return True
        title = str(it.get("title") or "").lower()
        if any(m in title for m in FABRICATED_TITLE_MARKERS):
            return True
    return False


# A shell the creature keeps REACHING FOR is demand, not abandonment.
#
# 2026-08-06: with the markers finally matching, 22 of 25 hollow stubs were old
# enough for the janitor. But two independent usage counters agreed that 8 of
# them are called repeatedly -- 34, 29, 21, 18, 15, 14, 13 and 10 invocations,
# every one of which printed "not implemented yet" and returned nothing. Attic
# those and the creature reaches for a tool it uses weekly and gets
# "command not found" -- the materializer scar's exact shape, which it once
# rationalised 715 times as its own tools' bugs. So: the janitor sweeps
# abandonment, and demand goes to the finish_stub organ instead.
#
# DEMAND_FLOOR is not a guess. The live distribution splits cleanly: the demanded
# group bottoms out at 10 invocations, the next stub down has 4. 5 sits in the gap.
DEMAND_FLOOR = 5


def _norm_tool_key(k: str) -> str:
    """Counter keys arrive as bare names, filenames and occasionally paths."""
    k = os.path.basename(str(k))
    return k[:-3] if k.endswith(".py") else k


def demand_counts(volume_mount: str) -> dict:
    """Merged invocation counts per tool, from BOTH usage counters.

    There are two, with different shapes and neither is authoritative:
    `tool_usage.json` is flat name->int, `state/tool_usage_cache.json` nests
    under "counts". They disagree per-tool (one records 2 where the other
    records 10), so the merge takes the MAX: "reached for at least this often".
    """
    out = {}
    sources = []
    try:
        with open(os.path.join(volume_mount, "tool_usage.json"),
                  encoding="utf-8") as f:
            sources.append(json.load(f))
    except Exception:
        pass
    try:
        with open(os.path.join(volume_mount, "state", "tool_usage_cache.json"),
                  encoding="utf-8") as f:
            sources.append(json.load(f).get("counts", {}))
    except Exception:
        pass
    for src in sources:
        if not isinstance(src, dict):
            continue
        for k, v in src.items():
            if isinstance(v, int):
                nk = _norm_tool_key(k)
                out[nk] = max(out.get(nk, 0), v)
    return out


def is_demanded(name: str, counts: dict) -> bool:
    """True if this tool has been invoked enough to count as demand."""
    return counts.get(_norm_tool_key(name), 0) >= DEMAND_FLOOR


def materialize_framework(volume_mount: str):
    """Copy canonical framework tools onto the volume, overwriting. Idempotent."""
    src = os.path.join(_repo_root(), "framework-tools")
    dst = os.path.join(volume_mount, "tools", "framework")
    os.makedirs(dst, exist_ok=True)
    os.makedirs(os.path.join(volume_mount, "tools", "own"), exist_ok=True)
    if not os.path.isdir(src):
        return
    for existing in os.listdir(dst):
        try:
            os.remove(os.path.join(dst, existing))
        except OSError:
            pass
    for name in os.listdir(src):
        if name.startswith((".", "__")) or name.endswith((".pyc", ".bak", ".tmp", ".swp")):
            continue  # junk, never a framework tool
        s = os.path.join(src, name)
        if not os.path.isfile(s):
            continue  # a stray __pycache__ dir crashed the copy loop post-wipe (Jul 10-14)
        d = os.path.join(dst, name)
        try:
            with open(s) as _f:
                text = _f.read()
            with open(d, "w", newline="\n") as _f:
                _f.write(text)
        except (OSError, UnicodeDecodeError):
            shutil.copy2(s, d)
        os.chmod(d, 0o755)


NON_TOOL_SUFFIXES = (".md", ".json", ".txt")
TOOL_EXTENSIONS = ("py", "sh", "bash", "txt")


def is_tool_file(name: str) -> bool:
    """Is this directory entry a TOOL the creature built? (audit P2-F2)

    There were several answers: loop excluded dotfiles and .md/.json/.txt,
    idea_gate excluded only junk, the architect census excluded only dotfiles --
    so the same library counted as 345, 349 and 387 tools depending on who asked,
    and every one of those numbers was shown to an LLM as fact.
    """
    from executive.embed_gate import _is_junk
    return not (name.startswith(".") or name.endswith(NON_TOOL_SUFFIXES)
                or _is_junk(name))


def list_tools(dirpath: str) -> list:
    """Sorted names of the actual tool FILES in a tools dir (audit P2-F2).

    The isfile check belongs here, not in every caller: on 2026-08-06 the
    architect census counted 349 where loop counted 346, and the three extras
    were DIRECTORIES the creature had created with tool-shaped names
    (`cross_cluster_signal_router`, `knowledge_gap_alert_planner`, `__pycache__`).
    A predicate that takes only a name cannot know that, so callers kept
    forgetting it -- which is what made three answers possible in the first place.
    """
    try:
        return sorted(n for n in os.listdir(dirpath)
                      if is_tool_file(n)
                      and os.path.isfile(os.path.join(dirpath, n)))
    except OSError:
        return []


def tool_stem(name: str) -> str:
    """A tool's name with one trailing tool extension removed (audit P2-F14).

    Two definitions existed: loop stripped `.py|.sh` ("only the extensions we
    actually see"), the architect stripped `.py|.sh|.bash|.txt`. So `X` and
    `X.bash` were twins to one and strangers to the other, and the collision scan
    and the lineage census disagreed about what a sibling was.
    """
    import re as _re
    return _re.sub(r"\.(" + "|".join(TOOL_EXTENSIONS) + r")$", "", name)


def tool_description(path: str) -> str:
    """THE description of a tool file. Canonical since 2026-08-06 (audit P2-F6).

    There were several extractors with materially different answers, and the
    embedding index used the STRICTEST one -- so a tool could be listed in the
    catalogue with a perfectly good description while being invisible to semantic
    dedup and to tool-find, which is how near-duplicates slip past the gate.
    Precedence, most explicit first: the creature's own `does:` line, then the
    first meaningful docstring/comment line.
    """
    return _first_doc_line(path)


def _first_doc_line(path: str) -> str:
    """Extract a one-line description from a tool file.
    Prefers a 'does: ...' line (creature's own format), then falls back
    to first meaningful non-boilerplate line (docstring, comment, etc).
    """
    try:
        with open(path) as f:
            lines = f.readlines()
        # Prefer explicit 'does:' line anywhere in the file
        for line in lines:
            s = line.strip()
            if s.lower().startswith("does:"):
                return s[5:].strip()
            if s.lower().startswith("# does:"):
                return s[7:].strip()
        # Fall back to first meaningful non-boilerplate line
        for line in lines:
            s = line.strip().strip('"').strip("'").strip("#").strip()
            if s and not s.startswith(("!", "import", "from", "def ", "class ", "tool:", "call:")):
                return s
    except Exception:
        pass
    return "(no description)"


def build_catalogue(volume_mount: str) -> str:
    """Compact tool catalogue for injection. Names + one-line descriptions only."""
    fw = os.path.join(volume_mount, "tools", "framework")
    own = os.path.join(volume_mount, "tools", "own")
    lines = ["Your tools (run them as commands in a bash block):",
             "(too many to skim -- ask by meaning: tool-find \"what you need\")",
             "", "Built-in (always available):"]
    if os.path.isdir(fw) and os.listdir(fw):
        for name in sorted(os.listdir(fw)):
            lines.append(f"  {name} - {_first_doc_line(os.path.join(fw, name))}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Tools you made (in /mind/tools/own):")
    if os.path.isdir(own) and os.listdir(own):
        for name in sorted(os.listdir(own)):
            lines.append(f"  {name} - {_first_doc_line(os.path.join(own, name))}")
    else:
        lines.append("  (none yet - make one with: tool-new <name>)")
    return "\n".join(lines)
