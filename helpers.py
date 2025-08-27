import requests, sqlite3
from urllib.parse import quote
import facebook
from gtts import gTTS

# --- TikTok download ---
def get_tiktok_video_data(url):
    api_url = f"https://www.tiktok.com/oembed?url={quote(url)}"
    resp = requests.get(api_url)
    if resp.status_code == 200:
        return resp.json()
    return None

# --- Hugging Face summary ---
def summarize_text(text, hf_api_key):
    headers = {"Authorization": f"Bearer {hf_api_key}"}
    payload = {"inputs": text}
    resp = requests.post("https://api-inference.huggingface.co/models/facebook/bart-large-cnn", 
                         headers=headers, json=payload)
    if resp.status_code == 200:
        return resp.json()[0]["summary_text"]
    return text

# --- Unsplash image based on text ---
def get_unsplash_image(query, unsplash_access_key):
    url = f"https://api.unsplash.com/photos/random?query={quote(query)}&client_id={unsplash_access_key}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()["urls"]["regular"]
    return None

# --- Facebook Post ---
def post_to_facebook(page_access_token, message, image_url=None):
    graph = facebook.GraphAPI(access_token=page_access_token)
    if image_url:
        graph.put_photo(image=requests.get(image_url).content, message=message)
    else:
        graph.put_object(parent_object='me', connection_name='feed', message=message)

# --- Text-to-Speech ---
def text_to_speech(text, filename="tts.mp3"):
    tts = gTTS(text=text, lang='vi')
    tts.save(filename)
    return filename

# --- Database helpers ---
def init_db():
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT, summary TEXT, message TEXT, image_url TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  hf_api_key TEXT, unsplash_key TEXT, fb_token TEXT)''')
    conn.commit()
    conn.close()

def log_post(title, summary, message, image_url):
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute("INSERT INTO posts (title, summary, message, image_url) VALUES (?, ?, ?, ?)",
              (title, summary, message, image_url))
    conn.commit()
    conn.close()

def save_api_keys(hf_api_key, unsplash_key, fb_token):
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute("DELETE FROM api_keys")
    c.execute("INSERT INTO api_keys (hf_api_key, unsplash_key, fb_token) VALUES (?, ?, ?)",
              (hf_api_key, unsplash_key, fb_token))
    conn.commit()
    conn.close()

def load_api_keys():
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute("SELECT hf_api_key, unsplash_key, fb_token FROM api_keys ORDER BY id DESC LIMIT 1")
    keys = c.fetchone()
    conn.close()
    if keys:
        return {"hf_api_key": keys[0], "unsplash_key": keys[1], "fb_token": keys[2]}
    return {"hf_api_key":"", "unsplash_key":"", "fb_token":""}

# --- Generate hashtags from text ---
def generate_hashtags(text):
    words = [w for w in text.split() if len(w) > 3]
    hashtags = [f"#{w.lower()}" for w in words[:5]]  # 5 hashtags max
    hashtags.append("#Nhutcoder")
    return " ".join(hashtags)
