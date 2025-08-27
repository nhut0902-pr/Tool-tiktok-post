from flask import Flask, render_template, request, redirect, url_for
from helpers import summarize_video, generate_hashtags, get_tiktok_thumbnail, get_facebook_insights, get_total_posts
import sqlite3

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    video_url = request.form['video_url']
    summary = summarize_video(video_url)
    hashtags = generate_hashtags(summary)
    thumbnail = get_tiktok_thumbnail(video_url)

    # Lưu vào DB
    conn = sqlite3.connect('dp.sqlite')
    c = conn.cursor()
    c.execute("INSERT INTO posts (title, summary, message, image) VALUES (?, ?, ?, ?)",
              ("TikTok Video", summary, summary + " " + hashtags, thumbnail))
    conn.commit()
    conn.close()

    return redirect(url_for('history'))

@app.route('/history')
def history():
    conn = sqlite3.connect('dp.sqlite')
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()
    conn.close()
    return render_template('history.html', posts=posts)

@app.route('/dashboard')
def dashboard():
    total_posts = get_total_posts()
    insights_data = get_facebook_insights()
    return render_template('dashboard.html',
                           total_posts=total_posts,
                           insights_data=insights_data)

if __name__ == '__main__':
    app.run(debug=True)
