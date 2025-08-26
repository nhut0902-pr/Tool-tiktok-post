import requests
import os

def process_one_url(url, keys):
    """
    Lấy metadata từ TikTok và tóm tắt nội dung qua Hugging Face.
    """
    text = get_tiktok_metadata(url)
    return {"summary": summarize_text(text, keys)}

def get_tiktok_metadata(url):
    """
    Lấy tiêu đề/mô tả video TikTok qua API trung gian.
    """
    api_endpoint = f"https://www.tikwm.com/api/?url={url}"
    try:
        resp = requests.get(api_endpoint, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', {}).get('title', 'Video không có mô tả')
        return f"Lỗi khi gọi TikTok API: {resp.text}"
    except Exception as e:
        return f"Lỗi kết nối TikTok API: {e}"

def summarize_text(text, keys):
    """
    Gọi Hugging Face API để tóm tắt text.
    """
    api_key = keys.get("huggingface_key")
    if not api_key:
        return "Chưa cấu hình Hugging Face API Key"

    API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "inputs": text,
        "parameters": {"max_length": 120, "min_length": 60, "do_sample": False}
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            try:
                return resp.json()[0]["summary_text"]
            except Exception:
                return "Không phân tích được kết quả từ Hugging Face"
        return f"Lỗi Hugging Face API: {resp.text}"
    except Exception as e:
        return f"Lỗi kết nối Hugging Face API: {e}"

def get_api_keys_from_db():
    """
    Giả lập hàm lấy API Key từ database hoặc environment.
    """
    return {
        "huggingface_key": os.getenv("HUGGINGFACE_API_KEY")
    }
