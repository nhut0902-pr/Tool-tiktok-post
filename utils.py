import os
import re
import time
import json
import unicodedata
import requests
import sqlite3
from typing import Dict, Any, Optional

APP_DB = "db.sqlite3"
HF_MODEL_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"

URL_PATTERN = re.compile(r"http\S+|www\.\S+", flags=re.IGNORECASE)
CTRL_PATTERN = re.compile(r"[\u0000-\u0008\u000B-\u000C\u000E-\u001F]")


def sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    text = URL_PATTERN.sub("", text)
    text = CTRL_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_tiktok_meta(video_url: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(
            "https://www.tiktok.com/oembed",
            params={"url": video_url},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def unsplash_search_image(query: str, unsplash_key: str) -> Optional[Dict[str, Any]]:
    if not unsplash_key:
        return None
    try:
        q = sanitize_text(query) or "artificial intelligence"
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": q, "per_page": 1, "orientation": "landscape"},
            headers={"Accept-Version": "v1", "Authorization": f"Client-ID {unsplash_key}"},
            timeout=12
        )
        r.raise_for_status()
        data = r.json()
        if data.get("results"):
            return data["results"][0]
        return None
    except Exception:
        return None


def download_image(url: str, dest_path: str) -> str:
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(1024 * 32):
            if chunk:
                f.write(chunk)
    return dest_path


def summarize_with_hf(text: str, hf_token: str, min_length: int = 130, max_length: int = 320) -> str:
    text = sanitize_text(text)
    if not text:
        return ""
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    payload = {
        "inputs": text,
        "parameters": {"min_length": min_length, "max_length": max_length, "do_sample": False},
        "options": {"wait_for_model": True}
    }
    try:
        r = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=40)
        if r.status_code in (429, 503):
            return text[:max_length]
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data and "summary_text" in data[0]:
            return sanitize_text(data[0]["summary_text"])
        if isinstance(data, dict) and "error" in data:
            return text[:max_length]
        return sanitize_text(str(data))[:max_length]
    except Exception:
        return sanitize_text(text)[:max_length]


def post_photo_to_facebook(photo_path: str, caption: str, fb_page_id: str, fb_page_token: str) -> Dict[str, Any]:
    url = f"https://graph.facebook.com/v23.0/{fb_page_id}/photos"
    with open(photo_path, "rb") as f:
        files = {"source": f}
        data = {"caption": caption, "access_token": fb_page_token}
        r = requests.post(url, files=files, data=data, timeout=120)
        r.raise_for_status()
        return r.json()


def get_api_keys_from_db() -> Dict[str, str]:
    conn = sqlite3.connect(APP_DB)
    c = conn.cursor()
    c.execute("SELECT hf_token, unsplash_key, fb_page_id, fb_page_token FROM apikeys WHERE id=1")
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "hf_token": row[0] or "",
            "unsplash_key": row[1] or "",
            "fb_page_id": row[2] or "",
            "fb_page_token": row[3] or ""
        }
    return {
        "hf_token": os.environ.get("HF_TOKEN", ""),
        "unsplash_key": os.environ.get("UNSPLASH_KEY", ""),
        "fb_page_id": os.environ.get("FB_PAGE_ID", ""),
        "fb_page_token": os.environ.get("FB_PAGE_TOKEN", "")
    }


def build_caption(meta: dict, summary: str) -> str:
    author = sanitize_text(meta.get("author_name") or "")
    parts = []
    if summary:
        parts.append(summary)
    if author:
        parts.append(f"\nNguồn: {author}")
    parts.append("\n#AI #TinTucAI")
    return "\n".join(parts).strip()


def process_one_url(url: str, keys: Dict[str, str]) -> Dict[str, Any]:
    meta = fetch_tiktok_meta(url)
    if not meta:
        raise Exception("Lỗi: không lấy được metadata TikTok.")

    raw_caption = meta.get("title") or meta.get("author_name") or ""
    clean_caption = sanitize_text(raw_caption)

    hf_token = keys.get("hf_token", "")
    unsplash_key = keys.get("unsplash_key", "")
    fb_page_id = keys.get("fb_page_id", "")
    fb_page_token = keys.get("fb_page_token", "")

    summary = summarize_with_hf(clean_caption, hf_token, min_length=140, max_length=360)
    img = unsplash_search_image(clean_caption or "artificial intelligence", unsplash_key)
    if not img:
        raise Exception("Lỗi: không tìm được ảnh Unsplash.")
    image_url = img["urls"]["regular"]
    local_path = f"/tmp/unsplash_{int(time.time())}.jpg"
    download_image(image_url, local_path)

    caption = build_caption(meta, summary)
    post_resp = post_photo_to_facebook(local_path, caption, fb_page_id, fb_page_token)

    return {
        "facebook_response": post_resp,
        "summary": summary,
        "image_url": image_url,
        "meta": meta
    }
