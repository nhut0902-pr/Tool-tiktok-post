from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pipeline import process_tiktok_url
import os
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev_secret_key"
DB_PATH = "db.sqlite3"

# --- Khởi tạo DB ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS links(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            status TEXT DEFAULT "pending",
            result TEXT,
            schedule_time TEXT DEFAULT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS apikeys(
            id INTEGER PRIMARY KEY,
            hf_token TEXT,
            unsplash_key TEXT,
            fb_page_id TEXT,
            fb_page_token TEXT
        )
    ''')
    c.execute("SELECT COUNT(*) FROM apikeys")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO apikeys(id,hf_token,unsplash_key,fb_page_id,fb_page_token) VALUES(1,'','','','')")
    conn.commit()
    conn.close()
init_db()

# --- Trang chính ---
@app.route("/", methods=["GET","POST"])
def index():
    if request.method=="POST":
        url = request.form.get("url")
        schedule_time = request.form.get("schedule_time")  # string "YYYY-MM-DDTHH:MM"
        if url:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO links(url, schedule_time) VALUES(?,?)", (url, schedule_time))
            conn.commit()
            conn.close()
            flash("Đã lưu link, chờ xử lý.")
        return redirect(url_for("index"))
    return render_template("index.html")

# --- Lịch sử ---
@app.route("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id,url,status,result,schedule_time FROM links ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return render_template("history.html", links=rows)

# --- API Keys ---
@app.route("/apikeys", methods=["GET","POST"])
def apikeys():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method=="POST":
        hf_token = request.form.get("hf_token")
        unsplash_key = request.form.get("unsplash_key")
        fb_page_id = request.form.get("fb_page_id")
        fb_page_token = request.form.get("fb_page_token")
        c.execute("""
            UPDATE apikeys SET hf_token=?, unsplash_key=?, fb_page_id=?, fb_page_token=? WHERE id=1
        """, (hf_token, unsplash_key, fb_page_id, fb_page_token))
        conn.commit()
        flash("Đã lưu API keys!")
    c.execute("SELECT hf_token, unsplash_key, fb_page_id, fb_page_token FROM apikeys WHERE id=1")
    keys = c.fetchone()
    conn.close()
    return render_template("apikeys.html", keys=keys)

# --- Xử lý link thủ công ---
@app.route("/process/<int:link_id>")
def process_link(link_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT url FROM links WHERE id=?",(link_id,))
    row = c.fetchone()
    if not row:
        flash("Link không tồn tại!")
        return redirect(url_for("history"))
    url = row[0]

    c.execute("SELECT hf_token, unsplash_key, fb_page_id, fb_page_token FROM apikeys WHERE id=1")
    hf_token, unsplash_key, fb_page_id, fb_page_token = c.fetchone()

    try:
        result = process_tiktok_url(url, hf_token, unsplash_key, fb_page_id, fb_page_token)
        c.execute("UPDATE links SET status='done', result=? WHERE id=?", (result, link_id))
    except Exception as e:
        c.execute("UPDATE links SET status='error', result=? WHERE id=?", (str(e), link_id))
    conn.commit()
    conn.close()
    flash("Xử lý xong link!")
    return redirect(url_for("history"))

# --- Scheduler tự động ---
def process_pending_links():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id,url,schedule_time FROM links WHERE status='pending' AND schedule_time IS NOT NULL")
    rows = c.fetchall()
    for link_id, url, sched_time_str in rows:
        if not sched_time_str: 
            continue
        sched_time = datetime.fromisoformat(sched_time_str)
        if sched_time <= datetime.now():
            c.execute("SELECT hf_token, unsplash_key, fb_page_id, fb_page_token FROM apikeys WHERE id=1")
            hf_token, unsplash_key, fb_page_id, fb_page_token = c.fetchone()
            try:
                result = process_tiktok_url(url, hf_token, unsplash_key, fb_page_id, fb_page_token)
                c.execute("UPDATE links SET status='done', result=? WHERE id=?", (result, link_id))
            except Exception as e:
                c.execute("UPDATE links SET status='error', result=? WHERE id=?", (str(e), link_id))
    conn.commit()
    conn.close()

scheduler = BackgroundScheduler()
scheduler.add_job(func=process_pending_links, trigger="interval", seconds=60)
scheduler.start()

if __name__=="__main__":
    app.run(debug=True)
