"""parser.py — extract bash blocks from LLM output. From VibeOS lineage."""
import re

_CODE = re.compile(r"```(\w*)\s*\n(.*?)\n\s*```", re.DOTALL)


def parse_bash_blocks(text: str) -> list:
    """Return list of bash command strings found in text."""
    blocks = []
    for m in _CODE.finditer(text):
        lang = m.group(1).lower()
        code = m.group(2).strip()
        if lang in ("bash", "sh") and code:
            blocks.append(code)
    return blocks


def strip_bash_blocks(text: str) -> str:
    cleaned = _CODE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
