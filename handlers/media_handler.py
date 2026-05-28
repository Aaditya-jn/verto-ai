# handlers/media_handler.py
import os
import requests

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/3gpp": ".3gp",
    "video/quicktime": ".mov",
    "application/pdf": ".pdf",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3"
}


def download_twilio_media(media_url: str, mime_type: str) -> str:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    ext = MIME_TO_EXT.get(mime_type, ".bin")
    local_path = f"/tmp/verto_media{ext}"
    response = requests.get(media_url, auth=(sid, token), timeout=30)
    with open(local_path, "wb") as f:
        f.write(response.content)
    return local_path


def get_media_category(mime_type: str) -> str:
    if "image" in mime_type:
        return "image"
    if "video" in mime_type:
        return "video"
    if "pdf" in mime_type or "document" in mime_type:
        return "document"
    if "audio" in mime_type:
        return "audio"
    return "unknown"
