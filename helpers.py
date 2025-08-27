import yt_dlp
from transformers import pipeline

# Tóm tắt video
def summarize_video(video_url):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    return summarizer(video_url, max_length=50, min_length=25, do_sample=False)[0]['summary_text']

# Gợi ý hashtag thông minh
def generate_hashtags(summary):
    keywords = [word for word in summary.split() if len(word) > 4]
    hashtags = [f"#{kw.capitalize()}" for kw in keywords[:5]]
    return " ".join(hashtags) + " #Nhutcoder #ai #congnghe"

# Lấy thumbnail từ TikTok
def get_tiktok_thumbnail(video_url):
    ydl_opts = {'skip_download': True, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return info.get('thumbnail', '')

# Thống kê Facebook Insights (Mock hoặc gọi API thật)
def get_facebook_insights():
    # Dữ liệu mẫu, cần API thật
    return {
        "post_impressions": 1250,
        "post_engaged_users": 240,
        "post_clicks": 85
    }

# Đếm số bài viết
def get_total_posts():
    import sqlite3
    conn = sqlite3.connect('dp.sqlite')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts")
    total = c.fetchone()[0]
    conn.close()
    return total
