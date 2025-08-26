# pipeline.py
import sqlite3
import json
from datetime import datetime
from utils import process_one_url, get_api_keys_from_db

APP_DB = "db.sqlite3"


def process_all_pending():
    """Xử lý các link pending không có schedule_time (xử lý ngay theo batch)."""
    conn = sqlite3.connect(APP_DB)
    c = conn.cursor()
    c.execute("SELECT id, url FROM links WHERE status='pending' AND (schedule_time IS NULL OR schedule_time='')")
    rows = c.fetchall()
    keys = get_api_keys_from_db()
    for link_id, url in rows:
        try:
            result = process_one_url(url, keys)
            c.execute("UPDATE links SET status='done', result=? WHERE id=?", (json.dumps(result, ensure_ascii=False), link_id))
        except Exception as e:
            c.execute("UPDATE links SET status='error', result=? WHERE id=?", (str(e), link_id))
    conn.commit()
    conn.close()


def process_scheduled():
    """Xử lý các link có schedule_time khi tới thời điểm."""
    conn = sqlite3.connect(APP_DB)
    c = conn.cursor()
    c.execute("SELECT id, url, schedule_time FROM links WHERE status='pending' AND schedule_time IS NOT NULL AND schedule_time != ''")
    rows = c.fetchall()
    keys = get_api_keys_from_db()
    now = datetime.now()
    for link_id, url, schedule_time in rows:
        try:
            sched = None
            try:
                # form input is like "YYYY-MM-DDTHH:MM" from datetime-local; convert to iso format
                # If stored already as ISO, datetime.fromisoformat works.
                sched = datetime.fromisoformat(schedule_time)
            except Exception:
                # ignore parse errors
                continue
            if sched <= now:
                try:
                    result = process_one_url(url, keys)
                    c.execute("UPDATE links SET status='done', result=? WHERE id=?", (json.dumps(result, ensure_ascii=False), link_id))
                except Exception as e:
                    c.execute("UPDATE links SET status='error', result=? WHERE id=?", (str(e), link_id))
        except Exception:
            continue
    conn.commit()
    conn.close()


def process_one_url_from_db(url):
    """Helper: process one url reading API keys from DB and return result."""
    keys = get_api_keys_from_db()
    return process_one_url(url, keys)


if __name__ == "__main__":
    # for debugging
    process_all_pending()
    process_scheduled()
