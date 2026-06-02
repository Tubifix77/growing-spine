"""memory.py — SQLite memory store on the persistent volume."""
import sqlite3, os, time, json

DB_FILENAME = "memory.db"

def _db_path(volume_mount: str) -> str:
    return os.path.join(volume_mount, DB_FILENAME)

def init_db(volume_mount: str):
    """Create tables if they don't exist."""
    conn = sqlite3.connect(_db_path(volume_mount))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            key       TEXT NOT NULL,
            value     TEXT NOT NULL,
            tags      TEXT DEFAULT '',
            created   REAL NOT NULL,
            updated   REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_key ON memories(key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)")
    conn.commit()
    conn.close()

def store(volume_mount: str, key: str, value: str, tags: list = None):
    """Insert or replace a memory by key."""
    now = time.time()
    tag_str = ",".join(tags or [])
    conn = sqlite3.connect(_db_path(volume_mount))
    existing = conn.execute("SELECT id FROM memories WHERE key=?", (key,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE memories SET value=?, tags=?, updated=? WHERE key=?",
            (value, tag_str, now, key)
        )
    else:
        conn.execute(
            "INSERT INTO memories (key, value, tags, created, updated) VALUES (?,?,?,?,?)",
            (key, value, tag_str, now, now)
        )
    conn.commit()
    conn.close()

def retrieve(volume_mount: str, key: str) -> dict | None:
    """Retrieve a memory by exact key."""
    conn = sqlite3.connect(_db_path(volume_mount))
    row = conn.execute(
        "SELECT key, value, tags, created, updated FROM memories WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"key": row[0], "value": row[1], "tags": row[2].split(","), "created": row[3], "updated": row[4]}

def search_by_tag(volume_mount: str, tag: str, limit: int = 20) -> list:
    """Return memories that have a given tag."""
    conn = sqlite3.connect(_db_path(volume_mount))
    rows = conn.execute(
        "SELECT key, value, tags, created, updated FROM memories WHERE tags LIKE ? ORDER BY updated DESC LIMIT ?",
        (f"%{tag}%", limit)
    ).fetchall()
    conn.close()
    return [{"key": r[0], "value": r[1], "tags": r[2].split(","), "created": r[3], "updated": r[4]} for r in rows]

def recent(volume_mount: str, n: int = 10) -> list:
    """Return the n most recently updated memories."""
    conn = sqlite3.connect(_db_path(volume_mount))
    rows = conn.execute(
        "SELECT key, value, tags, created, updated FROM memories ORDER BY updated DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [{"key": r[0], "value": r[1], "tags": r[2].split(","), "created": r[3], "updated": r[4]} for r in rows]

def delete(volume_mount: str, key: str) -> bool:
    """Delete a memory by key. Returns True if deleted."""
    conn = sqlite3.connect(_db_path(volume_mount))
    cur = conn.execute("DELETE FROM memories WHERE key=?", (key,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0

def count(volume_mount: str) -> int:
    conn = sqlite3.connect(_db_path(volume_mount))
    n = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    conn.close()
    return n
