import requests
import re

def get_tiktok_metadata(url):
    """
    Lấy metadata từ API trung gian. Có thể dùng RapidAPI hoặc self-hosted scraper.
    """
    try:
        api_url = "https://tiktok-metadata.p.rapidapi.com/"  # Ví dụ RapidAPI
        headers = {
            "X-RapidAPI-Key": "YOUR_RAPID_API_KEY",
            "X-RapidAPI-Host": "tiktok-metadata.p.rapidapi.com"
        }
        response = requests.get(api_url, headers=headers, params={"url": url})
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        return {"error": str(e)}


def summarize_with_hf(raw_text, hf_token):
    """
    Tóm tắt văn bản với Hugging Face, bỏ link TikTok, sửa lỗi ký tự.
    """
    try:
        # 1. Loại bỏ link
        clean_text = re.sub(r'http\S+', '', raw_text)

        # 2. Chuẩn hóa ký tự UTF-8
        clean_text = clean_text.encode('utf-8', errors='ignore').decode('utf-8')

        # 3. Gọi API Hugging Face
        API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": f"Bearer {hf_token}"}
        payload = {
            "inputs": clean_text,
            "parameters": {
                "min_length": 100,
                "max_length": 300,
                "do_sample": False
            }
        }
        response = requests.post(API_URL, headers=headers, json=payload)
        result = response.json()

        if isinstance(result, list) and len(result) > 0 and "summary_text" in result[0]:
            return result[0]["summary_text"]
        return "Không thể tóm tắt nội dung."
    except Exception as e:
        return f"Lỗi tóm tắt: {e}"


def get_unsplash_image(query, unsplash_key):
    """
    Lấy ảnh từ Unsplash dựa trên từ khóa (vd: AI, công nghệ).
    """
    try:
        url = "https://api.unsplash.com/photos/random"
        headers = {"Authorization": f"Client-ID {unsplash_key}"}
        params = {"query": query, "orientation": "landscape"}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("urls", {}).get("regular", "")
        return ""
    except Exception:
        return ""


def post_to_facebook(page_id, page_token, message, image_url=None):
    """
    Đăng bài lên Facebook Page.
    """
    try:
        if image_url:
            url = f"https://graph.facebook.com/{page_id}/photos"
            payload = {
                "url": image_url,
                "caption": message,
                "access_token": page_token
            }
        else:
            url = f"https://graph.facebook.com/{page_id}/feed"
            payload = {
                "message": message,
                "access_token": page_token
            }

        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def process_one_url(url, hf_token, unsplash_key, fb_page_id, fb_page_token):
    """
    Quy trình xử lý một link TikTok:
    - Lấy metadata
    - Tóm tắt với AI
    - Lấy ảnh từ Unsplash
    - Đăng lên Facebook
    """
    meta = get_tiktok_metadata(url)
    if not meta or "error" in meta:
        return f"Lỗi lấy metadata: {meta.get('error', 'Không có dữ liệu')}"

    raw_text = meta.get("title", "") + " " + meta.get("desc", "")
    summary = summarize_with_hf(raw_text, hf_token)

    image_url = get_unsplash_image("artificial intelligence", unsplash_key)
    fb_response = post_to_facebook(fb_page_id, fb_page_token, summary, image_url)

    return fb_response
