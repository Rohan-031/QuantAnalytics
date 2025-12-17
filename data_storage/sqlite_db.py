# data_storage/sqlite_db.py

import sqlite3
from config.settings import DB_PATH

import os

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def create_ticks_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            symbol TEXT,
            price REAL,
            size REAL,
            side TEXT
        )
    """)

    conn.commit()
    conn.close()

def insert_tick(ts, symbol, price, size, side):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ticks (ts, symbol, price, size, side)
        VALUES (?, ?, ?, ?, ?)
    """, (ts, symbol, price, size, side))

    conn.commit()
    conn.close()
