import sqlite3
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

DB_NAME = "jobs.db"

def get_db():
    db_path = Path(DB_NAME)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            snippet TEXT,
            url TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return conn

def main():
    if len(sys.argv) < 2:
        print("usage: python scrapper.py <command>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        get_db()
        print("db ready")
    else:
        print(f"unknown command {cmd}")

if __name__ == "__main__":
    main()
