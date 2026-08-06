"""parser.py — extract bash blocks from LLM output. From VibeOS lineage."""
import re

_CODE = re.compile(r"```(\w*)\s*\n(.*?)\n\s*```", re.DOTALL)


def parse_bash_blocks(text: str) -> list:
    """Return list of bash command strings found in text.

    Identical commands are de-duplicated within a single response (keeping the
    first occurrence, preserving order). Weak models often emit the same fenced
    block several times in one reply; running it N times produces identical
    output and is pure waste — and it amplifies observe-without-act loops.
    """
    blocks = []
    seen = set()
    for m in _CODE.finditer(text):
        lang = m.group(1).lower()
        code = m.group(2).strip()
        if lang in ("bash", "sh") and code and code not in seen:
            seen.add(code)
            blocks.append(code)
    return blocks


