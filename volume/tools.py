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
