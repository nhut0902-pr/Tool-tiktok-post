from flask import Flask, render_template, request, send_file, redirect
from helpers import get_tiktok_video_data, summarize_text, get_unsplash_image, post_to_facebook, text_to_speech, log_post, init_db, save_api_keys, load_api_keys, generate_hashtags

app = Flask(__name__)
init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    tts_file = None
    keys = load_api_keys()
    
    if request.method == "POST":
        tiktok_url = request.form.get("tiktok_url")
        hf_api_key = request.form.get("hf_api_key")
        unsplash_key = request.form.get("unsplash_key")
        fb_token = request.form.get("fb_token")
        
        # Lưu API Keys vào DB
        save_api_keys(hf_api_key, unsplash_key, fb_token)
        
        video_data = get_tiktok_video_data(tiktok_url)
        if video_data:
            title = video_data.get("title", "")
            summary = summarize_text(title, hf_api_key)
            img_url = get_unsplash_image(summary, unsplash_key)
            
            hashtags = generate_hashtags(summary)
            message = f"{summary}\n\n{hashtags} 🔥"
            
            post_to_facebook(fb_token, message, image_url=img_url)
            log_post(title, summary, message, img_url)
            
            tts_file = text_to_speech(summary)
            result = {
                "title": title,
                "summary": summary,
                "image": img_url,
                "message": message,
                "tts_file": tts_file
            }
    return render_template("index.html", result=result, keys=keys)

@app.route("/apikeys", methods=["GET", "POST"])
def apikeys():
    keys = load_api_keys()
    if request.method == "POST":
        hf_api_key = request.form.get("hf_api_key")
        unsplash_key = request.form.get("unsplash_key")
        fb_token = request.form.get("fb_token")
        save_api_keys(hf_api_key, unsplash_key, fb_token)
        return redirect("/")
    return render_template("apikeys.html", keys=keys)

@app.route("/history")
def history():
    import sqlite3
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()
    conn.close()
    return render_template("history.html", posts=posts)

@app.route("/tts/<filename>")
def serve_tts(filename):
    return send_file(filename)

if __name__ == "__main__":
    app.run(debug=True)
