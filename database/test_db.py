#!/usr/bin/env python3
"""Test SQLite database connection and Notes schema presence."""

import os
import sqlite3
import sys

DB_NAME = "myapp.db"
REQUIRED_TABLES = {"notes", "tags", "note_tags"}


def main() -> int:
    """Connect to the DB, print SQLite version, and verify required tables exist."""
    try:
        if not os.path.exists(DB_NAME):
            print(f"Database file '{DB_NAME}' not found")
            return 1

        conn = sqlite3.connect(DB_NAME)
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")

            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            print(f"SQLite version: {version}")

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            missing = REQUIRED_TABLES - tables
            if missing:
                print(f"Missing required tables: {sorted(missing)}")
                print("Run: python3 init_db.py")
                return 1

            print("Notes schema present.")
            return 0
        finally:
            conn.close()

    except sqlite3.Error as e:
        print(f"Connection failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
