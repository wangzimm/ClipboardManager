import os
import sqlite3
import hashlib
from datetime import datetime, timedelta


def _db_dir():
    path = os.path.join(os.environ["APPDATA"], "ClipboardManager")
    os.makedirs(path, exist_ok=True)
    return path


def _db_path():
    return os.path.join(_db_dir(), "clipboard.db")


def _connect():
    conn = sqlite3.connect(_db_path())
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _connect()
    # Create tables (with favorite column for fresh installs)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS clipboard_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            content TEXT,
            image_data BLOB,
            content_hash TEXT,
            pinned INTEGER DEFAULT 0,
            favorite INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_type ON clipboard_items(type);
        CREATE INDEX IF NOT EXISTS idx_created ON clipboard_items(created_at);
        CREATE INDEX IF NOT EXISTS idx_pinned ON clipboard_items(pinned);
        CREATE INDEX IF NOT EXISTS idx_content_hash ON clipboard_items(content_hash);

        CREATE TABLE IF NOT EXISTS recycle_bin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            content TEXT,
            image_data BLOB,
            content_hash TEXT,
            pinned INTEGER DEFAULT 0,
            favorite INTEGER DEFAULT 0,
            original_created_at TEXT,
            deleted_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_recycle_deleted ON recycle_bin(deleted_at);

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # Migrate existing tables: add favorite column if missing
    try:
        conn.execute("ALTER TABLE clipboard_items ADD COLUMN favorite INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE recycle_bin ADD COLUMN favorite INTEGER DEFAULT 0")
    except Exception:
        pass
    # Now safe to create the favorite index (column exists whether fresh or upgraded)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_favorite ON clipboard_items(favorite)")
    conn.commit()

    defaults = {"retention_hours": "72", "auto_start": "true"}
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
        )
    conn.commit()
    conn.close()


def add_text_item(text):
    if not text or not text.strip():
        return None
    content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    conn = _connect()
    row = conn.execute(
        "SELECT id FROM clipboard_items WHERE content_hash = ? ORDER BY id DESC LIMIT 1",
        (content_hash,),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE clipboard_items SET created_at = datetime('now','localtime') WHERE id = ?",
            (row[0],),
        )
        conn.commit()
        conn.close()
        return row[0]

    conn.execute(
        "INSERT INTO clipboard_items (type, content, content_hash) VALUES ('text', ?, ?)",
        (text, content_hash),
    )
    conn.commit()
    item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return item_id


def add_image_item(image_bytes):
    if not image_bytes:
        return None
    content_hash = hashlib.md5(image_bytes).hexdigest()
    conn = _connect()
    row = conn.execute(
        "SELECT id FROM clipboard_items WHERE content_hash = ? ORDER BY id DESC LIMIT 1",
        (content_hash,),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE clipboard_items SET created_at = datetime('now','localtime') WHERE id = ?",
            (row[0],),
        )
        conn.commit()
        conn.close()
        return row[0]

    conn.execute(
        "INSERT INTO clipboard_items (type, image_data, content_hash) VALUES ('image', ?, ?)",
        (image_bytes, content_hash),
    )
    conn.commit()
    item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return item_id


