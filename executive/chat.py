"""chat.py -- chat queue and conversation log for Growing Spine.

chat.jsonl on the volume stores all entries with these kinds:
  from_tue      -- message Tue sent, may be unread (read=false) or read (read=true)
  from_creature -- creature's text reply to Tue's last message
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


def peek_unread(volume_mount: str):
    """Return (ts, content) of the first unread Tue message WITHOUT marking it
    read, or None. The caller must call mark_read(ts) only AFTER it has actually
    processed the message (i.e. the think call succeeded). This is the B12 fix:
    pop_unread used to mark-read at cycle start, so a message consumed by a cycle
    that then died on quota was lost forever. Peek leaves it in the queue until a
    reply is genuinely produced."""
    for e in _read_all(volume_mount):
        if e.get("kind") == "from_tue" and not e.get("read"):
            return (e.get("ts"), e.get("content", ""))
    return None


def mark_read(volume_mount: str, ts) -> bool:
    """Mark the from_tue message with this timestamp as read. Returns True if a
    matching unread message was found and flipped."""
    entries = _read_all(volume_mount)
    changed = False
    for e in entries:
        if e.get("kind") == "from_tue" and not e.get("read") and e.get("ts") == ts:
            e["read"] = True
            changed = True
            break
    if changed:
        _write_all(volume_mount, entries)
    return changed


def pop_unread(volume_mount: str):
    """DEPRECATED (kept for backwards compatibility). Returns the first unread
    message content and marks it read in one step -- which loses the message if
    the cycle later fails. The executive now uses peek_unread + mark_read instead.
    """
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
    """Extract the creature's reply to a Tue message.

    Tag-only: <reply>...</reply>, unambiguous regardless of what else the
    creature writes around it. Returns "" when absent; the caller re-queues
    the message instead of recording task debris as a reply.
    """
    import re
    m = re.search(r"<reply>(.*?)</reply>", response, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # No fallback: the old before-first-bash-block heuristic captured task
    # cognition ("Okay, let's produce bash block:") as a chat reply when the
    # model ignored the tag. Tag or nothing; the caller retries the message.
    return ""


def bump_attempts(volume_mount: str, ts) -> int:
    """Increment the delivery-attempt counter on an unread Tue message.
    Returns the new attempt count (0 if the message was not found)."""
    entries = _read_all(volume_mount)
    n = 0
    for e in entries:
        if e.get("kind") == "from_tue" and not e.get("read") and e.get("ts") == ts:
            n = int(e.get("attempts", 0)) + 1
            e["attempts"] = n
            break
    if n:
        _write_all(volume_mount, entries)
    return n
