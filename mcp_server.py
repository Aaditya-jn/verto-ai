# mcp_server.py
import os
import json
import time
import fitz
import cv2
import PIL.Image
import urllib.request
import urllib.error
import concurrent.futures
from google import genai
from google.genai import types
from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

# ── Main Gemini client (image, video, document, translation only) ──────────────
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

MODEL = "gemini-flash-lite-latest"

# Grounded Config (uses Google Search Grounding + URL Context)
GROUNDED_TOOLS = [
    types.Tool(google_search=types.GoogleSearch()),
    types.Tool(url_context=types.UrlContext()),
]

GROUNDED_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
    tools=GROUNDED_TOOLS,
)

# Standard Config (no grounding)
STANDARD_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
)

mcp = FastMCP("verto-fake-news-mcp")


# ── Helper: Generate Content with Fallback ─────────────────────────────────────
def generate_content_with_fallback(contents, grounded: bool = True):
    """Call Gemini. If grounding quota is hit, fallback to standard generation."""
    if grounded:
        try:
            return client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=GROUNDED_CONFIG,
            )
        except Exception as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["quota", "limit", "429", "resource_exhausted", "billing", "blocked"]):
                return client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config=STANDARD_CONFIG,
                )
            raise e
    else:
        return client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=STANDARD_CONFIG,
        )


# ── 1. EXTRACT TEXT FROM IMAGE ─────────────────────────────────────────────────
@mcp.tool()
def extract_text_from_image(image_path: str) -> str:
    """Extract news claim text from an image file using PIL inline image delivery with grounding fallback."""
    try:
        img = PIL.Image.open(image_path)
        img_bytes = img.tobytes()

        import base64, io
        buffer = io.BytesIO()
        img.save(buffer, format=img.format or "PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        mime = f"image/{(img.format or 'png').lower()}"

        contents = [
            types.Content(parts=[
                types.Part.from_bytes(data=base64.b64decode(img_b64), mime_type=mime),
                types.Part.from_text(
                    text="Extract the main news claim or headline from this image. "
                    "Return only the text claim, nothing else."
                ),
            ])
        ]
        response = generate_content_with_fallback(contents, grounded=False)
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"


# ── 2. EXTRACT TEXT FROM VIDEO ─────────────────────────────────────────────────
@mcp.tool()
def extract_text_from_video(video_path: str) -> str:
    """Extract news claim from a video using direct upload or OpenCV frame extraction fallback."""
    try:
        # Fast local frame extraction using OpenCV
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_positions = [int(total_frames * x) for x in [0.1, 0.35, 0.65, 0.9]]

        import base64, io
        frame_parts = []
        for pos in sample_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if not ret:
                continue
            img = PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            frame_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            frame_parts.append(
                types.Part.from_bytes(data=base64.b64decode(frame_b64), mime_type="image/jpeg")
            )
        cap.release()

        if not frame_parts:
            return "Error: Could not extract frames from video."

        frame_parts.append(types.Part.from_text(
            text="These are sampled frames from a news video. "
            "Extract the main news claim or headline being shown or discussed. "
            "Return only the claim text, nothing else."
        ))

        contents = [types.Content(parts=frame_parts)]
        response = generate_content_with_fallback(contents, grounded=False)
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"


# ── 3. EXTRACT TEXT FROM DOCUMENT ──────────────────────────────────────────────
@mcp.tool()
def extract_text_from_document(doc_path: str) -> str:
    """Extract text from a PDF document using PyMuPDF, then summarize with grounding fallback."""
    try:
        doc = fitz.open(doc_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        extracted = text[:3000]
        if not extracted.strip():
            return "Error: No text could be extracted from this document."

        contents = [
            f"The following text was extracted from a news document:\n\n{extracted}\n\n"
            "Summarize the main news claim or headline from this text. "
            "Return only the extracted claim, nothing else."
        ]
        response = generate_content_with_fallback(contents, grounded=True)
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"


# ── 4. TRANSLATE TEXT ─────────────────────────────────────────────────────────
@mcp.tool()
def translate_text(text: str, target_language: str) -> str:
    """Translate verdict text to Hindi, Marathi, or Gujarati. Keep all emojis, URLs, and hashtags unchanged."""
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                f"Translate the following text to {target_language}. "
                "Keep all emojis, URLs, and hashtags exactly as they are. "
                f"Only translate the readable text portions:\n\n{text}"
            ],
            config=STANDARD_CONFIG,
        )
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