def get_items(item_type=None, search=None, limit=100, offset=0, include_image_data=True):
    conn = _connect()
    conditions = []
    params = []

    if item_type:
        conditions.append("type = ?")
        params.append(item_type)
    if search:
        conditions.append("content LIKE ?")
        params.append(f"%{search}%")

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    image_col = "image_data" if include_image_data else "NULL as image_data"
    query = f"""
        SELECT id, type, content, {image_col}, pinned, created_at, favorite
        FROM clipboard_items
        {where}
        ORDER BY pinned DESC, favorite DESC, created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_image_data(item_id):
    """Fetch raw image bytes for a single item — used when copying to clipboard."""
    conn = _connect()
    row = conn.execute(
        "SELECT image_data FROM clipboard_items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def delete_item(item_id):
    """Move item to recycle bin instead of deleting permanently."""
    conn = _connect()
    row = conn.execute(
        "SELECT type, content, image_data, content_hash, pinned, favorite, created_at FROM clipboard_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if not row:
        conn.close()
        return
    conn.execute("BEGIN")
    conn.execute(
        "INSERT INTO recycle_bin (type, content, image_data, content_hash, pinned, favorite, original_created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (row[0], row[1], row[2], row[3], row[4], row[5], row[6]),
    )
    conn.execute("DELETE FROM clipboard_items WHERE id = ?", (item_id,))
    conn.execute("COMMIT")
    conn.close()


def get_recycle_items(limit=100):
    conn = _connect()
    rows = conn.execute(
        "SELECT id, type, content, pinned, original_created_at, deleted_at "
        "FROM recycle_bin ORDER BY deleted_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def restore_from_recycle(item_id):
    """Move item back from recycle bin to clipboard_items."""
    conn = _connect()
    row = conn.execute(
        "SELECT type, content, image_data, content_hash, pinned, favorite, original_created_at FROM recycle_bin WHERE id = ?",
        (item_id,),
    ).fetchone()
    if not row:
        conn.close()
        return

    existing = conn.execute(
        "SELECT id FROM clipboard_items WHERE content_hash = ? ORDER BY id DESC LIMIT 1",
        (row[3],),
    ).fetchone()

    conn.execute("BEGIN")
    if existing:
        conn.execute(
            "UPDATE clipboard_items SET created_at = datetime('now','localtime') WHERE id = ?",
            (existing[0],),
        )
    else:
        conn.execute(
            "INSERT INTO clipboard_items (type, content, image_data, content_hash, pinned, favorite, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row[0], row[1], row[2], row[3], row[4], row[5], row[6]),
        )
    conn.execute("DELETE FROM recycle_bin WHERE id = ?", (item_id,))
    conn.execute("COMMIT")
    conn.close()


def restore_all_recycle():
    """Restore ALL items from recycle bin back to clipboard_items."""
    conn = _connect()
    rows = conn.execute(
        "SELECT type, content, image_data, content_hash, pinned, favorite, original_created_at "
        "FROM recycle_bin LIMIT 2000"
    ).fetchall()
    conn.execute("BEGIN")
    for row in rows:
        existing = conn.execute(
            "SELECT id FROM clipboard_items WHERE content_hash = ? ORDER BY id DESC LIMIT 1",
            (row[3],),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE clipboard_items SET created_at = datetime('now','localtime') WHERE id = ?",
                (existing[0],),
            )
        else:
            conn.execute(
                "INSERT INTO clipboard_items (type, content, image_data, content_hash, pinned, favorite, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row[0], row[1], row[2], row[3], row[4], row[5], row[6]),
            )
    conn.execute("DELETE FROM recycle_bin")
    conn.execute("COMMIT")
    count = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()
    return count


def permanent_delete(item_id):
    """Permanently delete an item from the recycle bin."""
    conn = _connect()
    conn.execute("DELETE FROM recycle_bin WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def cleanup_recycle():
    """Delete items in recycle bin older than 7 days."""
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    conn = _connect()
    conn.execute("DELETE FROM recycle_bin WHERE deleted_at < ?", (cutoff,))
    deleted = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    conn.close()
    return deleted


def empty_recycle():
    """Delete ALL items from recycle bin immediately."""
    conn = _connect()
    conn.execute("DELETE FROM recycle_bin")
    deleted = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    conn.close()
    return deleted


def delete_items_older_than(hours, item_type=None):
    """Move items older than N hours to recycle bin. Pinned or favorited items are skipped.

    If item_type is given (e.g. 'text' or 'image'), only that type is affected.
    """
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = _connect()

    type_clause = ""
    params = [cutoff]
    if item_type:
        type_clause = "AND type = ?"
        params.insert(1, item_type)

    conn.execute("BEGIN")
    conn.execute(
        f"INSERT INTO recycle_bin (type, content, image_data, content_hash, pinned, favorite, original_created_at) "
        f"SELECT type, content, image_data, content_hash, pinned, favorite, created_at "
        f"FROM clipboard_items WHERE pinned = 0 AND favorite = 0 AND created_at < ? {type_clause}",
        params,
    )
    conn.execute(
        f"DELETE FROM clipboard_items WHERE pinned = 0 AND favorite = 0 AND created_at < ? {type_clause}",
        params,
    )
    deleted = conn.execute("SELECT changes()").fetchone()[0]
    conn.execute("COMMIT")
    conn.close()
    return deleted


def toggle_pin(item_id):
    conn = _connect()
    conn.execute(
        "UPDATE clipboard_items SET pinned = 1 - pinned WHERE id = ?", (item_id,)
    )
    conn.commit()
    conn.close()


def is_pinned(item_id):
    conn = _connect()
    row = conn.execute(
        "SELECT pinned FROM clipboard_items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return bool(row[0]) if row else False


def toggle_favorite(item_id):
    conn = _connect()
    conn.execute(
        "UPDATE clipboard_items SET favorite = 1 - favorite WHERE id = ?", (item_id,)
    )
    conn.commit()
    conn.close()


def is_favorite(item_id):
    conn = _connect()
    row = conn.execute(
        "SELECT favorite FROM clipboard_items WHERE id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return bool(row[0]) if row else False


def get_favorites(limit=100, offset=0):
    conn = _connect()
    rows = conn.execute(
        "SELECT id, type, content, image_data, pinned, created_at, favorite "
        "FROM clipboard_items WHERE favorite = 1 "
        "ORDER BY pinned DESC, created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    conn.close()
    return rows


def cleanup_expired(retention_hours, direction="older", item_type=None):
    """Expire items to recycle bin. Pinned items are skipped.

    direction: 'older' = items older than cutoff; 'newer' = items newer than cutoff.
    item_type: 'text', 'image', or None (all types).
    """
    cutoff = (datetime.now() - timedelta(hours=retention_hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    op = ">" if direction == "newer" else "<"

    type_clause = ""
    params = [cutoff]
    if item_type:
        type_clause = "AND type = ?"
        params.append(item_type)

    conn = _connect()
    conn.execute("BEGIN")
    conn.execute(
        f"INSERT INTO recycle_bin (type, content, image_data, content_hash, pinned, favorite, original_created_at) "
        f"SELECT type, content, image_data, content_hash, pinned, favorite, created_at "
        f"FROM clipboard_items WHERE pinned = 0 AND favorite = 0 AND created_at {op} ? {type_clause}",
        params,
    )
    conn.execute(
        f"DELETE FROM clipboard_items WHERE pinned = 0 AND favorite = 0 AND created_at {op} ? {type_clause}", params,
    )
    deleted = conn.execute("SELECT changes()").fetchone()[0]
    conn.execute("COMMIT")
    conn.close()
    return deleted


def get_setting(key, default=None):
    conn = _connect()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = _connect()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
    conn.close()
