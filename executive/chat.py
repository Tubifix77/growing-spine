"""chat.py — chat queue and conversation log for Growing Spine.

chat.jsonl on the volume stores all entries with these kinds:
  from_tue      — message Tue sent, may be unread (read=false) or read (read=true)
  from_creature — creature's text reply to Tue's last message
"""
import json, os, time

CHAT_FILENAME = "chat.jsonl"


def _path(volume_mount: str) -> str:
    return os.path.join(volume_mount, CHAT_FILENAME)


def _read_all(volume_mount: str) -> list:
    p = _path(volume_mount)
    if not os.path.exists(p):
        return []
    entries = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def _write_all(volume_mount: str, entries: list):
    with open(_path(volume_mount), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def enqueue(volume_mount: str, message: str):
    """Observer calls this when Tue sends a message."""
    entry = {
        "ts": time.time(),
        "kind": "from_tue",
        "content": message,
        "read": False,
    }
    with open(_path(volume_mount), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def pop_unread(volume_mount: str) -> str | None:
    """Executive calls this at cycle start. Returns first unread message and marks it read."""
    entries = _read_all(volume_mount)
    for i, e in enumerate(entries):
        if e.get("kind") == "from_tue" and not e.get("read"):
            entries[i]["read"] = True
            _write_all(volume_mount, entries)
            return e["content"]
    return None


def record_reply(volume_mount: str, reply: str):
    """Executive calls this after think_end when a Tue message was in context."""
    entry = {
        "ts": time.time(),
        "kind": "from_creature",
        "content": reply,
    }
    with open(_path(volume_mount), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def all_messages(volume_mount: str) -> list:
    """Observer calls this to render the chat tab."""
    return _read_all(volume_mount)


def extract_text_reply(response: str) -> str:
    """Pull text before the first bash block. Falls back to full response if no bash."""
    import re
    match = re.search(r"```bash", response, re.IGNORECASE)
    if match:
        text = response[:match.start()].strip()
    else:
        text = response.strip()
    return text if text else ""
