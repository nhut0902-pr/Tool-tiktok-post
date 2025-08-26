from flask import Flask, request, render_template, redirect
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
from pipeline import process_all_pending, process_scheduled

app = Flask(__name__)
DB_PATH = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        status TEXT,
        result TEXT,
        schedule_time TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS apikeys (
        id INTEGER PRIMARY KEY,
        hf_token TEXT,
        unsplash_key TEXT,
        fb_page_id TEXT,
        fb_page_token TEXT
    )""")
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        schedule_time = request.form.get("schedule_time")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO links (url, status, schedule_time) VALUES (?, 'pending', ?)", (url, schedule_time))
        conn.commit()
        conn.close()
        return redirect("/")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM links ORDER BY id DESC")
    links = c.fetchall()
    conn.close()
    return render_template("index.html", links=links)

@app.route("/save_keys", methods=["POST"])
def save_keys():
    hf_token = request.form.get("hf_token")
    unsplash_key = request.form.get("unsplash_key")
    fb_page_id = request.form.get("fb_page_id")
    fb_page_token = request.form.get("fb_page_token")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM apikeys")
    c.execute("INSERT INTO apikeys (id, hf_token, unsplash_key, fb_page_id, fb_page_token) VALUES (1, ?, ?, ?, ?)",
              (hf_token, unsplash_key, fb_page_id, fb_page_token))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=process_all_pending, trigger="interval", minutes=5)
    scheduler.add_job(func=process_scheduled, trigger="interval", minutes=1)
    scheduler.start()
    app.run(host="0.0.0.0", port=5000)
