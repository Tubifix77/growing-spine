"""tools.py — framework tool materialization and catalogue building.

Framework tools are canonical on the host (framework-tools/). At each wake the
executive copies them onto the volume (tools/framework/), overwriting any
tampering — immutability by restoration, the same principle as the protected
prompt. The catalogue (names + one-line descriptions) is injected into context
each cycle so the creature always knows what it can do. Tool bodies are never
injected; the creature reads them on demand with cat.
"""
import os, shutil


def _repo_root() -> str:
    # volume/tools.py -> repo root is one level up
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
        d = os.path.join(dst, name)
        shutil.copy2(os.path.join(src, name), d)
        os.chmod(d, 0o755)


def _first_doc_line(path: str) -> str:
    try:
        with open(path) as f:
            for line in f:
                s = line.strip().strip('"').strip("'").strip("#").strip()
                if s and not s.startswith(("!", "import", "from", "def ", "class ")):
                    return s
    except Exception:
        pass
    return "(no description)"


def build_catalogue(volume_mount: str) -> str:
    """Compact tool catalogue for injection. Names + one-line descriptions only."""
    fw = os.path.join(volume_mount, "tools", "framework")
    own = os.path.join(volume_mount, "tools", "own")
    lines = ["Your tools (run them as commands in a bash block):",
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
