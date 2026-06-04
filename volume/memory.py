"""memory.py — three-tier layered memory store for Growing Spine.

Layer 1 (working):      last 5 entries, full content, always injected.
Layer 2 (intermediate): entries 6-50, one-line headline, always injected.
Layer 3 (archive):      entries 51+, key/theme only, always injected.

recall(query) fetches full content from any layer on demand.
"""
import sqlite3, os, time

DB_FILENAME = "memory.db"

LAYER1_SIZE = 5    # working memory — full content
LAYER2_MAX  = 50   # intermediate ceiling (entries 6-50)
                   # entries 51+ are archive


def _db(volume_mount: str) -> sqlite3.Connection:
    path = os.path.join(volume_mount, DB_FILENAME)
    conn = sqlite3.connect(path, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(volume_mount: str):
    """Create the memories table if it does not exist (idempotent)."""
    with _db(volume_mount) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                key     TEXT NOT NULL,
                value   TEXT NOT NULL,
                tags    TEXT DEFAULT '',
                created REAL NOT NULL,
                updated REAL NOT NULL
            )
        """)


def store(volume_mount: str, key: str, value: str, tags: list = None):
    """Write or update a memory entry by key."""
    tags_str = ",".join(tags) if tags else ""
    now = time.time()
    with _db(volume_mount) as conn:
        existing = conn.execute(
            "SELECT id FROM memories WHERE key=?", (key,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE memories SET value=?, tags=?, updated=? WHERE key=?",
                (value, tags_str, now, key)
            )
        else:
            conn.execute(
                "INSERT INTO memories (key, value, tags, created, updated) "
                "VALUES (?,?,?,?,?)",
                (key, value, tags_str, now, now)
            )


def _all_by_recency(volume_mount: str) -> list:
    """Return all memories newest-first as dicts."""
    with _db(volume_mount) as conn:
        rows = conn.execute(
            "SELECT key, value, tags, updated "
            "FROM memories ORDER BY id DESC"
        ).fetchall()
    return [
        {"key": r[0], "value": r[1], "tags": r[2], "updated": r[3]}
        for r in rows
    ]


def layer1(volume_mount: str) -> list:
    """Last 5 memories — full content."""
    return _all_by_recency(volume_mount)[:LAYER1_SIZE]


def layer2_headlines(volume_mount: str) -> list:
    """Entries 6-50 — key + one-line headline (first 120 chars of value)."""
    all_m = _all_by_recency(volume_mount)
    intermediate = all_m[LAYER1_SIZE:LAYER2_MAX]
    return [
        {
            "key": m["key"],
            "headline": m["value"][:120].replace("\n", " "),
        }
        for m in intermediate
    ]


def layer3_themes(volume_mount: str) -> list:
    """Entries 51+ — keys/themes only."""
    all_m = _all_by_recency(volume_mount)
    return [m["key"] for m in all_m[LAYER2_MAX:]]


def retrieve(volume_mount: str, key: str) -> dict:
    """Get a single memory by key. Returns None if not found."""
    with _db(volume_mount) as conn:
        row = conn.execute(
            "SELECT key, value, tags, updated FROM memories WHERE key=?", (key,)
        ).fetchone()
    if row is None:
        return None
    return {"key": row[0], "value": row[1], "tags": row[2], "updated": row[3]}


def search_by_tag(volume_mount: str, tag: str) -> list:
    """Find all memories matching a tag."""
    with _db(volume_mount) as conn:
        rows = conn.execute(
            "SELECT key, value, tags, updated FROM memories "
            "WHERE tags LIKE ? ORDER BY id DESC",
            (f"%{tag}%",)
        ).fetchall()
    return [
        {"key": r[0], "value": r[1], "tags": r[2], "updated": r[3]}
        for r in rows
    ]


def delete(volume_mount: str, key: str) -> bool:
    """Delete a memory by key. Returns True if deleted, False if not found."""
    with _db(volume_mount) as conn:
        cursor = conn.execute("DELETE FROM memories WHERE key=?", (key,))
        return cursor.rowcount > 0


def count(volume_mount: str) -> int:
    """Count total number of memories."""
    with _db(volume_mount) as conn:
        return conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]



def recall(volume_mount: str, query: str, limit: int = 10) -> list:
    """
    Search all memories for query string across key, value, and tags.
    Returns full entries, newest first.
    """
    q = f"%{query}%"
    with _db(volume_mount) as conn:
        rows = conn.execute(
            "SELECT key, value, tags, updated FROM memories "
            "WHERE key LIKE ? OR value LIKE ? OR tags LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (q, q, q, limit)
        ).fetchall()
    return [
        {"key": r[0], "value": r[1], "tags": r[2], "updated": r[3]}
        for r in rows
    ]


def recent(volume_mount: str, n: int = 5) -> list:
    """Backwards-compatible alias for layer1 (used by observer and tests)."""
    return _all_by_recency(volume_mount)[:n]
