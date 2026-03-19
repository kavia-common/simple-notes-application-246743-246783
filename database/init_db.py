#!/usr/bin/env python3
"""Initialize SQLite database for the Notes app (database container).

This script is the canonical initializer for the database container. It:
- Creates the SQLite DB file if missing
- Enables foreign keys
- Creates the Notes schema: notes, tags, note_tags
- Creates indexes optimized for list/search and tag filtering
- Writes/updates db_connection.txt and db_visualizer/sqlite.env for convenience

Run from the database container directory:
  python3 init_db.py
"""

from __future__ import annotations

import os
import sqlite3

DB_NAME = "myapp.db"


def _connect(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with safe defaults."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Enforce FK constraints in SQLite.
    conn.execute("PRAGMA foreign_keys = ON")
    # Improve concurrent read/write behavior (safe default for local dev).
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create the Notes schema and indexes (idempotent)."""
    cur = conn.cursor()

    # Notes table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            is_favorite INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    # Tags table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(name COLLATE NOCASE)
        )
        """
    )

    # Join table: many-to-many notes <-> tags
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
        """
    )

    # Indexes
    # Faster sorting/filtering for lists.
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notes_updated_at
        ON notes(updated_at DESC)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notes_created_at
        ON notes(created_at DESC)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notes_is_favorite
        ON notes(is_favorite, updated_at DESC)
        """
    )
    # Tag lookup and join performance.
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tags_name
        ON tags(name COLLATE NOCASE)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id
        ON note_tags(tag_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_note_tags_note_id
        ON note_tags(note_id)
        """
    )

    conn.commit()


def _write_connection_files(db_path_abs: str) -> None:
    """Write helper files used by this repository's database container tooling."""
    # Save connection information to a file
    current_dir = os.getcwd()
    connection_string = f"sqlite:///{db_path_abs}"

    with open("db_connection.txt", "w", encoding="utf-8") as f:
        f.write("# SQLite connection methods:\n")
        f.write(f"# Python: sqlite3.connect('{DB_NAME}')\n")
        f.write(f"# Connection string: {connection_string}\n")
        f.write(f"# File path: {db_path_abs}\n")

    # Create environment variables file for Node.js viewer
    os.makedirs("db_visualizer", exist_ok=True)
    with open("db_visualizer/sqlite.env", "w", encoding="utf-8") as f:
        f.write(f'export SQLITE_DB="{db_path_abs}"\n')


def main() -> None:
    """Initialize database schema."""
    print("Starting SQLite Notes DB setup...")

    db_exists = os.path.exists(DB_NAME)
    if db_exists:
        print(f"SQLite database already exists at {DB_NAME} (will ensure schema is present)")
    else:
        print("Creating new SQLite database...")

    db_path_abs = os.path.abspath(DB_NAME)

    conn = _connect(DB_NAME)
    try:
        _create_schema(conn)
    finally:
        conn.close()

    _write_connection_files(db_path_abs)

    print("\nSQLite Notes DB setup complete!")
    print(f"Database: {DB_NAME}")
    print(f"Location: {db_path_abs}")
    print("\nCreated/verified tables: notes, tags, note_tags")
    print("Helper files updated: db_connection.txt, db_visualizer/sqlite.env")
    print("\nScript completed successfully.")


if __name__ == "__main__":
    main()
