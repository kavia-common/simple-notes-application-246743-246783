#!/usr/bin/env python3
"""Seed the SQLite Notes database with sample data.

This script assumes the schema exists (run init_db.py first).
It is designed to be safe to run multiple times:
- Tags are inserted via INSERT OR IGNORE (case-insensitive uniqueness)
- Notes are inserted fresh only if the notes table is empty
- note_tags are inserted via INSERT OR IGNORE (PK prevents duplicates)

Run from the database container directory:
  python3 seed_db.py
"""

from __future__ import annotations

import os
import sqlite3
from typing import Dict, List, Tuple

DB_NAME = "myapp.db"


def _connect(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with safe defaults."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_existing_note_count(conn: sqlite3.Connection) -> int:
    """Return number of existing notes."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM notes")
    return int(cur.fetchone()["c"])


def _ensure_tags(conn: sqlite3.Connection, tag_names: List[str]) -> Dict[str, int]:
    """Ensure tags exist; return mapping {normalized_name -> tag_id}."""
    cur = conn.cursor()
    for name in tag_names:
        cur.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (name,))
    conn.commit()

    # Fetch ids back (case-insensitive unique means we can select by name with NOCASE)
    mapping: Dict[str, int] = {}
    for name in tag_names:
        cur.execute("SELECT id, name FROM tags WHERE name = ? COLLATE NOCASE", (name,))
        row = cur.fetchone()
        if row:
            mapping[row["name"].lower()] = int(row["id"])
    return mapping


def _insert_notes(conn: sqlite3.Connection) -> List[int]:
    """Insert sample notes and return their IDs."""
    cur = conn.cursor()

    sample_notes: List[Tuple[str, str, int]] = [
        (
            "Welcome to Simple Notes",
            "This is your first note. Edit me, tag me, or delete me.",
            1,
        ),
        (
            "Shopping list",
            "- Coffee\n- Bread\n- Eggs\n- Fruit",
            0,
        ),
        (
            "Project ideas",
            "1) Notes app enhancements\n2) Habit tracker\n3) Minimal portfolio",
            0,
        ),
        (
            "Meeting notes",
            "Agenda:\n- Status updates\n- Risks\n- Next steps",
            0,
        ),
    ]

    note_ids: List[int] = []
    for title, content, is_favorite in sample_notes:
        cur.execute(
            """
            INSERT INTO notes(title, content, is_favorite, created_at, updated_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
            """,
            (title, content, is_favorite),
        )
        note_ids.append(int(cur.lastrowid))

    conn.commit()
    return note_ids


def _link_tags(conn: sqlite3.Connection, note_ids: List[int], tag_ids: Dict[str, int]) -> None:
    """Create sample note/tag relationships."""
    cur = conn.cursor()

    # note_ids correspond to inserted sample notes order in _insert_notes
    relationships = [
        (note_ids[0], tag_ids["getting started"]),
        (note_ids[0], tag_ids["favorites"]),
        (note_ids[1], tag_ids["personal"]),
        (note_ids[1], tag_ids["errands"]),
        (note_ids[2], tag_ids["work"]),
        (note_ids[2], tag_ids["ideas"]),
        (note_ids[3], tag_ids["work"]),
    ]

    for note_id, tag_id in relationships:
        cur.execute(
            """
            INSERT OR IGNORE INTO note_tags(note_id, tag_id)
            VALUES (?, ?)
            """,
            (note_id, tag_id),
        )

    conn.commit()


def main() -> None:
    """Seed the database."""
    if not os.path.exists(DB_NAME):
        raise SystemExit(f"Database file '{DB_NAME}' not found. Run init_db.py first.")

    conn = _connect(DB_NAME)
    try:
        existing = _get_existing_note_count(conn)
        if existing > 0:
            print(f"Notes already present ({existing}). Skipping note insertion.")
            print("Tags will still be ensured (INSERT OR IGNORE).")
        else:
            print("No notes found. Inserting sample notes...")

        tags = [
            "Getting Started",
            "Favorites",
            "Personal",
            "Errands",
            "Work",
            "Ideas",
        ]
        tag_ids = _ensure_tags(conn, tags)

        if existing == 0:
            note_ids = _insert_notes(conn)
            _link_tags(conn, note_ids, tag_ids)

        # Basic summary
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM tags")
        tags_count = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM notes")
        notes_count = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM note_tags")
        links_count = int(cur.fetchone()["c"])

        print("\nSeed complete:")
        print(f"  notes: {notes_count}")
        print(f"  tags: {tags_count}")
        print(f"  note_tags: {links_count}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
