from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import requests
from datetime import datetime
from yt_dlp import YoutubeDL

app = Flask(__name__)

# ==== Trang chủ ====
@app.route('/')
def index():
    return render_template('index.html')

# ==== Trang lịch sử ====
@app.route('/history')
def history():
    return render_template('history.html')

# ==== Trang API Keys ====
@app.route('/apikeys', methods=['GET', 'POST'])
def apikeys():
    if request.method == 'POST':
        huggingface_key = request.form.get('huggingface_key')
        fb_access_token = request.form.get('fb_access_token')
        fb_page_id = request.form.get('fb_page_id')
        # Lưu tạm vào file (có thể thay bằng DB)
        with open('apikeys.txt', 'w') as f:
            f.write(f"{huggingface_key}\n{fb_access_token}\n{fb_page_id}")
        return redirect(url_for('index'))
    return render_template('apikeys.html')

# ==== API xử lý link TikTok ====
@app.route('/process', methods=['POST'])
def process():
    data = request.json
    tiktok_url = data.get('url')

    if not tiktok_url:
        return jsonify({"error": "Thiếu URL TikTok"}), 400

    try:
        # Lấy thông tin video từ TikTok
        ydl_opts = {'quiet': True, 'skip_download': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(tiktok_url, download=False)
            title = info.get('title', 'Video không có tiêu đề')
            thumbnail_url = info.get('thumbnail')

        # Gọi Hugging Face API tóm tắt (demo placeholder)
        summary = f"Tóm tắt nhanh: {title[:50]}..."

        return jsonify({
            "title": title,
            "thumbnail": thumbnail_url,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==== Chạy app trên Railway ====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
