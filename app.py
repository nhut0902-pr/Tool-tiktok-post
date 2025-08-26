# app.py
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import pipeline  # pipeline.process_all_pending, pipeline.process_scheduled

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "db.sqlite3")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev_secret_key")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # links: url entries
    c.execute('''
        CREATE TABLE IF NOT EXISTS links(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            status TEXT DEFAULT "pending",
            result TEXT,
            schedule_time TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # apikeys: single row id=1
    c.execute('''
        CREATE TABLE IF NOT EXISTS apikeys(
            id INTEGER PRIMARY KEY,
            hf_token TEXT,
            unsplash_key TEXT,
            fb_page_id TEXT,
            fb_page_token TEXT
        )
    ''')
    # ensure one row
    c.execute("SELECT COUNT(*) FROM apikeys")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO apikeys(id,hf_token,unsplash_key,fb_page_id,fb_page_token) VALUES(1,'','','','')")
    conn.commit()
    conn.close()


init_db()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        schedule_time = request.form.get("schedule_time") or None  # iso string or None
        if not url:
            flash("Vui lòng nhập URL TikTok.", "warning")
            return redirect(url_for("index"))
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO links (url, schedule_time) VALUES (?, ?)", (url, schedule_time))
        conn.commit()
        conn.close()
        flash("Đã lưu link. Nó sẽ được xử lý khi tới giờ hoặc khi bạn bấm xử lý.", "success")
        return redirect(url_for("index"))

    # show recent links and basic info
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, url, status, result, schedule_time, created_at FROM links ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return render_template("index.html", links=rows)


@app.route("/history")
def history():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, url, status, result, schedule_time, created_at FROM links ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return render_template("history.html", links=rows)


@app.route("/apikeys", methods=["GET", "POST"])
def apikeys():
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == "POST":
        hf_token = request.form.get("hf_token", "").strip()
        unsplash_key = request.form.get("unsplash_key", "").strip()
        fb_page_id = request.form.get("fb_page_id", "").strip()
        fb_page_token = request.form.get("fb_page_token", "").strip()
        c.execute("""
            UPDATE apikeys
            SET hf_token=?, unsplash_key=?, fb_page_id=?, fb_page_token=?
            WHERE id=1
        """, (hf_token, unsplash_key, fb_page_id, fb_page_token))
        conn.commit()
        flash("Đã lưu API keys.", "success")
        conn.close()
        return redirect(url_for("apikeys"))
    c.execute("SELECT hf_token, unsplash_key, fb_page_id, fb_page_token FROM apikeys WHERE id=1")
    keys = c.fetchone()
    conn.close()
    return render_template("apikeys.html", keys=keys)


@app.route("/process/<int:link_id>", methods=["GET"])
def process_link(link_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT url FROM links WHERE id=?", (link_id,))
    row = c.fetchone()
    if not row:
        flash("Không tìm thấy link.", "danger")
        conn.close()
        return redirect(url_for("history"))
    url = row["url"]
    # Call pipeline to process single url
    try:
        res = pipeline.process_one_url_from_db(url)  # pipeline exposes helper that reads keys from DB
        c.execute("UPDATE links SET status='done', result=? WHERE id=?", (str(res), link_id))
        conn.commit()
        flash("Đã xử lý link thành công.", "success")
    except Exception as e:
        c.execute("UPDATE links SET status='error', result=? WHERE id=?", (str(e), link_id))
        conn.commit()
        flash(f"Lỗi khi xử lý: {e}", "danger")
    finally:
        conn.close()
    return redirect(url_for("history"))


@app.route("/run_pending", methods=["GET"])
def run_pending():
    """Manual trigger for batch (for debugging)."""
    try:
        pipeline.process_all_pending()
        pipeline.process_scheduled()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Scheduler background jobs
scheduler = BackgroundScheduler()
# check scheduled links each minute
scheduler.add_job(func=pipeline.process_scheduled, trigger="interval", seconds=60, id="scheduled_job")
# process unscheduled pending every 5 minutes
scheduler.add_job(func=pipeline.process_all_pending, trigger="interval", minutes=5, id="batch_job")
scheduler.start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
