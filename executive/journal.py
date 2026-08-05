"""journal.py — append-only JSONL journal on the volume."""
import json, time, os


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


def last_of_kind(volume_mount: str, kind: str) -> dict | None:
    """Return the most recent journal entry of the given kind, or None."""
    path = _host_journal_path(volume_mount)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for line in reversed(lines):
        try:
            e = json.loads(line)
            if e.get("kind") == kind:
                return e
        except json.JSONDecodeError:
            pass
    return None


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

def atomic_json(path, obj, indent=None):
    """tmp + os.replace. Five state files were written with a plain
    open(w)+json.dump, so a crash mid-write truncated them -- and every loader
    treats corrupt-as-empty, silently amputating that organ's memory (audit
    cluster F, 2026-08-05). The idiom already existed ten lines from one of the
    offenders; the habit is what was missing."""
    import json as _json, os as _os
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        _json.dump(obj, f, indent=indent)
    _os.replace(tmp, path)
