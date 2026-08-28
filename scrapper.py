import sqlite3
import sys
import time
import random
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

DB_NAME = "jobs.db"
console = Console()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0"
]

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
    """
    )
    return conn

def fetch_jobs(query):
    """Pulls public job listings from linkedin search pages with simple rate limit handling."""
    conn = get_db()
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    search_url = f"[https://www.linkedin.com/jobs/search](https://www.linkedin.com/jobs/search)?bs/search?keywords=){query}&location=United%20States"
    
    retries = 3
    resp = None
    for i in range(retries):
        try:
            resp = requests.get(search_url, headers=headers, timeout=15)
            if resp.status_code == 429:
                sleep_time = (i + 1) * 5
                # TODO: add exponential backoff if linkedin keeps blocking
                time.sleep(sleep_time)
                continue
            break
        except Exception as e:
            console.print(f"[red]request failed: {e}[/red]")
            return

    if not resp or resp.status_code != 200:
        status = resp.status_code if resp else "none"
        console.print(f"[yellow]failed to fetch jobs, status: {status}[/yellow]")
        conn.close()
        return

    soup = BeautifulSoup(resp.text, 'html.parser')
    cards = soup.find_all('div', class_='base-card')
    
    saved = 0
    for card in cards:
        title_el = card.find('h3', class_='base-search-card__title')
        comp_el = card.find('h4', class_='base-search-card__subtitle')
        link_el = card.find('a', class_='base-card__full-link')
        
        if not title_el or not link_el:
            continue
            
        title = title_el.text.strip()
        company = comp_el.text.strip() if comp_el else "unknown"
        url = link_el['href'].split('?')[0]
        
        try:
            conn.execute(
                "INSERT OR IGNORE INTO posts (title, company, snippet, url) VALUES (?, ?, ?, ?)",
                (title, company, "", url)
            )
            saved += 1
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()
    console.print(f"saved {saved} new posts for query: {query}")

def search_db(keyword):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT title, company, url FROM posts WHERE title LIKE ? OR snippet LIKE ? ORDER BY id DESC", (f"%{keyword}%", f"%{keyword}%"))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]no matches found in local db[/yellow]")
        return

    table = Table(title=f"results for '{keyword}'")
    table.add_column("Title", style="cyan")
    table.add_column("Company", style="green")
    table.add_column("URL", style="dim")

    for r in rows:
        table.add_row(r[0], r[1], r[2])

    console.print(table)

def main():
    if len(sys.argv) < 2:
        print("usage: python scrapper.py <pull|search> <query>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "pull":
        query = sys.argv[2] if len(sys.argv) > 2 else "python"
        fetch_jobs(query)
    elif cmd == "search":
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        search_db(keyword)
    else:
        print(f"unknown command {cmd}")

if __name__ == "__main__":
    # print(sys.argv)
    main()
