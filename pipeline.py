# pipeline.py
import sqlite3
from datetime import datetime
from utils import process_one_url

DB_PATH = "db.sqlite3"

def process_all_pending():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, url FROM links WHERE status='pending' AND schedule_time IS NULL")
    rows = c.fetchall()

    c.execute("SELECT hf_token, unsplash_key, fb_page_id, fb_page_token FROM apikeys WHERE id=1")
    keys = c.fetchone()
    hf_token, unsplash_key, fb_page_id, fb_page_token = keys

    for link_id, url in rows:
        try:
            result = process_one_url(url, hf_token, unsplash_key, fb_page_id, fb_page_token)
            c.execute("UPDATE links SET status='done', result=? WHERE id=?", (str(result), link_id))
        except Exception as e:
            c.execute("UPDATE links SET status='error', result=? WHERE id=?", (str(e), link_id))
    conn.commit()
    conn.close()

def process_scheduled():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, url, schedule_time FROM links 
        WHERE status='pending' AND schedule_time IS NOT NULL
    """)
    rows = c.fetchall()

    c.execute("SELECT hf_token, unsplash_key, fb_page_id, fb_page_token FROM apikeys WHERE id=1")
    keys = c.fetchone()
    hf_token, unsplash_key, fb_page_id, fb_page_token = keys

    now = datetime.now()
    for link_id, url, schedule_time in rows:
        try:
            sched = datetime.fromisoformat(schedule_time)
            if sched <= now:
                result = process_one_url(url, hf_token, unsplash_key, fb_page_id, fb_page_token)
                c.execute("UPDATE links SET status='done', result=? WHERE id=?", (str(result), link_id))
        except Exception as e:
            c.execute("UPDATE links SET status='error', result=? WHERE id=?", (str(e), link_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    process_all_pending()
    process_scheduled()
