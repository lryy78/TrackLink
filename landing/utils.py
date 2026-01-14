# landing/utils.py
import sqlite3
from datetime import datetime, timedelta
from flask import request
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "..", "activity.db")  # DB one level up

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            page TEXT,
            visit_time TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_visit(page="unknown"):
    """Log a visit with page name; defaults to 'unknown'."""
    try:
        malaysia_time = datetime.utcnow() + timedelta(hours=8)
        malaysia_time_str = malaysia_time.strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO visits (ip, user_agent, page, visit_time)
            VALUES (?, ?, ?, ?)
        """, (request.remote_addr, request.headers.get("User-Agent"), page, malaysia_time_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log visit: {e}")  # log to console if fails

# Initialize DB
init_db()
