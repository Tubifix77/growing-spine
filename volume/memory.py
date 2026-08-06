"""memory.py — three-tier layered memory store for Growing Spine.

Layer 1 (working):      last 5 entries, full content, always injected.
Layer 2 (intermediate): entries 6-50, one-line headline, always injected.
Layer 3 (archive):      entries 51+, key/theme only, always injected.

recall(query) fetches full content from any layer on demand.
"""
import sqlite3, os, time, re

DB_FILENAME = "memory.db"

LAYER1_SIZE = 5    # working memory — full content
LAYER2_MAX  = 50   # intermediate ceiling (entries 6-50)
                   # entries 51+ are archive


# Executive control-state keys: already surfaced via the active-project block,
# so they are excluded from the ranked memory layers (they otherwise crowd out
# genuine memory). The creature's own ad-hoc keys are NOT listed here.
CONTROL_KEYS = {
    "current-project", "current-phase", "current-plan",
    "current-project-done-when", "completed-projects", "completed-log",
}


def _db(volume_mount: str) -> sqlite3.Connection:
    path = os.path.join(volume_mount, DB_FILENAME)
    conn = sqlite3.connect(path, timeout=5)
    conn.execute("PRAGMA journal_mode=DELETE")  # rollback journal works across the Docker bind mount; WAL shared-memory does not
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
        cols = [r[1] for r in conn.execute("PRAGMA table_info(memories)").fetchall()]
        if "project" not in cols:
            conn.execute(
                "ALTER TABLE memories ADD COLUMN project TEXT NOT NULL DEFAULT ''"
            )


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


def forget(volume_mount: str, key: str) -> bool:
    """Delete a memory entry by key. Returns True if a row was removed.
    Unlike store("") -- which leaves an empty-valued row still occupying a
    working-memory slot -- this removes the entry from the recency pool
    entirely."""
    with _db(volume_mount) as conn:
        cur = conn.execute("DELETE FROM memories WHERE key=?", (key,))
        return cur.rowcount > 0


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


def _slug(text: str) -> str:
    """Stable project slug from a current-project value: the title before the
    first ':' (or first 60 chars), lowercased, non-alphanumerics -> hyphens."""
    if not text:
        return ""
    head = text.split(":", 1)[0] if ":" in text else text[:60]
    head = head.strip().lower()[:60]
    return re.sub(r"[^a-z0-9]+", "-", head).strip("-")


def _state(project: str, cur: str) -> int:
    """Gage state rank: 0=ACTIVE, 1=STANDING, 2=ARCHIVED."""
    p = project or ""
    if p == "":
        return 1          # STANDING: written with no active project
    if cur and p == cur:
        return 0          # ACTIVE: belongs to the current project
    return 2              # ARCHIVED: a finished or abandoned project


def _candidates(volume_mount: str) -> list:
    """All non-control memories, newest-FIRST BY UPDATE TIME, carrying project.

    Audit P1-F13, resolved 2026-08-06: this ordered by `id DESC`, i.e. INSERTION
    order, while `store()` on an existing key does `UPDATE ... WHERE key=?` and
    keeps the original row id. So a re-stored memory could never climb back into
    working memory (layer1 = top LAYER1_SIZE) however fresh its content was. That
    is why `last_thought` was inert after the FIRST sleep: written once, updated
    every sleep thereafter, sinking further behind each newly inserted memory.
    The bug was general -- every updated key sank, including current_focus and
    the plan keys -- and the docstring already claimed "newest-first", which
    ordering by id only delivers for rows that are never touched again.
    Tie-break on id keeps the order stable for equal timestamps.
    """
    with _db(volume_mount) as conn:
        rows = conn.execute(
            "SELECT id, key, value, tags, updated, project "
            "FROM memories ORDER BY updated DESC, id DESC"
        ).fetchall()
    return [
        {"id": r[0], "key": r[1], "value": r[2], "tags": r[3],
         "updated": r[4], "project": r[5]}
        for r in rows if r[1] not in CONTROL_KEYS
    ]


def _cur_slug(volume_mount: str) -> str:
    row = retrieve(volume_mount, "current-project")
    return _slug(row["value"]) if row else ""


def _ranked_rest(volume_mount: str) -> list:
    """Candidates beyond working memory, ordered by (gage state, recency)."""
    rest = _candidates(volume_mount)[LAYER1_SIZE:]
    cur = _cur_slug(volume_mount)
    rest.sort(key=lambda m: (_state(m["project"], cur), -m["id"]))
    return rest


def stamp_project(volume_mount: str, project_text: str,
                  since_ts: float, exclude=None) -> int:
    """Stamp project=slug(project_text) on every memory updated at/after
    since_ts, except excluded keys. Sets `project` ONLY (never `updated`), so a
    stamped-but-untouched row will not re-qualify on a later cycle."""
    slug = _slug(project_text)
    if not slug:
        return 0
    exclude = exclude or set()
    with _db(volume_mount) as conn:
        rows = conn.execute(
            "SELECT id, key FROM memories WHERE updated >= ?", (since_ts,)
        ).fetchall()
        ids = [rid for (rid, k) in rows if k not in exclude]
        if not ids:
            return 0
        qmarks = ",".join("?" for _ in ids)
        conn.execute(
            f"UPDATE memories SET project=? WHERE id IN ({qmarks})",
            [slug, *ids]
        )
    return len(ids)


def layer1(volume_mount: str) -> list:
    """Working memory: the 5 most recent non-control memories, full content."""
    return _candidates(volume_mount)[:LAYER1_SIZE]


def layer2_headlines(volume_mount: str) -> list:
    """Intermediate: next entries by (gage state, recency) — one-line headlines."""
    intermediate = _ranked_rest(volume_mount)[:LAYER2_MAX - LAYER1_SIZE]
    return [
        {"key": m["key"], "headline": m["value"][:120].replace("\n", " ")}
        for m in intermediate
    ]


def layer3_themes(volume_mount: str) -> list:
    """Archive: remaining entries by (gage state, recency) — keys only."""
    return [m["key"] for m in _ranked_rest(volume_mount)[LAYER2_MAX - LAYER1_SIZE:]]


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
