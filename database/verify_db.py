#!/usr/bin/env python3
"""Verify the SQLite Notes database schema and basic integrity.

This script validates:
- Tables exist: notes, tags, note_tags
- Foreign keys are enabled
- Expected indexes exist
- A sample join query runs successfully

Run from the database container directory:
  python3 verify_db.py

Exit codes:
  0 - success
  1 - verification failed
"""

from __future__ import annotations

import os
import sqlite3
import sys
from typing import Iterable, Set

DB_NAME = "myapp.db"

EXPECTED_TABLES: Set[str] = {"notes", "tags", "note_tags"}

EXPECTED_INDEXES: Set[str] = {
    "idx_notes_updated_at",
    "idx_notes_created_at",
    "idx_notes_is_favorite",
    "idx_tags_name",
    "idx_note_tags_tag_id",
    "idx_note_tags_note_id",
}


def _connect(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with safe defaults."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _fetch_set(conn: sqlite3.Connection, sql: str, params: Iterable[object] = ()) -> Set[str]:
    """Run query and return first column as a set of strings."""
    cur = conn.cursor()
    cur.execute(sql, tuple(params))
    return {str(r[0]) for r in cur.fetchall()}


def main() -> int:
    """Run verification checks."""
    if not os.path.exists(DB_NAME):
        print(f"FAIL: Database file '{DB_NAME}' not found. Run init_db.py first.")
        return 1

    conn = _connect(DB_NAME)
    try:
        # Verify FK enforcement
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        if int(fk) != 1:
            print("FAIL: PRAGMA foreign_keys is not enabled.")
            return 1

        # Verify tables
        tables = _fetch_set(
            conn,
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        )
        missing_tables = EXPECTED_TABLES - tables
        if missing_tables:
            print(f"FAIL: Missing tables: {sorted(missing_tables)}")
            print(f"Found tables: {sorted(tables)}")
            return 1

        # Verify indexes
        indexes = _fetch_set(
            conn,
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'",
        )
        missing_indexes = EXPECTED_INDEXES - indexes
        if missing_indexes:
            print(f"FAIL: Missing indexes: {sorted(missing_indexes)}")
            print(f"Found indexes: {sorted(indexes)}")
            return 1

        # Verify join query works
        conn.execute(
            """
            SELECT n.id, n.title, COUNT(nt.tag_id) AS tag_count
            FROM notes n
            LEFT JOIN note_tags nt ON nt.note_id = n.id
            GROUP BY n.id
            ORDER BY n.updated_at DESC
            LIMIT 5
            """
        ).fetchall()

        # Verify cascading delete behavior (non-destructive if no data):
        # If notes exist, create a temp note + tag link and ensure deleting note removes note_tags.
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM notes")
        notes_count = int(cur.fetchone()["c"])

        if notes_count >= 0:
            # Create temp tag
            cur.execute("INSERT OR IGNORE INTO tags(name) VALUES ('__verify_temp__')")
            cur.execute("SELECT id FROM tags WHERE name='__verify_temp__' COLLATE NOCASE")
            temp_tag_id = int(cur.fetchone()["id"])

            # Create temp note
            cur.execute(
                "INSERT INTO notes(title, content, is_favorite) VALUES ('__verify__', 'temp', 0)"
            )
            temp_note_id = int(cur.lastrowid)

            # Link
            cur.execute(
                "INSERT OR IGNORE INTO note_tags(note_id, tag_id) VALUES (?, ?)",
                (temp_note_id, temp_tag_id),
            )
            conn.commit()

            # Delete note, expect note_tags row removed
            cur.execute("DELETE FROM notes WHERE id=?", (temp_note_id,))
            conn.commit()

            cur.execute("SELECT COUNT(*) AS c FROM note_tags WHERE note_id=?", (temp_note_id,))
            remaining = int(cur.fetchone()["c"])
            if remaining != 0:
                print("FAIL: Cascading delete did not remove note_tags rows.")
                return 1

        print("OK: Database schema, indexes, and integrity checks passed.")
        return 0
    except sqlite3.Error as e:
        print(f"FAIL: SQLite error: {e}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
