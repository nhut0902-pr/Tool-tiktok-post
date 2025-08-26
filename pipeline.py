import os, time, requests

def tiktok_oembed(video_url: str):
    try:
        r = requests.get(
            "https://www.tiktok.com/oembed",
            params={"url": video_url},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except:
        return None

def unsplash_search(query: str, unsplash_key: str):
    url = "https://api.unsplash.com/search/photos"
    params = {"query": query, "per_page": 1, "client_id": unsplash_key}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("results"):
        return data["results"][0]
    return None

def download_image(url: str, dest_path: str):
    r = requests.get(url, stream=True, timeout=20)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)

def summarize_text_hf(text: str, hf_token: str):
    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": text}
    url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    try:
        return r.json()[0]["summary_text"]
    except:
        return text[:150] + "..."

def post_photo_to_facebook(photo_path: str, message: str, fb_page_id: str, fb_page_token: str):
    url = f"https://graph.facebook.com/v23.0/{fb_page_id}/photos"
    files = {"source": open(photo_path, "rb")}
    data = {"caption": message, "access_token": fb_page_token}
    r = requests.post(url, files=files, data=data, timeout=120)
    r.raise_for_status()
    return r.json()

def process_tiktok_url(video_url: str, hf_token: str, unsplash_key: str, fb_page_id: str, fb_page_token: str):
    meta = tiktok_oembed(video_url)
    if not meta:
        return "Lỗi: không lấy được metadata TikTok"

    caption = meta.get("title") or meta.get("author_name") or "AI News"

    img_info = unsplash_search(caption, unsplash_key)
    if not img_info:
        return "Lỗi: không tìm được ảnh Unsplash"

    image_url = img_info["urls"]["regular"]
    image_path = f"/tmp/unsplash_{int(time.time())}.jpg"
    download_image(image_url, image_path)

    summary = summarize_text_hf(caption, hf_token)
    message = f"{summary}\n\nNguồn: {meta.get('author_name')}\nXem video: {video_url}\n#AI #TinTucAI"

    res = post_photo_to_facebook(image_path, message, fb_page_id, fb_page_token)
    return str(res)
