"""journal.py — append-only JSONL journal on the volume."""
import json, time, os

JOURNAL_PATH = "/mind/journal.jsonl"  # path inside container / on volume


def _host_journal_path(volume_mount: str) -> str:
    """Host-side path when writing from the executive directly."""
    return os.path.join(volume_mount, "journal.jsonl")


def append(volume_mount: str, kind: str, content: str, meta: dict = None):
    """Append one entry to the host-side journal file."""
    entry = {
        "ts": time.time(),
        "kind": kind,   # e.g. "wake", "sleep", "think", "exec", "error"
        "content": content,
    }
    if meta:
        entry.update(meta)
    path = _host_journal_path(volume_mount)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def recent(volume_mount: str, n: int = 20) -> list:
    """Return the last n journal entries as dicts."""
    path = _host_journal_path(volume_mount)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    entries = []
    for line in lines[-n:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries
