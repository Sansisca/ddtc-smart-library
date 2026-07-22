# -*- coding: utf-8 -*-
"""
db/database.py
Koneksi SQLite + inisialisasi skema untuk SIPAKAR AHP DDTC Library.
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "db_ahp_ddtc.sqlite3"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Buat koneksi baru ke database SQLite dengan row_factory dict-like."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection = None) -> None:
    """Jalankan schema.sql untuk membuat seluruh tabel jika belum ada."""
    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    if own_conn:
        conn.close()


def db_exists() -> bool:
    return DB_PATH.exists() and DB_PATH.stat().st_size > 0


def reset_database() -> None:
    """Hapus file database (dipakai untuk reset total saat pengembangan)."""
    if DB_PATH.exists():
        DB_PATH.unlink()
